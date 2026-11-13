#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
[1차]: Matplotlib 기반 고해상도 시스템 아키텍처 및 장애 메커니즘 다이어그램 생성기
[2차]: 복잡한 리눅스 서버 내부에서 일어나는 메모리 폭주, CPU 과열, 락 꼬임 현상을 돋보기로 들여다보듯 알록달록한 그림으로 그려내는 화가 스크립트
==============================================================================
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")  # [1차]: GUI 창을 띄우지 않고 파일로만 렌더링하는 헤드리스 백엔드 설정 / [2차]: 모니터 화면 없이 사진 인화기계로만 작동하는 모드
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# [1차]: 출력 디렉토리 경로 지정 및 생성
# [2차]: 그림 액자들을 보관할 전용 갤러리 방(diagrams/)을 만듭니다.
DIAGRAMS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "diagrams")
os.makedirs(DIAGRAMS_DIR, exist_ok=True)

# [1차]: 폰트 설정 (한글 깨짐 방지를 위해 영문/유니코드 범용 sans-serif 폰트 우선 적용)
# [2차]: 어떤 컴퓨터에서 열어도 글자가 네모 박스(□)로 깨지지 않고 깔끔하게 보이도록 글씨체를 다듬습니다.
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.unicode_minus'] = False

# ==============================================================================
# 다이어그램 1: 시스템 전체 아키텍처 및 관제 흐름도
# ==============================================================================
def generate_diagram_1():
    # [1차]: 1200x700 픽셀 비율의 Figure 및 Axes 객체를 생성합니다.
    # [2차]: 커다란 도화지 한 장을 이젤 위에 올려놓습니다.
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 배경 박스 (Host OS vs WSL2 Linux)
    # [1차]: WSL2 Ubuntu 가상환경 경계를 나타내는 둥근 직사각형(FancyBboxPatch)을 배치합니다.
    # [2차]: 리눅스 가상 머신이라는 울타리를 그리고, 그 안에서 프로세스가 뛰어노는 영역을 표시합니다.
    wsl_box = patches.FancyBboxPatch((5, 5), 90, 88, boxstyle="round,pad=1.5",
                                     edgecolor="#2B6CB0", facecolor="#EBF8FF", linewidth=2.5)
    ax.add_patch(wsl_box)
    ax.text(8, 88, "WSL2 Ubuntu 22.04 LTS (Host Environment)", fontsize=14, fontweight='bold', color="#2B6CB0")

    # 사용자 계정 영역
    user_box = patches.FancyBboxPatch((8, 12), 40, 72, boxstyle="round,pad=1",
                                      edgecolor="#319795", facecolor="#E6FFFA", linewidth=1.8)
    ax.add_patch(user_box)
    ax.text(10, 80, "User: agent-admin (UID: 1000, Non-Root)", fontsize=11, fontweight='bold', color="#234E52")

    # Agent Application Box
    app_box = patches.FancyBboxPatch((11, 20), 34, 56, boxstyle="round,pad=1",
                                     edgecolor="#D69E2E", facecolor="#FEFCBF", linewidth=2)
    ax.add_patch(app_box)
    ax.text(14, 71, "Target Process: agent-leak-app", fontsize=11, fontweight='bold', color="#744210")
    ax.text(14, 66, "Port: 0.0.0.0:15034 [LISTEN]", fontsize=9, color="#975A16")

    # 내부 모듈 3종
    # [1차]: 3대 장애 및 보호 데몬(MemoryGuard, Watchdog, Lock Manager) 서브 모듈 박스
    # [2차]: 앱 내부에서 일하는 3명의 직원(메모리 감시원, CPU 청원경찰, 교통정리원) 방을 배치합니다.
    mg_box = patches.Rectangle((13, 50), 30, 12, facecolor="#FC8181", edgecolor="#9B2C2C", linewidth=1.5)
    ax.add_patch(mg_box)
    ax.text(15, 57, "[Thread 1] MemoryGuard", fontsize=9, fontweight='bold', color="#742A2A")
    ax.text(15, 52, "Monitors RSS MB vs MEMORY_LIMIT", fontsize=8, color="#742A2A")

    wd_box = patches.Rectangle((13, 35), 30, 12, facecolor="#F6AD55", edgecolor="#9C4221", linewidth=1.5)
    ax.add_patch(wd_box)
    ax.text(15, 42, "[Thread 2] CPU Watchdog", fontsize=9, fontweight='bold', color="#7B341E")
    ax.text(15, 37, "Monitors %CPU vs CPU_MAX_OCCUPY", fontsize=8, color="#7B341E")

    dl_box = patches.Rectangle((13, 22), 30, 10, facecolor="#BEE3F8", edgecolor="#2B6CB0", linewidth=1.5)
    ax.add_patch(dl_box)
    ax.text(15, 27, "[Threads 3/4] Concurrency Locks", fontsize=9, fontweight='bold', color="#2A4365")
    ax.text(15, 23, "Lock-A vs Lock-B (Deadlock)", fontsize=8, color="#2A4365")

    # 관제 도구 (monitor.sh & 시스템 도구)
    mon_box = patches.FancyBboxPatch((52, 52), 40, 32, boxstyle="round,pad=1",
                                     edgecolor="#4A5568", facecolor="#EDF2F7", linewidth=2)
    ax.add_patch(mon_box)
    ax.text(54, 79, "Monitoring System (bin/monitor.sh)", fontsize=11, fontweight='bold', color="#1A202C")
    ax.text(54, 73, "- Process Check: pgrep -f agent-leak-app", fontsize=9, color="#2D3748")
    ax.text(54, 68, "- Resource Audit: CPU%, MEM%, DISK%", fontsize=9, color="#2D3748")
    ax.text(54, 63, "- Health Validation: Port 15034 check", fontsize=9, color="#2D3748")
    ax.text(54, 58, "- Log Rotation: 10MB limit, 10 backups", fontsize=9, color="#2D3748")

    # 파일 시스템 & 로그 저장소
    log_box = patches.FancyBboxPatch((52, 12), 40, 34, boxstyle="round,pad=1",
                                     edgecolor="#805AD5", facecolor="#FAF5FF", linewidth=2)
    ax.add_patch(log_box)
    ax.text(54, 41, "Logging Subsystem (/var/log/agent-app)", fontsize=11, fontweight='bold', color="#44337A")
    ax.text(54, 34, "1. app.log : Boot sequence & Crash events", fontsize=9, color="#553C9A")
    ax.text(54, 27, "2. monitor.log : Periodic resource stats", fontsize=9, color="#553C9A")
    ax.text(54, 20, "3. experiment_results/ : JSON test metrics", fontsize=9, color="#553C9A")

    # 화살표 연결 (App -> Logs, Monitor -> App, Monitor -> Logs)
    # [1차]: 모듈 간 데이터 흐름을 화살표(annotate)로 연결합니다.
    # [2차]: 어느 선으로 데이터와 보고서가 오고 가는지 통신 케이블을 연결합니다.
    ax.annotate("", xy=(52, 68), xytext=(45, 68),
                arrowprops=dict(arrowstyle="->", lw=2, color="#4A5568"))
    ax.annotate("", xy=(52, 28), xytext=(45, 28),
                arrowprops=dict(arrowstyle="->", lw=2, color="#805AD5"))
    ax.annotate("", xy=(72, 46), xytext=(72, 52),
                arrowprops=dict(arrowstyle="->", lw=2, color="#4A5568"))

    plt.tight_layout()
    out_path = os.path.join(DIAGRAMS_DIR, "01_system_architecture_overview.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[OK] Diagram 1 generated: {out_path}")

