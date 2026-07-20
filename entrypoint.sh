#!/usr/bin/env bash
set -euo pipefail

# RunPod-compatible Pod entrypoint.
# From a non-RunPod base image we must reproduce the SSH setup inherited by
# runpod/base: key injection, host keys, sshd startup, then keep the container up.

log() {
    printf '[entrypoint] %s\n' "$*"
}

export PATH="/opt/conda/envs/facefusion/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

mkdir -p /etc/profile.d
cat > /etc/profile.d/facefusion.sh <<'EOF'
export PATH=/opt/conda/envs/facefusion/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
EOF
chmod 644 /etc/profile.d/facefusion.sh

touch /root/.bashrc
if ! grep -q 'facefusion/bin' /root/.bashrc; then
    printf '\n# FaceFusion runtime path\nsource /etc/profile.d/facefusion.sh\n' >> /root/.bashrc
fi

if [ -x /opt/conda/envs/facefusion/bin/python ] && [ ! -e /usr/local/bin/python ]; then
    ln -s /opt/conda/envs/facefusion/bin/python /usr/local/bin/python
fi

if [ -x /opt/conda/envs/facefusion/bin/pip ] && [ ! -e /usr/local/bin/pip ]; then
    ln -s /opt/conda/envs/facefusion/bin/pip /usr/local/bin/pip
fi

append_key_var() {
    local value="${1:-}"
    if [ -n "$value" ]; then
        # Support both real newlines and escaped "\n" sequences, and strip CRLF.
        printf '%b\n' "$value" | tr -d '\r' >> /root/.ssh/authorized_keys
    fi
}

mkdir -p /root/.ssh /run/sshd /var/run/sshd
chmod 700 /root/.ssh
: > /root/.ssh/authorized_keys

append_key_var "${PUBLIC_KEY:-}"
append_key_var "${SSH_PUBLIC_KEY:-}"
append_key_var "${RUNPOD_PUBLIC_KEY:-}"

if [ -s /root/.ssh/authorized_keys ]; then
    sort -u /root/.ssh/authorized_keys -o /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
    log "SSH authorized_keys configured"
else
    log "WARNING: no PUBLIC_KEY, SSH_PUBLIC_KEY, or RUNPOD_PUBLIC_KEY provided"
fi

ssh-keygen -A

mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-runpod.conf <<'EOF'
Port 22
PermitRootLogin yes
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
UsePAM no
X11Forwarding no
AllowTcpForwarding yes
GatewayPorts yes
EOF

# Run sshd as a daemon. If startup fails, fail the container early.
/usr/sbin/sshd -e
log "sshd started"

if command -v python >/dev/null 2>&1; then
    log "python=$(python --version 2>&1)"
fi

if command -v nvidia-smi >/dev/null 2>&1; then
    log "nvidia-smi available"
fi

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

tail -f /dev/null
