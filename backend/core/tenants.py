from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional, List
import json, logging

logger = logging.getLogger("tenants")
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
TENANTS_FILE = DATA_DIR / "tenants.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TENANTS = {
    "default": {
        "name": "THE13TH (Demo)",
        "slug": "default",
        "theme": {"primary": "#6D28D9", "accent": "#9F7AEA", "bg": "#0f172a"},
        "logo": "",
        "demo": True
    },
    "realestate": {
        "name": "Propwise Realty",
        "slug": "realestate",
        "theme": {"primary": "#2E86AB", "accent": "#7FB3D5", "bg": "#071422"},
        "logo": "",
        "demo": True
    }
}

class TenantManager:
    def __init__(self, path: Path = TENANTS_FILE):
        self.path = path
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            logger.info("Tenants file not found — creating default tenants")
            self._data = DEFAULT_TENANTS.copy()
            self._save()
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8") or "{}")
            self._data = raw if isinstance(raw, dict) else DEFAULT_TENANTS.copy()
        except Exception as e:
            logger.exception("Failed to load tenants file: %s", e)
            self._data = DEFAULT_TENANTS.copy()
            self._save()

    def _save(self):
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def list_tenants(self) -> List[str]:
        return list(self._data.keys())

    def get(self, slug: str) -> Optional[Dict[str, Any]]:
        return self._data.get(slug)

    def add_or_update(self, slug: str, config: Dict[str, Any]):
        self._data[slug] = config
        self._save()

_manager = TenantManager()

def get_tenant_manager() -> TenantManager:
    return _manager
