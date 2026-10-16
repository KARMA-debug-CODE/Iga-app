"""Known vulnerabilities and leaked secrets are looked for on every change and every week
(.github/workflows/security.yml), and Dependabot proposes the upgrades (.github/dependabot.yml). These
tests keep those files doing that: a job or an ecosystem quietly dropped would fail here."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
WORKFLOW = (REPO / ".github" / "workflows" / "security.yml").read_text()
DEPENDABOT = (REPO / ".github" / "dependabot.yml").read_text()


def test_the_security_workflow_runs_on_changes_and_every_week():
    assert re.search(r"^  pull_request:", WORKFLOW, re.M)
    assert re.search(r'^    - cron: "[^"]+"', WORKFLOW, re.M)


def test_python_dependencies_fail_on_any_known_vulnerability():
    assert re.search(r"pip-audit --strict -r backend/requirements\.txt -r backend/requirements-dev\.txt", WORKFLOW)
    assert "--ignore-vuln" not in WORKFLOW.replace("--ignore-vuln <ID>", "")  # none accepted so far


def test_npm_dependencies_fail_on_high_and_critical():
    assert "npm audit --audit-level=high" in WORKFLOW


def test_shipped_images_fail_on_fixable_high_and_critical():
    scan = WORKFLOW[WORKFLOW.index("Scan the backend and web images") : WORKFLOW.index("Report the other images")]
    assert "iga-backend:scan iga-web:scan" in scan
    assert "--severity HIGH,CRITICAL" in scan and "--exit-code 1" in scan
    assert WORKFLOW.count("docker build --pull") == 3  # fresh bases, not a cached copy


def test_every_commit_is_scanned_for_secrets():
    assert "fetch-depth: 0" in WORKFLOW
    assert re.search(r"zricethezav/gitleaks:v\d+\.\d+\.\d+ \\\n\s+git /repo --config /repo/\.gitleaks\.toml", WORKFLOW)
    assert '--log-opts="--all"' in WORKFLOW


def test_the_gitleaks_exceptions_are_values_not_folders():
    config = (REPO / ".gitleaks.toml").read_text()
    assert "useDefault = true" in config
    assert "paths" not in config and "commits" not in config and "stopwords" not in config


def test_dependabot_watches_every_ecosystem():
    entries = re.findall(r"- package-ecosystem: (\S+)\n\s+director(?:y|ies): (.+)", DEPENDABOT)
    assert dict(entries) == {
        "pip": "/backend",
        "npm": "/frontend",
        "docker": "[/backend, /frontend, /coderunner]",
        "docker-compose": "/",
        "github-actions": "/",
    }


def test_nginx_runs_a_maintained_stable_line():
    match = re.search(r"^FROM nginx:1\.(\d+)-alpine", (REPO / "frontend" / "Dockerfile").read_text(), re.M)
    minor = int(match.group(1))
    assert minor % 2 == 0 and minor >= 30  # 1.27 (mainline, end of life) shipped critical OpenSSL CVEs
