import asyncio
from app.etl_pipeline import process_pdf

if __name__ == "__main__":
    pdf_path = "data/input_pdfs/attacks.pdf"
    # Adjust these as needed
    FROM_PAGE = 11
    TO_PAGE = 13   # or set to an integer, e.g., 20

    asyncio.run(process_pdf(pdf_path, dpi=300, from_page=FROM_PAGE, to_page=TO_PAGE))