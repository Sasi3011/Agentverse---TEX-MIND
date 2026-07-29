import os

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models, transforms

MODEL_PATH = os.path.join(os.path.dirname(__file__), "weights", "fabric_defect_model.pth")

DISPLAY_NAMES = {
    "New folder": "stain",
    "Vertical": "vertical",
    "horizontal": "horizontal",
    "lines": "lines",
    "hole": "hole",
    "stain": "stain",
    "defect free": "defect free",
}


class DefectDetector:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.class_names = [
            "defect free", "hole", "horizontal", "lines", "New folder", "stain", "Vertical"
        ]
        self.model = None
        self.val_accuracy = None

        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self.reload_model()

    def reload_model(self):
        if not os.path.exists(MODEL_PATH):
            print(f"No trained weights at {MODEL_PATH}. Run train_dataset_model.py first.")
            self.model = None
            return

        try:
            checkpoint = torch.load(MODEL_PATH, map_location=self.device, weights_only=False)
            self.class_names = checkpoint.get("class_names", self.class_names)
            self.val_accuracy = checkpoint.get("val_accuracy")

            model = models.resnet18(weights=None)
            model.fc = nn.Linear(model.fc.in_features, len(self.class_names))
            model.load_state_dict(checkpoint["model_state_dict"])
            model.to(self.device)
            model.eval()
            self.model = model
            acc = f"{self.val_accuracy * 100:.1f}%" if self.val_accuracy else "unknown"
            print(f"Loaded fabric defect model from {MODEL_PATH} (val acc {acc})")
        except Exception as exc:
            print(f"Error loading model weights: {exc}")
            self.model = None

    def _predict_probs(self, image: Image.Image) -> torch.Tensor:
        variants = [image, image.transpose(Image.FLIP_LEFT_RIGHT)]
        probs_sum = None
        for img in variants:
            tensor = self.transform(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                logits = self.model(tensor)
                probs = F.softmax(logits, dim=1)[0]
            probs_sum = probs if probs_sum is None else probs_sum + probs
        return probs_sum / len(variants)

    def _display_name(self, raw: str) -> str:
        return DISPLAY_NAMES.get(raw, raw)

    def _estimate_bbox(self, image: Image.Image) -> list:
        """Rough defect region from grayscale contrast (for UI overlay)."""
        gray = image.convert("L").resize((224, 224))
        pixels = torch.tensor(list(gray.getdata()), dtype=torch.float32).view(224, 224)
        threshold = pixels.mean() - pixels.std() * 0.35
        mask = pixels < threshold
        if not mask.any():
            return [60, 60, 180, 180]
        ys, xs = torch.where(mask)
        pad = 8
        x1 = max(0, int(xs.min()) - pad)
        y1 = max(0, int(ys.min()) - pad)
        x2 = min(223, int(xs.max()) + pad)
        y2 = min(223, int(ys.max()) + pad)
        scale_x = image.width / 224
        scale_y = image.height / 224
        return [
            int(x1 * scale_x), int(y1 * scale_y),
            int(x2 * scale_x), int(y2 * scale_y),
        ]

    def inspect(self, image: Image.Image) -> dict:
        if self.model is None:
            self.reload_model()
        if self.model is None:
            raise RuntimeError(
                "Fabric defect model not loaded. Train with train_dataset_model.py and restart the agent."
            )

        probs = self._predict_probs(image)
        pred_idx = int(probs.argmax().item())
        raw_class = self.class_names[pred_idx]
        predicted_class = self._display_name(raw_class)
        confidence = round(float(probs[pred_idx].item()), 4)

        defects = []
        if predicted_class != "defect free":
            bbox = self._estimate_bbox(image)
            defects.append({
                "type": predicted_class,
                "bbox": bbox,
                "confidence": confidence,
            })

        defect_density = len(defects)
        if defect_density > 3:
            decision = "reject roll"
        elif defect_density > 0:
            decision = "flag"
        else:
            decision = "continue"

        prob_map = {
            self._display_name(name): round(float(probs[i].item()), 4)
            for i, name in enumerate(self.class_names)
        }

        return {
            "defects": defects,
            "defect_density_per_10m": defect_density,
            "decision": decision,
            "primary_defect": predicted_class,
            "confidence": confidence,
            "class_probabilities": prob_map,
            "model_val_accuracy": self.val_accuracy,
        }
