#!/usr/bin/env bash
# Clone each method as a git submodule and check out its PINNED commit.
# Idempotent: re-running only fixes up missing submodules / wrong refs.
# Pins live in bench.env (single source of truth).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# shellcheck disable=SC1091
# Load pins from bench.env (strip the ':=' make syntax into shell vars).
while IFS= read -r line; do
    case "$line" in
        *_URL*:=*|*_REF*:=*)
            key="${line%%:=*}"; key="$(echo "$key" | tr -d '[:space:]')"
            val="${line#*:=}";  val="$(echo "$val" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
            export "$key"="$val" ;;
    esac
done < bench.env

add_pin () {
    local name="$1" url="$2" ref="$3" path="submodules/$1"
    echo "== $name  ($ref)"
    if [ ! -e "$path/.git" ]; then
        git submodule add --force "$url" "$path" 2>/dev/null || git clone "$url" "$path"
    fi
    git -C "$path" fetch --all --tags --quiet || true
    if [ "$ref" != "HEAD" ]; then
        git -C "$path" checkout --quiet "$ref"
    fi
    # methods pull their OWN third-party submodules (e.g. PRISM -> PanoVGGT)
    git -C "$path" submodule update --init --recursive --quiet || true
    echo "   -> $(git -C "$path" rev-parse --short HEAD)"
}

add_pin PRISM-VGGT  "$PRISM_URL"    "$PRISM_REF"
add_pin Pi3         "$PI3_URL"      "$PI3_REF"
add_pin VGGT-SLAM   "$VGGTSLAM_URL" "$VGGTSLAM_REF"
add_pin map-anything "$MAPANY_URL"  "$MAPANY_REF"
add_pin LASER       "$LASER_URL"    "$LASER_REF"

echo ""
echo "All submodules pinned. Next: make setup-all"
