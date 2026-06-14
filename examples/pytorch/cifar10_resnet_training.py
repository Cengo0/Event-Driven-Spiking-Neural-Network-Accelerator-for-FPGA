"""
CIFAR-10 ResNet Training Example for SpikeMold/SpikePress

This example shows how to train a ResNet-style SNN on CIFAR-10 using PyTorch,
then export the weights for FPGA deployment.

Usage:
    python cifar10_resnet_training.py --epochs 200 --batch-size 128 --lr 0.1
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import torchvision
import torchvision.transforms as transforms
import numpy as np
import argparse
import os
import sys
from typing import List, Tuple

# Add the software package to path
sys.path.append('../../software/python')

from spikepress.native import (
    SNNModel, SNNLayer, compile_snn_model,
    PoissonEncoder, LatencyEncoder, TemporalEncoder
)
from spikepress.native.pytorch_interface import TorchSNNLayer


class BasicBlock(nn.Module):
    """Basic ResNet block with spiking layers."""

    def __init__(self, in_channels: int, out_channels: int, stride: int = 1,
                 tau_mem: float = 20.0, threshold: float = 1.0):
        super().__init__()

        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3,
                               stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.lif1 = TorchSNNLayer(tau_mem=tau_mem, threshold=threshold)

        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.lif2 = TorchSNNLayer(tau_mem=tau_mem, threshold=threshold)

        # Shortcut connection
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1,
                          stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )

        # Final LIF after residual addition
        self.lif_out = TorchSNNLayer(tau_mem=tau_mem, threshold=threshold)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.lif1(out)

        out = self.conv2(out)
        out = self.bn2(out)

        # Add shortcut
        out += self.shortcut(x)

        out = self.lif_out(out)
        return out


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

        # Output layer - convert to spike rate
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


def train_cifar10_resnet(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int = 200,
    lr: float = 0.1,
    momentum: float = 0.9,
    weight_decay: float = 5e-4,
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
) -> Tuple[List[float], List[float]]:
    """Train the SpikingResNet on CIFAR-10."""

    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(
        model.parameters(),
        lr=lr,
        momentum=momentum,
        weight_decay=weight_decay
    )
    scheduler = optim.lr_scheduler.MultiStepLR(
        optimizer,
        milestones=[100, 150],
        gamma=0.1
    )

    train_losses = []
    val_accuracies = []

    for epoch in range(epochs):
        # Training phase
        model.train()
        train_loss = 0.0

        for batch_idx, (inputs, targets) in enumerate(train_loader):
            inputs, targets = inputs.to(device), targets.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        avg_train_loss = train_loss / len(train_loader)
        train_losses.append(avg_train_loss)

        # Validation phase
        model.eval()
        correct = 0
        total = 0

        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                _, predicted = torch.max(outputs.data, 1)
                total += targets.size(0)
                correct += (predicted == targets).sum().item()

        val_accuracy = 100 * correct / total
        val_accuracies.append(val_accuracy)

        print(f'Epoch [{epoch+1}/{epochs}] '
              f'Train Loss: {avg_train_loss:.4f} | '
              f'Val Acc: {val_accuracy:.2f}%')

        scheduler.step()

    return train_losses, val_accuracies


def export_to_snn_model(model: nn.Module, output_path: str):
    """Export trained model to SpikePress SNN format."""

    # Create SNN model
    snn_model = SNNModel(name="cifar10_resnet")

    # Convert each layer (simplified - actual conversion may need more work)
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear):
            # Extract weights and create SNN layer
            weight = module.weight.detach().cpu().numpy()
            bias = module.bias.detach().cpu().numpy() if module.bias is not None else None

            layer = SNNLayer(
                input_size=weight.shape[1],
                output_size=weight.shape[0]
            )
            layer.set_weights(weight.astype(np.int8))

            snn_model.add_layer(layer)

    # Compile and save
    artifact = compile_snn_model(snn_model, name="cifar10_resnet")
    artifact.save_npz(output_path)

    print(f"Exported to {output_path}")
    return artifact


def main():
    parser = argparse.ArgumentParser(description='CIFAR-10 ResNet Training')
    parser.add_argument('--epochs', type=int, default=200,
                        help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=128,
                        help='Batch size for training')
    parser.add_argument('--lr', type=float, default=0.1,
                        help='Learning rate')
    parser.add_argument('--output-dir', type=str, default='outputs/cifar10_resnet',
                        help='Output directory')
    parser.add_argument('--export-only', action='store_true',
                        help='Only export existing model weights')

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Data transforms
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465),
                            (0.2470, 0.2435, 0.2616)),
    ])

    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465),
                            (0.2470, 0.2435, 0.2616)),
    ])

    # Load datasets
    print("Loading CIFAR-10 dataset...")
    train_dataset = torchvision.datasets.CIFAR10(
        root='./data', train=True, download=True, transform=transform_train)
    test_dataset = torchvision.datasets.CIFAR10(
        root='./data', train=False, download=True, transform=transform_test)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size,
                              shuffle=True, num_workers=2)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size,
                             shuffle=False, num_workers=2)

    # Create model
    print("Creating SpikingResNet-18...")
    model = SpikingResNet(
        block=BasicBlock,
        layers=[2, 2, 2, 2],  # ResNet-18 architecture
        num_classes=10,
        tau_mem=20.0,
        threshold=1.0
    )

    if args.export_only:
        # Load existing weights and export
        weight_path = os.path.join(args.output_dir, 'model.pth')
        model.load_state_dict(torch.load(weight_path))
        export_to_snn_model(model, os.path.join(args.output_dir, 'cifar10_resnet.npz'))
    else:
        # Train the model
        print(f"Training on {'GPU' if torch.cuda.is_available() else 'CPU'}...")
        train_losses, val_accuracies = train_cifar10_resnet(
            model, train_loader, test_loader,
            epochs=args.epochs, lr=args.lr
        )

        # Save training results
        torch.save(model.state_dict(), os.path.join(args.output_dir, 'model.pth'))
        np.save(os.path.join(args.output_dir, 'train_losses.npy'), train_losses)
        np.save(os.path.join(args.output_dir, 'val_accuracies.npy'), val_accuracies)

        # Export to SNN format
        export_to_snn_model(model, os.path.join(args.output_dir, 'cifar10_resnet.npz'))

        print(f"\nTraining complete!")
        print(f"Final validation accuracy: {max(val_accuracies):.2f}%")
        print(f"Results saved to {args.output_dir}")


if __name__ == '__main__':
    main()
