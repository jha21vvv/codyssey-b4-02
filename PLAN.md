# 📋 [PLAN.md] 시스템 장애 분석 및 트러블슈팅 프로젝트 마스터 계획서

> **프로젝트명**: 시스템 장애 분석(OOM Crash / CPU Latency / Deadlock) 및 GitHub Issue 기술 리포팅  
> **기준 과제**: [코디세이-b4-02.md](file:///c:/Users/안재현/Documents/24_code/2609_codyssey/codyssey-b4-02/코디세이-b4-02.md)  
> **표준 템플릿**: [PROJECT_WORKFLOW_PROMPT_TEMPLATE.md](file:///c:/Users/안재현/Documents/24_code/2609_codyssey/codyssey-b4-02/PROJECT_WORKFLOW_PROMPT_TEMPLATE.md)  
> **운영 환경**: WSL2 Ubuntu 22.04 LTS (일반 계정: `agent-admin`, 서비스 경로: `/home/agent-admin/agent-app`)

---

## 1. 프로젝트 개요 및 미션 목표

본 프로젝트는 운영체제 위에서 동작하는 애플리케이션(`agent-leak-app`)의 3대 전형적 시스템 장애(**Memory Leak/OOM**, **CPU Spike/Latency**, **Deadlock**)를 관제 도구(`monitor.sh`, `top`, `ps`, `ss`)를 활용해 실시간으로 탐지하고, 객관적인 로그 데이터를 근거로 원인을 분석하여 현업 수준의 **GitHub Issue 기술 보고서(3건)** 및 **종합 엔지니어링 리포트**를 완성하는 것을 목표로 합니다.

특히 본 과제는 순수 코드 개발 과제와 달리 **가상환경/터미널 환경 설정 및 OS 자원 제어(환경변수, 시그널, 프로세스 모니터링)**가 핵심이므로, **"터미널에서 무엇을 어떻게 세팅하고 실행했는지"를 누구나 재현할 수 있도록 `ENVIRONMENT_SETUP_GUIDE.md`에 단계별로 기록**합니다.

---

## 2. 가상환경 및 인프라 현황 분석

| 구분 | 시스템 현황 및 요구 조건 | 현재 확인 상태 |
| :--- | :--- | :---: |
| **운영체제 / 런타임** | Linux (WSL2 Ubuntu 22.04.5 LTS) / Python 3.10+ | ✅ 준비 완료 |
| **실행 계정** | root가 아닌 일반 사용자 (`agent-admin`, UID 1000) | ✅ 확인 완료 |
| **바이너리/스크립트** | `/home/agent-admin/agent-app/agent_app.py`, `bin/monitor.sh` | ✅ 존재 확인 |
| **필수 환경변수** | `AGENT_HOME`, `AGENT_PORT(15034)`, `AGENT_UPLOAD_DIR`, `AGENT_KEY_PATH`, `AGENT_LOG_DIR` | ⚙️ 셋업 가이드화 |
| **장애 제어 환경변수** | `MEMORY_LIMIT`(50~512MB), `CPU_MAX_OCCUPY`(10~100%), `MULTI_THREAD_ENABLE`(true/false) | ⚙️ 시나리오별 제어 |
| **인증 키 파일** | `$AGENT_KEY_PATH/secret.key` (내용: `agent_api_key_test`) | ⚙️ 생성 및 권한 설정 |
| **네트워크 포트** | `0.0.0.0:15034` 바인딩 가능 여부 | ✅ 확인 완료 |

---

## 3. 표준 7단계 엔지니어링 프로세스

```text
[Step 1. PLAN]
요구사항 분해 및 PLAN.md 작성 (현재 단계)
      │
      ▼
[Step 2. ENVIRONMENT & AUTOMATION SCRIPTS]
가상환경 터미널 실행 기록 가이드(ENVIRONMENT_SETUP_GUIDE.md) 작성 & 장애 재현 자동화 쉘 스크립트 작성
      │
      ▼
[Step 3. EXPERIMENTATION & EVIDENCE ACQUISITION]
3대 장애 시나리오별 실행, Before & After 비교 측정, 모니터링/프로세스/종료 로그 객관적 증거 수집
      │
      ▼
[Step 4. AUDIT & STUDY DOC & DIAGRAMS]
과제 전문 수록, OS 원리(메모리누수/OOM, CPU스케줄링/Watchdog, 데드락 4대조건) 스터디 문서(스터디.md) &
matplotlib 기반 고해상도 아키텍처/장애 매커니즘 다이어그램 PNG 생성 (diagrams/*.png)
      │
      ▼
[Step 5. DETAILED REPORT & 3 GITHUB ISSUES & EVALUATOR RUNNER]
GitHub Issue 형태의 기술 리포트 3건 작성 (issues/*.md) & 종합 REPORT.md & 평가자 원클릭 검증 러너
      │
      ▼
[Step 6. NOTEBOOKLM SOURCE CONSOLIDATION & GUIDE]
이동 학습용 단일 텍스트 통합(NOTEBOOKLM_FULL_DOCS.txt) 및 빌더 스크립트, 팟캐스트 기획서(NOTEBOOKLM_GUIDE.md)
      │
      ▼
[Step 7. 2-TIER COMMENTS INLINE EMBEDDING]
모든 자동화 스크립트 및 환경설정 파일에 [1차: 기술문법] + [2차: 주니어 눈높이 일상비유] 2단 주석 내재화
```

---

## 4. 단계별 세부 수행 계획

### 📍 Step 1. 요구사항 분해 및 PLAN.md (현재 단계)
- 미션 목표 및 제약 조건 분석
- 가상환경(WSL) 인프라 확인 및 작업 프로세스 정립
- 사용자 사전 검토 및 승인 요청

### 📍 Step 2. 가상환경 터미널 셋업 & 자동화 스크립트 구현
- **`ENVIRONMENT_SETUP_GUIDE.md`**:
  - 가상환경 진입 (`wsl -u agent-admin`)
  - 디렉터리 구성 및 권한 설정 (`chmod`, `chown`)
  - `secret.key` 생성 및 검증
  - 필수 환경변수 영구/임시 export 설정
  - 서비스 기동 및 `monitor.sh` 백그라운드 구동 명령어
- **재현/모니터링 자동화 스크립트 (`scripts/`)**:
  - `scripts/setup_environment.sh`: 초기 디렉터리, 키, 환경변수 원클릭 셋업 스크립트
  - `scripts/run_oom_experiment.sh`: `MEMORY_LIMIT` 변경(예: 60MB vs 200MB)에 따른 메모리 증가율 및 종료 시점 자동 수집
  - `scripts/run_cpu_experiment.sh`: `CPU_MAX_OCCUPY` 변경에 따른 CPU 점유율 및 Watchdog SIGTERM 종료 추적
  - `scripts/run_deadlock_experiment.sh`: `MULTI_THREAD_ENABLE` 활성화/비활성화 시 PID/스레드 멈춤 현상 추적

### 📍 Step 3. 3대 장애 실험 및 객관적 증거 데이터 확보
- **Case 1: Memory Leak & OOM Crash**
  - 증거 1: `monitor.sh` 물리 메모리(RSS) 시간에 따른 선형/지수 상승 관제 데이터
  - 증거 2: `Memory limit exceeded`, `SELF-TERMINATED` 메모리 보호 정책(MemoryGuard) 종료 로그
  - 증거 3: `MEMORY_LIMIT` 변경 전후 비교(생존 시간, 최대 메모리 도달 수치) 2회 이상 실행 대조표
- **Case 2: CPU Spike & Latency**
  - 증거 1: `top`, `ps aux --sort=-%cpu` 급상승 구간 수치 및 프로세스 점유율
  - 증거 2: `WATCHDOG… SIGTERM` 시스템 보호 조치 종료 로그 발췌
  - 증거 3: `CPU_MAX_OCCUPY` 조정에 따른 생존 시간 및 프로세스 유지 Before/After 비교표
- **Case 3: Deadlock (교착 상태)**
  - 증거 1: PID 생존(`ps -ef | grep agent_app`), 하지만 CPU/MEM 변동치 0% 정체
  - 증거 2: 스레드 레벨 분석(`ps -eLf` 또는 `top -H -p <PID>`) 대기 상태 식별
  - 증거 3: 마지막 로그 지점(`WAITING… BLOCKED`) 발췌
  - 증거 4: `MULTI_THREAD_ENABLE=false` vs `true` 재현/회피 비교 결과

### 📍 Step 4. 스터디 문서(`스터디.md`) & Matplotlib 아키텍처 다이어그램
- 과제 안내문 전문 100% 수록 및 요구사항 Checklist 1:1 대조
- 3개월 차 주니어를 위한 시스템 핵심 개념의 일상 비유 설명:
  - 메모리 누수 & OOM: "식당 테이블(RAM)에 다 먹은 그릇을 치우지 않고 쌓아두어 결국 손님을 쫓아내는 상황"
  - CPU 스케줄링 & Watchdog: "은행 창구 직원을 1명이 독점하여 다른 손님들의 대기줄이 무한히 늘어나 청원경찰이 제지하는 상황"
  - Deadlock & 4대 조건: "외나무다리에서 마주친 두 염소 / 양손에 젓가락을 들어야 밥을 먹을 수 있는 식사하는 철학자들"
- `scripts/generate_diagrams_matplotlib.py`를 작성하여 `diagrams/` 폴더에 고해상도 PNG 이미지 4장 생성:
  1. `diagrams/01_system_architecture_overview.png`: 가상환경 및 에이전트 구조도
  2. `diagrams/02_oom_memory_leak_mechanism.png`: 메모리 누수 및 임계치 도달 메커니즘
  3. `diagrams/03_cpu_watchdog_mechanism.png`: CPU 과점유 및 Watchdog 감시 주기
  4. `diagrams/04_deadlock_circular_wait.png`: 스레드 간 자원 락 순환 대기 모델

### 📍 Step 5. 3대 GitHub Issue 기술 리포트, 종합 REPORT.md & 평가자 시각적 러너
- **GitHub Issue 표준 템플릿 준수 기술 보고서 3건 작성**:
  - `issues/01_oom_crash_issue.md`: `[Bug] Memory Leak - MemoryGuard 임계치 도달에 따른 프로세스 강제 종료 분석`
  - `issues/02_cpu_latency_issue.md`: `[Bug] CPU Latency - 특정 작업 루프의 CPU 과점유 및 Watchdog SIGTERM 조치 분석`
  - `issues/03_deadlock_issue.md`: `[Bug] Deadlock - 다중 스레드 자원 점유 대기로 인한 프로세스 무응답 상태 분석`
- **종합 엔지니어링 리포트 `REPORT.md`**:
  - 시스템 트러블슈팅 아키텍처 의사결정 및 OS 레벨 분석 총괄
  - 3대 장애 발생 원인, 증거, 해결(Workaround) 및 근본적 코드 수정 제안
- **평가자 시각적 검증 러너 (`scripts/verify_requirements.sh` / `.py`)**:
  - 평가자가 단 한 번의 실행으로 3대 장애의 증거와 환경 상태를 검증할 수 있는 터미널 컬러/테이블 러너
  - `README.md` 최종 섹션에 평가자용 실행 커맨드 및 시각적 출력 결과 수록

### 📍 Step 6. NotebookLM 이동 학습용 통합 텍스트 및 가이드
- `NOTEBOOKLM_FULL_DOCS.txt`: 순수 트러블슈팅 분석, 이슈 리포트, 스크립트 코드 전 파일 통합 텍스트
- `scripts/build_notebooklm_source.py`: 원클릭 소스 통합 빌더
- `NOTEBOOKLM_GUIDE.md`:
  - **문서 최상단 체크리스트 박스에 NotebookLM 업로드 대상 문서 목록 명시**
  - 호스트 2인(시니어 시스템 엔지니어 & 주니어 개발자) 팟캐스트 대화 대본 및 청취 핵심 포인트 수록
  - Customize Audio Overview 전용 프롬프트 수록

### 📍 Step 7. 전 라인 1차/2차 2단 주석 내재화
- 작성된 모든 쉘 스크립트 및 파이썬 검증 스크립트에 대해 기존 코드를 100% 보존하면서:
  - `[1차]`: 기술적/문법적 리눅스 명령어 및 파이썬 문법 설명
  - `[2차]`: 3개월 차 주니어 눈높이의 쉬운 일상 비유 해설 주석 추가

---

## 5. 최종 산출물 디렉터리 구조

```text
codyssey-b4-02/
├── PLAN.md                               # [Step 1] 마스터 계획서
├── ENVIRONMENT_SETUP_GUIDE.md            # [Step 2] 가상환경 터미널 설정 및 실행 기록부
├── 스터디.md                             # [Step 4] 과제 전문 수록, 요구사항 대조, OS 원리 스터디
├── REPORT.md                             # [Step 5] 종합 세부 엔지니어링 트러블슈팅 리포트
├── README.md                             # [Step 5] 평가자 실행 가이드 및 프로젝트 메인 문서
├── NOTEBOOKLM_GUIDE.md                   # [Step 6] 팟캐스트 기획서 (업로드 목록 최상단 수록)
├── NOTEBOOKLM_FULL_DOCS.txt              # [Step 6] NotebookLM 업로드용 단일 통합 텍스트
├── issues/                               # [Step 5] GitHub Issue 형태 기술 리포트 (3건)
│   ├── 01_oom_crash_issue.md
│   ├── 02_cpu_latency_issue.md
│   └── 03_deadlock_issue.md
├── diagrams/                             # [Step 4] Matplotlib 생성 고해상도 아키텍처 다이어그램 (.png)
│   ├── 01_system_architecture_overview.png
│   ├── 02_oom_memory_leak_mechanism.png
│   ├── 03_cpu_watchdog_mechanism.png
│   └── 04_deadlock_circular_wait.png
└── scripts/                              # [Step 2~7] 자동화 스크립트 및 평가자 러너
    ├── setup_environment.sh              # 가상환경 원클릭 설정 쉘 스크립트
    ├── run_oom_experiment.sh             # OOM 실험 및 데이터 수집 스크립트
    ├── run_cpu_experiment.sh             # CPU 과점유 실험 스크립트
    ├── run_deadlock_experiment.sh        # Deadlock 진단 스크립트
    ├── generate_diagrams_matplotlib.py   # 다이어그램 생성 파이썬 스크립트
    ├── verify_requirements.py            # 평가자 시각적 원클릭 검증 러너
    └── build_notebooklm_source.py        # NotebookLM 텍스트 빌더
```

---

## 6. 승인 요청 및 다음 단계 안내

위 계획서는 사용자의 요청사항인 **"터미널/가상환경 설정 업무의 단계별 기록"**과 **"PROJECT_WORKFLOW_PROMPT_TEMPLATE의 7단계 엄격 적용"**을 완벽히 반영하여 설계되었습니다.

본 계획서 승인 시, 즉시 **Step 2 (가상환경 터미널 셋업 & 실행 기록 가이드 `ENVIRONMENT_SETUP_GUIDE.md` 및 자동화 스크립트 구축)**로 진입하겠습니다.
