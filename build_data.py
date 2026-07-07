#!/usr/bin/env python3
"""
Lê data/snapshots/*.csv e gera docs/data.json + copia avatares para docs/avatars/.
Deve ser executado após cada scrape.
"""
import csv
import json
import shutil
from pathlib import Path

ROOT      = Path(__file__).parent
SNAPSHOTS = ROOT / "data" / "snapshots"
AVATARS   = ROOT / "data" / "avatars"
DOCS      = ROOT / "docs"
DOCS_AVT  = DOCS / "avatars"

DOCS.mkdir(exist_ok=True)
DOCS_AVT.mkdir(exist_ok=True)

# Copia avatares para docs/avatars/
copied = 0
for src in AVATARS.glob("*"):
    dst = DOCS_AVT / src.name
    shutil.copy2(src, dst)
    copied += 1

days = []
for csv_file in sorted(SNAPSHOTS.glob("*.csv")):
    with open(csv_file, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        continue

    entries = []
    for row in rows:
        avatar_path = row.get("avatar_path", "").strip()
        # Caminho relativo dentro de docs/ → "avatars/9.png"
        if avatar_path:
            avatar_path = "avatars/" + Path(avatar_path).name

        entries.append({
            "user_id":   row["user_id"],
            "name":      row["name"],
            "full_name": row["full_name"],
            "position":  int(row["position"]) if row["position"] else 0,
            "points":    int(row["points"])    if row["points"]   else 0,
            "avatar":    avatar_path,
        })

    entries.sort(key=lambda x: x["position"])
    days.append({"date": rows[0]["date"], "entries": entries})

output = DOCS / "data.json"
output.write_text(json.dumps({"days": days}, ensure_ascii=False, indent=2))
print(f"Gerado: {output}")
print(f"  {len(days)} dias | {len(days[0]['entries']) if days else 0} boleiros | {copied} avatares copiados")
