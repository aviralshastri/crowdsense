from __future__ import annotations
import math
import time
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Deque, List, Tuple, Any
from ultralytics import YOLO
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import cv2
from ultralytics import YOLO
import mysql.connector
from mysql.connector import errorcode


# -----------------------------
# data_models/record.py
# -----------------------------
@dataclass
class MinuteRecord:
    time: datetime
    cctv_count: Optional[float] 
    gas: float
    pir: float
    temperature: float
    noise: float

    # These will be added later in pipeline:
    sensor_est: Optional[float] = None
    fused_gt: Optional[float] = None
    prediction: Optional[float] = None
    error: Optional[float] = None


# -----------------------------
# preprocessing/outlier.py
# -----------------------------
class OutlierRejector:
    """
    Implements:
      - z-score based rejection (maintains running mean/std per sensor using small Welford windows)
      - Hampel filter using small window per feature
      - clipping to sensor-specific min/max
    """

    def __init__(
        self,
        z_thresh: float = 4.0,
        hampel_k: int = 7,
        hampel_thresh: float = 3.0,
        min_max: Optional[Dict[str, Tuple[float, float]]] = None,
    ):
        # z-score stats maintained via small Welford windows
        self.z_thresh = z_thresh
        self.hampel_k = hampel_k
        self.hampel_thresh = hampel_thresh

        # history windows for Hampel and z-score
        self.histories: Dict[str, Deque[float]] = {
            "gas": deque(maxlen=max(50, hampel_k * 3)),
            "pir": deque(maxlen=max(50, hampel_k * 3)),
            "temperature": deque(maxlen=max(50, hampel_k * 3)),
            "noise": deque(maxlen=max(50, hampel_k * 3)),
            "cctv_count": deque(maxlen=max(50, hampel_k * 3)),
        }

        # sensor-specific clipping bounds (defaults broad)
        self.min_max = min_max or {
            "gas": (0.0, 5000.0),
            "pir": (0.0, 1.0),
            "temperature": (-40.0, 85.0),
            "noise": (0.0, 140.0),
            "cctv_count": (0.0, 500.0),
        }

    @staticmethod
    def _median(data: List[float]) -> float:
        a = sorted(data)
        n = len(a)
        if n == 0:
            return 0.0
        mid = n // 2
        if n % 2 == 1:
            return a[mid]
        return 0.5 * (a[mid - 1] + a[mid])

    def _hampel_replace(self, vals: Deque[float], new_val: float) -> float:
        # use last k values (including new_val) to determine if it's an outlier
        window = list(vals)[- (self.hampel_k - 1):] if self.hampel_k - 1 > 0 else []
        window = window + [new_val]
        if len(window) < 3:
            return new_val
        med = self._median(window)
        # MAD
        abs_dev = [abs(x - med) for x in window]
        mad = self._median(abs_dev) or 1e-9
        if abs(new_val - med) / (1.4826 * mad) > self.hampel_thresh:
            # replace with median
            return float(med)
        return float(new_val)

    @staticmethod
    def _zscore(value: float, mean: float, std: float) -> float:
        if std <= 0:
            return 0.0
        return abs((value - mean) / std)

    def _compute_mean_std(self, vals: Deque[float]) -> Tuple[float, float]:
        arr = np.array(vals, dtype=float)
        if arr.size == 0:
            return 0.0, 0.0
        return float(arr.mean()), float(arr.std(ddof=0))

    def clean(self, record: MinuteRecord) -> MinuteRecord:
        # Work on a copy to avoid mutating input
        r = MinuteRecord(**{k: getattr(record, k) for k in record.__dataclass_fields__})
        # Process each sensor field
        for field_name in ["gas", "pir", "temperature", "noise", "cctv_count"]:
            val = getattr(r, field_name) if hasattr(r, field_name) else None
            if val is None:
                continue

            # clipping
            mn, mx = self.min_max.get(field_name, (float("-inf"), float("inf")))
            if val < mn:
                val = mn
            elif val > mx:
                val = mx

            # Hampel filter replacement
            hist = self.histories[field_name]
            val = self._hampel_replace(hist, val)

            # z-score rejection: if extremely deviant, replace with median
            # compute mean/std from history
            if len(hist) >= 2:
                mean, std = self._compute_mean_std(hist)
                z = self._zscore(val, mean, std)
                if z > self.z_thresh:
                    # extreme outlier -> replace with median of history
                    val = float(self._median(list(hist)))
            # push to history
            hist.append(float(val))
            setattr(r, field_name, val)

        return r


