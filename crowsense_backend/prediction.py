import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import List, Tuple, Optional, Deque
from collections import deque
import random
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CrowdRecord:
    timestamp: datetime
    crowd_count: float
    temperature: float
    noise: float
    air_quality: float

class Chomp1d(nn.Module):
    def __init__(self, chomp_size: int):
        super().__init__()
        self.chomp_size = chomp_size

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.chomp_size == 0:
            return x
        return x[:, :, :-self.chomp_size]


class TemporalBlock(nn.Module):
    def __init__(
        self, 
        in_channels: int, 
        out_channels: int, 
        kernel_size: int, 
        stride: int, 
        dilation: int, 
        padding: int, 
        dropout: float = 0.0
    ):
        super().__init__()
        self.conv1 = nn.Conv1d(
            in_channels, out_channels, kernel_size, 
            stride=stride, padding=padding, dilation=dilation
        )
        self.chomp1 = Chomp1d(padding)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        self.conv2 = nn.Conv1d(
            out_channels, out_channels, kernel_size, 
            stride=stride, padding=padding, dilation=dilation
        )
        self.chomp2 = Chomp1d(padding)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        self.net = nn.Sequential(
            self.conv1, self.chomp1, self.relu1, self.dropout1,
            self.conv2, self.chomp2, self.relu2, self.dropout2
        )
        
        self.downsample = nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else None
        self.relu = nn.ReLU()
        self.init_weights()

    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)


