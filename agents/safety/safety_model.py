import os
import json
import joblib
import numpy as np

class SafetyPredictor:
    def __init__(self, model_path=None, zone_map_path=None):
        base_dir = os.path.dirname(__file__)
        
        if model_path is None:
            model_path = os.path.join(base_dir, "models", "safety_risk_model.joblib")
            
        if zone_map_path is None:
            zone_map_path = os.path.join(base_dir, "zone_map.json")
            
        self.model_bundle = None
        if os.path.exists(model_path):
            try:
                self.model_bundle = joblib.load(model_path)
                print(f"[SafetyPredictor] Successfully loaded model bundle from {model_path}")
            except Exception as e:
                print(f"[SafetyPredictor] Error loading model bundle: {e}")
                
        self.zone_map = {}
        if os.path.exists(zone_map_path):
            with open(zone_map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.zone_map = data.get("zones", {})

    def is_point_in_polygon(self, x, y, polygon):
        """Ray-casting algorithm to test if point (x,y) is inside polygon."""
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def inspect_frame(self, zone_id, worker_count, helmet_present, vest_present, 
                      ear_protection_present, gloves_present, hazard_zone_intrusion,
                      confidence=0.92, ambient_noise_db=75.0, light_level_lux=450.0):
        
        zone_info = self.zone_map.get(zone_id, {
            "name": zone_id,
            "required_ppe": ["helmet", "vest"],
            "ambient_noise_limit_db": 85.0
        })
        
        # Rule-based violation checks
        violations = []
        req_ppe = zone_info.get("required_ppe", [])
        
        if "helmet" in req_ppe and not helmet_present:
            violations.append({"type": "MISSING_HELMET", "severity": "HIGH", "detail": "Worker detected without mandatory safety helmet."})
            
        if "gloves" in req_ppe and not gloves_present:
            violations.append({"type": "MISSING_GLOVES", "severity": "MEDIUM", "detail": "Chemical/Machine operator missing protective gloves."})
            
        if "ear_protection" in req_ppe and not ear_protection_present:
            if ambient_noise_db > 80.0:
                violations.append({"type": "MISSING_EAR_PROTECTION", "severity": "HIGH", "detail": f"Ear protection missing in high-noise zone ({ambient_noise_db} dB)."})
            else:
                violations.append({"type": "MISSING_EAR_PROTECTION", "severity": "LOW", "detail": "Ear protection recommended for zone."})
                
        if "vest" in req_ppe and not vest_present:
            violations.append({"type": "MISSING_VEST", "severity": "LOW", "detail": "High-visibility vest missing."})
            
        if hazard_zone_intrusion:
            violations.append({"type": "HAZARD_ZONE_INTRUSION", "severity": "CRITICAL", "detail": "Worker centroid inside active machine hazard boundary polygon."})
            
        # ML predictions if model bundle available
        predicted_violation = "NONE" if not violations else violations[0]["type"]
        predicted_risk = 0.05
        
        if self.model_bundle:
            try:
                zone_code = self.model_bundle["zone_mapping"].get(zone_id, 0)
                feat = np.array([[
                    zone_code, worker_count, int(helmet_present), int(vest_present),
                    int(ear_protection_present), int(gloves_present), int(hazard_zone_intrusion),
                    confidence, ambient_noise_db, light_level_lux
                ]])
                
                predicted_violation = self.model_bundle["classifier"].predict(feat)[0]
                predicted_risk = float(np.clip(self.model_bundle["regressor"].predict(feat)[0], 0.0, 1.0))
            except Exception as e:
                print(f"[SafetyPredictor] Inference fallback due to error: {e}")
        else:
            # Fallback risk scoring calculation
            r_score = 0.05
            if hazard_zone_intrusion: r_score += 0.50
            if not helmet_present: r_score += 0.30
            if not gloves_present: r_score += 0.20
            predicted_risk = min(1.0, r_score)

        status = "SECURE"
        if predicted_risk > 0.70 or hazard_zone_intrusion:
            status = "CRITICAL"
        elif predicted_risk > 0.35 or len(violations) > 0:
            status = "WARNING"

        return {
            "zone_id": zone_id,
            "zone_name": zone_info.get("name", zone_id),
            "camera_id": zone_info.get("camera_id", "CAM-01"),
            "status": status,
            "risk_score": round(predicted_risk, 4),
            "predicted_primary_violation": predicted_violation,
            "violations_count": len(violations),
            "violations": violations,
            "worker_count": worker_count,
            "ppe_state": {
                "helmet": bool(helmet_present),
                "vest": bool(vest_present),
                "ear_protection": bool(ear_protection_present),
                "gloves": bool(gloves_present)
            },
            "hazard_zone_intrusion": bool(hazard_zone_intrusion),
            "confidence": confidence,
            "alert_sent": status in ["WARNING", "CRITICAL"]
        }
