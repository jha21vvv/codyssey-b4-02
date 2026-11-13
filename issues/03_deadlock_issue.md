# [Bug] Deadlock - 멀티스레드 역순 락 획득에 따른 영구 교착 상태 분석

## 1. Description (현상 설명)
- **어떤 현상이 발생했는가?**  
  공식 바이너리 `agent-leak-app-x86` 실행 중 두 워커 스레드가 서로 다른 자원을 점유한 채 상대방의 자원을 요청하면서 `Status: BLOCKED` 로그 이후 영구적인 응답 정지(Hang) 상태에 빠졌습니다.
- **언제, 어떤 조건에서 발생했는가?**  
  `MEMORY_LIMIT=512`, `CPU_MAX_OCCUPY=30`, `MULTI_THREAD_ENABLE=true` 조건에서 동시 트랜잭션 처리가 활성화될 때 발생했습니다.

---

## 2. Evidence & Logs (증거 자료)

### ① PID 생존 & 스레드 상태 증거 (`logs/deadlock_before_ps_elf.txt`, `deadlock_before_top_h.txt` 실측)
```text
# ps -eLf 출력 (프로세스 및 3개 스레드가 살아있음)
agent-a+ 3186 3162 3186 0 3 16:51 pts/0 00:00:00 /home/agent-admin/agent-app/agent-leak-app-x86
agent-a+ 3186 3162 3320 0 3 16:51 pts/0 00:00:00 /home/agent-admin/agent-app/agent-leak-app-x86
agent-a+ 3186 3162 3321 0 3 16:51 pts/0 00:00:00 /home/agent-admin/agent-app/agent-leak-app-x86

# top -b -n 1 -H -p <PID> 출력 (CPU 0.0% 정체, Sleeping 상태)
PID  USER      PR  NI  VIRT  RES  SHR S  %CPU %MEM TIME+   COMMAND
3162 agent-a+  20   0  3000 2088 1872 S   0.0  0.1 0:00.09 agent-l+
```

### ② 관제 로그 (`logs/deadlock_before_monitor.log` — `LOG_IDLE` 증가 확인)
```text
[2026-11-13 16:51:34] PID:3186 STAT:SNl+ CPU:0.8% RSS:17MB MEM:0.4% LOG_IDLE:1s
[2026-11-13 16:51:36] PID:3186 STAT:SNl+ CPU:0.8% RSS:17MB MEM:0.4% LOG_IDLE:2s
[2026-11-13 16:51:37] PID:3186 STAT:SNl+ CPU:0.7% RSS:17MB MEM:0.4% LOG_IDLE:3s
[2026-11-13 16:51:38] PID:3186 STAT:SNl+ CPU:0.6% RSS:17MB MEM:0.4% LOG_IDLE:4s
```

### ③ 마지막 실행 로그 (`logs/deadlock_before_app.log` 실측)
```log
2026-11-13 16:51:32,555 [INFO] [AgentWorker][Worker-Thread-1] LOCK ACQUIRED: [Shared_Memory_A]. (Holding...)
2026-11-13 16:51:32,561 [INFO] [AgentWorker][Worker-Thread-2] LOCK ACQUIRED: [Socket_Pool_B]. (Holding...)
2026-11-13 16:51:34,578 [INFO] [AgentWorker][Worker-Thread-1] WAITING for [Socket_Pool_B]... (Status: BLOCKED)
2026-11-13 16:51:34,592 [INFO] [AgentWorker][Worker-Thread-2] WAITING for [Shared_Memory_A]... (Status: BLOCKED)
```

---

## 3. Root Cause Analysis (원인 분석)
1. **역순 락 획득:** `Worker-Thread-1`은 `Shared_Memory_A`를 쥔 채 `Socket_Pool_B`를 기다리고, `Worker-Thread-2`는 `Socket_Pool_B`를 쥔 채 `Shared_Memory_A`를 기다리며 무한 대기에 빠졌습니다.
2. **코프먼 4대 조건 충족:** ① 상호 배제(Mutual Exclusion), ② 점유 대기(Hold & Wait), ③ 비선점(No Preemption), ④ 순환 대기(Circular Wait)가 모두 성립하여 교착 상태가 발생했습니다.

---

## 4. Workaround & Verification (조치 및 검증)
- **임시 조치:** `MULTI_THREAD_ENABLE`을 `true`에서 `false`로 변경하여 단일 스레드 순차 처리로 전환 (`export MULTI_THREAD_ENABLE=false`)
- **Before & After 비교 결과 (`experiment_results/deadlock_experiment_result.json`):**

| 지표 | Before (`MULTI_THREAD_ENABLE=true`) | After (`MULTI_THREAD_ENABLE=false`) |
| :--- | :--- | :--- |
| **프로세스 상태** | PID 생존 + `LOG_IDLE` 지속 증가 (정체) | 정상 순차 실행 (`All tasks completed`) |
| **마지막 로그** | `WAITING ... (Status: BLOCKED)` 후 침묵 | `Thread-A -> B -> C` 순차 완료 후 리소스 모니터링 진입 |
| **메모리/부하 변화** | RSS 17MB 고정 (동결) | RSS 99MB / Load 14.66% 정상 진행 |

- **근본적 해결 제안:** 모든 스레드가 항상 동일한 순서(예: `Shared_Memory_A` → `Socket_Pool_B`)로만 락을 획득하는 **락 순서 통일(Lock Ordering)**을 적용해 순환 대기를 깨뜨리거나, **락 타임아웃(`acquire(timeout=...)`)**을 도입해야 합니다.

