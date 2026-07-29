from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import io
import uvicorn
from PIL import Image
from inference import DefectDetector

app = FastAPI(
    title="Agent 2 — Weaving Defect Detection Agent",
    description="Inspects continuous fabric coming off looms in real time using ResNet18 CNN trained on local Fabric Defect Dataset (defect free, hole, horizontal, lines, stain, Vertical) and 1,000,000 telemetry records.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = DefectDetector()

class InspectResponse(BaseModel):
    batch_id: str
    roll_position_m: float
    defects: List[dict]
    defect_density_per_10m: int
    decision: str
    primary_defect: str
    confidence: float

@app.get("/agents/defect/health")
def health_check():
    return {
        "status": "ok",
        "agent": "Agent 2 — Weaving Defect Detection",
        "model_version": "2.0",
        "model_loaded": detector.model is not None,
        "classes": detector.class_names,
        "dataset_telemetry_records": 1000000
    }

@app.get("/agents/defect/model-info")
def model_info():
    return {
        "model": "ResNet18-Fabric",
        "version": "2.0",
        "classes": detector.class_names
    }

@app.post("/agents/defect/inspect", response_model=InspectResponse)
async def inspect_fabric(
    batch_id: str = Form(...),
    roll_position_m: float = Form(...),
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")

    try:
        res = detector.inspect(image)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return InspectResponse(
        batch_id=batch_id,
        roll_position_m=roll_position_m,
        defects=res["defects"],
        defect_density_per_10m=res["defect_density_per_10m"],
        decision=res["decision"],
        primary_defect=res["primary_defect"],
        confidence=res["confidence"]
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
