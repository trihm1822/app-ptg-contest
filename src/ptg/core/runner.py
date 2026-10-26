"""Isolated C++17 Runner executing inside disposable Docker containers."""

import atexit
import logging
import os
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import List, Optional, Set

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

        self._active_containers: Set[str] = set()

        # Register process termination hooks for zombie container cleanup
        atexit.register(self._cleanup_all_containers)
        try:
            signal.signal(signal.SIGINT, self._handle_signal)
            signal.signal(signal.SIGTERM, self._handle_signal)
        except (ValueError, AttributeError):
            # Not in main thread or signal not supported on platform
            pass

        # Layer 1 Defense: Startup reconciliation of orphaned containers from prior crashes
        self._reconcile_lingering_containers()

    def _handle_signal(self, signum, frame):
        """Clean up active containers upon receiving OS signals."""
        self._cleanup_all_containers()
        # Re-raise or exit with standard signal code
        signal.default_int_handler(signum, frame)

    def _cleanup_all_containers(self) -> None:
        """Kill and remove any active containers tracked by this runner."""
        for cid in list(self._active_containers):
            try:
                subprocess.run(
                    ["docker", "rm", "-f", cid],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass
        self._active_containers.clear()

    def _reconcile_lingering_containers(self) -> None:
        """Startup reconciliation: prune orphaned ptg containers from previous crashes."""
        try:
            subprocess.run(
                ["docker", "container", "prune", "-f", "--filter", "label=managed-by=ptg"],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            # Docker daemon might be offline or starting up
            pass

    def _format_volume_path(self, path: Path) -> str:
        """Format path for Docker volume mounting across Windows and POSIX hosts."""
        resolved = str(path.resolve())
        return resolved.replace("\\", "/")

    def compile(
        self,
        source_code: str,
        binary_name: str = "solution",
        workspace_dir: Optional[Path] = None,
    ) -> CompileResult:
        """Compile C++17 source code inside a bounded Docker container with read-write workspace."""
        own_workspace = False
        if workspace_dir is None:
            temp_path = tempfile.mkdtemp(prefix="ptg_compile_", dir=self.base_temp_dir)
            workspace_dir = Path(temp_path)
            own_workspace = True

        source_file = workspace_dir / f"{binary_name}.cpp"
        source_file.write_text(source_code, encoding="utf-8")

        # Compile mount must be explicitly read-write (:rw)
        vol_mount = f"{self._format_volume_path(workspace_dir)}:/workspace:rw"
        container_name = f"ptg-comp-{uuid.uuid4().hex[:12]}"
        self._active_containers.add(container_name)

        cmd = [
            "docker", "run",
            "--name", container_name,
            "--label", "managed-by=ptg",
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
            # Always clean up container
            try:
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=5)
            except Exception:
                pass
            self._active_containers.discard(container_name)

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
        """Execute a compiled binary inside an isolated container with read-only workspace mount."""
        args = args or []
        timeout_sec = custom_timeout_sec or self.limits.exec_timeout_sec

        # SANDBOX-01: Volume mount MUST be strictly read-only (:ro)
        vol_mount = f"{self._format_volume_path(workspace_dir)}:/workspace:ro"
        container_name = f"ptg-exec-{uuid.uuid4().hex[:12]}"
        self._active_containers.add(container_name)

        cmd = [
            "docker", "run", "-i",
            "--name", container_name,
            "--label", "managed-by=ptg",
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

            oom_killed = False
            # Post-mortem inspection for non-zero exit codes (SANDBOX-02)
            if proc.returncode != 0:
                try:
                    inspect_res = subprocess.run(
                        ["docker", "inspect", "--format", "{{.State.OOMKilled}}", container_name],
                        capture_output=True,
                        text=True,
                        timeout=3,
                    )
                    if inspect_res.returncode == 0 and "true" in inspect_res.stdout.strip().lower():
                        oom_killed = True
                except Exception:
                    pass

            # Determine verdict with strict taxonomy
            if proc.returncode == 0:
                verdict = Verdict.OK
            elif oom_killed:
                verdict = Verdict.MEMORY_LIMIT_EXCEEDED
            elif "Resource temporarily unavailable" in proc.stderr or "EAGAIN" in proc.stderr:
                verdict = Verdict.RESOURCE_LIMIT_EXCEEDED
            elif proc.returncode == 137:
                if elapsed_ms >= timeout_sec * 1000 - 200:
                    verdict = Verdict.TIME_LIMIT_EXCEEDED
                else:
                    verdict = Verdict.RUNTIME_ERROR
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
                oom_killed=oom_killed,
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
        finally:
            # Layer 2 Defense: Guaranteed cleanup in finally block
            try:
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=5)
            except Exception:
                pass
            self._active_containers.discard(container_name)
