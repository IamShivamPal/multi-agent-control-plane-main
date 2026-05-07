import glob
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

from control_plane.app_override_manager import AppOverrideManager
from core_hooks.signal_builder import build_base_signal
import pathlib
from executer.runner import execute
from sarathi.headers import SARATHI_HEADER, SARATHI_VALUE

class MultiAppControlPlane:
    """Aggregates registry, health overview, and decision history across apps."""

    def __init__(self, env: str = "dev"):
        self.env = env
        self.registry_dir = "apps/registry"
        self.history_file = os.path.join("logs", "control_plane", "decision_history.jsonl")
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        self.override_manager = AppOverrideManager()

    def list_apps(self) -> List[Dict[str, Any]]:
        apps = []
        for file_path in glob.glob(os.path.join(self.registry_dir, "*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    spec = json.load(handle)
                app_name = spec.get("name") or os.path.splitext(os.path.basename(file_path))[0]
                apps.append({
                    "app_name": app_name,
                    "runtime": spec.get("type"),
                    "source_type": spec.get("source_type"),
                    "health_endpoint": spec.get("health_endpoint"),
                    "spec_file": file_path.replace("\\", "/")
                })
            except Exception:
                continue
        apps.sort(key=lambda x: x["app_name"])
        return apps

    def append_decision_history(self, record: Dict[str, Any]) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **record
        }
        with open(self.history_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

        # Build and emit a standardized sarathi signal when trace_id is available
        try:
            # Prefer an explicit `event` object if present (useful where action is finalized).
            event = payload.get('event') or payload

            # Use trace_id from the explicit event when available (strict)
            trace_id = event.get('trace_id')
            app_name = payload.get('app_name')
            action = payload.get('executed_action') or payload.get('decision_action') or payload.get('action')

            if trace_id and app_name and action:
                # Build signal using the event's trace id (ensures propagation)
                signal = build_base_signal(trace_id=event["trace_id"], service_id=app_name, action=action)

                # Prefer direct execution via executer with sarathi caller headers
                headers = {SARATHI_HEADER: SARATHI_VALUE}
                try:
                    execution_result = execute(signal, headers)
                except Exception:
                    # Fallback: persist emitted signals for now (sarathi emitter may pick these up)
                    signals_dir = pathlib.Path("logs/sarathi")
                    signals_dir.mkdir(parents=True, exist_ok=True)
                    signals_file = signals_dir / "signals.jsonl"
                    with open(signals_file, "a", encoding="utf-8") as sf:
                        sf.write(json.dumps(signal) + "\n")
        except Exception:
            # Never let signal emission break the control plane flow
            pass

    def _read_history(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.history_file):
            return []

        rows = []
        with open(self.history_file, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def get_decision_history(self, app_name: str, limit: int = 200) -> List[Dict[str, Any]]:
        rows = [row for row in self._read_history() if row.get("app_name") == app_name]
        rows.sort(key=lambda row: row.get("timestamp", ""), reverse=True)
        return rows[: max(1, min(limit, 1000))]

    def get_health_overview(self) -> List[Dict[str, Any]]:
        apps = self.list_apps()
        history_rows = self._read_history()

        latest_by_app: Dict[str, Dict[str, Any]] = {}
        for row in history_rows:
            app_name = row.get("app_name")
            if not app_name:
                continue
            old = latest_by_app.get(app_name)
            if old is None or row.get("timestamp", "") > old.get("timestamp", ""):
                latest_by_app[app_name] = row

        overview = []
        for app in apps:
            app_name = app["app_name"]
            last = latest_by_app.get(app_name)
            override = self.override_manager.get_app_override(app_name)
            overview.append({
                "app_name": app_name,
                "runtime": app.get("runtime"),
                "source_type": app.get("source_type"),
                "status": "healthy" if (last and last.get("execution_success") is True) else "unknown",
                "last_action": (last or {}).get("executed_action"),
                "last_reason": (last or {}).get("reason"),
                "last_seen": (last or {}).get("timestamp"),
                "manual_freeze": bool((override or {}).get("freeze_enabled", False)),
                "freeze_reason": (override or {}).get("reason")
            })

        overview.sort(key=lambda x: x["app_name"])
        return overview

    def set_manual_override(self, app_name: str, duration_minutes: int, reason: str) -> Dict[str, Any]:
        return self.override_manager.set_temporary_freeze(app_name, duration_minutes, reason)

    def clear_manual_override(self, app_name: str) -> Dict[str, Any]:
        return self.override_manager.clear_freeze(app_name)
