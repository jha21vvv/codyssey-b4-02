#!/bin/bash
# ==============================================================================
# [1차]: 스크립트 명칭 및 환경 초기화 스크립트 메타데이터 선언부
# [2차]: 리눅스 가상환경 안에서 서비스가 살아갈 집과 방을 원클릭으로 청소하고 세팅해주는 이삿짐센터 팀장 스크립트
# ==============================================================================

# [1차]: 실행 도중 명령어 에러(-e)가 발생하면 즉각 중단하고, 미정의 변수(-u) 사용을 차단합니다.
# [2차]: 공사 중 벽돌이 하나라도 깨지면 즉시 작업을 멈추고 안전점검을 받는 엄격한 안전모 규정입니다.
set -euo pipefail

# [1차]: 다국어 환경에 구애받지 않고 일관된 출력을 위해 표준 C 로케일로 강제 설정합니다.
# [2차]: 미국, 한국 어디서든 줄자와 저울 눈금을 똑같이 읽기 위한 국제 표준 규격입니다.
export LC_ALL=C

# [1차]: agent-leak-app의 홈 디렉토리 기본 경로를 변수에 할당합니다.
# [2차]: 우리 서비스가 영업할 메인 건물 주소를 명함에 적어둡니다.
AGENT_HOME="/home/agent-admin/agent-app"

# [1차]: 서비스가 통신할 기본 TCP 포트 번호를 상수로 선언합니다.
# [2차]: 손님들이 찾아올 공식 출입문 번호(15034호)를 확정합니다.
AGENT_PORT="15034"

# [1차]: 업로드 파일이 저장될 전용 하위 디렉토리 경로를 구성합니다.
# [2차]: 손님이 맡긴 택배 상자들을 보관할 택배 보관실 방 번호를 정합니다.
AGENT_UPLOAD_DIR="${AGENT_HOME}/upload_files"

# [1차]: 인증 키 및 시크릿 토큰 파일이 저장될 보안 디렉토리 경로를 구성합니다.
# [2차]: 황금 열쇠와 보안 카드를 넣어둘 은행 금고 방 위치를 정합니다.
AGENT_KEY_PATH="${AGENT_HOME}/api_keys"

# [1차]: 애플리케이션 및 모니터링 로그가 누적 기록될 시스템 로그 디렉토리 경로입니다.
# [2차]: 매일의 진료 기록과 블랙박스 영상을 모아둘 병원 의무기록실 서랍 위치입니다.
AGENT_LOG_DIR="/var/log/agent-app"

# [1차]: 과제 필수 secret.key 파일에 기록되어야 하는 고정 비밀번호 텍스트입니다.
# [2차]: 금고 문을 열 때 반드시 외쳐야 하는 암호("열려라 참깨") 텍스트입니다.
EXPECTED_SECRET="agent_api_key_test"

# [1차]: 콘솔에 컬러 출력을 지원하기 위한 ANSI 색상 이스케이프 코드 상수 정의부입니다.
# [2차]: 터미널 화면에 예쁜 신호등 불빛(초록, 빨강, 파랑, 노랑)을 켜기 위한 색연필 모음입니다.
C_RESET="\033[0m"
C_GREEN="\033[1;32m"
C_RED="\033[1;31m"
C_BLUE="\033[1;34m"
C_YELLOW="\033[1;33m"

# [1차]: 진행 단계 제목을 포맷팅하여 콘솔에 보기 좋게 출력하는 헬퍼 함수입니다.
# [2차]: 공사 현장 입구에 큼직한 작업 안내 표지판을 세우는 확성기입니다.
print_section() {
    echo -e "\n${C_BLUE}==================================================${C_RESET}"
    echo -e "${C_BLUE}  [SETUP] $1${C_RESET}"
    echo -e "${C_BLUE}==================================================${C_RESET}"
}

