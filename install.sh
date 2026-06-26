#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${RESEARCH_BUNDLE_REPO_URL:-https://github.com/murranli/research-bundle.git}"
REF="${RESEARCH_BUNDLE_REF:-main}"
TARGETS=()
DRY_RUN=0
SOURCE_DIR=""

usage() {
  cat <<'EOF'
将 Research Bundle 安装到本地 Agent Skills 目录。

用法：
  install.sh [--target DIR] [--source DIR] [--repo URL] [--ref REF] [--dry-run]

示例：
  curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/install.sh | bash
  curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/install.sh | bash -s -- --target "$HOME/.claude/skills"
  ./install.sh --target "$HOME/.codex/skills"
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      [ "$#" -ge 2 ] || { echo "--target 缺少目录参数" >&2; exit 2; }
      TARGETS+=("$2")
      shift 2
      ;;
    --source)
      [ "$#" -ge 2 ] || { echo "--source 缺少目录参数" >&2; exit 2; }
      SOURCE_DIR="$2"
      shift 2
      ;;
    --repo)
      [ "$#" -ge 2 ] || { echo "--repo 缺少仓库地址" >&2; exit 2; }
      REPO_URL="$2"
      shift 2
      ;;
    --ref)
      [ "$#" -ge 2 ] || { echo "--ref 缺少分支或标签名" >&2; exit 2; }
      REF="$2"
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

script_dir=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [ -z "$SOURCE_DIR" ] && [ -n "$script_dir" ] && [ -d "$script_dir/entropy-research-bundle" ]; then
  SOURCE_DIR="$script_dir/entropy-research-bundle"
fi

tmp_dir=""
cleanup() {
  if [ -n "$tmp_dir" ] && [ -d "$tmp_dir" ]; then
    rm -rf "$tmp_dir"
  fi
}
trap cleanup EXIT

if [ -z "$SOURCE_DIR" ]; then
  tmp_dir="$(mktemp -d)"
  if command -v git >/dev/null 2>&1; then
    log "正在从 $REPO_URL 下载 Research Bundle（$REF）..."
    git clone --depth 1 --branch "$REF" "$REPO_URL" "$tmp_dir/repo" >/dev/null
  elif command -v curl >/dev/null 2>&1 && command -v tar >/dev/null 2>&1; then
    log "正在从 GitHub 下载 Research Bundle 压缩包（$REF）..."
    curl -fsSL "https://github.com/murranli/research-bundle/archive/refs/heads/$REF.tar.gz" | tar -xz -C "$tmp_dir"
    mv "$tmp_dir"/research-bundle-* "$tmp_dir/repo"
  else
    echo "安装需要 git，或 curl + tar。" >&2
    exit 1
  fi
  SOURCE_DIR="$tmp_dir/repo/entropy-research-bundle"
fi

if [ ! -d "$SOURCE_DIR" ]; then
  echo "找不到技能包源目录：$SOURCE_DIR" >&2
  exit 1
fi

if [ "${#TARGETS[@]}" -eq 0 ]; then
  [ -d "$HOME/.codex/skills" ] && TARGETS+=("$HOME/.codex/skills")
  [ -d "$HOME/.claude/skills" ] && TARGETS+=("$HOME/.claude/skills")
fi

if [ "${#TARGETS[@]}" -eq 0 ]; then
  cat >&2 <<'EOF'
没有找到支持的 Agent Skills 目录。

请先创建目录，或用 --target 明确指定，例如：
  bash install.sh --target "$HOME/.claude/skills"
  bash install.sh --target "$HOME/.codex/skills"
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
)

legacy_items=(
  "entropy-research"
)

for target in "${TARGETS[@]}"; do
  log "正在安装 Research Bundle 到 $target"
  run mkdir -p "$target"
  stamp="$(date +%Y%m%d%H%M%S)"

  for item in "${legacy_items[@]}"; do
    legacy="$target/$item"
    if [ -e "$legacy" ]; then
      backup="$target/.research-bundle-backup-$stamp/$item"
      log "发现旧版目录，先备份：$legacy -> $backup"
      run mkdir -p "$(dirname "$backup")"
      run mv "$legacy" "$backup"
    fi
  done

  for item in "${items[@]}"; do
    src="$SOURCE_DIR/$item"
    dst="$target/$item"
    if [ ! -e "$src" ]; then
      echo "技能包缺少目录：$src" >&2
      exit 1
    fi
    if [ -e "$dst" ]; then
      backup="$target/.research-bundle-backup-$stamp/$item"
      log "发现已有目录，先备份：$dst -> $backup"
      run mkdir -p "$(dirname "$backup")"
      run mv "$dst" "$backup"
    fi
    run cp -R "$src" "$dst"
    run find "$dst" -name "__pycache__" -type d -prune -exec rm -rf "{}" "+"
    run find "$dst" -name "*.pyc" -type f -delete
  done
done

log "Research Bundle 安装完成。"
log "如果你的 Agent 没有自动发现新技能，请重启或刷新它，然后调用：research"
