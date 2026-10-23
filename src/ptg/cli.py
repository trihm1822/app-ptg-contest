"""PTG Command-line Interface."""

import sys
import typer
from rich.console import Console
from rich.panel import Panel

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(
    name="ptg",
    help="Problem-to-Testcase Generator (PTG) for Competitive Programming.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command(name="version")
def version():
    """Display PTG version and status."""
    from ptg import __version__
    console.print(Panel(
        f"[bold green]Problem-to-Testcase Generator (PTG)[/] v{__version__}\n"
        "[dim]Isolated C++17 Competitive Programming Test Engine[/]",
        title="PTG Core",
        expand=False,
    ))


@app.command(name="check-sandbox")
def check_sandbox():
    """Verify Docker sandbox availability and compile/run a test program."""
    from ptg.core.runner import IsolatedRunner
    from ptg.models.runner import Verdict

    console.print("[cyan]Checking Docker C++ Sandbox environment...[/]")
    runner = IsolatedRunner()

    test_code = """
    #include <iostream>
    int main() {
        std::cout << "SANDBOX_OPERATIONAL" << std::endl;
        return 0;
    }
    """
    with console.status("[bold yellow]Compiling C++ code inside isolated Docker container..."):
        comp_res = runner.compile(test_code, binary_name="smoke_test")

    if not comp_res.success:
        console.print(f"[bold red]Compilation failed:[/] {comp_res.error_message}")
        raise typer.Exit(code=1)

    console.print(f"[green]✓[/] Compilation succeeded ({comp_res.duration_ms} ms)")

    with console.status("[bold yellow]Executing binary inside restricted sandbox..."):
        import tempfile
        from pathlib import Path
        import shutil
        temp_dir = Path(tempfile.mkdtemp(prefix="ptg_smoke_", dir="temp"))
        try:
            # Recompile into this temp dir to execute
            comp_res = runner.compile(test_code, binary_name="smoke_test", workspace_dir=temp_dir)
            exec_res = runner.execute("smoke_test", workspace_dir=temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    if exec_res.verdict == Verdict.OK and "SANDBOX_OPERATIONAL" in exec_res.stdout:
        console.print(f"[green]✓[/] Sandboxed execution succeeded ({exec_res.duration_ms} ms)")
        console.print("[bold green]✓ Docker Sandbox is 100% OPERATIONAL for Phase 0![/]")
    else:
        console.print(f"[bold red]Execution failed: verdict={exec_res.verdict}[/]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