# ------------------------------------------------------------------------------
# 1. 실행 계정 확인 (root 금지, agent-admin 권장)
# ------------------------------------------------------------------------------
# [1차]: 현재 스크립트를 실행한 사용자의 실효 UID(id -u)가 0(root)인지 검사합니다.
# [2차]: 건물 출입구에서 마스터키를 든 최고관리자(root) 대신 일반 매니저(agent-admin)로 로그인했는지 신분증을 확인합니다.
print_section "1. Executing User Verification"
CURRENT_UID=$(id -u)
CURRENT_USER=$(whoami)

# [1차]: 일반 사용자 권한으로 실행 중인지 여부를 조건문으로 분기 검증합니다.
# [2차]: root가 아니어야만 과제 보안 요건(최소 권한의 원칙)을 통과하므로 초록 불을 켭니다.
if [ "${CURRENT_UID}" -eq 0 ]; then
    echo -e "${C_RED}[FAIL] Do not run the agent as root! Please run as 'agent-admin'.${C_RESET}"
    echo "Tip: Use 'wsl -u agent-admin' or 'su - agent-admin'"
    exit 1
else
    echo -e "${C_GREEN}[PASS] Execution Account: ${CURRENT_USER} (UID: ${CURRENT_UID}) - Non-root verified.${C_RESET}"
fi

# ------------------------------------------------------------------------------
# 2. 필수 디렉토리 생성 및 권한 설정
# ------------------------------------------------------------------------------
# [1차]: 업로드 디렉토리와 키 디렉토리가 없으면 mkdir -p 명령으로 자동 생성합니다.
# [2차]: 아직 방이 안 만들어졌으면 새 방을 짓고 페인트칠을 합니다.
print_section "2. Required Directories & Permissions Setup"
mkdir -p "${AGENT_UPLOAD_DIR}"
mkdir -p "${AGENT_KEY_PATH}"

# [1차]: 로그 디렉토리가 없거나 쓰기 권한이 없는 경우 안내 메시지와 함께 생성을 시도합니다.
# [2차]: 의무기록실 문이 잠겨 있거나 캐비닛이 없으면 관리자에게 열쇠를 요청하는 단계입니다.
if [ ! -d "${AGENT_LOG_DIR}" ] || [ ! -w "${AGENT_LOG_DIR}" ]; then
    echo -e "${C_YELLOW}[INFO] Log directory ${AGENT_LOG_DIR} needs setup. Checking permissions...${C_RESET}"
    if sudo -n true 2>/dev/null; then
        sudo mkdir -p "${AGENT_LOG_DIR}"
        sudo chown -R "${CURRENT_USER}:agent-core" "${AGENT_LOG_DIR}" 2>/dev/null || sudo chown -R "${CURRENT_USER}" "${AGENT_LOG_DIR}"
        sudo chmod -R 775 "${AGENT_LOG_DIR}"
        echo -e "${C_GREEN}[PASS] Created and configured ${AGENT_LOG_DIR} with 775 permissions.${C_RESET}"
    else
        echo -e "${C_YELLOW}[WARN] Sudo required to configure ${AGENT_LOG_DIR}. Falling back to local logs dir.${C_RESET}"
        AGENT_LOG_DIR="${AGENT_HOME}/logs"
        mkdir -p "${AGENT_LOG_DIR}"
    fi
else
    echo -e "${C_GREEN}[PASS] Log directory ${AGENT_LOG_DIR} is writable.${C_RESET}"
fi

# ------------------------------------------------------------------------------
# 3. secret.key 파일 생성 및 권한 부여
# ------------------------------------------------------------------------------
# [1차]: secret.key 파일 경로를 조합하고, 줄바꿈(\n) 없이 순수 키 문자열을 파일에 기록합니다.
# [2차]: 금고 비밀번호 카드에 번호(agent_api_key_test)를 인쇄하여 금고실에 꽂아둡니다.
print_section "3. API Secret Key File Deployment"
SECRET_FILE="${AGENT_KEY_PATH}/secret.key"

# [1차]: echo -n 옵션으로 파일 끝에 원치 않는 개행 문자가 들어가지 않도록 정밀 저장합니다.
# [2차]: 도장에 먼지가 묻지 않도록 깔끔하게 18글자만 잉크로 꾹 찍습니다.
echo -n "${EXPECTED_SECRET}" > "${SECRET_FILE}"