# -----------------------------
# preprocessing/normalization.py
# -----------------------------
class StreamingNormalizer:
    """
    Welford's algorithm per feature for online mean/variance.
    Supports update(record) and transform(record) -> normalized vector
    """

    def __init__(self):
        # state per feature: (count, mean, M2)
        self._state: Dict[str, Dict[str, float]] = {
            "gas": {"count": 0.0, "mean": 0.0, "M2": 0.0},
            "pir": {"count": 0.0, "mean": 0.0, "M2": 0.0},
            "temperature": {"count": 0.0, "mean": 0.0, "M2": 0.0},
            "noise": {"count": 0.0, "mean": 0.0, "M2": 0.0},
            "cctv_count": {"count": 0.0, "mean": 0.0, "M2": 0.0},
        }

    def update_value(self, name: str, value: float) -> None:
        s = self._state[name]
        s["count"] += 1.0
        delta = value - s["mean"]
        s["mean"] += delta / s["count"]
        delta2 = value - s["mean"]
        s["M2"] += delta * delta2

    def update(self, record: MinuteRecord) -> None:
        # update all available features
        # cctv_count may be None -> skip
        if record.cctv_count is not None:
            self.update_value("cctv_count", float(record.cctv_count))
        self.update_value("gas", float(record.gas))
        self.update_value("pir", float(record.pir))
        self.update_value("temperature", float(record.temperature))
        self.update_value("noise", float(record.noise))

    def mean_var(self, name: str) -> Tuple[float, float]:
        s = self._state[name]
        mean = s["mean"]
        if s["count"] < 2:
            return mean, 1.0
        var = s["M2"] / (s["count"])
        return mean, max(var, 1e-9)

    def transform(self, record: MinuteRecord) -> np.ndarray:
        # returns normalized vector [gas, pir, temperature, noise] (cctv excluded from features)
        out = []
        for name in ["gas", "pir", "temperature", "noise"]:
            mean, var = self.mean_var(name)
            std = math.sqrt(var)
            val = getattr(record, name)
            normalized = (float(val) - mean) / (std if std > 0 else 1.0)
            out.append(float(normalized))
        return np.asarray(out, dtype=np.float32)


# -----------------------------
# preprocessing/builder.py
# -----------------------------
class FeatureBuilder:
    """
    Build features tensor from cleaned + normalized records.
    Returns 1D tensor shape (4,) for a single timestamp.
    """

    def build_features(self, record: MinuteRecord, normalized_vector: Optional[np.ndarray] = None) -> torch.Tensor:
        if normalized_vector is None:
            raise ValueError("normalized_vector must be provided")
        # ensure ordering [gas_norm, pir_norm, temp_norm, noise_norm]
        tensor = torch.from_numpy(normalized_vector).to(dtype=torch.float32)
        return tensor  # shape (4,)


# -----------------------------
# fusion/sensor_regressor.py
# -----------------------------
class _SmallMLP(nn.Module):
    def __init__(self, input_dim: int = 4, hidden: int = 16):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch?, input_dim)
        return self.net(x)


