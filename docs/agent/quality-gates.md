# Quality gates

Every gate is a `make` target. CI calls those targets rather than invoking tools
directly, and the path lists live in Makefile variables, so a local run and a CI
run inspect the same tree with the same tool version.

```bash
make install    # .venv を作り requirements*.txt を固定版で導入
make tools      # 各ツールの解決先とバージョン（ローカルと CI の差を見る）
make ci         # lint format-check test cfn-lint security drift
make drift      # 設定の到達性 + 常時ロードコンテキスト予算
```

## Gate inventory

| Target | Tool | Scope variable |
|---|---|---|
| `lint`, `format-check` | ruff | `PY_PATHS` |
| `test` | pytest | `TEST_DIRS` |
| `cfn-lint` | cfn-lint | `TEMPLATE_GLOB` |
| `security` | bandit (`-ll`, Medium 以上) | `PY_PATHS` |
| `headings` | `tools/check_heading_style.py` (selftest, then scan) | `HEADING_CHECK`; walk scope is the script's `SKIP` set |
| `shellcheck` | shellcheck | `SHELL_PATHS` |
| `agent-config` | global `validate_agent_config.py` | steering / skills / hooks |
| `context-budget` | `scripts/check_agent_context_budget.py` | AGENTS.md, `.kiro/steering/` |

`shellcheck` is not part of `ci` because it is a system binary rather than a
pinned Python package; CI runs it as a separate job.

## Tool versions

`requirements.txt` holds what the scripts need at runtime. `requirements-dev.txt`
holds what the gates need. Both are exact-pinned. Widening either to a range
reintroduces the divergence described below.

## Pitfalls measured in this repository

| Pitfall | Root cause | Resolution |
|---|---|---|
| A `make` target named after an existing directory silently no-ops | make treats it as an up-to-date file target | All targets declared `.PHONY`; `scripts/tests/test_makefile_phony.py` fails the build on a new undeclared target and asserts `make -n security` emits a `bandit` line |
| CI reported a passing test gate with no tests | `pytest tests/ -v \|\| true` against a `tests/` directory that did not exist | `TEST_DIRS = scripts/tests`, no `\|\| true`; the directory now exists and is the only place tests live |
| Local and CI could disagree on lint results | CI ran `pip install ruff cfn-lint` unpinned while `requirements.txt` pinned `cfn-lint==1.52.0`; `ruff` was pinned nowhere | Both pinned in `requirements-dev.txt`; CI calls `make` targets |
| `.pre-commit-config.yaml` describes hooks that never ran | `pre-commit` is not installed locally; `core.hooksPath` points at `.githooks`, so only `.githooks/pre-commit` executes | Documented here. `.githooks/pre-commit` is the gate that actually runs locally |
| A new Python directory escaping lint | `PY_PATHS` named only `scripts`, so `tools/` would have been unlinted and unscanned | `PY_PATHS = scripts tools`; adding a Python directory means adding it here |
| A local virtualenv on a different Python than CI | `.venv` was created with Python 3.14; CI pins 3.12 | Unresolved — recreate `.venv` on 3.12 with `make install` if a version-sensitive failure appears |

## Guard outcomes

Both guards distinguish three outcomes so a warning cannot be mistaken for a
pass:

| Outcome | `check_agent_context_budget.py` | Global irreversible-operations hook |
|---|---|---|
| block | exit 1: over the hard cap, an index target missing, or untracked | `command` action, exit 2 |
| ask | exit 0 with `warning:` lines: past the warn threshold | exit 2 with an approval instruction |
| allow | exit 0, silent | exit 0, silent |

A guard that has never been observed rejecting bad input is not known to work.
`scripts/tests/` exercises the rejection paths, not only the healthy ones.
