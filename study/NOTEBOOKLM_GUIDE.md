# 🎙️ NotebookLM 오디오 오버뷰 & 학습 가이드 (`NOTEBOOKLM_GUIDE.md`)

> **[최상단 필수 체크리스트] Google NotebookLM 업로드 소스 목록**
> NotebookLM(https://notebooklm.google.com) 새 노트북을 만들고 아래 4개 파일을 그대로 업로드하세요. (`.py`/`.sh` 파일은 직접 업로드가 안 되므로 `NOTEBOOKLM_FULL_SOURCE.txt`로 통합되어 있습니다.)
> - [ ] `NOTEBOOKLM_FULL_SOURCE.txt` (핵심 구현 스크립트·코드 통합 텍스트)
> - [ ] `스터디.md` (원본 과제 전문, 1:1 요구사항 대조표, 일상 비유, 다이어그램 설명)
> - [ ] `REPORT.md` (공식 바이너리 `agent-leak-app-x86` 실측 기반 종합 엔지니어링 리포트)
> - [ ] `issues/01_oom_crash_issue.md`, `issues/02_cpu_latency_issue.md`, `issues/03_deadlock_issue.md` (개별 장애 리포트 3건)

---

## 1. 팟캐스트 기획 배경 & 호스트 설정
* **시니어 SRE 아키텍트 (Alex):** 리눅스 커널, `ps`/`top`, 시그널(137/143), 락 경합을 실전 비유로 명쾌하게 풀어주는 멘토.
* **3개월 차 주니어 개발자 (Minji):** "왜 `agent-leak-app-x86`은 `CPU_MAX_OCCUPY`를 낮춰야 안 죽나요?", "데드락은 왜 PID가 살아있는데 CPU가 0%인가요?"처럼 실전 궁금증을 던지는 역할.

---

## 2. 3개월 차 주니어가 반드시 챙겨야 할 청취 포인트 3가지
1. **"장애 시 재부팅보다 증거 수집이 먼저다"**: `ps -ef`, `top -H`, `monitor.log`(`LOG_IDLE`), `tail -f agent_app.log`로 죽은 건지(OOM), 바쁜 건지(CPU), 멈춘 건지(Deadlock)를 먼저 판별해야 합니다.
2. **"임시 조치(환경변수)와 근본 해결(코드/OS 격리)은 다르다"**: `MEMORY_LIMIT`, `CPU_MAX_OCCUPY`, `MULTI_THREAD_ENABLE` 변경은 당장 서비스를 살리는 응급처치일 뿐입니다.
3. **"데드락은 코프먼 4대 조건 중 1개만 깨뜨려도 사라진다"**: 순환 대기(Circular Wait)를 깨는 락 순서 통일(Lock Ordering)과 점유 대기를 깨는 타임아웃 설계가 핵심입니다.

---

## 3. NotebookLM Customize Audio Overview 시스템 프롬프트 (복사용)

```text
[System Instruction for NotebookLM Deep Dive Podcast]

Host an engaging technical podcast in Korean titled "The System Responders".
Characters:
1. Alex (Senior SRE Architect): Explains Linux process monitoring (ps -ef, top -H, ps -eLf, monitor.sh with LOG_IDLE), exit codes 137 (SIGKILL/MemoryGuard) and 143 (SIGTERM/Watchdog), and Coffman deadlock conditions using vivid everyday analogies.
2. Minji (Junior Backend Developer): Asks practical questions from running the real Linux binary agent-leak-app-x86 in WSL2 Ubuntu-22.04—especially why lowering CPU_MAX_OCCUPY from 80% to 30% triggers Cooldown instead of Watchdog SIGTERM, and why deadlocked threads stay alive with 0% CPU.

Key takeaways to emphasize:
- Always collect logs and monitoring metrics before restarting a frozen or crashed service.
- Distinguish temporary environment variable workarounds from root fixes (bounded LRU cache / streaming, time.sleep / Celery / cgroups, Lock Ordering).
Tone: Conversational, clear, encouraging, practical.
```

