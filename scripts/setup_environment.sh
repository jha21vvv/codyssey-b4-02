#!/bin/bash
# ==============================================================================
# [1차]: 공식 바이너리(agent-leak-app-x86) 실행을 위한 WSL2 Ubuntu 사전 요구사항 검증 및 환경 구축 스크립트입니다.
# [2차]: 손님(공식 프로그램)을 맞이하기 전에 방(디렉터리), 열쇠(secret.key), 출입문(15034 포트)을 깔끔하게 점검하는 사전 준비 스크립트입니다.
# ==============================================================================

set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
    echo "[ERROR] root 계정으로 실행할 수 없습니다. 일반 사용자(agent-admin)로 실행하세요."
    exit 1
fi

AGENT_HOME="${AGENT_HOME:-/home/agent-admin/agent-app}"
AGENT_PORT="${AGENT_PORT:-15034}"
AGENT_UPLOAD_DIR="${AGENT_UPLOAD_DIR:-${AGENT_HOME}/upload_files}"
AGENT_KEY_PATH="${AGENT_KEY_PATH:-${AGENT_HOME}/api_keys}"
AGENT_LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
BIN_NAME="agent-leak-app-x86"
BIN_PATH="${AGENT_HOME}/${BIN_NAME}"

mkdir -p "${AGENT_HOME}/bin" "${AGENT_HOME}/scripts" "${AGENT_UPLOAD_DIR}" "${AGENT_KEY_PATH}" "${AGENT_LOG_DIR}"
echo -n "agent_api_key_test" > "${AGENT_KEY_PATH}/secret.key"
chmod 600 "${AGENT_KEY_PATH}/secret.key"

if [ ! -x "${BIN_PATH}" ]; then
    echo "[ERROR] 실행 가능한 공식 바이너리가 없습니다: ${BIN_PATH}"
    exit 1
fi

pkill -9 -f "agent-leak-app" 2>/dev/null || true
pkill -9 -f "agent_app.py" 2>/dev/null || true
sleep 0.5

if ss -tlpn 2>/dev/null | grep -q ":${AGENT_PORT} "; then
    echo "[WARN] 포트 ${AGENT_PORT} 점유 프로세스 정리 중..."
    fuser -k "${AGENT_PORT}/tcp" 2>/dev/null || true
    sleep 0.5
fi

echo "[PASS] 실행 계정: $(whoami) (UID=$(id -u))"
echo "[PASS] 바이너리 경로: ${BIN_PATH}"
echo "[PASS] 필수 디렉터리 및 secret.key 준비 완료"
echo "[PASS] 포트 ${AGENT_PORT} 사용 가능"

