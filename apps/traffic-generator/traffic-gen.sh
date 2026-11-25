#!/bin/sh
# Send a request to a URL every few seconds, and print each response.
# Usage: traffic-gen.sh <target-url> <interval-in-seconds>

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <target-url> <interval-in-seconds>"
  exit 1
fi

TARGET=$1
INTERVAL=$2

# As PID 1, the shell ignores stop signals it doesn't handle, so Kubernetes
# would wait out the whole grace period. Exit as soon as one arrives.
trap 'echo "Stopping."; exit 0' TERM INT

echo "Sending requests to $TARGET every $INTERVAL seconds."

while true; do
  REQUEST_TIME=$(date +"%Y-%m-%d %H:%M:%S")
  # -m 2: give up after 2 seconds, so one slow request can't stall the loop.
  if RESPONSE=$(curl -s -m 2 "$TARGET"); then
    echo "[$REQUEST_TIME] $RESPONSE"
  else
    echo "[$REQUEST_TIME] (no response from $TARGET)"
  fi
  # Sleep in the background and wait for it, so a stop signal is handled
  # right away instead of after the sleep finishes.
  sleep "$INTERVAL" &
  wait $!
done
