# [Bug] Deadlock - 다중 스레드 상호 락 점유 대기로 인한 프로세스 무응답 상태 분석

> **이슈 번호**: #3  
> **장애 유형**: Deadlock (교착 상태) / Thread Starvation / Process Freeze  
> **심각도**: Critical (P1) - 프로세스 생존 상태에서 모든 서비스 무응답 (Zombie State)  
> **영향 범위**: 애플리케이션 전체 스레드 블로킹 및 포트 응답 불능  
> **보고자**: 시스템 엔지니어링팀 트러블슈팅 태스크포스

---

## 1. Description (현상 설명)

- **어떤 현상이 발생했는가?**  
  `agent-leak-app` 프로세스가 종료되지 않고 PID를 유지한 채 정상 생존해 있으나, CPU 사용률이 0%로 떨어지고 메모리 변동도 전혀 없는 완전한 무응답(Frozen/Hang) 상태에 빠졌습니다. 신규 로그 출력이 완전히 정지되었으며, 포트 `15034`로 HTTP 요청을 보내도 응답을 받지 못하고 무한 대기(Timeout)에 걸렸습니다.
- **언제, 어떤 조건에서 발생했는가?**  
  환경변수 `MULTI_THREAD_ENABLE=true`로 멀티스레드 동시성 모드가 활성화된 상태에서 서로 다른 두 작업 스레드가 복수의 공유 락 자원을 교차 획득하려고 할 때 발생했습니다.

---

## 2. Evidence & Logs (증거 자료)

### ① PID 생존 증명 (`ps -ef | grep agent-leak-app`)
프로세스가 크래시되어 죽은 것이 아니라 여전히 OS 프로세스 테이블에 살아있음을 입증:
```bash
ps -ef | grep agent-leak-app
# 출력 결과:
# agent-ad   710   580  0 14:52 pts/0    00:00:00 python3 -u /home/agent-admin/agent-app/agent-leak-app --mode=deadlock
```

### ② CPU/MEM 변화 정체 증거 (`top` / `ps`)
리소스 소비가 0%로 얼어붙어 아무런 작업도 진행하지 못하고 있음을 입증:
```bash
# 1초 간격 2회 측정 샘플링:
ps -p 710 -o %cpu,%mem,time,stat
# 샘플 1: 0.0 %CPU, 0.3 %MEM, TIME: 00:00:00, STAT: Sl
# 샘플 2: 0.0 %CPU, 0.3 %MEM, TIME: 00:00:00, STAT: Sl (완전 정체)
```

### ③ 스레드 레벨 분석 증명 (`ps -eLf` / `top -H`)
프로세스 내부 스레드들이 락 대기 상태에 갇혀 있음을 확인:
```bash
ps -eLf | grep 710 | grep -v grep
# 출력:
# agent-ad   710   580   710  0    4 14:52 pts/0    00:00:00 python3 (메인)
# agent-ad   710   580   712  0    4 14:52 pts/0    00:00:00 python3 (HTTP 리스너)
# agent-ad   710   580   714  0    4 14:52 pts/0    00:00:00 python3 (WorkerA - futex_wait)
# agent-ad   710   580   715  0    4 14:52 pts/0    00:00:00 python3 (WorkerB - futex_wait)
```

### ④ 프로그램 실행 로그 중 마지막 기록 발췌 (`/var/log/agent-app/app.log`)
```log
[2026-10-17 14:52:47] [*] Agent application running on PID 710 on port 15034
[2026-10-17 14:52:47] [*] Operating Mode: DEADLOCK
[2026-10-17 14:52:47] [Deadlock-Manager] MULTI_THREAD_ENABLE=true. Spawning concurrent threads with circular lock dependency...
[2026-10-17 14:52:47] [Thread-WorkerA] Attempting to acquire lock_alpha...
[2026-10-17 14:52:47] [Thread-WorkerA] Acquired lock_alpha. Sleeping 0.5s before requesting lock_beta...
[2026-10-17 14:52:47] [Thread-WorkerB] Attempting to acquire lock_beta...
[2026-10-17 14:52:47] [Thread-WorkerB] Acquired lock_beta. Sleeping 0.5s before requesting lock_alpha...
[2026-10-17 14:52:48] [Thread-WorkerA] WAITING for lock_beta... BLOCKED
[2026-10-17 14:52:48] [Thread-WorkerB] WAITING for lock_alpha... BLOCKED
[ 이후 영구적인 로그 침묵 발생 ]
```

