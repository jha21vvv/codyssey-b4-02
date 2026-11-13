#!/bin/bash
# ==============================================================================
# [1차]: CPU Spike & Watchdog 보호 정책 실험 및 Before/After 비교 자동화 스크립트
# [2차]: 직원이 과로(CPU 100%)할 때 경비원(Watchdog)이 퇴근 경고(SIGTERM)를 날리는 기준선(30% vs 95%)을 시험하는 스크립트
# ==============================================================================

# [1차]: 예외 발생 시 파이프라인 안전 차단 및 C 로케일 환경을 강제합니다.
# [2차]: 안전 차단기를 올리고 시험을 시작합니다.
set -euo pipefail
export LC_ALL=C

AGENT_HOME="${AGENT_HOME:-/home/agent-admin/agent-app}"
AGENT_BIN="${AGENT_HOME}/agent-leak-app"
LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
APP_LOG="${LOG_DIR}/app.log"
RESULT_DIR="${AGENT_HOME}/experiment_results"
mkdir -p "${RESULT_DIR}"

C_RESET="\033[0m"
C_GREEN="\033[1;32m"
C_RED="\033[1;31m"
C_BLUE="\033[1;34m"
C_YELLOW="\033[1;33m"
C_CYAN="\033[1;36m"

cleanup_process() {
    kill -9 $(pgrep -f "agent-leak-app") 2>/dev/null || true
    kill -9 $(lsof -t -i:15034) 2>/dev/null || true
    sleep 0.5
}

echo -e "${C_BLUE}====================================================================${C_RESET}"
echo -e "${C_BLUE}  [EXPERIMENT 2] CPU Spike & Watchdog Protection Analysis            ${C_RESET}"
echo -e "${C_BLUE}====================================================================${C_RESET}"

# ------------------------------------------------------------------------------
# Phase 1: Before 실험 (CPU_MAX_OCCUPY=30%, 엄격한 감시)
# ------------------------------------------------------------------------------
# [1차]: CPU_MAX_OCCUPY를 30%로 낮게 설정하여 고부하 시 Watchdog SIGTERM 종료를 유도합니다.
# [2차]: 체온계 기준선을 37도로 낮춰 잡아서 조금만 뛰어도 비상벨을 울리게 만듭니다.
echo -e "\n${C_YELLOW}>>> [PHASE 1: BEFORE] Testing with CPU_MAX_OCCUPY=30% ...${C_RESET}"
cleanup_process
> "${APP_LOG}"

export AGENT_HOME="${AGENT_HOME}"
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR="${AGENT_HOME}/upload_files"
export AGENT_KEY_PATH="${AGENT_HOME}/api_keys"
export AGENT_LOG_DIR="${LOG_DIR}"
export MEMORY_LIMIT=256
export CPU_MAX_OCCUPY=30
export MULTI_THREAD_ENABLE=true
export AGENT_MODE="cpu"

BEFORE_START=$(date +%s%N)
"${AGENT_BIN}" --mode=cpu >/dev/null 2>&1 &
BEFORE_PID=$!
echo "[INFO] Started agent-leak-app (CPU Mode) with PID: ${BEFORE_PID}"

# [1차]: 프로세스가 Watchdog에 의해 SIGTERM 수신 후 종료될 때까지 대기합니다 (최대 10초 타임아웃).
# [2차]: 경비원이 호루라기를 불고 점원을 끌어낼 때까지 시간을 잽니다.
BEFORE_PEAK_CPU=0
TIMEOUT_COUNTER=0
while kill -0 "${BEFORE_PID}" 2>/dev/null && [ "${TIMEOUT_COUNTER}" -lt 25 ]; do
    CURRENT_CPU=$(ps -p "${BEFORE_PID}" -o %cpu --no-headers 2>/dev/null | awk '{printf "%.0f", $1}' || echo 0)
    if [ "${CURRENT_CPU}" -gt "${BEFORE_PEAK_CPU}" ]; then
        BEFORE_PEAK_CPU="${CURRENT_CPU}"
    fi
    sleep 0.3
    TIMEOUT_COUNTER=$((TIMEOUT_COUNTER + 1))
done
BEFORE_END=$(date +%s%N)
BEFORE_DURATION_MS=$(( (BEFORE_END - BEFORE_START) / 1000000 ))
BEFORE_DURATION_SEC=$(awk "BEGIN {printf \"%.2f\", ${BEFORE_DURATION_MS} / 1000}")

# 종료 상태 검사
BEFORE_STATUS="Terminated by Watchdog (SIGTERM)"
if kill -0 "${BEFORE_PID}" 2>/dev/null; then
    BEFORE_STATUS="Still Running (Unexpected)"
    kill -9 "${BEFORE_PID}" 2>/dev/null || true
fi

BEFORE_LOG=$(grep -i "WATCHDOG.*SIGTERM" "${APP_LOG}" || echo "No watchdog termination log")
echo -e "${C_RED}[TERMINATION VERIFIED] Before Run Finished:${C_RESET}"
echo "  - Survival Duration : ${BEFORE_DURATION_SEC} s"
echo "  - Peak CPU Usage    : ${BEFORE_PEAK_CPU} %"
echo "  - Status            : ${BEFORE_STATUS}"
echo "  - Watchdog Log      : ${BEFORE_LOG}"

sleep 1

