from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..data.loader import DataLoader
from ..models.prefab import PrefabDef, PrefabInstance

logger = logging.getLogger(__name__)


class TiledPrefabLoader:
    """Extract prefab instances from a Tiled JSON map using prefab definitions.

    Conventions:
    - Your Tiled map is exported as JSON (not TMX)
    - Prefabs are represented as objects in any objectgroup layer
    - Each object should set its "type" (or "class") to the prefab id
    - Object properties (Tiled property list) override prefab default properties

    Coordinates:
    - Tiled object positions are in pixels; we keep them as floats and do not convert.
    - The y coordinate from Tiled refers to the bottom of the object by default; consumers
      should interpret accordingly.
    """

    def __init__(self, loader: Optional[DataLoader] = None) -> None:
        self.loader = loader or DataLoader()

    def load_prefab_defs(self, path: str | Path) -> Dict[str, PrefabDef]:
        data = self.loader.load(path, validate=True, schema="prefab")
        defs: Dict[str, PrefabDef] = {}
        for p in data["prefabs"]:
            defs[p["id"]] = PrefabDef(
                id=p["id"], name=p["name"], properties=p.get("properties", {}) or {}, tags=p.get("tags", []) or []
            )
        return defs

    def load_map(self, path: str | Path) -> Dict[str, Any]:
        p = Path(path)
        with p.open("rb") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or data.get("type") != "map":
            raise ValueError("Provided JSON is not a Tiled 'map' document")
        return data

    def extract_instances(self, tiled_map: Dict[str, Any], prefab_defs: Dict[str, PrefabDef]) -> List[PrefabInstance]:
        layers = tiled_map.get("layers", []) or []
        instances: List[PrefabInstance] = []

        for layer in layers:
            if layer.get("type") != "objectgroup":
                continue
            lname = layer.get("name")
            for obj in layer.get("objects", []) or []:
                prefab_id = obj.get("type") or obj.get("class")
                if not prefab_id:
                    continue  # ignore non-prefab objects
                if prefab_id not in prefab_defs:
                    logger.warning("Unknown prefab id '%s' at object id %s; skipping", prefab_id, obj.get("id"))
                    continue
                props = self._tiled_properties_to_dict(obj.get("properties"))
                inst = PrefabInstance(
                    id=prefab_id,
                    x=float(obj.get("x", 0.0)),
                    y=float(obj.get("y", 0.0)),
                    rotation=float(obj.get("rotation", 0.0) or 0.0),
                    properties=props,
                    source_name=lname,
                )
                inst = inst.with_defaults(prefab_defs[prefab_id].properties)
                instances.append(inst)
        return instances

    def run_cli_extract(self, map_path: str | Path, prefab_defs_path: str | Path) -> List[Dict[str, Any]]:
        defs = self.load_prefab_defs(prefab_defs_path)
        tmap = self.load_map(map_path)
        inst = self.extract_instances(tmap, defs)
        return [asdict(i) for i in inst]

    @staticmethod
    def _tiled_properties_to_dict(props: Optional[Iterable[Dict[str, Any]]]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not props:
            return out
        for p in props:
            name = p.get("name")
            if name is None:
                continue
            out[name] = p.get("value")
        return out
