# 🧩 핵심 코드 & 명령어 마스터 가이드 (`KEY_CODES_GUIDE.md`)

> 이 프로젝트에서 **"평가자가 질문했을 때 설명할 수 있어야 하고, 실무 트러블슈팅에서도 그대로 써먹는 핵심 코드 7선"** 을 뽑아 자세한 주석과 함께 정리한 문서입니다.

---

## 1. 일반 사용자(Non-root) 검증 & 포트 15034 정리
* **위치:** [`scripts/setup_environment.sh`](scripts/setup_environment.sh)
* **왜 중요한가요?** 과제 필수 조건인 "root 실행 금지"와 "이전 프로세스의 15034 포트 점유 충돌"을 부팅 전에 미리 막아주는 방어 코드입니다.

```bash
# [기술] 현재 실행 중인 사용자의 UID(User ID)가 0(root 관리자)이면 에러를 내고 즉시 종료합니다.
# [비유] 출입문에서 "사장님(root)은 위험하니 들어오실 수 없습니다" 하고 일반 직원(agent-admin)만 통과시키는 경비실입니다.
if [ "$(id -u)" -eq 0 ]; then
    echo "[ERROR] root 계정으로 실행할 수 없습니다. 일반 사용자(agent-admin)로 실행하세요."
    exit 1
fi

# [기술] ss -tlpn으로 15034 TCP 포트를 듣고(LISTEN) 있는 프로세스가 있는지 확인합니다.
# [비유] 우리 가게 출입문(15034호)을 어제 퇴근 안 한 직원이 아직도 잡고 있는지 확인하는 과정입니다.
if ss -tlpn 2>/dev/null | grep -q ":${AGENT_PORT} "; then
    # [기술] 해당 포트를 점유 중인 프로세스를 종료해 다음 실행 시 포트 충돌(Bind Error)을 막습니다.
    fuser -k "${AGENT_PORT}/tcp" 2>/dev/null || true
    sleep 0.5
fi
```

---

## 2. 실행 중인 프로세스 PID 찾기 & 다운 감지
* **위치:** [`scripts/monitor.sh`](scripts/monitor.sh)
* **왜 중요한가요?** `ps -ef | grep ...` 대신 스크립트가 1초마다 자동으로 대상 프로세스의 생존 여부를 판별하는 핵심 로직입니다.

```bash
# [기술] pgrep -n -f: 지정한 패턴(agent-leak-app-x86)과 일치하는 가장 최신(-n) 프로세스 ID(PID)를 찾습니다.
# [비유] 병실 명단에서 지금 막 들어온 환자 번호(PID)를 조회합니다. 없으면 빈 값이 나옵니다.
PID="$(pgrep -n -f "${TARGET_PATTERN}" || true)"

# [기술] -z "${PID}"는 문자열 길이가 0인지(프로세스가 없는지) 검사합니다. 없으면 PROCESS:down을 기록합니다.
# [비유] 병실에 환자가 없으면 차트에 "환자 퇴실(PROCESS:down)"이라고 도장을 찍고 조사를 마칩니다.
if [ -z "${PID}" ]; then
    echo "[${NOW_STR}] PROCESS:down TARGET:${TARGET_PATTERN}" >> "${MONITOR_LOG}"
    exit 1
fi
```

---

## 3. 물리 메모리(RSS), CPU%, 로그 정체 시간(`LOG_IDLE`) 측정
* **위치:** [`scripts/monitor.sh`](scripts/monitor.sh)
* **왜 중요한가요?** OOM(RSS 증가), CPU 스파이크(CPU% 증가), Deadlock(`LOG_IDLE` 증가) 3가지 장애를 **단 한 줄의 로그 포맷**으로 모두 잡아내는 핵심 관제 코드입니다.

