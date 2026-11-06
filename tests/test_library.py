"""Testes obrigatórios da AI Resource Library (secção 18 da especificação).

Executar:  python -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import search  # noqa: E402
import validate  # noqa: E402
from library import load_collections, load_environments, load_registry, load_resources  # noqa: E402


def run_search(*args) -> dict:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = search.main([*args, "--json"])
    assert code == 0, f"search falhou: {args}"
    return json.loads(buf.getvalue())


def ids(payload, n=None):
    res = payload["results"][:n] if n else payload["results"]
    return [r["id"] for r in res]


class T1WebDevelopment(unittest.TestCase):
    """Teste 1: landing page responsiva em WordPress."""

    def test_wordpress_landing_page(self):
        top = ids(run_search("landing page responsiva wordpress", "--limit", "5"))
        for expected in ("wordpress", "create-block-theme", "wordpress-playground"):
            self.assertIn(expected, top)

    def test_collection_recommendation_exists(self):
        coll = next(c for c in load_collections() if c["id"] == "web-development")
        rec = next(r for r in coll["recommendations"] if "WordPress" in r["scenario"])
        self.assertIn("wordpress", rec["prefer"])


class T2UiUxDesign(unittest.TestCase):
    """Teste 2: criar e documentar um design system em Figma."""

    def test_figma_design_system(self):
        top = ids(run_search("design system figma documentar", "--limit", "6"))
        self.assertIn("figma", top)
        self.assertIn("figma-mcp-server", top)
        self.assertTrue({"tokens-studio", "storybook"} & set(top))

    def test_figma_plugins_for_design_systems(self):
        top = ids(run_search("plugins figma design systems", "--type", "plugin"))
        self.assertEqual(top[0], "tokens-studio")


class T3AiAutomation(unittest.TestCase):
    """Teste 3: servidores MCP e ferramentas para automatizar desenvolvimento."""

    def test_mcp_for_github(self):
        payload = run_search("automatizar tarefas desenvolvimento github", "--type", "mcp-server")
        self.assertEqual(ids(payload)[0], "github-mcp-server")
        self.assertTrue(all(r["type"] == "mcp-server" for r in payload["results"]))

    def test_deprecated_hidden_by_default(self):
        payload = run_search("wordpress mcp")
        self.assertNotIn("automattic-wordpress-mcp", ids(payload))
        self.assertIn("automattic-wordpress-mcp", payload["hidden_deprecated"])
        shown = run_search("wordpress mcp", "--include-deprecated", "--limit", "50")
        self.assertIn("automattic-wordpress-mcp", ids(shown))
        # mesmo visível, fica abaixo da alternativa recomendada
        order = ids(shown)
        self.assertLess(order.index("wordpress-mcp-adapter"), order.index("automattic-wordpress-mcp"))


class T4CrossCollection(unittest.TestCase):
    """Teste 4: o mesmo recurso em várias coleções sem duplicar metadados."""

    def test_resource_in_multiple_collections(self):
        colls = load_collections()
        member = {}
        for c in colls:
            for ref in c["resources"]:
                member.setdefault(ref["id"], []).append(c["id"])
        multi = {k: v for k, v in member.items() if len(v) > 1}
        self.assertGreaterEqual(len(multi), 3)
        self.assertGreaterEqual(len(member["storybook"]), 2)

    def test_collections_hold_only_references(self):
        allowed = {"id", "role", "rationale"}
        for c in load_collections():
            for ref in c["resources"]:
                self.assertEqual(set(ref) - allowed, set(), f"{c['id']} duplica metadados de {ref['id']}")

    def test_single_source_of_truth(self):
        all_ids = [r["id"] for r in load_resources()]
        self.assertEqual(len(all_ids), len(set(all_ids)))


class T5Security(unittest.TestCase):
    """Teste 5: catalogado ≠ instalado ≠ autorizado ≠ seguro."""

    def test_catalog_has_no_install_or_authorization_fields(self):
        forbidden = {"installed", "authorized", "available", "safe", "approved"}
        for r in load_resources():
            self.assertFalse(forbidden & set(r), f"{r['id']} tem campos de ambiente no catálogo")

    def test_schema_rejects_installed_field(self):
        from jsonschema import Draft202012Validator
        schema = json.loads((ROOT / "schemas/resource.schema.json").read_text(encoding="utf-8"))
        rec = dict(next(r for r in load_resources() if r["id"] == "github-mcp-server"))
        rec = {k: v for k, v in rec.items() if not k.startswith("_")}
        rec["installed"] = True
        self.assertFalse(Draft202012Validator(schema).is_valid(rec))

    def test_search_marks_catalogued_only(self):
        for r in run_search("figma")["results"]:
            self.assertIn("NÃO implica", r["catalog_status"])

    def test_verified_is_not_safe(self):
        verified_risky = [r for r in load_resources()
                          if r["verification"]["status"] == "verified" and r["risk"]["level"] == "high"]
        self.assertTrue(verified_risky, "deve haver recursos verificados mas de risco alto")

    def test_environment_never_grants_blanket_authorization(self):
        for env in load_environments():
            for e in env["entries"]:
                self.assertNotEqual(e["authorization"]["level"], "allowed-with-scope",
                                    "autorizações devem ser concedidas pelo utilizador, não presumidas")

    def test_mcp_servers_flag_code_execution(self):
        for r in load_resources():
            if r["type"] == "mcp-server":
                self.assertTrue(r["risk"]["executes_code"], r["id"])


class T6Integrity(unittest.TestCase):
    """Teste 6: IDs e referências internas válidos."""

    def test_validate_passes(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = validate.main(["--json"])
        report = json.loads(buf.getvalue())
        self.assertEqual(code, 0, report["errors"])
        self.assertEqual(report["errors"], [])

    def test_validate_detects_broken_reference(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "lib"
            shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            p = dst / "collections/web-development.json"
            data = json.loads(p.read_text(encoding="utf-8"))
            data["resources"].append({"id": "nao-existe", "role": "optional", "rationale": "teste de referência inválida"})
            p.write_text(json.dumps(data), encoding="utf-8")
            out = subprocess.run([sys.executable, "scripts/validate.py"], cwd=dst, capture_output=True, text=True,
                                 env={"AI_RESOURCE_LIBRARY_ROOT": str(dst), "PATH": ""})
            self.assertEqual(out.returncode, 1)
            self.assertIn("nao-existe", out.stdout)

    def test_registry_files_exist(self):
        for t, meta in load_registry()["types"].items():
            self.assertTrue((ROOT / "catalog" / meta["file"]).exists(), t)


if __name__ == "__main__":
    unittest.main(verbosity=2)
