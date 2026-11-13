# 🧩 핵심 코드 & 명령어 마스터 가이드 (`KEY_CODES_GUIDE.md`)

> 이 프로젝트의 핵심 코드 7가지를 **모든 줄 단위**로 쪼개어  
> * `# [1차-단어]:` 해당 줄에 쓰인 명령어, 옵션, 기호, 변수 뜻을 **단어 하나하나** 전부 풀고,  
> * `# [2차-직관]:` 그래서 이 한 줄이 **직관적으로 뭘 하는 코드인지** 설명한 가이드입니다.

---

## 1. 일반 사용자(Non-root) 검증 & 포트 15034 정리
* **위치:** [`scripts/setup_environment.sh`](scripts/setup_environment.sh)

```bash
# [1차-단어]: if=만약, [ ]=조건검사, "$(id -u)"=현재사용자번호(UID)실행결과, -eq=같다(equal), 0=root관리자번호, ; then=그러면
# [2차-직관]: 지금 실행한 사람이 최고 관리자(root, 0번)인지 확인합니다.
if [ "$(id -u)" -eq 0 ]; then
    # [1차-단어]: echo=화면에글자출력, "[ERROR]..."=에러안내문구
    # [2차-직관]: root로 실행하면 안 된다는 안내 문구를 화면에 띄웁니다.
    echo "[ERROR] root 계정으로 실행할 수 없습니다. 일반 사용자(agent-admin)로 실행하세요."
    # [1차-단어]: exit=스크립트즉시종료, 1=실패(에러)종료코드
    # [2차-직관]: 더 이상 진행하지 않고 실패 상태로 프로그램을 멈춥니다.
    exit 1
# [1차-단어]: fi=if문을끝냄(if를거꾸로쓴단어)
# [2차-직관]: root 검사 블록을 닫습니다.
fi

# [1차-단어]: ss=소켓상태조회명령어, -t=TCP, -l=대기중(LISTEN), -p=프로세스정보, -n=숫자포트표시, 2>/dev/null=에러메시지버림, |=앞결과를뒤로넘김, grep=글자찾기, -q=화면출력없이찾았는지만확인, ":${AGENT_PORT} "=15034포트문자열
# [2차-직관]: 현재 리눅스에서 15034번 포트를 이미 쓰고 있는 프로그램이 있는지 조용히 검사합니다.
if ss -tlpn 2>/dev/null | grep -q ":${AGENT_PORT} "; then
    # [1차-단어]: fuser=파일/포트사용중인프로세스찾기, -k=죽이기(kill), "${AGENT_PORT}/tcp"=15034번TCP포트, 2>/dev/null=에러숨김, ||=앞이실패하면뒤실행, true=무조건성공처리
    # [2차-직관]: 15034번 포트를 잡고 있는 옛날 프로그램이 있으면 강제로 꺼서 문을 비워줍니다.
    fuser -k "${AGENT_PORT}/tcp" 2>/dev/null || true
    # [1차-단어]: sleep=잠시대기, 0.5=0.5초
    # [2차-직관]: 포트가 완전히 닫힐 때까지 0.5초만 기다려 줍니다.
    sleep 0.5
# [1차-단어]: fi=if문종료
# [2차-직관]: 포트 정리 블록을 닫습니다.
fi
```

---

## 2. 실행 중인 프로세스 PID 찾기 & 다운 감지
* **위치:** [`scripts/monitor.sh`](scripts/monitor.sh)

```bash
# [1차-단어]: PID=변수이름, "$(...)"=안쪽명령실행결과를문자열로저장, pgrep=프로세스ID찾기, -n=가장최신(newest)1개, -f=전체명령줄기준검색, "${TARGET_PATTERN}"=찾을이름, ||=실패시, true=빈값으로무사통과
# [2차-직관]: 현재 살아있는 agent-leak-app-x86의 최신 프로세스 번호(PID)를 찾아 변수에 담습니다.
PID="$(pgrep -n -f "${TARGET_PATTERN}" || true)"

# [1차-단어]: if=만약, -z=문자열길이가0(비어있음), "${PID}"=방금찾은PID변수, ; then=그러면
# [2차-직관]: PID가 비어있다면, 즉 프로그램이 이미 죽어서 꺼졌는지 확인합니다.
if [ -z "${PID}" ]; then
    # [1차-단어]: echo=문자출력, [${NOW_STR}]=현재시각, PROCESS:down=프로세스꺼짐표시, TARGET:...=대상앱이름, >>=기존파일끝에이어쓰기, "${MONITOR_LOG}"=monitor.log경로
    # [2차-직관]: 앱이 죽었다는 사실("PROCESS:down")을 관제 로그 파일 맨 끝에 한 줄 남깁니다.
    echo "[${NOW_STR}] PROCESS:down TARGET:${TARGET_PATTERN}" >> "${MONITOR_LOG}"
    # [1차-단어]: exit=종료, 1=프로세스없음(비정상)상태코드
    # [2차-직관]: 이미 죽었으므로 CPU/메모리 측정을 안 하고 여기서 관제를 끝냅니다.
    exit 1
# [1차-단어]: fi=if문종료
# [2차-직관]: 다운 감지 블록을 닫습니다.
fi
```

