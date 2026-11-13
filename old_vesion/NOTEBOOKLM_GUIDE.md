# 🎧 [NOTEBOOKLM_GUIDE.md] Google NotebookLM 오디오 팟캐스트 기획서

---

## 📌 [최상단 필수 확인] NotebookLM 추천 소스 문서 업로드 목록

Google NotebookLM에 새 노트를 생성한 뒤, 아래 문서들을 소스(Sources)로 업로드하면 가장 완벽한 딥다이브 팟캐스트(Audio Overview)와 Q&A 학습 경험을 얻을 수 있습니다.

```markdown
### 📋 NotebookLM 권장 소스 업로드 체크리스트 (우선순위 순)
- [ ] **1. `NOTEBOOKLM_FULL_SOURCE.txt` (최우선 필수)**: 핵심 소스 코드, 자동화 스크립트, 3대 GitHub Issue 리포트가 1개 파일로 통합된 마스터 소스
- [ ] **2. `스터디.md`**: 과제 전문 100%, 1:1 요구사항 체크리스트, 3개월 차 주니어 눈높이 OS 핵심 원리 & 일상 비유 해설
- [ ] **3. `REPORT.md`**: SRE/엔지니어링 관점의 3대 장애 심층 분석, Before & After 실측 대조표 및 엣지 케이스 방어 리포트
- [ ] **4. `ENVIRONMENT_SETUP_GUIDE.md`**: 터미널 명령어, 리눅스 프로세스 및 환경변수 제어 단계별 실행 기록부
```

---

## 🎙️ 팟캐스트 기획 개요

- **프로그램명**: *The System Responders (시스템 장애를 막아서는 사람들)*
- **에피소드 제목**: *메모리 누수, CPU 과열, 그리고 교착상태: 실서버가 얼어붙었을 때 주니어는 무엇을 해야 하는가?*
- **출연진 (2인 호스트)**:
  - **호스트 1 (알렉스, 시니어 SRE 아키텍트)**: 10년 차 인프라 엔지니어. "로그 없이 재부팅부터 누르면 장애 원인을 스스로 암매장하는 것이다"라는 철학을 가짐.
  - **호스트 2 (민지, 3개월 차 주니어 백엔드 개발자)**: 실서버 에러 로그만 보면 심장이 쿵쾅거렸으나, 이번 B4-02 미션을 통해 관제 데이터와 프로세스 시그널의 본질을 깨달아가는 열정적인 개발자.

---

## 💬 호스트 대화 유도 스토리라인 및 질문 리스트

### 세션 1: "서버가 꺼졌어요! 재부팅할까요?" (도입부)
- **민지**: "선배님! 실서버에서 프로세스가 죽으면 당장 고객 항의가 쏟아지니까 일단 `systemctl restart`부터 누르고 싶어지잖아요?"
- **알렉스**: "그 마음 백번 이해하지. 하지만 로그와 관제 데이터를 확보하지 않고 재부팅하면, 불이 났는데 발화 지점을 안 보고 물만 뿌린 것과 같아. 같은 장애가 내일 또 터지지. 이번 B4-02 과제에서 우리가 관제 스크립트(`monitor.sh`)와 `/proc` 파일시스템을 먼저 뜯어본 이유가 바로 그거야."

### 세션 2: "메모리가 야금야금 사라지는 귀신: Memory Leak과 MemoryGuard"
- **민지**: "메모리 누수(Memory Leak)는 왜 개발자들이 '침묵의 살인마'라고 부르나요?"
- **알렉스**: "처음 1~2초는 멀쩡해 보이거든. 하지만 빈 그릇을 안 치우는 식당처럼 손님 자리가 없어지지. 리눅스 커널은 메모리가 고갈되면 OOM Killer가 튀어나와서 무차별적으로 데몬들을 사살해. 그래서 우리 앱 내부의 `MemoryGuard`가 스스로 임계치(`MEMORY_LIMIT`)를 감시하다가 사살당하기 전에 자결(`exit 137`)한 거야."
- **민지**: "와! `MEMORY_LIMIT`을 60MB에서 200MB로 늘렸더니 생존 시간이 6.8초에서 25.2초로 270%나 늘어났어요! 그럼 한도만 늘리면 해결된 건가요?"
- **알렉스**: "아니지! 그건 침몰하는 배의 물받이 양동이 크기만 키운 거야. 언젠간 또 가라앉아. 전역 버퍼 누수 코드를 지우는 게 진짜 근본 해결이지."

