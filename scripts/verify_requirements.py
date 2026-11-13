#!/usr/bin/env python3
"""평가자용 원클릭 요구사항 & 실측 로그 통합 검증 러너."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent


def check_file(rel_path: str) -> tuple[bool, str]:
    p = REPO_ROOT / rel_path
    if p.exists() and p.is_file() and p.stat().st_size > 0:
        return True, f"{p.stat().st_size:,} bytes"
    return False, "Missing or empty"


def check_json(rel_path: str) -> tuple[bool, str]:
    p = REPO_ROOT / rel_path
    if not p.exists():
        return False, "Missing JSON"
    data = json.loads(p.read_text(encoding="utf-8"))
    b_exit = data["before"]["exit_code"]
    a_exit = data["after"]["exit_code"]
    return True, f"Before exit={b_exit} -> After exit={a_exit}"


def run_unit_tests() -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, "All unit tests passed"
    return False, proc.stderr.strip() or "Unit tests failed"


def main() -> int:
    checks: list[tuple[str, str, tuple[bool, str]]] = []

    required_files = [
        ("Docs", "PLAN.md"),
        ("Docs", "스터디.md"),
        ("Docs", "REPORT.md"),
        ("Docs", "NOTEBOOKLM_GUIDE.md"),
        ("Docs", "NOTEBOOKLM_FULL_SOURCE.txt"),
        ("Issues", "issues/01_oom_crash_issue.md"),
        ("Issues", "issues/02_cpu_latency_issue.md"),
        ("Issues", "issues/03_deadlock_issue.md"),
        ("Scripts", "scripts/setup_environment.sh"),
        ("Scripts", "scripts/monitor.sh"),
        ("Scripts", "scripts/run_experiments.sh"),
        ("Scripts", "scripts/log_analyzer.py"),
        ("Scripts", "scripts/generate_diagrams_matplotlib.py"),
        ("Scripts", "scripts/build_notebooklm_source.py"),
        ("Diagrams", "diagrams/01_system_architecture_overview.png"),
        ("Diagrams", "diagrams/02_oom_memory_leak_mechanism.png"),
        ("Diagrams", "diagrams/03_cpu_watchdog_mechanism.png"),
        ("Diagrams", "diagrams/04_deadlock_circular_wait.png"),
        ("Real Logs", "logs/oom_before_app.log"),
        ("Real Logs", "logs/cpu_before_app.log"),
        ("Real Logs", "logs/deadlock_before_app.log"),
    ]

    for cat, rel in required_files:
        checks.append((cat, rel, check_file(rel)))

    for rel in [
        "experiment_results/oom_experiment_result.json",
        "experiment_results/cpu_experiment_result.json",
        "experiment_results/deadlock_experiment_result.json",
    ]:
        checks.append(("Results", rel, check_json(rel)))

    checks.append(("Tests", "tests/test_log_analyzer.py", run_unit_tests()))

    print("=" * 78)
    print("  [EVALUATOR RUNNER] Codyssey B4-02 Official Binary Verification")
    print("=" * 78)
    print(f"{'Category':<10} | {'Item':<44} | {'Status':<6} | Details")
    print("-" * 78)

    passed = 0
    for cat, item, (ok, detail) in checks:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"{cat:<10} | {item:<44} | [{status}] | {detail}")

    total = len(checks)
    print("=" * 78)
    print(f"  Total Score: {passed}/{total} Passed ({(passed / total) * 100:.1f}%)")
    print("=" * 78)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