```bash
# [기술] ps -o <컬럼>= -p <PID>: 헤더 없이(=) 특정 PID의 상태(stat), CPU%, 메모리%, 실제 물리 메모리(rss, KB)만 추출합니다.
# [비유] 환자 차트에서 불필요한 제목은 빼고 체온(CPU), 혈압(RSS) 숫자만 깔끔하게 뽑아냅니다.
STAT="$(ps -o stat= -p "${PID}" 2>/dev/null | awk '{print $1}')"
CPU_PCT="$(ps -o pcpu= -p "${PID}" 2>/dev/null | awk '{print $1}')"
MEM_PCT="$(ps -o pmem= -p "${PID}" 2>/dev/null | awk '{print $1}')"
# [기술] 리눅스 ps의 rss 단위는 KB이므로 1024로 나누어 정수(int) MB 단위로 변환합니다.
RSS_MB="$(ps -o rss= -p "${PID}" 2>/dev/null | awk '{print int($1/1024)}')"

# [기술] stat -c %Y: 로그 파일의 마지막 수정 시각(Epoch 초)을 구해 현재 시각에서 빼서 '몇 초간 로그가 멈췄는지' 계산합니다.
# [비유] "마지막으로 숨 쉰 지 몇 초 지났나?"를 재는 초시계입니다. 데드락이 걸리면 이 숫자가 계속 커집니다!
LOG_IDLE=0
if [ -f "${APP_LOG}" ]; then
    NOW_EPOCH="$(date +%s)"
    MTIME_EPOCH="$(stat -c %Y "${APP_LOG}" 2>/dev/null || echo "${NOW_EPOCH}")"
    LOG_IDLE=$(( NOW_EPOCH - MTIME_EPOCH ))
fi

echo "[${NOW_STR}] PID:${PID} STAT:${STAT} CPU:${CPU_PCT}% RSS:${RSS_MB}MB MEM:${MEM_PCT}% LOG_IDLE:${LOG_IDLE}s" >> "${MONITOR_LOG}"
```

---

## 4. 백그라운드 실행 + 데드락 3단 증거 자동 채증
* **위치:** [`scripts/run_experiments.sh`](scripts/run_experiments.sh)
* **왜 중요한가요?** 데드락은 프로세스가 스스로 죽지 않기 때문에, 일정 시간(`max_wait`) 동안 멈춰있는 상태를 확인한 뒤 **`ps -ef`, `ps -eLf`, `top -H`** 증거를 자동으로 파일에 저장하고 정리합니다.

```bash
# [기술] kill -0 <PID>: 실제로 죽이지 않고 프로세스가 아직 살아있는지만 1초마다 확인하는 리눅스 관용구입니다.
while kill -0 "${app_pid}" 2>/dev/null; do
    if [ "${elapsed}" -ge "${max_wait}" ]; then
        # [기술] 데드락 실험에서 정지 시점에 도달하면 ps -ef(생존), ps -eLf(스레드), top -H(CPU 0%) 증거를 저장합니다.
        # [비유] 범인이 꼼짝도 안 하고 굳어있을 때 현장의 사진 3장(생존, 스레드, CPU 0%)을 찰칵 찍어 증거로 남깁니다.
        if [ "${case_name}" = "deadlock_before" ]; then
            ps -ef | grep "agent-leak-app-x86" | grep -v grep > "${LOG_ARCHIVE_DIR}/${case_name}_ps_ef.txt" || true
            ps -eLf | grep "${app_pid}" | grep -v grep > "${LOG_ARCHIVE_DIR}/${case_name}_ps_elf.txt" || true
            top -b -n 1 -H -p "${app_pid}" > "${LOG_ARCHIVE_DIR}/${case_name}_top_h.txt" || true
        fi
        # [기술] 증거 확보 후에는 멈춘 프로세스를 강제 종료(SIGKILL, -9)해 다음 실험이 막히지 않게 합니다.
        kill -9 "${app_pid}" 2>/dev/null || true
        exit_code=124
        break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done
```

---

## 5. 정규표현식 기반 로그 파싱 (`parse_monitor_log` & `parse_app_log`)
* **위치:** [`scripts/log_analyzer.py`](scripts/log_analyzer.py)
* **왜 중요한가요?** 수십~수백 줄의 텍스트 로그를 사람이 눈으로 읽는 대신, 정규표현식으로 최댓값과 장애 이벤트 발생 여부를 뽑아내 JSON 보고서로 자동 변환합니다.

