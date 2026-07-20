#!/bin/bash
# RunPod entrypoint: setup SSH from PUBLIC_KEY, then keep container alive

if [ -n "$PUBLIC_KEY" ]; then
    mkdir -p /root/.ssh
    echo "$PUBLIC_KEY" > /root/.ssh/authorized_keys
    chmod 700 /root/.ssh
    chmod 600 /root/.ssh/authorized_keys
    echo "SSH key configured"
fi

# Start SSH daemon (background, NOT with exec)
/usr/sbin/sshd -D -e &
echo "sshd started"

# Keep container running
if [ $# -gt 0 ]; then
    exec "$@"
else
    tail -f /dev/null
fi
