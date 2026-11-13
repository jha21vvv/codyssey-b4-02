# 🖥️ [ENVIRONMENT_SETUP_GUIDE.md] 가상환경 터미널 설정 및 실행 기록부

> **목적**: WSL2 Linux 가상환경 접속부터 환경변수 설정, 필수 보안 키 생성, 서비스 기동, 3대 장애 모니터링 및 트러블슈팅 명령어까지 터미널에서 수행한 모든 작업을 차근차근 재현할 수 있도록 상세히 기록한 가이드입니다.  
> **대상 시스템**: WSL2 Ubuntu 22.04 LTS  
> **실행 사용자**: `agent-admin` (일반 사용자, UID: 1000)  
> **서비스 홈**: `/home/agent-admin/agent-app`

---

## 📌 목차
1. [가상환경 접속 및 사용자 확인](#1-가상환경-접속-및-사용자-확인)
2. [사전 준비 필수 요건 점검표](#2-사전-준비-필수-요건-점검표)
3. [디렉터리 권한 및 secret.key 생성](#3-디렉터리-권한-및-secretkey-생성)
4. [환경변수 설정 및 프로필 등록](#4-환경변수-설정-및-프로필-등록)
5. [네트워크 및 포트(15034) 바인딩 검증](#5-네트워크-및-포트15034-바인딩-검증)
6. [애플리케이션 및 모니터링 구동 명령어](#6-애플리케이션-및-모니터링-구동-명령어)
7. [장애 시나리오별 터미널 트리거 및 관제 명령어](#7-장애-시나리오별-터미널-트리거-및-관제-명령어)

---

## 1. 가상환경 접속 및 사용자 확인

과제 제약사항에 따라 **root 계정이 아닌 일반 사용자 계정**으로 실행해야 합니다.

### ① Windows 터미널(PowerShell)에서 WSL 일반 사용자로 접속
```powershell
# 일반 사용자 agent-admin 계정으로 WSL Ubuntu 진입
wsl -u agent-admin
```

### ② 현재 사용자 및 권한 확인 (Linux 내부)
```bash
# UID 및 소속 그룹 확인 (root가 아님을 확인: UID 1000)
id
# 출력 예시:
# uid=1000(agent-admin) gid=1001(agent-core) groups=1001(agent-core),27(sudo),1000(agent-common)

# 작업 디렉터리 이동
cd /home/agent-admin/agent-app
pwd
```

---

## 2. 사전 준비 필수 요건 점검표

| 항목 | 과제 요구 조건 | 설정 위치 및 값 | 검증 명령어 |
| :--- | :--- | :--- | :--- |
| **실행 계정** | root가 아닌 일반 사용자 | `agent-admin` | `whoami` |
| **`AGENT_HOME`** | 필수 환경변수 설정 | `/home/agent-admin/agent-app` | `echo $AGENT_HOME` |
| **`AGENT_PORT`** | 15034 (고정) | `15034` | `echo $AGENT_PORT` |
| **`AGENT_UPLOAD_DIR`** | 디렉터리 존재 필수 | `$AGENT_HOME/upload_files` | `ls -ld $AGENT_UPLOAD_DIR` |
| **`AGENT_KEY_PATH`** | 경로 존재 필수 | `$AGENT_HOME/api_keys` | `ls -ld $AGENT_KEY_PATH` |
| **`AGENT_LOG_DIR`** | 존재 + 쓰기 권한 | `/var/log/agent-app` | `test -w $AGENT_LOG_DIR && echo OK` |
| **`secret.key`** | `$AGENT_KEY_PATH/secret.key` | 내용: `agent_api_key_test` | `cat $AGENT_KEY_PATH/secret.key` |
| **네트워크 포트** | 0.0.0.0:15034 바인딩 가능 | `0.0.0.0:15034` | `ss -tlpn \| grep 15034` |

---

## 3. 디렉터리 권한 및 secret.key 생성

### ① 필수 디렉터리 생성 및 쓰기 권한 부여
```bash
# 1. 업로드 및 키 디렉터리 생성
mkdir -p /home/agent-admin/agent-app/upload_files
mkdir -p /home/agent-admin/agent-app/api_keys

# 2. 로그 디렉터리 생성 및 권한 설정 (sudo 필요 시 1회 부여)
sudo mkdir -p /var/log/agent-app
sudo chown -R agent-admin:agent-core /var/log/agent-app
sudo chmod -R 775 /var/log/agent-app
```

### ② secret.key 파일 생성 및 유효성 검증
과제 요구조건: 파일 위치 `$AGENT_KEY_PATH/secret.key`, 파일 내용 `agent_api_key_test` (줄바꿈 없이 정확한 문자열).
```bash
# secret.key 생성 (개행 문자 없이 생성)
echo -n "agent_api_key_test" > /home/agent-admin/agent-app/api_keys/secret.key

# 읽기 권한 확인 (소유자 읽기/쓰기)
chmod 600 /home/agent-admin/agent-app/api_keys/secret.key

# 내용 및 파일 크기 확인 (18바이트)
cat /home/agent-admin/agent-app/api_keys/secret.key
wc -c /home/agent-admin/agent-app/api_keys/secret.key
```

---

## 4. 환경변수 설정 및 프로필 등록

애플리케이션은 부트 시퀀스 단계에서 필수 환경변수를 검증합니다.

### ① 세션 환경변수 일괄 export
```bash
# 기본 경로 및 포트 설정
export AGENT_HOME=/home/agent-admin/agent-app
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR=$AGENT_HOME/upload_files
export AGENT_KEY_PATH=$AGENT_HOME/api_keys
export AGENT_LOG_DIR=/var/log/agent-app

# 장애 제어 기본값 설정 (테스트 시나리오별로 동적 변경)
export MEMORY_LIMIT=128
export CPU_MAX_OCCUPY=80
export MULTI_THREAD_ENABLE=true
```

### ② 터미널 재접속 시 자동 로드를 위한 `.bashrc` 반영
```bash
cat << 'EOF' >> ~/.bashrc

# ==========================================
# Codyssey B4-02 Agent Environment Variables
# ==========================================
export AGENT_HOME=/home/agent-admin/agent-app
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR=$AGENT_HOME/upload_files
export AGENT_KEY_PATH=$AGENT_HOME/api_keys
export AGENT_LOG_DIR=/var/log/agent-app
export PATH=$PATH:$AGENT_HOME/bin
EOF
```

---

## 5. 네트워크 및 포트(15034) 바인딩 검증

포트 충돌이 발생하면 애플리케이션이 `[Step 5] Binding Port 15034: [FAIL]`을 출력하고 종료됩니다.

```bash
# 현재 포트 15034를 점유 중인 프로세스 확인
ss -tlpn | grep 15034

# 만약 기존 프로세스가 점유 중이라면 안전하게 종료
kill -15 $(lsof -t -i:15034) 2>/dev/null || true
```

---

## 6. 애플리케이션 및 모니터링 구동 명령어

### ① 애플리케이션 포그라운드 실행 (부트 시퀀스 확인)
```bash
cd /home/agent-admin/agent-app
python3 -u agent_app.py
```
**정상 부트 시퀀스 출력 예시**:
```text
==================================================
        Starting Agent Boot Sequence              
==================================================
[Step 1] Loading Environment Variables: [OK]
         AGENT_HOME       = /home/agent-admin/agent-app
         AGENT_PORT       = 15034
         AGENT_UPLOAD_DIR = /home/agent-admin/agent-app/upload_files
         AGENT_KEY_PATH   = /home/agent-admin/agent-app/api_keys
         AGENT_LOG_DIR    = /var/log/agent-app
[Step 2] Validating API Secret Key: [OK]
[Step 3] Checking Upload Directory Permissions: [OK]
[Step 4] Checking Log Directory Permissions: [OK]
[Step 5] Binding Port 15034 (0.0.0.0:15034): [OK]
==================================================
Agent READY
==================================================
[*] Agent application is now running on 0.0.0.0:15034
```

### ② 관제 스크립트(`monitor.sh`) 실행
```bash
# 단발성 헬스체크 및 리소스 확인
/home/agent-admin/agent-app/bin/monitor.sh

# 백그라운드 1초 주기 연속 관제 로그 기록
nohup bash -c 'while true; do /home/agent-admin/agent-app/bin/monitor.sh; sleep 1; done' > /dev/null 2>&1 &

# 관제 로그 실시간 모니터링
tail -f /var/log/agent-app/monitor.log
```

---

## 7. 장애 시나리오별 터미널 트리거 및 관제 명령어

### 🚨 시나리오 A: Memory Leak & OOM Crash 재현
1. **임계치 낮게 설정 (Before: 60MB)**
   ```bash
   export MEMORY_LIMIT=60
   python3 -u agent_app.py > /var/log/agent-app/app.log 2>&1 &
   AGENT_PID=$!
   ```
2. **메모리 증가 및 OOM 모니터링**
   ```bash
   # RSS 메모리 변화 실시간 관측
   watch -n 1 "ps -o pid,user,%cpu,%mem,rss,vsz,command -p $AGENT_PID"
   
   # 종료 로그 확인
   tail -f /var/log/agent-app/app.log | grep -E "Memory limit|SELF-TERMINATED"
   ```
3. **임계치 완화 조치 (After: 200MB)**
   ```bash
   export MEMORY_LIMIT=200
   python3 -u agent_app.py > /var/log/agent-app/app.log 2>&1 &
   # 생존 시간 대폭 연장 및 Before/After 비교 수치 수집
   ```

### ⚡ 시나리오 B: CPU Spike & Watchdog 재현
1. **CPU 임계치 설정 (Before: 30%)**
   ```bash
   export CPU_MAX_OCCUPY=30
   python3 -u agent_app.py > /var/log/agent-app/app.log 2>&1 &
   ```
2. **CPU 점유율 급상승 및 Watchdog 확인**
   ```bash
   # CPU 점유율 추적
   top -p $(pgrep -f agent_app.py)
   
   # Watchdog 종료 로그 확인
   grep -i "WATCHDOG" /var/log/agent-app/app.log
   ```
3. **임계치 완화 조치 (After: 90%)**
   ```bash
   export CPU_MAX_OCCUPY=90
   # 프로세스 생존 및 정상 유지 확인
   ```

### 🔒 시나리오 C: Deadlock (교착 상태) 진단
1. **멀티스레드 활성화 (Before: 데드락 재현)**
   ```bash
   export MULTI_THREAD_ENABLE=true
   python3 -u agent_app.py > /var/log/agent-app/app.log 2>&1 &
   DEADLOCK_PID=$(pgrep -f agent_app.py)
   ```
2. **무응답 상태 증명 명령어**
   ```bash
   # 1) PID는 여전히 살아있음 확인
   ps -ef | grep agent_app.py
   
   # 2) CPU/메모리 변화 정체(0%) 확인
   top -b -n 1 -p $DEADLOCK_PID
   
   # 3) 스레드 상태(futex_wait, 락 대기) 확인
   ps -eLf | grep $DEADLOCK_PID
   
   # 4) 마지막 멈춘 로그 지점 확인
   tail -n 20 /var/log/agent-app/app.log
   ```
3. **회피 조치 (After: 단일 스레드 안전 모드)**
   ```bash
   export MULTI_THREAD_ENABLE=false
   # 데드락 발생 없이 안정적 루프 구동 확인
   ```

---
*본 가이드는 과제 진행 과정에서 실행되는 모든 터미널 명령어와 시스템 상태를 기록하며, 향후 검증 스크립트(`verify_requirements.py`)와 100% 동기화됩니다.*
