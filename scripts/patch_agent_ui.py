#!/usr/bin/env python3
"""Strip duplicated neo-brutalist CSS blocks and link shared agent UI assets."""
import re
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
AGENT_FILES = sorted(
    f for f in UI_DIR.glob("*.html")
    if f.name[0].isdigit() or f.name.startswith("0.")
)

SHARED_LINKS = (
    '  <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Space+Mono:wght@400;700&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">\n'
    '  <link rel="stylesheet" href="agent-shared.css">\n'
    '  <script src="agent-embed.js"></script>\n'
)

NEO_PATTERN = re.compile(
    r"\n\s*/\* NEO-BRUTALIST GLOBAL OVERRIDES \*/.*?(?=\n\s*</style>)",
    re.DOTALL,
)


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    text = NEO_PATTERN.sub("", text)

    if 'href="agent-shared.css"' not in text:
        if "</head>" in text:
            text = text.replace("</head>", SHARED_LINKS + "</head>", 1)
        else:
            return False

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    for path in AGENT_FILES:
        if patch_file(path):
            print(f"patched: {path.name}")
            changed += 1
        else:
            print(f"skipped: {path.name}")
    print(f"done — {changed} file(s) updated")


if __name__ == "__main__":
    main()
