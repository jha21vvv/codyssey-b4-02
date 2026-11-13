#!/usr/bin/env python3
"""실측 기반 시스템 아키텍처 및 3대 장애 메커니즘 고해상도 PNG 다이어그램 생성기."""

from __future__ import annotations

from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams["font.sans-serif"] = ["Malgun Gothic", "DejaVu Sans", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

OUT_DIR = Path(__file__).resolve().parent.parent / "diagrams"


def _draw_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str,
    fc: str,
    ec: str,
    title_color: str = "#1A202C",
) -> None:
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.3,rounding_size=0.8",
        facecolor=fc,
        edgecolor=ec,
        linewidth=1.8,
    )
    ax.add_patch(box)
    ax.text(
        x + w / 2,
        y + h - 2.3,
        title,
        ha="center",
        va="top",
        fontsize=10.5,
        fontweight="bold",
        color=title_color,
    )
    ax.text(
        x + w / 2,
        y + h / 2 - 1.0,
        body,
        ha="center",
        va="center",
        fontsize=8.8,
        color="#2D3748",
    )


def _arrow(ax: plt.Axes, x1: float, y1: float, x2: float, y2: float, label: str = "", color: str = "#4A5568") -> None:
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": "->", "lw": 1.8, "color": color},
    )
    if label:
        ax.text(
            (x1 + x2) / 2,
            (y1 + y2) / 2 + 1.2,
            label,
            ha="center",
            va="bottom",
            fontsize=8.2,
            fontweight="bold",
            color=color,
        )


def gen_01_architecture() -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    ax.text(50, 56.5, "WSL2 Ubuntu-22.04 Official Binary Monitoring Architecture", ha="center", fontsize=14, fontweight="bold", color="#1A365D")
    ax.text(50, 53.3, "Target: agent-leak-app-x86 (Port 15034, Non-root: agent-admin)", ha="center", fontsize=9.5, color="#4A5568")

    _draw_box(ax, 5, 29, 26, 19, "Environment & Secrets", "AGENT_HOME / AGENT_PORT=15034\nsecret.key = agent_api_key_test\nMEMORY_LIMIT / CPU_MAX_OCCUPY\nMULTI_THREAD_ENABLE", "#EBF8FF", "#3182CE")
    _draw_box(ax, 38, 29, 28, 19, "agent-leak-app-x86", "[1/6~6/6] Boot Checks\nMemoryGuard + Watchdog\nWorker Threads (OOM/CPU/Lock)", "#FFF5F5", "#E53E3E")
    _draw_box(ax, 73, 29, 22, 19, "scripts/monitor.sh", "pgrep PID Tracking\nps RSS(MB), %CPU, %MEM\nstat -c %Y -> LOG_IDLE", "#F0FFF4", "#38A169")

    _draw_box(ax, 15, 5, 32, 16, "/var/log/agent-app/agent_app.log", "Boot Sequence, Memory Heap,\nWatchdog SIGTERM, Deadlock Events", "#FAF5FF", "#805AD5")
    _draw_box(ax, 55, 5, 32, 16, "/var/log/agent-app/monitor.log", "Periodic Time-Series Stats\nPID, STAT, CPU%, RSS, LOG_IDLE\nPROCESS:down Detection", "#FEFCBF", "#D69E2E")

    _arrow(ax, 31.5, 38.5, 37.5, 38.5, "Env Inject")
    _arrow(ax, 72.5, 38.5, 66.5, 38.5, "ps / pgrep")
    _arrow(ax, 48, 28.5, 34, 21.5, "Write Events", "#805AD5")
    _arrow(ax, 82, 28.5, 74, 21.5, "Write Stats", "#D69E2E")
    _arrow(ax, 47.5, 13, 54.5, 13, "stat mtime", "#38A169")

    plt.tight_layout()
    plt.savefig(OUT_DIR / "01_system_architecture_overview.png", dpi=150)
    plt.close(fig)