class TCNModel(nn.Module):

    def __init__(
        self, 
        num_inputs: int = 4, 
        num_channels: List[int] = [32, 32], 
        kernel_size: int = 3, 
        dropout: float = 0.05
    ):
        super().__init__()
        layers = []
        num_levels = len(num_channels)
        
        for i in range(num_levels):
            in_ch = num_inputs if i == 0 else num_channels[i - 1]
            out_ch = num_channels[i]
            dilation_size = 2 ** i
            padding = (kernel_size - 1) * dilation_size
            
            layers.append(
                TemporalBlock(
                    in_ch, out_ch, kernel_size, 
                    stride=1, dilation=dilation_size, 
                    padding=padding, dropout=dropout
                )
            )

        self.network = nn.Sequential(*layers)
        self.final_layer = nn.Sequential(
            nn.Conv1d(num_channels[-1], 1, kernel_size=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.permute(0, 2, 1).contiguous()
        y = self.network(x)
        y = self.final_layer(y)  
        out = y[:, 0, -1]  
        return out.unsqueeze(1)  

class FeatureNormalizer:
    def __init__(self):
        self.stats = {
            'crowd_count': {'count': 0, 'mean': 0.0, 'M2': 0.0},
            'temperature': {'count': 0, 'mean': 0.0, 'M2': 0.0},
            'noise': {'count': 0, 'mean': 0.0, 'M2': 0.0},
            'air_quality': {'count': 0, 'mean': 0.0, 'M2': 0.0},
        }
    
    def update(self, record: CrowdRecord):
        for name, value in [
            ('crowd_count', record.crowd_count),
            ('temperature', record.temperature),
            ('noise', record.noise),
            ('air_quality', record.air_quality)
        ]:
            s = self.stats[name]
            s['count'] += 1
            delta = value - s['mean']
            s['mean'] += delta / s['count']
            delta2 = value - s['mean']
            s['M2'] += delta * delta2
    
    def normalize(self, record: CrowdRecord) -> np.ndarray:
        normalized = []
        for name, value in [
            ('crowd_count', record.crowd_count),
            ('temperature', record.temperature),
            ('noise', record.noise),
            ('air_quality', record.air_quality)
        ]:
            s = self.stats[name]
            if s['count'] < 2:
                normalized.append(0.0)
            else:
                mean = s['mean']
                var = s['M2'] / s['count']
                std = np.sqrt(max(var, 1e-9))
                normalized.append((value - mean) / std)
        
        return np.array(normalized, dtype=np.float32)

class TCNPredictor:
    
    def __init__(
        self,
        window_size: int = 10,
        prediction_horizon: int = 10,  
        lr: float = 3e-4,
        device: Optional[str] = None,
        replay_size: int = 500
    ):
       
        self.window_size = window_size
        self.prediction_horizon = prediction_horizon
        
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        self.model = TCNModel(
            num_inputs=4,  # [crowd, temp, noise, aqi]
            num_channels=[32, 32],
            kernel_size=3,
            dropout=0.05
        ).to(self.device)
        
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        self.criterion = nn.MSELoss()
        
        self.normalizer = FeatureNormalizer()
        
        self.replay_buffer: Deque[Tuple[List[CrowdRecord], float]] = deque(maxlen=replay_size)
        
        print(f"[TCNPredictor] Initialized on device: {self.device}")
        print(f"[TCNPredictor] Window size: {window_size}, Prediction horizon: {prediction_horizon} minutes")
    
    def _records_to_tensor(self, records: List[CrowdRecord]) -> torch.Tensor:
        """Convert list of records to normalized tensor"""
        features = []
        for rec in records:
            norm = self.normalizer.normalize(rec)
            features.append(norm)
        
        arr = np.stack(features, axis=0) 
        tensor = torch.tensor(arr, dtype=torch.float32, device=self.device)
        return tensor.unsqueeze(0)  
    
    def predict(self, history: List[CrowdRecord]) -> float:
       
        for rec in history:
            self.normalizer.update(rec)
        
        if len(history) < self.window_size:
            counts = [r.crowd_count for r in history]
            return float(np.mean(counts)) if counts else 0.0
        
        window = history[-self.window_size:]
        
        self.model.eval()
        with torch.no_grad():
            x = self._records_to_tensor(window)
            output = self.model(x)
            prediction = float(output.squeeze().cpu().item())
        
        return prediction
    
    def train_step(self, history: List[CrowdRecord], target: float, steps: int = 3):
        
        if len(history) < self.window_size:
            return
        window = history[-self.window_size:]
        self.replay_buffer.append((window.copy(), target))
        
        batch_data = [self.replay_buffer[-1]]
        
        sample_size = min(len(self.replay_buffer) - 1, 4)
        if sample_size > 0:
            sampled = random.sample(list(self.replay_buffer)[:-1], k=sample_size)
            batch_data.extend(sampled)
        
        self.model.train()
        for _ in range(steps):
            self.optimizer.zero_grad()
            losses = []
            
            for records, tgt in batch_data:
                x = self._records_to_tensor(records)
                pred = self.model(x)
                y = torch.tensor([[tgt]], dtype=torch.float32, device=self.device)
                loss = self.criterion(pred, y)
                losses.append(loss)
            
            total_loss = torch.stack(losses).mean()
            total_loss.backward()
            
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=5.0)
            
            self.optimizer.step()
    
    def save_checkpoint(self, path: str = "tcn_model.pth"):
        
        checkpoint = {
            'model_state': self.model.state_dict(),
            'optimizer_state': self.optimizer.state_dict(),
            'normalizer_stats': self.normalizer.stats,
            'window_size': self.window_size,
            'prediction_horizon': self.prediction_horizon
        }
        torch.save(checkpoint, path)
        print(f"[TCNPredictor] Model saved to {path}")
    
    def load_checkpoint(self, path: str = "tcn_model.pth"):
        """Load model checkpoint"""
        try:
            checkpoint = torch.load(path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state'])
            self.normalizer.stats = checkpoint['normalizer_stats']
            print(f"[TCNPredictor] Model loaded from {path}")
        except FileNotFoundError:
            print(f"[TCNPredictor] No checkpoint found at {path}")

if __name__ == "__main__":
    from datetime import datetime, timedelta
    
    predictor = TCNPredictor(
        window_size=10,
        prediction_horizon=10,
        lr=3e-4
    )
    
    print("\n=== Generating sample training data ===")
    history = []
    base_time = datetime.now()
    
    for i in range(20):
        rec = CrowdRecord(
            timestamp=base_time + timedelta(minutes=i),
            crowd_count=15 + 5 * np.sin(i / 5) + np.random.randn(),
            temperature=28 + np.random.randn() * 0.5,
            noise=250 + np.random.randn() * 10,
            air_quality=170 + np.random.randn() * 5
        )
        history.append(rec)
    
    print("\n=== Making prediction ===")
    prediction = predictor.predict(history)
    print(f"Predicted crowd count: {prediction:.2f}")
    
    print("\n=== Training model ===")
    actual_count = 18.5
    predictor.train_step(history, actual_count, steps=3)
    print(f"Trained with actual count: {actual_count:.2f}")
    
    predictor.save_checkpoint("tcn_checkpoint.pth")