# [Bug] CPU Latency - CPU 과점유 및 Watchdog SIGTERM 비상 종료 분석

## 1. Description (현상 설명)
- **어떤 현상이 발생했는가?**  
  공식 바이너리 `agent-leak-app-x86` 실행 중 `[CpuWorker]`의 내부 연산 부하가 점진적으로 상승하여 `50.56%`에 도달한 순간, `CPU Threshold Violated!` 메시지와 함께 프로세스가 `SIGTERM`(`exit 143`)으로 강제 종료되었습니다.
- **언제, 어떤 조건에서 발생했는가?**  
  `MEMORY_LIMIT=512`, `CPU_MAX_OCCUPY=80`, `MULTI_THREAD_ENABLE=false` 조건에서 부팅 시 `[ WARNING: Recommend Under 50% ]` 경고와 함께 과부하 시나리오가 실행되며 약 **38초** 만에 종료되었습니다.

---

## 2. Evidence & Logs (증거 자료)

### ① 프로그램 실행 로그 (`logs/cpu_before_app.log` & `cpu_before_stdout.log` 실측 발췌)
```log
 [ CPU    ] Limit: 80%  		[ WARNING: Recommend Under 50% ]
...
2026-11-13 16:50:11,878 [INFO] [CpuWorker] Started. Maximum CPU Limit: 80%
2026-11-13 16:50:11,881 [INFO] [CpuWorker] Current Load: 5.00%
2026-11-13 16:50:24,351 [INFO] [CpuWorker] Current Load: 32.22%
2026-11-13 16:50:36,842 [INFO] [CpuWorker] Current Load: 41.46%
2026-11-13 16:50:46,200 [INFO] [CpuWorker] Current Load: 50.56%
2026-11-13 16:50:46,303 [CRITICAL] [CpuWorker] CPU Threshold Violated! (50.56%).
```

### ② 관제 로그 (`logs/cpu_before_monitor.log` 실측)
```text
[2026-11-13 16:50:09] PID:1408 STAT:R+ CPU:5.0% RSS:2MB MEM:0.0% LOG_IDLE:0s
...
[2026-11-13 16:50:46] PID:1432 STAT:SN+ CPU:0.2% RSS:17MB MEM:0.4% LOG_IDLE:0s
[2026-11-13 16:50:47] PROCESS:down TARGET:agent-leak-app-x86
```

---

## 3. Root Cause Analysis (원인 분석)
1. **CPU 부하 누적 및 안전 상한선(50%) 초과:** `CPU_MAX_OCCUPY=80` 설정으로 인해 `[CpuWorker]`가 50%를 넘는 부하(`50.56%`)까지 치솟았고, 시스템 전체 응답성 저하를 막기 위한 내부 안전장치가 작동했습니다.
2. **OS 시그널 동작 (`SIGTERM`, Exit 143):** 프로세스가 임계치를 위반하자 `SIGTERM`(Signal 15, 종료 코드 `128 + 15 = 143`)이 전달되어 프로세스를 즉시 정리했습니다.

---

## 4. Workaround & Verification (조치 및 검증)
- **임시 조치:** `CPU_MAX_OCCUPY`를 `80`%에서 권고 기준 이하인 `30`%로 하향 조정 (`export CPU_MAX_OCCUPY=30`)
- **Before & After 비교 결과 (`experiment_results/cpu_experiment_result.json`):**

| 지표 | Before (`CPU_MAX_OCCUPY=80`) | After (`CPU_MAX_OCCUPY=30`) |
| :--- | :--- | :--- |
| **종료 상태** | 임계치 위반 강제 종료 (`exit 143`) | **Cooldown 진입, 정상 유지** |
| **최고 내부 부하** | **50.56%** (위반) | **30.00%** (`Peak reached -> Cooldown`) |
| **동작 패턴** | 38초 만에 `PROCESS:down` | 30% 도달 시 5%까지 식히며 무중단 순환 |

- **근본적 해결 제안:** 연산 루프 내 `time.sleep` 양보(Yield) 삽입, 무거운 연산의 백그라운드 큐(Celery/Redis) 분리, Linux `cgroups`(`cpu.max`) 기반 하드웨어 자원 격리가 필요합니다.

