import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional


class AppOverrideManager:
    """Manages temporary per-app manual overrides such as freeze mode."""

    def __init__(self, store_file: str = "logs/control_plane/app_overrides.json"):
        self.store_file = store_file
        os.makedirs(os.path.dirname(self.store_file), exist_ok=True)
        if not os.path.exists(self.store_file):
            self._write_store({"apps": {}})

    def _read_store(self) -> Dict[str, Any]:
        try:
            with open(self.store_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict) and "apps" in data and isinstance(data["apps"], dict):
                    return data
        except Exception:
            pass
        return {"apps": {}}

    def _write_store(self, data: Dict[str, Any]) -> None:
        with open(self.store_file, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def set_temporary_freeze(self, app_name: str, duration_minutes: int, reason: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        until = now + timedelta(minutes=max(1, int(duration_minutes)))

        store = self._read_store()
        store["apps"][app_name] = {
            "freeze_enabled": True,
            "reason": reason.strip() or "manual_override",
            "set_at": now.isoformat(),
            "freeze_until": until.isoformat()
        }
        self._write_store(store)

        return {
            "app_name": app_name,
            "freeze_enabled": True,
            "reason": store["apps"][app_name]["reason"],
            "freeze_until": store["apps"][app_name]["freeze_until"]
        }

    def clear_freeze(self, app_name: str) -> Dict[str, Any]:
        store = self._read_store()
        if app_name in store["apps"]:
            store["apps"][app_name]["freeze_enabled"] = False
            store["apps"][app_name]["freeze_until"] = datetime.now(timezone.utc).isoformat()
            store["apps"][app_name]["reason"] = "manual_unfreeze"
            self._write_store(store)
        return {
            "app_name": app_name,
            "freeze_enabled": False
        }

    def get_app_override(self, app_name: str) -> Optional[Dict[str, Any]]:
        store = self._read_store()
        entry = store["apps"].get(app_name)
        if not entry:
            return None

        freeze_until_raw = entry.get("freeze_until")
        try:
            freeze_until = datetime.fromisoformat(freeze_until_raw)
        except Exception:
            freeze_until = datetime.now(timezone.utc)

        now = datetime.now(timezone.utc)
        is_active = bool(entry.get("freeze_enabled")) and freeze_until > now

        return {
            "app_name": app_name,
            "freeze_enabled": is_active,
            "reason": entry.get("reason", "manual_override"),
            "set_at": entry.get("set_at"),
            "freeze_until": freeze_until.isoformat()
        }

    def get_all_overrides(self) -> Dict[str, Any]:
        store = self._read_store()
        result = {}
        for app_name in store["apps"]:
            override = self.get_app_override(app_name)
            if override:
                result[app_name] = override
        return result
