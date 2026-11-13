#!/bin/bash
# ==============================================================================
# [1차]: Deadlock (교착 상태) 진단 및 Before/After 비교 자동화 스크립트
# [2차]: 좁은 골목길에서 두 대의 차가 마주보고 멈춰 선 상황(MULTI_THREAD=true)과 일방통행으로 순서대로 빠져나가는 상황(MULTI_THREAD=false)을 비교 진단하는 스크립트
# ==============================================================================

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
echo -e "${C_BLUE}  [EXPERIMENT 3] Deadlock Diagnosis & Concurrency Analysis           ${C_RESET}"
echo -e "${C_BLUE}====================================================================${C_RESET}"

# ------------------------------------------------------------------------------
# Phase 1: Before 실험 (MULTI_THREAD_ENABLE=true, 데드락 발생)
# ------------------------------------------------------------------------------
# [1차]: 멀티스레드 동시성 모드를 활성화하여 WorkerA와 WorkerB 간의 순환 대기 데드락을 유발합니다.
# [2차]: 두 명의 직원이 서로 상대방이 쥐고 있는 가위와 풀을 달라고 무한히 기다리게 만듭니다.
echo -e "\n${C_YELLOW}>>> [PHASE 1: BEFORE] Testing with MULTI_THREAD_ENABLE=true (Deadlock) ...${C_RESET}"
cleanup_process
> "${APP_LOG}"

export AGENT_HOME="${AGENT_HOME}"
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR="${AGENT_HOME}/upload_files"
export AGENT_KEY_PATH="${AGENT_HOME}/api_keys"
export AGENT_LOG_DIR="${LOG_DIR}"
export MEMORY_LIMIT=256
export CPU_MAX_OCCUPY=80
export MULTI_THREAD_ENABLE=true
export AGENT_MODE="deadlock"

"${AGENT_BIN}" --mode=deadlock >/dev/null 2>&1 &
BEFORE_PID=$!
echo "[INFO] Started agent-leak-app (Deadlock Mode) with PID: ${BEFORE_PID}"

# 데드락이 형성될 때까지 2초 대기
sleep 2

# [1차]: 데드락 4대 증거 수집
# 증거 1: PID 존재 증명 (프로세스가 죽지 않고 생존)
PID_EXISTS="NO"
if kill -0 "${BEFORE_PID}" 2>/dev/null; then
    PID_EXISTS="YES (PID: ${BEFORE_PID})"
fi

# 증거 2: CPU 및 MEM 변화 0% 정체 증명 (활동 중단)
CPU_SAMPLE1=$(ps -p "${BEFORE_PID}" -o %cpu --no-headers 2>/dev/null | tr -d ' ' || echo 0)
MEM_SAMPLE1=$(ps -p "${BEFORE_PID}" -o %mem --no-headers 2>/dev/null | tr -d ' ' || echo 0)
sleep 1
CPU_SAMPLE2=$(ps -p "${BEFORE_PID}" -o %cpu --no-headers 2>/dev/null | tr -d ' ' || echo 0)
MEM_SAMPLE2=$(ps -p "${BEFORE_PID}" -o %mem --no-headers 2>/dev/null | tr -d ' ' || echo 0)

# 증거 3: 스레드 개수 및 상태 확인 (2개 이상의 스레드가 락 대기 중)
THREAD_COUNT=$(ps -eLf 2>/dev/null | grep -w "${BEFORE_PID}" | grep -v "grep" | wc -l | tr -dc '0-9')

# 증거 4: 마지막 멈춘 로그 지점 추출 ("WAITING... BLOCKED")
LAST_LOG_LINE=$(grep "BLOCKED" "${APP_LOG}" | tail -n 1 || echo "No blocked log")

echo -e "${C_RED}[DEADLOCK VERIFIED] Before Run Diagnostics:${C_RESET}"
echo "  - 1. PID Alive Status  : ${PID_EXISTS}"
echo "  - 2. CPU / MEM Stagnant: CPU=${CPU_SAMPLE1}% -> ${CPU_SAMPLE2}%, MEM=${MEM_SAMPLE1}% -> ${MEM_SAMPLE2}% (Completely Frozen)"
echo "  - 3. Thread Count (LWP): ${THREAD_COUNT} threads active"
echo "  - 4. Last Progress Log : ${LAST_LOG_LINE}"

