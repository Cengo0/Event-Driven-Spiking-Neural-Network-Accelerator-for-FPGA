#!/usr/bin/env python3
"""Quick diagnostic: run just 5 batches at epoch 0 to find crash cause."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch

print(f"Python: {sys.executable}", flush=True)
print(f"PyTorch: {torch.__version__}", flush=True)
print(f"CUDA: {torch.cuda.is_available()}", flush=True)

torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
SEED = 42

from mnist_10class_train import DenseSTDP10Class
from onchip_stdp_faithful import FaithfulOnChipTrainer, PureInt8Trainer
from torchvision import datasets, transforms

print("[1] Loading MNIST...", flush=True)
transform = transforms.ToTensor()
train_ds = datasets.MNIST('./data', train=True, download=False, transform=transform)
test_ds  = datasets.MNIST('./data', train=False, download=False, transform=transform)

def to_tensors(ds, n=None):
    imgs, lbls = [], []
    for img, lbl in ds:
        imgs.append(img.squeeze(0)); lbls.append(lbl)
        if n and len(imgs) >= n: break
    return torch.stack(imgs), torch.tensor(lbls, dtype=torch.long)

# Use only 1000 train + 500 test for quick test
train_imgs, train_lbls = to_tensors(train_ds, 1000)
test_imgs,  test_lbls  = to_tensors(test_ds, 500)
print(f"  train={len(train_imgs)}, test={len(test_imgs)}", flush=True)

N = len(train_imgs)
flat_train = train_imgs.reshape(N, -1).to(DEVICE).float()
lbls_train = train_lbls.to(DEVICE)

print("[2] Creating trainers...", flush=True)
def make_trainer(cls):
    torch.manual_seed(SEED)
    torch.cuda.manual_seed(SEED)
    np.random.seed(SEED)
    return cls(n_input=784, n_classes=10, features_per_class=15,
               leak=0.5, timesteps=25, lr_plus=0.005, lr_minus=0.003, device=DEVICE)

sw = make_trainer(DenseSTDP10Class)
fc = make_trainer(FaithfulOnChipTrainer)
pi = make_trainer(PureInt8Trainer)
print("  Trainers created OK", flush=True)

print("[3] Init prototypes...", flush=True)
for trainer in [sw, fc, pi]:
    torch.manual_seed(SEED + 100); torch.cuda.manual_seed(SEED + 100)
    trainer.init_prototypes(train_imgs, train_lbls)
print("  Init OK", flush=True)
print(f"  SW init w range: [{sw.weights.min():.4f}, {sw.weights.max():.4f}]", flush=True)
print(f"  FC init w range: [{fc.weights.min():.4f}, {fc.weights.max():.4f}]", flush=True)

print("[4] Running 2 batches of epoch 0...", flush=True)
torch.manual_seed(SEED * 1000 + 0)
perm = torch.randperm(N, device=DEVICE)
BS = 128

for name, trainer in [("SW", sw), ("FC", fc), ("PI", pi)]:
    print(f"  Training {name}...", flush=True)
    for i, start in enumerate(range(0, min(N, BS*2), BS)):
        end = min(start + BS, N)
        idx = perm[start:end]
        imgs_b = flat_train[idx]
        lbls_b = lbls_train[idx]
        torch.manual_seed(SEED * 10000 + 0 * 100 + start)
        torch.cuda.manual_seed(SEED * 10000 + 0 * 100 + start)
        spikes = trainer.rate_encode(imgs_b)
        print(f"    batch {i}: spikes shape={spikes.shape}", flush=True)
        preds, pots, fired, ftimes = trainer.forward_batch(spikes)
        print(f"    batch {i}: preds={preds[:5]}", flush=True)
        trainer.train_rstdp_batch(spikes, lbls_b, preds, fired, ftimes)
        print(f"    batch {i}: STDP done", flush=True)
    trainer.adapt_thresholds()
    trainer.normalize_weights()
    print(f"  {name} OK — w range: [{trainer.weights.min():.4f} to {trainer.weights.max():.4f}]", flush=True)

print("[5] Validation pass...", flush=True)
flat_test = test_imgs.reshape(len(test_imgs), -1).to(DEVICE).float()
lbls_test_d = test_lbls.to(DEVICE)
for name, trainer in [("SW", sw), ("FC", fc), ("PI", pi)]:
    if hasattr(trainer, 'eval'):
        trainer.eval()
    correct = 0
    for vs in range(0, len(flat_test), 256):
        ve = min(vs+256, len(flat_test))
        sp = trainer.rate_encode(flat_test[vs:ve])
        pr, _, _, _ = trainer.forward_batch(sp)
        correct += (pr == lbls_test_d[vs:ve]).sum().item()
    if hasattr(trainer, 'train'):
        trainer.train()
    print(f"  {name} val acc: {correct/len(test_imgs)*100:.1f}%", flush=True)

# Weight correlation
sw_w = sw.weights.cpu().numpy()
fc_w = fc.weights.cpu().numpy()
corr = np.corrcoef(sw_w.flatten(), fc_w.flatten())[0,1]
maxd = np.abs(sw_w - fc_w).max()
print(f"[6] SW↔FC corr: {corr:.6f}, max_diff: {maxd:.2e}", flush=True)
print("DIAGNOSTIC COMPLETE - no crashes!", flush=True)
