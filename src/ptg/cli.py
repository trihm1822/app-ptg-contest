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


@app.command(name="generate-code")
def generate_code(
    problem: str = typer.Option(
        ...,
        "--problem",
        "-p",
        help="Path to problem statement Markdown file (e.g. tests/fixtures/problems/01_two_sum.md)",
    ),
    output_dir: str = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory to store the 5 generated artifacts (default: output/<problem_id>)",
    ),
    model: str = typer.Option(
        "gemini-3.8-flash",
        "--model",
        "-m",
        help="LLM model identifier (e.g. gemini-3.8-flash, gemini-2.5-flash)",
    ),
    temperature: float = typer.Option(
        0.2,
        "--temperature",
        "-t",
        help="Sampling temperature for code generation",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Bypass local SHA-256 response cache and force fresh generation",
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Use deterministic offline Mock LLM provider without calling remote API",
    ),
):
    """Generate C++ solutions, generator, validator, and explanation from a problem statement."""
    from pathlib import Path
    from rich.table import Table
    from ptg.core.code_generator import CodeGenerator

    problem_path = Path(problem)
    if not problem_path.exists():
        console.print(f"[bold red]Error:[/] Problem file not found: [yellow]{problem_path}[/]")
        raise typer.Exit(code=1)

    target_out_dir = Path(output_dir) if output_dir else Path("output") / problem_path.stem

    console.print(
        f"[cyan]Initiating code generation for problem:[/] [bold]{problem_path.name}[/] "
        f"([dim]model={model}, mock={mock}[/])"
    )

    generator = CodeGenerator()
    try:
        with console.status(f"[bold yellow]Generating code with {'Mock' if mock else model}..."):
            result, files = generator.generate_from_file(
                problem_path=problem_path,
                output_dir=target_out_dir,
                model_name=model,
                temperature=temperature,
                use_cache=not no_cache,
                use_mock=mock,
            )
    except Exception as e:
        console.print(f"[bold red]Generation failed:[/] {e}")
        raise typer.Exit(code=1)

    # Print summary table
    table = Table(title="[bold green]LLM Generation Summary[/]", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Problem ID", result.problem_id)
    table.add_row("Model Used", result.model_name)
    table.add_row("Cache Status", "[green]HIT (Local Disk)[/]" if result.is_cached else "[yellow]MISS (API Query)[/]")
    if result.cache_key:
        table.add_row("Cache Key (SHA-256)", f"[dim]{result.cache_key[:16]}...[/]")
    table.add_row("Latency", f"{result.usage.latency_ms:.1f} ms")
    table.add_row("Tokens (Prompt / Candidates / Total)", f"{result.usage.prompt_tokens} / {result.usage.candidates_tokens} / {result.usage.total_tokens}")
    table.add_row("Estimated Cost", f"${result.usage.estimated_cost_usd:.6f} USD")

    console.print(table)

    console.print("\n[bold green]✓ 5 Artifacts generated successfully in:[/] [yellow]" + str(target_out_dir) + "[/]")
    for fname, fpath in files.items():
        console.print(f"  [green]•[/] [bold]{fname}[/]: {fpath} ([dim]{fpath.stat().st_size} bytes[/])")


@app.command(name="run-differential")
def run_differential(
    problem_dir: str = typer.Option(
        ...,
        "--dir",
        "-d",
        help="Directory containing brute.cpp, optimized.cpp, generator.cpp, and validator.cpp",
    ),
    count: int = typer.Option(
        5,
        "--count",
        "-c",
        help="Number of testcases to generate and evaluate",
    ),
    subtask: int = typer.Option(
        1,
        "--subtask",
        "-s",
        help="Subtask ID passed to generator (argv[2])",
    ),
    start_seed: int = typer.Option(
        1000,
        "--seed",
        help="Initial random seed",
    ),
    save_dir: str = typer.Option(
        None,
        "--save-dir",
        help="Directory to save verified testcases (default: <dir>/tests)",
    ),
    continue_on_error: bool = typer.Option(
        False,
        "--continue-on-error",
        help="Do not halt immediately on mismatch or validation failure",
    ),
):
    """Run batch differential testing between brute and optimized solutions in Docker Sandbox."""
    from pathlib import Path
    from rich.table import Table
    from ptg.core.differential_engine import DifferentialEngine
    from ptg.models.testcase import TestcaseStatus

    p_dir = Path(problem_dir)
    if not p_dir.exists():
        console.print(f"[bold red]Error:[/] Problem directory not found: [yellow]{p_dir}[/]")
        raise typer.Exit(code=1)

    target_save_dir = Path(save_dir) if save_dir else p_dir / "tests"

    console.print(
        f"[cyan]Initiating Differential Testing for:[/] [bold]{p_dir.name}[/] "
        f"([dim]count={count}, subtask={subtask}, start_seed={start_seed}[/])"
    )

    def on_progress(rec, current, total):
        if rec.status == TestcaseStatus.PASSED:
            console.print(
                f"  [green]✓[/] Test #{current:02d} (Seed {rec.seed}): "
                f"Validated -> Brute ({rec.brute_duration_ms:.1f}ms) == Opt ({rec.optimized_duration_ms:.1f}ms) "
                f"-> [bold green]PASS[/]"
            )
        elif rec.status == TestcaseStatus.MISMATCH:
            console.print(
                f"  [bold red]✗[/] Test #{current:02d} (Seed {rec.seed}): "
                f"[bold red]MISMATCH FOUND[/]\n"
                f"    [dim]{rec.mismatch_detail}[/]"
            )
        elif rec.status == TestcaseStatus.VALIDATION_FAILED:
            console.print(
                f"  [bold red]✗[/] Test #{current:02d} (Seed {rec.seed}): "
                f"[bold red]VALIDATION FAILED[/] ({rec.error_message})"
            )
        else:
            console.print(
                f"  [bold red]✗[/] Test #{current:02d} (Seed {rec.seed}): "
                f"[bold red]{rec.status.value}[/] ({rec.error_message})"
            )

    engine = DifferentialEngine()
    with console.status("[bold yellow]Compiling C++ programs in Docker Sandbox..."):
        res = engine.run_differential_suite(
            problem_dir=p_dir,
            subtask_id=subtask,
            count=count,
            start_seed=start_seed,
            save_dir=target_save_dir,
            stop_on_mismatch=not continue_on_error,
            progress_callback=on_progress,
        )

    # Print summary table
    table = Table(title="[bold green]Differential Testing Summary[/]", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Problem ID", res.problem_id)
    table.add_row("Total Evaluated", str(res.total_cases))
    table.add_row("Passed Testcases", f"[green]{res.passed_cases}[/]")
    table.add_row("Failed Testcases", f"[red]{res.failed_cases}[/]" if res.failed_cases > 0 else "[green]0[/]")

    status_color = "bold green" if res.overall_status == "VERIFIED" else "bold red"
    table.add_row("Overall Verdict", f"[{status_color}]{res.overall_status}[/]")
    table.add_row("Total Duration", f"{res.duration_ms:.1f} ms")

    if res.error_message:
        table.add_row("Fatal Error", f"[red]{res.error_message}[/]")

    console.print(table)

    if res.overall_status == "VERIFIED":
        console.print(
            f"\n[bold green]✓ All {res.passed_cases} testcases verified and saved in:[/] [yellow]{target_save_dir}[/]"
        )
    else:
        console.print(
            f"\n[bold red]✗ Testing halted due to {res.overall_status}. Please review the mismatch/error above.[/]"
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
