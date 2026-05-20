import unicodedata

def clean_parameter_string(text: str) -> str:
    """Standardizes strings by removing accents and lowercasing."""
    if not text: return ""
    text = unicodedata.normalize('NFKD', text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    return text.lower().strip()

def clean_sapo_text(text: str) -> str:
    """Neutral utility to strip excess whitespace/newlines."""
    return " ".join(text.split())