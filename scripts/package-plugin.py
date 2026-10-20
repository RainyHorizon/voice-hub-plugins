from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python scripts/package-plugin.py <plugin-id> <version>", file=sys.stderr)
        return 2
    plugin_id, version = sys.argv[1:]
    source = ROOT / "plugins" / plugin_id / "versions" / version
    if not source.is_dir() or not (source / "voice-hub.plugin.json").is_file():
        raise SystemExit(f"missing plugin version: {source}")
    manifest = json.loads((source / "voice-hub.plugin.json").read_text(encoding="utf-8"))
    if manifest.get("id") != plugin_id or manifest.get("version") != version:
        raise SystemExit("manifest id/version does not match package arguments")
    output_dir = ROOT / "dist"
    output_dir.mkdir(exist_ok=True)
    archive = output_dir / f"{plugin_id}-{version}.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                bundle.write(path, f"{plugin_id}/{path.relative_to(source).as_posix()}")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output_dir / f"{plugin_id}-{version}.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
