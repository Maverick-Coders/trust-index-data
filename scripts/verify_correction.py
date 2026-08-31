"""Verify a correction issue's evidence and stage an override file (TI-09, FR-C2).

Runs in the verify-correction workflow. Reads the issue form body from the
ISSUE_BODY env var (never interpolated into a shell), fetches the cited public
evidence URL, and checks the corrected value literally appears on that page.
On success it writes `overrides/<domain>.json` for the workflow to open a PR
with; a human still merges. This is a presence check, not comprehension — the
PR reviewer makes the judgment call with the evidence one click away.

Issue text is data: values are matched as strings, never executed, and the
domain is validated before it is ever used in a file path.

Stdlib only — this repo is public and carries no pipeline code.
"""
from __future__ import annotations

import datetime
import html
import json
import os
import re
import sys
import urllib.request

# Mirrors the pipeline's OVERRIDABLE set, minus fields a correction form
# shouldn't drive (summary/summarySource are editorial, hiring is live data).
CORRECTABLE = {
    "name", "segment", "frameworks", "crunchbase", "linkedin",
    "founded", "industry", "firstObserved",
}

_DOMAIN = re.compile(r"^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$")
_MAX_FETCH = 2_000_000  # bytes
USER_AGENT = "trust-index-correction-check (+https://synergetic.solutions/trust-index/methodology)"


def parse_issue_body(body: str) -> dict[str, str]:
    """Issue-form markdown ('### Heading\\n\\nvalue') -> {heading: value}."""
    out: dict[str, str] = {}
    current = None
    lines: dict[str, list[str]] = {}
    for line in (body or "").splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
            lines[current] = []
        elif current is not None:
            lines[current].append(line)
    for heading, chunk in lines.items():
        value = "\n".join(chunk).strip()
        if value == "_No response_":
            value = ""
        out[heading] = value
    return out


def valid_domain(domain: str) -> bool:
    return bool(_DOMAIN.match(domain or ""))


def valid_field(field: str) -> bool:
    return field in CORRECTABLE


def valid_evidence(url: str) -> bool:
    return (url or "").startswith("https://")


def coerce_value(field: str, raw: str):
    """Form text -> the typed value the override will carry (None = invalid)."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if field == "founded":
        return int(raw) if raw.isdigit() and len(raw) == 4 else None
    if field == "frameworks":
        return [p.strip() for p in raw.split(",") if p.strip()]
    return raw


def evidence_supports(page_html: str, value) -> bool:
    """True if the value (every item, for lists) appears in the page text."""
    text = re.sub(r"<[^>]+>", " ", html.unescape(page_html)).lower()
    text = re.sub(r"\s+", " ", text)
    items = value if isinstance(value, list) else [value]
    return all(re.sub(r"\s+", " ", str(i).lower()) in text for i in items)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"user-agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(_MAX_FETCH).decode("utf-8", "replace")


def render_override(domain: str, field: str, value, evidence: str, issue: int, today: str) -> dict:
    return {
        "domain": domain,
        field: value,
        "evidence": evidence,
        "method": "evidence-presence-check",
        "verifiedAt": today,
        "issue": issue,
    }


def _out(key: str, val: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{key}={val}\n")


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    issue = int(os.environ.get("ISSUE_NUMBER", "0"))
    form = parse_issue_body(body)

    domain = form.get("Company domain", "").strip().lower()
    field = form.get("Field to correct", "").strip()
    raw_value = form.get("Corrected value", "")
    evidence = form.get("Public evidence URL", "").strip()

    def reject(msg: str) -> int:
        _out("verified", "false")
        _out("message", msg)
        print(f"NOT VERIFIED: {msg}")
        return 0  # the workflow comments; a rejection is not a job failure

    if not valid_domain(domain):
        return reject(f"`{domain or '(empty)'}` is not a valid registrable domain.")
    if not valid_field(field):
        return reject(f"`{field}` is not a correctable field ({', '.join(sorted(CORRECTABLE))}).")
    value = coerce_value(field, raw_value)
    if value is None:
        return reject(f"could not parse a `{field}` value from {raw_value!r}.")
    if not valid_evidence(evidence):
        return reject("the evidence URL must be a public https:// link.")

    existing_yaml = [p for p in ("yml", "yaml") if os.path.exists(f"overrides/{domain}.{p}")]
    if existing_yaml:
        return reject(f"`overrides/{domain}.{existing_yaml[0]}` is hand-maintained; needs manual review.")

    try:
        page = fetch(evidence)
    except Exception as e:
        return reject(f"could not fetch the evidence URL ({e.__class__.__name__}).")
    if not evidence_supports(page, value):
        return reject("the corrected value does not appear on the cited evidence page.")

    data = render_override(
        domain, field, value, evidence, issue,
        today=datetime.date.today().isoformat(),
    )
    path = f"overrides/{domain}.json"
    if os.path.exists(path):
        with open(path) as f:
            merged = json.load(f)
        merged.update(data)
        data = merged
    os.makedirs("overrides", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    _out("verified", "true")
    _out("domain", domain)
    _out("path", path)
    _out("message", f"evidence check passed; staged `{path}` setting `{field}`.")
    print(f"VERIFIED: wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
