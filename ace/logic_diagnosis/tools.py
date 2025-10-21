"""Convenience wrappers for external logic-diagnosis tooling."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence


@dataclass
class ToolResult:
    """Container with the stdout/stderr of a tool invocation."""

    command: Sequence[str]
    stdout: str
    stderr: str
    returncode: int

    def check_returncode(self) -> None:
        if self.returncode != 0:
            raise subprocess.CalledProcessError(
                self.returncode, list(self.command), output=self.stdout, stderr=self.stderr
            )


class ExternalTool:
    """Simple subprocess-based wrapper around a CLI utility."""

    def __init__(self, executable: str, *, default_args: Optional[Sequence[str]] = None) -> None:
        self.executable = executable
        self.default_args = list(default_args or [])

    def run(
        self,
        *args: str,
        input_text: Optional[str] = None,
        cwd: Optional[Path] = None,
        check: bool = False,
        timeout: Optional[float] = None,
    ) -> ToolResult:
        command = [self.executable, *self.default_args, *args]
        process = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            cwd=cwd,
            timeout=timeout,
        )
        result = ToolResult(command=command, stdout=process.stdout, stderr=process.stderr, returncode=process.returncode)
        if check:
            result.check_returncode()
        return result


class LogicDiagnosisToolset:
    """Provides named accessors for the external tooling used in the workflow."""

    def __init__(
        self,
        *,
        ganga: Optional[ExternalTool] = None,
        hope: Optional[ExternalTool] = None,
        atalanta: Optional[ExternalTool] = None,
        matcher: Optional[ExternalTool] = None,
        backconer: Optional[ExternalTool] = None,
        submit_tests: Optional[ExternalTool] = None,
    ) -> None:
        self.ganga = ganga or ExternalTool("ganga")
        self.hope = hope or ExternalTool("hope")
        self.atalanta = atalanta or ExternalTool("atalanta")
        self.matcher = matcher or ExternalTool("matcher")
        self.backconer = backconer or ExternalTool("backconer")
        self.submit_tests = submit_tests or ExternalTool("submit_tests")

    def all_tools(self) -> List[ExternalTool]:
        return [
            self.ganga,
            self.hope,
            self.atalanta,
            self.matcher,
            self.backconer,
            self.submit_tests,
        ]


__all__ = ["ExternalTool", "LogicDiagnosisToolset", "ToolResult"]
