# [Bug] OOM Crash - 메모리 누수 및 MemoryGuard 임계치 초과 강제 종료 분석

## 1. Description (현상 설명)
- **어떤 현상이 발생했는가?**  
  WSL2 Ubuntu-22.04 환경에서 공식 바이너리 `agent-leak-app-x86` 실행 중 물리 상주 메모리(RSS)와 힙 사용량이 지속적으로 상승하다가, 약 **18초** 시점에 `MemoryGuard`에 의해 프로세스가 강제 종료(`exit 137`, `SIGKILL`)되었습니다.
- **언제, 어떤 조건에서 발생했는가?**  
  `MEMORY_LIMIT=128`(MB), `CPU_MAX_OCCUPY=30`, `MULTI_THREAD_ENABLE=false` 조건에서 `[MemoryWorker]`가 주기적으로 25MB씩 메모리를 적재할 때 발생했습니다.

---

## 2. Evidence & Logs (증거 자료)

### ① `scripts/monitor.sh` 관제 로그 (`/var/log/agent-app/monitor.log` 실측)
```text
[2026-11-13 16:49:13] PID:409 STAT:R+ CPU:3.0% RSS:2MB MEM:0.0% LOG_IDLE:0s
[2026-11-13 16:49:15] PID:433 STAT:SN+ CPU:3.5% RSS:28MB MEM:0.7% LOG_IDLE:2s
[2026-11-13 16:49:18] PID:433 STAT:SN+ CPU:4.0% RSS:67MB MEM:1.8% LOG_IDLE:0s
[2026-11-13 16:49:21] PID:433 STAT:SN+ CPU:2.8% RSS:92MB MEM:2.5% LOG_IDLE:0s
[2026-11-13 16:49:24] PID:433 STAT:SN+ CPU:2.4% RSS:117MB MEM:3.2% LOG_IDLE:1s
[2026-11-13 16:49:28] PID:433 STAT:SN+ CPU:2.1% RSS:142MB MEM:3.9% LOG_IDLE:1s
[2026-11-13 16:49:31] PROCESS:down TARGET:agent-leak-app-x86
```

### ② 프로그램 실행 로그 (`logs/oom_before_app.log` 실측 발췌)
```log
2026-11-13 16:49:15,525 [INFO] [MemoryWorker] Current Heap: 25MB
2026-11-13 16:49:18,573 [INFO] [MemoryWorker] Current Heap: 50MB
2026-11-13 16:49:21,628 [INFO] [MemoryWorker] Current Heap: 75MB
2026-11-13 16:49:24,675 [INFO] [MemoryWorker] Current Heap: 100MB
2026-11-13 16:49:27,728 [INFO] [MemoryWorker] Current Heap: 125MB
2026-11-13 16:49:30,822 [INFO] [MemoryWorker] Current Heap: 150MB
2026-11-13 16:49:30,824 [CRITICAL] [MemoryGuard] Memory limit exceeded (150MB >= 128MB) / (Recommend Over 256MB)
2026-11-13 16:49:30,826 [CRITICAL] [MemoryGuard] Self-terminating process 433 to prevent system instability.
```

---

## 3. Root Cause Analysis (원인 분석)
1. **메모리 누적 구조:** `[MemoryWorker]`가 힙 메모리에 약 25MB 단위의 데이터를 해제 없이 지속적으로 적재하면서 프로세스 RSS가 선형적으로 증가했습니다.
2. **OS 및 자체 보호 정책 (`MemoryGuard`):** 리눅스 커널의 OOM Killer가 다른 시스템 데몬까지 무차별 종료하는 참사를 막기 위해, 내부 `MemoryGuard`가 `MEMORY_LIMIT(128MB)` 초과(150MB)를 감지하자마자 스스로 프로세스를 종료(`exit 137`, `SIGKILL`)했습니다.

---

## 4. Workaround & Verification (조치 및 검증)
- **임시 조치:** `MEMORY_LIMIT`을 `128`MB에서 `512`MB로 상향 조정 (`export MEMORY_LIMIT=512`)
- **Before & After 비교 결과 (`experiment_results/oom_experiment_result.json`):**

| 지표 | Before (`MEMORY_LIMIT=128`) | After (`MEMORY_LIMIT=512`) |
| :--- | :--- | :--- |
| **종료 상태** | `MemoryGuard` 자폭 (`exit 137`) | 35초 이상 정상 유지 (크래시 없음) |
| **생존 시간** | **18.0초** | **36.0초+ (관측 구간 무중단)** |
| **피크 힙 / RSS** | 150 MB / 142 MB | 275 MB / 292 MB (안정적 진행) |
| **다운 감지** | `PROCESS:down` 발생 | 정상 동작 (`Healthy System Monitoring`) |

- **근본적 해결 제안:** 전역 버퍼 누적 구조를 제거하고 고정 크기 LRU 캐시를 적용하거나, 대용량 데이터는 디스크 임시 파일(`tempfile`) 또는 스트리밍(Streaming)으로 처리해야 합니다.

