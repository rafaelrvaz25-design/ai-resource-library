#!/usr/bin/env python3
"""Validação da AI Resource Library.

Verifica: JSON válido, JSON Schema, tipos vs registo, IDs únicos, duplicados,
referências entre coleções/catálogo/ambientes, relações, coerência de estados,
recursos possivelmente descontinuados, verificações antigas e ausência de segredos.

Uso:
  python scripts/validate.py            # erros => exit 1
  python scripts/validate.py --strict   # avisos também falham
  python scripts/validate.py --json     # relatório estruturado
  python scripts/validate.py --stale-days 180 --inactive-days 365
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

# O modo isolado (-I) omite a pasta do script no sys.path.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from library import CATALOG, COLLECTIONS, ENVIRONMENTS, ROOT, SCHEMAS, load_json, normalize

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:  # pragma: no cover
    print("ERRO: falta o pacote 'jsonschema'. Instalar com: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)

SECRET_PATTERNS = [
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), "token GitHub"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{40,}"), "token GitHub fine-grained"),
    (re.compile(r"sk-(ant-)?[A-Za-z0-9_-]{30,}"), "chave API (sk-)"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "chave AWS"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "token Slack"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "chave privada"),
    (re.compile(r"eyJhbGciOi[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"), "JWT"),
]
CORE_ROLES = {"core", "recommended"}


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: dict = {}

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def schema_errors(validator, obj, where):
    for e in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
        path = "/".join(map(str, e.path)) or "(raiz)"
        yield f"{where}: {path}: {e.message}"


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--strict", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--stale-days", type=int, default=180, help="Avisar verificações mais antigas do que N dias.")
    p.add_argument("--inactive-days", type=int, default=365, help="Avisar recursos sem atividade há mais de N dias.")
    p.add_argument("--today", help="Data de referência (AAAA-MM-DD), para testes.")
    a = p.parse_args(argv)
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    rep = Report()

    # 1. JSON válido em todo o repositório
    parsed = {}
    for path in sorted(ROOT.rglob("*.json")):
        if any(part in (".git", "node_modules") for part in path.parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        try:
            parsed[rel] = load_json(path)
        except json.JSONDecodeError as e:
            rep.err(f"{rel}: JSON inválido ({e})")
    if rep.errors:
        return finish(rep, a)

    res_v = Draft202012Validator(load_json(SCHEMAS / "resource.schema.json"), format_checker=FormatChecker())
    col_v = Draft202012Validator(load_json(SCHEMAS / "collection.schema.json"), format_checker=FormatChecker())
    env_v = Draft202012Validator(load_json(SCHEMAS / "environment.schema.json"), format_checker=FormatChecker())

    # 2. Registo
    registry = parsed["catalog/_registry.json"]
    allowed_categories = set(registry.get("categories", []))
    expected_files = {f"catalog/{m['file']}": t for t, m in registry["types"].items()}
    for rel in parsed:
        if rel.startswith("catalog/") and rel != "catalog/_registry.json" and rel not in expected_files:
            rep.err(f"{rel}: ficheiro de catálogo não registado em catalog/_registry.json")

    # 3. Recursos
    resources = {}
    names, officials = {}, {}
    for rel, type_id in expected_files.items():
        if rel not in parsed:
            rep.err(f"{rel}: ficheiro registado para o tipo '{type_id}' não existe")
            continue
        data = parsed[rel]
        if not isinstance(data, list):
            rep.err(f"{rel}: deve conter uma lista de recursos")
            continue
        for i, rec in enumerate(data):
            where = f"{rel}[{i}]({rec.get('id', '?') if isinstance(rec, dict) else '?'})"
            errs = list(schema_errors(res_v, rec, where))
            for e in errs:
                rep.err(e)
            if errs or not isinstance(rec, dict):
                continue
            rid = rec["id"]
            if rec["type"] != type_id:
                rep.err(f"{where}: type '{rec['type']}' não corresponde ao ficheiro (esperado '{type_id}')")
            if rid in resources:
                rep.err(f"{where}: ID duplicado (também em {resources[rid]['_file']})")
            rec["_file"] = rel
            resources[rid] = rec
            for c in rec["categories"]:
                if c not in allowed_categories:
                    rep.err(f"{where}: categoria '{c}' não existe em _registry.json (adicionar lá primeiro)")
            n = re.sub(r"[^a-z0-9]", "", normalize(rec["name"]))
            if n in names:
                rep.err(f"{where}: possível duplicado — mesmo nome que '{names[n]}'")
            names[n] = rid
            off = rec["urls"].get("official")
            if off:
                key = off.rstrip("/").lower()
                if key in officials:
                    rep.err(f"{where}: possível duplicado — mesmo URL oficial que '{officials[key]}'")
                officials[key] = rid
            if rec.get("doc") and not (ROOT / rec["doc"]).exists():
                rep.err(f"{where}: doc '{rec['doc']}' não existe")
            # coerência de estados
            v, m = rec["verification"], rec["maintenance"]
            if m["status"] == "archived" and v["status"] != "deprecated":
                rep.warn(f"{where}: manutenção 'archived' mas verificação '{v['status']}' — considerar 'deprecated'")
            if v["status"] == "unverified" and v.get("confirmed_fields"):
                rep.warn(f"{where}: 'unverified' mas com confirmed_fields preenchido")
            if v.get("verified_on"):
                age = (today - dt.date.fromisoformat(v["verified_on"])).days
                if age > a.stale_days:
                    rep.warn(f"{where}: verificação com {age} dias — reverificar")
            if m.get("last_activity") and v["status"] != "deprecated":
                idle = (today - dt.date.fromisoformat(m["last_activity"])).days
                if idle > a.inactive_days:
                    rep.warn(f"{where}: sem atividade há {idle} dias — possivelmente descontinuado")
            if rec["origin"] == "internal" and "internal" not in rec["tags"]:
                rep.warn(f"{where}: recurso interno sem a tag 'internal'")

    # 4. Relações
    for rid, rec in resources.items():
        for rel_ in rec.get("related", []):
            if rel_["id"] == rid:
                rep.err(f"{rid}: relação consigo próprio")
            elif rel_["id"] not in resources:
                rep.err(f"{rid}: relação para ID inexistente '{rel_['id']}'")

    # 5. Coleções
    coll_ids = set()
    membership: dict[str, int] = {}
    for rel, c in parsed.items():
        if not rel.startswith("collections/"):
            continue
        errs = list(schema_errors(col_v, c, rel))
        for e in errs:
            rep.err(e)
        if errs:
            continue
        if c["id"] in coll_ids:
            rep.err(f"{rel}: ID de coleção duplicado '{c['id']}'")
        coll_ids.add(c["id"])
        if rel != f"collections/{c['id']}.json":
            rep.warn(f"{rel}: nome do ficheiro diferente do id '{c['id']}'")
        seen = set()
        for ref in c["resources"]:
            if ref["id"] in seen:
                rep.err(f"{rel}: recurso '{ref['id']}' repetido na coleção")
            seen.add(ref["id"])
            target = resources.get(ref["id"])
            if not target:
                rep.err(f"{rel}: referência inválida '{ref['id']}' (não existe no catálogo)")
                continue
            membership[ref["id"]] = membership.get(ref["id"], 0) + 1
            if target["verification"]["status"] == "deprecated" and ref["role"] != "avoid":
                rep.err(f"{rel}: '{ref['id']}' está deprecated mas tem papel '{ref['role']}' (usar 'avoid')")
            if target["verification"]["status"] == "unverified" and ref["role"] == "core":
                rep.warn(f"{rel}: '{ref['id']}' é unverified mas está como 'core'")
        for r in c.get("recommendations", []):
            for x in r["prefer"] + r.get("consider", []):
                if x not in resources:
                    rep.err(f"{rel}: recomendação '{r['scenario']}' refere ID inexistente '{x}'")
                elif resources[x]["verification"]["status"] == "deprecated":
                    rep.err(f"{rel}: recomendação '{r['scenario']}' sugere recurso deprecated '{x}'")
        bad_cats = set(c["categories"]) - allowed_categories
        if bad_cats:
            rep.err(f"{rel}: categorias desconhecidas {sorted(bad_cats)}")

    # 6. Ambientes
    for rel, e in parsed.items():
        if not rel.startswith("environments/"):
            continue
        for msg in schema_errors(env_v, e, rel):
            rep.err(msg)
        for entry in e.get("entries", []):
            if entry.get("resource_id") not in resources:
                rep.err(f"{rel}: resource_id inexistente '{entry.get('resource_id')}'")

    # 7. Segredos
    for path in ROOT.rglob("*"):
        if path.is_dir() or any(p in (".git", "node_modules", "__pycache__") for p in path.parts):
            continue
        if path.suffix.lower() not in {".json", ".md", ".py", ".yml", ".yaml", ".txt", ".toml", ""}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pat, label in SECRET_PATTERNS:
            if pat.search(text) and path.name != "validate.py":
                rep.err(f"{path.relative_to(ROOT)}: possível segredo ({label}) — remover e revogar")

    rep.info = {
        "resources": len(resources), "collections": len(coll_ids),
        "resources_in_multiple_collections": sorted(k for k, v in membership.items() if v > 1),
        "resources_without_collection": sorted(set(resources) - set(membership)),
    }
    return finish(rep, a)


def finish(rep: Report, a) -> int:
    failed = bool(rep.errors) or (a.strict and bool(rep.warnings))
    if a.json:
        print(json.dumps({"ok": not failed, "errors": rep.errors, "warnings": rep.warnings, "info": rep.info},
                         ensure_ascii=False, indent=2))
    else:
        for e in rep.errors:
            print(f"ERRO   {e}")
        for w in rep.warnings:
            print(f"AVISO  {w}")
        if rep.info:
            print(f"\nRecursos: {rep.info['resources']} · Coleções: {rep.info['collections']} · "
                  f"Em várias coleções: {len(rep.info['resources_in_multiple_collections'])} · "
                  f"Sem coleção: {len(rep.info['resources_without_collection'])}")
        print(f"\n{'FALHOU' if failed else 'OK'}: {len(rep.errors)} erro(s), {len(rep.warnings)} aviso(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
