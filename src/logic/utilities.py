from datetime import datetime
from typing import Optional

# Utility function to normalize date inputs ------------------------------------------------
def normalize_date_for_pg(date_input: Optional[str]) -> Optional[datetime]:
    """
    Normalize input to a Python datetime or return None.
    Accepts datetime, ISO strings (with/without Z), common formats.
    """
    if not date_input:
        return None

    if isinstance(date_input, datetime):
        return date_input

    s = str(date_input).strip()

    if "." in s:
        s = s.split(".", 1)[0]

    try:
        return datetime.fromisoformat(s)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
    return None

# Utility function to normalize date strings  ------------------------------------------------
def normalize_str_date(date_str: str) -> str:
    if date_str is None or date_str == "":
        return ""
    return date_str.replace("T", " ").split(".")[0]

# Utility function to normalize expiration date strings  ------------------------------------------------
def normalize_str_expdate(date_str: str) -> str:
    if date_str is None or date_str == "" or date_str.startswith("2222-01-01"):
        return ""
    return normalize_str_date(date_str)

