from __future__ import annotations

import os
import json
import math
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import joblib
from dotenv import load_dotenv
import matplotlib.pyplot as plt

from models.lstm_model import create_model

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("edge-ai-train")

def env_str(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return default if v is None else str(v).strip()


def env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return int(v)


def env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return float(v)


@dataclass(frozen=True)
class TrainConfig:
    csv_path: str

    seq_len: int
    batch_size: int
    epochs: int
    lr: float

    hidden_size: int
    num_layers: int
    dropout: float

    val_split: float
    seed: int

    model_out_path: str
    preproc_out_path: str
    meta_out_path: str

    history_csv_path: str
    history_plot_path: str


def load_config() -> TrainConfig:
    return TrainConfig(
        csv_path=env_str("TRAIN_CSV_PATH", r"/home/gla/Desktop/T77_Autonomous_Cold-Chain_Spoilage_Prediction_System/sensors_data.csv"),

        # 2 sec interval -> 10 min history ~ 300 steps (you can tune)
        seq_len=env_int("SEQ_LEN", 300),

        # RTX 3050 4GB safe default
        batch_size=env_int("BATCH_SIZE", 128),

        epochs=env_int("EPOCHS", 40),
        lr=env_float("LR", 3e-4),

        hidden_size=env_int("HIDDEN_SIZE", 256),
        num_layers=env_int("NUM_LAYERS", 3),
        dropout=env_float("DROPOUT", 0.15),

        val_split=env_float("VAL_SPLIT", 0.10),
        seed=env_int("SEED", 7),

        model_out_path=env_str("MODEL_OUT_PATH", os.path.join("models", "best_model.pth")),
        preproc_out_path=env_str("PREPROC_OUT_PATH", os.path.join("models", "preprocessor.pkl")),
        meta_out_path=env_str("META_OUT_PATH", os.path.join("models", "model_meta.json")),

        history_csv_path=env_str("HISTORY_CSV_PATH", os.path.join("models", "training_history.csv")),
        history_plot_path=env_str("HISTORY_PLOT_PATH", os.path.join("models", "training_history.png")),
    )
CATEGORICAL_COLS = ["cargo_type", "scenario"]
NUMERIC_COLS = [
    "temperature",
    "humidity",
    "vibration",
    "door_open",
    "gps_lat",
    "gps_lon",
    "refrigeration_failed",
    "cumulative_exposure.total_minutes",
    "cumulative_exposure.temp_degree_minutes",
    "cumulative_exposure.humidity_percent_minutes",
    "cumulative_exposure.door_open_minutes",
    "cumulative_exposure.vibration_warn_minutes",
    "cumulative_exposure.vibration_critical_minutes",
    "cumulative_exposure.out_of_range_minutes_in_hour",
]


def _get_nested(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _to_float(x: Any, default: float = 0.0) -> float:
    if x is None:
        return float(default)
    if isinstance(x, bool):
        return float(int(x))
    try:
        return float(x)
    except Exception:
        return float(default)


def _to_int01(x: Any) -> int:
    if isinstance(x, bool):
        return int(x)
    if x is None:
        return 0
    s = str(x).strip().lower()
    return 1 if s in {"1", "true", "yes", "y", "on"} else 0


def set_seed(seed: int) -> None:
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


class Preprocessor:
    def __init__(self, numeric_cols: List[str], categorical_cols: List[str]) -> None:
        self.numeric_cols = list(numeric_cols)
        self.categorical_cols = list(categorical_cols)

        self.scaler = StandardScaler()
        try:
            self.ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        except TypeError:
            self.ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)

        self._fitted = False

    def fit(self, df: pd.DataFrame) -> "Preprocessor":
        X_num = df[self.numeric_cols].to_numpy(dtype=np.float32)
        X_cat = df[self.categorical_cols].astype(str).fillna("unknown").to_numpy()
        self.scaler.fit(X_num)
        self.ohe.fit(X_cat)
        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Preprocessor not fitted")

        X_num = df[self.numeric_cols].to_numpy(dtype=np.float32)
        X_cat = df[self.categorical_cols].astype(str).fillna("unknown").to_numpy()

        X_num_s = self.scaler.transform(X_num).astype(np.float32)
        X_cat_o = self.ohe.transform(X_cat).astype(np.float32)
        return np.concatenate([X_num_s, X_cat_o], axis=1).astype(np.float32)

    def categories_map(self) -> Dict[str, List[str]]:
        if not self._fitted:
            raise RuntimeError("Preprocessor not fitted")
        cats = {}
        for col, values in zip(self.categorical_cols, self.ohe.categories_):
            cats[col] = [str(v) for v in values.tolist()]
        return cats


def load_training_dataframe(cfg: TrainConfig) -> pd.DataFrame:
    if not cfg.csv_path:
        raise ValueError("TRAIN_CSV_PATH / csv_path is required")
    if not os.path.exists(cfg.csv_path):
        raise FileNotFoundError(f"CSV file not found: {cfg.csv_path}")

    logger.info(f"Loading training data from CSV: {cfg.csv_path}")
    df = pd.read_csv(cfg.csv_path)

    # Required core columns
    required_core = ["asset_id", "timestamp", "risk_proxy"]
    missing_core = [c for c in required_core if c not in df.columns]
    if missing_core:
        raise ValueError(f"CSV is missing required columns: {missing_core}")

    # Parse core fields
    df["asset_id"] = df["asset_id"].astype(str)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["risk_proxy"] = df["risk_proxy"].apply(_to_float)

    # Ensure categorical columns exist
    for c in CATEGORICAL_COLS:
        if c not in df.columns:
            df[c] = "unknown"
        df[c] = df[c].astype(str).fillna("unknown")

    # Ensure numeric columns exist and are numeric
    for c in NUMERIC_COLS:
        if c not in df.columns:
            df[c] = 0.0

    # Convert 0/1 style boolean columns
    df["door_open"] = df["door_open"].apply(_to_int01)
    df["refrigeration_failed"] = df["refrigeration_failed"].apply(_to_int01)

    # Convert all other numeric columns
    for c in NUMERIC_COLS:
        if c not in {"door_open", "refrigeration_failed"}:
            df[c] = df[c].apply(_to_float)

    df = df.dropna(subset=["timestamp"]).sort_values(["asset_id", "timestamp"]).reset_index(drop=True)

    logger.info(f"Training DataFrame ready: rows={len(df)} cols={len(df.columns)}")
    logger.info(f"Unique assets: {df['asset_id'].nunique()}")
    return df

class SlidingWindowDataset(Dataset):
    def __init__(
        self,
        indices: List[Tuple[int, int]],
        X_by_asset: List[np.ndarray],
        y_by_asset: List[np.ndarray],
        seq_len: int,
    ) -> None:
        self.indices = indices
        self.X_by_asset = X_by_asset
        self.y_by_asset = y_by_asset
        self.seq_len = int(seq_len)

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, i: int):
        asset_i, end_i = self.indices[i]
        X_asset = self.X_by_asset[asset_i]
        y_asset = self.y_by_asset[asset_i]
        X_seq = X_asset[end_i - self.seq_len : end_i, :]
        y = y_asset[end_i]
        return torch.from_numpy(X_seq).float(), torch.tensor(y, dtype=torch.float32)


