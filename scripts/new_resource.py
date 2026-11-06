#!/usr/bin/env python3
"""Cria o esqueleto de um novo recurso com estado 'unverified', verificando duplicados.

Por omissão só imprime o JSON. Com --write, acrescenta-o ao ficheiro do tipo
(ordenado por id). Depois: preencher campos, verificar fontes e correr validate.py.

Exemplo:
  python scripts/new_resource.py --type mcp-server --id linear-mcp --name "Linear MCP" \\
      --url https://linear.app/docs/mcp --summary "Servidor MCP oficial do Linear." --write
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys

from library import CATALOG, load_registry, load_resources, normalize


def main(argv=None) -> int:
    reg = load_registry()
    p = argparse.ArgumentParser()
    p.add_argument("--type", required=True, choices=sorted(reg["types"]))
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--url", required=True, help="URL oficial")
    p.add_argument("--github")
    p.add_argument("--summary", default="Descrição curta por preencher (10-200 caracteres).")
    p.add_argument("--internal", action="store_true", help="Projeto próprio (origin=internal)")
    p.add_argument("--write", action="store_true")
    a = p.parse_args(argv)

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", a.id):
        print("ERRO: id deve ser kebab-case (a-z, 0-9, hífenes).", file=sys.stderr)
        return 1
    existing = load_resources(reg)
    ids = {r["id"] for r in existing}
    if a.id in ids:
        print(f"ERRO: id '{a.id}' já existe. Atualize o registo existente em vez de criar outro.", file=sys.stderr)
        return 1
    url_key = a.url.rstrip("/").lower()
    for r in existing:
        if (r["urls"].get("official") or "").rstrip("/").lower() == url_key:
            print(f"ERRO: URL oficial já usado por '{r['id']}'.", file=sys.stderr)
            return 1
    names = {normalize(r["name"]): r["id"] for r in existing}
    close = difflib.get_close_matches(normalize(a.name), list(names), n=3, cutoff=0.8)
    if close:
        print("AVISO: nomes semelhantes já catalogados: " + ", ".join(f"{names[c]} ({c})" for c in close), file=sys.stderr)

    rec = {
        "id": a.id, "name": a.name, "type": a.type, "origin": "internal" if a.internal else "external",
        "summary": a.summary, "description": a.summary,
        "urls": {"official": a.url, "docs": None, "github": a.github, "package": None},
        "categories": [], "tags": ["internal"] if a.internal else [], "features": [], "use_cases": [],
        "technologies": [], "platforms": [], "requirements": [], "dependencies": [], "related": [],
        "install": None, "configuration": None,
        "license": {"spdx": None, "name": None, "url": None},
        "pricing": {"model": "unknown", "notes": None},
        "maintenance": {"status": "unknown", "last_activity": None, "checked_on": None},
        "verification": {"status": "unverified", "verified_on": None, "method": None, "sources": [],
                         "confirmed_fields": [], "unconfirmed_fields": ["*"]},
        "risk": {"level": "unknown", "executes_code": False, "requires_credentials": False, "data_access": None, "notes": None},
        "limitations": [], "notes": None, "doc": None,
    }
    if not a.write:
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        print("\n(Não escrito. Use --write para acrescentar ao catálogo.)", file=sys.stderr)
        return 0
    path = CATALOG / reg["types"][a.type]["file"]
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    data.append(rec)
    data.sort(key=lambda r: r["id"])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Acrescentado a {path.relative_to(CATALOG.parent)}. Preencha categories (obrigatório para validar), "
          f"verifique as fontes e corra: python scripts/validate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
