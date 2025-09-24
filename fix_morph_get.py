import re
from pathlib import Path

FILE = Path("grc_macronizer/class_macronizer.py")

def fix_morph_get(code: str) -> str:
    """
    Rewrite all membership checks on morph.get() into the safe form
    using (morph.get(...) or "").
    """
    pattern = re.compile(r'in\s+morph\.get\(([^)]+)\)')
    return pattern.sub(r'in (morph.get(\1) or "")', code)

def main():
    code = FILE.read_text(encoding="utf-8")
    fixed = fix_morph_get(code)
    FILE.write_text(fixed, encoding="utf-8")
    print(f"Updated {FILE}")

if __name__ == "__main__":
    main()