# Object Management

> Three ways to create and change objects: imperative commands, imperative files, and declarative files.

---

In Part 3 you created every Pod with `kubectl run`, and changed one with `kubectl set image`. That's one way to manage Kubernetes objects. There are three, and two questions tell them apart:

1. **Where does the truth about your objects live:** only in the cluster, or also in files you keep? This separates commands from the two file-based approaches.
2. **Who decides what to do with a file:** you (`create` it, `replace` it), or kubectl (`apply` works it out)? This separates the two file-based approaches from each other, and decides what happens to changes made outside your files.

This chapter is the map. The rest of Part 4 tries each approach hands-on.

> **Not the same "declarative" as in [What is Kubernetes?](../getting-started/what-is-kubernetes.md#imperative-vs-declarative).** There, declarative described the **cluster**: every object states a desired state, and controllers keep reconciling toward it. That's true no matter how the object was created, even with `kubectl run`. Here, imperative vs. declarative describes **you**: how you tell the API server what to create and change.

## The three approaches at a glance

| | **Imperative commands** | **Imperative object configuration** | **Declarative object configuration** |
|---|---|---|---|
| **You say** | "Do this, now." | "Do this, with this file." | "Make it look like this file." |
| **Main commands** | `kubectl run`, `create <type>`, `expose`, `scale`, `set`, `label`, `delete <type> <name>` | `kubectl create -f`, `replace -f`, `delete -f` | `kubectl apply -f`, `diff -f`, `delete -f` |
| **Source of truth** | Only the cluster | Your files | Your files, merged with the live objects |
| **Who picks the operation** | You | You | kubectl |
| **Best for** | Experiments, debugging, one-offs | Learning why `apply` exists; small setups where nothing else touches the objects | Anything you keep, especially in Git |

The read-only commands (`get`, `describe`, `logs`) work the same way under all three. Only how you **change** things differs.

## 1. Imperative commands

You name an operation and its arguments on the command line. No file involved.

```bash
kubectl run color-api --image=<YOUR_DOCKERHUB_USER>/color-api:1.0.0
kubectl label pod color-api team=web
kubectl delete pod color-api
```

**Why it's good:**

- **Easiest to learn.** One command per action, and the verb says what happens: `create`, `scale`, `delete`.
- **One step.** No file to write first; the change happens immediately.

**Where it falls short:**

- **Nothing to reuse.** To create the same object again, or a similar one, you have to remember and retype the command.
- **No review, no history.** Nobody can review a change before it happens, and nothing records who changed what afterwards.
- **The cluster is the only record.** You can see what exists *now*, but not how it got that way, or what was deleted.

## 2. Imperative object configuration

You write the object as a YAML file, then tell kubectl exactly which operation to perform with it.

```bash
kubectl create -f color-config.yaml     # create it; fails if it already exists
kubectl replace -f color-config.yaml    # overwrite the live object with the file; fails if it doesn't exist
kubectl delete -f color-config.yaml     # delete what the file describes
```

**Why it's good:**

- **Files can go in Git.** Changes can be reviewed in a pull request, and the history is an audit trail.
- **Files are templates.** Copy one and edit it to create a similar object.
- **Simpler than declarative.** Each command does exactly one thing, with no merging to reason about.

**Where it falls short:**

- **You have to pick the operation.** `create` fails if the object exists, `replace` fails if it doesn't (for most kinds; [Imperative Commands with Files](imperative-object-configuration.md) covers the exception). That works for one file, but not for a directory of objects where some exist and some don't.
- **You have to know the schema.** Writing the YAML means knowing each object's fields (the next chapters help with that).
- **`replace` throws away changes made elsewhere.** It overwrites the **whole** object with your file, so anything changed outside the file is lost. See the example below.
- **`replace` needs the complete object.** The cluster fills in fields your file doesn't have. On a Pod, those include the node it was scheduled to, so `kubectl replace` on a Pod is rejected as an attempt to change its (immutable) spec.

## 3. Declarative object configuration

You describe the state you want in files, and `kubectl apply` works out what to do: create what's missing, and update what differs.

```bash
kubectl diff -f color-api.yaml       # preview what would change
kubectl apply -f color-api.yaml      # create or update, whichever is needed
kubectl apply -f manifests/          # works on a whole directory, too
kubectl delete -f color-api.yaml
```

**Why it's good:**

- **It figures out the operation.** You never decide between create and update: `apply` creates the object the first time, updates it after that, and handles a whole directory in one go.
- **It keeps changes made elsewhere.** `apply` only touches the fields your file manages. A label someone added with `kubectl label`, or a replica count set by an autoscaler, survives your next `apply`, as long as your file has never set that field itself.

**Where it falls short:**

- **Hardest to learn.** To predict the result, you need to understand how `apply` merges your file with the live object.
- **Partial updates can surprise you.** Deleting a line from the file isn't the same as "stop managing this field". For example, delete `replicas: 3` from a [Deployment](../core-objects/deployment.md)'s file because an autoscaler should own it now, and the next `apply` *removes* the field, so the Deployment falls back to the default of 1 replica. [Declarative Object Management](declarative-management.md) explains the merge rules behind this.
- **The file isn't the whole picture.** Because changes made elsewhere are kept, the live object can hold things your file doesn't mention. `kubectl diff` shows you the gap.

## The difference that matters: changes made elsewhere

Imperative object configuration and declarative object configuration both use files. The difference shows up when someone changes the live object **outside** the file. Say `color-config.yaml` describes a [ConfigMap](../config-and-data/configmap.md), a small object that holds settings, here `COLOR: blue`. After you create it, a teammate runs:

```bash
kubectl label configmap color-config team=web
```

Now you change `COLOR` to `red` in your file and push it to the cluster:

| You run | `COLOR` | The `team=web` label | Why |
|---|---|---|---|
| `kubectl replace -f color-config.yaml` | `red` | **Gone** | `replace` swaps in your file as the entire object. The label isn't in the file, so it isn't in the object anymore. |
| `kubectl apply -f color-config.yaml` | `red` | **Kept** | `apply` remembers which fields came from your file, and only updates those. The label was never one of them, so it's left alone. |

Neither is "wrong". `replace` gives you exactly what's in the file; `apply` lets the file and other tools share an object. You'll reproduce both behaviors in [Imperative Commands with Files](imperative-object-configuration.md) and [Declarative Object Management](declarative-management.md).

## Which one should you use?

| Situation | Use |
|---|---|
| Trying something out, debugging, a throwaway Pod | **Imperative commands** |
| Getting a first draft of a YAML file | **Imperative commands** with `--dry-run=client -o yaml` (see [Generating Manifests](generating-manifests.md)) |
| Anything you want to keep, share, or recreate | **Declarative**, with the files in Git |

Imperative object configuration is worth understanding, mostly to see why `apply` exists. In practice, teams pick declarative for everything they keep, and use imperative commands for quick experiments around it.

> ⚠️ **Pick one approach per object.** Mixing them on the same object gets confusing fast: for example, running `kubectl create -f` and then `kubectl apply -f` on the same file prints a warning, and changes you made imperatively may be overwritten by the next `apply`. If you started with commands and want to switch, [From Imperative to Declarative](imperative-to-declarative.md) shows how.

## What's in this part

| Chapter | Approach |
|---|---|
| [Manifest Files](manifest-files.md) | The YAML both file-based approaches use |
| [Imperative Commands](imperative-commands.md) | 1 |
| [Generating Manifests](generating-manifests.md) | 1 → files: let kubectl write the YAML |
| [Imperative Commands with Files](imperative-object-configuration.md) | 2 |
| [Declarative Object Management](declarative-management.md) | 3 |
| [From Imperative to Declarative](imperative-to-declarative.md) | 1 → 3 |
| [Multiple Objects in One File](multiple-objects-per-file.md) | Files for a whole app |

---

[← From Dockerfile to Pod](../pods/from-dockerfile-to-pod.md) · [↑ Contents](../../README.md) · [Manifest Files →](manifest-files.md)
