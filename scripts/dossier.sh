#!/usr/bin/env bash
# FORGE source-of-truth lookup. The verbatim documents are the ONLY authority.
#   scripts/dossier.sh verify              -> integrity check of all source-of-truth docs (sha256)
#   scripts/dossier.sh [-d] toc            -> section index with line numbers
#   scripts/dossier.sh [-d] section 21     -> print a section verbatim (also 21.2, 0 ...)
#   scripts/dossier.sh [-d] grep <regex>   -> case-insensitive search with line numbers
#   -d selects the DIRECTIVE (operator answers, newer, wins conflicts); default is the DOSSIER.
#   See docs/source-of-truth/RESOLUTIONS.md for how the two are reconciled.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="$ROOT/docs/source-of-truth"
DOC="$DIR/FORGE_MASTER_BUILD_DOSSIER.md"
if [[ "${1:-}" == "-d" ]]; then DOC="$DIR/FORGE_AUTONOMOUS_BUILD_DIRECTIVE.md"; shift; fi

verify() {
  local f
  for f in "$DIR"/*.sha256; do
    (cd "$DIR" && sha256sum --quiet -c "$(basename "$f")") \
      || { echo "SOURCE-OF-TRUTH INTEGRITY FAILURE ($f) — STOP AND TELL THE USER" >&2; exit 2; }
  done
}

case "${1:-}" in
  verify) verify; echo "OK: all source-of-truth documents intact:"; cut -c1-16,65- "$DIR"/*.sha256;;
  toc)    verify; grep -nE '^#{1,2} [0-9]+(\.[0-9]+)? |^# [0-9]+\.' "$DOC";;
  section)
    verify; n="${2:?section number required, e.g. 21 or 21.2}"
    awk -v n="$n" '
      BEGIN { depth = (index(n, ".") ? 2 : 1); hdr = (depth == 1 ? "# " : "## ") n "[ .]" }
      !p && $0 ~ "^" hdr { p = 1; print; next }
      p && depth == 1 && /^# [0-9]+\. / { exit }
      p && depth == 2 && /^#{1,2} [0-9]+[. ]/ { exit }
      p { print }' "$DOC";;
  grep)   verify; shift; grep -niE -- "$*" "$DOC";;
  *) sed -n '2,9p' "$0"; exit 1;;
esac
