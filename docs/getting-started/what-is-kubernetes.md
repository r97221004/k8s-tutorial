# What is Kubernetes?

> Declare the state you want; let the cluster make reality match — and keep it that way.

[🏠 Home](../../README.md) · [Architecture Overview →](architecture.md)

---

Kubernetes (often shortened to **k8s** — "k", eight letters, "s") is an open-source system for running containers across a pool of machines. You hand it a **desired state** — _"run three copies of this web app, reachable on port 80"_ — written as YAML, and Kubernetes makes reality match it and keeps it that way: if a container crashes it restarts it, if a machine dies it reschedules the work elsewhere, if you ask for more copies it spreads them out for you.

The mental shift from `docker run` is **declarative vs. imperative**:

- **Imperative** (Docker): you issue commands that each change the system — _"start this container"_, _"now restart it"_, _"now run another"_. You own every step.
- **Declarative** (Kubernetes): you describe the end state in a file and let the cluster's **control loops** continuously reconcile toward it. You own the goal; the cluster owns the steps.

That single idea — _declare the goal, let controllers converge on it_ — is the thread running through every object in this guide.

---

[🏠 Home](../../README.md) · [Architecture Overview →](architecture.md)