# ==============================================================================
# 다이어그램 2: Memory Leak 및 OOM MemoryGuard 메커니즘
# ==============================================================================
def generate_diagram_2():
    # [1차]: 1000x600 크기의 그래프로 메모리 누수와 임계치 도달 곡선을 그립니다.
    # [2차]: 시간에 따라 메모리 수조에 물이 차오르다가 넘쳐서 사이렌이 울리는 모습을 꺾은선 그래프로 표현합니다.
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    # 시간 축 (초)
    t_before = np.linspace(0, 6.8, 100)
    rss_before = 10 + 8.0 * t_before  # 60MB 도달

    t_after = np.linspace(0, 25.19, 100)
    rss_after = 10 + 7.6 * t_after   # 200MB 도달

    # Before 곡선
    ax.plot(t_before, rss_before, label="Before (MEMORY_LIMIT=60MB)", color="#E53E3E", linewidth=3)
    # After 곡선
    ax.plot(t_after, rss_after, label="After (MEMORY_LIMIT=200MB)", color="#3182CE", linewidth=3, linestyle="--")

    # 임계선 표시
    ax.axhline(y=60, color="#E53E3E", linestyle=":", linewidth=1.8, label="Limit: 60MB Threshold")
    ax.axhline(y=200, color="#3182CE", linestyle=":", linewidth=1.8, label="Limit: 200MB Threshold")

    # 충돌 지점 마커
    ax.scatter([6.8], [64.8], color="#E53E3E", s=150, zorder=5)
    ax.annotate("Crash (6.8s)\nSELF-TERMINATED (Exit 137)", xy=(6.8, 64.8), xytext=(8, 90),
                arrowprops=dict(facecolor="#E53E3E", shrink=0.08, width=1.5, headwidth=8),
                fontsize=9, fontweight='bold', color="#9B2C2C")

    ax.scatter([25.19], [202.8], color="#3182CE", s=150, zorder=5)
    ax.annotate("Extended Survival (25.2s)\n+270.4% Lifespan (+141MB)", xy=(25.19, 202.8), xytext=(17, 160),
                arrowprops=dict(facecolor="#3182CE", shrink=0.08, width=1.5, headwidth=8),
                fontsize=9, fontweight='bold', color="#2B6CB0")

    ax.set_title("Memory Leak Progression & MemoryGuard Protection (Before vs After)", fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel("Elapsed Time (Seconds)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Resident Set Size (RSS Memory MB)", fontsize=11, fontweight='bold')
    ax.set_ylim(0, 230)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="upper left", frameon=True, shadow=True)

    plt.tight_layout()
    out_path = os.path.join(DIAGRAMS_DIR, "02_oom_memory_leak_mechanism.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[OK] Diagram 2 generated: {out_path}")

