#!/bin/bash
# Custom confirmation script with environment variable expansion
# Usage: ./confirm.sh "message with ${VARIABLES}"

set -euo pipefail

# Expand environment variables in the message
message="$1"
expanded_message=$(eval "echo \"$message\"")

# Display the expanded message and prompt for confirmation
echo -n "$expanded_message (y/N): "
read -r response

case "$response" in
    [yY]|[yY][eE][sS])
        exit 0
        ;;
    *)
        exit 1
        ;;
esac