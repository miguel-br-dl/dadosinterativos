#!/usr/bin/env python3
"""
Scraper do WebBolão — coleta classificação cumulativa dia a dia.

Estratégia: mantém filtroInicioData fixo em 10/06/2026 e incrementa
filtroFimData um dia por vez. O snapshot de cada dia representa os
pontos acumulados até aquele dia.

Uso:
    python scraper.py                    # 11/06/2026 até hoje
    python scraper.py --start 2026-06-15 # data inicial diferente
    python scraper.py --end 2026-06-20   # até data específica
    python scraper.py --force            # sobrescreve todos os dias
"""

import argparse
import csv
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import dotenv_values

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

BASE_URL = "https://www.webbolao.com.br"
BOLAO_ID = "13694"
FILTER_START = "10/06/2026"  # data de início fixa do filtro (dia antes do bolão)
BOLAO_START = date(2026, 6, 11)

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
AVATARS_DIR = DATA_DIR / "avatars"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE_URL}/14/app/classificacaoUserFut",
    "Origin": BASE_URL,
}


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

def create_session(email: str, password: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)

    r = session.get(f"{BASE_URL}/login", timeout=15)
    r.raise_for_status()

    m = re.search(r'name="_token"\s+value="([^"]+)"', r.text)
    if not m:
        raise RuntimeError("_token não encontrado na página de login")

    resp = session.post(f"{BASE_URL}/login", data={
        "_token": m.group(1),
        "email": email,
        "password": password,
    }, timeout=15, allow_redirects=True)

    if "login" in resp.url.lower():
        raise RuntimeError("Login falhou — verifique email/password no .env")

    print(f"  Login OK ({email})")
    return session


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

