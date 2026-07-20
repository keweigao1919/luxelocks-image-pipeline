#!/bin/bash
set -e

# RunPod entrypoint: setup SSH from RunPod key env vars, then keep container alive.
# RunPod templates may expose either PUBLIC_KEY or SSH_PUBLIC_KEY depending on
# connection mode/template path, so support both.

mkdir -p /root/.ssh
touch /root/.ssh/authorized_keys

if [ -n "${PUBLIC_KEY:-}" ]; then
    echo "$PUBLIC_KEY" >> /root/.ssh/authorized_keys
fi

if [ -n "${SSH_PUBLIC_KEY:-}" ]; then
    echo "$SSH_PUBLIC_KEY" >> /root/.ssh/authorized_keys
fi

if [ -s /root/.ssh/authorized_keys ]; then
    mkdir -p /root/.ssh
    chmod 700 /root/.ssh
    chmod 600 /root/.ssh/authorized_keys
    echo "SSH authorized_keys configured"
else
    echo "WARNING: no PUBLIC_KEY or SSH_PUBLIC_KEY provided"
fi

# Ensure host keys exist even when the base image did not generate them.
ssh-keygen -A

# Start SSH daemon in background so an optional command can still run.
/usr/sbin/sshd -D -e &
echo "sshd started"

# Keep container running
if [ $# -gt 0 ]; then
    exec "$@"
else
    tail -f /dev/null
fi
