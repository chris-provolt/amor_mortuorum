from dataclasses import dataclass, field
from typing import List


@dataclass
class IssueSpec:
    title: str
    body: str
    labels: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)


@dataclass
class EpicSpec:
    title: str
    body: str
    labels: List[str] = field(default_factory=lambda: ["epic"])
    assignees: List[str] = field(default_factory=list)
    children: List[IssueSpec] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "EpicSpec":
        epic_d = d.get("epic", {})
        children_d = d.get("children", [])
        children = [IssueSpec(**c) for c in children_d]
        return EpicSpec(
            title=epic_d.get("title", "EPIC"),
            body=epic_d.get("body", ""),
            labels=epic_d.get("labels", ["epic"]),
            assignees=epic_d.get("assignees", []),
            children=children,
        )
