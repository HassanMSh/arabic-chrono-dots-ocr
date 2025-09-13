from typing import List, Dict, Any
import re
from app.utils import normalize_date

# Regex to detect date formats like "١٩٤٩/٨/١" or Western "1949/08/01"
DATE_PATTERN = re.compile(r"\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}")

def is_date_block(block: Dict[str, Any]) -> bool:
    """
    Check if a block is likely a date.
    """
    text = block.get("text", "").strip()
    return bool(DATE_PATTERN.search(text))


def aggregate_blocks(ocr_output: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Aggregate OCR blocks into {date, text}.
    Rules:
      - Each date starts a new event.
      - Text collected until next date.
      - No carryover between events.
    """
    events = []
    current_date = None
    buffer: List[str] = []

    def flush():
        nonlocal buffer, current_date
        if current_date and buffer:
            events.append({
                "date": normalize_date(current_date),   # <-- normalize here
                "text": "\n".join(buffer).strip()
            })
            buffer = []

    for block in ocr_output:
        if is_date_block(block):
            flush()
            current_date = block["text"].strip()
        else:
            if block["category"] == "Text":
                buffer.append(block["text"].strip())

    flush()
    return events