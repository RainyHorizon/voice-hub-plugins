from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    registry = json.loads((ROOT / "registry.json").read_text(encoding="utf-8"))
    if registry.get("schema_version") != 1 or not isinstance(registry.get("plugins"), list):
        raise SystemExit("registry.json must use schema_version 1 and a plugins array")
    ids: set[str] = set()
    for item in registry["plugins"]:
        plugin_id, version = item.get("id", ""), item.get("version", "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,39}", plugin_id) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise SystemExit("invalid plugin id or semantic version")
        if plugin_id in ids:
            raise SystemExit(f"duplicate plugin id: {plugin_id}")
        ids.add(plugin_id)
        if not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")):
            raise SystemExit(f"invalid sha256 for {plugin_id}")
        source = ROOT / "plugins" / plugin_id / "versions" / version
        manifest = json.loads((source / "voice-hub.plugin.json").read_text(encoding="utf-8"))
        if manifest.get("id") != plugin_id or manifest.get("version") != version:
            raise SystemExit(f"manifest mismatch for {plugin_id}@{version}")
        if len(list(source.rglob("voice-hub.plugin.json"))) != 1:
            raise SystemExit(f"expected exactly one manifest for {plugin_id}@{version}")

    if "--package" in sys.argv:
        index = sys.argv.index("--package")
        plugin_id, version = sys.argv[index + 1:index + 3]
        item = next((entry for entry in registry["plugins"] if entry["id"] == plugin_id and entry["version"] == version), None)
        if item is None:
            raise SystemExit("release package is not listed in registry.json")
        subprocess.run([sys.executable, str(ROOT / "scripts/package-plugin.py"), plugin_id, version], check=True)
        archive = ROOT / "dist" / f"{plugin_id}-{version}.zip"
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise SystemExit("generated package SHA-256 does not match registry.json")
    print(f"validated {len(registry['plugins'])} plugin(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
