# Color API v1.3: Health Endpoints

> Give color-api a `/health` and a `/ready` endpoint for the probes to call, and three switches that make it fail on purpose.

---

[Health Probes](health-probes.md) said that an `httpGet` probe is only as good as the endpoint it calls. color-api has none made for probes yet: `/` and `/api` answer as long as the process is up. In this chapter you'll add two, `/health` for the liveness probe and `/ready` for the readiness probe.

A healthy app isn't much use for watching probes, though. Its probes just pass, and nothing happens. So version `1.3.0` also gets three **switches**, environment variables that each make it misbehave in one way: start slowly, answer everything except `/health`, or never be ready. The next three chapters turn one on each, and watch the matching probe react.

## Before you start

You need what [From Dockerfile to Pod](../pods/from-dockerfile-to-pod.md#before-you-start) needed: **Docker Desktop** running on your laptop, logged in to Docker Hub, and this repository. Everything in this chapter runs on your laptop, not the node.

## 1. Two endpoints

Both endpoints are in [`apps/color-api/src/index.js`](../../apps/color-api/src/index.js), next to `/` and `/api`:

```js
// For the readiness probe: can this container take traffic right now?
app.get('/ready', (req, res) => {
  if (failReadiness) {
    return res.sendStatus(503);
  }
  res.send('ok');
});

// For the liveness probe: is this container still working?
app.get('/health', (req, res) => {
  if (failLiveness) {
    return res.sendStatus(503);
  }
  res.send('ok');
});
```

Each answers `200` with `ok` when all is well, and `503 Service Unavailable` when it isn't. An `httpGet` probe passes on any status from 200 to 399, so the code is the whole answer. The body is just for people reading it with `curl`.

There are two endpoints, not one, because they answer the two different questions from [Health Probes](health-probes.md#1-three-probes-three-questions). In a real app, `/ready` is where you'd check what the app needs to serve, like its database connection, and `/health` would check only the app itself, so a database outage never restarts it. Here, a switch stands in for each of those checks.

## 2. Three switches

Near the top of the file, each switch is read from an environment variable:

```js
const delayStartup = process.env.DELAY_STARTUP === 'true';
const failLiveness = process.env.FAIL_LIVENESS === 'true';
// A coin flip when the container starts: with FAIL_READINESS, about half never become ready.
const failReadiness = process.env.FAIL_READINESS === 'true' ? Math.random() < 0.5 : false;
```

| Variable | What the app does | For |
|---|---|---|
| `DELAY_STARTUP=true` | Waits 60 seconds before it starts listening. Nothing answers until then | The startup probe |
| `FAIL_LIVENESS=true` | `/health` always answers `503`. Everything else works | The liveness probe |
| `FAIL_READINESS=true` | Flips a coin when the container starts. On heads, `/ready` always answers `503` | The readiness probe |

All three are off unless set to exactly `true`, so `1.3.0` with no variables behaves just like `1.2.0`, plus two endpoints that say `ok`.

The readiness coin flip is there so that one Deployment shows both cases. With several replicas, some Pods are ready and some never are, side by side, and you can watch the Service send traffic only to the ready ones.

The startup delay sits at the bottom, around `app.listen`:

```js
// With DELAY_STARTUP, wait a minute before listening, like an app loading a large cache.
const startupDelayMs = delayStartup ? 60_000 : 0;
if (delayStartup) {
  console.log('Starting in 60 seconds');
}

let server;
setTimeout(() => {
  server = app.listen(port, () => {
    console.log(`color-api listening on port ${port} (color: ${color})`);
  });
}, startupDelayMs);
```

For that minute, the process runs but nothing listens on port 8080, so every request fails, just like an app that's still loading. The stop-signal handler checks for this, so `docker stop` and Ctrl+C still work during the delay: with no server yet, it exits straight away.

The app also logs all three switches when it starts, so `docker logs` and `kubectl logs` tell you which way the coin landed.

## 3. Build it, and try each switch

On your laptop, from the repo root, build `1.3.0`. On an Apple Silicon Mac, add `--platform linux/amd64`, as in [From Dockerfile to Pod](../pods/from-dockerfile-to-pod.md#3-build-and-test-it-locally):

```bash
docker build -t <YOUR_DOCKERHUB_USER>/color-api:1.3.0 apps/color-api
```

You'll check each endpoint by its status code alone, which is all a probe looks at. This `curl` prints just the code:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/health
```

`-o /dev/null` throws the body away, and `-w '%{http_code}\n'` prints the status. If nothing answers at all, it prints `000`.

### No switches

```bash
docker run -d --rm --name capi -p 8080:8080 <YOUR_DOCKERHUB_USER>/color-api:1.3.0
sleep 2      # give the app a moment to start listening
docker logs capi
```

```text
9c3f5a1e2b7d...
Delay startup: false, fail liveness: false, fail readiness: false
color-api listening on port 8080 (color: blue)
```

The first line is the new container's ID, which `docker run -d` prints; yours will differ. Then the app's log: no switches on, and listening. Check all three paths:

```bash
for path in /health /ready /api; do
  echo "$path $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080$path)"
done
```

```text
/health 200
/ready 200
/api 200
```

All healthy. Stop it before the next one, since each run uses port 8080:

```bash
docker stop capi
```

### `FAIL_LIVENESS`: everything but `/health`

```bash
docker run -d --rm --name capi -p 8080:8080 -e FAIL_LIVENESS=true <YOUR_DOCKERHUB_USER>/color-api:1.3.0
sleep 2      # give the app a moment to start listening
for path in /health /ready /api; do
  echo "$path $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080$path)"
done
docker stop capi
```

```text
4b1e0c7f9a2d...
/health 503
/ready 200
/api 200
capi
```

Only `/health` fails. `/api` still answers, so from the outside the app looks fine, which is exactly the case a liveness probe exists for.

(The last line is `docker stop` naming the container it stopped. Without the `sleep`, the `curl`s can run before the app is listening, and print `000`.)

### `FAIL_READINESS`: a coin flip

Run it a few times, and look at the first log line and `/ready` each time:

```bash
for i in 1 2 3 4; do
  docker run -d --rm --name capi -p 8080:8080 -e FAIL_READINESS=true <YOUR_DOCKERHUB_USER>/color-api:1.3.0 > /dev/null
  sleep 2
  echo "$(docker logs capi | head -1) -> /ready $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/ready)"
  docker stop capi > /dev/null
done
```

```text
Delay startup: false, fail liveness: false, fail readiness: false -> /ready 200
Delay startup: false, fail liveness: false, fail readiness: true -> /ready 503
Delay startup: false, fail liveness: false, fail readiness: true -> /ready 503
Delay startup: false, fail liveness: false, fail readiness: false -> /ready 200
```

Yours will come out in a different order. Note that `fail readiness` in the log is the coin's result, not the variable: the variable was `true` every time, and the coin decided whether this container fails. Within one container, the answer never changes.

### `DELAY_STARTUP`: a slow start

```bash
docker run -d --rm --name capi -p 8080:8080 -e DELAY_STARTUP=true <YOUR_DOCKERHUB_USER>/color-api:1.3.0
sleep 2
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/health
docker logs capi
```

```text
7e2d9b4c1a6f...
000
Delay startup: true, fail liveness: false, fail readiness: false
Starting in 60 seconds
```

`000`: nothing answered. The container is running, but the app isn't listening yet. Wait a minute, and try again:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/health
docker logs capi
docker stop capi
```

```text
200
Delay startup: true, fail liveness: false, fail readiness: false
Starting in 60 seconds
color-api listening on port 8080 (color: blue)
capi
```

A liveness probe with the default settings would have given up on this container after about 30 seconds, and restarted it before it ever finished starting. That's the problem the startup probe solves.

## 4. Push it

```bash
docker push <YOUR_DOCKERHUB_USER>/color-api:1.3.0
```

The Pods in the next chapters pull `1.3.0` from Docker Hub, with one switch set in each Deployment's `env`.

## Clean up

Every container above ran with `--rm`, so stopping it removed it. Check nothing is left:

```bash
docker ps --filter name=capi
```

Keep the `1.3.0` image: the next three chapters use it.

## Best practices

- **Give liveness and readiness separate endpoints**, since they answer different questions.
- **Keep `/health` about the app itself.** Don't check databases or other services there; that belongs in `/ready`.
- **Make probe endpoints cheap.** The kubelet calls them every few seconds, for every container, for as long as it runs.
- **Answer with the status code.** A probe only reads the code, so a `200` with an error message in the body still passes.

---

[← Health Probes](health-probes.md) · [↑ Contents](../../README.md) · [Startup Probes →](startup-probes.md)
