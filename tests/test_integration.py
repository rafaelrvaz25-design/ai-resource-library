"""Testes de integração entre projetos: descoberta da biblioteca, fallback remoto e contexto do projeto.

Sem credenciais reais nem rede: o "remoto" é um repositório Git local (file://) e as falhas de autenticação
são simuladas com um executor de git falso.

Executar:  python -m unittest discover -s tests -v
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_SCRIPTS = ROOT / "skills/ai-resource-library/scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import locate_library as ll  # noqa: E402
import project_context as pc  # noqa: E402

NO_KNOWN = ()  # isola os testes de caminhos reais do ambiente (ex.: /home/claude/ai-resource-library)


def make_library(dest: Path) -> Path:
    """Cópia mínima e válida da biblioteca (só os ficheiros que a validação exige)."""
    for rel in ll.REQUIRED:
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, dest / rel)
    reg = json.loads((ROOT / "catalog/_registry.json").read_text(encoding="utf-8"))
    for meta in reg["types"].values():
        shutil.copy(ROOT / "catalog" / meta["file"], dest / "catalog" / meta["file"])
    return dest


def fake_git(returncode=0, stderr="", stdout=""):
    calls = []

    def run(args, timeout):
        calls.append(args)
        return subprocess.CompletedProcess(["git", *args], returncode, stdout=stdout, stderr=stderr)
    run.calls = calls
    return run


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.cwd = self.tmp / "work" / "projeto"
        self.cwd.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def locate(self, **kw):
        kw.setdefault("env", {})
        kw.setdefault("home", self.home)
        kw.setdefault("cwd", self.cwd)
        kw.setdefault("known_paths", NO_KNOWN)
        return ll.locate(**kw)


class TestDiscovery(Base):
    def test_found_by_environment_variable(self):
        lib = make_library(self.tmp / "algures" / "lib")
        make_library(self.home / "ai-resource-library")  # também existe, mas a variável tem prioridade
        r = self.locate(env={"AI_RESOURCE_LIBRARY_ROOT": str(lib)})
        self.assertEqual(r["status"], "found")
        self.assertEqual(r["source"], "env:AI_RESOURCE_LIBRARY_ROOT")
        self.assertEqual(Path(r["path"]), lib.resolve())

    def test_found_in_conventional_local_path(self):
        make_library(self.home / "ai-resource-library")
        r = self.locate()
        self.assertEqual((r["status"], r["source"]), ("found", "home"))

    def test_found_in_alternative_known_path(self):
        alt = make_library(self.tmp / "mnt" / "ai-resource-library")
        r = self.locate(known_paths=(str(alt),))
        self.assertEqual((r["status"], r["source"]), ("found", "known-environment"))

    def test_found_via_extra_paths_variable(self):
        alt = make_library(self.tmp / "partilhado" / "ai-resource-library")
        r = self.locate(env={"AI_RESOURCE_LIBRARY_EXTRA_PATHS": str(alt)})
        self.assertEqual(r["source"], "known-environment")

    def test_found_in_project_directories(self):
        make_library(self.tmp / "work" / "ai-resource-library")  # irmão do projeto
        r = self.locate()
        self.assertEqual((r["status"], r["source"]), ("found", "project"))

    def test_existing_but_invalid_directory_is_skipped(self):
        bad = self.home / "ai-resource-library"
        (bad / "catalog").mkdir(parents=True)
        (bad / "catalog/_registry.json").write_text("{}", encoding="utf-8")
        good = make_library(self.tmp / "mnt" / "ai-resource-library")
        r = self.locate(known_paths=(str(good),))
        self.assertEqual(r["status"], "found")
        self.assertEqual(Path(r["path"]), good.resolve())
        invalid = [c for c in r["checked"] if not c["valid"]]
        self.assertTrue(any(Path(c["path"]) == bad for c in invalid))
        self.assertIn("faltam ficheiros", invalid[0]["reason"])

    def test_invalid_env_path_falls_through(self):
        make_library(self.home / "ai-resource-library")
        r = self.locate(env={"AI_RESOURCE_LIBRARY_ROOT": str(self.tmp / "nao-existe")})
        self.assertEqual(r["source"], "home")

    def test_registry_listing_missing_catalog_file_is_invalid(self):
        lib = make_library(self.tmp / "lib")
        (lib / "catalog/tools.json").unlink()
        ok, reason = ll.validate_library(lib)
        self.assertFalse(ok)
        self.assertIn("tools.json", reason)

    def test_unavailable_locally_without_remote(self):
        r = self.locate()
        self.assertEqual(r["status"], "not_found")
        self.assertIsNone(r["path"])
        self.assertIn("--remote", r["message"])

    def test_local_copy_prevents_clone(self):
        make_library(self.home / "ai-resource-library")
        git = fake_git()
        r = self.locate(remote=True, git=git)
        self.assertEqual(r["status"], "found")
        self.assertEqual(git.calls, [], "não deve contactar o remoto quando há cópia local válida")


@unittest.skipUnless(shutil.which("git"), "git não disponível")
class TestRemoteFallback(Base):
    def make_remote(self) -> str:
        src = make_library(self.tmp / "origem")
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@e", "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(self.home)}
        for cmd in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
            subprocess.run(["git", "-C", str(src), *cmd], check=True, env=env, capture_output=True)
        return src.resolve().as_uri()

    def test_remote_fallback_clones_to_temp_and_cleans_up(self):
        tmp_root = self.tmp / "tmp"
        tmp_root.mkdir()
        r = self.locate(remote=True, repo_url=self.make_remote(), tmp_root=str(tmp_root))
        self.assertEqual(r["status"], "cloned", r)
        self.assertEqual(r["mode"], "remote-temp")
        path = Path(r["path"])
        self.assertEqual(path.parent, tmp_root.resolve())
        self.assertTrue(path.name.startswith(ll.TEMP_PREFIX))
        self.assertTrue(ll.validate_library(path)[0])
        push = subprocess.run(["git", "-C", str(path), "remote", "get-url", "--push", "origin"],
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(push, "DISABLED", "push deve ficar desativado na cópia temporária")
        self.assertEqual(ll.cleanup(str(path), tmp_root=str(tmp_root))["status"], "removed")
        self.assertFalse(path.exists())

    def test_remote_repo_not_found(self):
        r = self.locate(remote=True, repo_url=(self.tmp / "nada").as_uri(), tmp_root=str(self.tmp))
        self.assertEqual(r["status"], "repo_not_found")
        self.assertFalse(any(p.name.startswith(ll.TEMP_PREFIX) for p in self.tmp.iterdir()),
                         "não deve criar pasta temporária quando o acesso falha")


class TestRemoteErrors(Base):
    def test_authentication_failure_is_reported_clearly(self):
        fake_token = "gh" + "p_" + "SECRET" * 6  # montado em runtime para não disparar o detetor de segredos
        git = fake_git(128, f"fatal: Authentication failed for 'https://{fake_token}@github.com/x/y'")
        r = self.locate(remote=True, git=git, tmp_root=str(self.tmp))
        self.assertEqual(r["status"], "auth_failed")
        self.assertIn("acesso", r["message"])
        self.assertNotIn("SECRETSECRET", json.dumps(r), "credenciais não podem aparecer na saída")
        self.assertEqual(len(git.calls), 1, "falha no ls-remote não deve tentar clonar")
        self.assertEqual(git.calls[0][0], "ls-remote")

    def test_terminal_prompt_disabled_counts_as_auth_failure(self):
        git = fake_git(128, "fatal: could not read Username for 'https://github.com': terminal prompts disabled")
        self.assertEqual(self.locate(remote=True, git=git, tmp_root=str(self.tmp))["status"], "auth_failed")

    def test_network_failure(self):
        git = fake_git(128, "fatal: unable to access: Could not resolve host: github.com")
        self.assertEqual(self.locate(remote=True, git=git, tmp_root=str(self.tmp))["status"], "network_error")

    def test_credentials_in_url_are_refused(self):
        r = ll.fetch_remote("https://user:token@github.com/x/y", git=fake_git())
        self.assertEqual(r["status"], "remote_error")

    def test_cleanup_refuses_arbitrary_directories(self):
        victim = self.tmp / "importante"
        victim.mkdir()
        self.assertEqual(ll.cleanup(str(victim))["status"], "refused")
        self.assertTrue(victim.exists())

    def test_cli_exit_codes(self):
        out = subprocess.run([sys.executable, "-I", str(SKILL_SCRIPTS / "locate_library.py"), "--path-only"],
                             cwd=self.cwd, capture_output=True, text=True,
                             env={"HOME": str(self.home), "PATH": "", "AI_RESOURCE_LIBRARY_ROOT": str(self.tmp / "x")})
        # pode encontrar um caminho conhecido real do ambiente (exit 0) ou nenhum (exit 2); nunca erro
        self.assertIn(out.returncode, (0, 2), out.stderr)


class TestUpdateCheck(unittest.TestCase):
    def test_current_and_different(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / ".git").mkdir()
            def same(args, timeout):
                return subprocess.CompletedProcess(args, 0, stdout="abc123\n" if "rev-parse" in args else "abc123\trefs/heads/main\n", stderr="")
            def different(args, timeout):
                return subprocess.CompletedProcess(args, 0, stdout="abc123\n" if "rev-parse" in args else "def456\trefs/heads/main\n", stderr="")
            self.assertEqual(ll.check_updates(path, git=same)["status"], "current")
            self.assertEqual(ll.check_updates(path, git=different)["status"], "different")

    def test_real_git_history_behind_ahead_and_diverged(self):
        def run(*args):
            subprocess.run(["git", *map(str, args)], check=True, capture_output=True, text=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "remote.git"
            work = root / "work"
            run("init", "--bare", remote)
            run("init", "-b", "main", work)
            run("-C", work, "config", "user.email", "test@example.invalid")
            run("-C", work, "config", "user.name", "Test")
            (work / "test.txt").write_text("one")
            run("-C", work, "add", "test.txt")
            run("-C", work, "commit", "-m", "one")
            run("-C", work, "remote", "add", "origin", remote)
            run("-C", work, "push", "-u", "origin", "main")
            (work / "test.txt").write_text("two")
            run("-C", work, "commit", "-am", "two")
            self.assertEqual(ll.check_updates(work, str(remote), check_history=True)["history"], "ahead")
            run("-C", work, "push", "origin", "main")
            old = root / "old"
            run("clone", "-b", "main", remote, old)
            (work / "test.txt").write_text("three")
            run("-C", work, "commit", "-am", "three")
            run("-C", work, "push", "origin", "main")
            self.assertEqual(ll.check_updates(old, str(remote), check_history=True)["history"], "behind")
            run("-C", old, "config", "user.email", "test@example.invalid")
            run("-C", old, "config", "user.name", "Test")
            (old / "test.txt").write_text("local")
            run("-C", old, "commit", "-am", "local")
            self.assertEqual(ll.check_updates(old, str(remote), check_history=True)["history"], "diverged")

    def test_missing_git_or_network_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            self.assertEqual(ll.check_updates(path)["status"], "unknown")
            (path / ".git").mkdir()
            def failure(args, timeout):
                if "rev-parse" in args:
                    return subprocess.CompletedProcess(args, 0, stdout="abc123\n", stderr="")
                return subprocess.CompletedProcess(args, 128, stdout="", stderr="Could not resolve host")
            self.assertEqual(ll.check_updates(path, git=failure)["status"], "unknown")



class TestProjectContext(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "proj"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def w(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_javascript_project(self):
        self.w("package.json", json.dumps({
            "name": "site", "scripts": {"build": "next build", "postinstall": "rm -rf /"},
            "dependencies": {"next": "13.4.10", "react": "18.2.0", "gsap": "^3", "framer-motion": "^10"},
            "devDependencies": {"sass": "^1"}}))
        self.w("package-lock.json", "{}")
        self.w("next.config.js", "module.exports = { output: 'export', basePath: process.env.BASE_PATH, "
                                 "eslint: { ignoreDuringBuilds: true } }")
        self.w("src/app/page.jsx", "export default function P(){return null}")
        self.w("README.md", "# Site\nPublicado com GitHub Pages.\n## Comandos\n")
        self.w(".env.local", "SECRET=ghp_naoleras")
        self.w("node_modules/x/index.js", "")
        r = pc.analyse(self.root, library=ROOT)
        for t in ("nextjs", "react", "gsap", "motion", "sass"):
            self.assertIn(t, r["technologies"])
        self.assertIn("github-pages", r["mentioned_in_docs"])
        self.assertIn("javascript", r["languages"])
        self.assertTrue(any("exportação estática" in c for c in r["constraints"]))
        self.assertTrue(any("ESLint desativado" in c for c in r["constraints"]))
        self.assertIn("Sem CI/CD (.github/workflows)", r["gaps"])
        self.assertEqual(r["search_queries"][0], "github pages nextjs deploy")
        self.assertIn("npm", r["tooling"]["lockfiles"])
        used = {x["id"] for x in r["already_used_catalog_resources"]}
        self.assertTrue({"nextjs", "react", "gsap", "motion", "sass"} <= used)
        dump = json.dumps(r)
        self.assertNotIn("ghp_naoleras", dump, "não pode ler .env")
        self.assertNotIn("rm -rf", dump, "só nomes de scripts, nunca o conteúdo")
        self.assertNotIn("node_modules", json.dumps(r["configs"]))


    def test_goal_detects_plural_images_and_colors(self):
        queries = pc.goal_queries("Melhorar as cores, imagens, tipografia e performance")
        self.assertIn("cores contraste", queries)
        self.assertIn("imagens otimizacao", queries)
        self.assertIn("tipografia", queries)
        self.assertIn("performance", queries)
        self.assertEqual(len(queries), len(set(queries)))

    def test_goal_does_not_infer_unmentioned_areas(self):
        self.assertEqual(pc.goal_queries("Corrigir deploy do website"), [])
        self.assertEqual(pc.goal_queries("fontes de pesquisa"), [])

    def test_goal_first_queries(self):
        self.w("package.json", json.dumps({"dependencies": {"react": "18"}}))
        r = pc.analyse(self.root, goal="Melhorar a qualidade visual e acessibilidade do portfolio")
        self.assertEqual(r["search_queries"][0], "direcao visual interface")
        self.assertIn("acessibilidade", r["search_queries"])
        self.assertIn("react accessibility lint", r["search_queries"])
        self.assertEqual(pc.goal_queries(""), [])


    def test_project_without_package_json(self):
        self.w("pyproject.toml", '[project]\nname="api"\ndependencies=["fastapi>=0.1","requests"]\n')
        self.w("app/main.py", "print('ok')\n")
        self.w("tests/test_main.py", "")
        self.w(".github/workflows/ci.yml", "on:\n  push:\njobs:\n  t:\n    steps:\n      - uses: actions/checkout@v4\n")
        r = pc.analyse(self.root)
        self.assertNotIn("package.json", r["manifests"])
        self.assertIn("python", r["languages"])
        self.assertIn("python", r["technologies"])
        self.assertIn("fastapi", r["technologies"])
        self.assertIn("github-actions", r["technologies"])
        self.assertNotIn("Sem testes automatizados detetados", r["gaps"])
        self.assertNotIn("javascript", r["technologies"])

    def test_wordpress_theme_without_package_json(self):
        self.w("style.css", "/*\nTheme Name: Landing\n*/")
        self.w("functions.php", "<?php\n")
        self.w("theme.json", "{}")
        self.w("wp-config.php", "<?php define('DB_PASSWORD','segredo');")
        r = pc.analyse(self.root)
        self.assertIn("wordpress", r["technologies"])
        self.assertIn("php", r["languages"])
        self.assertEqual(r["search_queries"][0], "wordpress")
        self.assertNotIn("segredo", json.dumps(r))

    def test_static_site_only_html(self):
        self.w("index.html", "<html></html>")
        self.w("assets/css/style.css", "body{}")
        r = pc.analyse(self.root)
        self.assertEqual(r["manifests"], {})
        self.assertIn("html", r["technologies"])

    def test_does_not_execute_project_code(self):
        marker = self.root / "EXECUTADO"
        self.w("setup.py", f"open({str(marker)!r},'w').write('x')\n")
        self.w("package.json", json.dumps({"scripts": {"preinstall": f"touch {marker}"}}))
        pc.analyse(self.root)
        self.assertFalse(marker.exists())

    def test_scan_limits(self):
        deep = self.root / "a/b/c/d/e/f"
        deep.mkdir(parents=True)
        (deep / "fundo.py").write_text("", encoding="utf-8")
        r = pc.analyse(self.root)
        self.assertNotIn("python", r["languages"], "deve respeitar a profundidade máxima")


if __name__ == "__main__":
    unittest.main(verbosity=2)
