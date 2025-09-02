import os
from amormortuorum.issue_tools.epic_generator import EpicGenerator
from amormortuorum.issue_tools.github_client import GitHubClient


class DummyClient(GitHubClient):
    def __init__(self):
        # Do not call base init; this dummy does not perform HTTP
        self.repo = "dummy/dummy"
        self._labels_cache = {}

    def list_labels(self):
        return {}

    def ensure_label(self, name, color="5319e7", description=None):
        return {"name": name, "color": color, "description": description}

    def search_issue_by_title(self, title):
        return None

    def create_issue(self, title, body=None, labels=None, assignees=None, milestone=None):
        # Return incrementing numbers based on hash for determinism not required; use 1
        return {"number": 1, "title": title}

    def update_issue(self, number, body=None, title=None, state=None):
        return {"number": number}

    def comment_on_issue(self, number, body):
        return {"id": 1}


def test_load_config_and_build_body(tmp_path):
    # Use the provided YAML file
    cfg_path = os.path.join("configs", "epics", "turn_based_combat.yaml")
    gen = EpicGenerator(DummyClient())
    cfg = gen.load_config(cfg_path)

    # Dry run to build body
    result = gen.generate(cfg, dry_run=True)

    assert "EPIC: Turn-Based Combat" in result["epic"]["title"]
    body = result["epic"]["body"]
    # Should contain a Checklist header
    assert "Checklist" in body
    # Should list at least one child title
    assert any(c.get("title").startswith("Combat Architecture") for c in result["children"]) 
