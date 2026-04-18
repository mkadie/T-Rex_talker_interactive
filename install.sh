#!/usr/bin/env bash
# install.sh — overlay installer for T-Rex Talker Interactive
#
# Usage:
#   ./install.sh /path/to/your/trextalkv3
#
# What it does:
#   1. Copies stim_games/, new menus, tools/make_trainer_sounds.py,
#      and T-Rex_Talker_Subprogram.md into the target T-Rex Talker
#      checkout.
#   2. Backs up each file in upstream_patches/ to <file>.pre_interactive.bak
#      in the target, then overwrites with the patched version.
#
# What it does NOT do:
#   - Push anything to SD or the device — that's the existing T-Rex
#     Talker installer's job. Run this against your source checkout,
#     then run the T-Rex Talker installer to deploy to the device.
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 /path/to/your/trextalkv3" >&2
    exit 1
fi

TARGET="$1"
SRC="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$TARGET" ]; then
    echo "error: target directory does not exist: $TARGET" >&2
    exit 2
fi
# A reasonable heuristic to confirm we're pointed at a T-Rex Talker
# checkout: code.py + machine.py + menus/ all present.
for mandatory in "code.py" "machine.py" "menus"; do
    if [ ! -e "$TARGET/$mandatory" ]; then
        echo "warning: '$TARGET' doesn't contain '$mandatory' — is this really a T-Rex Talker checkout?" >&2
    fi
done

echo "Installing T-Rex Talker Interactive overlay into: $TARGET"
echo

# 1. Pure-new files — copy into place
copy_tree () {
    # copy_tree <src-subdir> <dest-subdir>
    local src="$SRC/$1"
    local dst="$TARGET/$2"
    mkdir -p "$dst"
    echo "  copy:   $1/* -> ${2%/}/"
    cp -R "$src/." "$dst/"
}

copy_tree "stim_games" "stim_games"
copy_tree "menus" "menus"          # games.menu, trainer.menu, base_with_games.menu
mkdir -p "$TARGET/tools"
cp "$SRC/tools/make_trainer_sounds.py" "$TARGET/tools/"
echo "  copy:   tools/make_trainer_sounds.py"
cp "$SRC/T-Rex_Talker_Subprogram.md" "$TARGET/"
echo "  copy:   T-Rex_Talker_Subprogram.md"

echo
# 2. Patched upstream files — back up originals, then overwrite
apply_patch () {
    local rel="$1"
    local src="$SRC/upstream_patches/$rel"
    local dst="$TARGET/$rel"
    if [ ! -f "$dst" ]; then
        echo "  new:    $rel (no upstream file to back up)"
    else
        if [ ! -e "$dst.pre_interactive.bak" ]; then
            cp "$dst" "$dst.pre_interactive.bak"
            echo "  backup: $rel.pre_interactive.bak"
        else
            echo "  backup: already exists, skipping ($rel.pre_interactive.bak)"
        fi
    fi
    cp "$src" "$dst"
    echo "  patch:  $rel"
}

apply_patch "action.py"
apply_patch "machine.py"
apply_patch "config_reader.py"
apply_patch "config.txt"
apply_patch "menu_system.md"

echo
echo "Done. Next steps:"
echo "  1. Review the changes to your T-Rex Talker checkout."
echo "  2. Run your normal T-Rex Talker installer to flash the device."
echo "  3. (Optional) Generate trainer sound files:"
echo "       python $TARGET/tools/make_trainer_sounds.py --out $TARGET/sounds/trainer"
echo "  4. (Optional) Boot into the trainer by adding to $TARGET/config.txt:"
echo "       mode = stim_games/aac_trainer.py"
