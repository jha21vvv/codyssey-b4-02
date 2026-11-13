# 📑 [REPORT.md] 시스템 장애 분석 및 트러블슈팅 종합 엔지니어링 리포트

> **프로젝트명**: 시스템 장애 분석(OOM Crash / CPU Latency / Deadlock) 및 GitHub Issue 기술 리포팅  
> **기준 과제**: [코디세이-b4-02.md](file:///c:/Users/안재현/Documents/24_code/2609_codyssey/codyssey-b4-02/코디세이-b4-02.md)  
> **표준 템플릿**: [PROJECT_WORKFLOW_PROMPT_TEMPLATE.md](file:///c:/Users/안재현/Documents/24_code/2609_codyssey/codyssey-b4-02/PROJECT_WORKFLOW_PROMPT_TEMPLATE.md)  
> **작성 일자**: 2026-10-17  
> **작성자**: 시스템 엔지니어링 & SRE 태스크포스

---

## 📌 목차
1. [프로젝트 개요 및 엔지니어링 목표](#1-프로젝트-개요-및-엔지니어링-목표)
2. [핵심 아키텍처 및 시스템 제어 설계](#2-핵심-아키텍처-및-시스템-제어-설계)
3. [3대 시스템 장애 분석 및 Before & After 실험 결과](#3-3대-시스템-장애-분석-및-before--after-실험-결과)
   - [Case 1: Memory Leak & OOM Crash (MemoryGuard)](#case-1-memory-leak--oom-crash-memoryguard)
   - [Case 2: CPU Spike & System Latency (Watchdog)](#case-2-cpu-spike--system-latency-watchdog)
   - [Case 3: Deadlock & Concurrency Lock Contention](#case-3-deadlock--concurrency-lock-contention)
4. [엣지 케이스 및 방어 엔지니어링 내역](#4-엣지-케이스-및-방어-엔지니어링-내역)
5. [평가자 시각적 원클릭 검증 체계](#5-평가자-시각적-원클릭-검증-체계)
6. [종합 결론 및 향후 프로덕션 운영 권고사항](#6-종합-결론-및-향후-프로덕션-운영-권고사항)

---

## 1. 프로젝트 개요 및 엔지니어링 목표

실제 프로덕션 서버 환경에서 발생하는 장애의 90% 이상은 하드웨어 결함이 아닌 **애플리케이션의 비정상적 OS 리소스 잠식(메모리 누수, CPU 독점)과 동시성 제어 오류(교착 상태)**에서 기인합니다. 로그와 관제 데이터를 확보하지 않고 재부팅만 수행할 경우 장애 원인이 은폐되고 동일한 재앙이 반복됩니다.

본 프로젝트는 WSL2 Ubuntu 22.04 LTS 환경에서 운영되는 `agent-leak-app`을 대상으로:
1. 관제 스크립트(`bin/monitor.sh`) 및 시스템 도구(`ps`, `top`, `ss`, `lsof`)를 통해 장애 현상을 객관적으로 계측하고,
2. MemoryGuard, Watchdog, Concurrency Control 등 OS 및 애플리케이션 레벨의 보호 정책 동작을 규명하며,
3. 현업 개발팀 및 SRE 조직과의 명확한 협업 커뮤니케이션을 위한 **3건의 GitHub Issue 기술 보고서** 및 **평가자 원클릭 검증 스위트**를 완벽하게 구축하는 것을 목표로 완수되었습니다.

---

## 2. 핵심 아키텍처 및 시스템 제어 설계

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        WSL2 Linux Environment                          │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │  User: agent-admin (UID: 1000, Non-Root Principle)             │   │
│   │                                                                │   │
│   │  ┌──────────────────────────────────────────────────────────┐  │   │
│   │  │ Target Application: agent-leak-app (PID dynamically allocated)│  │   │
│   │  │ Port: 0.0.0.0:15034 [LISTEN]                             │  │   │
│   │  │                                                          │  │   │
│   │  │ ├─ [Thread 1] MemoryGuard Daemon (RSS MB vs MEMORY_LIMIT)│  │   │
│   │  │ ├─ [Thread 2] CPU Watchdog Daemon (%CPU vs CPU_MAX_OCCUPY)│  │   │
│   │  │ ├─ [Threads 3/4] Mutex Lock Alpha/Beta (Deadlock)        │  │   │
│   │  │ └─ [Thread 5] HTTP Socket Health Listener                │  │   │
│   │  └──────────────────────────────────────────────────────────┘  │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                │                                       │
│          Metric Sampling       │ Telemetry & Log Emission               │
│                 ▼              ▼                                       │
│   ┌───────────────────────────┐      ┌─────────────────────────────┐   │
│   │ bin/monitor.sh            │ ───► │ /var/log/agent-app/         │   │
│   │ (Health, Resource, Rotate)│      │ ├─ app.log (Crash Events)   │   │
│   └───────────────────────────┘      │ ├─ monitor.log (Stats)      │   │
│                                      │ └─ experiment_results/ (JSON)│   │
│                                      └─────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 3대 시스템 장애 분석 및 Before & After 실험 결과

### Case 1: Memory Leak & OOM Crash (MemoryGuard)

- **원인 분석**:
  워커 스레드가 0.4초마다 3MB의 버퍼 객체를 전역 리스트에 누적하여 참조 카운트가 해제되지 않고 물리 메모리(RSS)가 선형 증가했습니다.
- **보호 정책 (MemoryGuard)**:
  전체 OS 메모리 고갈로 인한 커널 패닉을 방지하기 위해, 내부 데몬이 `MEMORY_LIMIT` 초과 즉시 `[MemoryGuard] SELF-TERMINATED` 로그를 남기고 `os._exit(137)`로 자결했습니다.
- **Before & After 실측 결과 대조**:
  ```text
  ====================================================================
  Metric               | Before (Limit 60MB) | After (Limit 200MB) | Improvement 
  ---------------------+-----------------+-----------------+-------------
  Survival Duration    | 6.80 s          | 25.19 s         | +270.4%     
  Peak RSS Memory      | 61 MB           | 202 MB          | +141 MB     
  Exit Code            | 137 (SIGKILL)   | 137 (SIGKILL)   | Identical   
  Protection Policy    | MemoryGuard     | MemoryGuard     | Active      
  ====================================================================
  ```

---

### Case 2: CPU Spike & System Latency (Watchdog)

- **원인 분석**:
  타이트 루프(Tight Loop)에서 수학 연산 집약 작업을 sleep 없이 수행하여 CPU 코어를 100% 포화시켰고, 이로 인해 시스템 레이턴시가 폭증했습니다.
- **보호 정책 (Watchdog)**:
  1초 주기로 CPU 사용량을 샘플링하여 `CPU_MAX_OCCUPY(30%)`를 2회 연속 초과하자 즉시 `SIGTERM(15)`을 발송하여 프로세스를 정상 정리(Graceful Shutdown)시켰습니다.
- **Before & After 실측 결과 대조**:
  ```text
  ====================================================================
  Metric                 | Before (Limit 30%) | After (Limit 95%) | Improvement 
  -----------------------+------------------+------------------+-------------
  Process Survival       | Killed by Watchdog | Sustained Stable | RESOLVED    
  Survival Duration      | 2.21 s           | > 4.60 s         | Uninterrupted
  Peak CPU Recorded      | 122 %            | 121 %            | Handled     
  Watchdog Action        | SIGTERM Sent     | No Signal (Safe) | Protected   
  ====================================================================
  ```

---

### Case 3: Deadlock & Concurrency Lock Contention

- **원인 분석**:
  `MULTI_THREAD_ENABLE=true` 상태에서 `Thread-WorkerA`(`Lock Alpha` 점유 -> `Lock Beta` 요청)와 `Thread-WorkerB`(`Lock Beta` 점유 -> `Lock Alpha` 요청)가 서로 상대방의 락을 기다리며 무한 대기 상태에 빠졌습니다.
- **진단 증거**:
  - PID 생존 확인 (`ps -ef`)
  - CPU 및 메모리 변화 0% 완전 정체 확인 (`ps -p <PID> -o %cpu,%mem`)
  - 4개 LWP 스레드가 `futex_wait` 상태에 갇혀 있음 확인 (`ps -eLf`)
  - 마지막 로그 지점: `[Thread-WorkerA] WAITING for lock_beta... BLOCKED`
- **Before & After 실측 결과 대조**:
  ```text
  ====================================================================
  Diagnostic Metric      | Before (Thread=true) | After (Thread=false) | Evaluation  
  -----------------------+----------------------+----------------------+-------------
  Deadlock Condition     | Circular Wait LOCKED | Sequential Avoided   | RESOLVED    
  Process PID Status     | Alive (Frozen)       | Alive (Responsive)   | Healthy     
  Resource Activity      | 0% CPU, 0% MEM Delta | Normal Activity      | Recovered   
  Last Log Event         | WAITING... BLOCKED   | Safe processed       | Smooth      
  ====================================================================
  ```

---

## 4. 엣지 케이스 및 방어 엔지니어링 내역

| 엣지 케이스 항목 | 발생 가능한 취약점 / 장애 | 구현된 방어 로직 및 엔지니어링 조치 |
| :--- | :--- | :--- |
| **Root 실행 시도** | 보안 규정 위반 및 파일 권한 오염 | `os.geteuid() == 0` 검사 시 `[Step 0] Security Check: [FAILED]` 출력 후 즉시 종료 (최소 권한의 원칙 준수) |
| **포트 선점 (Errno 98)** | 이전 인스턴스 미종료로 바인딩 충돌 | `setup_environment.sh`에서 `ss -tlpn` 검사 후 이전 프로세스에 `SIGTERM`을 발송하여 안전 해제 보장 |
| **멀티코어 CPU 정규화** | 멀티코어 환경에서 %CPU 100% 초과 오류 | `get_current_cpu_percent()`에서 `os.cpu_count()`를 나누어 0~100% 표준 환산 정규화 적용 |
| **비밀키 파일 형식 오차** | 개행 문자(\n) 포함 시 키 불일치 실패 | `echo -n "agent_api_key_test"`로 순수 18바이트 파일 생성 및 strip() 비교 방어 |
| **로그 파일 디렉터리 권한** | 쓰기 권한 부재 시 부팅 실패 | `/var/log/agent-app`에 775 권한 부여 및 불가 시 로컬 `${AGENT_HOME}/logs` 폴백(Fallback) 보장 |

---

## 5. 평가자 시각적 원클릭 검증 체계

평가자가 환경 설정부터 3대 장애 재현 및 증거 수집 여부를 단 1회 명령으로 시각적으로 검증할 수 있는 파이썬 러너 [scripts/verify_requirements.py](file:///c:/Users/안재현/Documents/24_code/2609_codyssey/codyssey-b4-02/scripts/verify_requirements.py)를 제작했습니다.

```bash
# 평가자 원클릭 실행 명령어 (PowerShell 또는 WSL)
python scripts/verify_requirements.py
```
- 터미널 ANSI 컬러 및 규격화된 테이블 형태로 성공 여부와 수치를 실시간 출력합니다.
- 평가 검증 결과 JSON(`experiment_results/verification_summary.json`)을 자동 생성합니다.

---

## 6. 종합 결론 및 향후 프로덕션 운영 권고사항

1. **관제와 로깅의 불가분성**:
   단순한 프로세스 생존(PID) 체크만으로는 교착 상태(Deadlock)를 감지할 수 없습니다. 주기적인 리소스 변화율(Delta)과 스레드 LWP 상태를 종합 감시하는 다계층 모니터링이 필수적입니다.
2. **임계치 완화(Workaround)와 근본 해결(Root Cause Fix)의 구분**:
   `MEMORY_LIMIT`이나 `CPU_MAX_OCCUPY` 상향은 서비스 장애 시간을 늦추는 임시방편(Workaround)일 뿐이므로, 전역 버퍼 누수 코드 제거와 락 순서 일관성(Lock Ordering) 강제화가 반드시 코드 레벨에서 병행되어야 합니다.
