"""Fail CI when legacy/duplicate GitHub Actions workflows reappear."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "collect.yml": "Market Data Collection",
    "blackrock-universe-to-mongodb.yml": "Company Universe & SEC Sync",
    "largecap-fundamentals.yml": "SEC Fundamentals (Manual)",
    "financial-quality-audit.yml": "Financial Quality Audit (Manual)",
}

def verify(root=ROOT):
    workflows = root / ".github" / "workflows"
    actual = {p.name for p in workflows.iterdir() if p.is_file() and p.suffix in {".yml", ".yaml"}}
    if actual != set(EXPECTED):
        raise RuntimeError(f"Workflow mismatch: extra={sorted(actual-set(EXPECTED))}; missing={sorted(set(EXPECTED)-actual)}")
    for filename, name in EXPECTED.items():
        content = (workflows / filename).read_text(encoding="utf-8")
        if f"name: {name}" not in content:
            raise RuntimeError(f"Unexpected workflow name: {filename}")
    print("WORKFLOW_VERIFY PASS: exactly 4 approved workflows")

if __name__ == "__main__":
    verify()
