from collections import deque
import numpy as np

class BaselineCalculator:
    def __init__(self, window_size=50):
        # Dictionary to store a rolling window of recent consumption per machine
        self.history = {}
        self.window_size = window_size

    def update_and_get_baseline(self, machine_id: str, power_kwh: float):
        """
        Updates the rolling history for the machine and returns the current baseline (mean)
        and standard deviation.
        """
        if machine_id not in self.history:
            self.history[machine_id] = deque(maxlen=self.window_size)
            
        self.history[machine_id].append(power_kwh)
        
        # Calculate mean and standard deviation
        data = list(self.history[machine_id])
        mean = np.mean(data)
        
        # Avoid division by zero if all values are same
        std = np.std(data) if len(data) > 1 else 1.0 
        
        # ensure std is not 0
        if std == 0:
            std = 1.0
            
        return float(mean), float(std)
