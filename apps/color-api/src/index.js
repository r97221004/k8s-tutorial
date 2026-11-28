const os = require('node:os');
const express = require('express');

const app = express();
const port = Number(process.env.PORT) || 8080;
const color = process.env.COLOR || 'blue';

// Switches that make the app misbehave on purpose, for the health-probe chapters.
const delayStartup = process.env.DELAY_STARTUP === 'true';
const failLiveness = process.env.FAIL_LIVENESS === 'true';
// A coin flip when the container starts: with FAIL_READINESS, about half never become ready.
const failReadiness = process.env.FAIL_READINESS === 'true' ? Math.random() < 0.5 : false;

console.log(
  `Delay startup: ${delayStartup}, fail liveness: ${failLiveness}, fail readiness: ${failReadiness}`
);

app.get('/', (req, res) => {
  res.send(
    `<h1 style="color:${color};">Hello from color-api!</h1>` +
      `<p>Served by <code>${os.hostname()}</code></p>`
  );
});

// JSON by default; ?format=text for one plain line, handy for scripts and logs.
app.get('/api', (req, res) => {
  if (req.query.format === 'text') {
    return res.type('text/plain').send(`COLOR: ${color}, HOSTNAME: ${os.hostname()}\n`);
  }
  res.json({ color, hostname: os.hostname() });
});

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

// As PID 1, Node ignores stop signals it doesn't handle.
// SIGTERM: Kubernetes and `docker stop`. SIGINT: Ctrl+C.
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, () => {
    console.log(`${signal} received, shutting down`);
    if (!server) {
      process.exit(0); // still in the startup delay: nothing to close
    }
    server.close(() => process.exit(0));
  });
}
