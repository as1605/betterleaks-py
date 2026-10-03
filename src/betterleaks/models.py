"""Data models for betterleaks scan findings."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class BetterleaksError(Exception):
    """Exception raised for Betterleaks scanning or runtime errors."""
    pass


@dataclass
class Match:
    full: str = ""
    value: str = ""
    fingerprint: Optional[str] = None
    line: Optional[str] = None
    captures: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Match:
        return cls(
            full=data.get("full", ""),
            value=data.get("value", ""),
            fingerprint=data.get("fingerprint"),
            line=data.get("line"),
            captures=data.get("captures") or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "full": self.full,
            "value": self.value,
            "captures": self.captures,
        }
        if self.fingerprint:
            res["fingerprint"] = self.fingerprint
        if self.line:
            res["line"] = self.line
        return res


@dataclass
class Location:
    path: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    start_column: int = 0
    end_column: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Location:
        return cls(
            path=data.get("path"),
            start_line=data.get("start_line", 0),
            end_line=data.get("end_line", 0),
            start_column=data.get("start_column", 0),
            end_column=data.get("end_column", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "start_column": self.start_column,
            "end_column": self.end_column,
        }


@dataclass
class Finding:
    rule_id: str
    description: str
    confidence: str
    match: Match
    location: Location
    tags: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def secret(self) -> str:
        """Convenience property returning the matched secret value."""
        return self.match.value

    @property
    def file(self) -> Optional[str]:
        """Convenience property returning the file path if present."""
        return self.location.path

    @property
    def component_sets(self) -> List[Dict[str, Any]]:
        """Combinations of component findings for multi-part rules (e.g. AWS access/secret keys)."""
        return self.raw.get("component_sets") or []

    @property
    def encodings(self) -> List[str]:
        """List of encodings detected during decode passes."""
        return self.raw.get("encodings") or []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Finding:
        match_data = data.get("match") or {}
        location_data = data.get("location") or {}
        return cls(
            rule_id=data.get("rule_id", ""),
            description=data.get("description", ""),
            confidence=data.get("confidence", ""),
            match=Match.from_dict(match_data),
            location=Location.from_dict(location_data),
            tags=data.get("tags") or [],
            raw=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding back to a standard dictionary."""
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "confidence": self.confidence,
            "secret": self.secret,
            "match": self.match.to_dict(),
            "location": self.location.to_dict(),
            "tags": self.tags,
        }

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access (e.g., finding['rule_id'] or finding['secret'])."""
        if key == "secret":
            return self.secret
        if key == "file":
            return self.file
        if hasattr(self, key):
            val = getattr(self, key)
            if isinstance(val, (Match, Location)):
                return val.to_dict()
            return val
        if key in self.raw:
            return self.raw[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default
