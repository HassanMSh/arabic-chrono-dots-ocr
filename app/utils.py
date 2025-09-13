# app/utils.py

ARABIC_DIGITS = {
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"
}

def normalize_digits(s: str) -> str:
    return "".join(ARABIC_DIGITS.get(ch, ch) for ch in s)

def normalize_date(date_str: str) -> str:
    """
    Convert Arabic/Western mixed OCR dates into normalized YYYY/MM/DD.
    Example: "١٩٤٩/٨/١٧" -> "1949/08/17"
    """
    import re
    ascii_str = normalize_digits(date_str)

    # split into parts (year, month, day)
    parts = re.split(r"[^\d]+", ascii_str)
    parts = [p for p in parts if p]

    if len(parts) == 3:
        year, month, day = parts
        return f"{int(year):04d}/{int(month):02d}/{int(day):02d}"
    return ascii_str