def fetch_classificacao(session: requests.Session, end_date: date) -> str:
    """Busca HTML da classificação cumulativa até end_date."""
    end_str = end_date.strftime("%d/%m/%Y")
    r = session.post(
        f"{BASE_URL}/14/app/classificacaoUserFut",
        data={
            "bolao": BOLAO_ID,
            "inF": "s",
            "filtro": "1",
            "filtroInicioData": FILTER_START,
            "filtroFimData": end_str,
            "filtroInicioFaseRodada": "1",
            "filtroFimFaseRodada": "9",
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.text


def parse_row(html: str, a_tag) -> dict | None:
    """Extrai todos os campos de uma linha da tabela a partir da tag <a> da lupa."""
    m = re.search(r"mostraApostas\((\d+),\d+,\d+,'([^']+)'\)", a_tag["onclick"])
    if not m:
        return None
    user_id, short_name = m.group(1), m.group(2)

    # Posição no ranking e variação
    pos_in_html = html.find(f"mostraApostas({user_id},")
    # Volta ~300 chars para pegar a célula de posição antes da lupa
    snippet_before = html[max(0, pos_in_html - 400):pos_in_html]
    pos_match = re.search(r'text-align:right">(\d+)<', snippet_before)
    rank_change_match = re.search(r'rankneutral|rankup|rankdown', snippet_before)
    rank_img = re.search(r'(rank(?:neutral|up|down))\.gif" title="(-?\d+)"', snippet_before)

    position = int(pos_match.group(1)) if pos_match else None
    rank_delta = int(rank_img.group(2)) if rank_img else 0
    rank_dir = rank_img.group(1).replace("rank", "") if rank_img else "neutral"

    # Campos após a lupa
    snippet_after = html[pos_in_html:pos_in_html + 600]

    # Avatar
    avatar_match = re.search(
        r'class="avatar"[^>]*src="([^"]+)"[^>]*title="([^"]+)"', snippet_after
    )
    avatar_url = avatar_match.group(1) if avatar_match else ""
    full_name = avatar_match.group(2) if avatar_match else short_name

    # Campos pontos (na ordem: pts, na_rodada, moscas, ares, jsa)
    pts_values = re.findall(r'class="pontos">\s*([^<]+?)\s*<', snippet_after)

    def safe_int(val):
        v = val.strip()
        return int(v) if v.lstrip("-").isdigit() else v

    points = safe_int(pts_values[0]) if len(pts_values) > 0 else 0
    na_rodada = safe_int(pts_values[1]) if len(pts_values) > 1 else 0
    moscas = safe_int(pts_values[2]) if len(pts_values) > 2 else 0
    ares = safe_int(pts_values[3]) if len(pts_values) > 3 else 0
    jsa = pts_values[4].strip() if len(pts_values) > 4 else ""

    # Percentual
    pct_match = re.search(r'position:absolute[^>]+>(\d+)%<', snippet_after)
    percent = int(pct_match.group(1)) if pct_match else None

    return {
        "position": position,
        "rank_delta": rank_delta,
        "rank_dir": rank_dir,
        "user_id": user_id,
        "name": short_name,
        "full_name": full_name,
        "points": points,
        "na_rodada": na_rodada,
        "moscas": moscas,
        "ares": ares,
        "jsa": jsa,
        "percent": percent,
        "avatar_url": avatar_url,
    }


def parse_classificacao(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for a in soup.find_all("a", onclick=re.compile(r"mostraApostas\(")):
        row = parse_row(html, a)
        if row:
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Avatares
# ---------------------------------------------------------------------------

def normalize_url(raw: str) -> str:
    """Converte path relativo em URL absoluta com encoding correto.

    Usa os safe chars do RFC 3986 para paths — inclui parênteses e outros
    sub-delimiters que o servidor pode rejeitar se codificados como %28%29.
    """
    from urllib.parse import quote
    # RFC 3986 pchar safe: unreserved + sub-delims + : @  (exceto espaço)
    RFC3986_PATH_SAFE = "/:@!$&'()*+,;=~.-_"
    path = BASE_URL + raw if raw.startswith("/") else raw
    # Só re-encoda a parte do path (antes do ?)
    if "?" in path:
        p, q = path.split("?", 1)
        return quote(p, safe=RFC3986_PATH_SAFE) + "?" + q
    return quote(path, safe=RFC3986_PATH_SAFE)


def download_avatars(session: requests.Session, rows: list[dict]):
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    for row in rows:
        raw_url = row["avatar_url"]
        if not raw_url or "padrao" in raw_url:
            row["avatar_path"] = ""
            continue

        url = normalize_url(raw_url)

        # Nome do arquivo: userId + extensão original
        ext = Path(url.split("?")[0]).suffix or ".png"
        filename = f"{row['user_id']}{ext}"
        dest = AVATARS_DIR / filename

        try:
            # Usa requests direto com cookies da sessão — evita Referer/Origin
            # que causam 403 em arquivos estáticos deste servidor
            r = requests.get(url, timeout=10, cookies=session.cookies,
                             headers={"User-Agent": session.headers["User-Agent"]})
            r.raise_for_status()
            dest.write_bytes(r.content)
            row["avatar_path"] = str(dest.relative_to(ROOT))
        except Exception as e:
            print(f"    Aviso: avatar de {row['name']} falhou ({e})")
            row["avatar_path"] = ""
        time.sleep(0.3)


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "date", "position", "rank_delta", "rank_dir",
    "user_id", "name", "full_name",
    "points", "na_rodada", "moscas", "ares", "jsa", "percent",
    "avatar_url", "avatar_path",
]


def save_snapshot(rows: list[dict], snap_date: date):
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOTS_DIR / f"{snap_date.isoformat()}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({"date": snap_date.isoformat(), **row})
    return path


def save_raw(html: str, snap_date: date):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{snap_date.isoformat()}.html"
    path.write_text(html, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Scraper WebBolão")
    parser.add_argument("--start", default=BOLAO_START.isoformat(),
                        help="Data inicial YYYY-MM-DD (padrão: 2026-06-11)")
    parser.add_argument("--end", default=date.today().isoformat(),
                        help="Data final YYYY-MM-DD (padrão: hoje)")
    parser.add_argument("--force", action="store_true",
                        help="Sobrescreve snapshots existentes")
    parser.add_argument("--no-avatars", action="store_true",
                        help="Pula download de avatares")
    return parser.parse_args()


def iter_dates(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def main():
    args = parse_args()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    today = date.today()

    config = dotenv_values(ROOT / ".env")
    email = config.get("login") or config.get("email", "")
    password = config.get("password", "")
    if not email or not password:
        print("ERRO: 'login' e 'password' precisam estar no .env")
        sys.exit(1)

    print("Autenticando...")
    session = create_session(email, password)

    dates = list(iter_dates(start, end))
    print(f"Coletando {len(dates)} dias ({start} → {end})\n")

    for snap_date in dates:
        csv_path = SNAPSHOTS_DIR / f"{snap_date.isoformat()}.csv"
        is_today = snap_date == today

        if csv_path.exists() and not is_today and not args.force:
            print(f"  {snap_date}  já existe, pulando")
            continue

        print(f"  {snap_date}  buscando...", end=" ", flush=True)
        try:
            html = fetch_classificacao(session, snap_date)
            rows = parse_classificacao(html)

            if not rows:
                print("sem dados (sem jogos nesta data?)")
                continue

            save_raw(html, snap_date)

            if not args.no_avatars:
                download_avatars(session, rows)

            path = save_snapshot(rows, snap_date)
            print(f"{len(rows)} participantes → {path.name}")

            # Pausa respeitosa entre requisições
            if snap_date != dates[-1]:
                time.sleep(1.0)

        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário")
            break
        except Exception as e:
            print(f"ERRO: {e}")
            continue

    print("\nConcluído.")


if __name__ == "__main__":
    main()
