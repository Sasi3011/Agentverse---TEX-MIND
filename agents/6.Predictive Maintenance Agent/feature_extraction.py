import numpy as np
from collections import deque

class SignalFeatureExtractor:
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.buffers = {}

    def extract_features(self, machine_id: str, vibration_rms: float, temperature_c: float, operating_hours: float):
        if machine_id not in self.buffers:
            self.buffers[machine_id] = {
                "vibration": deque(maxlen=self.window_size),
                "temperature": deque(maxlen=self.window_size)
            }
        
        buf = self.buffers[machine_id]
        buf["vibration"].append(vibration_rms)
        buf["temperature"].append(temperature_c)
        
        vib_list = list(buf["vibration"])
        temp_list = list(buf["temperature"])
        
        # Calculate kurtosis approximation & peak ratios
        mean_vib = float(np.mean(vib_list))
        std_vib = float(np.std(vib_list)) if len(vib_list) > 1 else 0.05
        if std_vib == 0:
            std_vib = 0.05
            
        kurtosis = float(np.mean([(x - mean_vib)**4 for x in vib_list]) / (std_vib**4)) if std_vib > 0 else 3.0
        kurtosis = max(2.5, min(kurtosis, 15.0))
        
        avg_temp = float(np.mean(temp_list))
        
        return {
            "vibration_rms": vibration_rms,
            "vibration_kurtosis": round(kurtosis, 4),
            "temperature_c": round(avg_temp, 2),
            "operating_hours": operating_hours
        }
