# 🚀 Codyssey B4-02 — 리눅스 시스템 장애 트러블슈팅 (공식 바이너리 실측 기반)

공식 배포 바이너리 **`agent-leak-app-x86`** 을 WSL2 `Ubuntu-22.04` 환경에서 직접 구동·관제하여 **OOM Crash**, **CPU 과점유(Watchdog)**, **Deadlock(교착 상태)** 3대 장애를 재현하고, 표준 리눅스 도구(`monitor.sh`, `ps`, `top -H`, `tail -f`)로 증거를 수집해 GitHub Issue 보고서로 정리한 프로젝트입니다.

---

## 📂 주요 산출물 안내
* **기획서 & 스터디:** [PLAN.md](PLAN.md) | [스터디.md](스터디.md) | [REPORT.md](REPORT.md)
* **GitHub Issue 리포트 3건:**
  * [issues/01_oom_crash_issue.md](issues/01_oom_crash_issue.md) — `MEMORY_LIMIT=128` (`exit 137`) ➔ `512` 정상 유지
  * [issues/02_cpu_latency_issue.md](issues/02_cpu_latency_issue.md) — `CPU_MAX_OCCUPY=80` (`exit 143`) ➔ `30` Cooldown 정상 유지
  * [issues/03_deadlock_issue.md](issues/03_deadlock_issue.md) — `MULTI_THREAD_ENABLE=true` (`BLOCKED`) ➔ `false` 순차 완료
* **관제/실험 스크립트 & 테스트:** `scripts/setup_environment.sh`, `scripts/monitor.sh`, `scripts/run_experiments.sh`, `scripts/log_analyzer.py`, `tests/test_log_analyzer.py`
* **NotebookLM 학습 자료:** [NOTEBOOKLM_GUIDE.md](NOTEBOOKLM_GUIDE.md) | [NOTEBOOKLM_FULL_SOURCE.txt](NOTEBOOKLM_FULL_SOURCE.txt)

---

## 📊 시스템 아키텍처
![시스템 아키텍처](diagrams/01_system_architecture_overview.png)

---

## 🧪 평가자 원클릭 검증 (Windows / Linux 공통)

아래 명령어를 실행하면 모든 필수 문서, 다이어그램, 실측 로그, JSON 결과, 단위 테스트(Mock) 통과 여부를 1초 만에 검증합니다.
```bash
python scripts/verify_requirements.py
```

---

## 🎬 평가자 앞 라이브 시연 가이드 (한 단위씩 복붙 실행)

> **사용법:** 아래 **회색 코드 박스 1개 = 터미널에 한 번 붙여넣고 Enter 치는 단위**입니다.  
> `tail -f`로 로그를 실시간으로 본 뒤에는 반드시 **`Ctrl + C`** 를 눌러 빠져나온 다음, 아래 박스를 순서대로 붙여넣으세요.

---

### 0단계: WSL2 리눅스 접속 및 환경변수 세팅

**① PowerShell에서 WSL 리눅스(`agent-admin`)로 들어가기**
```powershell
wsl -u agent-admin
```

**② 리눅스 프롬프트(`agent-admin@...$`)가 뜨면 경로 이동, 환경변수 설정 및 기존 15034 포트 정리**
```bash
cd /home/agent-admin/agent-app
export AGENT_HOME=/home/agent-admin/agent-app
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR=$AGENT_HOME/upload_files
export AGENT_KEY_PATH=$AGENT_HOME/api_keys
export AGENT_LOG_DIR=/var/log/agent-app
fuser -k 15034/tcp 2>/dev/null || true
pkill -9 -f 'agent_app.py' 2>/dev/null || true
```

---

### 1단계: OOM 크래시 시연 (`MEMORY_LIMIT` 128MB ➔ 512MB)

