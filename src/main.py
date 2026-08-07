"""
Lab 11 — Main Entry Point
Run the Day 11 flows: red-team demo -> 2026 checkpoint verification.

Usage:
    python main.py              # Run the 2026 checkpoint verification
    python main.py --part 1     # Run the optional red-team demo (API key required)
    python main.py --part 2     # Verify the 2026 controlled-security checkpoints
    python main.py --legacy-part 2  # Run the old guardrails walkthrough (optional)
    python main.py --legacy-part 3  # Run the old testing walkthrough (optional)
    python main.py --legacy-part 4  # Run the old HITL walkthrough (optional)
"""
import asyncio
import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

async def part1_attacks():
    """Attack the unsafe demo, then exercise the public Guards policy reference."""
    print("\n" + "=" * 60)
    print("PART 1 / Hạng mục B: Attack Unsafe + Public Guards Reference")
    print("=" * 60)

    from agents.agent import create_unsafe_agent, test_agent
    from agents.guards_agent import create_guards_agent
    from attacks.attacks import run_attacks, generate_ai_attacks, save_attack_results

    # --- Unsafe (required for hạng mục B) ---
    unsafe_agent, unsafe_runner = create_unsafe_agent()
    await test_agent(unsafe_agent, unsafe_runner)

    print("\n--- Attacks on UNSAFE agent (hạng mục B) ---")
    unsafe_results = await run_attacks(
        unsafe_agent, unsafe_runner, target_name="unsafe"
    )

    # --- Public reference (local policy experiment, never a bonus oracle) ---
    print("\n--- Attacks on public Guards reference (local policy experiment) ---")
    guards_agent, guards_runner = create_guards_agent()
    guards_results = await run_attacks(
        guards_agent, guards_runner, target_name="guards_reference"
    )

    print("\n--- Generating AI attacks (TODO 2) ---")
    try:
        ai_attacks = await generate_ai_attacks()
    except Exception as error:
        print(f"AI attack generation failed: {error}")
        ai_attacks = []

    print("\n" + "=" * 60)
    print("Local Guards results are diagnostic only → host verifier replay decides tiered bonus (max +10)")
    print("=" * 60)

    save_attack_results(
        unsafe_attacks=unsafe_results,
        guards_attacks=guards_results,
        ai_generated_attacks=ai_attacks,
        output_path=str(
            Path(__file__).resolve().parents[1] / "outputs" / "attack_results.json"
        ),
    )

    return {
        "unsafe": unsafe_results,
        "guards_reference": guards_results,
        "ai_attacks": ai_attacks,
    }


def _run_checkpoint_command(name: str, command: list[str], cwd: Path) -> bool:
    """Run one local verification command and print a concise result."""
    print(f"\n--- {name} ---")
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"[FAIL] {name}: {error}")
        return False

    output = (completed.stdout + completed.stderr).strip()
    if output:
        print(output)
    status = "PASS" if completed.returncode == 0 else "NEEDS WORK"
    print(f"[{status}] {name}")
    return completed.returncode == 0


def _print_artifact_status(repo_root: Path) -> None:
    """Show checkpoint artifacts without creating learner-controlled evidence."""
    print("\n--- Checkpoint artifacts ---")
    for relative_path in (
        "outputs/results.json",
        "outputs/audit_log.json",
        "outputs/metrics.json",
        "outputs/attack_results.json",
        "outputs/grade_report.json",
    ):
        path = repo_root / relative_path
        status = "CREATED" if path.is_file() else "MISSING"
        print(f"[{status}] {relative_path}")


def _checkpoint_dependencies_available() -> bool:
    """Keep the no-API-key checkpoint failure actionable when setup is incomplete."""
    required_modules = ("pytest", "jsonschema", "google.genai", "google.adk")
    missing = [
        module
        for module in required_modules
        if importlib.util.find_spec(module) is None
    ]
    if not missing:
        return True

    print("[SETUP REQUIRED] Missing Python packages: " + ", ".join(missing))
    print("Run: python -m pip install -r requirements.txt")
    print("No Google API key is needed for this checkpoint verification.")
    return False


