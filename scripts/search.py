#!/usr/bin/env python3
"""Pesquisa local no catálogo da AI Resource Library.

Pesquisa determinística por correspondência textual ponderada sobre metadados
(nome, tags, categorias, tecnologias, plataformas, casos de uso, descrição),
com sinónimos PT→EN simples. NÃO interpreta linguagem natural: perguntas
complexas devem ser decompostas pelo agente em palavras-chave e filtros.

Exemplos:
  python scripts/search.py "landing page wordpress"
  python scripts/search.py "design system figma" --collection ui-ux-design
  python scripts/search.py github automation --type mcp-server
  python scripts/search.py --show github-mcp-server
  python scripts/search.py --collection web-development
  python scripts/search.py --list-collections
  python scripts/search.py --stats
  python scripts/search.py "acessibilidade" --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from library import (VERIFICATION_ORDER, collection_index, load_collections, load_environments,
                     load_registry, load_resources, normalize)

STOPWORDS = set("""
a o as os um uma uns umas de do da dos das em no na nos nas para por com sem que qual quais
e ou ao aos se me te meu minha meus minhas tenho tens tem temos posso pode podem ser sao estao
como onde quando mais melhor melhores recursos recurso ferramenta ferramentas disponiveis disponivel
utilizar usar usado utilizado criar desenvolver fazer trabalhar ajudar podem pode adequado adequados
the of to in on for with and or an is are be can which what best tools tool resources resource use using
create build help my i we available
""".split())

# Sinónimos simples PT → termos usados nos metadados (em inglês). Expandir conforme necessário.
SYNONYMS = {
    "acessibilidade": ["accessibility", "a11y", "wcag"], "acessivel": ["accessibility", "a11y"],
    "testar": ["testing", "test"], "teste": ["testing", "test"], "testes": ["testing", "test"],
    "automatizar": ["automation"], "automacao": ["automation"], "automacoes": ["automation"],
    "servidor": ["server", "mcp"], "servidores": ["server", "mcp"],
    "componente": ["components"], "componentes": ["components"],
    "reutilizavel": ["reusable", "reusable-components"], "reutilizaveis": ["reusable", "reusable-components"],
    "documentar": ["documentation"], "documentacao": ["documentation", "docs"],
    "pesquisa": ["research"], "investigacao": ["research", "ux-research"],
    "desenvolvimento": ["development"], "tarefas": ["tasks", "automation"],
    "pagina": ["page"], "responsiva": ["responsive"], "responsivo": ["responsive"],
    "animacao": ["animation"], "animacoes": ["animation"],
    "desempenho": ["performance"], "implementacao": ["deployment"], "publicar": ["deployment", "hosting"],
    "deploy": ["deploy", "deployment"], "pages": ["github-pages", "pages"],
    "alojamento": ["hosting"], "fontes": ["sources", "references"], "referencias": ["references"],
    "sintese": ["synthesis"], "conhecimento": ["knowledge-management"],
    "prototipagem": ["prototyping"], "prototipo": ["prototyping"], "usabilidade": ["usability", "ux-research"],
    "tokens": ["design-tokens", "tokens"], "design-system": ["design-system", "design-systems"],
    "agentes": ["ai-agents", "agents"], "agente": ["ai-agents", "agents"], "ia": ["ai-agents"], "ai": ["ai-agents"],
    "repositorio": ["repository"], "repositorios": ["repository"],
    "mcp": ["mcp", "mcp-server"], "plugin": ["plugin"], "plugins": ["plugin"], "skill": ["skill"], "skills": ["skill"],
    "landing": ["landing-page", "landing"], "responsive": ["responsive"],
}

# Pesos por campo
WEIGHTS = {"id": 6, "name": 6, "tags": 4, "categories": 3, "technologies": 3, "platforms": 2.5,
           "type": 3, "summary": 2, "use_cases": 2, "features": 1.5, "description": 1}


def tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9.+#-]+", normalize(text)) if t]


def expand_query(query: str) -> list[list[str]]:
    """Cada termo da pergunta vira um grupo de alternativas (termo + sinónimos)."""
    norm = normalize(query)
    # junta expressões compostas conhecidas
    for phrase, joined in (("design system", "design-system"), ("landing page", "landing"),
                           ("design tokens", "tokens"), ("model context protocol", "mcp")):
        norm = norm.replace(phrase, joined)
    groups = []
    for tok in tokenize(norm):
        tok = tok.strip(".-")
        if not tok or tok in STOPWORDS or len(tok) < 2:
            continue
        alts = [tok] + [x for x in SYNONYMS.get(tok, []) if x != tok]
        if tok.endswith("s") and not tok.endswith("ss") and len(tok) > 4:
            alts.append(tok[:-1])
        groups.append(alts)
    return groups


def field_text(rec: dict, field: str) -> str:
    v = rec.get(field)
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(map(str, v))
    return str(v)


def match_term(term: str, tokens: set[str], text: str) -> bool:
    if term in tokens:
        return True
    if "-" in term and term in text:
        return True
    # prefixo para termos longos (ex.: "access" ~ "accessibility")
    if len(term) >= 5:
        return any(t.startswith(term) for t in tokens)
    return False


def score(rec: dict, groups: list[list[str]], coll_idx: dict) -> tuple[float, dict]:
    reasons: dict[str, set[str]] = {}
    total = 0.0
    matched_groups = 0
    fields = dict(WEIGHTS)
    texts = {f: normalize(field_text(rec, f)) for f in fields}
    texts["collections"] = " ".join(c for c, _ in coll_idx.get(rec["id"], []))
    fields["collections"] = 1
    toks = {f: set(tokenize(t)) | set(tokenize(t.replace("-", " "))) for f, t in texts.items()}
    for alts in groups:
        group_hit = False
        for f, w in fields.items():
            if any(match_term(a, toks[f], texts[f]) for a in alts):
                total += w
                reasons.setdefault(f, set()).add(alts[0])
                group_hit = True
        if group_hit:
            matched_groups += 1
    if not groups:
        return 0.0, {}
    coverage = matched_groups / len(groups)
    total *= (0.4 + 0.6 * coverage)
    status = rec["verification"]["status"]
    if status == "deprecated":
        total *= 0.2
    elif status == "unverified":
        total *= 0.85
    return round(total, 2), {k: sorted(v) for k, v in reasons.items()} | {"_coverage": round(coverage, 2)}


def env_status(envs: list[dict], rid: str) -> list[dict]:
    out = []
    for e in envs:
        for entry in e["entries"]:
            if entry["resource_id"] == rid:
                out.append({"environment": e["id"], "observed_on": e["observed_on"], "installed": entry["installed"],
                            "available_for_execution": entry["available_for_execution"],
                            "authorization": entry["authorization"]["level"]})
    return out


def summarize(rec: dict, reasons: dict, coll_idx: dict, envs: list[dict], s: float | None = None) -> dict:
    return {
        "id": rec["id"], "name": rec["name"], "type": rec["type"], "origin": rec["origin"],
        "score": s, "summary": rec["summary"], "categories": rec["categories"],
        "relevance": {k: v for k, v in reasons.items() if not k.startswith("_")},
        "coverage": reasons.get("_coverage"),
        "platforms": rec.get("platforms", []), "technologies": rec.get("technologies", []),
        "verification": rec["verification"]["status"], "verified_on": rec["verification"].get("verified_on"),
        "maintenance": rec["maintenance"]["status"],
        "license": rec["license"].get("spdx") or rec["license"].get("name"), "pricing": rec["pricing"]["model"],
        "risk": rec["risk"]["level"], "executes_code": rec["risk"]["executes_code"],
        "requires_credentials": rec["risk"]["requires_credentials"],
        "limitations": rec.get("limitations", []),
        "docs": rec["urls"].get("docs") or rec["urls"].get("official") or rec["urls"].get("github"),
        "collections": [{"id": c, "role": r} for c, r in coll_idx.get(rec["id"], [])],
        "environment_status": env_status(envs, rec["id"]),
        "catalog_status": "catalogued-only: presença no catálogo NÃO implica instalado, disponível nem autorizado",
    }


def print_result(i: int, r: dict) -> None:
    flag = " ⚠ DEPRECATED" if r["verification"] == "deprecated" else ""
    internal = " [interno]" if r["origin"] == "internal" else ""
    print(f"{i}. {r['name']}  ({r['type']} · id: {r['id']}){internal}{flag}")
    print(f"   {r['summary']}")
    if r["relevance"]:
        why = "; ".join(f"{k}: {', '.join(v)}" for k, v in r["relevance"].items())
        print(f"   Relevância: {why}  (cobertura {int((r['coverage'] or 0) * 100)}%)")
    print(f"   Categorias: {', '.join(r['categories'])}")
    if r["platforms"]:
        print(f"   Compatibilidade: {', '.join(r['platforms'])}")
    print(f"   Verificação: {r['verification']} ({r['verified_on'] or 'sem data'}) · manutenção: {r['maintenance']}"
          f" · licença: {r['license'] or 'desconhecida'} · preço: {r['pricing']}")
    print(f"   Risco: {r['risk']} (executa código: {'sim' if r['executes_code'] else 'não'}; "
          f"credenciais: {'sim' if r['requires_credentials'] else 'não'})")
    for lim in r["limitations"][:2]:
        print(f"   Limitação: {lim}")
    if r["collections"]:
        print("   Coleções: " + ", ".join(f"{c['id']} ({c['role']})" for c in r["collections"]))
    for e in r["environment_status"]:
        print(f"   Ambiente {e['environment']} (observado {e['observed_on']}): instalado={e['installed']}, "
              f"executável={e['available_for_execution']}, autorização={e['authorization']}")
    if r["docs"]:
        print(f"   Docs: {r['docs']}")
    print()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Pesquisa no catálogo da AI Resource Library.")
    p.add_argument("query", nargs="*", help="Palavras-chave (PT ou EN).")
    p.add_argument("--type", help="Filtrar por tipo (tool, plugin, mcp-server, ...).")
    p.add_argument("--category", help="Filtrar por categoria.")
    p.add_argument("--tag", help="Filtrar por tag.")
    p.add_argument("--platform", help="Filtrar por plataforma compatível (ex.: claude, figma, wordpress).")
    p.add_argument("--collection", help="Restringir a uma coleção (sem query: lista a coleção).")
    p.add_argument("--origin", choices=["external", "internal"])
    p.add_argument("--min-verification", choices=["unverified", "partially_verified", "verified"])
    p.add_argument("--include-deprecated", action="store_true", help="Mostrar recursos deprecated (ocultos por omissão).")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--min-coverage", type=float, default=0.5,
                   help="Fração mínima de termos da pergunta que um resultado tem de cobrir (0-1). Omissão: 0.5.")
    p.add_argument("--json", action="store_true", help="Saída JSON estruturada.")
    p.add_argument("--show", metavar="ID", help="Mostrar o registo completo de um recurso.")
    p.add_argument("--list-collections", action="store_true")
    p.add_argument("--stats", action="store_true")
    a = p.parse_args(argv)

    registry = load_registry()
    resources = load_resources(registry)
    collections = load_collections()
    envs = load_environments()
    coll_idx = collection_index(collections)
    by_id = {r["id"]: r for r in resources}

    if a.stats:
        from collections import Counter
        st = {"total": len(resources), "by_type": dict(Counter(r["type"] for r in resources)),
              "by_verification": dict(Counter(r["verification"]["status"] for r in resources)),
              "by_origin": dict(Counter(r["origin"] for r in resources)),
              "collections": {c["id"]: len(c["resources"]) for c in collections}}
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return 0

    if a.list_collections:
        for c in collections:
            print(f"{c['id']}: {c['name']} — {len(c['resources'])} recursos (atualizada {c['updated_on']})")
            print(f"   {c['description']}")
        return 0

    if a.show:
        rec = by_id.get(a.show)
        if not rec:
            print(f"Recurso '{a.show}' não encontrado.", file=sys.stderr)
            return 1
        full = {k: v for k, v in rec.items() if not k.startswith("_")}
        full["_collections"] = [{"id": c, "role": r} for c, r in coll_idx.get(rec["id"], [])]
        full["_environment_status"] = env_status(envs, rec["id"])
        full["_file"] = rec["_file"]
        print(json.dumps(full, ensure_ascii=False, indent=2))
        return 0

    pool = resources
    coll = None
    if a.collection:
        coll = next((c for c in collections if c["id"] == a.collection), None)
        if not coll:
            print(f"Coleção '{a.collection}' não encontrada.", file=sys.stderr)
            return 1
        ids = {ref["id"] for ref in coll["resources"]}
        pool = [r for r in pool if r["id"] in ids]
    if a.type:
        pool = [r for r in pool if r["type"] == a.type]
    if a.category:
        pool = [r for r in pool if a.category in r["categories"]]
    if a.tag:
        pool = [r for r in pool if a.tag in r["tags"]]
    if a.platform:
        pool = [r for r in pool if a.platform in r.get("platforms", [])]
    if a.origin:
        pool = [r for r in pool if r["origin"] == a.origin]
    if a.min_verification:
        lvl = VERIFICATION_ORDER[a.min_verification]
        pool = [r for r in pool if VERIFICATION_ORDER[r["verification"]["status"]] >= lvl]
    query = " ".join(a.query)
    groups = expand_query(query)

    if coll and not groups:
        # listar a coleção por papel
        role_order = ["core", "recommended", "optional", "alternative", "reference", "avoid"]
        refs = sorted(coll["resources"], key=lambda x: role_order.index(x["role"]))
        results = []
        for ref in refs:
            rec = by_id[ref["id"]]
            if rec not in pool:
                continue
            item = summarize(rec, {}, coll_idx, envs)
            item["role"], item["rationale"] = ref["role"], ref["rationale"]
            results.append(item)
        if a.json:
            print(json.dumps({"collection": coll["id"], "results": results,
                              "recommendations": coll.get("recommendations", [])}, ensure_ascii=False, indent=2))
            return 0
        print(f"Coleção: {coll['name']} — {coll['description']}\n")
        for r in results:
            print(f"[{r['role']}] {r['name']} ({r['id']}) · {r['verification']}: {r['rationale']}")
        if coll.get("recommendations"):
            print("\nRecomendações:")
            for rec in coll["recommendations"]:
                print(f"- {rec['scenario']}: preferir {', '.join(rec['prefer'])}"
                      + (f"; considerar {', '.join(rec.get('consider', []))}" if rec.get("consider") else ""))
                print(f"  Porquê: {rec['why']}")
        return 0

    if not groups and not any([a.type, a.category, a.tag, a.platform, a.origin]):
        p.print_help()
        return 2

    scored = []
    for rec in pool:
        if groups:
            s, reasons = score(rec, groups, coll_idx)
            if s <= 0 or reasons.get("_coverage", 0) < a.min_coverage:
                continue
        else:
            s, reasons = 1.0, {}
        scored.append((s, rec, reasons))
    hidden_deprecated = []
    if not a.include_deprecated:
        hidden_deprecated = [rec["id"] for _, rec, _ in scored if rec["verification"]["status"] == "deprecated"]
        scored = [x for x in scored if x[1]["verification"]["status"] != "deprecated"]
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    results = [summarize(rec, reasons, coll_idx, envs, s) for s, rec, reasons in scored[: a.limit]]

    payload = {"query": query, "terms": groups, "filters": {k: v for k, v in vars(a).items()
               if k in ("type", "category", "tag", "platform", "collection", "origin", "min_verification") and v},
               "total_matches": len(scored), "results": results, "hidden_deprecated": hidden_deprecated,
               "note": "Pesquisa textual determinística. Catalogado ≠ instalado ≠ autorizado."}
    if a.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not results:
        print("Sem resultados. Experimente termos mais gerais, outra língua (PT/EN) ou remover filtros.")
    else:
        print(f"{len(scored)} resultado(s) para «{query or '(filtros)'}» — a mostrar {len(results)}.\n")
        for i, r in enumerate(results, 1):
            print_result(i, r)
    if hidden_deprecated:
        print(f"Ocultos por estarem deprecated: {', '.join(hidden_deprecated)} (use --include-deprecated).")
    print("Nota: presença no catálogo não significa que o recurso esteja instalado, disponível ou autorizado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