**① [Before] 128MB 제한으로 실행 → 약 18초 뒤 `MemoryGuard`가 자폭(`exit 137`)하는 모습 보기**
```bash
pkill -9 -f '/agent-leak-app-x86' 2>/dev/null || true
export MEMORY_LIMIT=128 CPU_MAX_OCCUPY=30 MULTI_THREAD_ENABLE=false
: > $AGENT_LOG_DIR/agent_app.log
./agent-leak-app-x86 > /dev/null 2>&1 &
tail -f $AGENT_LOG_DIR/agent_app.log
```
* **👀 나와야 하는 결과:**
  ```text
  [MemoryWorker] Current Heap: 125MB -> 150MB
  [CRITICAL] [MemoryGuard] Memory limit exceeded (150MB >= 128MB)
  [CRITICAL] [MemoryGuard] Self-terminating process ... to prevent system instability.
  ```
* **💬 의미 (평가자 설명용):** 힙 메모리가 25MB씩 계속 쌓이다가 설정 한도(128MB)를 넘자, 리눅스 OS 전체가 뻗기 전에 내부 `MemoryGuard`가 스스로 프로세스를 종료(`exit 137`)했음을 보여줍니다. *(확인 후 **`Ctrl + C`**)*

**② [After] 임시 조치: 512MB로 상향 후 크래시 없이 정상 동작하는 모습 보기**
```bash
pkill -9 -f '/agent-leak-app-x86' 2>/dev/null || true
export MEMORY_LIMIT=512
: > $AGENT_LOG_DIR/agent_app.log
./agent-leak-app-x86 > /dev/null 2>&1 &
tail -f $AGENT_LOG_DIR/agent_app.log
```
* **👀 나와야 하는 결과:**
  ```text
  [INFO] >>> Scenario Selected: [Healthy System Monitoring]
  [INFO] [Scheduler] All tasks completed.
  [INFO] [MemoryWorker] Current Heap: 25MB -> 50MB -> ... (128MB 넘어도 종료 안 됨)
  ```
* **💬 의미 (평가자 설명용):** 메모리 한도를 512MB로 넉넉히 주면 캐시 정리 시점까지 버틸 수 있어 자폭 없이 정상 모니터링 상태로 유지됩니다. *(확인 후 **`Ctrl + C`**)*

---

### 2단계: CPU 과점유 시연 (`CPU_MAX_OCCUPY` 80% ➔ 30%)

**① [Before] 80%로 실행 → 부하가 50%를 넘기며 Watchdog 종료(`CPU Threshold Violated!`) 보기**
```bash
pkill -9 -f '/agent-leak-app-x86' 2>/dev/null || true
export MEMORY_LIMIT=512 CPU_MAX_OCCUPY=80 MULTI_THREAD_ENABLE=false
: > $AGENT_LOG_DIR/agent_app.log
./agent-leak-app-x86 > /dev/null 2>&1 &
tail -f $AGENT_LOG_DIR/agent_app.log
```
* **👀 나와야 하는 결과:**
  ```text
  [INFO] [CpuWorker] Current Load: 5.00% -> 32.22% -> 50.56%
  [CRITICAL] [CpuWorker] CPU Threshold Violated! (50.56%).
  ```
* **💬 의미 (평가자 설명용):** CPU 목표 한도를 80%로 높게 두면 부하가 내부 안전선(50%)을 넘어 치솟고, 약 38초 만에 Watchdog 보호 정책이 작동해 `SIGTERM`(`exit 143`)으로 프로세스를 강제 종료합니다. *(확인 후 **`Ctrl + C`**)*

**② [After] 임시 조치: 권고치 30%로 하향 후 `Cooldown` 모드로 무중단 순환하는 모습 보기**
```bash
pkill -9 -f '/agent-leak-app-x86' 2>/dev/null || true
export CPU_MAX_OCCUPY=30
: > $AGENT_LOG_DIR/agent_app.log
./agent-leak-app-x86 > /dev/null 2>&1 &
tail -f $AGENT_LOG_DIR/agent_app.log
```
* **👀 나와야 하는 결과:**
  ```text
  [INFO] [CpuWorker] Peak reached (30.00%). Starting cooldown...
  [INFO] [CpuWorker] Cooldown complete (5.00%). Resuming load increase...
  ```
