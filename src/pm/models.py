from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class RepoRef(BaseModel):
    """GitHub repository reference in owner/name form."""

    owner: str = Field(..., description="Repository owner or organization")
    name: str = Field(..., description="Repository name")

    @classmethod
    def from_full(cls, full: str) -> "RepoRef":
        if "/" not in full:
            raise ValueError("Repository must be in the form 'owner/name'")
        owner, name = full.split("/", 1)
        return cls(owner=owner, name=name)

    def full(self) -> str:
        return f"{self.owner}/{self.name}"


class ChildIssue(BaseModel):
    """Configuration for a child issue that belongs to an Epic."""

    title: str = Field(..., description="Issue title")
    body: str = Field("", description="Issue body/description")
    labels: List[str] = Field(default_factory=list, description="Labels to apply to the issue")
    assignees: Optional[List[str]] = Field(default=None, description="Optional list of assignees")
    milestone: Optional[str] = Field(default=None, description="Optional milestone title (not number)")

    @field_validator("labels")
    @classmethod
    def ensure_labels_not_empty(cls, v: List[str]) -> List[str]:
        # Ensure consistent list type
        return list(v or [])


class EpicConfig(BaseModel):
    """Configuration for creating or updating an Epic and its child issues."""

    epic_title: str = Field(..., description="Epic title")
    epic_body: str = Field("", description="Epic summary body")
    labels: List[str] = Field(default_factory=lambda: ["epic"], description="Labels for the epic issue")
    children: List[ChildIssue] = Field(default_factory=list, description="List of child issues")

    @field_validator("labels")
    @classmethod
    def default_epic_label(cls, v: List[str]) -> List[str]:
        # Guarantee 'epic' label is present
        out = set(v or [])
        out.add("epic")
        return list(out)
