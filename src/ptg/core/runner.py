"""Isolated C++17 Runner executing inside disposable Docker containers."""

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Optional

from ptg.models.runner import CompileResult, ExecutionResult, SandboxLimits, Verdict

logger = logging.getLogger(__name__)


class IsolatedRunner:
    """Manages secure compilation and execution of untrusted C++ code in Docker sandbox."""

    def __init__(
        self,
        image_name: str = "ptg-cpp-runner:latest",
        limits: Optional[SandboxLimits] = None,
        base_temp_dir: Optional[str] = None,
    ):
        self.image_name = image_name
        self.limits = limits or SandboxLimits()
        self.base_temp_dir = base_temp_dir or os.path.abspath("temp")
        os.makedirs(self.base_temp_dir, exist_ok=True)

    def _format_volume_path(self, path: Path) -> str:
        """Format path for Docker volume mounting across Windows and POSIX hosts."""
        resolved = str(path.resolve())
        # Replace backslashes with forward slashes for Docker volume mounting
        return resolved.replace("\\", "/")

    def compile(
        self,
        source_code: str,
        binary_name: str = "solution",
        workspace_dir: Optional[Path] = None,
    ) -> CompileResult:
        """Compile C++17 source code inside a bounded Docker container."""
        own_workspace = False
        if workspace_dir is None:
            temp_path = tempfile.mkdtemp(prefix="ptg_compile_", dir=self.base_temp_dir)
            workspace_dir = Path(temp_path)
            own_workspace = True

        source_file = workspace_dir / f"{binary_name}.cpp"
        source_file.write_text(source_code, encoding="utf-8")

        vol_mount = f"{self._format_volume_path(workspace_dir)}:/workspace"

        # Docker compile command with hard timeout and resource bounds (ADR-004)
        cmd = [
            "docker", "run", "--rm",
            "--network=none",
            "--cpus", str(self.limits.cpu_limit),
            "--memory", self.limits.compile_memory_limit,
            "--memory-swap", self.limits.compile_memory_limit,
            "--pids-limit", str(self.limits.pids_limit),
            "-v", vol_mount,
            self.image_name,
            "timeout", "-s", "KILL", f"{self.limits.compile_timeout_sec}s",
            "g++", "-O2", "-std=c++17",
            "-ftemplate-depth=256", "-fmax-errors=3",
            "-o", f"/workspace/{binary_name}",
            f"/workspace/{binary_name}.cpp",
        ]

        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.limits.compile_timeout_sec + 5,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            binary_path = workspace_dir / binary_name
            # In Windows host, binary inside Linux container is an ELF without .exe
            is_success = proc.returncode == 0 and binary_path.exists()

            error_msg = None
            if proc.returncode == 137:
                error_msg = f"Compilation timed out after {self.limits.compile_timeout_sec}s (possible compiler bomb or resource exhaustion)."
            elif not is_success:
                error_msg = proc.stderr.strip() or "Compilation failed."

            return CompileResult(
                success=is_success,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_ms=elapsed_ms,
                binary_name=binary_name if is_success else None,
                error_message=error_msg,
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return CompileResult(
                success=False,
                exit_code=137,
                stdout="",
                stderr="Docker container compilation exceeded host supervisor timeout.",
                duration_ms=elapsed_ms,
                error_message="Compilation timed out.",
            )
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return CompileResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=elapsed_ms,
                error_message=f"Infrastructure error: {e}",
            )
        finally:
            if own_workspace and not is_success:
                shutil.rmtree(workspace_dir, ignore_errors=True)

    def execute(
        self,
        binary_name: str,
        workspace_dir: Path,
        stdin_data: str = "",
        args: Optional[List[str]] = None,
        custom_timeout_sec: Optional[int] = None,
    ) -> ExecutionResult:
        """Execute a compiled binary inside an isolated, non-root, networkless container."""
        args = args or []
        timeout_sec = custom_timeout_sec or self.limits.exec_timeout_sec
        vol_mount = f"{self._format_volume_path(workspace_dir)}:/workspace"

        cmd = [
            "docker", "run", "--rm", "-i",
            "--network=none",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--cpus", str(self.limits.cpu_limit),
            "--memory", self.limits.memory_limit,
            "--memory-swap", self.limits.memory_limit,
            "--pids-limit", str(self.limits.pids_limit),
            "--security-opt=no-new-privileges",
            "--cap-drop=ALL",
            "-v", vol_mount,
            self.image_name,
            "timeout", "-s", "KILL", f"{timeout_sec}s",
            f"/workspace/{binary_name}",
            *args,
        ]

        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=timeout_sec + 5,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            # Determine verdict according to exit code and elapsed time
            if proc.returncode == 0:
                verdict = Verdict.OK
            elif proc.returncode == 137:
                # 137 is SIGKILL: either from 'timeout' or Linux OOM-killer
                if elapsed_ms >= timeout_sec * 1000 - 200:
                    verdict = Verdict.TIME_LIMIT_EXCEEDED
                else:
                    verdict = Verdict.MEMORY_LIMIT_EXCEEDED
            else:
                verdict = Verdict.RUNTIME_ERROR

            # Enforce max output bytes limit
            stdout = proc.stdout
            if len(stdout.encode("utf-8")) > self.limits.max_output_bytes:
                stdout = stdout[:self.limits.max_output_bytes]
                verdict = Verdict.OUTPUT_LIMIT_EXCEEDED

            return ExecutionResult(
                verdict=verdict,
                exit_code=proc.returncode,
                stdout=stdout,
                stderr=proc.stderr,
                duration_ms=elapsed_ms,
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return ExecutionResult(
                verdict=Verdict.TIME_LIMIT_EXCEEDED,
                exit_code=137,
                stdout="",
                stderr="Execution host timeout expired.",
                duration_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return ExecutionResult(
                verdict=Verdict.INFRASTRUCTURE_ERROR,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=elapsed_ms,
            )