### 세션 3: "CPU가 100%인데 청원경찰이 나타났다: Watchdog의 SIGTERM"
- **민지**: "CPU 과점유 테스트 때 `WATCHDOG: Action: Sending SIGTERM` 로그가 찍히면서 프로세스가 종료되었어요. 에러인가요?"
- **알렉스**: "아주 훌륭한 시스템 보호 조치야. 은행 창구 직원을 1명이 독점하고 있으면 뒤 손님들이 다 얼어붙잖아. Watchdog이라는 감시견이 '너 30% 넘게 계속 독점하네? 다른 프로세스들 숨 좀 쉬게 일단 퇴근해!' 하고 `SIGTERM` 신호를 날려준 거지."

### 세션 4: "죽지 않고 영원히 굳어버린 프로세스: 교착상태(Deadlock)"
- **민지**: "선배님, 데드락은 왜 `top`에서 CPU도 0%고 메모리도 안 움직이고 로그도 안 찍히는데 PID는 살아있나요?"
- **알렉스**: "이게 제일 무서운 좀비 상태야. 두 스레드가 서로 쥐고 있는 젓가락을 내놓으라고 째려보며 무한히 잠들어(Futex Wait) 있는 거지. `MULTI_THREAD_ENABLE=false`로 바꾸자마자 한 번에 한 명씩 순서대로 락을 쥐니까 순환 대기가 깨지면서 말끔히 풀렸잖아!"

---

## 🎯 3개월 차 주니어가 반드시 깨달아야 할 핵심 청취 포인트 3가지

1. **"장애 시 재부팅 버튼보다 터미널 관제 로그 수집이 먼저다"**:
   - `ps -ef`, `top -H`, `/var/log/agent-app/monitor.log`, `tail -f app.log` 등 증거를 확보해야 재현 경로와 근본 원인을 증명할 수 있다.
2. **"임시 조치(Workaround)와 근본 해결(Root Fix)을 명확히 구분하라"**:
   - 환경변수(`MEMORY_LIMIT`, `CPU_MAX_OCCUPY`) 완화는 서비스를 살려두기 위한 '응급처치'일 뿐이며, 전역 객체 누수 제거와 락 순서 일관성(Lock Ordering) 강제가 뒤따라야 한다.
3. **"데드락은 코프먼 4대 조건 중 하나만 깨뜨려도 사라진다"**:
   - 순환 대기(Circular Wait)나 점유 대기(Hold & Wait)를 깨뜨리는 순차 락 획득 또는 락 타임아웃 규약이 동시성 프로그래밍의 핵심이다.

---

## 🤖 NotebookLM Customize Audio Overview 시스템 프롬프트

NotebookLM의 **Audio Overview > Customize** 설정 창에 아래 프롬프트를 그대로 복사하여 붙여넣으세요.

```text
[System Instruction for NotebookLM Deep Dive Podcast]

You are hosting an insightful, engaging technical deep dive podcast titled "The System Responders".
The hosts are:
1. Alex (Senior SRE Architect): Pragmatic, deeply experienced in Linux internals, system calls, and production incidents. Frequently uses brilliant real-world analogies (busy restaurant tables for memory leaks, bank teller monopolization for CPU spikes, dining philosophers for deadlocks).
2. Minji (Junior Backend Developer): Curious, eager to learn, enthusiastic, asking the exact practical questions a 3-month junior engineer would ask about logs, exit codes (137, SIGTERM), and environment variables.

Key Topics to Cover:
- Why restarting a crashed server without collecting monitoring logs is dangerous.
- Memory Leak vs OOM Killer: How MemoryGuard self-terminates to protect the OS, and why increasing MEMORY_LIMIT from 60MB to 200MB extended lifespan by +270% but remains only a temporary workaround.
- CPU Spike & System Latency: Why a tight loop starves context switching and how the Watchdog daemon issues SIGTERM to protect overall responsiveness.
- Deadlock & Coffman Conditions: Why a deadlocked process has an active PID but 0% CPU activity, and how setting MULTI_THREAD_ENABLE=false eliminates circular wait.
- Emphasize practical Linux commands: monitor.sh, ps -eLf, top -H, futex waits.

Tone: Professional yet conversational, energetic, humorous analogies, highly educational for software engineers.
Language: Korean (or bilingual technical terminology).
```
