"""Every Makefile target must be declared .PHONY.

Why: a target whose name matches an existing directory (docs, scripts,
templates, security) is a file target to make. Since the directory exists and is
newer than nothing, make prints "'security' is up to date" and skips the recipe.
The gate looks like it passed while having run no scanner at all. In a sibling
repository `make security` was a silent no-op for this reason; the first real run
reported 9 findings at Medium or above.

This test also proves the failure is detectable: parsing is exercised against a
deliberately broken Makefile body, not only against the real one.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = REPO_ROOT / "Makefile"

# A target line: name at column 0, then ':' not followed by '='.
TARGET_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:(?!=)")
PHONY_RE = re.compile(r"^\.PHONY\s*:\s*(.*)$")

# Targets make defines itself; they are not ours to declare.
BUILTIN_TARGETS = {".PHONY", ".DEFAULT_GOAL", ".SUFFIXES", ".NOTPARALLEL"}


def parse_makefile(text: str) -> tuple[set[str], set[str]]:
    """Return (declared_phony, defined_targets)."""
    phony: set[str] = set()
    targets: set[str] = set()
    for line in text.splitlines():
        if line.startswith("\t"):
            continue  # recipe line
        phony_match = PHONY_RE.match(line)
        if phony_match:
            phony.update(phony_match.group(1).split())
            continue
        target_match = TARGET_RE.match(line)
        if target_match:
            name = target_match.group(1)
            if name not in BUILTIN_TARGETS:
                targets.add(name)
    return phony, targets


def test_makefile_exists() -> None:
    assert MAKEFILE.is_file(), "Makefile がありません。CI が素のツールを直接呼ぶ状態に戻ります。"


def test_every_target_is_phony() -> None:
    phony, targets = parse_makefile(MAKEFILE.read_text(encoding="utf-8"))
    undeclared = sorted(targets - phony)
    assert not undeclared, (
        f".PHONY 未宣言のターゲット: {', '.join(undeclared)}。"
        "同名のディレクトリが存在すると make は up to date を返してレシピを実行しません。"
    )


def test_targets_colliding_with_directories_are_phony() -> None:
    """The subset that can actually go silent, called out separately."""
    phony, targets = parse_makefile(MAKEFILE.read_text(encoding="utf-8"))
    colliding = {t for t in targets if (REPO_ROOT / t).exists()}
    assert not (colliding - phony), f"同名パスが存在し .PHONY 未宣言: {sorted(colliding - phony)}"


def test_detects_an_undeclared_target() -> None:
    """The parser must fail on a broken Makefile, not just pass on a good one."""
    broken = ".PHONY: lint\nlint:\n\ttrue\n\nsecurity:\n\ttrue\n"
    phony, targets = parse_makefile(broken)
    assert "security" in targets - phony


def test_phony_declaration_is_not_confused_by_variable_assignment() -> None:
    text = "VENV := .venv\nTEST_DIRS := scripts/tests\n.PHONY: lint\nlint:\n\ttrue\n"
    phony, targets = parse_makefile(text)
    assert targets == {"lint"}
    assert phony == {"lint"}


@pytest.mark.skipif(sys.platform == "win32", reason="make 前提")
def test_declared_targets_actually_run() -> None:
    """`make -n` must emit a recipe for a directory-colliding target.

    Proves the .PHONY declaration takes effect rather than merely being present:
    if `security` were treated as a file target, make would print
    "up to date" and no command line.
    """
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["make", "-n", "security"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert "up to date" not in result.stdout, (
        f"make security がレシピを実行しません: {result.stdout!r}"
    )
    assert "bandit" in result.stdout, f"bandit の呼び出しが出ません: {result.stdout!r}"
