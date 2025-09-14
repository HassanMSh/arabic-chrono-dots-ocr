from fastapi import FastAPI
# from model.dots_ocr_4b import ocr_app
from app.ui import ui as ui_app  # make sure in ui.py you named it `ui = FastAPI()`

# This is the FastAPI instance uvicorn will look for
app = FastAPI()

# # # Mount the OCR API at /api
# app.mount("/api", ocr_app)

# Mount the UI at /
app.mount("/", ui_app)

# Optional: simple healthcheck
@app.get("/health")
async def health():
    return {"status": "ok"}
