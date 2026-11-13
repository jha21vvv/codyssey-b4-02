#!/bin/bash
# ==============================================================================
# [1차]: 공식 바이너리(agent-leak-app-x86)를 WSL2에서 실제로 실행해 OOM, CPU, Deadlock Before/After 로그를 수집합니다.
# [2차]: 3가지 고장 상황을 실험실에서 직접 재현하고, 관제 기록(monitor.log)과 진료 차트(agent_app.log)를 파일로 봉인하는 자동 실험기입니다.
# ==============================================================================

set -euo pipefail

REPO_ROOT="$(pwd)"
LOG_ARCHIVE_DIR="${REPO_ROOT}/logs"
mkdir -p "${LOG_ARCHIVE_DIR}"

export AGENT_HOME="/home/agent-admin/agent-app"
export AGENT_PORT="15034"
export AGENT_UPLOAD_DIR="${AGENT_HOME}/upload_files"
export AGENT_KEY_PATH="${AGENT_HOME}/api_keys"
export AGENT_LOG_DIR="/var/log/agent-app"
BIN_PATH="${AGENT_HOME}/agent-leak-app-x86"
MONITOR_SCRIPT="${AGENT_HOME}/scripts/monitor.sh"

mkdir -p "${AGENT_HOME}/scripts"
sed 's/\r$//' "${REPO_ROOT}/scripts/monitor.sh" > "${MONITOR_SCRIPT}"
chmod +x "${MONITOR_SCRIPT}"

cleanup_all() {
    pkill -9 -f "agent-leak-app" 2>/dev/null || true
    pkill -9 -f "agent_app.py" 2>/dev/null || true
    pkill -9 -f "monitor.sh" 2>/dev/null || true
    fuser -k "${AGENT_PORT}/tcp" 2>/dev/null || true
    sleep 1
}

run_case() {
    local case_name="$1"
    local mem_limit="$2"
    local cpu_limit="$3"
    local multi_thread="$4"
    local max_wait="$5"

    echo "=== Running ${case_name} (MEM=${mem_limit}, CPU=${cpu_limit}, THREAD=${multi_thread}) ==="
    cleanup_all
    : > "${AGENT_LOG_DIR}/agent_app.log"
    : > "${AGENT_LOG_DIR}/monitor.log"

    export MEMORY_LIMIT="${mem_limit}"
    export CPU_MAX_OCCUPY="${cpu_limit}"
    export MULTI_THREAD_ENABLE="${multi_thread}"

    local start_ts
    start_ts="$(date +%s)"

    "${BIN_PATH}" > "${LOG_ARCHIVE_DIR}/${case_name}_stdout.log" 2>&1 &
    local app_pid=$!

    (
        while kill -0 "${app_pid}" 2>/dev/null; do
            "${MONITOR_SCRIPT}" || true
            sleep 1
        done
        "${MONITOR_SCRIPT}" || true
    ) &
    local mon_pid=$!

    local elapsed=0
    local exit_code=0
    while kill -0 "${app_pid}" 2>/dev/null; do
        if [ "${elapsed}" -ge "${max_wait}" ]; then
            if [ "${case_name}" = "deadlock_before" ]; then
                ps -ef | grep "agent-leak-app-x86" | grep -v grep > "${LOG_ARCHIVE_DIR}/${case_name}_ps_ef.txt" || true
                ps -eLf | grep "${app_pid}" | grep -v grep > "${LOG_ARCHIVE_DIR}/${case_name}_ps_elf.txt" || true
                top -b -n 1 -H -p "${app_pid}" > "${LOG_ARCHIVE_DIR}/${case_name}_top_h.txt" || true
            fi
            kill -9 "${app_pid}" 2>/dev/null || true
            exit_code=124
            break
        fi
        if [ "${case_name}" = "cpu_before" ] && [ "${elapsed}" -eq 3 ]; then
            top -b -n 1 -p "${app_pid}" > "${LOG_ARCHIVE_DIR}/${case_name}_top.txt" || true
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    if [ "${exit_code}" -eq 0 ]; then
        wait "${app_pid}" || exit_code=$?
    fi
    wait "${mon_pid}" 2>/dev/null || true

    local end_ts
    end_ts="$(date +%s)"
    local duration=$((end_ts - start_ts))

    cp "${AGENT_LOG_DIR}/agent_app.log" "${LOG_ARCHIVE_DIR}/${case_name}_app.log"
    cp "${AGENT_LOG_DIR}/monitor.log" "${LOG_ARCHIVE_DIR}/${case_name}_monitor.log"
    echo "${exit_code},${duration}" > "${LOG_ARCHIVE_DIR}/${case_name}_meta.txt"
    echo "[DONE] ${case_name}: exit=${exit_code}, duration=${duration}s"
}

# 1. OOM: Before (128MB) vs After (512MB)
run_case "oom_before" 128 30 false 60
run_case "oom_after" 512 30 false 35

# 2. CPU: Before (80%) vs After (30%)
run_case "cpu_before" 512 80 false 60
run_case "cpu_after" 512 30 false 35

# 3. Deadlock: Before (true) vs After (false)
run_case "deadlock_before" 512 30 true 12
run_case "deadlock_after" 512 30 false 12

cleanup_all
echo "ALL REAL BINARY EXPERIMENTS COMPLETED."