def build_indices_by_time(
    asset_ids: List[str],
    y_by_asset: List[np.ndarray],
    ts_by_asset: List[np.ndarray],
    seq_len: int,
    cutoff_ts: pd.Timestamp,
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    train_idx: List[Tuple[int, int]] = []
    val_idx: List[Tuple[int, int]] = []

    for ai in range(len(asset_ids)):
        n = len(y_by_asset[ai])
        if n <= seq_len:
            continue

        ts = ts_by_asset[ai]
        for end_i in range(seq_len, n):
            label_ts = ts[end_i]
            if label_ts <= cutoff_ts:
                train_idx.append((ai, end_i))
            else:
                val_idx.append((ai, end_i))

    return train_idx, val_idx


def train_one_epoch(model, loader, optimizer, loss_fn, device, log_every_batches: int = 200) -> float:
    model.train()
    total = 0.0
    n = 0

    for bi, (Xb, yb) in enumerate(loader, start=1):
        Xb = Xb.to(device, non_blocking=True)
        yb = yb.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)
        pred = model(Xb)
        loss = loss_fn(pred, yb)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        bs = int(Xb.size(0))
        total += float(loss.item()) * bs
        n += bs

        if log_every_batches > 0 and bi % log_every_batches == 0:
            logger.info(f"Batch {bi} | batch_mse={loss.item():.6f}")

    return total / max(1, n)


