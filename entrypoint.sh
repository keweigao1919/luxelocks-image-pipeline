#!/bin/bash
set -e
# RunPod compatible entrypoint

# Setup SSH from PUBLIC_KEY env var
if [ -n "$PUBLIC_KEY" ]; then
    mkdir -p /root/.ssh
    echo "$PUBLIC_KEY" > /root/.ssh/authorized_keys
    chmod 700 /root/.ssh
    chmod 600 /root/.ssh/authorized_keys
    echo "SSH key configured"
fi

# Start SSH daemon in foreground
echo "Starting SSH..."
exec /usr/sbin/sshd -D -e &
SSHD_PID=$!
echo "sshd started (PID=$SSHD_PID)"

# Keep container alive
if [ $# -gt 0 ]; then
    exec "$@"
else
    # Default: wait for sshd
    wait $SSHD_PID
fi
