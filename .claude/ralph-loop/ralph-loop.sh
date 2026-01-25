#!/bin/bash
# Ralph Wiggum Loop - Autonomous AI Development
# Usage: ./ralph-loop.sh [plan] [max_iterations]
# Examples:
#   ./ralph-loop.sh              # Build mode, unlimited
#   ./ralph-loop.sh 20           # Build mode, max 20 iterations
#   ./ralph-loop.sh plan         # Plan mode, unlimited
#   ./ralph-loop.sh plan 5       # Plan mode, max 5 iterations

# Get script directory (works even when called via symlink)
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

# Parse arguments
if [ "$1" = "plan" ]; then
    MODE="plan"
    PROMPT_FILE="$SCRIPT_DIR/PROMPT_plan.md"
    MAX_ITERATIONS=${2:-0}
elif [[ "$1" =~ ^[0-9]+$ ]]; then
    MODE="build"
    PROMPT_FILE="$SCRIPT_DIR/PROMPT_build.md"
    MAX_ITERATIONS=$1
else
    MODE="build"
    PROMPT_FILE="$SCRIPT_DIR/PROMPT_build.md"
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

# Verify prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    echo "❌ Error: $PROMPT_FILE not found"
    exit 1
fi

# Verify we're in a git repo
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

echo ""
echo "🚀 Starting Ralph loop..."
echo "   Press Ctrl+C to stop"
echo ""

while true; do
    if [ $MAX_ITERATIONS -gt 0 ] && [ $ITERATION -ge $MAX_ITERATIONS ]; then
        echo "✅ Reached max iterations: $MAX_ITERATIONS"
        break
    fi

    # Run Ralph iteration with selected prompt
    # -p: Headless mode (non-interactive, reads from stdin)
    # --dangerously-skip-permissions: Auto-approve all tool calls (YOLO mode)
    # --model opus: Primary agent uses Opus for complex reasoning
    cat "$PROMPT_FILE" | claude -p \
        --dangerously-skip-permissions \
        --model opus
    # Push changes after each iteration
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

echo ""
echo "🏁 Ralph loop finished after $ITERATION iterations"
