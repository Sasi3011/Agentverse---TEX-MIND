import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model import train_dyeing_model

if __name__ == "__main__":
    print("Training Agent 03 Random Forest on historical dyeing records...")
    success = train_dyeing_model(sample_size=120_000)
    if success:
        print("Agent 03 model training completed.")
    else:
        print("Agent 03 model training failed.")
        sys.exit(1)