---

## 3. 물리 메모리(RSS), CPU%, 로그 정체 시간(`LOG_IDLE`) 측정
* **위치:** [`scripts/monitor.sh`](scripts/monitor.sh)

```bash
# [1차-단어]: STAT=변수명, ps=프로세스상태조회, -o=출력컬럼지정, stat==상태컬럼만(제목줄생략), -p "${PID}"=특정PID만조회, 2>/dev/null=에러숨김, |=파이프전달, awk '{print $1}'=첫번째단어만공백제거후추출
# [2차-직관]: 해당 PID가 지금 일하는 중(R)인지 자는 중(S)인지 상태 글자만 깔끔하게 뽑아냅니다.
STAT="$(ps -o stat= -p "${PID}" 2>/dev/null | awk '{print $1}')"

# [1차-단어]: CPU_PCT=변수명, pcpu==CPU사용률(%), awk '{print $1}'=숫자만추출
# [2차-직관]: 해당 PID의 현재 CPU 사용률(%) 숫자만 뽑아냅니다.
CPU_PCT="$(ps -o pcpu= -p "${PID}" 2>/dev/null | awk '{print $1}')"

# [1차-단어]: MEM_PCT=변수명, pmem==전체메모리대비사용률(%)
# [2차-직관]: 전체 RAM 중 이 앱이 몇 %를 쓰고 있는지 숫자만 뽑아냅니다.
MEM_PCT="$(ps -o pmem= -p "${PID}" 2>/dev/null | awk '{print $1}')"

# [1차-단어]: RSS_MB=변수명, rss==실제물리메모리(단위:KB), int($1/1024)=1024로나누어정수MB로변환
# [2차-직관]: KB 단위로 나오는 실제 물리 메모리 사용량을 보기 쉽게 MB 단위 정수로 바꿉니다.
RSS_MB="$(ps -o rss= -p "${PID}" 2>/dev/null | awk '{print int($1/1024)}')"

# [1차-단어]: LOG_IDLE=변수명, 0=초기값0초
# [2차-직관]: 로그가 멈춰있는 시간(초)을 기본값 0으로 초기화합니다.
LOG_IDLE=0

# [1차-단어]: if=만약, -f=일반파일이존재하면, "${APP_LOG}"=앱로그파일경로
# [2차-직관]: 앱 로그 파일이 실제로 존재할 때만 멈춘 시간을 계산합니다.
if [ -f "${APP_LOG}" ]; then
    # [1차-단어]: NOW_EPOCH=변수명, date +%s=1970년1월1일부터지금까지의총초(Unix타임스탬프)
    # [2차-직관]: 현재 시각을 초 단위 숫자로 구합니다.
    NOW_EPOCH="$(date +%s)"
    # [1차-단어]: MTIME_EPOCH=변수명, stat -c %Y=파일이마지막으로수정된시각(초), ||=실패시, echo "${NOW_EPOCH}"=현재시각대체
    # [2차-직관]: 앱 로그 파일에 마지막으로 글자가 찍힌 시각을 초 단위 숫자로 구합니다.
    MTIME_EPOCH="$(stat -c %Y "${APP_LOG}" 2>/dev/null || echo "${NOW_EPOCH}")"
    # [1차-단어]: $(( ... ))=산술뺄셈연산, NOW_EPOCH - MTIME_EPOCH=현재초에서수정초를뺌
    # [2차-직관]: 현재 시각에서 마지막 로그 시각을 빼서 "몇 초 동안 로그가 안 찍혔는지" 계산합니다.
    LOG_IDLE=$(( NOW_EPOCH - MTIME_EPOCH ))
# [1차-단어]: fi=if문종료
# [2차-직관]: 파일 존재 확인 블록을 닫습니다.
fi

# [1차-단어]: echo=문자열출력, >> "${MONITOR_LOG}"=monitor.log파일맨끝에한줄추가
# [2차-직관]: 지금까지 모은 시각, PID, 상태, CPU, RSS(MB), MEM%, 로그정체시간을 한 줄로 기록합니다.
echo "[${NOW_STR}] PID:${PID} STAT:${STAT} CPU:${CPU_PCT}% RSS:${RSS_MB}MB MEM:${MEM_PCT}% LOG_IDLE:${LOG_IDLE}s" >> "${MONITOR_LOG}"
```

