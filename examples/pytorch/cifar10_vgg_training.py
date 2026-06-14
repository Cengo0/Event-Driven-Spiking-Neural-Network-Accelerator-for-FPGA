"""
CIFAR-10 VGG Training Example for SpikeMold/SpikePress

This example shows how to train a VGG-style SNN on CIFAR-10 using PyTorch,
then export the weights for FPGA deployment.

Usage:
    python cifar10_vgg_training.py --epochs 200 --batch-size 64 --lr 0.01
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


class SpikingVGG(nn.Module):
    """Spiking VGG-style network for CIFAR-10 classification."""

    def __init__(self, cfg: list, num_classes: int = 10,
                 tau_mem: float = 20.0, threshold: float = 1.0):
        super().__init__()

        self.features = self._make_layers(cfg)
        self.classifier = nn.Linear(512, num_classes)
        self.tau_mem = tau_mem
        self.threshold = threshold

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


# VGG configurations
cfgs = {
    'VGG11': [64, 'M', 128, 'M', 256, 256, 'M', 512, 512, 'M', 512, 512],
    'VGG13': [64, 64, 'M', 128, 128, 'M', 256, 256, 'M', 512, 512, 'M', 512, 512],
    'VGG16': [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 'M', 512, 512, 512, 'M', 512, 512, 512],
    'VGG19': [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 256, 'M', 512, 512, 512, 512, 'M', 512, 512, 512, 512],
}


def get_vgg_model(version: str = 'VGG16', **kwargs) -> SpikingVGG:
    """Get a Spiking VGG model."""
    return SpikingVGG(cfgs[version], **kwargs)


def train_cifar10_vgg(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int = 200,
    lr: float = 0.01,
    momentum: float = 0.9,
    weight_decay: float = 5e-4,
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
) -> tuple:
    """Train the SpikingVGG on CIFAR-10."""

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

        # Validation
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


def export_to_snn(model: nn.Module, output_path: str):
    """Export trained model to SpikePress SNN format."""

    from spikepress.native import SNNModel, SNNLayer, compile_snn_model

    snn_model = SNNModel(name="cifar10_vgg")

    for name, module in model.named_modules():
        if isinstance(module, nn.Linear):
            weight = module.weight.detach().cpu().numpy()
            layer = SNNLayer(
                input_size=weight.shape[1],
                output_size=weight.shape[0]
            )
            layer.set_weights(weight.astype(np.int8))
            snn_model.add_layer(layer)

    artifact = compile_snn_model(snn_model, name="cifar10_vgg")
    artifact.save_npz(output_path)

    print(f"Exported to {output_path}")
    return artifact


if __name__ == '__main__':
    import torch.optim as optim

    parser = argparse.ArgumentParser(description='CIFAR-10 VGG Training')
    parser.add_argument('--version', type=str, default='VGG16',
                        choices=['VGG11', 'VGG13', 'VGG16', 'VGG19'],
                        help='VGG version')
    parser.add_argument('--epochs', type=int, default=200)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--lr', type=float, default=0.01)
    parser.add_argument('--output-dir', type=str, default='outputs/cifar10_vgg')
    parser.add_argument('--export-only', action='store_true')

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Data transforms
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2470, 0.2435, 0.2616)),
    ])

    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2470, 0.2435, 0.2616)),
    ])

    # Load datasets
    print("Loading CIFAR-10...")
    train_dataset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transform_train)
    test_dataset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform_test)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=2)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False, num_workers=2)

    # Create model
    print(f"Creating Spiking {args.version}...")
    model = get_vgg_model(
        args.version,
        num_classes=10,
        tau_mem=20.0,
        threshold=1.0
    )

    if args.export_only:
        weight_path = os.path.join(args.output_dir, 'model.pth')
        model.load_state_dict(torch.load(weight_path))
        export_to_snn(model, os.path.join(args.output_dir, 'cifar10_vgg.npz'))
    else:
        # Train
        print(f"Training on {'GPU' if torch.cuda.is_available() else 'CPU'}...")
        train_losses, val_accuracies = train_cifar10_vgg(
            model, train_loader, test_loader,
            epochs=args.epochs, lr=args.lr
        )

        # Save results
        torch.save(model.state_dict(), os.path.join(args.output_dir, 'model.pth'))
        np.save(os.path.join(args.output_dir, 'train_losses.npy'), train_losses)
        np.save(os.path.join(args.output_dir, 'val_accuracies.npy'), val_accuracies)

        export_to_snn(model, os.path.join(args.output_dir, 'cifar10_vgg.npz'))

        print(f"\nTraining complete!")
        print(f"Final validation accuracy: {max(val_accuracies):.2f}%")
        print(f"Results saved to {args.output_dir}")
