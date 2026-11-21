const os = require('node:os');
const express = require('express');

const app = express();
const port = Number(process.env.PORT) || 8080;
const color = process.env.COLOR || 'blue';

app.get('/', (req, res) => {
  res.send(
    `<h1 style="color:${color};">Hello from color-api!</h1>` +
      `<p>Served by <code>${os.hostname()}</code></p>`
  );
});

app.get('/api', (req, res) => {
  res.json({ color, hostname: os.hostname() });
});

const server = app.listen(port, () => {
  console.log(`color-api listening on port ${port} (color: ${color})`);
});

// As PID 1, Node ignores stop signals it doesn't handle.
// SIGTERM: Kubernetes and `docker stop`. SIGINT: Ctrl+C.
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, () => {
    console.log(`${signal} received, shutting down`);
    server.close(() => process.exit(0));
  });
}
