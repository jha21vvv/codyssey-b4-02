# [Bug] OOM Crash - MemoryGuard 메모리 임계치 초과로 인한 프로세스 강제 종료 분석

> **이슈 번호**: #1  
> **장애 유형**: Out Of Memory (OOM) / Memory Leak  
> **심각도**: Critical (P1) - 서비스 프로세스 비정상 중단  
> **영향 범위**: `agent-leak-app` 메인 서비스 및 포트 `15034` 연결 끊김  
> **보고자**: 시스템 엔지니어링팀 트러블슈팅 태스크포스

---

## 1. Description (현상 설명)

- **어떤 현상이 발생했는가?**  
  `0.0.0.0:15034` 포트에서 정상적으로 요청을 대기하던 `agent-leak-app` 프로세스가 실행 시작 후 수 초(약 6.8초) 만에 아무런 외부 입력 없이 갑자기 종료되었습니다. 포트 접속 시 `Connection refused` 에러가 발생하며 서비스가 불능 상태에 빠졌습니다.
- **언제, 어떤 조건에서 발생했는가?**  
  기본 환경변수 `MEMORY_LIMIT=60`(MB) 조건 하에서 애플리케이션의 내부 워커가 지속적으로 메모리 버퍼를 할당하는 루프를 수행할 때 발생했습니다.

---

## 2. Evidence & Logs (증거 자료)

### ① `monitor.sh` 관제 로그 데이터 (수치 및 추세)
`bin/monitor.sh` 관제 스크립트 실행 기록(`/var/log/agent-app/monitor.log`):
```text
[2026-10-17 14:50:05] PID:604 CPU:0% MEM:12% DISK_USED:1%
[2026-10-17 14:50:07] PID:604 CPU:0% MEM:18% DISK_USED:1%
[2026-10-17 14:50:09] PID:604 CPU:0% MEM:26% DISK_USED:1%
[2026-10-17 14:50:11] [ERROR] Health Check Failed: Process 'agent-leak-app' is NOT running!
```
- **분석**: 시간 경과에 따라 물리 메모리(MEM%)가 급격히 상승하다가 프로세스가 증발(Evaporated)했습니다.

### ② 프로그램 실행 로그 (`/var/log/agent-app/app.log`) 핵심 구간 발췌
```log
[2026-10-17 14:50:04] [*] Agent application running on PID 604 on port 15034
[2026-10-17 14:50:04] [*] Operating Mode: OOM
[2026-10-17 14:50:04] [MemoryGuard] Started daemon. Upper limit = 60 MB
[2026-10-17 14:50:04] [Worker-Mem] Memory leak worker started. Continuously allocating buffer chunks...
[2026-10-17 14:50:05] [Worker-Mem] Leak iteration 1: Allocated 3MB (Current RSS: 13.45MB)
[2026-10-17 14:50:06] [Worker-Mem] Leak iteration 5: Allocated 15MB (Current RSS: 25.60MB)
[2026-10-17 14:50:08] [Worker-Mem] Leak iteration 10: Allocated 30MB (Current RSS: 41.12MB)
[2026-10-17 14:50:10] [Worker-Mem] Leak iteration 15: Allocated 45MB (Current RSS: 56.78MB)
[2026-10-17 14:50:11] [Worker-Mem] Leak iteration 18: Allocated 54MB (Current RSS: 64.86MB)
[2026-10-17 14:50:11] [MemoryGuard] Memory limit exceeded: current 64.86MB > limit 60MB
[2026-10-17 14:50:11] [MemoryGuard] SELF-TERMINATED by MemoryGuard policy to prevent OS crash
```

### ③ 시스템 도구 출력 결과 (`ps`)
종료 직전 프로세스 메모리 상태:
```bash
ps -o pid,user,%cpu,%mem,rss,vsz,command -p 604
# 출력:
#   PID USER     %CPU %MEM   RSS    VSZ COMMAND
#   604 agent-ad  0.0  0.8 62840 124500 python3 -u agent_leak_app.py
```
- **종료 코드**: `137` (SIGKILL / 128 + 9) 확인.

---

## 3. Root Cause Analysis (원인 분석)

1. **기술적 원인 (Memory Leak)**:
   - 애플리케이션 내부 `run_memory_leak_simulation()` 함수에서 0.4초마다 3MB 크기의 `bytearray`를 전역 참조 리스트 `leak_storage`에 지속적으로 누적(append)하였습니다.
   - 파이썬의 참조 카운팅(Reference Counting) 가비지 컬렉터는 활성 참조가 유지되는 객체를 회수할 수 없으므로, 프로세스의 물리 상주 메모리(RSS)가 선형적으로 무한히 증가했습니다.
2. **관련 OS 동작 원리 및 보호 정책 (MemoryGuard)**:
   - 일반적인 리눅스 환경에서 메모리가 고갈되면 커널 레벨의 **OOM Killer**가 작동하여 시스템의 다른 주요 데몬(SSH, init 등)까지 불특정하게 강제 종료시키는 대형 참사가 발생합니다.
   - 본 애플리케이션은 이러한 시스템 전체 붕괴를 예방하기 위해, 내부 데몬 스레드인 **MemoryGuard**가 `/proc/self/status`의 `VmRSS`를 0.5초마다 감시하다가, `MEMORY_LIMIT` 임계치를 초과하는 순간 프로세스 스스로를 `os._exit(137)`로 안전하게 격리 종료(Self-Termination)시켰습니다.

---

## 4. Workaround & Verification (조치 및 검증)

### ① 임시 조치 내용 (Workaround)
- 환경변수 `MEMORY_LIMIT` 값을 기존 `60`MB에서 `200`MB로 3.3배 상향 조정하여 프로세스의 메모리 허용 한도를 완화했습니다.
```bash
export MEMORY_LIMIT=200
```

### ② Before & After 비교 결과 (실측 데이터)

```text
====================================================================
  [OOM Crash] Before vs After Verification Comparison Table
====================================================================
지표 (Metric)         | Before (조치 전)      | After (조치 후)       | 개선 결과 (Change)
----------------------+----------------------+----------------------+-------------------
설정 환경변수         | MEMORY_LIMIT=60 MB   | MEMORY_LIMIT=200 MB  | +140 MB 상향
프로세스 생존 시간    | 6.80 초              | 25.19 초             | +270.4% 수명 연장
피크 물리 메모리(RSS) | 61 MB                | 202 MB               | 정상 한도 내 허용
종료 사유             | MemoryGuard 초과     | MemoryGuard 초과     | 임계치 완화 확인
종료 코드             | 137 (SIGKILL)        | 137 (SIGKILL)        | 일치
```

### ③ 근본적 해결을 위한 추가 제안 (Root Fix Suggestion)
1. **임시 조치의 한계**: `MEMORY_LIMIT` 상향은 누수가 일어나는 근본 코드를 고친 것이 아니라 "가라앉는 배의 물받이 통 크기를 키운 것"에 불과하므로, 일정 시간이 지나면 결국 다시 OOM이 발생합니다.
2. **근본적 코드 수정**:
   - `leak_storage`와 같은 전역 버퍼 누적 구조를 즉시 제거하고, 요청 처리 완료 후 데이터를 파기하거나 고정 크기의 LRU(Least Recently Used) 캐시로 교체해야 합니다.
   - 대용량 데이터는 메모리가 아닌 디스크 임시 파일(`tempfile`) 또는 스트리밍 방식으로 처리해야 합니다.
