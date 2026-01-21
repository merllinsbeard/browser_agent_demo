#!/usr/bin/env bash
# ralph.sh - Universal Ralph Wiggum Loop for AI Coding CLIs
# Supports: Claude Code, OpenCode, Custom agents
# Usage: ./ralph.sh -n 10 --agent claude

set -euo pipefail

# ============================================================================
# Configuration (override via environment variables)
# ============================================================================
RALPH_AGENT="${RALPH_AGENT:-claude}"
RALPH_ITERATIONS="${RALPH_ITERATIONS:-1}"
RALPH_PROMPT="${RALPH_PROMPT:-ralph-prompt.md}"
RALPH_VERBOSE="${RALPH_VERBOSE:-false}"
RALPH_PROGRESS_FILE="${RALPH_PROGRESS_FILE:-progress.txt}"

# Custom agent (optional - for using other AI CLIs)
RALPH_CUSTOM_AGENT_CMD="${RALPH_CUSTOM_AGENT_CMD:-}"

# Telegram integration (optional)
HAS_TELEGRAM=false
TELEGRAM_LIB="$HOME/.claude/hooks/lib/telegram-lib.sh"

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Logging
# ============================================================================
log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_verbose() { [[ "$RALPH_VERBOSE" == "true" ]] && echo -e "${BLUE}[DEBUG]${NC} $1" || true; }

# ============================================================================
# Help
# ============================================================================
show_help() {
  cat << 'EOF'
ralph.sh - Universal Ralph Wiggum Loop for AI Coding CLIs

USAGE:
    ./ralph.sh [OPTIONS]

OPTIONS:
    -n, --iterations NUM    Number of iterations (default: 1)
    -a, --agent AGENT       Agent to use: claude|opencode|custom (default: claude)
    -p, --prompt FILE       Custom prompt file (default: ralph-prompt.md)
    -v, --verbose           Verbose output
    -h, --help              Show this help

EXAMPLES:
    ./ralph.sh                            # Single iteration with Claude (HITL mode)
    ./ralph.sh -n 10                      # 10 iterations with Claude (AFK mode)
    ./ralph.sh --agent opencode -n 5      # 5 iterations with OpenCode

ENVIRONMENT VARIABLES:
    RALPH_AGENT=opencode           Default agent
    RALPH_ITERATIONS=10            Default iterations
    RALPH_PROMPT=custom.md         Custom prompt file
    RALPH_CUSTOM_AGENT_CMD="..."   Command for custom agent

AGENTS:
    claude   - Claude Code CLI (claude --print)
    opencode - OpenCode CLI (opencode run)
    custom   - Your own CLI via RALPH_CUSTOM_AGENT_CMD

FILES:
    ralph-prompt.md    Prompt template (customize per project)
    progress.txt       Progress tracking between iterations

For more info: https://ghuntley.com/ralph/
EOF
}

# ============================================================================
# Argument Parsing
# ============================================================================
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -n|--iterations)
        RALPH_ITERATIONS="$2"
        shift 2
        ;;
      -a|--agent)
        RALPH_AGENT="$2"
        shift 2
        ;;
      -p|--prompt)
        RALPH_PROMPT="$2"
        shift 2
        ;;
      -v|--verbose)
        RALPH_VERBOSE=true
        shift
        ;;
      -h|--help)
        show_help
        exit 0
        ;;
      *)
        log_error "Unknown option: $1"
        show_help
        exit 1
        ;;
    esac
  done
}

# ============================================================================
# Validation
# ============================================================================
validate_agent() {
  case "$RALPH_AGENT" in
    claude|opencode|custom) ;;
    *)
      log_error "Unknown agent: $RALPH_AGENT (supported: claude, opencode, custom)"
      log_error "For custom agents, set RALPH_CUSTOM_AGENT_CMD"
      exit 1
      ;;
  esac
}

validate_iterations() {
  if ! [[ "$RALPH_ITERATIONS" =~ ^[1-9][0-9]*$ ]]; then
    log_error "Iterations must be a positive integer (got: $RALPH_ITERATIONS)"
    exit 1
  fi
}

validate_prompt() {
  if [[ ! -f "$RALPH_PROMPT" ]]; then
    log_warn "Prompt file not found: $RALPH_PROMPT - creating default"
    create_default_prompt
  fi
}

check_agent_installed() {
  # Skip check for custom agents (command provided by user)
  [[ "$RALPH_AGENT" == "custom" ]] && return 0

  if ! type "$RALPH_AGENT" &> /dev/null; then
    log_error "$RALPH_AGENT CLI not found. Please install it first."
    exit 1
  fi
}

check_speckit_files() {
  if ! git rev-parse --git-dir &> /dev/null; then
    log_warn "Not a git repository - commits won't work"
  fi
  [[ -f "$RALPH_PROGRESS_FILE" ]] || touch "$RALPH_PROGRESS_FILE"
}

