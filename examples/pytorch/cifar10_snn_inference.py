"""
CIFAR-10 SNN Inference Example for SpikeMold/SpikePress

This example shows how to:
1. Load a trained SNN model (ResNet/VGG)
2. Run inference on CIFAR-10 test set
3. Export results and compare with ground truth

Usage:
    python cifar10_snn_inference.py --model-path outputs/cifar10_resnet/model.pth \
                                      --output-dir outputs/cifar10_inference
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import torchvision
import torchvision.transforms as transforms
import numpy as np
import argparse
import os
import sys

# Add the software package to path
sys.path.append('../../software/python')

from spikepress.native.pytorch_interface import TorchSNNLayer


class SpikingResNet(nn.Module):
    """Spiking ResNet for CIFAR-10 classification."""

    def __init__(self, block: nn.Module, layers: List[int],
                 num_classes: int = 10,
                 tau_mem: float = 20.0, threshold: float = 1.0):
        super().__init__()

        self.in_channels = 64

        # Initial convolution
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1,
                               padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.lif_init = TorchSNNLayer(tau_mem=tau_mem, threshold=threshold)

        # ResNet layers
        self.layer1 = self._make_layer(block, 64, layers[0], stride=1,
                                       tau_mem=tau_mem, threshold=threshold)
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2,
                                       tau_mem=tau_mem, threshold=threshold)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2,
                                       tau_mem=tau_mem, threshold=threshold)

        # Final pooling and classifier
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.flatten = nn.Flatten()
        self.fc = nn.Linear(256, num_classes)

    def _make_layer(self, block: nn.Module, out_channels: int,
                    num_blocks: int, stride: int,
                    tau_mem: float, threshold: float) -> nn.Sequential:
        layers = []
        layers.append(block(self.in_channels, out_channels, stride,
                           tau_mem=tau_mem, threshold=threshold))
        self.in_channels = out_channels

        for _ in range(1, num_blocks):
            layers.append(block(out_channels, out_channels, 1,
                               tau_mem=tau_mem, threshold=threshold))

        return nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with multi-step temporal encoding."""
        batch_size = x.size(0)
        num_steps = getattr(self, 'num_steps', 100)

        # Reset LIF states
        for module in self.modules():
            if hasattr(module, 'reset_state'):
                module.reset_state()

        # Accumulator for output spikes
        output_spikes = torch.zeros(batch_size, self.fc.out_features, device=x.device)

        # Multi-step forward pass
        for step in range(num_steps):
            out = self.conv1(x)
            out = self.bn1(out)
            out = self.lif_init(out)

            out = self.layer1(out)
            out = self.layer2(out)
            out = self.layer3(out)

            out = self.avgpool(out)
            out = self.flatten(out)
            out = self.fc(out)

            output_spikes += out

        return output_spikes / num_steps