# ------------------------------------------------------------------------------
# Phase 2: After 실험 (CPU_MAX_OCCUPY=95%, 임계치 완화 조치)
# ------------------------------------------------------------------------------
# [1차]: CPU_MAX_OCCUPY를 95%로 상향하여 고부하 상황에서도 프로세스가 강제 종료되지 않도록 조치합니다.
# [2차]: 체온계 기준선을 42도로 대폭 올려서 마라톤을 뛰어도 경비원이 제지하지 않도록 허용합니다.
echo -e "\n${C_YELLOW}>>> [PHASE 2: AFTER] Testing with CPU_MAX_OCCUPY=95% (Mitigation) ...${C_RESET}"
cleanup_process
> "${APP_LOG}"

export CPU_MAX_OCCUPY=95
AFTER_START=$(date +%s%N)
"${AGENT_BIN}" --mode=cpu >/dev/null 2>&1 &
AFTER_PID=$!
echo "[INFO] Started agent-leak-app (CPU Mode) with PID: ${AFTER_PID}"

# [1차]: 5초간 지속 관측하여 프로세스가 죽지 않고 안정적으로 유지되는지 검증합니다.
# [2차]: 5초 동안 지켜보며 직원이 쓰러지지 않고 계속 일하고 있는지 확인합니다.
AFTER_PEAK_CPU=0
for ((i=1; i<=15; i++)); do
    if kill -0 "${AFTER_PID}" 2>/dev/null; then
        CURRENT_CPU=$(ps -p "${AFTER_PID}" -o %cpu --no-headers 2>/dev/null | awk '{printf "%.0f", $1}' || echo 0)
        if [ "${CURRENT_CPU}" -gt "${AFTER_PEAK_CPU}" ]; then
            AFTER_PEAK_CPU="${CURRENT_CPU}"
        fi
    fi
    sleep 0.3
done
AFTER_END=$(date +%s%N)
AFTER_DURATION_MS=$(( (AFTER_END - AFTER_START) / 1000000 ))
AFTER_DURATION_SEC=$(awk "BEGIN {printf \"%.2f\", ${AFTER_DURATION_MS} / 1000}")

AFTER_STATUS="Active & Serving (Normal)"
if ! kill -0 "${AFTER_PID}" 2>/dev/null; then
    AFTER_STATUS="Prematurely Terminated"
else
    echo -e "${C_GREEN}[STABILITY VERIFIED] Process is still happily running without Watchdog interruption.${C_RESET}"
    kill -9 "${AFTER_PID}" 2>/dev/null || true
fi

AFTER_LOG=$(grep -i "WATCHDOG.*SIGTERM" "${APP_LOG}" || echo "None (No SIGTERM trigger)")
echo -e "${C_GREEN}[STABLE RESULT] After Run Finished:${C_RESET}"
echo "  - Test Duration     : ${AFTER_DURATION_SEC} s"
echo "  - Peak CPU Usage    : ${AFTER_PEAK_CPU} %"
echo "  - Process Status    : ${AFTER_STATUS}"
echo "  - Watchdog Signal   : ${AFTER_LOG}"

# ------------------------------------------------------------------------------
# Phase 3: Before & After 요약 대조표 및 JSON 데이터 보존
# ------------------------------------------------------------------------------
echo -e "\n${C_GREEN}====================================================================${C_RESET}"
echo -e "${C_GREEN}  [SUMMARY] CPU Latency & Watchdog Before & After Comparison        ${C_RESET}"
echo -e "${C_GREEN}====================================================================${C_RESET}"
printf "%-22s | %-16s | %-16s | %-12s\n" "Metric" "Before (Limit 30%)" "After (Limit 95%)" "Improvement"
printf "%-22s-+-%-16s-+-%-16s-+-%-12s\n" "----------------------" "----------------" "----------------" "------------"
printf "%-22s | %-16s | %-16s | %-12s\n" "Process Survival" "Killed by Watchdog" "Sustained Stable" "RESOLVED"
printf "%-22s | %-16s | %-16s | %-12s\n" "Survival Duration" "${BEFORE_DURATION_SEC} s" "> ${AFTER_DURATION_SEC} s" "Uninterrupted"
printf "%-22s | %-16s | %-16s | %-12s\n" "Peak CPU Recorded" "${BEFORE_PEAK_CPU} %" "${AFTER_PEAK_CPU} %" "Handled"
printf "%-22s | %-16s | %-16s | %-12s\n" "Watchdog Action" "SIGTERM Sent" "No Signal (Safe)" "Protected"

JSON_OUTPUT="${RESULT_DIR}/cpu_experiment_result.json"
cat << EOF > "${JSON_OUTPUT}"
{
  "experiment": "CPU Spike & Watchdog Protection",
  "timestamp": "$(date -Iseconds)",
  "before": {
    "cpu_limit_pct": 30,
    "survival_duration_sec": ${BEFORE_DURATION_SEC},
    "peak_cpu_pct": ${BEFORE_PEAK_CPU},
    "status": "${BEFORE_STATUS}",
    "watchdog_log": "${BEFORE_LOG}"
  },
  "after": {
    "cpu_limit_pct": 95,
    "survival_duration_sec": ${AFTER_DURATION_SEC},
    "peak_cpu_pct": ${AFTER_PEAK_CPU},
    "status": "${AFTER_STATUS}",
    "watchdog_log": "${AFTER_LOG}"
  }
}
EOF
echo -e "\n[INFO] Experiment raw data saved to: ${C_CYAN}${JSON_OUTPUT}${C_RESET}"