# ==============================================================================
# 다이어그램 3: CPU 과점유 및 Watchdog 보호 메커니즘
# ==============================================================================
def generate_diagram_3():
    # [1차]: CPU 부하 급상승과 Watchdog SIGTERM 차단 흐름 그래프 생성
    # [2차]: 모터가 과열(CPU 100%)되었을 때 퓨즈(Watchdog)가 전원을 차단하는 과정을 비교합니다.
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    t = np.linspace(0, 8, 100)
    # CPU 부하 스파이크
    cpu_load = 10 + 90 / (1 + np.exp(-3 * (t - 1.5)))

    ax.plot(t, cpu_load, label="Process CPU Usage (%)", color="#DD6B20", linewidth=3)
    ax.axhline(y=30, color="#E53E3E", linestyle=":", linewidth=2, label="Before Limit: CPU_MAX_OCCUPY=30%")
    ax.axhline(y=95, color="#38A169", linestyle="-.", linewidth=2, label="After Limit: CPU_MAX_OCCUPY=95% (Safe)")

    # 30% 초과 종료 지점 (t=2.2s)
    ax.scatter([2.2], [75], color="#E53E3E", s=160, zorder=5)
    ax.annotate("SIGTERM by Watchdog (2.2s)\nProcess Terminated (Limit 30%)", xy=(2.2, 75), xytext=(0.5, 45),
                arrowprops=dict(facecolor="#E53E3E", shrink=0.08, width=1.5, headwidth=8),
                fontsize=9, fontweight='bold', color="#9B2C2C")

    # 95% 이하 유지 안전 영역
    ax.fill_between(t, 0, 95, color="#C6F6D5", alpha=0.3, label="Safe Execution Zone (< 95%)")

    ax.set_title("CPU Spike Latency & Watchdog Intervention Mechanism", fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel("Time Elapsed (Seconds)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Normalized CPU Occupancy (%)", fontsize=11, fontweight='bold')
    ax.set_ylim(0, 110)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="lower right", frameon=True, shadow=True)

    plt.tight_layout()
    out_path = os.path.join(DIAGRAMS_DIR, "03_cpu_watchdog_mechanism.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[OK] Diagram 3 generated: {out_path}")

