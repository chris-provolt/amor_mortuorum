"""Epic management package for GitHub issue tracking.

Provides utilities to define Epics via YAML configs and synchronize
child issues, labels, and progress checklists on GitHub.

Main entrypoints:
- epics.github_api.GitHubAPI
- epics.manager.EpicManager

CLI:
- tools/epics/sync_epic.py
"""

__all__ = [
    "__version__",
]

__version__ = "0.1.0"
