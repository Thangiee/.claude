#!/bin/bash
input=$(cat)

# Debug mode: DEBUG_STATUSLINE=1 claude
[ -n "$DEBUG_STATUSLINE" ] && echo "$input" >> ~/.claude/statusline-debug.json && echo "---" >> ~/.claude/statusline-debug.json

# Parse all values efficiently
eval "$(echo "$input" | jq -r '
  @sh "model_name=\(.model.display_name // "Unknown")",
  @sh "model_id=\(.model.id // "")",
  @sh "session_id=\(.session_id // "")",
  @sh "cwd=\(.workspace.current_dir // "")",
  @sh "total_input=\(.context_window.total_input_tokens // 0)",
  @sh "total_output=\(.context_window.total_output_tokens // 0)",
  @sh "used_pct=\(.context_window.used_percentage // "")",
  @sh "context_size=\(.context_window.context_window_size // 200000)",
  @sh "cache_read=\(.context_window.current_usage.cache_read_input_tokens // 0)",
  @sh "official_cost=\(.cost.total_cost_usd // 0)"
' 2>/dev/null | tr '\n' ' ')"

# Defaults
model_name="${model_name:-Unknown}"
total_input="${total_input:-0}"
total_output="${total_output:-0}"
official_cost="${official_cost:-0}"

# ANSI colors - BRIGHT for visibility
CYAN='\033[96m'
BLUE='\033[94m'
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
MAGENTA='\033[95m'
WHITE='\033[97m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# Model pricing for per-model breakdown
get_model_price() {
  case "$1" in
    *"opus-4"*)   echo "15.00 75.00";;
    *"sonnet-4"*) echo "3.00 15.00";;
    *"haiku-4"*)  echo "0.80 4.00";;
    *"sonnet-3"*) echo "3.00 15.00";;
    *"haiku-3"*)  echo "0.25 1.25";;
    *)            echo "3.00 15.00";;
  esac
}