class SpikingVGG(nn.Module):
    """Spiking VGG-style network for CIFAR-10 classification."""

    def __init__(self, cfg: list, num_classes: int = 10,
                 tau_mem: float = 20.0, threshold: float = 1.0):
        super().__init__()

        self.features = self._make_layers(cfg)
        self.classifier = nn.Linear(512, num_classes)

    def _make_layers(self, cfg: list) -> nn.Sequential:
        layers = []
        in_channels = 3

        for v in cfg:
            if v == 'M':
                layers.append(nn.MaxPool2d(kernel_size=2, stride=2))
            else:
                conv2d = nn.Conv2d(in_channels, v, kernel_size=3, padding=1)
                bn = nn.BatchNorm2d(v)
                lif = TorchSNNLayer(tau_mem=self.tau_mem, threshold=self.threshold)
                layers.extend([conv2d, bn, lif])
                in_channels = v

        return nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with multi-step temporal encoding."""
        batch_size = x.size(0)
        num_steps = getattr(self, 'num_steps', 100)

        # Reset LIF states
        for module in self.modules():
            if hasattr(module, 'reset_state'):
                module.reset_state()

        # Accumulator for output spikes
        output_spikes = torch.zeros(batch_size, self.classifier.out_features, device=x.device)

        # Multi-step forward pass
        for step in range(num_steps):
            out = self.features(x)
            out = nn.AdaptiveAvgPool2d((1, 1))(out)
            out = torch.flatten(out, 1)
            out = self.classifier(out)
            output_spikes += out

        return output_spikes / num_steps


def run_inference(
    model: nn.Module,
    test_loader: DataLoader,
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
) -> Tuple[float, np.ndarray, np.ndarray]:
    """Run inference on test set and return accuracy + predictions."""

    model = model.to(device)
    model.eval()

    correct = 0
    total = 0
    all_predictions = []
    all_labels = []

    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs, labels = inputs.to(device), labels.to(device)

            outputs = model(inputs)
            _, predicted = torch.max(outputs.data, 1)

            total += labels.size(0)
            correct += (predicted == labels).sum().item()

            all_predictions.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    accuracy = 100 * correct / total
    return accuracy, np.array(all_predictions), np.array(all_labels)


def main():
    parser = argparse.ArgumentParser(description='CIFAR-10 SNN Inference')
    parser.add_argument('--model-path', type=str, required=True,
                        help='Path to trained model weights (.pth)')
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--num-steps', type=int, default=100,
                        help='Number of timesteps for inference')
    parser.add_argument('--output-dir', type=str, default='outputs/cifar10_inference')

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Data transforms
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2470, 0.2435, 0.2616)),
    ])

    # Load dataset
    print("Loading CIFAR-10 test set...")
    test_dataset = torchvision.datasets.CIFAR10(
        root='./data', train=False, download=True, transform=transform_test)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size,
                             shuffle=False, num_workers=2)

    # Create model
    print("Creating SpikingResNet-18...")
    from examples.pytorch.cifar10_resnet_training import BasicBlock

    model = SpikingResNet(
        block=BasicBlock,
        layers=[2, 2, 2, 2],  # ResNet-18 architecture
        num_classes=10,
        tau_mem=20.0,
        threshold=1.0
    )
    model.num_steps = args.num_steps

    # Load weights
    print(f"Loading model from {args.model_path}...")
    model.load_state_dict(torch.load(args.model_path, map_location='cpu'))
    model.eval()

    # Run inference
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    accuracy, predictions, labels = run_inference(model, test_loader, device)

    # Save results
    print(f"\nInference Results:")
    print(f"Accuracy: {accuracy:.2f}%")

    np.save(os.path.join(args.output_dir, 'predictions.npy'), predictions)
    np.save(os.path.join(args.output_dir, 'labels.npy'), labels)

    # Per-class accuracy
    class_names = ['airplane', 'automobile', 'bird', 'cat', 'deer',
                   'dog', 'frog', 'horse', 'ship', 'truck']
    per_class_acc = {}
    for c in range(10):
        mask = labels == c
        if mask.sum() > 0:
            acc = (predictions[mask] == labels[mask]).mean() * 100
            per_class_acc[class_names[c]] = acc

    print("\nPer-class accuracy:")
    for cls, acc in per_class_acc.items():
        print(f"  {cls}: {acc:.2f}%")

    # Save summary
    with open(os.path.join(args.output_dir, 'summary.txt'), 'w') as f:
        f.write(f"CIFAR-10 SNN Inference Results\n")
        f.write(f"=============================\n")
        f.write(f"Model: {args.model_path}\n")
        f.write(f"Num steps: {args.num_steps}\n")
        f.write(f"Batch size: {args.batch_size}\n")
        f.write(f"\nOverall Accuracy: {accuracy:.2f}%\n")
        f.write(f"\nPer-class accuracy:\n")
        for cls, acc in per_class_acc.items():
            f.write(f"  {cls}: {acc:.2f}%\n")

    print(f"\nResults saved to {args.output_dir}")


if __name__ == '__main__':
    main()
