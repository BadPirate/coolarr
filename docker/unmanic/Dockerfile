# Extends official Unmanic with a pre-packaged plugin: safari_h264_mp4 (see bundled-plugins/).
# Build context must be the repository root (see docker-compose.yaml build.context).
FROM josh5/unmanic:latest

USER root

COPY docker/unmanic/bundled-plugins/ /opt/unmanic-bundled-plugins/
COPY docker/unmanic/register_bundled_plugin.py /opt/unmanic-bundled-plugins/register_bundled_plugin.py
COPY docker/unmanic/cont-init.d/ /etc/cont-init.d/

RUN chmod 755 /etc/cont-init.d/*.sh 2>/dev/null || true
