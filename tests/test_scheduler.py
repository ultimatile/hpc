"""Scheduler unit tests."""

from hpc.scheduler import PJM


class TestPJMParseJobID:
    def test_parse_job_id_prefers_job_token(self):
        scheduler = PJM()

        output = "[INFO] PJM 0000 pjsub Job 12345678 submitted."

        assert scheduler.parse_job_id(output) == "12345678"

    def test_parse_job_id_falls_back_to_last_numeric_token(self):
        scheduler = PJM()

        output = "PJM 0000: submitted job 87654321"

        assert scheduler.parse_job_id(output) == "87654321"

    def test_parse_job_id_returns_stripped_output_when_no_numeric_token(self):
        scheduler = PJM()

        output = " unexpected output "

        assert scheduler.parse_job_id(output) == "unexpected output"
