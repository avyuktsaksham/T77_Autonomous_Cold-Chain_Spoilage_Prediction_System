from __future__ import annotations
import torch
import torch.nn as nn
class LSTMRiskRegressor(nn.Module):
    def __init__(
        self,
        num_features: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.20,
        output_activation: str = "sigmoid",  # "sigmoid" keeps output in 0..1, "none" leaves it unbounded
    ) -> None:
        super().__init__()
        if num_features <= 0:
            raise ValueError("num_features must be > 0")
        self.num_features = int(num_features)
        self.hidden_size = int(hidden_size)
        self.num_layers = int(num_layers)
        self.dropout = float(dropout)
        self.lstm = nn.LSTM(
            input_size=self.num_features,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            batch_first=True,
            dropout=self.dropout if self.num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.LayerNorm(self.hidden_size),
            nn.Linear(self.hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(64, 1),
        )
        output_activation = (output_activation or "none").strip().lower()
        if output_activation not in {"sigmoid", "none"}:
            raise ValueError("output_activation must be 'sigmoid' or 'none'")
        self.output_activation = output_activation
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() != 3:
            raise ValueError("Expected x shape (batch, seq_len, num_features)")
        out, _ = self.lstm(x)  # out: (batch, seq_len, hidden)
        last = out[:, -1, :]   # (batch, hidden)
        y = self.head(last).squeeze(-1)  # (batch,)
        if self.output_activation == "sigmoid":
            y = torch.sigmoid(y)
        return y
def create_model(
    num_features: int,
    hidden_size: int = 128,
    num_layers: int = 2,
    dropout: float = 0.20,
    output_activation: str = "sigmoid",
) -> LSTMRiskRegressor:
    return LSTMRiskRegressor(
        num_features=num_features,
        hidden_size=hidden_size,
        num_layers=num_layers,
        dropout=dropout,
        output_activation=output_activation,
    )