# ==============================================================================
# 다이어그램 4: 교착 상태(Deadlock) 순환 대기 모델
# ==============================================================================
def generate_diagram_4():
    # [1차]: 원형 순환 대기(Circular Wait)와 상호 배제, 점유 대기를 보여주는 다이어그램
    # [2차]: 두 철학자가 젓가락을 하나씩 쥐고 서로 상대방 젓가락을 내놓으라고 째려보는 교착상태 지도입니다.
    fig, ax = plt.subplots(figsize=(10, 7), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 93, "Deadlock: Circular Wait & 4 Coffman Conditions",
            fontsize=14, fontweight='bold', ha='center', color="#1A202C")

    # Thread A Box (Left)
    thread_a = patches.FancyBboxPatch((10, 50), 25, 25, boxstyle="round,pad=1",
                                      edgecolor="#3182CE", facecolor="#EBF8FF", linewidth=2.5)
    ax.add_patch(thread_a)
    ax.text(22.5, 65, "Thread-WorkerA", fontsize=11, fontweight='bold', ha='center', color="#2B6CB0")
    ax.text(22.5, 57, "Holds: Lock Alpha\nWaiting: Lock Beta", fontsize=9, ha='center', color="#2C5282")

    # Thread B Box (Right)
    thread_b = patches.FancyBboxPatch((65, 50), 25, 25, boxstyle="round,pad=1",
                                      edgecolor="#805AD5", facecolor="#FAF5FF", linewidth=2.5)
    ax.add_patch(thread_b)
    ax.text(77.5, 65, "Thread-WorkerB", fontsize=11, fontweight='bold', ha='center', color="#553C9A")
    ax.text(77.5, 57, "Holds: Lock Beta\nWaiting: Lock Alpha", fontsize=9, ha='center', color="#44337A")

    # Lock Alpha Box (Top Center)
    lock_a = patches.FancyBboxPatch((40, 70), 20, 15, boxstyle="round,pad=0.8",
                                    edgecolor="#D69E2E", facecolor="#FEFCBF", linewidth=2)
    ax.add_patch(lock_a)
    ax.text(50, 78, "Resource:\nLock Alpha", fontsize=10, fontweight='bold', ha='center', color="#744210")

    # Lock Beta Box (Bottom Center)
    lock_b = patches.FancyBboxPatch((40, 35), 20, 15, boxstyle="round,pad=0.8",
                                    edgecolor="#DD6B20", facecolor="#FEEBC8", linewidth=2)
    ax.add_patch(lock_b)
    ax.text(50, 43, "Resource:\nLock Beta", fontsize=10, fontweight='bold', ha='center', color="#7B341E")

    # 화살표 (점유 vs 대기)
    # Thread A -> Lock A (점유: Held)
    ax.annotate("HELD BY", xy=(35, 60), xytext=(40, 75),
                arrowprops=dict(facecolor="#3182CE", edgecolor="#3182CE", width=2, headwidth=8),
                fontsize=8, fontweight='bold', color="#2B6CB0")
    # Thread A -> Lock B (대기: Requests)
    ax.annotate("REQUESTS (BLOCKED)", xy=(40, 40), xytext=(25, 50),
                arrowprops=dict(facecolor="#E53E3E", edgecolor="#E53E3E", linestyle="--", width=2, headwidth=8),
                fontsize=8, fontweight='bold', color="#E53E3E")

    # Thread B -> Lock B (점유: Held)
    ax.annotate("HELD BY", xy=(65, 60), xytext=(60, 40),
                arrowprops=dict(facecolor="#805AD5", edgecolor="#805AD5", width=2, headwidth=8),
                fontsize=8, fontweight='bold', color="#553C9A")
    # Thread B -> Lock A (대기: Requests)
    ax.annotate("REQUESTS (BLOCKED)", xy=(60, 75), xytext=(75, 50),
                arrowprops=dict(facecolor="#E53E3E", edgecolor="#E53E3E", linestyle="--", width=2, headwidth=8),
                fontsize=8, fontweight='bold', color="#E53E3E")

    # 하단 4대 조건 요약 배너
    info_box = patches.FancyBboxPatch((8, 8), 84, 18, boxstyle="round,pad=0.8",
                                      edgecolor="#A0AEC0", facecolor="#EDF2F7", linewidth=1.5)
    ax.add_patch(info_box)
    ax.text(50, 20, "Four Coffman Conditions Satisfied:", fontsize=10, fontweight='bold', ha='center', color="#2D3748")
    ax.text(50, 12, "1. Mutual Exclusion  |  2. Hold & Wait  |  3. No Preemption  |  4. Circular Wait (LOCKED)",
            fontsize=9, ha='center', color="#4A5568")

    plt.tight_layout()
    out_path = os.path.join(DIAGRAMS_DIR, "04_deadlock_circular_wait.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[OK] Diagram 4 generated: {out_path}")

def main():
    print("==================================================")
    print("Generating Matplotlib High-Resolution Architecture Diagrams...")
    print("==================================================")
    generate_diagram_1()
    generate_diagram_2()
    generate_diagram_3()
    generate_diagram_4()
    print("All 4 diagrams created successfully in diagrams/ directory.")

if __name__ == "__main__":
    main()