---

## 3. Root Cause Analysis (원인 분석)

1. **기술적 원인 (역순 락 획득 패턴)**:
   - `Thread-WorkerA`는 `lock_alpha`를 획득한 후 `lock_beta`를 요청했습니다.
   - 동시에 `Thread-WorkerB`는 `lock_beta`를 획득한 후 `lock_alpha`를 요청했습니다.
   - 두 스레드가 상대방이 이미 쥐고 있는 락을 해제하기만을 기다리며 무한 대기 상태(Futex Sleep)에 진입했습니다.
2. **관련 OS 동작 원리 (코프먼 4대 조건 만족)**:
   - **상호 배제 (Mutual Exclusion)**: 뮤텍스 락은 오직 한 스레드만 독점 소유할 수 있음.
   - **점유 대기 (Hold and Wait)**: 각 스레드가 락 하나를 점유한 채 다른 락을 요구함.
   - **비선점 (No Preemption)**: 상대방이 쥐고 있는 락을 강제로 빼앗아 올 수 없음.
   - **순환 대기 (Circular Wait)**: WorkerA -> Lock B(WorkerB 소유) -> Lock A(WorkerA 소유)의 순환 고리가 형성됨.
   - 4대 조건이 완벽히 충족됨으로써 교착 상태가 성립되었습니다.

---

## 4. Workaround & Verification (조치 및 검증)

### ① 임시 조치 내용 (Workaround)
- 동시성 충돌을 유발하는 멀티스레드 교차 실행을 방지하기 위해 `MULTI_THREAD_ENABLE` 값을 `false`로 변경하여 단일 스레드 순차 처리 모드로 전환했습니다.
```bash
export MULTI_THREAD_ENABLE=false
```

### ② Before & After 비교 결과 (실측 데이터)

```text
====================================================================
  [Deadlock] Before vs After Verification Comparison Table
====================================================================
진단 지표 (Metric)    | Before (조치 전)             | After (조치 후)              | 개선 결과 (Change)
----------------------+-----------------------------+-----------------------------+-------------------
설정 환경변수         | MULTI_THREAD_ENABLE=true    | MULTI_THREAD_ENABLE=false   | 단일 순차모드 전환
교착 상태 발생 여부   | Circular Wait LOCKED (발생) | Sequential Avoided (미발생) | 장애 해결(RESOLVED)
프로세스 PID 상태     | Alive (완전 정체/동결)      | Alive (정상 응답 지속)      | 정상화 달성
자원 활동성           | CPU 0%, MEM Delta 0%        | 정상 자원 순환 및 해제      | 복구 완료
마지막 로그 지점      | WAITING... BLOCKED          | All locks processed safely  | 원활한 로그 진행
```

### ③ 근본적 해결을 위한 추가 제안 (Root Fix Suggestion)
1. **락 획득 순서의 전역 일관성 강제 (Lock Ordering Protocol)**:
   - 모든 스레드가 복수의 락을 획득할 때 반드시 사전 정의된 순서(예: 항상 `lock_alpha` -> `lock_beta`)로만 획득하도록 규약을 강제하면 **순환 대기(Circular Wait)**가 수학적으로 불가능해집니다.
2. **락 타임아웃 적용 (`try-lock` / `acquire(timeout=...)`)**:
   - 무한정 블로킹되는 `lock.acquire()` 대신, 일정 시간(예: 2초) 내에 락을 획득하지 못하면 기존에 점유하던 락을 모두 반납하고 지수 백오프(Exponential Backoff) 후 재시도하도록 설계해야 합니다.