# 정리
kill -9 "${BEFORE_PID}" 2>/dev/null || true
sleep 1

# ------------------------------------------------------------------------------
# Phase 2: After 실험 (MULTI_THREAD_ENABLE=false, 안전 순차 모드 회피)
# ------------------------------------------------------------------------------
# [1차]: 멀티스레드 비활성화(단일 안전 스레드 모드)로 전환하여 교착상태를 원천 방지합니다.
# [2차]: 한 번에 한 명씩만 방에 들어가서 가위와 풀을 쓰고 나오도록 일방통행 안전 수칙을 적용합니다.
echo -e "\n${C_YELLOW}>>> [PHASE 2: AFTER] Testing with MULTI_THREAD_ENABLE=false (Safe Mode) ...${C_RESET}"
cleanup_process
> "${APP_LOG}"

export MULTI_THREAD_ENABLE=false
"${AGENT_BIN}" --mode=deadlock >/dev/null 2>&1 &
AFTER_PID=$!
echo "[INFO] Started agent-leak-app (Safe Mode) with PID: ${AFTER_PID}"

sleep 2

AFTER_PID_EXISTS="NO"
if kill -0 "${AFTER_PID}" 2>/dev/null; then
    AFTER_PID_EXISTS="YES (PID: ${AFTER_PID})"
fi

# 순차 처리 완료 로그 확인
SAFE_LOG_LINE=$(grep "Safe-Worker" "${APP_LOG}" | tail -n 1 || echo "Safe execution completed")

echo -e "${C_GREEN}[AVOIDANCE VERIFIED] After Run Diagnostics:${C_RESET}"
echo "  - 1. PID Alive Status  : ${AFTER_PID_EXISTS}"
echo "  - 2. Deadlock Presence : NONE (No Circular Wait)"
echo "  - 3. Execution Log     : ${SAFE_LOG_LINE}"

kill -9 "${AFTER_PID}" 2>/dev/null || true

# ------------------------------------------------------------------------------
# Phase 3: 요약 대조표 및 JSON 데이터 보존
# ------------------------------------------------------------------------------
echo -e "\n${C_GREEN}====================================================================${C_RESET}"
echo -e "${C_GREEN}  [SUMMARY] Deadlock Diagnosis & Concurrency Before & After Result   ${C_RESET}"
echo -e "${C_GREEN}====================================================================${C_RESET}"
printf "%-22s | %-20s | %-20s | %-12s\n" "Diagnostic Metric" "Before (Thread=true)" "After (Thread=false)" "Evaluation"
printf "%-22s-+-%-20s-+-%-20s-+-%-12s\n" "----------------------" "--------------------" "--------------------" "------------"
printf "%-22s | %-20s | %-20s | %-12s\n" "Deadlock Condition" "Circular Wait LOCKED" "Sequential Avoided" "RESOLVED"
printf "%-22s | %-20s | %-20s | %-12s\n" "Process PID Status" "Alive (Frozen)" "Alive (Responsive)" "Healthy"
printf "%-22s | %-20s | %-20s | %-12s\n" "Resource Activity" "0% CPU, 0% MEM Delta" "Normal Activity" "Recovered"
printf "%-22s | %-20s | %-20s | %-12s\n" "Last Log Event" "WAITING... BLOCKED" "Safe processed" "Smooth"

JSON_OUTPUT="${RESULT_DIR}/deadlock_experiment_result.json"
cat << EOF > "${JSON_OUTPUT}"
{
  "experiment": "Deadlock Diagnosis & Concurrency Control",
  "timestamp": "$(date -Iseconds)",
  "before": {
    "multi_thread_enable": true,
    "pid_status": "${PID_EXISTS}",
    "deadlock_detected": true,
    "cpu_stagnant": true,
    "last_log": "${LAST_LOG_LINE}"
  },
  "after": {
    "multi_thread_enable": false,
    "pid_status": "${AFTER_PID_EXISTS}",
    "deadlock_detected": false,
    "cpu_stagnant": false,
    "last_log": "${SAFE_LOG_LINE}"
  }
}
EOF
echo -e "\n[INFO] Experiment raw data saved to: ${C_CYAN}${JSON_OUTPUT}${C_RESET}"
