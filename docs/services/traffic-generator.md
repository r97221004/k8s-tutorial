# Traffic Generator

> Build a small app that calls color-api over and over, so you can see where requests land.

---

To watch a Service spread traffic across Pods, you need a client that keeps sending requests and shows **which Pod answered** each one. color-api already reports its Pod's name; this chapter builds the other half: a tiny **traffic generator** that calls a URL every few seconds and prints each response.

It's a shell script in an Alpine image, built and pushed exactly like color-api in [From Dockerfile to Pod](../pods/from-dockerfile-to-pod.md). Along the way, you'll fix two problems that are easy to miss in a script that runs as a container.

## Before you start

- **Docker Desktop**, running, and logged in to Docker Hub, as in [From Dockerfile to Pod](../pods/from-dockerfile-to-pod.md#before-you-start).
- **color-api `1.2.0`** on Docker Hub. Version `1.2.0` adds a plain-text format to `/api`, which the traffic generator uses:

  ```bash
  docker build -t <YOUR_DOCKERHUB_USER>/color-api:1.2.0 apps/color-api
  docker push <YOUR_DOCKERHUB_USER>/color-api:1.2.0
  ```

  | Request | Response |
  |---|---|
  | `/api` | `{"color":"blue","hostname":"…"}` (JSON, as before) |
  | `/api?format=text` | `COLOR: blue, HOSTNAME: …` (one plain line) |

## 1. The script

[`apps/traffic-generator/traffic-gen.sh`](../../apps/traffic-generator/traffic-gen.sh):

```sh
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
```

The loop itself is simple: request, print with a timestamp, sleep, repeat. The parts worth a closer look are there because the script will run as a container:

| Part | Why |
|---|---|
| The two arguments | The target URL and interval aren't baked in, so the same image can point at anything. In Kubernetes, you'll pass them as the container's `args`. |
| `trap … TERM INT` | Like color-api's [signal handlers](../pods/from-dockerfile-to-pod.md#1-the-app). Without it, the shell, as PID 1, ignores the stop signal, and every `kubectl delete` waits out the full 30-second grace period. |
| `sleep … &` then `wait` | A shell only runs a `trap` between commands. A plain `sleep 5` would delay the exit by up to 5 seconds; `wait` is interrupted by the signal at once. |
| `curl -m 2` | Without a timeout, one request to a target that never answers would freeze the loop for minutes. |
| The `else` branch | A failed request is printed too, so you can *see* an outage rather than a mysterious gap in the output. |

## 2. The Dockerfile

[`apps/traffic-generator/Dockerfile`](../../apps/traffic-generator/Dockerfile):

```dockerfile
FROM alpine:3.20
RUN apk add --no-cache curl
WORKDIR /app
COPY traffic-gen.sh .
RUN chmod +x traffic-gen.sh
USER nobody
ENTRYPOINT ["/app/traffic-gen.sh"]
```

| Line | What it does |
|---|---|
| `FROM alpine:3.20` | A tiny Linux base, about 8MB. It has a shell, but not `curl`. |
| `RUN apk add --no-cache curl` | Install `curl`. `--no-cache` keeps the package index out of the image. |
| `COPY` and `chmod +x` | Put the script in `/app`, and make it executable. |
| `USER nobody` | Run as Alpine's unprivileged `nobody` user, not root. |
| `ENTRYPOINT ["/app/traffic-gen.sh"]` | Run the script. Anything after the image name in `docker run`, or in `args` in Kubernetes, becomes its arguments. |

Use the **full path** in `ENTRYPOINT`. With just the file name, `ENTRYPOINT ["traffic-gen.sh"]`, Docker looks for the program in `$PATH`, which doesn't include `/app`, and the container can't even start:

```text
exec: "traffic-gen.sh": executable file not found in $PATH
```

`WORKDIR` sets the directory the program *runs in*; it doesn't help find the program.

## 3. Build and try it locally

```bash
docker build -t <YOUR_DOCKERHUB_USER>/traffic-generator:1.0.0 apps/traffic-generator
```

Run it without arguments first, to see the usage check:

```bash
docker run --rm <YOUR_DOCKERHUB_USER>/traffic-generator:1.0.0
```

```
Usage: /app/traffic-gen.sh <target-url> <interval-in-seconds>
```

Now point it at a real color-api. Put both containers on a Docker network, so the traffic generator can reach color-api by its container name:

```bash
docker network create tg-net
docker run -d --rm --name color-api --network tg-net <YOUR_DOCKERHUB_USER>/color-api:1.2.0
docker run --rm --name tg --network tg-net \
  <YOUR_DOCKERHUB_USER>/traffic-generator:1.0.0 "http://color-api:8080/api?format=text" 1
```

```text
Sending requests to http://color-api:8080/api?format=text every 1 seconds.
[2026-11-25 07:16:13] COLOR: blue, HOSTNAME: 442781fd93b2
[2026-11-25 07:16:14] COLOR: blue, HOSTNAME: 442781fd93b2
[2026-11-25 07:16:15] COLOR: blue, HOSTNAME: 442781fd93b2
```

One request a second, each answered by the same container (`442781fd93b2` is its ID). Quote the URL: unquoted, your shell would treat the `?` as a wildcard. The timestamps are in **UTC**, the container's time zone, so they may be hours off from your clock.

In a second terminal, stop color-api and watch the traffic generator report it:

```bash
docker stop color-api
```

```text
[2026-11-25 07:16:17] (no response from http://color-api:8080/api?format=text)
```

Then press Ctrl+C in the first terminal. The `trap` catches it:

```
Stopping.
```

**See what the `trap` saves you.** Run the same image with a plain `sleep` as PID 1, no `trap`, and stop it, giving it 10 seconds to exit:

```bash
docker run -d --name no-trap --entrypoint sh <YOUR_DOCKERHUB_USER>/traffic-generator:1.0.0 -c 'sleep 60'
time docker stop -t 10 no-trap
docker inspect -f '{{.State.ExitCode}}' no-trap
docker rm no-trap
```

```text
real    0m10.3s
137
```

The shell ignored the stop signal, so Docker waited the full 10 seconds and then killed it: exit code `137` means killed. Your traffic generator, with its `trap`, exited with `0` almost at once, even halfway through a `sleep`. In Kubernetes, the wait is 30 seconds: the difference between a Pod that's gone in a second and one that hangs around for half a minute.

Clean up the network:

```bash
docker network rm tg-net
```

## 4. Push it

```bash
docker push <YOUR_DOCKERHUB_USER>/traffic-generator:1.0.0
```

The image is about 20MB, almost all of it Alpine and `curl`.

## What you have now

Two images on Docker Hub:

| Image | Does |
|---|---|
| `color-api:1.2.0` | Answers requests, and says which Pod it is |
| `traffic-generator:1.0.0` | Sends requests to a URL every few seconds, and prints the answers |

Locally, the traffic generator found color-api by its **container name** on a Docker network. In Kubernetes, that job belongs to a Service. Next, in [Deploying Color API and Traffic Generator](deploying-color-api.md), you'll run both in the cluster.

## Best practices

- **Handle stop signals in every container's main process**, shell scripts included. `trap` for shell, a signal handler for apps.
- **Give network calls a timeout**, so one stuck request can't stall a loop.
- **Use absolute paths in `ENTRYPOINT`.** `WORKDIR` doesn't put a directory on `$PATH`.
- **Take settings as arguments or environment variables**, not hard-coded, so one image works in many places.

---

[← What Are Services](what-are-services.md) · [↑ Contents](../../README.md) · [Deploying Color API and Traffic Generator →](deploying-color-api.md)