def gen_02_oom() -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 55)
    ax.axis("off")

    ax.text(50, 51.5, "Case 1: OOM Crash (MemoryGuard) vs Cache Flush Mechanism", ha="center", fontsize=13.5, fontweight="bold", color="#742A2A")

    _draw_box(ax, 6, 29, 24, 15, "1. Memory Allocation", "MemoryWorker allocates\nheap chunks continuously\n(RSS rises linearly)", "#FFF5F5", "#C53030")
    _draw_box(ax, 38, 29, 24, 15, "2. MemoryGuard Check", "Monitors RSS vs\nMEMORY_LIMIT threshold", "#FEFCBF", "#B7791F")
    _draw_box(ax, 70, 32, 25, 14, "Before: LIMIT=128MB", "Limit Exceeded!\nSELF-TERMINATED\nExit Code 137 (SIGKILL)", "#FED7D7", "#9B2C2C")
    _draw_box(ax, 70, 10, 25, 14, "After: LIMIT=512MB", "Memory Cache Flushed\nHeap Drops Safely\nSustained Healthy Run", "#C6F6D5", "#276749")

    _arrow(ax, 30.5, 36.5, 37.5, 36.5, "RSS Up")
    _arrow(ax, 62.5, 38, 69.5, 39, "Exceeds", "#C53030")
    _arrow(ax, 62.5, 33, 69.5, 17, "Flush Triggered", "#276749")

    _draw_box(ax, 6, 8, 56, 13, "Root Fix Principle", "1) Remove unbounded global buffer accumulation (use bounded LRU cache)\n2) Process large payloads via disk tempfile or streaming chunks", "#EDF2F7", "#4A5568")

    plt.tight_layout()
    plt.savefig(OUT_DIR / "02_oom_memory_leak_mechanism.png", dpi=150)
    plt.close(fig)


def gen_03_cpu() -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 55)
    ax.axis("off")

    ax.text(50, 51.5, "Case 2: CPU Spike & Watchdog SIGTERM vs Cooldown", ha="center", fontsize=13.5, fontweight="bold", color="#7B341E")

    _draw_box(ax, 6, 29, 24, 15, "1. CpuWorker Loop", "Intensive compute bursts\nraising internal CPU load", "#FFFAF0", "#DD6B20")
    _draw_box(ax, 38, 29, 24, 15, "2. SafetyGuard / Watchdog", "Checks CPU_MAX_OCCUPY\n& internal safety ceiling", "#FEFCBF", "#D69E2E")
    _draw_box(ax, 70, 32, 25, 14, "Before: LIMIT=80%", "Load > Safety Threshold\nWATCHDOG: SIGTERM\nExit Code 143", "#FED7D7", "#9B2C2C")
    _draw_box(ax, 70, 10, 25, 14, "After: LIMIT=30%", "Peak Reached -> Cooldown\nLoad throttled safely\nNo SIGTERM, Sustained", "#C6F6D5", "#276749")

    _arrow(ax, 30.5, 36.5, 37.5, 36.5, "Load Up")
    _arrow(ax, 62.5, 38, 69.5, 39, "Violated", "#C53030")
    _arrow(ax, 62.5, 33, 69.5, 17, "Cooldown", "#276749")

    _draw_box(ax, 6, 8, 56, 13, "Root Fix Principle", "1) Insert time.sleep() yield inside tight loops   2) Offload heavy tasks to Celery\n3) Enforce OS-level hardware isolation via Linux cgroups (cpu.max)", "#EDF2F7", "#4A5568")

    plt.tight_layout()
    plt.savefig(OUT_DIR / "03_cpu_watchdog_mechanism.png", dpi=150)
    plt.close(fig)


def gen_04_deadlock() -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 55)
    ax.axis("off")

    ax.text(50, 51.5, "Case 3: Deadlock Circular Wait vs Sequential Mode", ha="center", fontsize=13.5, fontweight="bold", color="#2B6CB0")

    _draw_box(ax, 6, 28, 25, 17, "Before: THREAD=true", "Worker-A holds Lock A\nwaits for Lock B\nWorker-B holds Lock B\nwaits for Lock A", "#FED7D7", "#C53030")
    _draw_box(ax, 37, 28, 26, 17, "3-Step Diagnosis", "1) ps -ef: PID Alive\n2) top -H: CPU 0% (futex)\n3) monitor.sh: LOG_IDLE up", "#FEFCBF", "#D69E2E")
    _draw_box(ax, 69, 28, 25, 17, "After: THREAD=false", "Sequential execution\nNo circular wait\nAll tasks completed", "#C6F6D5", "#276749")

    _arrow(ax, 31.5, 36.5, 36.5, 36.5, "Diagnose")
    _arrow(ax, 63.5, 36.5, 68.5, 36.5, "Workaround")

    _draw_box(ax, 6, 8, 88, 13, "Coffman 4 Conditions & Root Fix", "Deadlock requires: Mutual Exclusion + Hold & Wait + No Preemption + Circular Wait.\nBreak any 1 condition -> Enforce global Lock Ordering (always Lock A -> Lock B) or Lock Timeout.", "#EBF8FF", "#3182CE")

    plt.tight_layout()
    plt.savefig(OUT_DIR / "04_deadlock_circular_wait.png", dpi=150)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gen_01_architecture()
    gen_02_oom()
    gen_03_cpu()
    gen_04_deadlock()
    print(f"Generated 4 diagrams in {OUT_DIR}")


if __name__ == "__main__":
    main()

