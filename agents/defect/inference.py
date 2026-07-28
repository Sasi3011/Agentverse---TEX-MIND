import os
import random
from PIL import Image

class DefectDetector:
    def __init__(self, model_path: str, conf_threshold: float = 0.5):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.device = 'cpu'
        print(f"Loaded Mock Defect Detection model from {model_path} on {self.device}")
        
        self.classes = ['hole', 'weft-crack', 'oil-stain', 'color-bleed']

    def inspect(self, image: Image.Image):
        """
        Run inference on a given PIL Image.
        Returns a list of detected defects.
        """
        # Convert PIL to cv2 for processing if needed
        # img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Real inference code:
        # results = self.model.predict(image, conf=self.conf_threshold)
        # defects = []
        # for r in results:
        #     for box in r.boxes:
        #         defects.append({
        #             "type": self.model.names[int(box.cls)],
        #             "confidence": float(box.conf),
        #             "bbox": [float(x) for x in box.xyxy[0]]
        #         })
        
        # Mock inference for hackathon/demo purposes:
        import random
        defects = []
        
        # Randomly decide if there's a defect (e.g., 30% chance)
        if random.random() < 0.3:
            num_defects = random.randint(1, 2)
            width, height = image.size
            for _ in range(num_defects):
                x1 = random.uniform(0, width * 0.8)
                y1 = random.uniform(0, height * 0.8)
                x2 = x1 + random.uniform(10, 50)
                y2 = y1 + random.uniform(10, 50)
                
                defects.append({
                    "type": random.choice(self.classes),
                    "confidence": round(random.uniform(self.conf_threshold, 0.99), 2),
                    "bbox": [round(x1), round(y1), round(x2), round(y2)]
                })
                
        return defects