---

## 4. 백그라운드 실행 + 데드락 3단 증거 자동 채증
* **위치:** [`scripts/run_experiments.sh`](scripts/run_experiments.sh)

```bash
# [1차-단어]: while=동안반복, kill -0 "${app_pid}"=죽이지않고PID가살아있는지만신호0으로확인, 2>/dev/null=에러숨김, ; do=반복시작
# [2차-직관]: 실행한 앱이 아직 살아있는 동안 1초마다 아래 감시 코드를 계속 반복합니다.
while kill -0 "${app_pid}" 2>/dev/null; do
    # [1차-단어]: if=만약, "${elapsed}"=경과초, -ge=크거나같으면(>=), "${max_wait}"=최대대기시간
    # [2차-직관]: 정해진 제한 시간(예: 데드락은 12초)을 다 채웠는지 검사합니다.
    if [ "${elapsed}" -ge "${max_wait}" ]; then
        # [1차-단어]: "${case_name}" = "deadlock_before"=현재실험이름이데드락Before인지비교
        # [2차-직관]: 데드락 실험 중이라면 강제로 끄기 직전에 현장 증거부터 먼저 저장합니다.
        if [ "${case_name}" = "deadlock_before" ]; then
            # [1차-단어]: ps -ef=전체프로세스상세출력, grep "..."=앱이름찾기, grep -v grep=grep자기자신은제외, >=파일로덮어쓰기저장
            # [2차-직관]: 증거 1: "데드락 걸린 프로세스의 PID가 여전히 살아있다"는 화면을 파일로 저장합니다.
            ps -ef | grep "agent-leak-app-x86" | grep -v grep > "${LOG_ARCHIVE_DIR}/${case_name}_ps_ef.txt" || true
            # [1차-단어]: ps -eLf=스레드(LWP)단위까지모두출력, grep "${app_pid}"=해당PID의스레드들만필터
            # [2차-직관]: 증거 2: 프로세스 내부에 스레드 여러 개가 살아있다는 목록을 파일로 저장합니다.
            ps -eLf | grep "${app_pid}" | grep -v grep > "${LOG_ARCHIVE_DIR}/${case_name}_ps_elf.txt" || true
            # [1차-단어]: top -b=화면제어없는배치(텍스트)모드, -n 1=1번만측정, -H=스레드단위, -p "${app_pid}"=해당PID만측정
            # [2차-직관]: 증거 3: 모든 스레드가 CPU 0.0%로 멈춰 잠들어(S) 있다는 스냅샷을 저장합니다.
            top -b -n 1 -H -p "${app_pid}" > "${LOG_ARCHIVE_DIR}/${case_name}_top_h.txt" || true
        # [1차-단어]: fi=내부if문종료
        # [2차-직관]: 데드락 증거 저장 블록을 닫습니다.
        fi
        # [1차-단어]: kill -9=강제종료(SIGKILL, 9번신호), "${app_pid}"=앱PID
        # [2차-직관]: 증거를 다 찍었으니 멈춰있는 앱을 강제 종료시켜 다음 실험으로 넘어갑니다.
        kill -9 "${app_pid}" 2>/dev/null || true
        # [1차-단어]: exit_code=124=타임아웃종료코드기록
        # [2차-직관]: 시간 초과로 종료했다는 표시(124)를 남깁니다.
        exit_code=124
        # [1차-단어]: break=while반복문탈출
        # [2차-직관]: 감시 루프를 빠져나옵니다.
        break
    # [1차-단어]: fi=바깥if문종료
    # [2차-직관]: 제한 시간 체크를 닫습니다.
    fi
    # [1차-단어]: sleep 1=1초대기
    # [2차-직관]: 다음 체크까지 1초 쉽니다.
    sleep 1
    # [1차-단어]: elapsed=$((elapsed + 1))=경과초에1더하기
    # [2차-직관]: 경과 시간을 1초 늘립니다.
    elapsed=$((elapsed + 1))
# [1차-단어]: done=while반복문끝
# [2차-직관]: 감시 반복을 마무리합니다.
done
```