```python
# [기술] 정규표현식(re.compile)으로 "RSS:142MB", "CPU:7.0%", "LOG_IDLE:3s" 패턴을 미리 컴파일해 둡니다.
# [비유] 수백 페이지 일기장에서 특정 형광펜 색깔(RSS, CPU, LOG_IDLE)만 골라내는 전용 돋보기입니다.
RSS_PATTERN = re.compile(r"RSS:(\d+)MB")
CPU_PATTERN = re.compile(r"CPU:([0-9.]+)%")
IDLE_PATTERN = re.compile(r"LOG_IDLE:(\d+)s")

def parse_monitor_log(text: str) -> dict[str, Any]:
    # [기술] finditer로 매칭된 모든 숫자를 리스트로 모아 최댓값(peak)을 구합니다. 빈 로그일 땐 0을 반환해 에러를 막습니다.
    rss_values = [int(m.group(1)) for m in RSS_PATTERN.finditer(text)]
    cpu_values = [float(m.group(1)) for m in CPU_PATTERN.finditer(text)]
    idle_values = [int(m.group(1)) for m in IDLE_PATTERN.finditer(text)]
    return {
        "samples": len(rss_values),
        "peak_rss_mb": max(rss_values) if rss_values else 0,
        "peak_cpu_pct": max(cpu_values) if cpu_values else 0.0,
        "max_log_idle_sec": max(idle_values) if idle_values else 0,
        "process_down_detected": "PROCESS:down" in text,
    }
```

---

## 6. Mock 기반 초고속 단위 테스트
* **위치:** [`tests/test_log_analyzer.py`](tests/test_log_analyzer.py)
* **왜 중요한가요?** 리눅스 서버나 바이너리를 매번 1분씩 돌리지 않고도, 파이썬 파서 로직이 정상/빈 입력/한글 경로에서 깨지지 않는지 **0.02초 만에 검증**합니다.

```python
class TestLogAnalyzer(unittest.TestCase):
    def test_parse_monitor_log_normal_and_down(self) -> None:
        # [기술] 실제 파일이나 WSL 실행 없이 가짜(Mock) 로그 문자열을 만들어 파서 함수에 직접 넣어봅니다.
        # [비유] 실제 자동차를 도로에 몰고 나가지 않고, 시뮬레이터 안에서 계기판 숫자만 넣어 정상 작동하는지 0.01초 만에 검사합니다.
        sample = (
            "[2026-11-13 16:47:10] PID:101 STAT:S CPU:1.5% RSS:42MB MEM:0.5% LOG_IDLE:0s\n"
            "[2026-11-13 16:47:11] PID:101 STAT:R CPU:82.4% RSS:128MB MEM:1.6% LOG_IDLE:3s\n"
            "[2026-11-13 16:47:12] PROCESS:down TARGET:agent-leak-app-x86\n"
        )
        parsed = log_analyzer.parse_monitor_log(sample)
        self.assertEqual(parsed["peak_rss_mb"], 128)
        self.assertAlmostEqual(parsed["peak_cpu_pct"], 82.4)
        self.assertTrue(parsed["process_down_detected"])
```

---

## 7. 평가자 원클릭 통합 검증 러너
* **위치:** [`scripts/verify_requirements.py`](scripts/verify_requirements.py)
* **왜 중요한가요?** 평가자가 `python scripts/verify_requirements.py` 한 줄만 쳐서 문서·다이어그램·실측 로그·JSON·단위 테스트 25개 항목의 이상 유무를 한눈에 확인할 수 있게 해주는 마무리 장치입니다.

```python
def run_unit_tests() -> tuple[bool, str]:
    # [기술] subprocess.run으로 현재 파이썬 실행기(sys.executable)를 호출해 tests/ 폴더의 단위 테스트를 자동 실행합니다.
    # [비유] 최종 검수관이 체크리스트 도장을 찍기 전에 테스트 팀을 호출해 "전부 통과했지?" 하고 즉석에서 확인받는 코드입니다.
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, "All unit tests passed"
    return False, proc.stderr.strip() or "Unit tests failed"
```

