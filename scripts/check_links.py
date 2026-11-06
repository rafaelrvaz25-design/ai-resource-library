#!/usr/bin/env python3
"""Verifica os URLs do catálogo (urls.* e verification.sources).

Nunca altera ficheiros: apenas produz um relatório com propostas de correção.
Classificação:
  ok            2xx/3xx
  broken        404/410 ou domínio inexistente  -> propor correção
  inconclusive  401/403/429/5xx/timeouts        -> verificar manualmente (muitos sites bloqueiam bots)

Uso:
  python scripts/check_links.py                     # relatório no terminal
  python scripts/check_links.py --report report.md  # relatório Markdown
  python scripts/check_links.py --fail-on-broken    # exit 1 se houver links partidos
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import re
import socket
import sys
import urllib.error
import urllib.request

from library import load_resources

UA = "ai-resource-library-linkcheck/1.0 (+https://github.com/)"


def api_fallback(url: str) -> str | None:
    """Alguns sites bloqueiam pedidos automáticos (403). Para estes, usar a API oficial equivalente."""
    m = re.match(r"https://github\.com/([^/]+)/([^/#?]+)", url)
    if m and m.group(1) not in ("features", "orgs"):
        return f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}"
    m = re.match(r"https://www\.npmjs\.com/package/(.+)", url)
    if m:
        return f"https://registry.npmjs.org/{m.group(1)}/latest"
    return None


def check(url: str, timeout: int) -> tuple[str, str]:
    status, code = _check(url, timeout)
    if status == "inconclusive" and code in ("403", "429"):
        alt = api_fallback(url)
        if alt:
            s2, c2 = _check(alt, timeout)
            if s2 != "inconclusive":
                return s2, f"{c2} via API"
    return status, code


def _check(url: str, timeout: int) -> tuple[str, str]:
    headers = {"User-Agent": UA, "Accept": "*/*"}
    if url.startswith("https://api.github.com/") and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return "ok", str(r.status)
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (400, 403, 405, 429, 501):
                continue  # alguns servidores não aceitam HEAD
            if e.code in (404, 410):
                return "broken", str(e.code)
            return "inconclusive", str(e.code)
        except urllib.error.URLError as e:
            if isinstance(e.reason, socket.gaierror):
                return "broken", "DNS"
            if method == "HEAD":
                continue
            return "inconclusive", str(e.reason)[:60]
        except (TimeoutError, socket.timeout):
            return "inconclusive", "timeout"
        except Exception as e:  # noqa: BLE001
            return "inconclusive", type(e).__name__
    return "inconclusive", "?"


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--report", help="Escrever relatório Markdown neste ficheiro.")
    p.add_argument("--fail-on-broken", action="store_true")
    p.add_argument("--timeout", type=int, default=15)
    p.add_argument("--workers", type=int, default=8)
    a = p.parse_args(argv)

    urls: dict[str, set[str]] = {}
    for rec in load_resources():
        for k, u in rec["urls"].items():
            if u:
                urls.setdefault(u, set()).add(f"{rec['id']}:urls.{k}")
        for u in rec["verification"].get("sources", []):
            urls.setdefault(u, set()).add(f"{rec['id']}:sources")

    results = {}
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(check, u, a.timeout): u for u in urls}
        for f in cf.as_completed(futs):
            results[futs[f]] = f.result()

    groups = {"broken": [], "inconclusive": [], "ok": []}
    for u, (status, code) in sorted(results.items()):
        groups[status].append((u, code, sorted(urls[u])))

    lines = [f"# Relatório de links\n", f"Total: {len(results)} · ok: {len(groups['ok'])} · "
             f"partidos: {len(groups['broken'])} · inconclusivos: {len(groups['inconclusive'])}\n"]
    if groups["broken"]:
        lines.append("\n## Partidos (propor correção)\n")
        for u, code, refs in groups["broken"]:
            lines.append(f"- [{code}] {u} — usado em {', '.join(refs)}")
    if groups["inconclusive"]:
        lines.append("\n## Inconclusivos (verificar manualmente)\n")
        for u, code, refs in groups["inconclusive"]:
            lines.append(f"- [{code}] {u} — usado em {', '.join(refs)}")
    text = "\n".join(lines) + "\n"
    print(text)
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            f.write(text)
    return 1 if (a.fail_on_broken and groups["broken"]) else 0


if __name__ == "__main__":
    sys.exit(main())