# [1차]: 소유자만 읽고 쓸 수 있도록 chmod 644 또는 600 권한을 부여합니다.
# [2차]: 열쇠 카드를 다른 사람이 훔쳐보지 못하게 자물쇠 서랍에 보관합니다.
chmod 644 "${SECRET_FILE}"

# [1차]: 파일이 정상 생성되었고 내용이 일치하는지 wc 및 cat으로 더블 체크합니다.
# [2차]: 인쇄된 글자가 번지지 않았는지 돋보기로 확인하고 합격 도장을 찍습니다.
ACTUAL_LEN=$(wc -c < "${SECRET_FILE}" | tr -dc '0-9')
if [ "${ACTUAL_LEN}" -eq 18 ]; then
    echo -e "${C_GREEN}[PASS] secret.key file verified at ${SECRET_FILE} (Exact 18 bytes: ${EXPECTED_SECRET})${C_RESET}"
else
    echo -e "${C_RED}[FAIL] secret.key length mismatch: expected 18, got ${ACTUAL_LEN}${C_RESET}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 4. 포트 15034 충돌 검사 및 기존 좀비 프로세스 정리
# ------------------------------------------------------------------------------
# [1차]: ss 또는 lsof 명령어를 통해 15034 포트를 선점하고 있는 프로세스가 있는지 검사합니다.
# [2차]: 우리 출입문(15034호)에 어제 퇴근 안 하고 자고 있는 취객(이전 프로세스)이 있는지 확인합니다.
print_section "4. Port 15034 Availability Check"
if ss -tlpn | grep -q ":${AGENT_PORT} "; then
    echo -e "${C_YELLOW}[WARN] Port ${AGENT_PORT} is currently in use. Cleaning up previous instance...${C_RESET}"
    # [1차]: 점유 중인 프로세스 PID를 조회하여 SIGTERM 시그널로 정상 종료를 유도합니다.
    # [2차]: 취객을 깨워서 집으로 안전하게 귀가(종료)시킵니다.
    OCCUPY_PID=$(ss -tlpn | grep ":${AGENT_PORT} " | awk '{print $NF}' | sed -E 's/.*pid=([0-9]+).*/\1/' || true)
    if [ -n "${OCCUPY_PID}" ]; then
        kill -15 "${OCCUPY_PID}" 2>/dev/null || true
        sleep 1
    fi
fi
echo -e "${C_GREEN}[PASS] Port ${AGENT_PORT} is free and ready for binding.${C_RESET}"

# ------------------------------------------------------------------------------
# 5. 환경변수 export 스크립트 작성 및 쉘 환경 제공
# ------------------------------------------------------------------------------
# [1차]: 사용자가 터미널에서 즉시 'source env.sh'로 불러올 수 있는 환경변수 파일을 생성합니다.
# [2차]: 매번 일일이 환경변수를 타이핑하지 않고 1초 만에 외울 수 있는 커닝페이퍼를 만듭니다.
print_section "5. Generating Environment Variable Helper (.env.agent)"
ENV_HELPER="${AGENT_HOME}/.env.agent"
cat << EOF > "${ENV_HELPER}"
export AGENT_HOME="${AGENT_HOME}"
export AGENT_PORT="${AGENT_PORT}"
export AGENT_UPLOAD_DIR="${AGENT_UPLOAD_DIR}"
export AGENT_KEY_PATH="${AGENT_KEY_PATH}"
export AGENT_LOG_DIR="${AGENT_LOG_DIR}"
export MEMORY_LIMIT="128"
export CPU_MAX_OCCUPY="80"
export MULTI_THREAD_ENABLE="true"
export APP_PROCESS_NAME="agent-leak-app"
EOF
chmod 644 "${ENV_HELPER}"

echo -e "${C_GREEN}[SUCCESS] Environment configuration completed successfully!${C_RESET}"
echo -e "To activate in your current terminal session, run:"
echo -e "  ${C_YELLOW}source ${ENV_HELPER}${C_RESET}\n"
