#!/usr/bin/env python3
"""실제 agent-leak-app-x86 실행 로그(agent_app.log, monitor.log)를 파싱해 JSON 요약 결과를 생성하는 모듈."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


RSS_PATTERN = re.compile(r"RSS:(\d+)MB")
CPU_PATTERN = re.compile(r"CPU:([0-9.]+)%")
HEAP_PATTERN = re.compile(r"Current Heap:\s*(\d+)MB")
LOAD_PATTERN = re.compile(r"Current Load:\s*([0-9.]+)%")
IDLE_PATTERN = re.compile(r"LOG_IDLE:(\d+)s")


def parse_monitor_log(text: str) -> dict[str, Any]:
    """monitor.log 텍스트에서 최대 RSS, 최대 CPU, 최대 LOG_IDLE, 다운 감지 여부를 추출합니다."""
    # [1차]: 정규표현식 finditer로 로그 전체에서 RSS, CPU, LOG_IDLE 수치를 리스트로 추출합니다.
    # [2차]: 간호사가 적어둔 진료 차트에서 혈압(RSS), 체온(CPU), 호흡 멈춤 시간(LOG_IDLE) 숫자만 쏙쏙 뽑아냅니다.
    rss_values = [int(m.group(1)) for m in RSS_PATTERN.finditer(text)]
    cpu_values = [float(m.group(1)) for m in CPU_PATTERN.finditer(text)]
    idle_values = [int(m.group(1)) for m in IDLE_PATTERN.finditer(text)]
    # [1차]: 프로세스 종료 마커("PROCESS:down") 문자열 포함 여부를 불리언으로 판별합니다.
    # [2차]: 차트 맨 아래에 "환자 퇴실(PROCESS:down)" 도장이 찍혔는지 확인합니다.
    process_down = "PROCESS:down" in text

    return {
        "samples": len(rss_values),
        "peak_rss_mb": max(rss_values) if rss_values else 0,
        "min_rss_mb": min(rss_values) if rss_values else 0,
        "peak_cpu_pct": max(cpu_values) if cpu_values else 0.0,
        "max_log_idle_sec": max(idle_values) if idle_values else 0,
        "process_down_detected": process_down,
    }


def parse_app_log(text: str) -> dict[str, Any]:
    """agent_app.log 텍스트에서 핵심 이벤트(OOM, Cache Flushed, Watchdog, Deadlock)를 추출합니다."""
    heap_values = [int(m.group(1)) for m in HEAP_PATTERN.finditer(text)]
    load_values = [float(m.group(1)) for m in LOAD_PATTERN.finditer(text)]

    return {
        "line_count": len(text.splitlines()),
        "peak_heap_mb": max(heap_values) if heap_values else 0,
        "peak_internal_load_pct": max(load_values) if load_values else 0.0,
        "oom_self_terminated": "SELF-TERMINATED" in text or "Self-terminating" in text,
        "memory_cache_flushed": "Memory Cache Flushed" in text or "Flushed" in text,
        "watchdog_sigterm": ("WATCHDOG" in text and "SIGTERM" in text) or "CPU Threshold Violated" in text,
        "cooldown_detected": "Cooldown" in text or "cooldown" in text.lower(),
        "deadlock_detected": (
            "Deadlock" in text
            or "BLOCKED" in text
            or "waiting" in text.lower()
            or "Contention" in text
        ),
        "healthy_completed": "All tasks completed" in text,
    }


def summarize_experiment_pair(
    experiment_name: str,
    before_app_log: str,
    before_monitor_log: str,
    before_exit_code: int,
    before_duration_sec: float,
    after_app_log: str,
    after_monitor_log: str,
    after_exit_code: int,
    after_duration_sec: float,
) -> dict[str, Any]:
    """Before/After 실험 로그와 종료 코드를 종합하여 JSON 구조체로 반환합니다."""
    return {
        "experiment": experiment_name,
        "target_binary": "agent-leak-app-x86",
        "before": {
            "exit_code": before_exit_code,
            "duration_sec": round(before_duration_sec, 2),
            "app": parse_app_log(before_app_log),
            "monitor": parse_monitor_log(before_monitor_log),
        },
        "after": {
            "exit_code": after_exit_code,
            "duration_sec": round(after_duration_sec, 2),
            "app": parse_app_log(after_app_log),
            "monitor": parse_monitor_log(after_monitor_log),
        },
    }


def save_json_summary(output_path: Path, payload: dict[str, Any]) -> None:
    """요약 딕셔너리를 UTF-8 JSON 파일로 저장합니다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_meta(meta_path: Path) -> tuple[int, float]:
    """<case>_meta.txt에서 (exit_code, duration_sec)를 읽어옵니다."""
    if not meta_path.exists():
        return -1, 0.0
    parts = meta_path.read_text(encoding="utf-8").strip().split(",")
    return int(parts[0]), float(parts[1])


def generate_all_results(repo_root: Path | None = None) -> list[Path]:
    """logs/ 폴더의 실측 로그를 파싱해 experiment_results/*.json 3종을 생성합니다."""
    root = repo_root or Path(__file__).resolve().parent.parent
    logs_dir = root / "logs"
    out_dir = root / "experiment_results"
    cases = [
        ("oom", "oom_before", "oom_after", "oom_experiment_result.json"),
        ("cpu", "cpu_before", "cpu_after", "cpu_experiment_result.json"),
        ("deadlock", "deadlock_before", "deadlock_after", "deadlock_experiment_result.json"),
    ]
    written: list[Path] = []
    for name, before_key, after_key, out_name in cases:
        b_app = (logs_dir / f"{before_key}_app.log").read_text(encoding="utf-8", errors="replace")
        b_mon = (logs_dir / f"{before_key}_monitor.log").read_text(encoding="utf-8", errors="replace")
        b_exit, b_dur = _read_meta(logs_dir / f"{before_key}_meta.txt")

        a_app = (logs_dir / f"{after_key}_app.log").read_text(encoding="utf-8", errors="replace")
        a_mon = (logs_dir / f"{after_key}_monitor.log").read_text(encoding="utf-8", errors="replace")
        a_exit, a_dur = _read_meta(logs_dir / f"{after_key}_meta.txt")

        summary = summarize_experiment_pair(name, b_app, b_mon, b_exit, b_dur, a_app, a_mon, a_exit, a_dur)
        out_path = out_dir / out_name
        save_json_summary(out_path, summary)
        written.append(out_path)
    return written


if __name__ == "__main__":
    for p in generate_all_results():
        print(f"Saved: {p}")
