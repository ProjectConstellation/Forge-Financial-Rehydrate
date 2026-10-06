#!/usr/bin/env bash
# FORGE source-of-truth lookup. The verbatim dossier is the ONLY authority.
#   scripts/dossier.sh verify          -> integrity check (sha256)
#   scripts/dossier.sh toc             -> section index with line numbers
#   scripts/dossier.sh section 21      -> print section 21 verbatim (also 21.2, 0, 47 ...)
#   scripts/dossier.sh grep <pattern>  -> case-insensitive search with line numbers
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="$ROOT/docs/source-of-truth"
DOC="$DIR/FORGE_MASTER_BUILD_DOSSIER.md"

verify() {
  (cd "$DIR" && sha256sum --quiet -c FORGE_MASTER_BUILD_DOSSIER.md.sha256) \
    || { echo "DOSSIER INTEGRITY FAILURE — STOP AND TELL THE USER" >&2; exit 2; }
}

case "${1:-}" in
  verify) verify; echo "OK: dossier intact ($(cut -c1-16 "$DIR/FORGE_MASTER_BUILD_DOSSIER.md.sha256")…)";;
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
  *) sed -n '2,6p' "$0"; exit 1;;
esac
