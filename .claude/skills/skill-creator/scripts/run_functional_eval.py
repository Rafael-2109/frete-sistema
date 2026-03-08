#!/usr/bin/env python3
"""Run functional evaluation for a skill's behavioral evals.

Tests whether an agent with/without skill context makes the right decisions
(correct script, correct arguments, proper error handling) when given a prompt.

Unlike run_eval.py (trigger evaluation), this tests BEHAVIOR over a full
agent interaction, not just whether the skill is triggered.

Usage:
    cd .claude/skills/skill-creator
    python -m scripts.run_functional_eval \
        --evals-json ../../skills/operando-portal-atacadao/evals/evals.json \
        --skill-path ../../skills/operando-portal-atacadao \
        --workspace ../../skills/operando-portal-atacadao-workspace/iteration-1 \
        --model claude-sonnet-4-6 \
        --verbose

Directory structure created:
    <workspace>/
    └── eval-N/
        ├── eval_metadata.json
        ├── with_skill/
        │   └── run-1/
        │       ├── transcript.json
        │       ├── timing.json
        │       └── grading.json
        └── without_skill/
            └── run-1/
                ├── transcript.json
                ├── timing.json
                └── grading.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
import httpx

from scripts.run_eval import _hide_real_skill, _restore_real_skill


def run_executor(
    prompt: str,
    timeout: int,
    project_root: str,
    model: str | None = None,
) -> tuple[list[dict], float]:
    """Run claude -p with a prompt and capture the full stream-json output.

    Returns (events, duration_seconds).
    """
    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--max-turns", "10",
    ]
    if model:
        cmd.extend(["--model", model])

    # Remove CLAUDECODE env var to allow nesting
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=project_root,
            env=env,
            timeout=timeout,
            start_new_session=True,
        )
        duration = time.time() - t0
        output = result.stdout.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        duration = time.time() - t0
        # Capture any partial stdout collected before timeout
        output = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""

    # Parse stream-json events
    events = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return events, duration


def extract_transcript_text(events: list[dict]) -> str:
    """Extract a human-readable transcript from stream-json events.

    Focuses on assistant messages and tool calls/results.
    """
    lines = []
    for event in events:
        etype = event.get("type")

        if etype == "assistant":
            msg = event.get("message", {})
            for block in msg.get("content", []):
                if block.get("type") == "text":
                    lines.append(f"[ASSISTANT TEXT]: {block['text']}")
                elif block.get("type") == "tool_use":
                    tool_name = block.get("name", "?")
                    tool_input = json.dumps(block.get("input", {}), ensure_ascii=False)
                    # Truncate very long inputs
                    if len(tool_input) > 2000:
                        tool_input = tool_input[:2000] + "...(truncated)"
                    lines.append(f"[TOOL CALL]: {tool_name}({tool_input})")

        elif etype == "tool_result":
            content = event.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") for c in content if isinstance(c, dict)
                )
            # Truncate very long results
            if len(str(content)) > 3000:
                content = str(content)[:3000] + "...(truncated)"
            lines.append(f"[TOOL RESULT]: {content}")

        elif etype == "result":
            result_text = event.get("result", "")
            if result_text:
                lines.append(f"[FINAL RESULT]: {result_text}")

    return "\n".join(lines)


def grade_transcript(
    client: anthropic.Anthropic,
    eval_prompt: str,
    expectations: list[str],
    transcript_text: str,
    model: str,
) -> dict:
    """Grade a transcript against expectations using the Anthropic API.

    Returns a grading dict matching the format from grader.md.
    """
    grading_prompt = f"""You are a grader for a skill evaluation. Your job is to evaluate whether an agent's execution transcript satisfies each expectation.

## Eval Prompt (what the user asked):
{eval_prompt}

## Transcript (what the agent did):
<transcript>
{transcript_text}
</transcript>

## Expectations to evaluate:
{json.dumps(expectations, indent=2, ensure_ascii=False)}

