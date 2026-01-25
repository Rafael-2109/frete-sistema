#!/usr/bin/env python3
"""
Initialize Ralph Wiggum structure in a project.

Usage:
    python init_ralph_project.py [--force]

Creates:
    - specs/.gitkeep
    - AGENTS.md (template)
    - PROMPT_plan.md (template)
    - PROMPT_build.md (template)
    - ralph-loop.sh (executable)
    - Dockerfile.ralph
    - docker-compose.ralph.yml
"""

import os
import sys
import stat
from pathlib import Path

AGENTS_TEMPLATE = '''## Build & Run

- Build: `[your build command]`
- Run: `[your run command]`
- Test: `[your test command]`

## Validation

Run these after implementing to get immediate feedback:

- Tests: `[test command]`
- Typecheck: `[typecheck command]`
- Lint: `[lint command]`

## Operational Notes

[Add project-specific notes here]

### Codebase Patterns

[Document your project's patterns here]
'''

PROMPT_PLAN_TEMPLATE = '''0a. Study `specs/*` with up to 250 parallel subagents to learn specifications.
0b. Study @IMPLEMENTATION_PLAN.md (if present) to understand the plan so far.
0c. Study `src/` with up to 250 parallel subagents to understand existing code.
0d. Reference any project documentation for conventions.

1. Use up to 500 subagents to study existing source code and compare against `specs/*`. Analyze findings, prioritize tasks, and create/update @IMPLEMENTATION_PLAN.md as a bullet point list sorted by priority. Ultrathink. Consider searching for TODO, minimal implementations, placeholders, skipped tests, and inconsistent patterns.

IMPORTANT: Plan only. Do NOT implement anything. Do NOT assume functionality is missing; confirm with code search first.

ULTIMATE GOAL: [Descrever objetivo específico do projeto aqui]
'''

PROMPT_BUILD_TEMPLATE = '''0a. Study `specs/*` with up to 500 parallel subagents to learn specifications.
0b. Study @IMPLEMENTATION_PLAN.md.
0c. Reference project documentation for conventions.

1. Implement functionality per specifications following @IMPLEMENTATION_PLAN.md. Choose the most important item. Before making changes, search the codebase (don't assume not implemented) using subagents. Use up to 500 parallel subagents for searches/reads and only 1 subagent for build/tests. Use subagents for complex reasoning when needed.

2. After implementing, run tests for that unit of code. If functionality is missing, add it per specifications. Ultrathink.

3. When you discover issues, immediately update @IMPLEMENTATION_PLAN.md with your findings. When resolved, update and remove the item.

4. When tests pass, update @IMPLEMENTATION_PLAN.md, then `git add -A` then `git commit` with descriptive message. After commit, `git push`.

99999. Capture the why in documentation.
999999. Single sources of truth, no migrations/adapters. If unrelated tests fail, resolve them.
9999999. Create git tag on clean builds (start 0.0.0, increment patch).
99999999. Add extra logging if needed for debugging.
999999999. Keep @IMPLEMENTATION_PLAN.md current with learnings.
9999999999. Update @AGENTS.md with operational learnings (keep brief).
99999999999. Resolve or document bugs in @IMPLEMENTATION_PLAN.md.
999999999999. Implement completely. No placeholders or stubs.
9999999999999. Periodically clean completed items from @IMPLEMENTATION_PLAN.md.
99999999999999. Use Opus 4.5 subagent with 'ultrathink' for spec inconsistencies.
999999999999999. Keep @AGENTS.md operational only — progress notes go in IMPLEMENTATION_PLAN.md.
'''

LOOP_SCRIPT = '''#!/bin/bash
# Ralph Wiggum Loop - Autonomous AI Development
# Usage: ./ralph-loop.sh [plan] [max_iterations]

if [ "$1" = "plan" ]; then
    MODE="plan"
    PROMPT_FILE="PROMPT_plan.md"
    MAX_ITERATIONS=${2:-0}
elif [[ "$1" =~ ^[0-9]+$ ]]; then
    MODE="build"
    PROMPT_FILE="PROMPT_build.md"
    MAX_ITERATIONS=$1
else
    MODE="build"
    PROMPT_FILE="PROMPT_build.md"
    MAX_ITERATIONS=0
fi

ITERATION=0
CURRENT_BRANCH=$(git branch --show-current)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 Ralph Wiggum Loop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Mode:   $MODE"
echo "Prompt: $PROMPT_FILE"
echo "Branch: $CURRENT_BRANCH"
[ $MAX_ITERATIONS -gt 0 ] && echo "Max:    $MAX_ITERATIONS iterations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -f "$PROMPT_FILE" ]; then
    echo "❌ Error: $PROMPT_FILE not found"
    exit 1
fi

while true; do
    if [ $MAX_ITERATIONS -gt 0 ] && [ $ITERATION -ge $MAX_ITERATIONS ]; then
        echo "✅ Reached max iterations: $MAX_ITERATIONS"
        break
    fi

    cat "$PROMPT_FILE" | claude -p \\
        --dangerously-skip-permissions \\
        --output-format=stream-json \\
        --model opus \\
        --verbose

    git push origin "$CURRENT_BRANCH" 2>/dev/null || {
        echo "📤 Creating remote branch..."
        git push -u origin "$CURRENT_BRANCH"
    }

    ITERATION=$((ITERATION + 1))
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "                     LOOP $ITERATION COMPLETE"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
done

echo "🏁 Ralph loop finished after $ITERATION iterations"
'''

DOCKERFILE_TEMPLATE = '''FROM python:3.12-slim

RUN apt-get update && apt-get install -y \\
    git curl nodejs npm \\
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY . .

RUN git config --global user.email "ralph@container.local" && \\
    git config --global user.name "Ralph Wiggum"

ENTRYPOINT ["/bin/bash"]
'''

COMPOSE_TEMPLATE = '''version: '3.8'

services:
  ralph:
    build:
      context: .
      dockerfile: Dockerfile.ralph
    volumes:
      - .:/app
      - ~/.anthropic:/root/.anthropic:ro
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    working_dir: /app
    stdin_open: true
    tty: true
'''


def main():
    force = '--force' in sys.argv
    project_root = Path.cwd()

    files = {
        'specs/.gitkeep': '',
        'AGENTS.md': AGENTS_TEMPLATE,
        'PROMPT_plan.md': PROMPT_PLAN_TEMPLATE,
        'PROMPT_build.md': PROMPT_BUILD_TEMPLATE,
        'ralph-loop.sh': LOOP_SCRIPT,
        'Dockerfile.ralph': DOCKERFILE_TEMPLATE,
        'docker-compose.ralph.yml': COMPOSE_TEMPLATE,
    }

    created = []
    skipped = []

    for filepath, content in files.items():
        full_path = project_root / filepath

        # Create directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if full_path.exists() and not force:
            skipped.append(filepath)
            continue

        full_path.write_text(content)
        created.append(filepath)

        # Make script executable
        if filepath.endswith('.sh'):
            current = full_path.stat().st_mode
            full_path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print("🤖 Ralph Wiggum structure initialized!")
    print()

    if created:
        print("✅ Created:")
        for f in created:
            print(f"   - {f}")

    if skipped:
        print()
        print("⏭️  Skipped (already exists, use --force to overwrite):")
        for f in skipped:
            print(f"   - {f}")

    print()
    print("Next steps:")
    print("1. Edit AGENTS.md with your project's commands")
    print("2. Create specs in specs/ directory")
    print("3. Run: ./ralph-loop.sh plan 3")


if __name__ == '__main__':
    main()
