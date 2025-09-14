import httpx
import asyncio
import io
import json
from pathlib import Path
from typing import List, Dict, Any

from PIL import Image
from app.pdf_utils import pdf_to_pages, slice_page
from app.db import insert_raw_result, insert_event, clear_previous_results
from app.aggregator import aggregate_blocks

OCR_SERVER = "http://localhost:8000/infer"
CHECKPOINT_DIR = Path("data/checkpoints")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------
# Extract stage
# --------------------

async def extract_pdf(pdf_path: str, dpi: int = 300, from_page: int = 1, to_page: int | None = None) -> List[Dict[str, Any]]:
    """
    Run OCR on a PDF range.
    Returns a single list of blocks across all pages (merged).
    """
    pdf_path = Path(pdf_path)
    all_blocks: List[Dict[str, Any]] = []
    
    # Track already processed pages
    processed_pages = {
        int(f.stem.split("_page")[-1])
        for f in CHECKPOINT_DIR.glob(f"{pdf_path.stem}_page*.json")
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        page_idx = from_page - 1
        for page in pdf_to_pages(str(pdf_path), dpi=dpi, from_page=from_page, to_page=to_page):
            page_idx += 1
            
            checkpoint_file = CHECKPOINT_DIR / f"{pdf_path.stem}_page{page_idx}.json"
            if page_idx in processed_pages:
                print(f"[EXTRACT] Skipping page {page_idx}, already checkpointed")
                page_blocks = json.loads(checkpoint_file.read_text(encoding="utf-8"))
                all_blocks.extend(page_blocks)
                continue
            
            print(f"[EXTRACT] Processing page {page_idx} ...")

            halves = list(slice_page(page, order="right_first"))
            page_blocks: List[Dict[str, Any]] = []

            for side_idx, half in enumerate(halves, start=1):
                buf = io.BytesIO()
                half.save(buf, format="PNG")
                buf.seek(0)

                files = {"file": (f"page{page_idx}_half{side_idx}.png", buf, "image/png")}
                resp = await client.post(OCR_SERVER, files=files)
                resp.raise_for_status()
                half_blocks = resp.json()
                
                if isinstance(half_blocks, dict) and "raw_output" in half_blocks:
                    try:
                        half_blocks = json.loads(half_blocks["raw_output"])
                    except json.JSONDecodeError:
                        print(f"[WARN] Could not decode raw_output on page {page_idx}")
                        half_blocks = []

                # Tag blocks with page number for traceability
                for b in half_blocks:
                    b["page"] = page_idx
                    if b.get("category") == "List-item":
                        b["category"] = "Text"
                page_blocks.extend(half_blocks)
                print(f"[EXTRACT]  -> half {side_idx} done, {len(half_blocks)} blocks")
            # Save per-page JSON checkpoint after both halves
            checkpoint_file.write_text(json.dumps(page_blocks, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[CHECKPOINT] Saved {checkpoint_file}")

            # Append page’s blocks into global book stream
            all_blocks.extend(page_blocks)
            print(f"[EXTRACT] ✅ Page {page_idx} done, total {len(page_blocks)} blocks")

    # Save one merged JSON row for the whole range
    insert_raw_result(str(pdf_path), -1, json.dumps(all_blocks, ensure_ascii=False))

    return all_blocks


# --------------------
# Transform + Load stage
# --------------------

def transform_and_load(pdf_path: str, all_blocks: List[Dict[str, Any]]):
    """
    Transform OCR blocks into structured events and insert into DB.
    """
    events = aggregate_blocks(all_blocks)

    for e in events:
        insert_event(
            e["date"],
            e["text"],
            source_pdf=str(pdf_path),
            slice_idx=-1,  # -1 = merged book-level
        )

    print(f"[TRANSFORM+LOAD] Inserted {len(events)} events into DB")


# --------------------
# Full pipeline
# --------------------

def load_checkpoints(pdf_path: str, resume_safe: bool = True) -> List[Dict[str, Any]]:
    pdf_path = Path(pdf_path)
    files = sorted(CHECKPOINT_DIR.glob(f"{pdf_path.stem}_page*.json"))
    if not files:
        return []

    if resume_safe:
        # Drop last checkpoint to force re-OCR of that page
        last = files[-1]
        print(f"[RESUME] Removing last checkpoint {last} to reprocess safely")
        last.unlink(missing_ok=True)
        files = files[:-1]

    blocks = []
    for f in files:
        blocks.extend(json.loads(f.read_text(encoding="utf-8")))
    return blocks

async def process_pdf(pdf_path: str, dpi: int = 300, from_page: int = 1, to_page: int | None = None):
    """
    Full ETL: Extract → Transform → Load
    Supports checkpoint resume.
    """
    # Load existing checkpoints first (drops last one for safety)
    all_blocks = load_checkpoints(pdf_path, resume_safe=True)

    # Figure out where to resume
    checkpoint_files = sorted(CHECKPOINT_DIR.glob(f"{Path(pdf_path).stem}_page*.json"))
    if checkpoint_files:
        last_done_page = int(checkpoint_files[-1].stem.split("_page")[-1])
        resume_from_page = last_done_page + 1
    else:
        resume_from_page = from_page

    if not all_blocks:  # nothing checkpointed yet → fresh OCR
        clear_previous_results(str(pdf_path))
        all_blocks = await extract_pdf(pdf_path, dpi=dpi, from_page=from_page, to_page=to_page)
    else:
        print(f"[RESUME] Loaded {len(all_blocks)} blocks from checkpoints")
        print(f"[RESUME] Resuming OCR from page {resume_from_page}")
        new_blocks = await extract_pdf(pdf_path, dpi=dpi, from_page=resume_from_page, to_page=to_page)
        all_blocks.extend(new_blocks)

    transform_and_load(pdf_path, all_blocks)