* **💬 의미 (평가자 설명용):** 목표치를 권고 기준(30%)으로 낮추면 30%에 닿는 순간 스스로 쿨다운 모드로 들어가 5%까지 부하를 식히므로, Watchdog에 의해 죽지 않고 안정적으로 순환합니다. *(확인 후 **`Ctrl + C`**)*

---

### 3단계: Deadlock 시연 (`MULTI_THREAD_ENABLE` true ➔ false)

**① [Before] `true`로 실행 후 10초 대기 (`Status: BLOCKED`에서 멈춤 유발)**
```bash
pkill -9 -f '/agent-leak-app-x86' 2>/dev/null || true
export MEMORY_LIMIT=512 CPU_MAX_OCCUPY=30 MULTI_THREAD_ENABLE=true
: > $AGENT_LOG_DIR/agent_app.log
./agent-leak-app-x86 > /dev/null 2>&1 &
sleep 10
```
* **👀 나와야 하는 결과:** 10초 동안 조용히 기다린 뒤 다시 입력 프롬프트(`$`)가 돌아옵니다.
* **💬 의미 (평가자 설명용):** 앱이 부팅(2초) 후 스레드 2개를 띄워 서로 교차 락을 잡고 `Status: BLOCKED` 상태에 빠질 때까지 10초를 기다려 준 것입니다.

**② [증거 3단 콤보] 살아있음(`ps -ef`) + CPU 0% 정체(`top -H`) + `BLOCKED` 로그(`tail`) 한 번에 보여주기**
```bash
ps -ef | grep agent-leak-app-x86 | grep -v grep
top -b -n 1 -H -p $(pgrep -n -f '/agent-leak-app-x86')
tail -n 10 $AGENT_LOG_DIR/agent_app.log
```
* **👀 나와야 하는 결과:**
  1. `ps -ef`: `./agent-leak-app-x86` 프로세스(PID)가 **살아있음**
  2. `top -H`: 스레드들의 상태가 `S`(Sleeping)이고 `%CPU`가 **`0.0`으로 멈춰 있음**
  3. `tail`: 두 스레드가 서로의 락(`Shared_Memory_A`, `Socket_Pool_B`)을 기다리며 **`(Status: BLOCKED)`** 를 찍고 멈춤
* **💬 의미 (평가자 설명용):** **"죽지 않았는데(`ps`), 일도 안 하고(`top 0%`), 락 대기에서 멈췄다(`tail BLOCKED`)"** 는 3가지 증거를 조합해 데드락임을 확정 짓는 과정입니다.

**③ [After] 임시 조치: `false`(단일 스레드)로 전환 후 정상 완료되는 모습 보기**
```bash
pkill -9 -f '/agent-leak-app-x86' 2>/dev/null || true
export MULTI_THREAD_ENABLE=false
: > $AGENT_LOG_DIR/agent_app.log
./agent-leak-app-x86 > /dev/null 2>&1 &
tail -f $AGENT_LOG_DIR/agent_app.log
```
* **👀 나와야 하는 결과:**
  ```text
  [INFO] [Thread-A] Task Completed. (100%) -> [Thread-B] -> [Thread-C]
  [INFO] [Scheduler] All tasks completed.
  ```
* **💬 의미 (평가자 설명용):** 멀티스레드 동시 실행을 끄고(`false`) 한 번에 하나씩 순차 처리하도록 바꾸면, 순환 대기 조건이 깨지면서 데드락 없이 모든 작업이 정상 완료됩니다. *(확인 후 **`Ctrl + C`**)*
MULTI_THREAD_ENABLE=false로 바꾸면 작업 3개(Thread-A, Thread-B, Thread-C)를 동시에 출발시키지 않고, 한 번에 하나씩 차례대로 실행합니다.

**④ 시연 종료 후 프로세스 깔끔하게 정리**
```bash
pkill -9 -f '/agent-leak-app-x86' 2>/dev/null || true
```

