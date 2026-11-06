#!/usr/bin/env python3
"""Descoberta progressiva: índice compacto -> shortlist -> ficha completa.

Os resumos são derivados do catálogo em tempo de execução; não existe um segundo
catálogo a sincronizar. Nenhuma ferramenta externa é executada ou instalada.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from library import load_resources, load_collections, load_environments, collection_index, normalize
from search import expand_query, score, env_status

# Exceções semânticas explícitas para confusões observadas em testes.
# Os casos de uso e resumos continuam a vir do catálogo, sem cópias.
AVOID_WHEN = {
    "lightning-css": "Precisas de linting, regras de qualidade ou consistência de CSS, não de minificação.",
    "stylelint": "Queres apenas minificar CSS ou otimizar o tamanho final do bundle.",
    "sharp": "Basta exportar manualmente poucas imagens e não precisas de um pipeline.",
    "zotero": "Procuras fontes tipográficas, formatos de fonte ou carregamento de webfonts.",
    "skill-frontend-design": "Pretendes preservar a identidade visual existente sem redesenhar a interface.",
    "oil-ui": "Pretendes apenas corrigir acessibilidade ou consistência sem nova direção visual.",
    "query-monitor": "O projeto não utiliza WordPress.",
}

# O contexto muda a ordem, não altera a existência de recursos no catálogo.
INTENTS = {
    "lint": ("stylelint",),
    "linting": ("stylelint",),
    "linter": ("stylelint",),
    "minification": ("lightning-css",),
    "minificacao": ("lightning-css",),
    "minificar": ("lightning-css",),
    "regression": ("playwright",),
    "regressao": ("playwright",),
    "tipografia": ("stylelint",),
    "typography": ("stylelint",),
}


def card(rec: dict) -> dict:
    """Ficha compacta, com referência inequívoca ao registo integral."""
    return {
        "id": rec["id"], "name": rec["name"], "type": rec["type"],
        "summary": rec["summary"], "capabilities": rec.get("tags", [])[:6],
        "use_when": rec.get("use_cases", [])[:2],
        "avoid_when": AVOID_WHEN.get(rec["id"]),
        "verification": rec["verification"]["status"],
        "detail_command": f"python scripts/discover.py --show {rec['id']}",
    }


def compact_index(resources: list[dict]) -> list[dict]:
    return [card(r) for r in sorted(resources, key=lambda r: r["id"])]


def rank(query: str, resources: list[dict], collections: list[dict],
         limit: int = 8, technology: str | None = None) -> list[dict]:
    groups = expand_query(query)
    idx = collection_index(collections)
    words = set(normalize(query).replace("-", " ").split())
    selected = []
    for rec in resources:
        if rec["verification"]["status"] == "deprecated":
            continue
        raw, reasons = score(rec, groups, idx)
        bonus = 0.0
        for word in words:
            if rec["id"] in INTENTS.get(word, ()):
                bonus += 12.0
        # Penalizar resultados incompatíveis, sem excluir recursos que possam ser úteis.
        if technology and rec["id"] == "query-monitor" and technology.lower() != "wordpress":
            bonus -= 30.0
        if raw <= 0 and bonus <= 0:
            continue
        selected.append((raw + bonus, rec, reasons))
    selected.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [{**card(rec), "score": round(points, 2), "coverage": why.get("_coverage", 0)}
            for points, rec, why in selected[:limit]]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Índice compacto e descoberta progressiva da biblioteca.")
    p.add_argument("query", nargs="*", help="Pesquisa por capacidades, não pelo nome do projeto.")
    p.add_argument("--index", action="store_true", help="Índice de todos os recursos, sem fichas completas.")
    p.add_argument("--show", metavar="ID", help="Ficha integral do recurso selecionado.")
    p.add_argument("--technology", help="Contexto tecnológico opcional, ex.: nextjs ou wordpress.")
    p.add_argument("--limit", type=int, default=8)
    a = p.parse_args(argv)
    if a.limit < 1:
        p.error("--limit deve ser positivo")
    resources = load_resources()
    if a.show:
        rec = next((r for r in resources if r["id"] == a.show), None)
        if not rec:
            print(json.dumps({"error": "unknown_resource", "id": a.show}), file=sys.stderr)
            return 1
        print(json.dumps({k: v for k, v in rec.items() if not k.startswith("_")},
                         ensure_ascii=False, indent=2))
        return 0
    if a.index:
        payload = {"total": len(resources), "results": compact_index(resources)}
    elif a.query:
        query = " ".join(a.query)
        payload = {"query": query, "results": rank(query, resources, load_collections(),
                                                   a.limit, a.technology),
                   "note": "Pré-seleção, não autorização nem recomendação final."}
    else:
        p.print_help()
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
