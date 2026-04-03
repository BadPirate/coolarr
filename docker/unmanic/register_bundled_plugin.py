#!/opt/venv/bin/python3
"""
Register the bundled safari_h264_mp4 plugin in Unmanic's SQLite DB.
The Web UI only lists plugins that exist in the Plugins table, not only on disk.
"""
import json
import os
import sys
import time

# Ensure config matches the container (compose sets HOME_DIR=/config)
os.environ.setdefault("HOME_DIR", "/config")

from unmanic import config  # noqa: E402
from unmanic.libs.plugins import PluginsHandler  # noqa: E402
from unmanic.service import init_db  # noqa: E402


def main() -> int:
    plugin_id = sys.argv[1] if len(sys.argv) > 1 else "safari_h264_mp4"

    settings = config.Config()
    plugin_path = os.path.join(settings.get_plugins_path(), plugin_id)
    info_path = os.path.join(plugin_path, "info.json")

    if not os.path.isfile(info_path):
        print("register_bundled_plugin: skip (no {})".format(info_path), file=sys.stderr)
        return 0

    db = init_db(settings.get_config_path())
    try:
        with open(info_path, encoding="utf-8") as f:
            info = json.load(f)
        info["plugin_id"] = info.get("id")
        info.setdefault("icon", "")
        PluginsHandler.write_plugin_data_to_db(info, plugin_path)
        print("register_bundled_plugin: registered '{}' in Unmanic database".format(plugin_id))
    finally:
        db.stop()
        while not db.is_stopped():
            time.sleep(0.05)

    return 0


if __name__ == "__main__":
    sys.exit(main())