@torch.no_grad()
def eval_epoch(model, loader, loss_fn, device) -> Tuple[float, float]:
    model.eval()
    total = 0.0
    n = 0

    for Xb, yb in loader:
        Xb = Xb.to(device, non_blocking=True)
        yb = yb.to(device, non_blocking=True)

        pred = model(Xb)
        loss = loss_fn(pred, yb)

        bs = int(Xb.size(0))
        total += float(loss.item()) * bs
        n += bs

    mse = total / max(1, n)
    rmse = math.sqrt(mse)
    return mse, rmse


def main() -> None:
    load_dotenv()
    cfg = load_config()
    set_seed(cfg.seed)

    logger.info("=== Edge-AI Training Started ===")
    logger.info(f"CSV_PATH={cfg.csv_path}")
    logger.info(f"SEQ_LEN={cfg.seq_len} BATCH_SIZE={cfg.batch_size} EPOCHS={cfg.epochs} LR={cfg.lr}")
    logger.info(f"HIDDEN_SIZE={cfg.hidden_size} NUM_LAYERS={cfg.num_layers} DROPOUT={cfg.dropout} VAL_SPLIT={cfg.val_split}")

    df = load_training_dataframe(cfg)

    cutoff_ts: pd.Timestamp = df["timestamp"].quantile(1.0 - cfg.val_split)
    logger.info(f"Time-based val cutoff (UTC): {cutoff_ts}")

    train_rows = df[df["timestamp"] <= cutoff_ts].copy()
    val_rows = df[df["timestamp"] > cutoff_ts].copy()
    logger.info(f"Train rows={len(train_rows)} | Val rows={len(val_rows)}")

    preproc = Preprocessor(NUMERIC_COLS, CATEGORICAL_COLS).fit(train_rows)
    logger.info("Preprocessor fitted (StandardScaler + OneHotEncoder).")
    logger.info(f"OHE categories: {preproc.categories_map()}")

    X_all = preproc.transform(df)  # (N, feature_dim)
    y_all = df["risk_proxy"].to_numpy(dtype=np.float32)
    ts_all = df["timestamp"].to_numpy()

    logger.info(f"Feature dim after OHE: {X_all.shape[1]}")

    asset_ids: List[str] = []
    X_by_asset: List[np.ndarray] = []
    y_by_asset: List[np.ndarray] = []
    ts_by_asset: List[np.ndarray] = []

    logger.info("Packing per-asset arrays...")
    for asset_id, g in df.groupby("asset_id", sort=False):
        idx = g.index.to_numpy()
        asset_ids.append(str(asset_id))
        X_by_asset.append(X_all[idx, :].astype(np.float32))
        y_by_asset.append(y_all[idx].astype(np.float32))
        ts_by_asset.append(ts_all[idx])

    train_idx, val_idx = build_indices_by_time(
        asset_ids=asset_ids,
        y_by_asset=y_by_asset,
        ts_by_asset=ts_by_asset,
        seq_len=cfg.seq_len,
        cutoff_ts=cutoff_ts,
    )

    logger.info(f"Sequences: train={len(train_idx)} val={len(val_idx)}")

    train_ds = SlidingWindowDataset(train_idx, X_by_asset, y_by_asset, cfg.seq_len)
    val_ds = SlidingWindowDataset(val_idx, X_by_asset, y_by_asset, cfg.seq_len)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    pin = device.type == "cuda"
    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True, num_workers=0, pin_memory=pin)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False, num_workers=0, pin_memory=pin)

    model = create_model(
        num_features=int(X_all.shape[1]),
        hidden_size=cfg.hidden_size,
        num_layers=cfg.num_layers,
        dropout=cfg.dropout,
        output_activation="sigmoid",
        bidirectional=True,
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.5,
        patience=3,
    )
    loss_fn = torch.nn.SmoothL1Loss(beta=0.1)


    best_val_rmse = float("inf")
    best_state: Optional[Dict[str, torch.Tensor]] = None
    patience = 6
    bad_epochs = 0
    history: List[Dict[str, float]] = []

    logger.info("Starting epochs...")
    for epoch in range(1, cfg.epochs + 1):
        logger.info(f"--- Epoch {epoch}/{cfg.epochs} ---")
        train_mse = train_one_epoch(model, train_loader, optimizer, loss_fn, device, log_every_batches=200)
        val_mse, val_rmse = eval_epoch(model, val_loader, loss_fn, device)
        prev_lr = optimizer.param_groups[0]["lr"];
        scheduler.step(val_rmse)
        new_lr = optimizer.param_groups[0]["lr"];

        if new_lr != prev_lr:
            logger.info(f"LR reduced: {prev_lr:.8f} -> {new_lr:.8f}")

        logger.info(f"Epoch {epoch} done | train_mse={train_mse:.6f} | val_mse={val_mse:.6f} | val_rmse={val_rmse:.6f}")
        current_lr = float(optimizer.param_groups[0]["lr"])

        history.append({
            "epoch": epoch,
            "train_loss": float(train_mse),
            "val_loss": float(val_mse),
            "val_rmse": float(val_rmse),
            "lr": current_lr,
        })

        if val_rmse < best_val_rmse:
            best_val_rmse = val_rmse
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
            bad_epochs = 0
            logger.info(f"New best model saved in memory | best_val_rmse={best_val_rmse:.6f}")
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                logger.info(f"Early stopping triggered after {epoch} epochs")
                break

    if best_state is None:
        raise RuntimeError("Training failed to produce a model state")

    os.makedirs(os.path.dirname(cfg.model_out_path) or ".", exist_ok=True)
    torch.save(best_state, cfg.model_out_path)

    os.makedirs(os.path.dirname(cfg.preproc_out_path) or ".", exist_ok=True)
    joblib.dump(
        {
            "numeric_cols": NUMERIC_COLS,
            "categorical_cols": CATEGORICAL_COLS,
            "scaler": preproc.scaler,
            "ohe": preproc.ohe,
        },
        cfg.preproc_out_path,
    )

    meta = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_source": "csv",
        "csv_path": cfg.csv_path,
        "seq_len": cfg.seq_len,
        "val_split": cfg.val_split,
        "time_split_cutoff_utc": str(cutoff_ts),
        "input_schema": {
            "categorical_cols": CATEGORICAL_COLS,
            "numeric_cols": NUMERIC_COLS,
            "ohe_categories": preproc.categories_map(),
            "feature_dim": int(X_all.shape[1]),
        },
        "model": {
            "hidden_size": cfg.hidden_size,
            "num_layers": cfg.num_layers,
            "dropout": cfg.dropout,
            "output_activation": "sigmoid",
        },
        "artifacts": {
            "model_path": cfg.model_out_path,
            "preprocessor_path": cfg.preproc_out_path,
            "history_csv_path": cfg.history_csv_path,
            "history_plot_path": cfg.history_plot_path,
        },
        "metrics": {
            "best_val_rmse": float(best_val_rmse),
        },
    }

    os.makedirs(os.path.dirname(cfg.meta_out_path) or ".", exist_ok=True)
    with open(cfg.meta_out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info("=== Training Completed ===")
    logger.info(f"Saved model        -> {cfg.model_out_path}")
    logger.info(f"Saved preprocessor -> {cfg.preproc_out_path}")
    logger.info(f"Saved meta         -> {cfg.meta_out_path}")
    logger.info(f"Best val RMSE      -> {best_val_rmse:.6f}")
    os.makedirs(os.path.dirname(cfg.history_csv_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(cfg.history_plot_path) or ".", exist_ok=True)

    history_df = pd.DataFrame(history)
    history_df.to_csv(cfg.history_csv_path, index=False)

    plt.figure(figsize=(10, 6))
    plt.plot(history_df["epoch"], history_df["train_loss"], label="Train Loss", marker="o")
    plt.plot(history_df["epoch"], history_df["val_loss"], label="Val Loss", marker="o")
    plt.plot(history_df["epoch"], history_df["val_rmse"], label="Val RMSE", marker="o")
    plt.xlabel("Epoch")
    plt.ylabel("Metric Value")
    plt.title("Training History")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(cfg.history_plot_path, dpi=200)
    plt.close()

if __name__ == "__main__":
    main()