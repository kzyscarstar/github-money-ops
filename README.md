# GitHub Money Ops

Lawful automation for finding, ranking, and preparing GitHub-based earning opportunities.

This workspace is intentionally conservative. It does not spam maintainers, test unauthorized targets, create fake activity, or promise income. It builds a repeatable pipeline around public bounties, open-source issues, portfolio assets, and eventually sponsorable or sellable developer tools.

## Public Identity

- Public name: `scarstar`
- Profile language: bilingual Chinese/English
- Public background policy: do not disclose school, major, private identity details, or personal background.

## Pipeline

1. Scan GitHub issues and bounty boards for public opportunities.
2. Rank opportunities by payout signal, technical fit, freshness, competition, and likely delivery size.
3. Write a daily report to `reports/` and machine-readable data to `data/`.
4. Use Codex to inspect the top candidates and prepare PR-ready patches or project assets.
5. Submit only legitimate work, with human account/payment setup handled by the account owner.

## Quick Start

```bash
cd /Users/scarstar/github-money-ops
./scripts/run_scout.sh
```

Optional:

```bash
export GITHUB_TOKEN=...
```

A GitHub token increases API rate limits. The scanner works without it, but unauthenticated GitHub search is more limited.

## Human-Gated Items

These cannot be safely or legally bypassed by automation:

- platform account sign-in and terms acceptance
- tax, payout, bank, PayPal, Stripe, or crypto wallet setup
- final approval before submitting paid work where platform rules require the account owner
- any security testing permission or bug bounty scope confirmation

Everything else should be automated where practical.

## Sources

The default sources are stored in `config/sources.json`. They currently focus on:

- GitHub issue search
- Algora bounties
- IssueHunt issues