class SensorRegressor:
    """
    Online-learnable small MLP mapping normalized features -> sensor_est (float).
    Performs SGD updates on single examples (or small batches).
    """

    def __init__(self, lr: float = 1e-4, device: Optional[torch.device] = None):
        self.device = device or (torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu"))
        self.model = _SmallMLP(input_dim=4, hidden=32).to(self.device)
        # Use simple SGD with small lr
        self.lr = lr
        self.opt = optim.SGD(self.model.parameters(), lr=self.lr)
        self.loss_fn = nn.MSELoss()

    def predict(self, features: torch.Tensor) -> float:
        """
        features: torch.Tensor shape (4,) or (1,4)
        """
        x = features
        if x.dim() == 1:
            x = x.unsqueeze(0)
        x = x.to(self.device)
        self.model.eval()
        with torch.no_grad():
            out = self.model(x)
        val = float(out.squeeze().cpu().item())
        return val

    def update(self, features: torch.Tensor, target: float) -> None:
        # Single-step SGD update
        x = features
        if x.dim() == 1:
            x = x.unsqueeze(0)
        x = x.to(self.device)
        y = torch.tensor([target], dtype=torch.float32, device=self.device).unsqueeze(0)
        self.model.train()
        self.opt.zero_grad()
        pred = self.model(x)
        loss = self.loss_fn(pred, y)
        loss.backward()
        self.opt.step()


# -----------------------------
# fusion/kalman.py
# -----------------------------
class KalmanFusion:
    """
    Simple 1D Kalman filter to fuse sensor_est and cctv_count.
    The returned fused_gt is the filter's posterior estimate.
    """

    def __init__(
        self,
        x0: float = 0.0,
        P0: float = 1.0,
        R_sensor: float = 4.0,  # variance of sensor estimator
        R_cctv: float = 1.0,  # variance of cctv measurement
        Q: float = 0.01,  # process noise variance
    ):
        self.x = float(x0)
        self.P = float(P0)
        self.R_sensor = float(R_sensor)
        self.R_cctv = float(R_cctv)
        self.Q = float(Q)

    def fuse(self, sensor_est: Optional[float], cctv_count: Optional[float]) -> float:
        """
        Both inputs may be None. Basic strategy:
          - If both present: perform combined measurement update (sequential)
          - If only one present: update with that.
          - If none: predict step only.
        """
        # Predict (identity model): x = x, P = P + Q
        self.P += self.Q

        # helper to update with measurement z with variance R
        def update_with(z: float, R: float):
            # Kalman gain
            K = self.P / (self.P + R)
            self.x = self.x + K * (z - self.x)
            self.P = (1.0 - K) * self.P

        # use cctv_count and sensor_est
        if cctv_count is not None and sensor_est is not None:
            # fuse sequentially: first sensor, then cctv
            update_with(sensor_est, self.R_sensor)
            update_with(cctv_count, self.R_cctv)
        elif sensor_est is not None:
            update_with(sensor_est, self.R_sensor)
        elif cctv_count is not None:
            update_with(cctv_count, self.R_cctv)
        # else no measurement: keep prediction

        return float(self.x)


# -----------------------------
# model/tcn.py
# -----------------------------
class Chomp1d(nn.Module):
    def __init__(self, chomp_size: int):
        super().__init__()
        self.chomp_size = chomp_size

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, channels, seq_len + padding)
        if self.chomp_size == 0:
            return x
        return x[:, :, :-self.chomp_size]


class TemporalBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int, stride: int, dilation: int, padding: int, dropout: float = 0.0):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size, stride=stride, padding=padding, dilation=dilation)
        self.chomp1 = Chomp1d(padding)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size, stride=stride, padding=padding, dilation=dilation)
        self.chomp2 = Chomp1d(padding)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        self.net = nn.Sequential(self.conv1, self.chomp1, self.relu1, self.dropout1,
                                 self.conv2, self.chomp2, self.relu2, self.dropout2)
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
    """
    Small Temporal Convolutional Network.
    Inputs: sequence of feature vectors; for our case features per timestep are 4-dim
    We will accept input shape: (batch, seq_len, features) and transform to Conv1d (batch, channels, seq_len)
    Output: single scalar prediction per batch (next-minute crowd count)
    """

    def __init__(self, num_inputs: int = 4, num_channels: List[int] = [32, 32], kernel_size: int = 3, dropout: float = 0.05):
        super().__init__()
        layers = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            in_ch = num_inputs if i == 0 else num_channels[i - 1]
            out_ch = num_channels[i]
            dilation_size = 2 ** i
            padding = (kernel_size - 1) * dilation_size
            layers.append(TemporalBlock(in_ch, out_ch, kernel_size, stride=1, dilation=dilation_size, padding=padding, dropout=dropout))

        self.network = nn.Sequential(*layers)
        self.final_layer = nn.Sequential(
            nn.Conv1d(num_channels[-1], 1, kernel_size=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, features)
        # transform to (batch, features, seq_len)
        x = x.permute(0, 2, 1).contiguous()
        y = self.network(x)
        y = self.final_layer(y)  # (batch, 1, seq_len)
        # we need last time-step value (causal)
        # y shape (batch, 1, seq_len) - take last index
        out = y[:, 0, -1]  # (batch,)
        return out.unsqueeze(1)  # (batch, 1)


# -----------------------------
# model/model_manager.py
# -----------------------------
class ModelManager:
    """
    Holds TCN model, replay buffer, inference and online learning,
    EMA of weights, save/load checkpoints.
    """

    def __init__(self,
                 device: Optional[torch.device] = None,
                 window_size: int = 10,
                 lr: float = 3e-4,
                 ema_alpha: float = 0.99,
                 replay_size: int = 500):
        self.device = device or (torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu"))
        self.window_size = window_size
        self.model = TCNModel(num_inputs=4, num_channels=[32, 32], kernel_size=3).to(self.device)
        self.lr = lr
        self.opt = optim.Adam(self.model.parameters(), lr=self.lr)
        self.criterion = nn.MSELoss()
        self.replay: Deque[Tuple[List[MinuteRecord], float]] = deque(maxlen=replay_size)
        self.ema_alpha = ema_alpha
        self.ema_state: Dict[str, torch.Tensor] = {k: v.detach().cpu().clone() for k, v in self.model.state_dict().items()}

    def _records_to_tensor(self, window: List[MinuteRecord], normalizer: StreamingNormalizer) -> torch.Tensor:
        # returns (1, seq_len, feature_dim)
        features = []
        for rec in window:
            norm = normalizer.transform(rec)
            features.append(norm)
        arr = np.stack(features, axis=0)  # (seq_len, feature_dim)
        t = torch.tensor(arr, dtype=torch.float32, device=self.device).unsqueeze(0)  # (1, seq_len, feat)
        return t

    def predict(self, window: List[MinuteRecord], normalizer: StreamingNormalizer) -> float:
        if len(window) < self.window_size:
            # not enough data: return simple average of cctv_count or 0
            vals = [r.cctv_count for r in window if r.cctv_count is not None]
            if vals:
                return float(sum(vals) / len(vals))
            return 0.0
        self.model.eval()
        x = self._records_to_tensor(window[-self.window_size:], normalizer)
        with torch.no_grad():
            out = self.model(x)
        return float(out.squeeze().cpu().item())

    def update(self, window: List[MinuteRecord], target: float, normalizer: StreamingNormalizer, steps: int = 3) -> None:
        """
        Performs online learning with 1-5 gradient steps (default 3).
        Saves the example to replay buffer and occasionally samples minibatches from replay.
        """
        if len(window) < self.window_size:
            return

        # save to replay buffer
        copied_window = [MinuteRecord(**{k: getattr(r, k) for k in r.__dataclass_fields__}) for r in window[-self.window_size:]]
        self.replay.append((copied_window, float(target)))

        # single example update + a small replay sample
        batch_windows = [self.replay[-1]]
        # sample up to 4 more from replay randomly
        sample_size = min(len(self.replay), 4)
        if sample_size > 1:
            sampled = random.sample(list(self.replay)[:-1] if len(self.replay) > 1 else list(self.replay), k=min(sample_size - 1, max(0, len(self.replay) - 1)))
            batch_windows.extend(sampled)

        self.model.train()
        for step in range(max(1, min(5, steps))):
            self.opt.zero_grad()
            losses = []
            for win, tgt in batch_windows:
                x = self._records_to_tensor(win, normalizer)
                out = self.model(x)          # shape may be (1), (1,1), (1,1,1), etc.
                out = out.view(-1)           # flatten to 1D
                pred = out[0]                # first element (tensor)
                y = torch.tensor([tgt], dtype=torch.float32, device=self.device)
                loss = self.criterion(pred, y)
                losses.append(loss)
            loss_total = torch.stack(losses).mean()
            loss_total.backward()
            # gradient clipping for stability
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=5.0)
            self.opt.step()

            # update EMA
            self._update_ema()

    def _update_ema(self):
        sd = self.model.state_dict()
        for k, v in sd.items():
            v_cpu = v.detach().cpu()
            self.ema_state[k] = self.ema_alpha * self.ema_state[k] + (1.0 - self.ema_alpha) * v_cpu

    def apply_ema(self):
        # swap in EMA weights (on CPU) to model (on device)
        sd = {k: v.clone().to(self.device) for k, v in self.ema_state.items()}
        self.model.load_state_dict(sd)

    def save(self, path: str = "tcn_checkpoint.pth") -> None:
        # save model + optimizer + replay
        payload = {
            "model_state": self.model.state_dict(),
            "opt_state": self.opt.state_dict(),
            "replay": list(self.replay),
            "ema_state": self.ema_state,
        }
        torch.save(payload, path)

    def load(self, path: str = "tcn_checkpoint.pth") -> None:
        try:
            payload = torch.load(path, map_location=self.device)
            self.model.load_state_dict(payload["model_state"])
            if "opt_state" in payload:
                try:
                    self.opt.load_state_dict(payload["opt_state"])
                except Exception:
                    # optimizer state may not match if device differs; ignore
                    pass
            self.replay = deque(payload.get("replay", []), maxlen=self.replay.maxlen)
            self.ema_state = payload.get("ema_state", self.ema_state)
        except FileNotFoundError:
            # no checkpoint yet - ignore
            pass


# -----------------------------
# storage/db.py
# -----------------------------
class Database:
    """
    Minimal MySQL wrapper using mysql-connector-python.
    Note: caller must provide valid connection params.
    """

    def __init__(self,
                 host: str = "127.0.0.1",
                 port: int = 3306,
                 user: str = "root",
                 password: str = "mysql",
                 database: str = "crowdsensedb"):
        self.cfg = {
            "user": user,
            "password": password,
            "host": host,
            "port": port,
            "database": database,
            "raise_on_warnings": True,
        }
        self.conn: Optional[mysql.connector.connection_cext.CMySQLConnection] = None
        self._connect_and_init()

    def _connect_and_init(self):
        try:
            self.conn = mysql.connector.connect(**self.cfg)
            self._ensure_table()
        except mysql.connector.Error as err:
            # For offline testing, allow falling back to an in-memory list if DB not available.
            print(f"[Database] MySQL connection failed: {err}. Falling back to in-memory store.")
            self.conn = None
            # fallback store
            self._mem_table: List[Dict[str, Any]] = []

    def _ensure_table(self):
        if self.conn is None:
            return
        cursor = self.conn.cursor()
        try:
            create_table = (
                "CREATE TABLE IF NOT EXISTS minute_records ("
                "id INT AUTO_INCREMENT PRIMARY KEY,"
                "timestamp DATETIME NOT NULL,"
                "cctv_count FLOAT NULL,"
                "gas FLOAT NOT NULL,"
                "pir FLOAT NOT NULL,"
                "temperature FLOAT NOT NULL,"
                "noise FLOAT NOT NULL,"
                "sensor_est FLOAT NULL,"
                "fused_gt FLOAT NULL,"
                "prediction FLOAT NULL,"
                "error FLOAT NULL"
                ") ENGINE=InnoDB"
            )
            cursor.execute(create_table)
            self.conn.commit()
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                # Table already exists, this is fine - just continue
                print("[Database] Table 'minute_records' already exists. Using existing table.")
            else:
                # Some other error occurred, re-raise it
                raise
        finally:
            cursor.close()

    def _row_to_record(self, row: Tuple) -> MinuteRecord:
        # mapping: id, timestamp, cctv_count, gas, pir, temperature, noise, sensor_est, fused_gt, prediction, error
        # some fields may be None; tuple indexing depends on schema
        # We'll name columns explicitly when fetching
        # This method used in fetch_last_n only with explicit SELECT
        raise NotImplementedError("_row_to_record should not be called directly")

    def insert_record(self, record: MinuteRecord) -> None:
        if self.conn is None:
            # fallback in-memory
            self._mem_table.append({
                "timestamp": record.time,
                "cctv_count": record.cctv_count,
                "gas": record.gas,
                "pir": record.pir,
                "temperature": record.temperature,
                "noise": record.noise,
                "sensor_est": record.sensor_est,
                "fused_gt": record.fused_gt,
                "prediction": record.prediction,
                "error": record.error,
            })
            return

        cursor = self.conn.cursor()
        insert_sql = (
            "INSERT INTO minute_records (timestamp, cctv_count, gas, pir, temperature, noise, sensor_est, fused_gt, prediction, error) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        vals = (
            record.time.strftime("%Y-%m-%d %H:%M:%S"),
            record.cctv_count,
            record.gas,
            record.pir,
            record.temperature,
            record.noise,
            record.sensor_est,
            record.fused_gt,
            record.prediction,
            record.error,
        )
        cursor.execute(insert_sql, vals)
        self.conn.commit()
        cursor.close()

    def fetch_last_n(self, n: int) -> List[MinuteRecord]:
        if self.conn is None:
            # fallback: read last n from mem table
            rows = self._mem_table[-n:]
            out = []
            for r in rows:
                out.append(MinuteRecord(
                    time=r["timestamp"],
                    cctv_count=r["cctv_count"],
                    gas=r["gas"],
                    pir=r["pir"],
                    temperature=r["temperature"],
                    noise=r["noise"],
                    sensor_est=r.get("sensor_est"),
                    fused_gt=r.get("fused_gt"),
                    prediction=r.get("prediction"),
                    error=r.get("error"),
                ))
            return out

        cursor = self.conn.cursor(dictionary=True)
        sql = (
            "SELECT timestamp, cctv_count, gas, pir, temperature, noise, sensor_est, fused_gt, prediction, error "
            "FROM minute_records ORDER BY timestamp DESC LIMIT %s"
        )
        cursor.execute(sql, (n,))
        rows = cursor.fetchall()
        cursor.close()
        # rows are newest first; reverse to chronological
        out: List[MinuteRecord] = []
        for row in reversed(rows):
            ts = row["timestamp"]
            if isinstance(ts, datetime):
                t = ts
            else:
                t = datetime.strptime(str(ts), "%Y-%m-%d %H:%M:%S")
            out.append(MinuteRecord(
                time=t,
                cctv_count=row["cctv_count"],
                gas=float(row["gas"]),
                pir=float(row["pir"]),
                temperature=float(row["temperature"]),
                noise=float(row["noise"]),
                sensor_est=row.get("sensor_est"),
                fused_gt=row.get("fused_gt"),
                prediction=row.get("prediction"),
                error=row.get("error"),
            ))
        return out

    def update_prediction(self, time_dt: datetime, predicted_value: float) -> None:
        if self.conn is None:
            for r in self._mem_table:
                if isinstance(r["timestamp"], datetime) and r["timestamp"] == time_dt:
                    r["prediction"] = float(predicted_value)
                    return
            # if not found, append a minimal
            self._mem_table.append({
                "timestamp": time_dt,
                "cctv_count": None,
                "gas": 0.0,
                "pir": 0.0,
                "temperature": 0.0,
                "noise": 0.0,
                "sensor_est": None,
                "fused_gt": None,
                "prediction": float(predicted_value),
                "error": None,
            })
            return

        cursor = self.conn.cursor()
        sql = "UPDATE minute_records SET prediction = %s WHERE timestamp = %s"
        cursor.execute(sql, (predicted_value, time_dt.strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()
        cursor.close()

    def update_fused_gt(self, time_dt: datetime, fused_gt: float) -> None:
        if self.conn is None:
            for r in self._mem_table:
                if r["timestamp"] == time_dt:
                    r["fused_gt"] = float(fused_gt)
                    return
            # append if missing
            self._mem_table.append({
                "timestamp": time_dt,
                "cctv_count": None,
                "gas": 0.0,
                "pir": 0.0,
                "temperature": 0.0,
                "noise": 0.0,
                "sensor_est": None,
                "fused_gt": float(fused_gt),
                "prediction": None,
                "error": None,
            })
            return

        cursor = self.conn.cursor()
        sql = "UPDATE minute_records SET fused_gt = %s WHERE timestamp = %s"
        cursor.execute(sql, (fused_gt, time_dt.strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()
        cursor.close()

    def update_error(self, time_dt: datetime, error: float) -> None:
        if self.conn is None:
            for r in self._mem_table:
                if r["timestamp"] == time_dt:
                    r["error"] = float(error)
                    return
            # append if missing
            self._mem_table.append({
                "timestamp": time_dt,
                "cctv_count": None,
                "gas": 0.0,
                "pir": 0.0,
                "temperature": 0.0,
                "noise": 0.0,
                "sensor_est": None,
                "fused_gt": None,
                "prediction": None,
                "error": float(error),
            })
            return

        cursor = self.conn.cursor()
        sql = "UPDATE minute_records SET error = %s WHERE timestamp = %s"
        cursor.execute(sql, (error, time_dt.strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()
        cursor.close()


# -----------------------------
# pipeline/ingest_handler.py
# -----------------------------
class IngestHandler:
    """
    Handles ingesting raw minute data:
      - OutlierRejector.clean()
      - Normalizer.update() + transform()
      - FeatureBuilder.build_features()
      - SensorRegressor.predict() -> sensor_est
      - KalmanFusion.fuse(sensor_est, cctv_count) -> fused_gt
      - Save full MinuteRecord to DB
    """

    def __init__(self,
                 db: Database,
                 outlier: OutlierRejector,
                 normalizer: StreamingNormalizer,
                 builder: FeatureBuilder,
                 sensor_reg: SensorRegressor,
                 kalman: KalmanFusion):
        self.db = db
        self.outlier = outlier
        self.normalizer = normalizer
        self.builder = builder
        self.sensor_reg = sensor_reg
        self.kalman = kalman

    def process_minute(self, raw_record: MinuteRecord) -> MinuteRecord:
        # 1. Outlier clean
        cleaned = self.outlier.clean(raw_record)

        # 2. Update normalizer with cleaned values and transform to normalized vector
        self.normalizer.update(cleaned)
        norm_vector = self.normalizer.transform(cleaned)

        # 3. Build features tensor
        features = self.builder.build_features(cleaned, norm_vector)  # tensor shape (4,)

        # 4. Sensor regressor prediction
        sensor_est = self.sensor_reg.predict(features)
        cleaned.sensor_est = sensor_est

        # 5. Kalman fusion with cctv_count
        fused = self.kalman.fuse(sensor_est=sensor_est, cctv_count=cleaned.cctv_count)
        cleaned.fused_gt = fused

        # 6. Persist to DB
        self.db.insert_record(cleaned)

        return cleaned


# -----------------------------
# pipeline/predictor.py
# -----------------------------
class Predictor:
    """
    Load last 10 records from DB, build window, call ModelManager.predict(), save prediction to DB
    """

    def __init__(self, db: Database, model_mgr: ModelManager, normalizer: StreamingNormalizer):
        self.db = db
        self.model_mgr = model_mgr
        self.normalizer = normalizer

    def run(self) -> Optional[Tuple[datetime, float]]:
        window = self.db.fetch_last_n(self.model_mgr.window_size)
        if not window:
            return None
        predicted = self.model_mgr.predict(window, self.normalizer)
        # prediction is for next minute after last record's timestamp
        last_ts = window[-1].time
        predict_ts = last_ts + timedelta(minutes=1)
        # Save prediction for the previous minute? Spec says save prediction to DB — we'll attach it to the last timestamp
        self.db.update_prediction(last_ts, predicted)
        return last_ts, predicted


# -----------------------------
# pipeline/trainer.py
# -----------------------------
class Trainer:
    """
    Called once GT arrives for previous minute:
      - Load last 10 records
      - Use fused_gt as target for TCN
      - Compute error = fused_gt - predicted
      - Update model: ModelManager.update()
      - Save error + updated model state to DB
    """

    def __init__(self, db: Database, model_mgr: ModelManager, normalizer: StreamingNormalizer):
        self.db = db
        self.model_mgr = model_mgr
        self.normalizer = normalizer

    def run(self) -> Optional[Tuple[datetime, float, float]]:
        """
        Returns tuple (target_time, fused_gt, error) if training applied, else None.
        Assumes fused_gt is present for most recent record and that a prediction exists for same timestamp.
        """
        window = self.db.fetch_last_n(self.model_mgr.window_size)
        if len(window) < self.model_mgr.window_size:
            return None
        target_record = window[-1]
        if target_record.fused_gt is None:
            # nothing to train on
            return None
        target = float(target_record.fused_gt)
        predicted = float(target_record.prediction) if target_record.prediction is not None else self.model_mgr.predict(window, self.normalizer)
        error = target - predicted

        # update model using fused_gt as target for time index (train to predict next minute from previous window)
        self.model_mgr.update(window, target, self.normalizer, steps=3)

        # update DB with error
        self.db.update_error(target_record.time, error)

        # optionally save model checkpoint
        self.model_mgr.save()

        return target_record.time, target, error

class YOLOCrowdCounter:
    """
    Uses YOLO model (via ultralytics) to count people in images.
    Loads model once at initialization and provides fast inference.
    """

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        person_class_id: int = 0,
        device: Optional[str] = None,
        verbose: bool = False
    ):
        """
        Initialize YOLO model for crowd counting.
        
        Args:
            model_path: Path to YOLO model weights (.pt file)
            conf_threshold: Confidence threshold for detections (0-1)
            iou_threshold: IoU threshold for NMS (0-1)
            person_class_id: Class ID for 'person' in COCO (default: 0)
            device: Device to run inference on ('cpu', 'cuda', '0', '1', etc.)
                   If None, automatically selects best available device
            verbose: Whether to print model loading info
        """
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.person_class_id = person_class_id
        self.verbose = verbose
        
        # Load YOLO model
        try:
            print(f"[YOLOCrowdCounter] Loading model from: {model_path}")
            self.model = YOLO(model_path)
            
            # Set device
            if device is not None:
                self.model.to(device)
                self.device = device
            else:
                # Auto-detect device
                import torch
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
                self.model.to(self.device)
            
            print(f"[YOLOCrowdCounter] Model loaded successfully on device: {self.device}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load YOLO model from {model_path}: {e}")

    def predict(self, image: np.ndarray) -> int:
        """
        Predict crowd count from an OpenCV image.
        
        Args:
            image: OpenCV image (BGR format, numpy array)
                   Shape should be (height, width, 3)
        
        Returns:
            count: Number of people detected in the image
        """
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("Image must be a valid numpy array (OpenCV image)")
        
        if len(image.shape) != 3 or image.shape[2] != 3:
            raise ValueError(f"Image must be BGR format with shape (H, W, 3), got shape: {image.shape}")
        
        try:
            # Run inference
            results = self.model.predict(
                source=image,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=self.verbose,
                device=self.device
            )
            
            # Extract detections from first result (single image)
            result = results[0]
            
            # Filter for person class only
            person_count = 0
            if result.boxes is not None and len(result.boxes) > 0:
                # Get class IDs of all detections
                class_ids = result.boxes.cls.cpu().numpy()
                
                # Count persons (class_id == person_class_id)
                person_count = int(np.sum(class_ids == self.person_class_id))
            
            if self.verbose:
                print(f"[YOLOCrowdCounter] Detected {person_count} person(s) in image")
            
            return person_count
            
        except Exception as e:
            print(f"[YOLOCrowdCounter] Prediction failed: {e}")
            return 0

    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.
        
        Returns:
            info: Dictionary containing model metadata
        """
        return {
            "model_type": self.model.type,
            "device": self.device,
            "conf_threshold": self.conf_threshold,
            "iou_threshold": self.iou_threshold,
            "person_class_id": self.person_class_id,
            "model_task": self.model.task,
        }


# -----------------------------
# main.py (example loop)
# -----------------------------
def _simulate_minute(previous_time: Optional[datetime] = None) -> MinuteRecord:
    """
    Returns a synthetic MinuteRecord. In a real system you'd receive real sensor readings.
    We simulate some correlation between sensors and ground cctv_count.
    """
    now = (previous_time + timedelta(minutes=1)) if previous_time else datetime.utcnow()
    # base crowd
    base = random.uniform(0, 10)
    # sensors reflect base + noise
    gas = max(0.0, 100.0 * base + random.normalvariate(0, 30))
    pir = max(0.0, min(1.0, 0.05 * base + random.normalvariate(0, 0.05)))
    temperature = 20.0 + random.normalvariate(0, 1.0)
    noise = max(0.0, 30.0 + 2.0 * base + random.normalvariate(0, 3.0))
    # cctv_count simulates aggregated average from camera (maybe intermittently missing)
    cctv_present = random.random() > 0.05  # 5% missing
    cctv_count = (base + random.normalvariate(0, 1.0)) if cctv_present else None
    return MinuteRecord(time=now, cctv_count=cctv_count, gas=gas, pir=pir, temperature=temperature, noise=noise)


def main_loop_example(iterations: int = 10, db_cfg: Optional[Dict[str, Any]] = None):
    # Instantiate components
    db_cfg = db_cfg or {}
    db = Database(**db_cfg)
    outlier = OutlierRejector()
    normalizer = StreamingNormalizer()
    builder = FeatureBuilder()
    sensor_reg = SensorRegressor(lr=1e-4)
    kalman = KalmanFusion()
    ingest = IngestHandler(db, outlier, normalizer, builder, sensor_reg, kalman)

    model_mgr = ModelManager()
    predictor = Predictor(db, model_mgr, normalizer)
    trainer = Trainer(db, model_mgr, normalizer)

    # Start with an initial warm-up of a few minutes to populate normalizer and model window
    last_time = None
    print("[Main] Starting simulation loop. Press Ctrl-C to stop.")
    try:
        for it in range(iterations):
            # simulate ingesting a minute
            rec = _simulate_minute(last_time)
            last_time = rec.time
            cleaned = ingest.process_minute(rec)
            print(f"[Ingest] Time={cleaned.time} CCTV={cleaned.cctv_count} Gas={cleaned.gas:.1f} PIR={cleaned.pir:.3f} Temp={cleaned.temperature:.2f} Noise={cleaned.noise:.1f} SensorEst={cleaned.sensor_est:.2f} Fused={cleaned.fused_gt:.2f}")

            # run predictor (predict for last minute)
            pred_res = predictor.run()
            if pred_res is not None:
                ts, pred = pred_res
                print(f"[Predictor] For timestamp {ts} predicted={pred:.3f}")

            # simulate waiting one minute (we will not actually sleep full minute in example)
            # Next minute: when GT (fused_gt) is considered to have arrived for previous minute, run trainer
            train_res = trainer.run()
            if train_res is not None:
                t_time, tgt, err = train_res
                print(f"[Trainer] Trained on {t_time} fused_gt={tgt:.3f} error={err:.3f}")

            # tiny sleep only for simulation nicety
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Interrupted by user.")
    print("[Main] Simulation ended.")


if __name__ == "__main__":
    # Run a short example loop (not infinite by default). To run forever replace iterations with while True.
    main_loop_example(iterations=200)