# Track per-model usage for breakdown display
usage_file="$HOME/.claude/session-env/${session_id}/model-usage.json"
if [ -n "$session_id" ]; then
  mkdir -p "$HOME/.claude/session-env/${session_id}" 2>/dev/null
  [ ! -f "$usage_file" ] && echo '{"models":{},"total_input":0,"total_output":0}' > "$usage_file"

  prev_total=$(jq -r '.total_input // 0' "$usage_file" 2>/dev/null || echo 0)
  prev_output=$(jq -r '.total_output // 0' "$usage_file" 2>/dev/null || echo 0)
  delta_input=$((total_input - prev_total))
  delta_output=$((total_output - prev_output))

  if [ $delta_input -gt 0 ] || [ $delta_output -gt 0 ]; then
    jq --arg model "$model_id" \
       --argjson d_in "$delta_input" \
       --argjson d_out "$delta_output" \
       --argjson t_in "$total_input" \
       --argjson t_out "$total_output" \
       '.models[$model].input = (.models[$model].input // 0) + $d_in |
        .models[$model].output = (.models[$model].output // 0) + $d_out |
        .total_input = $t_in |
        .total_output = $t_out' "$usage_file" > "${usage_file}.tmp" 2>/dev/null && mv "${usage_file}.tmp" "$usage_file"
  fi
fi

# Format cost (use official cost from Claude Code)
cost_display=$(printf "%.3f" ${official_cost:-0} 2>/dev/null || echo "0.000")

# Build status
status_parts=()

# Model - white bold
status_parts+=("$(printf "${WHITE}${BOLD}%s${RESET}" "$model_name")")

# Directory - cyan
[ -n "$cwd" ] && status_parts+=("$(printf "${CYAN}[%s]${RESET}" "$(basename "$cwd")")")

# Context usage - color coded
if [ -n "$used_pct" ] && [ "$used_pct" != "null" ]; then
  used_int=$(printf "%.0f" "$used_pct" 2>/dev/null || echo 0)
  if [ $used_int -ge 90 ]; then
    ctx_color="${RED}${BOLD}"
  elif [ $used_int -ge 75 ]; then
    ctx_color="${YELLOW}"
  else
    ctx_color="${GREEN}"
  fi
  status_parts+=("$(printf "${ctx_color}Ctx: %s%%${RESET}" "$used_pct")")
fi

# Tokens - blue
total_tokens=$((total_input + total_output))
if [ $total_tokens -gt 0 ]; then
  if [ $total_tokens -gt 1000000 ]; then
    tokens_display=$(printf "%.1fM" $(echo "$total_tokens / 1000000" | bc -l))
  elif [ $total_tokens -gt 1000 ]; then
    tokens_display=$(printf "%.1fK" $(echo "$total_tokens / 1000" | bc -l))
  else
    tokens_display="$total_tokens"
  fi
  status_parts+=("$(printf "${BLUE}%s tok${RESET}" "$tokens_display")")
fi

# Cache hits - dim cyan (if significant)
if [ "${cache_read:-0}" -gt 1000 ]; then
  cache_display=$(printf "%.1fK" $(echo "$cache_read / 1000" | bc -l))
  status_parts+=("$(printf "${DIM}${CYAN}cache: %s${RESET}" "$cache_display")")
fi

# Cost - color coded (using official Claude cost)
if [ -n "$official_cost" ] && (( $(echo "$official_cost > 0" | bc -l 2>/dev/null || echo 0) )); then
  if (( $(echo "$official_cost >= 1.0" | bc -l 2>/dev/null || echo 0) )); then
    cost_color="${RED}${BOLD}"
  elif (( $(echo "$official_cost >= 0.50" | bc -l 2>/dev/null || echo 0) )); then
    cost_color="${YELLOW}"
  else
    cost_color="${GREEN}"
  fi
  status_parts+=("$(printf "${cost_color}\$%s${RESET}" "$cost_display")")
fi

# Per-model breakdown (if multiple models used)
if [ -f "$usage_file" ]; then
  model_count=$(jq '.models | length' "$usage_file" 2>/dev/null || echo 0)
  if [ "$model_count" -gt 1 ]; then
    breakdown=""
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      m_id=$(echo "$line" | jq -r '.model')
      m_input=$(echo "$line" | jq -r '.input')
      m_output=$(echo "$line" | jq -r '.output')

      case "$m_id" in
        *"opus-4"*)   m_short="O4";;
        *"sonnet-4"*) m_short="S4";;
        *"haiku-4"*)  m_short="H4";;
        *"opus-3"*)   m_short="O3";;
        *"sonnet-3"*) m_short="S3";;
        *"haiku-3"*)  m_short="H3";;
        *)            m_short="??";;
      esac

      read m_price_in m_price_out < <(get_model_price "$m_id")
      m_cost=$(printf "%.2f" $(echo "scale=4; ($m_input / 1000000 * $m_price_in) + ($m_output / 1000000 * $m_price_out)" | bc 2>/dev/null || echo "0"))

      m_total=$((m_input + m_output))
      if [ $m_total -gt 1000 ]; then
        m_tokens=$(printf "%.1fK" $(echo "$m_total / 1000" | bc -l))
      else
        m_tokens="$m_total"
      fi

      [ -n "$breakdown" ] && breakdown="${breakdown} "
      breakdown="${breakdown}${m_short}:${m_tokens}(\$${m_cost})"
    done < <(jq -c '.models | to_entries[]? | {model: .key, input: .value.input, output: .value.output}' "$usage_file" 2>/dev/null)

    [ -n "$breakdown" ] && status_parts+=("$(printf "${MAGENTA}%s${RESET}" "$breakdown")")
  fi
fi

# Join with separators
output=""
for i in "${!status_parts[@]}"; do
  [ $i -eq 0 ] && output="${status_parts[$i]}" || output="$output $(printf "${DIM}|${RESET}") ${status_parts[$i]}"
done

printf "%b\n" "$output"
