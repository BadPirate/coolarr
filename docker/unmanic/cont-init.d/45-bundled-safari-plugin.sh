# Sourced by Unmanic entrypoint (see /usr/bin entrypoint.sh)
# Unmanic's plugin list is backed by SQLite (Plugins table), not only the on-disk plugin folder.
if [[ -d /opt/unmanic-bundled-plugins/safari_h264_mp4 ]]; then
    log "Bundled plugin: safari_h264_mp4"
    PLUG_ROOT="${HOME_DIR:-/config}/.unmanic/plugins"
    mkdir -p "${PLUG_ROOT}"
    if [[ ! -d "${PLUG_ROOT}/safari_h264_mp4" ]]; then
        cp -a /opt/unmanic-bundled-plugins/safari_h264_mp4 "${PLUG_ROOT}/"
        chown -R "${PUID:-1000}:${PGID:-1000}" "${PLUG_ROOT}/safari_h264_mp4" 2>/dev/null || true
        log "Installed safari_h264_mp4 to ${PLUG_ROOT}"
    else
        log "Plugin safari_h264_mp4 already in ${PLUG_ROOT}; remove that folder to re-seed from the image"
    fi

    if [[ -f "${PLUG_ROOT}/safari_h264_mp4/info.json" ]] && [[ -f /opt/unmanic-bundled-plugins/register_bundled_plugin.py ]]; then
        log "Registering safari_h264_mp4 in Unmanic database (required for Web UI)"
        if /opt/venv/bin/python3 /opt/unmanic-bundled-plugins/register_bundled_plugin.py safari_h264_mp4; then
            :
        else
            log "WARNING: register_bundled_plugin.py failed; plugin files are on disk but may not appear in the UI until registered"
        fi
    fi
fi
