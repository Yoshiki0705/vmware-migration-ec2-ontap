#!/usr/bin/env python3
"""Redact sensitive tokens from AWS console screenshots via OCR word boxes.

Why this exists: some console states are transient (a service-initialization
page disappears once the service is initialized), so they cannot be recaptured
with DOM-level redaction applied. Those images have to be redacted as pixels.

Usage:
    python3 tools/redact_screenshot.py IN.png OUT.png [--header-strip]

What it does:
  1. Runs tesseract in TSV mode to get per-word bounding boxes.
  2. Draws an opaque box over every word matching a sensitive pattern.
  3. Optionally blanks the top-right header strip, where the AWS console always
     renders the account alias and account ID. This is a belt-and-braces step:
     OCR misreads digit groups often enough that pattern matching alone is not
     a sufficient guarantee for an account ID.

Verify the result with OCR afterwards. A redaction that is not verified is a
claim, not a fact.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Tokens that must never appear in a published screenshot.
#
# Personal names and account aliases are deliberately NOT hardcoded here: this
# file is committed to a public repository, so embedding the names it is meant
# to redact would publish exactly what it exists to remove. Supply them at run
# time instead:
#
#     REDACT_EXTRA_NAMES="alice,bob" python3 tools/redact_screenshot.py ...
#
# The CI equivalent is the PROJECT_CONTEXT_NAMES secret used by
# .github/workflows/agent-output-audit.yml.
_BASE_PATTERNS = [
    r"\d{12}",  # bare AWS account id
    r"\d{4}-\d{4}-\d{4}",  # account id, console hyphenated form
    r"(?:fs|svm|subnet|vpc|rct|i|sg)-[0-9a-f]{6,}",  # environment-specific resource ids
    r"\b172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+\b",  # private IPv4, RFC1918 /12
    r"\b10\.\d+\.\d+\.\d+\b",
    r"\b192\.168\.\d+\.\d+\b",
]


def _build_pattern() -> re.Pattern[str]:
    """Compile the sensitive-token pattern, folding in run-time names.

    Names are matched as SUBSTRINGS, not on word boundaries. A resource name
    frequently embeds a person's name with no delimiter: a file system tagged
    `fsxsomebody`, derived from the owner `somebody`, is not caught by a
    `\\bsomebody\\b` pattern, and a screenshot of it then passes review. This
    over-matches deliberately. A false positive costs one extra black box; a
    false negative publishes the name.
    """
    patterns = list(_BASE_PATTERNS)
    extra = os.environ.get("REDACT_EXTRA_NAMES", "").strip()
    if extra:
        names = [re.escape(n.strip()) for n in extra.split(",") if n.strip()]
        if names:
            patterns.append(r"\S*(?:" + "|".join(names) + r")\S*")
    return re.compile("|".join(patterns), re.IGNORECASE)


SENSITIVE = _build_pattern()

BOX_FILL = (24, 24, 24)
PAD = 2


def ocr_words(path: Path) -> list[dict]:
    """Return tesseract word boxes as dicts, or [] when OCR yields nothing."""
    proc = subprocess.run(
        ["tesseract", str(path), "-", "-l", "eng+jpn", "tsv"],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"tesseract failed on {path}: {proc.stderr.strip()[:200]}")

    lines = proc.stdout.splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    out: list[dict] = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) != len(header):
            continue
        row = dict(zip(header, parts, strict=True))
        if not row.get("text", "").strip():
            continue
        out.append(row)
    return out


def redact(src: Path, dst: Path, header_strip: bool) -> dict:
    img = Image.open(src).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    boxed = 0
    for row in ocr_words(src):
        text = row["text"]
        if not SENSITIVE.search(text):
            continue
        try:
            x, y = int(row["left"]), int(row["top"])
            bw, bh = int(row["width"]), int(row["height"])
        except (KeyError, ValueError):
            continue
        draw.rectangle([x - PAD, y - PAD, x + bw + PAD, y + bh + PAD], fill=BOX_FILL)
        boxed += 1

    stripped = False
    if header_strip:
        # AWS console header: account menu sits in the top-right. Blank the right
        # 30% of the first 44px. Coordinates are in CSS pixels, matching the
        # screenshots taken with scale=css.
        draw.rectangle([int(w * 0.70), 0, w, 44], fill=BOX_FILL)
        stripped = True

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst)
    return {"words_boxed": boxed, "header_strip": stripped, "size": f"{w}x{h}"}


def verify(path: Path) -> list[str]:
    """OCR the output and return any sensitive tokens still readable."""
    proc = subprocess.run(
        ["tesseract", str(path), "-", "-l", "eng+jpn"],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    hits = sorted(set(m.group(0) for m in SENSITIVE.finditer(proc.stdout)))
    # OCR of a redacted region sometimes emits placeholder ids we injected on
    # purpose; those are not leaks.
    return [h for h in hits if "EXAMPLE" not in h.upper()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--header-strip", action="store_true")
    args = ap.parse_args()

    if not args.src.is_file():
        print(f"error: {args.src} not found", file=sys.stderr)
        return 2

    stats = redact(args.src, args.dst, args.header_strip)
    residual = verify(args.dst)
    print(
        f"{args.src.name} -> {args.dst.name}  "
        f"boxed={stats['words_boxed']} header_strip={stats['header_strip']} "
        f"size={stats['size']}"
    )
    if residual:
        print(f"  FAIL residual tokens still readable: {residual}", file=sys.stderr)
        return 1
    print("  verified: no sensitive tokens readable by OCR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
