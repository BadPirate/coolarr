#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Re-encode to H.264 / AAC / MP4 for Safari, iOS, and WebOS-friendly playback.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Any, Dict, List

from unmanic.libs.unplugins.settings import PluginSettings

logger = logging.getLogger("Unmanic.Plugin.safari_h264_mp4")

TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+\.?\d*)")

VIDEO_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".m4v",
    ".avi",
    ".wmv",
    ".mpg",
    ".mpeg",
    ".ts",
    ".m2ts",
    ".mts",
    ".webm",
    ".mov",
    ".flv",
    ".ogv",
    ".divx",
}


class Settings(PluginSettings):
    settings = {
        "video_encoder": "libx264",
        # medium is a good default: much faster than slow/veryslow with modest size/quality cost
        "preset": "medium",
        "crf": "22",
        "audio_bitrate_k": "192",
        "strip_subtitles": True,
        # 0 = ffmpeg/libx264 use all logical CPUs (helps decode of heavy sources + encode)
        "thread_count": "0",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_settings = {
            "video_encoder": {
                "label": "Video encoder (libx264 for quality/compat; h264_v4l2m2m on Pi with /dev/video* passed through)",
                "input_type": "select",
                "select_options": [
                    {"value": "libx264", "label": "libx264 (software, recommended)"},
                    {"value": "h264_v4l2m2m", "label": "h264_v4l2m2 (Raspberry Pi hardware)"},
                ],
            },
            "preset": {
                "label": "x264 preset: slower = better compression at same CRF, faster presets = higher speed, larger files or more artifacts (ignored for v4l2m2m)",
                "input_type": "select",
                "select_options": [
                    {"value": "veryslow", "label": "veryslow (smallest files, slowest)"},
                    {"value": "slower", "label": "slower"},
                    {"value": "slow", "label": "slow"},
                    {"value": "medium", "label": "medium (balanced)"},
                    {"value": "fast", "label": "fast"},
                    {"value": "faster", "label": "faster"},
                    {"value": "veryfast", "label": "veryfast"},
                    {"value": "superfast", "label": "superfast"},
                    {"value": "ultrafast", "label": "ultrafast (fastest, worst efficiency)"},
                ],
            },
            "crf": {
                "label": "CRF (18–28, lower is higher quality; v4l2m2m uses similar QP via -b:v)",
                "input_type": "text",
            },
            "audio_bitrate_k": {
                "label": "AAC audio bitrate (kb/s)",
                "input_type": "text",
            },
            "strip_subtitles": {
                "label": "Strip subtitle streams (best for broad device support)",
                "input_type": "checkbox",
            },
            "thread_count": {
                "label": "Thread count (0 = auto, use all CPUs for decode/encode)",
                "input_type": "text",
            },
        }


def _run_ffprobe(path: str) -> Optional[Dict[str, Any]]:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=120)
        return json.loads(out.decode("utf-8", errors="replace"))
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError) as e:
        logger.debug("ffprobe failed for %s: %s", path, e)
        return None


def _format_names_ok(name: str) -> bool:
    if not name:
        return False
    parts = {p.strip() for p in name.replace(",", " ").split() if p.strip()}
    return bool(parts & {"mp4", "mov", "isom", "iso6", "iso2", "avc1", "mp41", "mp42"})


def _streams_match_target(probe: Dict[str, Any]) -> bool:
    streams: List[Dict[str, Any]] = probe.get("streams") or []
    video = [s for s in streams if s.get("codec_type") == "video"]
    if not video:
        return False

    v0 = video[0]
    if (v0.get("codec_name") or "").lower() != "h264":
        return False
    pix = (v0.get("pix_fmt") or "").lower()
    if pix != "yuv420p":
        return False

    for s in streams:
        if s.get("codec_type") != "audio":
            continue
        if (s.get("codec_name") or "").lower() != "aac":
            return False

    return True


def _container_is_mp4_family(probe: Dict[str, Any]) -> bool:
    fmt = probe.get("format") or {}
    return _format_names_ok(fmt.get("format_name") or "")


def _is_fully_compatible(probe: Dict[str, Any]) -> bool:
    return _streams_match_target(probe) and _container_is_mp4_family(probe)


