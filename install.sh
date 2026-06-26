#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${RESEARCH_BUNDLE_REPO_URL:-https://github.com/murranli/research-bundle.git}"
REF="${RESEARCH_BUNDLE_REF:-main}"
TARGETS=()
DRY_RUN=0
SOURCE_DIR=""

usage() {
  cat <<'EOF'
Install Research Bundle into local Agent Skills directories.

Usage:
  install.sh [--target DIR] [--source DIR] [--repo URL] [--ref REF] [--dry-run]

Examples:
  curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/install.sh | bash
  curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/install.sh | bash -s -- --target "$HOME/.claude/skills"
  ./install.sh --target "$HOME/.codex/skills"
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      [ "$#" -ge 2 ] || { echo "Missing value for --target" >&2; exit 2; }
      TARGETS+=("$2")
      shift 2
      ;;
    --source)
      [ "$#" -ge 2 ] || { echo "Missing value for --source" >&2; exit 2; }
      SOURCE_DIR="$2"
      shift 2
      ;;
    --repo)
      [ "$#" -ge 2 ] || { echo "Missing value for --repo" >&2; exit 2; }
      REPO_URL="$2"
      shift 2
      ;;
    --ref)
      [ "$#" -ge 2 ] || { echo "Missing value for --ref" >&2; exit 2; }
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
      echo "Unknown argument: $1" >&2
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
    log "Downloading Research Bundle from $REPO_URL ($REF)..."
    git clone --depth 1 --branch "$REF" "$REPO_URL" "$tmp_dir/repo" >/dev/null
  elif command -v curl >/dev/null 2>&1 && command -v tar >/dev/null 2>&1; then
    log "Downloading Research Bundle archive from GitHub ($REF)..."
    curl -fsSL "https://github.com/murranli/research-bundle/archive/refs/heads/$REF.tar.gz" | tar -xz -C "$tmp_dir"
    mv "$tmp_dir"/research-bundle-* "$tmp_dir/repo"
  else
    echo "Install requires git, or curl + tar." >&2
    exit 1
  fi
  SOURCE_DIR="$tmp_dir/repo/entropy-research-bundle"
fi

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Cannot find bundle source directory: $SOURCE_DIR" >&2
  exit 1
fi

if [ "${#TARGETS[@]}" -eq 0 ]; then
  [ -d "$HOME/.codex/skills" ] && TARGETS+=("$HOME/.codex/skills")
  [ -d "$HOME/.claude/skills" ] && TARGETS+=("$HOME/.claude/skills")
fi

if [ "${#TARGETS[@]}" -eq 0 ]; then
  cat >&2 <<'EOF'
No supported Agent Skills directory was found.

Create one or pass an explicit target, for example:
  bash install.sh --target "$HOME/.claude/skills"
  bash install.sh --target "$HOME/.codex/skills"
EOF
  exit 1
fi

items=(
  "_shared"
  "entropy-research"
  "goal-decompose"
  "search-strategy"
  "retrieval-exec"
  "content-audit"
  "report-compose"
  "report-render"
  "review-deliver"
)

for target in "${TARGETS[@]}"; do
  log "Installing Research Bundle into $target"
  run mkdir -p "$target"
  stamp="$(date +%Y%m%d%H%M%S)"

  for item in "${items[@]}"; do
    src="$SOURCE_DIR/$item"
    dst="$target/$item"
    if [ ! -e "$src" ]; then
      echo "Missing bundle item: $src" >&2
      exit 1
    fi
    if [ -e "$dst" ]; then
      backup="$target/.research-bundle-backup-$stamp/$item"
      log "Backing up existing $dst to $backup"
      run mkdir -p "$(dirname "$backup")"
      run mv "$dst" "$backup"
    fi
    run cp -R "$src" "$dst"
  done
done

log "Research Bundle installed."
log "Restart your agent if it does not detect new skills automatically, then invoke: entropy-research"
