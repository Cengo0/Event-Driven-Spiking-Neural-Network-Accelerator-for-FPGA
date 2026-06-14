#!/usr/bin/env python3
"""Quick evaluation of saved faithful model."""
import sys, os, torch, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
from onchip_stdp_faithful import FaithfulOnChipTrainer

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load MNIST directly (same as training script)
from torchvision import datasets, transforms
test_ds = datasets.MNIST('./data', train=False, download=True,
                          transform=transforms.ToTensor())
test_imgs = torch.stack([img.squeeze(0) for img, _ in test_ds])
test_lbls = torch.tensor([lbl for _, lbl in test_ds], dtype=torch.long)
print(f"Test set: {len(test_imgs)} images, shape={test_imgs.shape}")

# Load model
model_path = 'data/cache/onchip_faithful_model_150n.npz'
saved = np.load(model_path)
print(f"Model keys: {list(saved.keys())}")
print(f"Weights shape: {saved['weights'].shape}")
print(f"Weights range: [{saved['weights'].min():.4f}, {saved['weights'].max():.4f}]")

# Create trainer and load weights
trainer = FaithfulOnChipTrainer(n_classes=10, features_per_class=15, device=DEVICE)
trainer.weights = torch.tensor(saved['weights'], device=DEVICE, dtype=torch.float32)
trainer.thresholds = torch.tensor(saved['thresholds'], device=DEVICE, dtype=torch.float32)

# Test in eval mode (int8 forward = FPGA-realistic)
print("\n--- Int8 Eval (FPGA-realistic) ---")
acc, pc, pt = trainer.test_batch(test_imgs, test_lbls)
print(f"Accuracy: {acc:.1f}%")
per_class = (pc / pt.clamp(min=1) * 100)
for c in range(10):
    print(f"  Class {c}: {per_class[c].item():.1f}% ({int(pc[c].item())}/{int(pt[c].item())})")

# Test in train mode (float forward = identical to SW)
print("\n--- Float Forward (identical to SW) ---")
trainer.train()
acc2, pc2, pt2 = trainer.test_batch(test_imgs, test_lbls)
print(f"Accuracy: {acc2:.1f}%")
per_class2 = (pc2 / pt2.clamp(min=1) * 100)
for c in range(10):
    print(f"  Class {c}: {per_class2[c].item():.1f}% ({int(pc2[c].item())}/{int(pt2[c].item())})")

print(f"\nInt8 gap: {acc2 - acc:.1f}%")

# Also load and compare with SW model if available
sw_path = 'data/cache/mnist_10class_model_150n.npz'
if os.path.exists(sw_path):
    sw_saved = np.load(sw_path)
    sw_w = sw_saved['weights']
    fc_w = saved['weights']
    corr = np.corrcoef(sw_w.flatten(), fc_w.flatten())[0, 1]
    print(f"\nSW vs Faithful weight correlation: {corr:.6f}")
    print(f"SW weight range: [{sw_w.min():.4f}, {sw_w.max():.4f}]")
    print(f"FC weight range: [{fc_w.min():.4f}, {fc_w.max():.4f}]")
    print(f"Max abs diff: {np.abs(sw_w - fc_w).max():.6f}")
