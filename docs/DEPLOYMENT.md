# Reference Deployment

This document describes the deployment model used by NexusChat without including production credentials or host-wide configuration.

## 1. Filesystem layout

```text
/opt/nexuschat/
  nexus/
  deploy/
  .venv/
  data/
/etc/nexuschat.env
```

Recommended ownership:

- application code: `root:root`, read-only to the service;
- data directory: `nexuschat:nexuschat`, mode `0750`;
- environment file: `root:root`, mode `0600`;
- SQLite databases and snapshots: not world-readable.

## 2. Service account

Create a non-login account and data directory:

```bash
sudo useradd --system --home /opt/nexuschat --shell /usr/sbin/nologin nexuschat
sudo install -d -o nexuschat -g nexuschat -m 0750 /opt/nexuschat/data
```

Install dependencies in `/opt/nexuschat/.venv`, copy `deploy/nexuschat.service` to `/etc/systemd/system/`, and review all paths before enabling it.

The reference unit uses:

- `User=nexuschat`
- `NoNewPrivileges=true`
- an empty capability bounding set
- `ProtectSystem=strict`
- `ProtectHome=true`
- a single writable data path

## 3. Environment

Copy `deploy/nexuschat.env.example` to `/etc/nexuschat.env`, replace placeholders, and apply mode `0600`.

The API key must never be stored in the repository or systemd unit itself.

## 4. Reverse proxy

`deploy/nginx.conf.example` demonstrates hosting the app below `/nexus/`. Merge it into your own HTTPS server block and add your production host to `TrustedHostMiddleware` in `nexus/app.py`, then run:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

The Uvicorn listener should remain bound to loopback unless another authenticated network layer is intentionally used.

The proxy template permits 12 MiB request bodies for the application's 10 MiB
per-file RAG limit. Keep both values aligned if the upload limit changes.

## 5. Infra snapshot timer

The snapshot generator executes as a hardened one-shot root service because some host checks may not be available to the web-service account. It writes only the sanitized JSON snapshot into the application data directory. The timer refreshes it approximately once per minute.

Review the fixed service list, endpoint list, domain used for TLS inspection, and output path before installation.

```bash
sudo install -m 0750 deploy/nexuschat-infra-snapshot.py \
  /usr/local/sbin/nexuschat-infra-snapshot
sudo cp deploy/nexuschat-infra-snapshot.service /etc/systemd/system/
sudo cp deploy/nexuschat-infra-snapshot.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nexuschat-infra-snapshot.timer
```

LIVE Infra does not call this privileged unit. It performs its smaller bounded collection inside the unprivileged web-service process.

## 6. Database migrations

Schema initialization is idempotent and runs at application startup. Back up the database before deploying new code:

```bash
sudo install -d -m 0750 /var/backups/nexuschat
sudo sqlite3 /opt/nexuschat/data/nexus.sqlite3 \
  ".backup '/var/backups/nexuschat/nexus-$(date -u +%Y%m%d-%H%M%S).sqlite3'"
```

Verify backups by opening a copy and running `PRAGMA integrity_check;`.

## 7. Release procedure

1. Run `pytest` and the Playwright smoke test.
2. Scan the release artifact for secrets and path traversal.
3. Back up code and SQLite.
4. Stop the web service.
5. Extract the new code with ownership and permissions preserved intentionally.
6. Refresh the snapshot helper and systemd units.
7. Start the snapshot and web services.
8. Poll `/health`, run `nginx -t`, and execute authenticated agent smoke tests.
9. Confirm database integrity, service status, and error-free logs.

Keep the previous code archive and database backup as the rollback pair.
