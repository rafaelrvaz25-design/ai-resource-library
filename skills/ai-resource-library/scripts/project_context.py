#!/usr/bin/env python3
"""Extrai o contexto técnico de um projeto para orientar a pesquisa na AI Resource Library.

Só LÊ ficheiros: não executa scripts do projeto, não instala nada, não lê ficheiros .env nem segredos.
Funciona com qualquer linguagem (JavaScript, Python, PHP/WordPress, Go, Rust, Ruby, Java, .NET, estático...).

Limites: profundidade 4, até 4000 entradas, ficheiros lidos até 256 KB, pastas pesadas ignoradas
(node_modules, .git, vendor, dist, build, .next, out, venv...).

Saída: JSON com languages, manifests, dependencies, frameworks, configs, docs, constraints, tooling,
technologies (termos normalizados para o catálogo), gaps e search_queries sugeridas.
Com --library <caminho>, indica também que recursos do catálogo o projeto JÁ usa.

Uso:
  python project_context.py [DIRETÓRIO] [--library CAMINHO] [--compact]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

MAX_DEPTH = 4
MAX_ENTRIES = 4000
MAX_READ = 256 * 1024
SKIP_DIRS = {"node_modules", ".git", "vendor", "dist", "build", ".next", "out", ".nuxt", ".svelte-kit", ".venv",
             "venv", "env", "__pycache__", "target", ".cache", "coverage", ".turbo", ".idea", ".vscode", "bower_components",
             "Pods", ".gradle", "bin", "obj", "uploads", ".output"}
SECRET_NAMES = re.compile(r"^(\.env.*|.*\.pem|.*\.key|id_rsa.*|.*secret.*|.*credentials.*|wp-config\.php)$", re.I)

LANG_EXT = {
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".py": "python", ".php": "php", ".rb": "ruby", ".go": "go", ".rs": "rust",
    ".java": "java", ".kt": "kotlin", ".swift": "swift", ".cs": "csharp", ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".sass": "scss", ".less": "less", ".vue": "vue", ".svelte": "svelte",
    ".astro": "astro", ".md": "markdown", ".mdx": "markdown", ".sql": "sql", ".sh": "shell", ".dart": "dart",
    ".liquid": "liquid", ".twig": "twig",
}

# ficheiro (padrão) -> (tipo, tecnologia)
CONFIG_PATTERNS = [
    (r"^next\.config\.(js|mjs|cjs|ts)$", "framework", "nextjs"),
    (r"^vite\.config\.", "build", "vite"), (r"^astro\.config\.", "framework", "astro"),
    (r"^nuxt\.config\.", "framework", "nuxt"), (r"^svelte\.config\.", "framework", "svelte"),
    (r"^angular\.json$", "framework", "angular"), (r"^remix\.config\.", "framework", "remix"),
    (r"^gatsby-config\.", "framework", "gatsby"),
    (r"^tailwind\.config\.", "styling", "tailwindcss"), (r"^postcss\.config\.", "styling", "postcss"),
    (r"^tsconfig\.json$", "language", "typescript"), (r"^jsconfig\.json$", "language", "javascript"),
    (r"^(\.eslintrc(\..+)?|eslint\.config\..+)$", "lint", "eslint"), (r"^\.prettierrc", "format", "prettier"),
    (r"^playwright\.config\.", "testing", "playwright"), (r"^(jest|vitest|cypress)\.config\.", "testing", None),
    (r"^mkdocs\.ya?ml$", "docs", "mkdocs"), (r"^docusaurus\.config\.", "docs", "docusaurus"),
    (r"^theme\.json$", "cms", "wordpress"), (r"^functions\.php$", "cms", "wordpress"),
    (r"^netlify\.toml$", "hosting", "netlify"), (r"^vercel\.json$", "hosting", "vercel"),
    (r"^(CNAME|\.nojekyll)$", "hosting", "github-pages"), (r"^_config\.yml$", "framework", "jekyll"),
    (r"^Dockerfile$|^docker-compose\.ya?ml$|^compose\.ya?ml$", "container", "docker"),
    (r"^deno\.jsonc?$", "runtime", "deno"), (r"^\.nvmrc$|^\.node-version$", "runtime", "node"),
    (r"^\.python-version$", "runtime", "python"), (r"^\.tool-versions$", "runtime", None),
]
MANIFESTS = {
    "package.json": "javascript", "pyproject.toml": "python", "requirements.txt": "python", "Pipfile": "python",
    "setup.py": "python", "composer.json": "php", "Gemfile": "ruby", "go.mod": "go", "Cargo.toml": "rust",
    "pom.xml": "java", "build.gradle": "java", "build.gradle.kts": "kotlin", "pubspec.yaml": "dart",
}
LOCKFILES = {"package-lock.json": "npm", "yarn.lock": "yarn", "pnpm-lock.yaml": "pnpm", "bun.lockb": "bun",
             "bun.lock": "bun", "poetry.lock": "poetry", "uv.lock": "uv", "composer.lock": "composer",
             "Gemfile.lock": "bundler", "Cargo.lock": "cargo", "go.sum": "go"}
DOC_FILES = re.compile(r"^(README|AGENTS|CLAUDE|CONTRIBUTING|ARCHITECTURE|CHANGELOG)(\.[a-z]+)?$", re.I)

# nome de dependência -> termo do catálogo
DEP_ALIASES = {
    "next": "nextjs", "react": "react", "react-dom": "react", "gsap": "gsap", "framer-motion": "motion",
    "motion": "motion", "three": "threejs", "sass": "sass", "tailwindcss": "tailwindcss",
    "locomotive-scroll": "locomotive-scroll", "marked": "marked", "@playwright/test": "playwright",
    "playwright": "playwright", "storybook": "storybook", "axe-core": "axe-core", "@supabase/supabase-js": "supabase",
    "style-dictionary": "style-dictionary", "eslint-plugin-jsx-a11y": "eslint-plugin-jsx-a11y",
    "@radix-ui/react-slot": "radix-ui-primitives", "lighthouse": "lighthouse", "vue": "vue", "svelte": "svelte",
    "astro": "astro", "@docusaurus/core": "docusaurus", "mkdocs": "mkdocs", "mkdocs-material": "mkdocs-material",
    "django": "django", "flask": "flask", "fastapi": "fastapi", "wp-cli/wp-cli": "wp-cli",
}


def safe_read(p: Path) -> str | None:
    try:
        if SECRET_NAMES.match(p.name) or p.stat().st_size > MAX_READ:
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def scan(root: Path):
    """Percorre o projeto com limites. Devolve lista de caminhos relativos (ficheiros) e se foi truncado."""
    files, truncated, count = [], False, 0
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        depth = 0 if str(rel) == "." else len(rel.parts)
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not (d.startswith(".") and d not in
                             (".github", ".storybook", ".claude", ".cursor", ".wordpress-org")))
        if depth >= MAX_DEPTH:
            dirnames[:] = []
        for f in sorted(filenames):
            count += 1
            if count > MAX_ENTRIES:
                return files, True
            files.append(rel / f)
    return files, truncated


def parse_package_json(text: str) -> dict:
    try:
        d = json.loads(text)
    except ValueError:
        return {"error": "package.json inválido"}
    return {
        "name": d.get("name"), "private": d.get("private"), "type": d.get("type"),
        "dependencies": sorted((d.get("dependencies") or {}).keys()),
        "devDependencies": sorted((d.get("devDependencies") or {}).keys()),
        "versions": {k: v for k, v in {**(d.get("devDependencies") or {}), **(d.get("dependencies") or {})}.items()},
        "scripts": sorted((d.get("scripts") or {}).keys()),  # só nomes: nunca executados
        "engines": d.get("engines"), "packageManager": d.get("packageManager"),
    }


def parse_python_deps(name: str, text: str) -> list[str]:
    deps = []
    if name.startswith("requirements"):
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if line and not line.startswith("-"):
                deps.append(re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0].lower())
    elif name == "pyproject.toml":
        try:
            import tomllib
            d = tomllib.loads(text)
            raw = list(d.get("project", {}).get("dependencies", []))
            raw += list(d.get("tool", {}).get("poetry", {}).get("dependencies", {}).keys())
        except Exception:  # noqa: BLE001  (Python < 3.11 ou TOML inválido)
            raw = re.findall(r'^\s*"([A-Za-z0-9_.\-]+)', text, re.M)
        deps = [re.split(r"[<>=!~\[; ]", r, maxsplit=1)[0].lower() for r in raw if r and r.lower() != "python"]
    return sorted(set(d for d in deps if d))


def parse_composer(text: str) -> list[str]:
    try:
        d = json.loads(text)
    except ValueError:
        return []
    return sorted({**(d.get("require") or {}), **(d.get("require-dev") or {})}.keys())


def workflow_summary(text: str) -> dict:
    return {"uses": sorted(set(re.findall(r"uses:\s*([\w.\-/]+)@", text))),
            "triggers": sorted(set(re.findall(r"^\s{2}(push|pull_request|schedule|workflow_dispatch|release):", text, re.M)))}


def readme_outline(text: str) -> list[str]:
    return [l.strip("# ").strip() for l in text.splitlines() if l.startswith("#")][:15]


def catalog_matches(library: Path, terms: set[str], deps: set[str]) -> list[dict]:
    """Recursos do catálogo que o projeto já usa (por id ou nome do pacote npm/pypi)."""
    out = []
    try:
        reg = json.loads((library / "catalog/_registry.json").read_text(encoding="utf-8"))
        for meta in reg["types"].values():
            for r in json.loads((library / "catalog" / meta["file"]).read_text(encoding="utf-8")):
                pkg = (r.get("urls") or {}).get("package") or ""
                pkg_name = pkg.split("/package/", 1)[-1] if "/package/" in pkg else None
                if r["id"] in terms or (pkg_name and pkg_name in deps):
                    out.append({"id": r["id"], "name": r["name"], "type": r["type"],
                                "verification": r["verification"]["status"]})
    except (OSError, ValueError, KeyError):
        pass
    return sorted(out, key=lambda x: x["id"])


def analyse(root: Path, library: Path | None = None) -> dict:
    root = root.resolve()
    files, truncated = scan(root)
    names = {str(f): f for f in files}
    top = [f for f in files if len(f.parts) == 1]

    langs = Counter()
    for f in files:
        lang = LANG_EXT.get(f.suffix.lower())
        if lang:
            langs[lang] += 1

    manifests, deps, dep_versions, configs, techs = {}, set(), {}, [], set()
    lockfiles = sorted({LOCKFILES[f.name] for f in files if f.name in LOCKFILES and len(f.parts) <= 2})
    for f in files:
        if f.name in MANIFESTS and len(f.parts) <= 2:
            text = safe_read(root / f) or ""
            entry = {"language": MANIFESTS[f.name], "path": str(f)}
            if f.name == "package.json":
                pj = parse_package_json(text)
                entry.update(pj)
                deps |= set(pj.get("dependencies", [])) | set(pj.get("devDependencies", []))
                dep_versions.update(pj.get("versions", {}))
                entry.pop("versions", None)
            elif f.name in ("requirements.txt", "pyproject.toml"):
                entry["dependencies"] = parse_python_deps(f.name, text)
                deps |= set(entry["dependencies"])
            elif f.name == "composer.json":
                entry["dependencies"] = parse_composer(text)
                deps |= set(entry["dependencies"])
            manifests[str(f)] = entry
        for pat, kind, tech in CONFIG_PATTERNS:
            if re.match(pat, f.name) and len(f.parts) <= 3:
                configs.append({"path": str(f), "kind": kind, "technology": tech})
                if tech:
                    techs.add(tech)
                break

    for d in deps:
        if d in DEP_ALIASES:
            techs.add(DEP_ALIASES[d])
        elif d.startswith("@storybook/"):
            techs.add("storybook")
        elif d.startswith("@radix-ui/"):
            techs.add("radix-ui-primitives")
    techs |= {l for l in langs if l in ("python", "php", "go", "rust", "ruby", "java", "html", "css", "typescript")}

    # WordPress (tema ou plugin) e Supabase
    for f in files:
        if f.suffix == ".php" and len(f.parts) == 1:
            head = (safe_read(root / f) or "")[:2000]
            if re.search(r"Plugin Name:", head):
                techs.add("wordpress")
        if f.name == "style.css" and len(f.parts) == 1 and "Theme Name:" in (safe_read(root / f) or "")[:2000]:
            techs.add("wordpress")
        if "wp-content" in f.parts:
            techs.add("wordpress")
        if len(f.parts) >= 2 and f.parts[0] == "supabase":
            techs.add("supabase")

    workflows = {}
    for f in files:
        if len(f.parts) == 3 and f.parts[:2] == (".github", "workflows") and f.suffix in (".yml", ".yaml"):
            workflows[f.name] = workflow_summary(safe_read(root / f) or "")
    if workflows:
        techs.add("github-actions")

    docs, mentioned = {}, set()
    for f in files:
        if DOC_FILES.match(f.name) and len(f.parts) <= 2:
            text = safe_read(root / f) or ""
            docs[str(f)] = {"outline": readme_outline(text)}
            low = text.lower()
            if len(f.parts) == 1:
                for term, tech in (("github pages", "github-pages"), ("gh-pages", "github-pages"),
                                   ("wordpress", "wordpress"), ("netlify", "netlify"), ("supabase", "supabase"),
                                   ("figma", "figma"), ("vercel", "vercel")):
                    if term in low:
                        mentioned.add(tech)
    has_docs_dir = any(f.parts[0] == "docs" for f in files if len(f.parts) > 1)

    # restrições lidas de configurações conhecidas (regex, sem executar)
    constraints = []
    for c in configs:
        if c["technology"] == "nextjs":
            t = safe_read(root / c["path"]) or ""
            if re.search(r"output\s*:\s*['\"]export['\"]", t):
                constraints.append("Next.js com exportação estática (output: 'export'): sem funcionalidades de servidor")
            if re.search(r"basePath", t):
                constraints.append("Usa basePath (site servido num subcaminho)")
            if re.search(r"ignoreDuringBuilds\s*:\s*true", t):
                constraints.append("ESLint desativado durante o build (ignoreDuringBuilds: true)")
    for m in manifests.values():
        if m.get("engines"):
            constraints.append(f"engines: {m['engines']}")
    if dep_versions.get("next"):
        constraints.append(f"Versão de Next.js: {dep_versions['next']}")
    for f in top:
        if f.name in (".nvmrc", ".node-version", ".python-version"):
            constraints.append(f"{f.name}: {(safe_read(root / f) or '').strip()[:20]}")

    has_tests = any(re.search(r"(^|/)(tests?|__tests__|spec)(/|$)", str(f)) or re.search(r"\.(test|spec)\.", f.name)
                    for f in files)
    agent_files = sorted(str(f) for f in files if f.name in ("AGENTS.md", "CLAUDE.md") or
                         (len(f.parts) >= 2 and f.parts[0] in (".cursor", ".claude")))

    # lacunas -> pesquisas sugeridas (heurísticas simples, documentadas)
    gaps, queries = [], []
    if not workflows:
        gaps.append("Sem CI/CD (.github/workflows)")
        queries.append("github actions deploy" if "github-pages" in (techs | mentioned) else "github actions")
    if not has_tests:
        gaps.append("Sem testes automatizados detetados")
        queries.append("testing " + ("responsive browser" if langs.get("html") or "react" in techs else ""))
    if "react" in techs and "eslint-plugin-jsx-a11y" not in deps:
        queries.append("react accessibility lint")
    if any("ESLint desativado" in c for c in constraints):
        gaps.append("Lint não é aplicado no build")
    if langs.get("html") or "react" in techs or "wordpress" in techs:
        queries.append("performance accessibility audit")
    if not agent_files:
        gaps.append("Sem instruções para agentes (AGENTS.md/CLAUDE.md)")
    context_techs = techs | mentioned
    if "github-pages" in context_techs and "nextjs" in techs:
        queries.insert(0, "github pages nextjs deploy")
    if "wordpress" in techs:
        queries.insert(0, "wordpress")

    tooling = {
        "dependencies_installed": {"node_modules": (root / "node_modules").is_dir(),
                                   "python_venv": any((root / v).is_dir() for v in (".venv", "venv")),
                                   "vendor": (root / "vendor").is_dir()},
        "environment_commands": {c: bool(shutil.which(c)) for c in
                                 ("git", "node", "npm", "python3", "php", "composer", "go", "cargo", "docker", "gh")},
        "lockfiles": lockfiles,
        "workflows": workflows,
        "agent_instruction_files": agent_files,
    }

    result = {
        "project": root.name,
        "scanned": {"files": len(files), "truncated": truncated, "max_depth": MAX_DEPTH},
        "languages": dict(langs.most_common(8)),
        "manifests": manifests,
        "configs": configs,
        "technologies": sorted(techs),
        "mentioned_in_docs": sorted(mentioned - techs),
        "docs": {"files": docs, "docs_dir": has_docs_dir},
        "constraints": constraints,
        "tooling": tooling,
        "gaps": gaps,
        "search_queries": [q.strip() for q in dict.fromkeys(queries) if q.strip()],
        "notes": "Análise estática e limitada; nenhum script do projeto foi executado. 'environment_commands' "
                 "descreve o ambiente atual, não o projeto.",
    }
    if library:
        result["already_used_catalog_resources"] = catalog_matches(Path(library), techs, deps)
        result["possibly_used_catalog_resources"] = [
            r for r in catalog_matches(Path(library), mentioned - techs, set())]
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Contexto técnico de um projeto (só leitura).")
    p.add_argument("project", nargs="?", default=".")
    p.add_argument("--library", help="Caminho da AI Resource Library para indicar recursos já usados.")
    p.add_argument("--compact", action="store_true", help="Só tecnologias, restrições, lacunas e pesquisas.")
    a = p.parse_args(argv)
    root = Path(a.project)
    if not root.is_dir():
        print(json.dumps({"error": f"'{a.project}' não é um diretório"}, ensure_ascii=False))
        return 1
    r = analyse(root, Path(a.library) if a.library else None)
    if a.compact:
        r = {k: r[k] for k in ("project", "languages", "technologies", "mentioned_in_docs", "constraints", "gaps",
                               "search_queries")
             if k in r} | ({"already_used_catalog_resources": r["already_used_catalog_resources"]}
                           if "already_used_catalog_resources" in r else {})
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