async def part2_controlled_security() -> None:
    """Verify the current 2026 checkpoint instead of running the legacy lab."""
    repo_root = Path(__file__).resolve().parents[1]
    print("\n" + "=" * 60)
    print("PART 2: Controlled Agent Security — Checkpoint Verification")
    print("=" * 60)

    if not _checkpoint_dependencies_available():
        return

    checks = (
        ("Starter structure", [sys.executable, "-m", "pytest", "tests/smoke", "-q"]),
        ("Security checkpoint tests", [sys.executable, "-m", "pytest", "tests/public", "-q"]),
        (
            "Submission self-check",
            [
                sys.executable,
                "scripts/grade.py",
                "--submission-dir",
                ".",
                "--out",
                "outputs/grade_report.json",
            ],
        ),
    )
    results = [
        _run_checkpoint_command(name, command, repo_root)
        for name, command in checks
    ]
    _print_artifact_status(repo_root)

    passed = sum(results)
    print(f"\nCheckpoint commands passed: {passed}/{len(results)}")
    if not results[1]:
        print(
            "Public tests are expected to fail on the untouched starter. "
            "Complete the TODOs in src/assignment/, src/guardrails/ and src/hitl/."
        )
    print(
        "outputs/grade_report.json is a packaging self-check only; hidden runtime "
        "tests decide implementation points and the host verifier decides bonus."
    )


async def legacy_part2_guardrails():
    """Optional pre-2026 walkthrough, retained only for reference."""
    print("\n" + "=" * 60)
    print("LEGACY PART 2: Guardrails walkthrough (not the 2026 checkpoint)")
    print("=" * 60)

    from guardrails.input_guardrails import (
        test_injection_detection,
        test_topic_filter,
        test_input_plugin,
    )
    from guardrails.output_guardrails import test_content_filter, _init_judge

    test_injection_detection()
    print()
    test_topic_filter()
    print()
    await test_input_plugin()
    _init_judge()
    test_content_filter()


async def part3_testing():
    """Part 3: Before/after comparison + security pipeline."""
    print("\n" + "=" * 60)
    print("PART 3: Security Testing Pipeline")
    print("=" * 60)

    from testing.testing import run_comparison, print_comparison, SecurityTestPipeline
    from agents.agent import create_unsafe_agent

    # TODO 10: Before vs after comparison
    print("\n--- TODO 10: Before/After Comparison ---")
    unprotected, protected = await run_comparison()
    if unprotected and protected:
        print_comparison(unprotected, protected)
    else:
        print("Complete TODO 10 to see the comparison.")

    # TODO 11: Automated security pipeline
    print("\n--- TODO 11: Security Test Pipeline ---")
    agent, runner = create_unsafe_agent()
    pipeline = SecurityTestPipeline(agent, runner)
    results = await pipeline.run_all()
    if results:
        pipeline.print_report(results)
    else:
        print("Complete TODO 11 to see the pipeline report.")


def part4_hitl():
    """Part 4: HITL design."""
    print("\n" + "=" * 60)
    print("PART 4: Human-in-the-Loop Design")
    print("=" * 60)

    from hitl.hitl import test_confidence_router, test_hitl_points

    # TODO 12: Confidence Router
    print("\n--- TODO 12: Confidence Router ---")
    test_confidence_router()

    # TODO 13: HITL Decision Points
    print("\n--- TODO 13: HITL Decision Points ---")
    test_hitl_points()


async def main(parts=None):
    """Run the full lab or specific parts.

    Args:
        parts: List of part numbers to run, or None for all
    """
    if parts is None:
        parts = [2]

    if 1 in parts:
        from core.config import setup_api_key

        setup_api_key()

    for part in parts:
        if part == 1:
            await part1_attacks()
        elif part == 2:
            await part2_controlled_security()
        elif part == 3:
            await part3_testing()
        elif part == 4:
            part4_hitl()
        else:
            print(f"Unknown part: {part}")

    print("\n" + "=" * 60)
    print("Lab 11 complete! Check your results above.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Lab 11: Guardrails, HITL & Responsible AI"
    )
    parser.add_argument(
        "--part", type=int, choices=[1, 2],
        help="Run Part 1 (red-team demo) or Part 2 (2026 checkpoint).",
    )
    parser.add_argument(
        "--legacy-part",
        type=int,
        choices=[2, 3, 4],
        help="Run an optional pre-2026 walkthrough; it is not the graded checkpoint.",
    )
    args = parser.parse_args()

    if args.part and args.legacy_part:
        parser.error("Use either --part or --legacy-part, not both.")
    if args.legacy_part:
        if args.legacy_part == 2:
            asyncio.run(legacy_part2_guardrails())
        elif args.legacy_part == 3:
            from core.config import setup_api_key

            setup_api_key()
            asyncio.run(part3_testing())
        else:
            part4_hitl()
    elif args.part:
        asyncio.run(main(parts=[args.part]))
    else:
        asyncio.run(main())
