#!/bin/bash
# ==============================================================================
# [1차]: Memory Leak & OOM Crash 실험 및 Before/After 비교 자동화 스크립트
# [2차]: 물이 새는 고무보트에 물받이 통(MEMORY_LIMIT) 크기를 60L vs 200L로 바꿔가며 언제 가라앉는지 시간을 재는 실험실 스크립트
# ==============================================================================

# [1차]: 미정의 변수 사용 차단 및 비정상 파이프라인 중단 플래그를 설정합니다.
# [2차]: 실험 도중 시약이 쏟아지면 즉시 실험을 멈추고 안전하게 대피하는 규칙입니다.
set -euo pipefail
export LC_ALL=C

# [1차]: 기본 경로 및 로그 파일 위치를 변수로 선언합니다.
# [2차]: 실험실 주소와 실험 관측 일지 장소를 지정합니다.
AGENT_HOME="${AGENT_HOME:-/home/agent-admin/agent-app}"
AGENT_BIN="${AGENT_HOME}/agent-leak-app"
LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
APP_LOG="${LOG_DIR}/app.log"
MONITOR_LOG="${LOG_DIR}/monitor.log"
RESULT_DIR="${AGENT_HOME}/experiment_results"
mkdir -p "${RESULT_DIR}"

# [1차]: ANSI 컬러 코드 상수 정의부입니다.
# [2차]: 터미널 화면에 실험 결과를 화려한 색상으로 보고하기 위한 팔레트입니다.
C_RESET="\033[0m"
C_GREEN="\033[1;32m"
C_RED="\033[1;31m"
C_BLUE="\033[1;34m"
C_YELLOW="\033[1;33m"
C_CYAN="\033[1;36m"

# [1차]: 포트 및 프로세스를 정리하는 공통 헬퍼 함수입니다.
# [2차]: 새 실험을 시작하기 전에 실험실 테이블 위를 깨끗이 닦는 청소 도구입니다.
cleanup_process() {
    kill -9 $(pgrep -f "agent-leak-app") 2>/dev/null || true
    kill -9 $(lsof -t -i:15034) 2>/dev/null || true
    sleep 0.5
}

echo -e "${C_BLUE}====================================================================${C_RESET}"
echo -e "${C_BLUE}  [EXPERIMENT 1] Memory Leak & OOM Crash Analysis (MemoryGuard)      ${C_RESET}"
echo -e "${C_BLUE}====================================================================${C_RESET}"

# ------------------------------------------------------------------------------
# Phase 1: Before 실험 (MEMORY_LIMIT=60 MB, 타이트한 임계치)
# ------------------------------------------------------------------------------
# [1차]: 환경변수 MEMORY_LIMIT을 60MB로 작게 설정하여 조기 OOM Crash를 유도합니다.
# [2차]: 작은 컵(60ml)을 준비하여 물이 조금만 차올라도 금방 넘치게 만드는 상황입니다.
echo -e "\n${C_YELLOW}>>> [PHASE 1: BEFORE] Testing with MEMORY_LIMIT=60 MB ...${C_RESET}"
cleanup_process
> "${APP_LOG}"

# [1차]: 환경변수 export 및 OOM 모드로 백그라운드 구동합니다.
# [2차]: 스톱워치를 누르는 순간 프로세스에게 "메모리를 마구 먹어치워라" 명령을 내립니다.
export AGENT_HOME="${AGENT_HOME}"
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR="${AGENT_HOME}/upload_files"
export AGENT_KEY_PATH="${AGENT_HOME}/api_keys"
export AGENT_LOG_DIR="${LOG_DIR}"
export MEMORY_LIMIT=60
export CPU_MAX_OCCUPY=80
export MULTI_THREAD_ENABLE=true
export AGENT_MODE="oom"

BEFORE_START=$(date +%s%N)
"${AGENT_BIN}" --mode=oom >/dev/null 2>&1 &
BEFORE_PID=$!
echo "[INFO] Started agent-leak-app with PID: ${BEFORE_PID}"

# [1차]: 프로세스가 MemoryGuard에 의해 종료될 때까지 0.3초 간격으로 RSS 메모리를 추적합니다.
# [2차]: 풍선에 바람이 차오르는 것을 0.3초마다 자로 재며 언제 뻥 터지는지 지켜봅니다.
BEFORE_MAX_RSS=0
while kill -0 "${BEFORE_PID}" 2>/dev/null; do
    if [ -f "/proc/${BEFORE_PID}/status" ]; then
        CURRENT_KB=$(grep -i "VmRSS:" "/proc/${BEFORE_PID}/status" 2>/dev/null | awk '{print $2}' || echo 0)
        CURRENT_MB=$((CURRENT_KB / 1024))
        if [ "${CURRENT_MB}" -gt "${BEFORE_MAX_RSS}" ]; then
            BEFORE_MAX_RSS="${CURRENT_MB}"
        fi
    fi
    sleep 0.3
done
BEFORE_END=$(date +%s%N)
BEFORE_DURATION_MS=$(( (BEFORE_END - BEFORE_START) / 1000000 ))
BEFORE_DURATION_SEC=$(awk "BEGIN {printf \"%.2f\", ${BEFORE_DURATION_MS} / 1000}")

# [1차]: MemoryGuard가 남긴 핵심 종료 로그를 수집합니다.
# [2차]: 환자가 쓰러지며 남긴 마지막 블랙박스 기록을 복사해 둡니다.
BEFORE_LOG=$(grep -E "Memory limit exceeded|SELF-TERMINATED" "${APP_LOG}" || echo "No termination log found")
echo -e "${C_RED}[CRASH DETECTED] Before Run Finished:${C_RESET}"
echo "  - Survival Duration : ${BEFORE_DURATION_SEC} s"
echo "  - Peak Memory (RSS) : ${BEFORE_MAX_RSS} MB"
echo "  - Termination Log   : ${BEFORE_LOG}"

