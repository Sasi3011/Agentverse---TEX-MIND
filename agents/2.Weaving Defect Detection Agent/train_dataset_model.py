"""Train ResNet18 fabric defect classifier on the local Fabric Defect Dataset."""
import os
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Subset, WeightedRandomSampler
from torchvision import datasets, models, transforms

AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = AGENT_DIR.parent.parent
DATASET_PATH = REPO_ROOT / "Fabric Defect Dataset"
MODEL_SAVE_PATH = AGENT_DIR / "weights" / "fabric_defect_model.pth"

CLASS_DISPLAY = {
    "New folder": "stain",
    "Vertical": "vertical",
    "defect free": "defect free",
}


def build_loaders(batch_size: int = 32):
    train_tf = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomResizedCrop(224, scale=(0.85, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(12),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    full_train = datasets.ImageFolder(root=str(DATASET_PATH), transform=train_tf)
    full_val = datasets.ImageFolder(root=str(DATASET_PATH), transform=val_tf)
    class_names = full_train.classes

    n = len(full_train)
    n_val = max(1, int(n * 0.15))
    n_train = n - n_val
    generator = torch.Generator().manual_seed(42)
    train_idx, val_idx = torch.utils.data.random_split(
        range(n), [n_train, n_val], generator=generator
    )

    train_ds = Subset(full_train, train_idx.indices)
    val_ds = Subset(full_val, val_idx.indices)

    targets = [full_train.samples[i][1] for i in train_idx.indices]
    class_count = torch.tensor([(torch.tensor(targets) == i).sum().item() for i in range(len(class_names))])
    weight = 1.0 / class_count.float().clamp(min=1)
    sample_weight = torch.tensor([weight[t] for t in targets])
    sampler = WeightedRandomSampler(sample_weight, num_samples=len(sample_weight), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    return train_loader, val_loader, class_names, weight


def evaluate(model, loader, device, criterion):
    model.eval()
    total = 0
    correct = 0
    loss_sum = 0.0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss_sum += criterion(outputs, labels).item() * images.size(0)
            correct += (outputs.argmax(1) == labels).sum().item()
            total += labels.size(0)
    return loss_sum / max(total, 1), correct / max(total, 1)


def train_fabric_defect_model(epochs: int = 25):
    if not DATASET_PATH.is_dir():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")

    print(f"Dataset: {DATASET_PATH}")
    os.makedirs(MODEL_SAVE_PATH.parent, exist_ok=True)

    train_loader, val_loader, class_names, class_weight = build_loaders()
    print(f"Classes ({len(class_names)}): {class_names}")
    print(f"Train batches: {len(train_loader)}, Val batches: {len(val_loader)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, len(class_names))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weight.to(device))
    optimizer = optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)

    best_val_acc = 0.0
    start = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        seen = 0
        train_correct = 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            train_correct += (outputs.argmax(1) == labels).sum().item()
            seen += images.size(0)

        train_acc = train_correct / max(seen, 1)
        val_loss, val_acc = evaluate(model, val_loader, device, criterion)
        scheduler.step(val_acc)

        print(
            f"Epoch {epoch}/{epochs} | "
            f"train loss {running_loss/seen:.4f} acc {train_acc*100:.2f}% | "
            f"val loss {val_loss:.4f} acc {val_acc*100:.2f}%"
        )

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            torch.save({
                "model_state_dict": model.state_dict(),
                "class_names": class_names,
                "val_accuracy": val_acc,
                "display_map": CLASS_DISPLAY,
            }, MODEL_SAVE_PATH)
            print(f"  -> saved best model (val acc {val_acc*100:.2f}%)")

    elapsed = time.time() - start
    print(f"Done in {elapsed:.1f}s. Best validation accuracy: {best_val_acc*100:.2f}%")
    print(f"Model saved to {MODEL_SAVE_PATH}")
    return best_val_acc


if __name__ == "__main__":
    train_fabric_defect_model()
