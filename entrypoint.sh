#!/bin/bash
# RunPod entrypoint: setup SSH from PUBLIC_KEY env var, then execute CMD

if [ -n "$PUBLIC_KEY" ]; then
    mkdir -p /root/.ssh
    echo "$PUBLIC_KEY" > /root/.ssh/authorized_keys
    chmod 700 /root/.ssh
    chmod 600 /root/.ssh/authorized_keys
fi

# Start SSH daemon
/usr/sbin/sshd

# Run the container command (or keep alive)
if [ $# -gt 0 ]; then
    exec "$@"
else
    # Default: keep container alive for SSH/exec
    tail -f /dev/null
fi