# ============================================================================
# Default Prompt
# ============================================================================
create_default_prompt() {
  cat > "$RALPH_PROMPT" << 'PROMPT_EOF'
# Ralph Loop Iteration

Read these files to understand what to do:
- AGENTS.md (if exists)
- CLAUDE.md (if exists)
- .specify/ directory (if exists)
- README.md
- progress.txt (if exists)

## Your Task

1. Analyze the project documentation to understand current goals
2. Check git log and progress.txt to see what's already done
3. Decide which task has the highest priority
4. Implement ONE feature/fix
5. Run feedback loops (tests, lint, types) if available
6. Commit with descriptive message
7. Append your progress to progress.txt

## Completion

If ALL tasks from the documentation are complete, output exactly:
<promise>COMPLETE</promise>

## Rules

- ONE feature per iteration
- Commit after each feature
- Don't push to remote
- Update progress.txt with what you did
- Small steps, high quality
PROMPT_EOF
  log_ok "Created default prompt: $RALPH_PROMPT"
}

# ============================================================================
# Agent Commands
# ============================================================================

build_full_prompt() {
  local prompt_text progress_text

  if [[ -f "$RALPH_PROMPT" ]]; then
    prompt_text=$(cat "$RALPH_PROMPT")
  else
    prompt_text="Execute the next uncompleted task from tasks.md"
  fi

  progress_text=$(tail -30 "$RALPH_PROGRESS_FILE" 2>/dev/null || true)

  printf '%s\n\n---\n## Recent Progress:\n%s' "$prompt_text" "$progress_text"
}

run_agent() {
  local prompt="$1"

  case "$RALPH_AGENT" in
    claude)
      claude --print --dangerously-skip-permissions "$prompt"
      ;;
    opencode)
      OPENCODE_YOLO=true opencode run "$prompt"
      ;;
    custom)
      if [[ -z "$RALPH_CUSTOM_AGENT_CMD" ]]; then
        log_error "RALPH_CUSTOM_AGENT_CMD required for custom agent. Set it via:"
        log_error "  export RALPH_CUSTOM_AGENT_CMD='your-cli --print'"
        exit 1
      fi
      eval "$RALPH_CUSTOM_AGENT_CMD \"\$prompt\""
      ;;
  esac
}

# ============================================================================
# Telegram Notifications
# ============================================================================
init_telegram() {
  if [[ -f "$TELEGRAM_LIB" ]]; then
    # shellcheck source=/dev/null
    source "$TELEGRAM_LIB"
    HAS_TELEGRAM=true
    log_verbose "Telegram notifications enabled"
  else
    log_verbose "Telegram lib not found at $TELEGRAM_LIB"
  fi
}

send_notification() {
  local type="$1"   # success|error|info
  local message="$2"
  local project_name
  project_name=$(basename "$(pwd)")

  if [[ "$HAS_TELEGRAM" == "true" ]]; then
    local emoji
    case "$type" in
      success) emoji="✅" ;;
      error)   emoji="❌" ;;
      info)    emoji="📝" ;;
      *)       emoji="🤖" ;;
    esac

    local full_message="${emoji} <b>Ralph</b> [${project_name}]"$'\n'"${message}"
    send_telegram_message "$full_message" 2>/dev/null || log_warn "Failed to send Telegram notification"
  fi
}

# ============================================================================
# Main Loop
# ============================================================================
run_loop() {
  local iterations="$RALPH_ITERATIONS"

  log_info "Starting Ralph Loop"
  log_info "Agent: $RALPH_AGENT"
  log_info "Iterations: $iterations"
  log_info "Prompt: $RALPH_PROMPT"
  echo ""

  for ((i=1; i<=iterations; i++)); do
    echo "=============================================="
    log_info "Iteration $i / $iterations"
    echo "=============================================="
    echo ""

    # Build fresh prompt each iteration (includes latest progress)
    local full_prompt
    full_prompt=$(build_full_prompt)

    log_verbose "Prompt length: ${#full_prompt} chars"

    # Run agent and capture output
    local result=""
    local exit_code=0

    # Execute the agent command directly (no eval)
    set +e
    result=$(run_agent "$full_prompt" 2>&1)
    exit_code=$?
    set -e

    # Print output
    echo "$result"
    echo ""

    # Check for completion marker
    if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
      echo "=============================================="
      log_ok "All tasks complete!"
      log_ok "Finished in $i iteration(s)"
      echo "=============================================="
      send_notification "success" "Completed all tasks in $i iteration(s)"
      exit 0
    fi

    # Check for errors
    if [[ $exit_code -ne 0 ]]; then
      log_error "Agent exited with code $exit_code at iteration $i"
      send_notification "error" "Failed at iteration $i (exit code: $exit_code)"
      exit 1
    fi

    # Brief pause between iterations to avoid rate limiting
    if [[ $i -lt $iterations ]]; then
      log_verbose "Pausing 2 seconds before next iteration..."
      sleep 2
    fi
  done

  echo "=============================================="
  log_info "Completed $iterations iteration(s)"
  log_warn "COMPLETE marker not found - tasks may still remain"
  echo "=============================================="
  send_notification "info" "Finished $iterations iterations (no COMPLETE marker)"
}

# ============================================================================
# Main
# ============================================================================
main() {
  parse_args "$@"
  validate_agent
  validate_iterations
  check_agent_installed
  validate_prompt
  check_speckit_files
  init_telegram

  log_verbose "Configuration:"
  log_verbose "  Agent: $RALPH_AGENT"
  log_verbose "  Iterations: $RALPH_ITERATIONS"
  log_verbose "  Prompt: $RALPH_PROMPT"
  log_verbose "  Telegram: $HAS_TELEGRAM"

  run_loop
}

main "$@"
