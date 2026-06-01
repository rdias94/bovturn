#!/usr/bin/env python3
"""
Replica a planilha V15 BZBM (ou export do Google Sheets) em CSV locais.

Uso:
  # Do arquivo .xlsm/.xlsx local (padrão: Downloads)
  python scripts/sincronizar_planilha.py

  # De um caminho específico
  python scripts/sincronizar_planilha.py --origem ~/Downloads/planilha.xlsx

  # De URL pública do Google Sheets (aba com link "qualquer pessoa com o link")
  python scripts/sincronizar_planilha.py --google-sheet-id ID --gid 2424350

Saída: data/planilha_v15_bzbm/*.csv + manifest.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "planilha_v15_bzbm"
DEFAULT_XLSM = Path.home() / "Downloads" / (
    "V15 BZBM 220-390 Orçamento Controle Operação VPagro.xlsm"
)
GOOGLE_SHEET_ID = "1xq62c9QZLgIsV_StMh3yHo3C8P2Tq33M5fQJVLvy-co"


def safe_name(name: str) -> str:
    s = re.sub(r"[^\w\s\-]", "", name, flags=re.UNICODE)
    s = re.sub(r"\s+", "_", s.strip())
    return s[:80] or "aba"


def export_workbook(origem: Path, out_dir: Path, fonte: str, extra: dict | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    xl = pd.ExcelFile(origem, engine="openpyxl")
    manifest: dict = {
        "fonte": fonte,
        "arquivo_origem": str(origem),
        "google_sheet_id": GOOGLE_SHEET_ID,
        "exportado_em": datetime.now(timezone.utc).isoformat(),
        "abas": [],
        **(extra or {}),
    }
    for sheet in xl.sheet_names:
        df = pd.read_excel(origem, sheet_name=sheet, engine="openpyxl", header=None)
        fname = f"{safe_name(sheet)}.csv"
        df.to_csv(out_dir / fname, index=False, header=False, encoding="utf-8")
        manifest["abas"].append(
            {
                "nome": sheet,
                "arquivo_csv": fname,
                "linhas": int(df.shape[0]),
                "colunas": int(df.shape[1]),
            }
        )
        print(f"  {sheet} -> {fname} ({df.shape[0]}x{df.shape[1]})")
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def fetch_google_gid(sheet_id: str, gid: str, out_dir: Path) -> None:
    url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/"
        f"gviz/tq?tqx=out:csv&gid={gid}"
    )
    r = httpx.get(url, follow_redirects=True, timeout=60)
    if "accounts.google.com" in str(r.url) or r.text.strip().startswith("<!DOCTYPE"):
        raise SystemExit(
            "Planilha privada: compartilhe como 'Qualquer pessoa com o link' (leitor) "
            "ou exporte File → Download → .xlsx e use --origem."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"google_gid_{gid}.csv"
    path.write_bytes(r.content)
    manifest = {
        "fonte": "google_sheets_gid",
        "google_sheet_id": sheet_id,
        "google_sheet_gid": gid,
        "exportado_em": datetime.now(timezone.utc).isoformat(),
        "abas": [{"nome": f"gid_{gid}", "arquivo_csv": path.name}],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Baixado: {path} ({len(r.content)} bytes)")


def main() -> None:
    p = argparse.ArgumentParser(description="Replica planilha BovTurn em CSV local")
    p.add_argument("--origem", type=Path, help="Arquivo .xlsm/.xlsx local")
    p.add_argument("--saida", type=Path, default=OUT_DIR)
    p.add_argument("--google-sheet-id", default=GOOGLE_SHEET_ID)
    p.add_argument("--gid", help="Baixar só uma aba pública do Google (gid da URL)")
    args = p.parse_args()

    if args.gid:
        fetch_google_gid(args.google_sheet_id, args.gid, args.saida)
        return

    origem = args.origem or DEFAULT_XLSM
    if not origem.exists():
        print(f"Arquivo não encontrado: {origem}", file=sys.stderr)
        print("Exporte a planilha do Google (Download → .xlsx) ou informe --origem.", file=sys.stderr)
        sys.exit(1)

    print(f"Exportando {origem} -> {args.saida}")
    m = export_workbook(origem, args.saida, "arquivo_local")
    print(f"Concluído: {len(m['abas'])} abas.")


if __name__ == "__main__":
    main()
