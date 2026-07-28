import os
import sys

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model import train_dyeing_model

if __name__ == "__main__":
    print("Starting Agent 3 ML Model Training on 1,000,000 Dataset...")
    success = train_dyeing_model()
    if success:
        print("Agent 3 Training Completed Successfully.")
    else:
        print("Training Failed.")
