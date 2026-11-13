"""scripts/log_analyzer.py의 로그 파싱 및 JSON 요약 기능을 검증하는 초고속 단위 테스트."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import log_analyzer


class TestLogAnalyzer(unittest.TestCase):
    """모의(Mock) 로그 입력을 통해 파서 및 엣지 케이스를 검증합니다."""

    def test_parse_monitor_log_normal_and_down(self) -> None:
        sample = (
            "[2026-11-13 16:47:10] PID:101 STAT:S CPU:1.5% RSS:42MB MEM:0.5% LOG_IDLE:0s\n"
            "[2026-11-13 16:47:11] PID:101 STAT:R CPU:82.4% RSS:128MB MEM:1.6% LOG_IDLE:3s\n"
            "[2026-11-13 16:47:12] PROCESS:down TARGET:agent-leak-app-x86\n"
        )
        parsed = log_analyzer.parse_monitor_log(sample)
        self.assertEqual(parsed["samples"], 2)
        self.assertEqual(parsed["peak_rss_mb"], 128)
        self.assertEqual(parsed["min_rss_mb"], 42)
        self.assertAlmostEqual(parsed["peak_cpu_pct"], 82.4)
        self.assertEqual(parsed["max_log_idle_sec"], 3)
        self.assertTrue(parsed["process_down_detected"])

    def test_parse_monitor_log_empty(self) -> None:
        parsed = log_analyzer.parse_monitor_log("")
        self.assertEqual(parsed["samples"], 0)
        self.assertEqual(parsed["peak_rss_mb"], 0)
        self.assertEqual(parsed["peak_cpu_pct"], 0.0)
        self.assertFalse(parsed["process_down_detected"])

    def test_parse_app_log_oom_and_flush(self) -> None:
        oom_log = (
            "2026-11-13 16:47:14 [INFO] [MemoryWorker] Current Heap: 130MB\n"
            "2026-11-13 16:47:15 [CRITICAL] [MemoryGuard] SELF-TERMINATED\n"
        )
        parsed_oom = log_analyzer.parse_app_log(oom_log)
        self.assertEqual(parsed_oom["peak_heap_mb"], 130)
        self.assertTrue(parsed_oom["oom_self_terminated"])
        self.assertFalse(parsed_oom["memory_cache_flushed"])

        flush_log = (
            "2026-11-13 16:47:20 [INFO] [MemoryWorker] Current Heap: 517MB\n"
            "2026-11-13 16:47:21 [INFO] Memory Cache Flushed\n"
        )
        parsed_flush = log_analyzer.parse_app_log(flush_log)
        self.assertTrue(parsed_flush["memory_cache_flushed"])

    def test_parse_app_log_cpu_and_deadlock(self) -> None:
        cpu_log = (
            "2026-11-13 16:48:00 [INFO] [CpuWorker] Current Load: 55.51%\n"
            "2026-11-13 16:48:01 [CRITICAL] WATCHDOG: INITIATING EMERGENCY ABORT (SIGTERM)\n"
        )
        parsed_cpu = log_analyzer.parse_app_log(cpu_log)
        self.assertAlmostEqual(parsed_cpu["peak_internal_load_pct"], 55.51)
        self.assertTrue(parsed_cpu["watchdog_sigterm"])

        deadlock_log = (
            "2026-11-13 16:49:00 [WARNING] [Worker-A] waiting for lock_B\n"
        )
        parsed_dl = log_analyzer.parse_app_log(deadlock_log)
        self.assertTrue(parsed_dl["deadlock_detected"])

    def test_summarize_and_save_json_with_korean_path(self) -> None:
        summary = log_analyzer.summarize_experiment_pair(
            experiment_name="oom",
            before_app_log="SELF-TERMINATED\n",
            before_monitor_log="PID:1 STAT:S CPU:1.0% RSS:128MB MEM:1.0% LOG_IDLE:0s\n",
            before_exit_code=137,
            before_duration_sec=17.2,
            after_app_log="Memory Cache Flushed\nAll tasks completed.\n",
            after_monitor_log="PID:2 STAT:S CPU:1.2% RSS:512MB MEM:2.0% LOG_IDLE:0s\n",
            after_exit_code=0,
            after_duration_sec=35.0,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "한글폴더" / "oom_result.json"
            with patch.object(log_analyzer, "save_json_summary", wraps=log_analyzer.save_json_summary):
                log_analyzer.save_json_summary(out_file, summary)
            loaded = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(loaded["before"]["exit_code"], 137)
            self.assertTrue(loaded["after"]["app"]["memory_cache_flushed"])


if __name__ == "__main__":
    unittest.main()

