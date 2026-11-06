"""Funções partilhadas para ler a biblioteca. Só usa a biblioteca padrão do Python (3.9+)."""
from __future__ import annotations

import json
import os
import unicodedata
from pathlib import Path

ROOT = Path(os.environ.get("AI_RESOURCE_LIBRARY_ROOT", Path(__file__).resolve().parent.parent))
CATALOG = ROOT / "catalog"
COLLECTIONS = ROOT / "collections"
ENVIRONMENTS = ROOT / "environments"
SCHEMAS = ROOT / "schemas"

VERIFICATION_ORDER = {"verified": 3, "partially_verified": 2, "unverified": 1, "deprecated": 0}


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_registry() -> dict:
    return load_json(CATALOG / "_registry.json")


def load_resources(registry: dict | None = None) -> list[dict]:
    """Devolve todos os recursos de todos os ficheiros registados, com '_file' anotado."""
    registry = registry or load_registry()
    items = []
    for type_id, meta in registry["types"].items():
        path = CATALOG / meta["file"]
        if not path.exists():
            continue
        for rec in load_json(path):
            rec = dict(rec)
            rec["_file"] = f"catalog/{meta['file']}"
            rec["_registry_type"] = type_id
            items.append(rec)
    return items


def load_collections() -> list[dict]:
    out = []
    for path in sorted(COLLECTIONS.glob("*.json")):
        c = load_json(path)
        c["_file"] = f"collections/{path.name}"
        out.append(c)
    return out


def load_environments() -> list[dict]:
    if not ENVIRONMENTS.exists():
        return []
    out = []
    for path in sorted(ENVIRONMENTS.glob("*.json")):
        e = load_json(path)
        e["_file"] = f"environments/{path.name}"
        out.append(e)
    return out


def normalize(text: str) -> str:
    """minúsculas e sem acentos."""
    text = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def collection_index(collections: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """resource_id -> [(collection_id, role), ...]"""
    idx: dict[str, list[tuple[str, str]]] = {}
    for c in collections:
        for ref in c.get("resources", []):
            idx.setdefault(ref["id"], []).append((c["id"], ref["role"]))
    return idx
