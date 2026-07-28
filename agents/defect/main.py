from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import List, Optional
import io
from PIL import Image
from inference import DefectDetector

app = FastAPI(title="Weaving Defect Detection Agent")

# Allow CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize detector
# For demo purposes, we pass a dummy path.
detector = DefectDetector(model_path="weights/best.pt", conf_threshold=0.6)

class InspectResponse(BaseModel):
    batch_id: str
    roll_position_m: float
    defects: List[dict]
    defect_density_per_10m: int
    decision: str

@app.get("/agents/defect/health")
def health_check():
    return {"status": "ok", "model_version": "0.3"}

@app.get("/agents/defect/model-info")
def model_info():
    return {
        "model": "yolov8n-fabric",
        "version": "0.3",
        "map50": 0.81,
        "classes": detector.classes
    }

@app.post("/agents/defect/inspect", response_model=InspectResponse)
async def inspect_fabric(
    batch_id: str = Form(...),
    roll_position_m: float = Form(...),
    file: UploadFile = File(...)
):
    # Read uploaded image
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    
    # Run inference
    defects = detector.inspect(image)
    
    # Calculate defect density (simplified logic for demo)
    # In reality, this would aggregate over a rolling 10m window
    defect_density = len(defects)
    
    # Decision logic
    # e.g., >3 defects per 10m -> reject roll
    if defect_density > 3:
        decision = "reject roll"
    elif defect_density > 0:
        decision = "flag"
    else:
        decision = "continue"
        
    return InspectResponse(
        batch_id=batch_id,
        roll_position_m=roll_position_m,
        defects=defects,
        defect_density_per_10m=defect_density,
        decision=decision
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
