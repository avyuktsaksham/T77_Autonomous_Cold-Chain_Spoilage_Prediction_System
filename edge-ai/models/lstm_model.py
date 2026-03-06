from __future__ import annotations
import os
import torch
import torch.nn as nn
class LSTMRiskRegressor(nn.Module):
    def __init__(
        self,
        num_features: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.20,
        output_activation: str = "sigmoid",
    ) -> None:
        super().__init__()

        if num_features <= 0:
            raise ValueError("num_features must be > 0")

        self.lstm = nn.LSTM(
            input_size=int(num_features),
            hidden_size=int(hidden_size),
            num_layers=int(num_layers),
            batch_first=True,
            dropout=float(dropout) if int(num_layers) > 1 else 0.0,
        )

        self.head = nn.Sequential(
            nn.LayerNorm(int(hidden_size)),
            nn.Linear(int(hidden_size), 64),
            nn.ReLU(),
            nn.Dropout(float(dropout)),
            nn.Linear(64, 1),
        )

        output_activation = (output_activation or "none").strip().lower()
        if output_activation not in {"sigmoid", "none"}:
            raise ValueError("output_activation must be 'sigmoid' or 'none'")
        self.output_activation = output_activation

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() != 3:
            raise ValueError("Expected x shape (batch, seq_len, num_features)")

        out, _ = self.lstm(x)
        last = out[:, -1, :]
        y = self.head(last).squeeze(-1)

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
def count_parameters(model: nn.Module) -> int:
    return int(sum(p.numel() for p in model.parameters() if p.requires_grad))
if __name__ == "__main__":
    nf = int(os.getenv("NUM_FEATURES", "16"))
    hs = int(os.getenv("HIDDEN_SIZE", "128"))
    nl = int(os.getenv("NUM_LAYERS", "2"))
    dp = float(os.getenv("DROPOUT", "0.20"))

    m = create_model(num_features=nf, hidden_size=hs, num_layers=nl, dropout=dp)
    print("[lstm_model] Model created")
    print(f"[lstm_model] num_features={nf} hidden_size={hs} num_layers={nl} dropout={dp}")
    print(f"[lstm_model] trainable_params={count_parameters(m)}")