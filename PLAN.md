# 📋 [Step 1] 프로젝트 설계 및 실행 계획서 (`PLAN.md`)

> **과제명:** Codyssey B4-02 — 리눅스 시스템 장애(OOM, CPU Spike, Deadlock) 실전 트러블슈팅 및 이슈 리포팅  
> **기준 문서:** `코디세이-b4-02.md`, `PROJECT_WORKFLOW_PROMPT_TEMPLATE.md`  
> **핵심 전환점:** 기존의 자체 Python 시뮬레이션(`src/agent_leak_app.py`) 방식에서 벗어나, **과제 공식 배포 바이너리(`agent-app-leak/agent-leak-app-x86`)를 실제 WSL2 Ubuntu-22.04 리눅스 환경에서 직접 구동·관제하여 실측 로그와 증거를 확보하는 정석 방식**으로 처음부터 다시 수행합니다.

---

## 1. 과제 요구사항 및 제약사항 분해 (`코디세이-b4-02.md` 기준)

### 1.1 사전 준비 및 실행 환경 조건
| 항목 | 필수 조건 | 본 프로젝트 적용 설계 |
| :--- | :--- | :--- |
| **실행 OS** | 제공된 바이너리 실행 가능한 리눅스 | Windows WSL2 `Ubuntu-22.04` (`x86_64`) |
| **대상 바이너리** | 공식 제공 바이너리 (`리버스 엔지니어링 금지`) | `agent-app-leak/agent-leak-app-x86` |
| **실행 계정** | `root`가 아닌 일반 사용자 | `agent-admin` (또는 일반 UID 계정, `root` 실행 차단) |
| **필수 환경변수** | `AGENT_HOME`, `AGENT_PORT=15034`, `AGENT_UPLOAD_DIR`, `AGENT_KEY_PATH`, `AGENT_LOG_DIR` | `scripts/setup_environment.sh`로 일괄 구성 및 검증 |
| **장애 제어 변수** | `MEMORY_LIMIT` (50~512 MB), `CPU_MAX_OCCUPY` (10~100 %), `MULTI_THREAD_ENABLE` (`true`/`false`) | 단일 변인 통제 원칙으로 1개씩 변경하며 Before & After 실험 |
| **보안 키 & 네트워크** | `$AGENT_KEY_PATH/secret.key` (`agent_api_key_test`), `0.0.0.0:15034` 바인딩 | 부트 시퀀스 전 포트 충돌 정리 및 키 파일 자동 생성 |
| **사용 도구 제약** | `monitor.sh`, `ps`, `top`, `htop`, `pstree`, `kill` 등 리눅스 표준 도구 | 디컴파일/역공학 절대 금지, 표준 관제 도구로만 진단 |

### 1.2 케이스별 필수 증거 및 실험 계획
1. **Case 1: OOM / Memory Leak**
   - **증거 1:** `monitor.sh` 관제 로그 (시간 경과에 따른 RSS 메모리 상승 추이)
   - **증거 2:** `app.log` 종료 직전/직후 핵심 로그 (`Memory limit exceeded`, `SELF-TERMINATED`)
   - **증거 3:** `MEMORY_LIMIT` 변경 전후 비교 (예: `128MB` / `256MB` → `512MB` 상향 시 생존 시간 및 동작 변화 실측)
2. **Case 2: CPU 과점유 & Watchdog**
   - **증거 1:** `top` / `ps` / `monitor.sh`의 CPU 급상승 구간 관측
   - **증거 2:** `app.log` 종료 로그 (`WATCHDOG`, `SIGTERM`)
   - **증거 3:** `CPU_MAX_OCCUPY` 변경 전후 비교 (공식 바이너리의 실제 동작 특성에 맞춰 임계치 변경 전후 생존/쿨다운/종료 여부 실측)
3. **Case 3: Deadlock (교착 상태)**
   - **증거 1:** `ps -ef | grep agent-leak-app`로 PID 생존 증명
   - **증거 2:** `top -H` 또는 `ps -eLf` / `ps -L`로 CPU/MEM 변화 정체 및 스레드 대기 상태(`futex` 등) 확인
   - **증거 3:** `app.log` 마지막 멈춘 지점 + `monitor.sh`의 로그 정체 시간(`LOG_IDLE`) 확인
   - **증거 4:** `MULTI_THREAD_ENABLE` (`true` → `false`) 전환 전후 비교

---

