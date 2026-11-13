#!/usr/bin/env python3
"""핵심 구현 스크립트 파일들을 단일 텍스트(NOTEBOOKLM_FULL_SOURCE.txt)로 통합하는 빌더."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = REPO_ROOT / "NOTEBOOKLM_FULL_SOURCE.txt"

SOURCE_FILES = [
    "scripts/setup_environment.sh",
    "scripts/monitor.sh",
    "scripts/run_experiments.sh",
    "scripts/log_analyzer.py",
    "scripts/generate_diagrams_matplotlib.py",
    "scripts/verify_requirements.py",
]


def build_source_bundle() -> Path:
    """지정된 핵심 소스 파일들을 하나의 텍스트 파일로 병합해 저장합니다."""
    sections: list[str] = []
    for rel_path in SOURCE_FILES:
        file_path = REPO_ROOT / rel_path
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        header = f"{'=' * 72}\nFILE: {rel_path}\n{'=' * 72}\n"
        sections.append(header + content.rstrip() + "\n")

    OUTPUT_FILE.write_text("\n".join(sections), encoding="utf-8")
    return OUTPUT_FILE


if __name__ == "__main__":
    out = build_source_bundle()
    print(f"Built {out} ({out.stat().st_size} bytes)")

