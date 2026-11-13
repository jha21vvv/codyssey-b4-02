#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
[1차]: Google NotebookLM 업로드용 소스 및 핵심 리포트 통합 텍스트 빌더
[2차]: 흩어져 있는 소스 코드와 진료 일지들을 한 권의 두꺼운 오디오북 대본으로 묶어주는 제본기 스크립트
==============================================================================
"""

import os
import sys

# Windows 콘솔 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_file = os.path.join(base_dir, "NOTEBOOKLM_FULL_SOURCE.txt")

    # 통합할 대상 파일 목록 (순수 핵심 소스 및 주요 가이드)
    target_files = [
        "src/agent_leak_app.py",
        "scripts/setup_environment.sh",
        "scripts/run_oom_experiment.sh",
        "scripts/run_cpu_experiment.sh",
        "scripts/run_deadlock_experiment.sh",
        "scripts/verify_requirements.py",
        "ENVIRONMENT_SETUP_GUIDE.md",
        "issues/01_oom_crash_issue.md",
        "issues/02_cpu_latency_issue.md",
        "issues/03_deadlock_issue.md",
    ]

    print("==================================================")
    print("Building NOTEBOOKLM_FULL_SOURCE.txt...")
    print("==================================================")

    total_lines = 0
    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write("=" * 80 + "\n")
        outfile.write("  CODYSSEY B4-02: SYSTEM TROUBLESHOOTING & ARCHITECTURE FULL CONSOLIDATION\n")
        outfile.write("  Integrated Source Code, Scripts, Guides, and Issue Reports for NotebookLM\n")
        outfile.write("=" * 80 + "\n\n")

        for rel_path in target_files:
            abs_path = os.path.join(base_dir, rel_path)
            if os.path.isfile(abs_path):
                print(f"  -> Consolidating: {rel_path}")
                outfile.write("\n" + "#" * 80 + "\n")
                outfile.write(f"### FILE: {rel_path}\n")
                outfile.write("#" * 80 + "\n\n")

                with open(abs_path, "r", encoding="utf-8", errors="replace") as infile:
                    lines = infile.readlines()
                    total_lines += len(lines)
                    outfile.writelines(lines)
                outfile.write("\n\n")
            else:
                print(f"  [WARN] File not found: {rel_path}")

    print("==================================================")
    print(f"Successfully generated: {output_file}")
    print(f"Total lines consolidated: {total_lines:,} lines")
    print("==================================================")

if __name__ == "__main__":
    main()
