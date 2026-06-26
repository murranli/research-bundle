#!/usr/bin/env bash
set -euo pipefail

TARGETS=()
DRY_RUN=0

usage() {
  cat <<'EOF'
从本地 Agent Skills 目录卸载 Research Bundle。

用法：
  uninstall.sh [--target DIR] [--dry-run]

示例：
  curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/uninstall.sh | bash
  ./uninstall.sh --target "$HOME/.claude/skills"
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      [ "$#" -ge 2 ] || { echo "--target 缺少目录参数" >&2; exit 2; }
      TARGETS+=("$2")
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数：$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

log() {
  printf '%s\n' "$*"
}

run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] %q' "$1"
    shift
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  else
    "$@"
  fi
}

if [ "${#TARGETS[@]}" -eq 0 ]; then
  [ -d "$HOME/.codex/skills" ] && TARGETS+=("$HOME/.codex/skills")
  [ -d "$HOME/.claude/skills" ] && TARGETS+=("$HOME/.claude/skills")
fi

if [ "${#TARGETS[@]}" -eq 0 ]; then
  cat >&2 <<'EOF'
没有找到支持的 Agent Skills 目录。

如需指定目录，请使用：
  bash uninstall.sh --target "$HOME/.claude/skills"
  bash uninstall.sh --target "$HOME/.codex/skills"
EOF
  exit 1
fi

items=(
  "_shared"
  "research"
  "goal-decompose"
  "search-strategy"
  "retrieval-exec"
  "content-audit"
  "report-compose"
  "report-render"
  "review-deliver"
  "entropy-research"
)

removed=0

for target in "${TARGETS[@]}"; do
  log "正在检查 $target"
  for item in "${items[@]}"; do
    path="$target/$item"
    if [ -e "$path" ]; then
      log "删除 $path"
      run rm -rf "$path"
      removed=$((removed + 1))
    fi
  done
done

if [ "$removed" -eq 0 ]; then
  log "没有发现 Research Bundle 技能目录，无需卸载。"
else
  log "Research Bundle 卸载完成。"
fi

log "未删除任何 .entropy/ 运行记录、报告产物或第三方账号配置。"
