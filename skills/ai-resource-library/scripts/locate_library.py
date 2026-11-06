#!/usr/bin/env python3
"""Localiza uma cópia válida da AI Resource Library.

Ordem de procura (a primeira cópia VÁLIDA ganha; nada é clonado se existir uma):
  1. $AI_RESOURCE_LIBRARY_ROOT
  2. Caminhos convencionais no diretório pessoal (~/ai-resource-library, ...)
  3. Caminhos conhecidos de ambientes (ex.: /home/claude/ai-resource-library) e $AI_RESOURCE_LIBRARY_EXTRA_PATHS
  4. Diretórios associados ao projeto atual (o próprio, ./ai-resource-library e antecessores)
  5. Remoto: clone superficial, só de leitura, para uma pasta TEMPORÁRIA (apenas com --remote)

Nunca escreve no repositório remoto, nunca põe credenciais no URL e não imprime variáveis de ambiente.
A autenticação é a que o git já tiver configurada (credential helper, proxy da sessão, gh, SSH).

Saída: JSON em stdout.
  status: found | cloned | not_found | auth_failed | repo_not_found | network_error | remote_error
Códigos de saída: 0 encontrada/clonada · 2 não encontrada localmente (sem --remote) · 3 falha remota

Exemplos:
  python locate_library.py                      # só local
  python locate_library.py --remote             # local e, se preciso, clone temporário
  python locate_library.py --cleanup /tmp/ai-resource-library-abc123
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

DEFAULT_REPO_URL = "https://github.com/rafaelrvaz25-design/ai-resource-library"
TEMP_PREFIX = "ai-resource-library-"
NAMES = ("ai-resource-library", ".ai-resource-library")
CONVENTIONAL_HOME = ("ai-resource-library", ".ai-resource-library", "src/ai-resource-library",
                     "projects/ai-resource-library", "code/ai-resource-library", "dev/ai-resource-library")
KNOWN_ENV_PATHS = ("/home/claude/ai-resource-library", "/workspace/ai-resource-library",
                   "/workspaces/ai-resource-library")
REQUIRED = ("AGENTS.md", "catalog/_registry.json", "schemas/resource.schema.json",
            "schemas/collection.schema.json", "scripts/search.py")


# --------------------------------------------------------------------------- validação

def validate_library(path: Path) -> tuple[bool, str]:
    """Confirma que `path` contém uma AI Resource Library utilizável."""
    try:
        path = Path(path)
        if not path.is_dir():
            return False, "não é um diretório"
        missing = [f for f in REQUIRED if not (path / f).is_file()]
        if missing:
            return False, "faltam ficheiros: " + ", ".join(missing)
        reg = json.loads((path / "catalog/_registry.json").read_text(encoding="utf-8"))
        types = reg.get("types")
        if not isinstance(types, dict) or not types:
            return False, "catalog/_registry.json sem 'types'"
        absent = [m.get("file") for m in types.values() if not (path / "catalog" / str(m.get("file"))).is_file()]
        if absent:
            return False, "ficheiros de catálogo em falta: " + ", ".join(map(str, absent))
        return True, "ok"
    except (OSError, ValueError) as e:
        return False, f"erro ao ler: {type(e).__name__}"


# --------------------------------------------------------------------------- candidatos

def candidate_paths(env: dict, home: Path, cwd: Path, project: Path | None = None,
                    known_paths: tuple[str, ...] = KNOWN_ENV_PATHS) -> list[tuple[str, Path]]:
    cands: list[tuple[str, Path]] = []
    if env.get("AI_RESOURCE_LIBRARY_ROOT"):
        cands.append(("env:AI_RESOURCE_LIBRARY_ROOT", Path(env["AI_RESOURCE_LIBRARY_ROOT"]).expanduser()))
    for rel in CONVENTIONAL_HOME:
        cands.append(("home", home / rel))
    extra = [p for p in env.get("AI_RESOURCE_LIBRARY_EXTRA_PATHS", "").split(os.pathsep) if p]
    for p in list(known_paths) + extra:
        cands.append(("known-environment", Path(p).expanduser()))
    roots = [project] if project else []
    roots.append(cwd)
    for root in roots:
        cur = Path(root).resolve()
        for _ in range(4):  # o próprio diretório e até 3 antecessores
            cands.append(("project", cur))
            for n in NAMES:
                cands.append(("project", cur / n))
            if cur.parent == cur:
                break
            cur = cur.parent
    seen, out = set(), []
    for src, p in cands:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append((src, p))
    return out


def find_local(env: dict, home: Path, cwd: Path, project: Path | None = None,
               known_paths: tuple[str, ...] = KNOWN_ENV_PATHS) -> tuple[dict | None, list[dict]]:
    checked = []
    for src, p in candidate_paths(env, home, cwd, project, known_paths):
        if not p.exists():
            continue  # não listar caminhos inexistentes (seria ruído)
        ok, reason = validate_library(p)
        checked.append({"path": str(p), "source": src, "valid": ok, "reason": reason})
        if ok:
            return {"path": str(p.resolve()), "source": src}, checked
    return None, checked


# --------------------------------------------------------------------------- remoto

GitRunner = Callable[[list[str], int], subprocess.CompletedProcess]


def default_git(args: list[str], timeout: int) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    return subprocess.run(["git", *args], capture_output=True, text=True, timeout=timeout, env=env)


def classify_git_error(stderr: str) -> str:
    s = stderr.lower()
    if any(k in s for k in ("authentication failed", "could not read username", "terminal prompts disabled",
                            "permission denied", "403", "401", "invalid username or password",
                            "access denied", "not enabled for this session")):
        return "auth_failed"
    if any(k in s for k in ("repository not found", "not found", "does not appear to be a git repository",
                            "does not exist")):
        return "repo_not_found"
    if any(k in s for k in ("could not resolve host", "timed out", "connection refused", "network is unreachable",
                            "failed to connect", "connection reset")):
        return "network_error"
    return "remote_error"


REMOTE_HELP = {
    "auth_failed": "Sem acesso autenticado ao repositório privado nesta sessão. Dar acesso ao repositório "
                   "(integração GitHub da sessão, `gh auth login`, credential helper ou SSH) ou usar uma cópia local "
                   "e definir AI_RESOURCE_LIBRARY_ROOT.",
    "repo_not_found": "Repositório não encontrado. Num repositório privado sem autenticação o GitHub também "
                      "responde 'not found': confirmar URL e acesso.",
    "network_error": "Sem ligação à rede/GitHub neste ambiente. Usar uma cópia local (AI_RESOURCE_LIBRARY_ROOT).",
    "remote_error": "O git falhou ao contactar o repositório. Ver 'detail'.",
}


def scrub(text: str) -> str:
    """Remove possíveis credenciais de mensagens do git (ex.: https://user:token@host)."""
    import re
    text = re.sub(r"(https?://)[^/@\s]+@", r"\1***@", text)
    return re.sub(r"(gh[pousr]_|github_pat_)[A-Za-z0-9_]+", r"\1***", text)[:400]


def fetch_remote(repo_url: str, git: GitRunner = default_git, tmp_root: str | None = None,
                 timeout: int = 300) -> dict:
    if "@" in repo_url.split("://", 1)[-1].split("/", 1)[0]:
        return {"status": "remote_error", "message": "Não incluir credenciais no URL do repositório."}
    # 1) verificar acesso antes de criar qualquer pasta
    try:
        probe = git(["ls-remote", "--heads", repo_url], 60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"status": "network_error", "message": REMOTE_HELP["network_error"], "detail": type(e).__name__}
    if probe.returncode != 0:
        status = classify_git_error(probe.stderr)
        return {"status": status, "message": REMOTE_HELP[status], "detail": scrub(probe.stderr.strip())}
    # 2) clone superficial só de leitura para pasta temporária
    dest = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX, dir=tmp_root))
    try:
        res = git(["clone", "--quiet", "--depth", "1", "--single-branch", "--no-tags", repo_url, str(dest)], timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        shutil.rmtree(dest, ignore_errors=True)
        return {"status": "network_error", "message": REMOTE_HELP["network_error"], "detail": type(e).__name__}
    if res.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        status = classify_git_error(res.stderr)
        return {"status": status, "message": REMOTE_HELP[status], "detail": scrub(res.stderr.strip())}
    ok, reason = validate_library(dest)
    if not ok:
        shutil.rmtree(dest, ignore_errors=True)
        return {"status": "remote_error", "message": f"O repositório clonado não é uma biblioteca válida: {reason}"}
    # impedir pushes acidentais a partir da cópia temporária
    git(["-C", str(dest), "remote", "set-url", "--push", "origin", "DISABLED"], 30)
    commit = git(["-C", str(dest), "rev-parse", "--short", "HEAD"], 30)
    return {"status": "cloned", "path": str(dest), "source": "remote-temp", "temporary": True,
            "commit": commit.stdout.strip() or None,
            "message": "Cópia temporária só de leitura. Apagar no fim com --cleanup <path>."}


def cleanup(path: str, tmp_root: str | None = None) -> dict:
    p = Path(path).resolve()
    base = Path(tmp_root or tempfile.gettempdir()).resolve()
    if p.parent != base or not p.name.startswith(TEMP_PREFIX):
        return {"status": "refused", "message": "Só apaga pastas temporárias criadas por este script."}
    shutil.rmtree(p, ignore_errors=True)
    return {"status": "removed", "path": str(p)}


# --------------------------------------------------------------------------- CLI

def locate(env: dict | None = None, home: Path | None = None, cwd: Path | None = None, project: Path | None = None,
           remote: bool = False, repo_url: str | None = None, git: GitRunner = default_git,
           tmp_root: str | None = None, known_paths: tuple[str, ...] = KNOWN_ENV_PATHS) -> dict:
    env = dict(os.environ) if env is None else env
    home = home or Path.home()
    cwd = cwd or Path.cwd()
    found, checked = find_local(env, home, cwd, project, known_paths)
    if found:
        return {"status": "found", "mode": "local", **found, "checked": checked}
    result = {"status": "not_found", "mode": None, "path": None, "checked": checked,
              "message": "Nenhuma cópia local válida. Usar --remote para um clone temporário, ou definir "
                         "AI_RESOURCE_LIBRARY_ROOT."}
    if not remote:
        return result
    url = repo_url or env.get("AI_RESOURCE_LIBRARY_REPO") or DEFAULT_REPO_URL
    r = fetch_remote(url, git=git, tmp_root=tmp_root)
    r["checked"] = checked
    r["mode"] = "remote-temp" if r["status"] == "cloned" else None
    return r



def check_updates(path: Path, repo_url: str = DEFAULT_REPO_URL, git: GitRunner = default_git,
                  check_history: bool = False) -> dict:
    """Verifica main remota; o histórico opcional usa apenas um clone temporário."""
    path = Path(path)
    if not (path / ".git").exists():
        return {"status": "unknown", "reason": "cópia sem metadados Git"}
    try:
        local = git(["-C", str(path), "rev-parse", "HEAD"], timeout=8)
        if local.returncode or not local.stdout.strip():
            return {"status": "unknown", "reason": "não foi possível ler HEAD local"}
        remote = git(["ls-remote", repo_url, "refs/heads/main"], timeout=12)
        if remote.returncode:
            return {"status": "unknown", "reason": "não foi possível consultar a main remota",
                    "detail": scrub(remote.stderr.strip())}
        line = remote.stdout.strip().split()
        if not line:
            return {"status": "unknown", "reason": "main remota não encontrada"}
        head = local.stdout.strip()
        result = {"status": "current" if head == line[0] else "different",
                  "local_sha": head, "remote_sha": line[0]}
        if result["status"] == "current" or not check_history:
            return result
        with tempfile.TemporaryDirectory(prefix="ai-resource-library-history-") as tmp:
            target = tmp + "/repo"
            clone = git(["clone", "--quiet", "--no-hardlinks", "--no-checkout",
                         str(path.resolve()), target], timeout=30)
            if clone.returncode:
                return {**result, "history": "unknown", "reason": "clone temporário falhou",
                        "detail": scrub(clone.stderr.strip())}
            fetched = git(["-C", target, "fetch", "--quiet", "--no-tags",
                           repo_url, "refs/heads/main"], timeout=60)
            if fetched.returncode:
                return {**result, "history": "unknown", "reason": "fetch temporário falhou",
                        "detail": scrub(fetched.stderr.strip())}
            remote_ref = git(["-C", target, "rev-parse", "FETCH_HEAD"], timeout=8)
            if remote_ref.returncode or remote_ref.stdout.strip() != line[0]:
                return {**result, "history": "unknown", "reason": "main remota mudou durante a verificação"}
            behind = git(["-C", target, "merge-base", "--is-ancestor", head, line[0]], timeout=10)
            ahead = git(["-C", target, "merge-base", "--is-ancestor", line[0], head], timeout=10)
            if behind.returncode == 0:
                result["history"] = "behind"
            elif ahead.returncode == 0:
                result["history"] = "ahead"
            elif behind.returncode == 1 and ahead.returncode == 1:
                result["history"] = "diverged"
            else:
                result["history"] = "unknown"
                result["reason"] = "histórico insuficiente ou Git falhou"
            return result
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "unknown", "reason": "Git indisponível ou timeout"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Localiza a AI Resource Library.")
    p.add_argument("--remote", action="store_true", help="Se não houver cópia local, clonar para pasta temporária.")
    p.add_argument("--repo-url", help=f"URL do repositório (omissão: $AI_RESOURCE_LIBRARY_REPO ou {DEFAULT_REPO_URL}).")
    p.add_argument("--project", help="Diretório do projeto atual (omissão: diretório de trabalho).")
    p.add_argument("--cleanup", metavar="PATH", help="Apagar uma cópia temporária criada por --remote.")
    p.add_argument("--check-updates", action="store_true", help="Comparar HEAD local com main remota, sem modificar ficheiros.")
    p.add_argument("--check-history", action="store_true", help="Comparar histórico num clone temporário; requer --check-updates.")
    p.add_argument("--path-only", action="store_true", help="Imprimir só o caminho (vazio se não encontrada).")
    a = p.parse_args(argv)
    if a.check_history and not a.check_updates:
        p.error("--check-history requer --check-updates")
    if a.cleanup:
        r = cleanup(a.cleanup)
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r["status"] == "removed" else 1
    r = locate(project=Path(a.project) if a.project else None, remote=a.remote, repo_url=a.repo_url)
    if a.check_updates and r["status"] == "found":
        r["update_check"] = check_updates(Path(r["path"]), repo_url=a.repo_url or DEFAULT_REPO_URL, check_history=a.check_history)
    if a.path_only:
        print(r.get("path") or "")
    else:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    if r["status"] in ("found", "cloned"):
        return 0
    return 2 if r["status"] == "not_found" else 3


if __name__ == "__main__":
    sys.exit(main())
