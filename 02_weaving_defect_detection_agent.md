# Agent 2 — Weaving Defect Detection Agent

## 1. Role in the System
Runs right after intake. Inspects the fabric coming off the loom, in real time, using computer vision — replacing (or augmenting) a manual visual inspector walking the line.

## 2. Real-World Problem It Solves
Manual inspection catches maybe 60–70% of defects and only after meters of fabric have already been woven wrong. This agent inspects continuously and flags a defect within seconds of it appearing, cutting wasted fabric.

## 3. What You Need to Provide
| Item | Why it's needed | Example |
|---|---|---|
| Camera feed or image samples | The actual thing being inspected | RTSP stream from a line camera, or a folder of captured frames |
| Labeled defect dataset (or use public one) | To fine-tune the detection model | Public: "Fabric Defect Dataset" (Kaggle/Roboflow) — or your own labeled images if available |
| Defect taxonomy | What counts as what | e.g. hole, weft-crack, oil-stain, color-bleed — your QC team's actual defect categories |
| Acceptable defect density threshold | To decide "flag vs auto-reject roll" | e.g. >3 defects per 10m → reject the roll |

## 4. Input / Output Contract
**Input:** image (JPEG/PNG) or video frame, batch_id, roll position (meters).
```json
{
  "batch_id": "B-2026-0001",
  "roll_position_m": 42.5,
  "image_ref": "s3://texverse/frames/b1/042.jpg"
}
```
**Output:**
```json
{
  "batch_id": "B-2026-0001",
  "roll_position_m": 42.5,
  "defects": [
    {"type": "hole", "bbox": [120, 88, 160, 130], "confidence": 0.94}
  ],
  "defect_density_per_10m": 1,
  "decision": "continue"
}
```

## 5. Internal Working — Step by Step
1. Receive frame → preprocess (resize, normalize).
2. Run object-detection model → get bounding boxes + class + confidence.
3. Filter detections below confidence threshold (avoid noisy false positives).
4. Aggregate detections over a rolling window (per 10m of fabric) → compute defect density.
5. Compare density against threshold → decide `continue` / `flag` / `reject roll`.
6. Write to shared state and push an annotated image (with bounding boxes drawn) to the dashboard for human review.

## 6. Model / Algorithm Details
- **Model:** YOLOv8n (nano) fine-tuned on a fabric-defect dataset — small enough to run fast on modest hardware, good enough for a hackathon-to-pilot jump.
- **Training approach:** transfer learning from COCO-pretrained YOLOv8, fine-tune on ~500–1000 labeled fabric images for a handful of epochs.
- **Fallback if no time to train:** run a pretrained anomaly-detection approach (e.g. autoencoder reconstruction error) that flags "this patch looks different from normal fabric" without needing labeled defects at all.

## 7. Tech Stack
- Python, FastAPI
- Ultralytics YOLOv8, OpenCV, Pillow
- Torch (CPU inference is fine for a demo; GPU recommended for real production throughput)
- S3-compatible object storage for frame archive (or local disk for demo)

## 8. Standalone API Contract
```
POST /agents/defect/inspect      (multipart image or image_ref)
GET  /agents/defect/health
GET  /agents/defect/model-info   -> {"model": "yolov8n-fabric", "version": "0.3", "map50": 0.81}
```

## 9. Standalone Deployment
```
agents/defect/
├── main.py
├── inference.py
├── train.py             # fine-tuning script, run offline not at request time
├── Dockerfile
├── requirements.txt
└── weights/best.pt
```
GPU deployment note: use `nvidia/cuda` base image if deploying with GPU inference; CPU-only base image is fine for lower-throughput pilots.

## 10. How the Master Brain Calls It
Orchestrator streams frames (or polls a frame queue) to this agent as fabric moves. This can run **asynchronously/in parallel** with Agent 1 once a batch has passed intake — it doesn't need to block other agents, but its output does feed into Agent 3 (dyeing) since a batch with excessive early defects may be rejected before dyeing even starts.

## 11. Production Hardening
- Confidence thresholding tuned against a validation set — don't hardcode 0.5 blindly, tune for your precision/recall tradeoff (missed defects are worse than false alarms, usually).
- Frame-drop handling: if the inference queue backs up, drop frames rather than crash — log dropped-frame count.
- Model rollback plan: keep the last known-good weights file, auto-fallback if a new deployed model's live precision drops below a floor.
- Human-in-the-loop review queue for low-confidence detections (0.4–0.7 range) rather than auto-deciding.

## 12. Testing Strategy
- Held-out labeled test set — report precision/recall/mAP per defect class.
- Load test: sustained frame throughput at target FPS.
- Adversarial test: feed frames with lighting variation, motion blur — confirm graceful degradation, not crashes.

## 13. Monitoring & Observability
- Track: inference latency (p50/p95), defect rate over time per machine/loom, model confidence distribution drift.
- Alert on sustained high defect rate on a specific loom (points to a mechanical fault, not a fabric problem).

## 14. Environment Variables
```
MODEL_WEIGHTS_PATH=/app/weights/best.pt
CONFIDENCE_THRESHOLD=0.6
DEFECT_DENSITY_LIMIT_PER_10M=3
FRAME_QUEUE_MAX=200
DEVICE=cuda   # or cpu
```