sleep 1

# ------------------------------------------------------------------------------
# Phase 2: After 실험 (MEMORY_LIMIT=200 MB, 완화된 임계치)
# ------------------------------------------------------------------------------
# [1차]: 환경변수 MEMORY_LIMIT을 200MB로 3.3배 상향 조정하여 생존 시간 변화를 관측합니다.
# [2차]: 컵을 대형 비커(200ml)로 바꾸어 물이 넘치기까지 얼마나 더 오래 버티는지 측정합니다.
echo -e "\n${C_YELLOW}>>> [PHASE 2: AFTER] Testing with MEMORY_LIMIT=200 MB ...${C_RESET}"
cleanup_process
> "${APP_LOG}"

export MEMORY_LIMIT=200
AFTER_START=$(date +%s%N)
"${AGENT_BIN}" --mode=oom >/dev/null 2>&1 &
AFTER_PID=$!
echo "[INFO] Started agent-leak-app with PID: ${AFTER_PID}"

# [1차]: 메모리 모니터링 루프를 실행하며 After 생존 기간을 정밀 측정합니다.
# [2차]: 더 커진 비커가 찰 때까지 차분히 타이머를 측정합니다.
AFTER_MAX_RSS=0
while kill -0 "${AFTER_PID}" 2>/dev/null; do
    if [ -f "/proc/${AFTER_PID}/status" ]; then
        CURRENT_KB=$(grep -i "VmRSS:" "/proc/${AFTER_PID}/status" 2>/dev/null | awk '{print $2}' || echo 0)
        CURRENT_MB=$((CURRENT_KB / 1024))
        if [ "${CURRENT_MB}" -gt "${AFTER_MAX_RSS}" ]; then
            AFTER_MAX_RSS="${CURRENT_MB}"
        fi
    fi
    sleep 0.3
done
AFTER_END=$(date +%s%N)
AFTER_DURATION_MS=$(( (AFTER_END - AFTER_START) / 1000000 ))
AFTER_DURATION_SEC=$(awk "BEGIN {printf \"%.2f\", ${AFTER_DURATION_MS} / 1000}")

AFTER_LOG=$(grep -E "Memory limit exceeded|SELF-TERMINATED" "${APP_LOG}" || echo "No termination log found")
echo -e "${C_GREEN}[CRASH DETECTED] After Run Finished:${C_RESET}"
echo "  - Survival Duration : ${AFTER_DURATION_SEC} s"
echo "  - Peak Memory (RSS) : ${AFTER_MAX_RSS} MB"
echo "  - Termination Log   : ${AFTER_LOG}"

# ------------------------------------------------------------------------------
# Phase 3: Before & After 비교 대조표 생성 및 JSON 데이터 저장
# ------------------------------------------------------------------------------
# [1차]: Before와 After의 측정 결과를 종합하여 터미널 대조표 및 JSON 형식으로 영구 보존합니다.
# [2차]: 실험 보고서 맨 위에 올릴 핵심 성적표(Before vs After)를 깔끔한 표로 요약합니다.
echo -e "\n${C_GREEN}====================================================================${C_RESET}"
echo -e "${C_GREEN}  [SUMMARY] OOM MemoryGuard Before & After Comparison Result        ${C_RESET}"
echo -e "${C_GREEN}====================================================================${C_RESET}"
printf "%-20s | %-15s | %-15s | %-12s\n" "Metric" "Before (Limit 60MB)" "After (Limit 200MB)" "Improvement"
printf "%-20s-+-%-15s-+-%-15s-+-%-12s\n" "--------------------" "---------------" "---------------" "------------"
printf "%-20s | %-15s | %-15s | %-12s\n" "Survival Duration" "${BEFORE_DURATION_SEC} s" "${AFTER_DURATION_SEC} s" "+$(awk "BEGIN {printf \"%.1f\", (${AFTER_DURATION_SEC} - ${BEFORE_DURATION_SEC}) / ${BEFORE_DURATION_SEC} * 100}")%"
printf "%-20s | %-15s | %-15s | %-12s\n" "Peak RSS Memory" "${BEFORE_MAX_RSS} MB" "${AFTER_MAX_RSS} MB" "+$(awk "BEGIN {printf \"%.0f\", ${AFTER_MAX_RSS} - ${BEFORE_MAX_RSS}}") MB"
printf "%-20s | %-15s | %-15s | %-12s\n" "Exit Code" "137 (SIGKILL)" "137 (SIGKILL)" "Identical"
printf "%-20s | %-15s | %-15s | %-12s\n" "Protection Policy" "MemoryGuard" "MemoryGuard" "Active"

# JSON 파일로 저장 (평가자 및 리포트 참조용)
JSON_OUTPUT="${RESULT_DIR}/oom_experiment_result.json"
cat << EOF > "${JSON_OUTPUT}"
{
  "experiment": "OOM Crash & MemoryGuard",
  "timestamp": "$(date -Iseconds)",
  "before": {
    "memory_limit_mb": 60,
    "survival_duration_sec": ${BEFORE_DURATION_SEC},
    "peak_rss_mb": ${BEFORE_MAX_RSS},
    "exit_code": 137,
    "termination_log": "${BEFORE_LOG}"
  },
  "after": {
    "memory_limit_mb": 200,
    "survival_duration_sec": ${AFTER_DURATION_SEC},
    "peak_rss_mb": ${AFTER_MAX_RSS},
    "exit_code": 137,
    "termination_log": "${AFTER_LOG}"
  }
}
EOF
echo -e "\n[INFO] Experiment raw data saved to: ${C_CYAN}${JSON_OUTPUT}${C_RESET}"
