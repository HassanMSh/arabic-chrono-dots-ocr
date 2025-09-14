from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from PIL import Image
import torch
from transformers import AutoModelForCausalLM, AutoProcessor
from qwen_vl_utils import process_vision_info
import io, json
from pathlib import Path
from huggingface_hub import snapshot_download

# Fixed default prompt (same as in your script)
DEFAULT_PROMPT = """\
Please output the layout information from the image, including each layout element's bbox, its category, and the corresponding text content within the bbox.
1. Bbox format: [x1, y1, x2, y2]
2. Layout Categories: The possible categories are ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].
3. Text Extraction & Formatting Rules:
- Picture: For the 'Picture' category, the text field should be omitted.
- Formula: Format its text as LaTeX.
- Table: Format its text as HTML.
- All Others (Text, Title, etc.): Format their text as Markdown.
4. Constraints:
- The output text must be the original text from the image, with no translation.
- All layout elements must be sorted according to human reading order.
5. Final Output: The entire output must be a single JSON object.\
"""

MODEL_ID = "helizac/dots.ocr-4bit"

# Load model once at startup
local_model_path = snapshot_download(repo_id=MODEL_ID)

model = AutoModelForCausalLM.from_pretrained(
    local_model_path,
    device_map="auto",
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2"
)
processor = AutoProcessor.from_pretrained(local_model_path, trust_remote_code=True, use_fast=True)

ocr_app = FastAPI()

@ocr_app.post("/infer")
async def infer(file: UploadFile, prompt: str = Form(DEFAULT_PROMPT)):
    """
    Inference endpoint: takes an image, runs OCR model,
    returns JSON layout result.
    """
    # Load image
    image = Image.open(io.BytesIO(await file.read()))

    # Build messages
    messages = [
        {"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": prompt}
        ]}
    ]

    # Preprocess
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, _ = process_vision_info(messages)

    inputs = processor(
        text=[text],
        images=image_inputs,
        padding=True,
        return_tensors="pt"
    ).to(model.device)

    # Run generation
    generated_ids = model.generate(
        **inputs,
        max_new_tokens=4096,
        do_sample=False,
        temperature=0.0,
        repetition_penalty=1.0
    )

    # Decode only new tokens
    generated_ids_trimmed = [
        out_ids[len(in_ids):]
        for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )[0]

    return output_text