## Instructions:
For each expectation, determine PASS or FAIL:
- PASS: Clear evidence in the transcript that the expectation is satisfied
- FAIL: No evidence, or evidence contradicts the expectation

IMPORTANT: Scripts may fail due to missing Playwright session. Grade based on the agent's BEHAVIOR:
- Did it call the RIGHT script with the RIGHT arguments?
- Did it handle errors appropriately?
- Did it NOT hallucinate data?
- Did it follow the correct workflow?

A script failing with "session expired" is NOT a failure of the agent if the agent:
1. Correctly identified which script to use
2. Used correct arguments
3. Properly handled the error (suggested re-login, didn't invent data)

Respond with ONLY a JSON object (no markdown fences) in this exact format:
{{
  "expectations": [
    {{
      "text": "<expectation text>",
      "passed": true/false,
      "evidence": "<specific quote or description from transcript>"
    }}
  ],
  "summary": {{
    "passed": <count>,
    "failed": <count>,
    "total": <count>,
    "pass_rate": <0.0 to 1.0>
  }},
  "claims": [],
  "eval_feedback": {{
    "suggestions": [],
    "overall": "<brief assessment>"
  }}
}}"""

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": grading_prompt}],
    )

    text = response.content[0].text

    # Try to parse JSON from response (handle markdown fences)
    json_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    try:
        grading = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: mark all as failed
        grading = {
            "expectations": [
                {"text": exp, "passed": False, "evidence": "Grading failed to parse"}
                for exp in expectations
            ],
            "summary": {
                "passed": 0,
                "failed": len(expectations),
                "total": len(expectations),
                "pass_rate": 0.0,
            },
            "parse_error": text[:500],
        }

    return grading


def run_single_eval(
    eval_item: dict,
    config: str,  # "with_skill" or "without_skill"
    workspace: Path,
    project_root: str,
    executor_model: str | None,
    grader_model: str,
    timeout: int,
    verbose: bool,
    skill_path: Path | None = None,  # For hiding during without_skill
) -> dict:
    """Run a single eval for a single configuration.

    Returns the grading result.
    """
    eval_id = eval_item["id"]
    run_dir = workspace / f"eval-{eval_id}" / config / "run-1"
    run_dir.mkdir(parents=True, exist_ok=True)

    prompt = eval_item["prompt"]
    expectations = eval_item["expectations"]

    if verbose:
        label = f"eval-{eval_id}/{config}"
        print(f"  [{label}] Starting executor...", file=sys.stderr)

    # Hide skill for without_skill runs
    hidden_path = None
    if config == "without_skill" and skill_path:
        hidden_path = _hide_real_skill(skill_path)

    try:
        events, duration = run_executor(
            prompt=prompt,
            timeout=timeout,
            project_root=project_root,
            model=executor_model,
        )
    finally:
        if hidden_path:
            _restore_real_skill(hidden_path)

    # Save raw events
    (run_dir / "transcript.json").write_text(
        json.dumps(events, indent=2, ensure_ascii=False)
    )

    # Save timing
    timing = {
        "executor_duration_seconds": round(duration, 1),
        "total_duration_seconds": round(duration, 1),
    }
    (run_dir / "timing.json").write_text(json.dumps(timing, indent=2))

    # Extract readable transcript
    transcript_text = extract_transcript_text(events)

    if verbose:
        label = f"eval-{eval_id}/{config}"
        print(
            f"  [{label}] Executor done ({duration:.1f}s, {len(events)} events). Grading...",
            file=sys.stderr,
        )

    # Grade
    client = anthropic.Anthropic(timeout=httpx.Timeout(120.0))
    grading = grade_transcript(
        client=client,
        eval_prompt=prompt,
        expectations=expectations,
        transcript_text=transcript_text,
        model=grader_model,
    )

    # Add timing to grading
    grading["timing"] = timing

    # Save grading
    (run_dir / "grading.json").write_text(
        json.dumps(grading, indent=2, ensure_ascii=False)
    )

    if verbose:
        label = f"eval-{eval_id}/{config}"
        summary = grading.get("summary", {})
        print(
            f"  [{label}] Graded: {summary.get('passed', 0)}/{summary.get('total', 0)} PASS",
            file=sys.stderr,
        )

    return grading


def run_functional_evals(
    evals_path: Path,
    skill_path: Path,
    workspace: Path,
    executor_model: str | None,
    grader_model: str,
    timeout: int,
    max_workers: int,
    verbose: bool,
    eval_ids: list[int] | None = None,
    configs: list[str] | None = None,
) -> dict:
    """Run all functional evals and return aggregated results.

    Args:
        eval_ids: If provided, only run these eval IDs. Otherwise run all.
        configs: List of configs to run. Default: ["with_skill", "without_skill"]
    """
    evals_data = json.loads(evals_path.read_text())
    evals_list = evals_data.get("evals", evals_data)  # Support both formats

    if eval_ids is not None:
        evals_list = [e for e in evals_list if e["id"] in eval_ids]

    if configs is None:
        configs = ["with_skill", "without_skill"]

    project_root = str(Path.cwd())
    workspace.mkdir(parents=True, exist_ok=True)

    # Save eval metadata
    for eval_item in evals_list:
        eval_dir = workspace / f"eval-{eval_item['id']}"
        eval_dir.mkdir(parents=True, exist_ok=True)
        (eval_dir / "eval_metadata.json").write_text(
            json.dumps(
                {
                    "eval_id": eval_item["id"],
                    "prompt": eval_item["prompt"],
                    "expected_output": eval_item.get("expected_output", ""),
                    "expectations": eval_item["expectations"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )

    if verbose:
        total_runs = len(evals_list) * len(configs)
        print(
            f"Running {total_runs} evals ({len(evals_list)} evals x {len(configs)} configs)",
            file=sys.stderr,
        )

    # Build all tasks
    tasks = []
    for eval_item in evals_list:
        for config in configs:
            tasks.append((eval_item, config))

    # IMPORTANT: without_skill runs hide/restore SKILL.md, so they CANNOT
    # run in parallel with each other or with with_skill runs (file race).
    # Run sequentially: all with_skill first, then all without_skill.
    all_results = {}

    for config in configs:
        config_tasks = [(e, c) for e, c in tasks if c == config]

        if verbose:
            print(f"\n--- Config: {config} ({len(config_tasks)} runs) ---", file=sys.stderr)

        # Within a config, we can parallelize with_skill runs
        # but without_skill runs must be sequential (shared SKILL.md hide/restore)
        if config == "with_skill" and max_workers > 1:
            executor = ThreadPoolExecutor(max_workers=max_workers)
            try:
                futures = {}
                for eval_item, cfg in config_tasks:
                    future = executor.submit(
                        run_single_eval,
                        eval_item=eval_item,
                        config=cfg,
                        workspace=workspace,
                        project_root=project_root,
                        executor_model=executor_model,
                        grader_model=grader_model,
                        timeout=timeout,
                        verbose=verbose,
                        skill_path=skill_path,
                    )
                    futures[future] = (eval_item["id"], cfg)

                for future in as_completed(futures):
                    eval_id, cfg = futures[future]
                    try:
                        grading = future.result(timeout=timeout + 120)
                        all_results[(eval_id, cfg)] = grading
                    except TimeoutError:
                        print(f"Timeout in eval-{eval_id}/{cfg}: exceeded {timeout + 120}s", file=sys.stderr)
                    except Exception as e:
                        print(f"Error in eval-{eval_id}/{cfg}: {e}", file=sys.stderr)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
        else:
            # Sequential execution (required for without_skill due to file hide/restore)
            for eval_item, cfg in config_tasks:
                try:
                    grading = run_single_eval(
                        eval_item=eval_item,
                        config=cfg,
                        workspace=workspace,
                        project_root=project_root,
                        executor_model=executor_model,
                        grader_model=grader_model,
                        timeout=timeout,
                        verbose=verbose,
                        skill_path=skill_path,
                    )
                    all_results[(eval_item["id"], cfg)] = grading
                except Exception as e:
                    print(f"Error in eval-{eval_item['id']}/{cfg}: {e}", file=sys.stderr)

    # Build summary
    summary = {}
    for config in configs:
        config_results = {
            eid: g for (eid, cfg), g in all_results.items() if cfg == config
        }
        pass_rates = []
        for eid, grading in config_results.items():
            s = grading.get("summary", {})
            pass_rates.append(s.get("pass_rate", 0.0))

        avg_pass_rate = sum(pass_rates) / len(pass_rates) if pass_rates else 0.0
        summary[config] = {
            "evals_run": len(config_results),
            "avg_pass_rate": round(avg_pass_rate, 4),
            "pass_rates": {str(eid): pr for eid, pr in zip(config_results.keys(), pass_rates)},
        }

    if len(configs) >= 2:
        delta = summary[configs[0]]["avg_pass_rate"] - summary[configs[1]]["avg_pass_rate"]
        summary["delta"] = round(delta, 4)

    return {
        "skill_name": evals_data.get("skill_name", skill_path.name),
        "evals_run": [e["id"] for e in evals_list],
        "configs": configs,
        "summary": summary,
        "results": {
            f"eval-{eid}/{cfg}": {
                "pass_rate": g.get("summary", {}).get("pass_rate", 0.0),
                "passed": g.get("summary", {}).get("passed", 0),
                "failed": g.get("summary", {}).get("failed", 0),
                "total": g.get("summary", {}).get("total", 0),
            }
            for (eid, cfg), g in all_results.items()
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run functional evaluation for a skill"
    )
    parser.add_argument(
        "--evals-json",
        required=True,
        help="Path to evals.json with test cases",
    )
    parser.add_argument(
        "--skill-path",
        required=True,
        help="Path to skill directory (containing SKILL.md)",
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Path to workspace directory for outputs",
    )
    parser.add_argument(
        "--executor-model",
        default=None,
        help="Model for executor (default: user's configured model)",
    )
    parser.add_argument(
        "--grader-model",
        default="claude-sonnet-4-6",
        help="Model for grading (default: claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Timeout per executor run in seconds (default: 180)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Max parallel executor runs for with_skill config (default: 3)",
    )
    parser.add_argument(
        "--eval-ids",
        type=str,
        default=None,
        help="Comma-separated list of eval IDs to run (default: all)",
    )
    parser.add_argument(
        "--configs",
        type=str,
        default="with_skill,without_skill",
        help="Comma-separated configs to run (default: with_skill,without_skill)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress to stderr",
    )
    args = parser.parse_args()

    evals_path = Path(args.evals_json)
    skill_path = Path(args.skill_path)
    workspace = Path(args.workspace)

    if not evals_path.exists():
        print(f"Error: evals file not found: {evals_path}", file=sys.stderr)
        sys.exit(1)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    eval_ids = None
    if args.eval_ids:
        eval_ids = [int(x.strip()) for x in args.eval_ids.split(",")]

    configs = [c.strip() for c in args.configs.split(",")]

    results = run_functional_evals(
        evals_path=evals_path,
        skill_path=skill_path,
        workspace=workspace,
        executor_model=args.executor_model,
        grader_model=args.grader_model,
        timeout=args.timeout,
        max_workers=args.max_workers,
        verbose=args.verbose,
        eval_ids=eval_ids,
        configs=configs,
    )

    # Save results summary
    results_path = workspace / "functional_eval_results.json"
    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    print(json.dumps(results, indent=2, ensure_ascii=False))

    if args.verbose:
        print(f"\nResults saved to: {results_path}", file=sys.stderr)
        summary = results["summary"]
        for config in configs:
            cs = summary.get(config, {})
            print(
                f"  {config}: avg_pass_rate={cs.get('avg_pass_rate', 0):.0%}",
                file=sys.stderr,
            )
        if "delta" in summary:
            print(f"  delta: {summary['delta']:+.4f}", file=sys.stderr)


if __name__ == "__main__":
    main()