---

## 5. 정규표현식 기반 로그 파싱 (`parse_monitor_log`)
* **위치:** [`scripts/log_analyzer.py`](scripts/log_analyzer.py)

```python
# [1차-단어]: RSS_PATTERN=변수명, re.compile=정규식패턴미리컴파일, r"RSS:(\d+)MB"=RSS:뒤의숫자1개이상(\d+)을그룹으로잡음
# [2차-직관]: 로그 글자 속에서 "RSS:142MB" 같은 부분의 숫자(142)만 쏙 뽑아내는 돋보기를 만듭니다.
RSS_PATTERN = re.compile(r"RSS:(\d+)MB")

# [1차-단어]: CPU_PATTERN=변수명, r"CPU:([0-9.]+)%"=CPU:뒤의소수점포함숫자([0-9.]+)와%를매칭
# [2차-직관]: "CPU:7.0%"에서 소수점 포함 숫자(7.0)만 뽑아내는 돋보기를 만듭니다.
CPU_PATTERN = re.compile(r"CPU:([0-9.]+)%")

# [1차-단어]: IDLE_PATTERN=변수명, r"LOG_IDLE:(\d+)s"=LOG_IDLE:뒤의정수(\d+)와s를매칭
# [2차-직관]: "LOG_IDLE:4s"에서 정체 시간 숫자(4)만 뽑아내는 돋보기를 만듭니다.
IDLE_PATTERN = re.compile(r"LOG_IDLE:(\d+)s")

# [1차-단어]: def=함수정의, parse_monitor_log=함수명, (text: str)=문자열입력, -> dict[str, Any]=딕셔너리반환타입힌트
# [2차-직관]: monitor.log 전체 글자를 받아서 핵심 통계만 딕셔너리로 돌려주는 함수를 선언합니다.
def parse_monitor_log(text: str) -> dict[str, Any]:
    # [1차-단어]: rss_values=리스트변수, [int(m.group(1)) ...]=잡힌1번그룹문자를정수(int)로변환, finditer(text)=문자열전체에서반복탐색
    # [2차-직관]: 로그 전체에 적힌 모든 RSS 숫자를 리스트([2, 17, 28, ...])로 모읍니다.
    rss_values = [int(m.group(1)) for m in RSS_PATTERN.finditer(text)]
    # [1차-단어]: float(m.group(1))=실수(소수점)변환, CPU_PATTERN.finditer(text)=CPU숫자모두탐색
    # [2차-직관]: 로그 전체에 적힌 모든 CPU 사용률 숫자를 소수점 리스트로 모읍니다.
    cpu_values = [float(m.group(1)) for m in CPU_PATTERN.finditer(text)]
    # [1차-단어]: int(m.group(1))=정수변환, IDLE_PATTERN.finditer(text)=LOG_IDLE숫자모두탐색
    # [2차-직관]: 로그 전체에 적힌 모든 로그 정체 시간(초)을 리스트로 모읍니다.
    idle_values = [int(m.group(1)) for m in IDLE_PATTERN.finditer(text)]
    # [1차-단어]: return {...}=결과딕셔너리반환, max(...) if ... else 0=리스트가비어있지않으면최댓값, 비면0반환, "PROCESS:down" in text=해당문구포함여부(True/False)
    # [2차-직관]: 샘플 개수, 최대 메모리, 최대 CPU, 최대 정체 시간, 프로세스 다운 여부를 깔끔한 표(딕셔너리)로 반환합니다.
    return {
        "samples": len(rss_values),
        "peak_rss_mb": max(rss_values) if rss_values else 0,
        "peak_cpu_pct": max(cpu_values) if cpu_values else 0.0,
        "max_log_idle_sec": max(idle_values) if idle_values else 0,
        "process_down_detected": "PROCESS:down" in text,
    }
```

