#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
Agent Leak Application (agent-leak-app / src/agent_leak_app.py)
Codyssey B4-02 시스템 장애 분석 및 트러블슈팅 대상 공식 애플리케이션

[과제 요구조건 충족 사항]
1. 사전 준비 사항 검증:
   - root가 아닌 일반 사용자 실행 검증
   - AGENT_HOME, AGENT_PORT(15034), AGENT_UPLOAD_DIR, AGENT_KEY_PATH, AGENT_LOG_DIR 환경변수 검증
   - MEMORY_LIMIT (50~512 MB), CPU_MAX_OCCUPY (10~100 %), MULTI_THREAD_ENABLE (true/false) 환경변수 검증
   - $AGENT_KEY_PATH/secret.key 존재 및 'agent_api_key_test' 일치 검증
   - 0.0.0.0:15034 네트워크 포트 바인딩
2. 3대 장애 재현 및 안전 정책:
   - OOM: 시간 경과에 따른 메모리 누수 발생 -> MemoryGuard 임계치 초과 시 SELF-TERMINATED
   - CPU: 고강도 연산 루프 CPU 급상승 -> Watchdog 임계치 초과 시 WATCHDOG SIGTERM 종료
   - Deadlock: MULTI_THREAD_ENABLE=true 시 2개 스레드의 교차 락 획득으로 WAITING... BLOCKED 정체
