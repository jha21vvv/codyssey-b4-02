#!/bin/bash
# ==============================================================================
# [1차]: agent-leak-app-x86 프로세스의 생존 여부, CPU/메모리 사용량, 로그 정체 시간(LOG_IDLE)을 감시하는 관제 스크립트입니다.
# [2차]: 서버라는 병실에 들어간 환자의 심박수(PID), 체온(CPU), 혈압(RSS 메모리), 숨쉬는 간격(LOG_IDLE)을 체크해 진료 차트(monitor.log)에 적는 간호사입니다.
# ==============================================================================

set -u

TARGET_PATTERN="${TARGET_PATTERN:-agent-leak-app-x86}"
LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
MONITOR_LOG="${MONITOR_LOG:-${LOG_DIR}/monitor.log}"
APP_LOG="${APP_LOG:-${LOG_DIR}/agent_app.log}"

if [ ! -f "${APP_LOG}" ] && [ -f "${LOG_DIR}/app.log" ]; then
    APP_LOG="${LOG_DIR}/app.log"
fi

mkdir -p "${LOG_DIR}"
NOW_STR="$(date '+%Y-%m-%d %H:%M:%S')"
PID="$(pgrep -n -f "${TARGET_PATTERN}" || true)"

if [ -z "${PID}" ]; then
    echo "[${NOW_STR}] PROCESS:down TARGET:${TARGET_PATTERN}" >> "${MONITOR_LOG}"
    exit 1
fi

STAT="$(ps -o stat= -p "${PID}" 2>/dev/null | awk '{print $1}')"
CPU_PCT="$(ps -o pcpu= -p "${PID}" 2>/dev/null | awk '{print $1}')"
MEM_PCT="$(ps -o pmem= -p "${PID}" 2>/dev/null | awk '{print $1}')"
RSS_MB="$(ps -o rss= -p "${PID}" 2>/dev/null | awk '{print int($1/1024)}')"

if [ -z "${STAT}" ]; then
    echo "[${NOW_STR}] PROCESS:down TARGET:${TARGET_PATTERN}" >> "${MONITOR_LOG}"
    exit 1
fi

LOG_IDLE=0
if [ -f "${APP_LOG}" ]; then
    NOW_EPOCH="$(date +%s)"
    MTIME_EPOCH="$(stat -c %Y "${APP_LOG}" 2>/dev/null || echo "${NOW_EPOCH}")"
    LOG_IDLE=$(( NOW_EPOCH - MTIME_EPOCH ))
fi

echo "[${NOW_STR}] PID:${PID} STAT:${STAT} CPU:${CPU_PCT}% RSS:${RSS_MB}MB MEM:${MEM_PCT}% LOG_IDLE:${LOG_IDLE}s" >> "${MONITOR_LOG}"

