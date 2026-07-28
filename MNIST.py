import torch
import torch.nn as nn

from .layers import (
    ExpandTemporalDim,
    LIFSpike,
    MergeTemporalDim,
    TensorNormalization,
    add_dimention,
)


class SmallMNISTSNN(nn.Module):
    """
    Small convolutional SNN for static 28x28 MNIST images.

    Input:
        [batch, 1, 28, 28]

    Output when T > 0:
        [T, batch, 10]

    Approximately 52,000 trainable parameters.
    """

    def __init__(
        self,
        T: int,
        num_classes: int = 10,
        norm=None,
        tau: float = 1.0,
    ):
        super().__init__()

        if T < 1:
            raise ValueError("SmallMNISTSNN expects T >= 1")

        self.T = T
        self.tau = tau
        self.poisson = False

        if norm is None:
            norm = ((0.1307,), (0.3081,))

        self.norm = TensorNormalization(*norm)
        #self.encode = Poisson()
        self.merge = MergeTemporalDim(T)
        self.expand = ExpandTemporalDim(T)

        self.features = nn.Sequential(
            # [T*B, 1, 28, 28] -> [T*B, 8, 28, 28]
            nn.Conv2d(
                in_channels=1,
                out_channels=8,
                kernel_size=3,
                padding=1,
                bias=False,
            ),
            nn.BatchNorm2d(8),
            LIFSpike(T=T, tau=tau),
            nn.AvgPool2d(kernel_size=2),  # 28 -> 14

            # [T*B, 8, 14, 14] -> [T*B, 16, 14, 14]
            nn.Conv2d(
                in_channels=8,
                out_channels=16,
                kernel_size=3,
                padding=1,
                bias=False,
            ),
            nn.BatchNorm2d(16),
            LIFSpike(T=T, tau=tau),
            nn.AvgPool2d(kernel_size=2),  # 14 -> 7
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(16 * 7 * 7, 64),
            LIFSpike(T=T, tau=tau),
            nn.Linear(64, num_classes),
        )

        self._initialize_weights()

    def _initialize_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Conv2d):
                nn.init.kaiming_normal_(
                    module.weight,
                    mode="fan_out",
                    nonlinearity="relu",
                )
            elif isinstance(module, nn.BatchNorm2d):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(
                    module.weight,
                    nonlinearity="linear",
                )
                nn.init.zeros_(module.bias)

    def set_simulation_time(self, T: int, mode: str = "bptt"):
        self.T = T

        for module in self.modules():
            if isinstance(module, (LIFSpike, ExpandTemporalDim)):
                module.T = T

            if isinstance(module, LIFSpike):
                module.mode = mode

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Match the repository's VGG behavior:
        # constant encoding uses normalized input;
        # Poisson encoding operates on input values in [0, 1].
        if not self.poisson:
            x = self.norm(x)

        # [B, 1, 28, 28] -> [T, B, 1, 28, 28]
        x = add_dimention(x, self.T)

        if self.poisson:
            x = self.encode(x)

        # [T, B, 1, 28, 28] -> [T*B, 1, 28, 28]
        x = self.merge(x)

        x = self.features(x)
        x = self.classifier(x)

        # [T*B, 10] -> [T, B, 10]
        x = self.expand(x)

        return x
