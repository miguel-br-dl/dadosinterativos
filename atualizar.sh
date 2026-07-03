#!/usr/bin/env bash
# Atualiza scrape do dia e reconstrói o site.
# 
# Uso:
#   ./atualizar.sh 28/06        # coleta dia 28/06/2026
#   ./atualizar.sh              # usa a data de hoje automaticamente
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv/bin/python"

# ── Parse do parâmetro ──────────────────────────────────────────────────────
if [[ $# -ge 1 ]]; then
  INPUT="$1"   # esperado: dd/mm
  DD="${INPUT%%/*}"
  MM="${INPUT##*/}"
  # Determina o ano: se mm >= 06 é 2026 (Copa), senão 2027 (final/Copa)
  YEAR=2026
  END_DATE="${YEAR}-${MM}-${DD}"
  START_DATE="$END_DATE"
else
  END_DATE="$(date +%Y-%m-%d)"
  START_DATE="2026-06-10"
  DD="$(date +%d)"
  MM="$(date +%m)"
fi

echo "════════════════════════════════════════"
echo "  Bolão Copa 2026 — atualizando ${DD}/${MM}/2026"
echo "════════════════════════════════════════"

# ── Scraper ─────────────────────────────────────────────────────────────────
echo ""
echo "▶ Scraping de 10/06/2026 até ${END_DATE}..."
"$VENV" "$ROOT/scraper.py" --start "$START_DATE" --end "$END_DATE" --force

# ── Build do site ────────────────────────────────────────────────────────────
echo ""
echo "▶ Gerando docs/data.json e copiando avatares..."
"$VENV" "$ROOT/build_data.py"

echo ""
echo "✓ Pronto! Para visualizar localmente:"
echo "  cd $ROOT && python3 -m http.server 8765"
echo "  Abrir: http://localhost:8765/docs/"
echo ""
echo "  Para publicar no GitHub Pages:"
echo "  git add docs/ data/snapshots/ data/avatars/"
echo "  git commit -m 'atualiza bolão ${DD}/${MM}'"
echo "  git push"
