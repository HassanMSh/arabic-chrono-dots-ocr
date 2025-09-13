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

    async with httpx.AsyncClient(timeout=120.0) as client:
        page_idx = from_page - 1
        for page in pdf_to_pages(str(pdf_path), dpi=dpi, from_page=from_page, to_page=to_page):
            page_idx += 1
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

                # Tag blocks with page number for traceability
                for b in half_blocks:
                    b["page"] = page_idx

                page_blocks.extend(half_blocks)
                print(f"[EXTRACT]  -> half {side_idx} done, {len(half_blocks)} blocks")

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

async def process_pdf(pdf_path: str, dpi: int = 300, from_page: int = 1, to_page: int | None = None):
    """
    Full ETL: Extract → Transform → Load
    Treats whole range as one continuous stream.
    """
    clear_previous_results(str(pdf_path))
    all_blocks = await extract_pdf(pdf_path, dpi=dpi, from_page=from_page, to_page=to_page)
    transform_and_load(pdf_path, all_blocks)
