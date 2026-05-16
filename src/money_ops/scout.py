from __future__ import annotations

import argparse
import datetime as dt
import html
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"


AMOUNT_RE = re.compile(
    r"(?:(?:USD|USDC|USDT)\s*)?[$]\s?([0-9][0-9,]*(?:\.[0-9]+)?)|"
    r"\b([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:USD|USDC|USDT)\b",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def headers() -> dict[str, str]:
    result = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "kzyscarstar-money-ops-scout/0.1",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        result["Authorization"] = f"Bearer {token}"
    return result


def get_text(url: str, *, accept: str | None = None, timeout: int = 20) -> str:
    req_headers = headers()
    if accept:
        req_headers["Accept"] = accept
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        try:
            raw = response.read()
        except http.client.IncompleteRead as exc:
            raw = exc.partial
        return raw.decode(charset, errors="replace")


def get_json(url: str, *, timeout: int = 20) -> dict[str, Any]:
    text = get_text(url, accept="application/vnd.github+json", timeout=timeout)
    return json.loads(text)


def clean_text(value: str | None, limit: int = 260) -> str:
    if not value:
        return ""
    text = html.unescape(re.sub(r"\s+", " ", value)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def extract_amount(text: str) -> float | None:
    values: list[float] = []
    for match in AMOUNT_RE.finditer(text or ""):
        raw = match.group(1) or match.group(2)
        if not raw:
            continue
        try:
            values.append(float(raw.replace(",", "")))
        except ValueError:
            continue
    return max(values) if values else None


def repo_full_name_from_api_url(url: str | None) -> str | None:
    if not url:
        return None
    marker = "/repos/"
    if marker not in url:
        return None
    return url.split(marker, 1)[1]


def fetch_repo_meta(repo_api_url: str | None, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    repo = repo_full_name_from_api_url(repo_api_url)
    if not repo:
        return {}
    if repo in cache:
        return cache[repo]
    try:
        meta = get_json(f"https://api.github.com/repos/{repo}")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        meta = {}
    cache[repo] = meta
    return meta


def github_issue_opportunities(config: dict[str, Any], *, max_queries: int | None = None) -> list[dict[str, Any]]:
    opportunities: list[dict[str, Any]] = []
    repo_cache: dict[str, dict[str, Any]] = {}
    queries = config.get("github_issue_queries", [])
    if max_queries is not None:
        queries = queries[:max_queries]

    for index, item in enumerate(queries):
        query = item["query"]
        per_page = int(item.get("per_page", 10))
        params = urllib.parse.urlencode(
            {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": str(per_page),
            }
        )
        url = f"https://api.github.com/search/issues?{params}"
        try:
            payload = get_json(url)
        except urllib.error.HTTPError as exc:
            print(f"warning: GitHub search failed for {item['name']}: HTTP {exc.code}", file=sys.stderr)
            continue
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"warning: GitHub search failed for {item['name']}: {exc}", file=sys.stderr)
            continue

        for issue in payload.get("items", []):
            repo_meta = fetch_repo_meta(issue.get("repository_url"), repo_cache)
            labels = [label.get("name", "") for label in issue.get("labels", [])]
            body = issue.get("body") or ""
            combined = " ".join([issue.get("title", ""), body, " ".join(labels)])
            amount = extract_amount(combined)
            repo = repo_full_name_from_api_url(issue.get("repository_url"))
            opportunities.append(
                {
                    "source": "GitHub",
                    "source_query": item["name"],
                    "title": clean_text(issue.get("title"), 180),
                    "url": issue.get("html_url"),
                    "repo": repo,
                    "repo_stars": repo_meta.get("stargazers_count"),
                    "repo_language": repo_meta.get("language"),
                    "repo_pushed_at": repo_meta.get("pushed_at"),
                    "labels": labels,
                    "comments": issue.get("comments", 0),
                    "updated_at": issue.get("updated_at"),
                    "amount_usd_signal": amount,
                    "summary": clean_text(body),
                    "risk_text": clean_text(body, 3000),
                }
            )

        if not os.getenv("GITHUB_TOKEN") and index < len(queries) - 1:
            time.sleep(6)

    return opportunities


def absolute_url(base: str, href: str) -> str:
    return urllib.parse.urljoin(base, href)


def strip_tags(fragment: str) -> str:
    return clean_text(re.sub(r"<[^>]+>", " ", fragment), 220)


def bounty_page_opportunities(config: dict[str, Any]) -> list[dict[str, Any]]:
    opportunities: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source in config.get("bounty_pages", []):
        name = source["name"]
        url = source["url"]
        try:
            text = get_text(url, accept="text/html")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, http.client.IncompleteRead) as exc:
            print(f"warning: bounty page failed for {name}: {exc}", file=sys.stderr)
            continue

        for match in re.finditer(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", text, re.IGNORECASE | re.DOTALL):
            href, inner = match.group(1), match.group(2)
            full_url = absolute_url(url, href)
            if full_url in seen:
                continue
            if full_url.endswith("#"):
                continue
            interesting = (
                "github.com/" in full_url
                or "/bount" in full_url.lower()
                or "/issues" in full_url.lower()
                or "issuehunt" in full_url.lower()
            )
            title = strip_tags(inner)
            if not interesting or not title or len(title) < 8:
                continue
            lowered_title = title.lower()
            if " awarded " in f" {lowered_title} " or " shared " in f" {lowered_title} ":
                continue
            window = text[max(0, match.start() - 500) : min(len(text), match.end() + 500)]
            amount = extract_amount(title) or extract_amount(strip_tags(window))
            seen.add(full_url)
            opportunities.append(
                {
                    "source": name,
                    "source_query": "bounty-page",
                    "title": title,
                    "url": full_url,
                    "repo": None,
                    "repo_stars": None,
                    "repo_language": None,
                    "repo_pushed_at": None,
                    "labels": [],
                    "comments": None,
                    "updated_at": None,
                    "amount_usd_signal": amount,
                    "summary": clean_text(strip_tags(window)),
                    "risk_text": clean_text(strip_tags(window), 3000),
                }
            )

    return opportunities


def score(opportunity: dict[str, Any], config: dict[str, Any]) -> tuple[float, list[str]]:
    score_value = 0.0
    reasons: list[str] = []
    text = " ".join(
        [
            str(opportunity.get("title") or ""),
            str(opportunity.get("summary") or ""),
            str(opportunity.get("risk_text") or ""),
            " ".join(opportunity.get("labels") or []),
            str(opportunity.get("repo_language") or ""),
        ]
    ).lower()

    amount = opportunity.get("amount_usd_signal")
    if amount:
        numeric_amount = float(amount)
        if numeric_amount < 20:
            score_value += min(numeric_amount / 5, 4)
            reasons.append(f"micropayment signal around ${amount:g}")
        else:
            score_value += 20 + min(numeric_amount / 20, 40)
            reasons.append(f"payout signal around ${amount:g}")

    if opportunity.get("source") in {"Algora", "IssueHunt"}:
        score_value += 25
        reasons.append("bounty platform source")

    labels = {label.lower() for label in opportunity.get("labels") or []}
    if "help wanted" in labels:
        score_value += 14
        reasons.append("help wanted")
    if "good first issue" in labels:
        score_value += 10
        reasons.append("good first issue")
    if "bug" in labels:
        score_value += 8
        reasons.append("bug fix")
    if any(label in labels for label in {"documentation", "docs"}):
        score_value += 8
        reasons.append("documentation fit")

    for keyword in config.get("positive_keywords", []):
        if keyword.lower() in text:
            score_value += 4
            reasons.append(f"matches {keyword}")

    for keyword in config.get("negative_keywords", []):
        if keyword.lower() in text:
            score_value -= 18
            reasons.append(f"risk: {keyword}")

    comments = opportunity.get("comments")
    if isinstance(comments, int):
        if comments <= 2:
            score_value += 7
            reasons.append("low discussion competition")
        elif comments >= 15:
            score_value -= 8
            reasons.append("crowded discussion")

    stars = opportunity.get("repo_stars")
    if isinstance(stars, int):
        if 50 <= stars <= 20000:
            score_value += 6
            reasons.append("credible repository")
        elif stars > 100000:
            score_value -= 4
            reasons.append("very high competition")

    return round(score_value, 1), reasons[:8]


def dedupe(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in opportunities:
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(item)
    return result


def next_move(item: dict[str, Any]) -> str:
    source = item.get("source")
    if item.get("amount_usd_signal"):
        return "Open the linked bounty terms, verify claim rules, then inspect the repo locally before committing."
    if source == "GitHub":
        return "Inspect issue acceptance criteria, clone repo, run tests, and prepare a minimal PR if the fix is scoped."
    return "Verify that the bounty is active and has clear payout mechanics before spending implementation time."


def write_report(opportunities: list[dict[str, Any]], generated_at: str) -> Path:
    report_path = REPORTS_DIR / f"{generated_at[:10]}-scout.md"
    lines = [
        "# Money Ops Scout Report",
        "",
        f"Generated: {generated_at}",
        "",
        "## Top Opportunities",
        "",
    ]

    if not opportunities:
        lines.extend(["No opportunities found in this run.", ""])
    else:
        for idx, item in enumerate(opportunities[:20], start=1):
            reasons = ", ".join(item.get("score_reasons", [])) or "general fit"
            labels = ", ".join(item.get("labels") or [])
            lines.extend(
                [
                    f"{idx}. [{item.get('title')}]({item.get('url')})",
                    f"   - Score: {item.get('score')}",
                    f"   - Source: {item.get('source')} / {item.get('source_query')}",
                    f"   - Repo: {item.get('repo') or 'unknown'}",
                    f"   - Language: {item.get('repo_language') or 'unknown'}",
                    f"   - Payout signal: {('$' + str(item.get('amount_usd_signal'))) if item.get('amount_usd_signal') else 'none found'}",
                    f"   - Labels: {labels or 'none'}",
                    f"   - Why: {reasons}",
                    f"   - Next move: {next_move(item)}",
                    "",
                ]
            )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def run(max_queries: int | None = None) -> tuple[Path, Path, list[dict[str, Any]]]:
    config = load_json(CONFIG_DIR / "sources.json")
    DATA_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    opportunities = []
    opportunities.extend(github_issue_opportunities(config, max_queries=max_queries))
    opportunities.extend(bounty_page_opportunities(config))
    opportunities = dedupe(opportunities)

    for item in opportunities:
        item["score"], item["score_reasons"] = score(item, config)
        item["next_move"] = next_move(item)

    opportunities.sort(key=lambda item: item.get("score", 0), reverse=True)
    data_path = DATA_DIR / "opportunities.json"
    data_path.write_text(
        json.dumps({"generated_at": generated_at, "opportunities": opportunities}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path = write_report(opportunities, generated_at)
    return data_path, report_path, opportunities


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan GitHub earning opportunities.")
    parser.add_argument("--max-queries", type=int, default=None, help="Limit GitHub issue queries for testing.")
    args = parser.parse_args()

    data_path, report_path, opportunities = run(max_queries=args.max_queries)
    print(f"wrote {data_path}")
    print(f"wrote {report_path}")
    print(f"found {len(opportunities)} opportunities")
    if opportunities:
        top = opportunities[0]
        print(f"top: {top.get('score')} - {top.get('title')} - {top.get('url')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
