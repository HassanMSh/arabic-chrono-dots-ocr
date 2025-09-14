# Arabic Chrono OCR

## Setup the env

```bash
python3.12 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## Setup the model

```bash
# Install the custom code and dependencies
pip install -r requirements.txt # around 5GB
pip install flash-attn==2.8.3 --no-build-isolation
python -m scripts.download_model # around 2.2GB
```

## Run the Inference Model API and OCR Events Browser

- Uncomment the model then run:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## Run the model alone and to ETL with inference

```bash
uvicorn model.dots_ocr_4b:ocr_app --host 0.0.0.0 --port 8000
```
```bash
python -m scripts.run_etl
```

## Info

- Each image takes around 1 min to complete on an RTX3060 12GB VRAM.