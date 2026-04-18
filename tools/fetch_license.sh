#!/usr/bin/env bash
# Fetch the verbatim PolyForm Noncommercial 1.0.0 license text
# and write it to ./LICENSE, replacing the placeholder.
#
# Run this ONCE, locally, before publishing the repository.
#
# Usage:
#   ./tools/fetch_license.sh
set -euo pipefail

URL="https://raw.githubusercontent.com/polyformproject/polyform-licenses/1.0.0/PolyForm-Noncommercial-1.0.0.md"
TARGET="LICENSE"

if ! command -v curl >/dev/null 2>&1; then
    echo "error: curl is required" >&2
    exit 1
fi

echo "Fetching PolyForm Noncommercial 1.0.0 from $URL ..."
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
curl --fail --silent --show-error --location "$URL" -o "$tmp"

# Sanity check — the canonical file starts with "# PolyForm Noncommercial"
if ! head -n 1 "$tmp" | grep -q "PolyForm Noncommercial"; then
    echo "error: fetched content does not look like the PolyForm license" >&2
    head -n 3 "$tmp" >&2
    exit 2
fi

# Keep the existing SPDX identifier line at the top of LICENSE, then
# append the canonical license text.
{
    echo "SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
    echo ""
    cat "$tmp"
} > "$TARGET"

echo "Wrote $TARGET ($(wc -l < "$TARGET") lines)."