def _probe_duration(probe: Dict[str, Any]) -> float:
    fmt = probe.get("format") or {}
    try:
        return float(fmt.get("duration") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _make_progress_parser(duration_sec: float):
    def parse_line(line_text: str):
        result = {"killed": False, "paused": False, "percent": "0"}
        if duration_sec <= 0:
            return result
        m = TIME_RE.search(str(line_text))
        if not m:
            return result
        h, mn = int(m.group(1)), int(m.group(2))
        sec = float(m.group(3))
        cur = h * 3600 + mn * 60 + sec
        pct = min(99, int(100 * cur / duration_sec))
        result["percent"] = str(pct)
        return result

    return parse_line


def on_library_management_file_test(data):
    path = data.get("path") or ""
    ext = os.path.splitext(path)[1].lower()
    if ext not in VIDEO_EXTENSIONS:
        return data

    probe = _run_ffprobe(path)
    if not probe:
        return data

    streams = probe.get("streams") or []
    if not any(s.get("codec_type") == "video" for s in streams):
        return data

    if "shared_info" not in data or data["shared_info"] is None:
        data["shared_info"] = {}
    data["shared_info"]["safari_h264_mp4_probe"] = probe

    if _is_fully_compatible(probe):
        data["add_file_to_pending_tasks"] = False
        logger.debug("Skip (already compatible): %s", path)
    else:
        data["add_file_to_pending_tasks"] = True
        logger.debug("Queue for processing: %s", path)

    return data


def on_worker_process(data):
    data["exec_command"] = []
    data["repeat"] = False

    abspath = data.get("file_in")
    if not abspath:
        return data

    library_id = data.get("library_id")
    settings = Settings(library_id=library_id) if library_id else Settings()

    probe = None
    shared = data.get("shared_info") or {}
    if isinstance(shared, dict) and "safari_h264_mp4_probe" in shared:
        probe = shared["safari_h264_mp4_probe"]
    if probe is None:
        probe = _run_ffprobe(abspath)
    if not probe:
        logger.error("ffprobe failed in worker for %s", abspath)
        return data

    if _is_fully_compatible(probe):
        logger.info("Worker skipping (already fully compatible): %s", abspath)
        return data

    duration_sec = _probe_duration(probe)

    split_out = os.path.splitext(data.get("file_out") or "")
    file_out = "{}{}".format(split_out[0], ".mp4")
    data["file_out"] = file_out

    encoder = settings.get_setting("video_encoder") or "libx264"
    preset = settings.get_setting("preset") or "medium"
    try:
        crf = int(str(settings.get_setting("crf") or "22"))
    except ValueError:
        crf = 22
    crf = max(18, min(28, crf))
    try:
        abit = int(str(settings.get_setting("audio_bitrate_k") or "192"))
    except ValueError:
        abit = 192
    strip_subs = bool(settings.get_setting("strip_subtitles"))
    try:
        threads = int(str(settings.get_setting("thread_count") or "0"))
    except ValueError:
        threads = 0
    if threads < 0:
        threads = 0

    remux_only = _streams_match_target(probe) and not _container_is_mp4_family(probe)

    cmd: List[str] = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-stats",
        "-threads",
        str(threads),
        "-y",
        "-i",
        abspath,
    ]

    if remux_only:
        # Stream copy into MP4; subtitles omitted (PGS / bitmap subs break MP4 copy)
        cmd.extend(["-map", "0:v:0", "-map", "0:a?", "-sn", "-map_chapters", "0", "-map_metadata", "0", "-c", "copy", "-movflags", "+faststart", "-f", "mp4", file_out])
        data["exec_command"] = cmd
        data["command_progress_parser"] = _make_progress_parser(duration_sec)
        return data

    cmd.extend(["-map", "0:v:0"])
    if strip_subs:
        cmd.extend(["-map", "0:a?"])
        cmd.append("-sn")
    else:
        cmd.extend(["-map", "0:a?"])
        cmd.extend(["-map", "0:s?"])
        cmd.extend(["-c:s", "mov_text"])

    cmd.extend(["-map_chapters", "0", "-map_metadata", "0"])

    if encoder == "h264_v4l2m2m":
        cmd.extend(
            [
                "-c:v",
                "h264_v4l2m2m",
                "-pix_fmt",
                "yuv420p",
                "-b:v",
                "8M",
                "-maxrate",
                "10M",
                "-bufsize",
                "16M",
            ]
        )
    else:
        x264_args = [
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-level",
            "4.1",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            str(preset),
            "-crf",
            str(crf),
        ]
        if threads > 0:
            x264_args.extend(["-x264-params", "threads={}".format(threads)])
        cmd.extend(x264_args)

    cmd.extend(
        [
            "-c:a",
            "aac",
            "-b:a",
            "{}k".format(abit),
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            file_out,
        ]
    )

    data["exec_command"] = cmd
    data["command_progress_parser"] = _make_progress_parser(duration_sec)
    return data


def on_postprocessor_file_movement(data):
    """
    Remove the original file when the completed output lives at a different path
    (e.g. movie.mkv → movie.mp4). Same-path HEVC→H.264 replacement is handled by overwrite.
    """
    source = (data.get("source_data") or {}).get("abspath") or ""
    dest = data.get("file_out") or ""
    if source and dest and os.path.normpath(source) != os.path.normpath(dest):
        data["remove_source_file"] = True
    return data
