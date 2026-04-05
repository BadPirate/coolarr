#!/usr/bin/env python3
"""
Exercise the real safari_h264_mp4 plugin module (file-test + worker runners) and run the
resulting ffmpeg command — same data flow as Unmanic, without duplicating encode logic.

Run inside the Unmanic container (needs unmanic Python env + PluginSettings):

  docker compose exec unmanic /opt/venv/bin/python3 /path/to/run_plugin_encode_test.py \\
    --input /library/sample.mkv --output /library/sample_clip5s.mp4

Or copy this script into the container / mount it with the compose volume.

Exit code 0 on success, non-zero on failure or skip (no encode requested).
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile


def _load_plugin_module(plugin_dir: str):
    path = os.path.join(plugin_dir, "plugin.py")
    if not os.path.isfile(path):
        print("error: missing plugin at {}".format(path), file=sys.stderr)
        sys.exit(2)
    # Must match plugin id so PluginSettings.get_plugin_directory() works (uses sys.modules[Settings.__module__]).
    module_name = "safari_h264_mp4"
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    parser = argparse.ArgumentParser(description="Run safari_h264_mp4 plugin + ffmpeg (integration-style test)")
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Source video (e.g. short MKV clip)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="",
        help="Destination file (default: <input_dir>/sample_clip5s.mp4)",
    )
    parser.add_argument(
        "--plugin-dir",
        default="",
        help="Path to safari_h264_mp4 plugin folder (default: $HOME_DIR/.unmanic/plugins/safari_h264_mp4)",
    )
    parser.add_argument(
        "--library-id",
        type=int,
        default=1,
        help="library_id passed to plugin runners (default: 1)",
    )
    args = parser.parse_args()

    os.environ.setdefault("HOME_DIR", "/config")

    in_path = os.path.abspath(os.path.expanduser(args.input))
    if not os.path.isfile(in_path):
        print("error: input not found: {}".format(in_path), file=sys.stderr)
        return 2

    if args.output:
        out_path = os.path.abspath(os.path.expanduser(args.output))
    else:
        out_path = os.path.join(os.path.dirname(in_path), "sample_clip5s.mp4")

    plugin_dir = args.plugin_dir or os.path.join(
        os.environ.get("HOME_DIR", "/config"),
        ".unmanic",
        "plugins",
        "safari_h264_mp4",
    )

    plugin = _load_plugin_module(plugin_dir)

    # --- library file test (same keys as Unmanic)
    ft = {
        "library_id": args.library_id,
        "path": in_path,
        "issues": [],
        "add_file_to_pending_tasks": True,
        "priority_score": 0,
        "shared_info": {},
    }
    plugin.on_library_management_file_test(ft)
    print("file_test: add_file_to_pending_tasks={}".format(ft.get("add_file_to_pending_tasks")))
    if not ft.get("add_file_to_pending_tasks"):
        print("info: plugin would skip queue (already compatible). No ffmpeg run.")
        return 3

    shared = ft.get("shared_info") or {}

    # --- worker (match Unmanic worker template; file_out pattern similar to cache WORKING file)
    base, ext = os.path.splitext(in_path)
    tmp_root = tempfile.mkdtemp(prefix="safari_plugin_test_")
    try:
        working_out = os.path.join(tmp_root, "task-cache-WORKING-1-1{}".format(ext))
        wrk = {
            "task_id": 999001,
            "worker_log": [],
            "library_id": args.library_id,
            "exec_command": [],
            "current_command": [],
            "command_progress_parser": None,
            "file_in": in_path,
            "file_out": working_out,
            "original_file_path": in_path,
            "repeat": False,
            "shared_info": shared,
        }
        plugin.on_worker_process(wrk)

        cmd = wrk.get("exec_command")
        if not cmd:
            print("info: worker returned no exec_command (nothing to run).")
            return 4

        produced = wrk.get("file_out")
        if not produced:
            print("error: worker did not set file_out", file=sys.stderr)
            return 5

        print("ffmpeg:", subprocess.list2cmdline(cmd) if isinstance(cmd, list) else cmd)
        os.makedirs(os.path.dirname(produced) or ".", exist_ok=True)

        if isinstance(cmd, list):
            rc = subprocess.call(cmd)
        else:
            rc = subprocess.call(cmd, shell=True)
        if rc != 0:
            print("error: ffmpeg exited with {}".format(rc), file=sys.stderr)
            return rc

        if not os.path.isfile(produced):
            print("error: expected output missing: {}".format(produced), file=sys.stderr)
            return 6

        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        shutil.move(produced, out_path)
        print("ok: {}".format(out_path))
        return 0
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
