#!/usr/bin/env bash
set -euo pipefail

log() { printf '[entrypoint] %s\n' "$*" | tee -a /var/log/entrypoint.log; }

export PATH="/opt/conda/envs/facefusion/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

# ── Environment ──
mkdir -p /etc/profile.d
cat > /etc/profile.d/facefusion.sh <<'EOF'
export PATH=/opt/conda/envs/facefusion/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
EOF
chmod 644 /etc/profile.d/facefusion.sh

touch /root/.bashrc
if ! grep -q 'facefusion/bin' /root/.bashrc; then
    printf '\n# FaceFusion runtime path\nsource /etc/profile.d/facefusion.sh\n' >> /root/.bashrc
fi

[ -x /opt/conda/envs/facefusion/bin/python ] && [ ! -e /usr/local/bin/python ] && ln -sf /opt/conda/envs/facefusion/bin/python /usr/local/bin/python || true
[ -x /opt/conda/envs/facefusion/bin/pip ] && [ ! -e /usr/local/bin/pip ] && ln -sf /opt/conda/envs/facefusion/bin/pip /usr/local/bin/pip || true

# ── SSH Keys ──
mkdir -p /root/.ssh /run/sshd /var/run/sshd /var/log
chmod 700 /root/.ssh
: > /root/.ssh/authorized_keys

append_key() {
    local value="${1:-}"
    [ -n "$value" ] && printf '%b\n' "$value" | tr -d '\r' >> /root/.ssh/authorized_keys
}
append_key "${PUBLIC_KEY:-}"
append_key "${SSH_PUBLIC_KEY:-}"
append_key "${RUNPOD_PUBLIC_KEY:-}"

sort -u /root/.ssh/authorized_keys -o /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
log "SSH keys configured ($(wc -l < /root/.ssh/authorized_keys) entries)"

# ── SSHD Config ──
ssh-keygen -A 2>/dev/null || true

# Global sshd config
{
    echo "Port 22"
    echo "PermitRootLogin yes"
    echo "PubkeyAuthentication yes"
    echo "AuthorizedKeysFile .ssh/authorized_keys"
    echo "PasswordAuthentication no"
    echo "UsePAM no"
    echo "X11Forwarding no"
    echo "AllowTcpForwarding yes"
    echo "GatewayPorts yes"
    # Keep connections alive - critical for stability
    echo "ClientAliveInterval 30"
    echo "ClientAliveCountMax 3"
    echo "TCPKeepAlive yes"
    # Accept more concurrent connections
    echo "MaxStartups 10:30:100"
    echo "MaxSessions 100"
} > /etc/ssh/sshd_config.d/99-runpod.conf

# ── Start SSHD with retry ──
log "Starting SSH..."
SSHD_STARTED=false
for i in $(seq 1 5); do
    # Kill any existing sshd first
    pkill sshd 2>/dev/null || true
    sleep 1

    if command -v service >/dev/null 2>&1; then
        service ssh start 2>/dev/null || service ssh restart 2>/dev/null || true
    else
        /usr/sbin/sshd -e -D &
        sleep 1
    fi

    sleep 2
    if pgrep -x sshd >/dev/null 2>&1; then
        log "sshd started (attempt $i)"
        SSHD_STARTED=true
        break
    fi
    log "sshd start failed (attempt $i), retrying..."
    sleep 3
done

if [ "$SSHD_STARTED" = false ]; then
    log "FATAL: sshd failed to start after 5 attempts"
    # Last resort: try direct sshd
    /usr/sbin/sshd -e
    sleep 2
    pgrep -x sshd >/dev/null 2>&1 || { log "CRITICAL: cannot start sshd"; exit 1; }
fi

# ── Verify environment ──
log "Entrypoint ready"
[ -x "$(command -v python)" ] && log "python: $(python --version 2>&1)" || true
[ -x "$(command -v nvidia-smi)" ] && log "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'pending')" || true
log "Disk: $(df -h / | tail -1 | awk '{print $4 " free of " $2}')"

# Kill the background sshd from direct start attempt (service-managed sshd is fine)
# and keep container alive
exec tail -f /dev/null
