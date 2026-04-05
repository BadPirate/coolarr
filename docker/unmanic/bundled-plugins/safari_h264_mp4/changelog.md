# Changelog

## 1.0.3

- **Audio (iOS silent playback):** global `-ac 2` did not downmix; output stayed 6‑channel AAC. Use **`-ac:a:N 2`** for each output audio stream before `-c:a aac` so surround (e.g. eac3 5.1) becomes stereo AAC-LC @ 48 kHz.

## 1.0.2

- Audio: stereo downmix attempt, AAC-LC, 48 kHz; skip remux when source audio has >2 channels.

## 1.0.1

- Default x264 preset `medium` (was `slow`); added faster/superfast/ultrafast options; optional thread count; global `-threads` for decode.

## 1.0.0

- Initial release: H.264 (yuv420p) + AAC + MP4 with faststart; optional Raspberry Pi `h264_v4l2m2m` encoder; file-test gate; remove source when output path differs after success.
