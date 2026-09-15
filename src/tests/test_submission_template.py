"""
src/tests/test_submission_template.py
Validates that the repository satisfies all structural and metadata
rules defined in drijesh-ppatel/bob-ai-hackathon-submission-template
and tested by .github/workflows/validate.yml.

NOTE: This file lives at src/tests/, so REPO_ROOT resolves 3 levels up
(src/tests/ -> src/ -> repo root).
"""

import os
import yaml
import pytest

# File is at: <repo_root>/src/tests/test_submission_template.py
# parents[0] = src/tests/  parents[1] = src/  parents[2] = repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_required_files_exist():
    required_files = [
        "README.md",
        "submission.yaml",
        "docs/problem-statement.md",
        "docs/solution-overview.md",
        "docs/architecture.md",
        "docs/setup-guide.md",
        "demo/demo-video-link.txt",
    ]
    missing = [f for f in required_files if not os.path.isfile(os.path.join(REPO_ROOT, f))]
    assert not missing, f"Missing required template files: {missing}"


def test_submission_yaml_validity():
    yaml_path = os.path.join(REPO_ROOT, "submission.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Check team fields
    team = data.get("team", {})
    assert team.get("name"), "team.name must not be empty"
    assert team.get("track") in ["AI", "DevOps", "Sustainability", "Open"], (
        f"team.track must be one of AI | DevOps | Sustainability | Open, got {team.get('track')}"
    )

    lead = team.get("lead", {})
    assert lead.get("name"), "team.lead.name must not be empty"
    assert lead.get("email"), "team.lead.email must not be empty"

    # Check submission fields
    sub = data.get("submission", {})
    assert sub.get("title"), "submission.title must not be empty"
    assert sub.get("problem_statement"), "submission.problem_statement must not be empty"
    assert sub.get("solution_summary"), "submission.solution_summary must not be empty"

    features = sub.get("key_features", [])
    assert len(features) >= 1, "submission.key_features must contain at least 1 feature"


def test_src_directory_contains_source_code():
    src_dir = os.path.join(REPO_ROOT, "src")
    assert os.path.isdir(src_dir), "src/ directory must exist"

    code_files = [
        os.path.join(dp, f)
        for dp, _, fn in os.walk(src_dir)
        for f in fn
        if f not in ["README.md", ".env.example"]
    ]
    assert len(code_files) >= 1, "src/ must contain actual code files"


def test_demo_video_link_not_placeholder():
    video_path = os.path.join(REPO_ROOT, "demo", "demo-video-link.txt")
    with open(video_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "your-demo-video-link-here" not in content, "demo/demo-video-link.txt still contains template placeholder"


def test_readme_no_placeholders():
    readme_path = os.path.join(REPO_ROOT, "README.md")
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "[Your Project Title Here]" not in content, "README.md contains '[Your Project Title Here]'"
    assert "[Your Team Name]" not in content, "README.md contains '[Your Team Name]'"