## 2. 7단계 표준 워크플로우 마일스톤 (`PROJECT_WORKFLOW_PROMPT_TEMPLATE.md` 준수)

| 단계 | 수행 내용 | 주요 산출물 |
| :--- | :--- | :--- |
| **Step 1. PLAN** | 요구사항 분해, 공식 바이너리 기반 아키텍처 및 실험 설계 (**현재 단계**) | `PLAN.md` (승인 대기) |
| **Step 2. BUILD** | WSL2 환경 구축 스크립트 및 공식 바이너리 전용 관제/실험 스크립트 구현 (`monitor.sh`, 환경 세팅, 3대 실험 자동화) | `scripts/setup_environment.sh`, `scripts/monitor.sh`, `scripts/run_experiments.sh` |
| **Step 3. TEST & LIVE RUN** | 1) 스크립트 문법/로직 Mock 단위 테스트(`tests/test_monitor_and_parser.py`)<br>2) **실제 WSL2에서 `agent-leak-app-x86` 구동하여 3대 장애 실측 로그 확보** | `tests/test_*.py`, `logs/real_*.log`, `experiment_results/*.json` |
| **Step 4. AUDIT & DIAGRAMS** | `코디세이-b4-02.md` 전문 100% 수록 + 요구사항 1:1 매핑표 + 주니어 일상 비유 + `matplotlib` 고해상도 PNG 다이어그램 생성 (**상대경로 `diagrams/*.png` 임베딩**) | `스터디.md`, `scripts/generate_diagrams_matplotlib.py`, `diagrams/*.png` |
| **Step 5. REFINE & REPORT** | 실측 로그 기반 **GitHub Issue 리포트 3건** + 종합 `REPORT.md` + 평가자 원클릭 검증 러너(`scripts/verify_requirements.py`) + `README.md` 평가자 시연 가이드 | `issues/01_oom_crash_issue.md`, `issues/02_cpu_latency_issue.md`, `issues/03_deadlock_issue.md`, `REPORT.md`, `README.md` |
| **Step 6. NOTEBOOKLM** | 핵심 스크립트/문서 소스 통합(`NOTEBOOKLM_FULL_SOURCE.txt`), 빌더 스크립트, 최상단 업로드 체크리스트 포함 `NOTEBOOKLM_GUIDE.md` | `NOTEBOOKLM_FULL_SOURCE.txt`, `scripts/build_notebooklm_source.py`, `NOTEBOOKLM_GUIDE.md` |
| **Step 7. 2-TIER COMMENTS** | 우리가 작성한 모든 `.sh`, `.py` 스크립트 전 라인에 `[1차: 기술 설명]` + `[2차: 주니어 일상 비유]` 2단 주석 적용 (기존 코드 100% 보존) | `scripts/*.sh`, `scripts/*.py` |

---

## 3. 모듈 및 디렉터리 설계 (Step 2에서 구현할 대상)

* **`scripts/setup_environment.sh`**: WSL2 일반 사용자(`agent-admin`) 확인, `/var/log/agent-app` 및 `$AGENT_HOME` 디렉터리 권한 구성, `secret.key` 생성, `agent-leak-app-x86` 배치 및 실행 권한(`+x`) 부여, 15034 포트 사전 정리.
* **`scripts/monitor.sh`**: `pgrep`으로 최신 `agent-leak-app-x86` PID 추적, `ps`로 `RSS(MB)`, `%CPU`, `%MEM`, `STAT` 수집, `stat -c %Y`로 로그 정체 시간(`LOG_IDLE`) 계산 후 `monitor.log` 기록.
* **`scripts/run_experiments.sh`**: WSL2 내부에서 `MEMORY_LIMIT`, `CPU_MAX_OCCUPY`, `MULTI_THREAD_ENABLE`을 단일 변인 통제 방식으로 바꿔가며 **실제 `agent-leak-app-x86`을 실행**하고 Before/After 실측 로그와 JSON 요약을 `experiment_results/`에 저장.
* **`tests/test_monitor_and_parser.py`**: 실제 리눅스 프로세스 없이도 로그 파싱, 임계치 판정, 예외 케이스(프로세스 다운, 인자/인코딩 처리)를 0.1초 내에 검증하는 `unittest` + `mock` 테스트.

---

> **승인 요청:** 위 **Step 1 계획(`PLAN.md`)** 대로 **공식 바이너리(`agent-leak-app-x86`)를 WSL2 `Ubuntu-22.04`에서 직접 실행하는 정석 방식**으로 Step 2부터 진행할까요?