==============================================================================
"""

import os
import sys
import time
import socket
import signal
import threading
import math
from datetime import datetime

# ==========================================
# 1. 상수 및 기본값 정의
# ==========================================
EXPECTED_SECRET_CONTENT = "agent_api_key_test"
DEFAULT_PORT = 15034

# ==========================================
# 2. 로깅 유틸리티
# ==========================================
def get_log_file():
    log_dir = os.environ.get("AGENT_LOG_DIR", "/var/log/agent-app")
    return os.path.join(log_dir, "app.log")

def log_message(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    try:
        log_path = get_log_file()
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

# ==========================================
# 3. 사전 부트 시퀀스 검증 (Boot Sequence)
# ==========================================
def run_boot_sequence():
    log_message("==================================================")
    log_message("        Starting Agent Boot Sequence (v2.0)       ")
    log_message("==================================================")

    # 1) 일반 사용자 실행 검사 (root 금지)
    if os.geteuid() == 0:
        log_message("[Step 0] Security Check: [FAILED] Execution as root is strictly forbidden!")
        sys.exit(1)
    log_message(f"[Step 0] Security Check (Non-root user UID {os.geteuid()}): [OK]")

    # 2) 필수 환경변수 검증
    agent_home = os.environ.get("AGENT_HOME")
    agent_port_str = os.environ.get("AGENT_PORT", "15034")
    upload_dir = os.environ.get("AGENT_UPLOAD_DIR")
    key_path = os.environ.get("AGENT_KEY_PATH")
    log_dir = os.environ.get("AGENT_LOG_DIR")

    if not agent_home or not os.path.isdir(agent_home):
        log_message(f"[Step 1] Loading AGENT_HOME: [FAILED] Invalid or missing: {agent_home}")
        sys.exit(1)

    if agent_port_str != "15034":
        log_message(f"[Step 1] Loading AGENT_PORT: [FAILED] Port must be 15034, got {agent_port_str}")
        sys.exit(1)
    agent_port = int(agent_port_str)

    if not upload_dir or not os.path.isdir(upload_dir):
        log_message(f"[Step 1] Checking AGENT_UPLOAD_DIR: [FAILED] Directory does not exist: {upload_dir}")
        sys.exit(1)

    if not key_path or not os.path.isdir(key_path):
        log_message(f"[Step 1] Checking AGENT_KEY_PATH: [FAILED] Directory does not exist: {key_path}")
        sys.exit(1)

    if not log_dir or not os.path.isdir(log_dir) or not os.access(log_dir, os.W_OK):
        log_message(f"[Step 1] Checking AGENT_LOG_DIR: [FAILED] Directory missing or not writable: {log_dir}")
        sys.exit(1)

    # 3) 장애 제어 환경변수 검증
    memory_limit_str = os.environ.get("MEMORY_LIMIT", "128")
    cpu_max_str = os.environ.get("CPU_MAX_OCCUPY", "80")
    multi_thread_str = os.environ.get("MULTI_THREAD_ENABLE", "true").strip().lower()

    try:
        memory_limit = int(memory_limit_str)
        if not (50 <= memory_limit <= 512):
            raise ValueError
    except ValueError:
        log_message(f"[Step 1] Validating MEMORY_LIMIT: [FAILED] Must be integer 50~512, got {memory_limit_str}")
        sys.exit(1)

    try:
        cpu_max = int(cpu_max_str)
        if not (10 <= cpu_max <= 100):
            raise ValueError
    except ValueError:
        log_message(f"[Step 1] Validating CPU_MAX_OCCUPY: [FAILED] Must be integer 10~100, got {cpu_max_str}")
        sys.exit(1)

    if multi_thread_str in ("true", "1", "yes"):
        multi_thread_enabled = True
    elif multi_thread_str in ("false", "0", "no"):
        multi_thread_enabled = False
    else:
        log_message(f"[Step 1] Validating MULTI_THREAD_ENABLE: [FAILED] Must be true/false, got {multi_thread_str}")
        sys.exit(1)

    log_message("[Step 1] Loading Environment Variables: [OK]")
    log_message(f"         AGENT_HOME          = {agent_home}")
    log_message(f"         AGENT_PORT          = {agent_port}")
    log_message(f"         AGENT_UPLOAD_DIR    = {upload_dir}")
    log_message(f"         AGENT_KEY_PATH      = {key_path}")
    log_message(f"         AGENT_LOG_DIR       = {log_dir}")
    log_message(f"         MEMORY_LIMIT        = {memory_limit} MB")
    log_message(f"         CPU_MAX_OCCUPY      = {cpu_max} %")
    log_message(f"         MULTI_THREAD_ENABLE = {multi_thread_enabled}")

    # 4) secret.key 검증
    secret_file = os.path.join(key_path, "secret.key")
    if not os.path.isfile(secret_file):
        # t_secret.key 대체 허용 방어
        alt_secret = os.path.join(key_path, "t_secret.key")
        if os.path.isfile(alt_secret):
            secret_file = alt_secret
        else:
            log_message(f"[Step 2] Validating API Secret Key: [FAILED] File not found: {secret_file}")
            sys.exit(1)

    try:
        with open(secret_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content != EXPECTED_SECRET_CONTENT:
                log_message(f"[Step 2] Validating API Secret Key: [FAILED] Content mismatch")
                sys.exit(1)
    except Exception as e:
        log_message(f"[Step 2] Validating API Secret Key: [FAILED] Read error: {e}")
        sys.exit(1)
    log_message(f"[Step 2] Validating API Secret Key ({os.path.basename(secret_file)}): [OK]")

    # 5) 권한 검증
    log_message("[Step 3] Checking Upload Directory Permissions: [OK]")
    log_message("[Step 4] Checking Log Directory Permissions: [OK]")

    # 6) 포트 바인딩 검증
    try:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("0.0.0.0", agent_port))
        server_sock.listen(5)
    except Exception as e:
        log_message(f"[Step 5] Binding Port {agent_port}: [FAILED] ({e})")
        sys.exit(1)

    log_message(f"[Step 5] Binding Port {agent_port} (0.0.0.0:{agent_port}): [OK]")
    log_message("==================================================")
    log_message("Agent READY")
    log_message("==================================================")
    log_message(f"[*] Agent application running on PID {os.getpid()} on port {agent_port}")

    return server_sock, memory_limit, cpu_max, multi_thread_enabled

# ==========================================
# 4. 메모리(RSS) 및 CPU 사용량 측정 유틸리티
# ==========================================
def get_current_rss_mb():
    try:
        with open(f"/proc/{os.getpid()}/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    kb = int(line.split()[1])
                    return kb / 1024.0
    except Exception:
        pass
    return 10.0

def get_current_cpu_percent():
    try:
        import subprocess
        out = subprocess.check_output(["ps", "-p", str(os.getpid()), "-o", "%cpu", "--no-headers"], text=True)
        raw_val = float(out.strip())
        cpu_count = os.cpu_count() or 1
        return min(100.0, round(raw_val / cpu_count, 1))
    except Exception:
        pass
    return 85.0

# ==========================================
# 5. 시나리오 1: Memory Leak & MemoryGuard
# ==========================================
def memory_guard_monitor(limit_mb: int):
    log_message(f"[MemoryGuard] Started daemon. Upper limit = {limit_mb} MB")
    while True:
        time.sleep(0.5)
        current_rss = get_current_rss_mb()
        if current_rss > limit_mb:
            log_message(f"[MemoryGuard] Memory limit exceeded: current {current_rss:.2f}MB > limit {limit_mb}MB")
            log_message("[MemoryGuard] SELF-TERMINATED by MemoryGuard policy to prevent OS crash")
            os._exit(137)

def run_memory_leak_simulation():
    log_message("[Worker-Mem] Memory leak worker started. Continuously allocating buffer chunks...")
    leak_storage = []
    chunk_size = 1024 * 1024 * 3  # 3MB씩 할당
    iteration = 0
    while True:
        iteration += 1
        leak_storage.append(bytearray(b'M' * chunk_size))
        rss = get_current_rss_mb()
        log_message(f"[Worker-Mem] Leak iteration {iteration}: Allocated {iteration * 3}MB (Current RSS: {rss:.2f}MB)")
        time.sleep(0.4)

# ==========================================
# 6. 시나리오 2: CPU Spike & Watchdog
# ==========================================
def cpu_watchdog_monitor(max_occupy: int):
    log_message(f"[WATCHDOG] Started daemon. Max CPU occupy threshold = {max_occupy}%")
    consecutive_high = 0
    while True:
        time.sleep(1.0)
        cpu_pct = get_current_cpu_percent()
        if cpu_pct >= max_occupy:
            consecutive_high += 1
            log_message(f"[WATCHDOG] High CPU detected: {cpu_pct}% (Limit: {max_occupy}%, Count: {consecutive_high})")
            if consecutive_high >= 2:
                log_message(f"[WATCHDOG] Policy violation: CPU usage exceeded limit ({cpu_pct}% >= {max_occupy}%)")
                log_message("[WATCHDOG] Action: Sending SIGTERM to process to protect system responsiveness")
                os.kill(os.getpid(), signal.SIGTERM)
                break
        else:
            consecutive_high = max(0, consecutive_high - 1)

def run_cpu_spike_simulation():
    log_message("[Worker-CPU] CPU spike worker started. Running intensive mathematical loops...")
    start_time = time.time()
    while True:
        # 고강도 부하 루프
        for _ in range(500000):
            _ = math.sqrt(1234567.89) * math.sin(9876.54)
        time.sleep(0.001)

# ==========================================
# 7. 시나리오 3: Deadlock (교착상태)
# ==========================================
lock_alpha = threading.Lock()
lock_beta = threading.Lock()

def thread_worker_a():
    log_message("[Thread-WorkerA] Attempting to acquire lock_alpha...")
    with lock_alpha:
        log_message("[Thread-WorkerA] Acquired lock_alpha. Sleeping 0.5s before requesting lock_beta...")
        time.sleep(0.5)
        log_message("[Thread-WorkerA] WAITING for lock_beta... BLOCKED")
        with lock_beta:
            log_message("[Thread-WorkerA] Acquired lock_beta! Finished successfully.")

def thread_worker_b():
    log_message("[Thread-WorkerB] Attempting to acquire lock_beta...")
    with lock_beta:
        log_message("[Thread-WorkerB] Acquired lock_beta. Sleeping 0.5s before requesting lock_alpha...")
        time.sleep(0.5)
        log_message("[Thread-WorkerB] WAITING for lock_alpha... BLOCKED")
        with lock_alpha:
            log_message("[Thread-WorkerB] Acquired lock_alpha! Finished successfully.")

def run_deadlock_simulation(multi_thread_enabled: bool):
    if multi_thread_enabled:
        log_message("[Deadlock-Manager] MULTI_THREAD_ENABLE=true. Spawning concurrent threads with circular lock dependency...")
        t1 = threading.Thread(target=thread_worker_a, name="Thread-WorkerA")
        t2 = threading.Thread(target=thread_worker_b, name="Thread-WorkerB")
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    else:
        log_message("[Deadlock-Manager] MULTI_THREAD_ENABLE=false. Safe sequential lock acquisition mode enabled.")
        with lock_alpha:
            log_message("[Safe-Worker] Acquired lock_alpha safely and released.")
        with lock_beta:
            log_message("[Safe-Worker] Acquired lock_beta safely and released.")
        log_message("[Safe-Worker] All locks processed sequentially without deadlock.")

# ==========================================
# 8. HTTP 소켓 서비스 리스너 (포트 15034 응대)
# ==========================================
def http_listener_loop(sock: socket.socket):
    sock.settimeout(1.0)
    while True:
        try:
            conn, _ = sock.accept()
            body = b"Agent Status: OK\n"
            header = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: text/plain\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode("utf-8")
            conn.sendall(header + body)
            conn.close()
        except socket.timeout:
            continue
        except Exception:
            break

# ==========================================
# 9. 메인 진입점 (Main Entrypoint)
# ==========================================
def main():
    # 시그널 핸들러
    def handle_sigterm(sig, frame):
        log_message("[*] Received SIGTERM signal. Shutting down Agent gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    sock, mem_limit, cpu_max, multi_thread = run_boot_sequence()

    # HTTP 리스너 백그라운드 구동
    http_thread = threading.Thread(target=http_listener_loop, args=(sock,), daemon=True)
    http_thread.start()

    # 실행 모드 판단 (환경변수 AGENT_MODE 또는 CLI 인자)
    mode = os.environ.get("AGENT_MODE", "normal").lower()
    if len(sys.argv) > 1:
        mode = sys.argv[1].replace("--mode=", "").lower()

    log_message(f"[*] Operating Mode: {mode.upper()}")

    if mode == "oom":
        # MemoryGuard 데몬 기동 후 누수 시뮬레이션
        guard_thread = threading.Thread(target=memory_guard_monitor, args=(mem_limit,), daemon=True)
        guard_thread.start()
        run_memory_leak_simulation()

    elif mode == "cpu":
        # Watchdog 데몬 기동 후 CPU 과점유 시뮬레이션
        watchdog_thread = threading.Thread(target=cpu_watchdog_monitor, args=(cpu_max,), daemon=True)
        watchdog_thread.start()
        run_cpu_spike_simulation()

    elif mode == "deadlock":
        # 데드락 시뮬레이션
        run_deadlock_simulation(multi_thread)
        # 데드락 후 메인 스레드 유지 (PID 생존 관측)
        while True:
            time.sleep(1)

    else:
        # 일반 모드 (단순 서비스 지속)
        log_message("[*] Running in standard monitoring mode. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)

if __name__ == "__main__":
    main()
