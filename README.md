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
pip install torch transformers accelerate bitsandbytes peft sentencepiece # around 5GB
python -m scripts.download_model # around 2.2GB
```

## Run the Inference Model API and OCR Events Browser

```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## Run the model alone

```
uvicorn model.dots_ocr_4b:ocr_app --host 0.0.0.0 --port 8000
```