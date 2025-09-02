from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def _atomic_write_json(path: Path, data: Any) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, path)


@dataclass
class Crypt:
    """
    Persistent item bank that survives across runs.

    - Capacity-limited (default 3 slots)
    - Simple JSON persistence
    - Accepts items as strings or dicts; internally stored as dicts with at least a 'name' key

    This implementation is intentionally simple and deterministic for unit tests.
    """

    capacity: int = 3
    save_dir: Optional[Path] = None
    filename: str = "crypt.json"
    _items: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("Crypt capacity must be at least 1")
        # Determine save directory; in tests, pass a temp directory
        if self.save_dir is None:
            self.save_dir = Path.home() / ".amormortuorum"
        else:
            self.save_dir = Path(self.save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.save_dir / self.filename
        self._load()

    def _normalize_item(self, item: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(item, str):
            return {"name": item}
        if isinstance(item, dict):
            if "name" not in item and "id" not in item:
                raise ValueError("Item dict must contain a 'name' or 'id' key")
            # Ensure a name exists for equality and user display; fallback to id
            if "name" not in item:
                item = {**item, "name": str(item.get("id"))}
            return item
        raise TypeError("Item must be a string or dict")

    def _load(self) -> None:
        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data.get("items", []) if isinstance(data, dict) else []
                self._items = [self._normalize_item(i) for i in items]
            except Exception:
                # If corrupted, reset to empty to avoid blocking gameplay/tests
                self._items = []
        else:
            self._items = []

    def _save(self) -> None:
        data = {"items": self._items}
        _atomic_write_json(self._path, data)

    @property
    def items(self) -> List[Dict[str, Any]]:
        return list(self._items)

    def deposit(self, item: Union[str, Dict[str, Any]]) -> None:
        if len(self._items) >= self.capacity:
            raise ValueError("Crypt is full")
        norm = self._normalize_item(item)
        self._items.append(norm)
        self._save()

    def withdraw(self, selector: Union[int, str]) -> Dict[str, Any]:
        """
        Withdraw an item by index (int) or by name (str). Returns the withdrawn item.
        Raises ValueError if not found or index out of range.
        """
        if isinstance(selector, int):
            if selector < 0 or selector >= len(self._items):
                raise ValueError("Invalid index")
            item = self._items.pop(selector)
            self._save()
            return item
        elif isinstance(selector, str):
            for idx, item in enumerate(self._items):
                if item.get("name") == selector:
                    removed = self._items.pop(idx)
                    self._save()
                    return removed
            raise ValueError("Item with that name not found")
        else:
            raise TypeError("Selector must be int (index) or str (name)")

    def clear(self) -> None:
        self._items.clear()
        self._save()

    def space_left(self) -> int:
        return self.capacity - len(self._items)

    def is_full(self) -> bool:
        return len(self._items) >= self.capacity
