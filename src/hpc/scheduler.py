"""Scheduler abstraction for Slurm and PJM"""

import re
from abc import ABC, abstractmethod
from enum import Enum


class JobStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class Scheduler(ABC):
    @abstractmethod
    def directive_prefix(self) -> str: ...

    @abstractmethod
    def submit_cmd(self) -> list[str]: ...

    @abstractmethod
    def parse_job_id(self, output: str) -> str: ...

    @abstractmethod
    def status_cmd(self, job_id: str) -> list[str]: ...

    @abstractmethod
    def parse_status(self, output: str) -> JobStatus: ...


class Slurm(Scheduler):
    def directive_prefix(self) -> str:
        return "#SBATCH"

    def submit_cmd(self) -> list[str]:
        return ["sbatch", "--parsable"]

    def parse_job_id(self, output: str) -> str:
        return output.strip()

    def status_cmd(self, job_id: str) -> list[str]:
        return ["sacct", "-j", job_id, "--format=State", "--noheader"]

    def parse_status(self, output: str) -> JobStatus:
        lines = output.strip().splitlines()
        status_str = lines[0].strip().rstrip("+") if lines else ""
        return _STATUS_MAP.get(status_str, JobStatus.FAILED)


class PJM(Scheduler):
    _STATUS_MAP = {
        "ACC": JobStatus.PENDING,
        "QUE": JobStatus.PENDING,
        "RNA": JobStatus.PENDING,
        "RNP": JobStatus.RUNNING,
        "RUN": JobStatus.RUNNING,
        "RNE": JobStatus.RUNNING,
        "RNO": JobStatus.RUNNING,
        "EXT": JobStatus.COMPLETED,
        "CCL": JobStatus.CANCELLED,
        "ERR": JobStatus.FAILED,
        "HLD": JobStatus.PENDING,
        "RJT": JobStatus.FAILED,
    }

    def directive_prefix(self) -> str:
        return "#PJM -L"

    def submit_cmd(self) -> list[str]:
        return ["pjsub"]

    def parse_job_id(self, output: str) -> str:
        # pjsub output example: "[INFO] PJM 0000 pjsub Job XXXXXXXX submitted."
        match = re.search(r"\bJob\s+(\d+)\b", output, flags=re.IGNORECASE)
        if match:
            return match.group(1)

        # Fallback: use the last numeric token to avoid picking status code "0000".
        numbers = re.findall(r"\d+", output)
        if numbers:
            return numbers[-1]

        return output.strip()

    def status_cmd(self, job_id: str) -> list[str]:
        return ["pjstat", "--choose", "st", job_id]

    def parse_status(self, output: str) -> JobStatus:
        lines = output.strip().splitlines()
        status_str = lines[1].strip() if len(lines) >= 2 else ""
        return self._STATUS_MAP.get(status_str, JobStatus.FAILED)


_STATUS_MAP = {
    "PENDING": JobStatus.PENDING,
    "RUNNING": JobStatus.RUNNING,
    "COMPLETED": JobStatus.COMPLETED,
    "FAILED": JobStatus.FAILED,
    "CANCELLED": JobStatus.CANCELLED,
    "TIMEOUT": JobStatus.TIMEOUT,
}


def get_scheduler(name: str) -> Scheduler:
    schedulers = {"slurm": Slurm, "pjm": PJM}
    if name not in schedulers:
        raise ValueError(f"Unknown scheduler: {name}")
    return schedulers[name]()
