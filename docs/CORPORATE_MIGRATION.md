# Corporate migration runbook

This release targets **one organization on one Linux host, one application worker,
and a local persistent SQLite volume**. Docker and systemd deployment templates are
provided. The container and VM must be behind an HTTPS reverse proxy. Do not use
NFS/SMB for SQLite files or run multiple replicas against the same volume.

## Deployment configuration

Start from `deploy/corporate.env.example`. Store the actual file outside version
control, mode `0600`, and distribute it with the organization's secret manager.

| Setting | Purpose |
| --- | --- |
| `NEXUS_ALLOWED_HOSTS` | Explicit comma-separated DNS names accepted by the API |
| `NEXUS_BASE_PATH` | Empty for `/`, or a prefix such as `/nexus`; proxy strips it |
| `NEXUS_SECURE_COOKIES=1` | HTTPS-only session cookie |
| `NEXUS_REGISTRATION_ENABLED=0` | Disable public self-registration in API and GUI |
| `NEXUS_SESSION_HOURS=8` | Absolute lifetime for new sessions; allowed range 1–168 |
| `NEXUS_MAX_CONCURRENT_CHATS=4` | Per-process cap; excess generations return 429 |
| `NEXUS_RAG_MAX_DOCUMENTS=1000` | Total knowledge-base document quota |
| `NEXUS_RAG_MAX_CHARACTERS=200000000` | Total source-character quota, not disk bytes |
| `NEXUS_LDAP_CA_FILE` | Optional trusted corporate CA PEM file, read-only |
| `NEXUS_TLS_HOST` / `NEXUS_TLS_ADDRESS` | Hostname and address checked by Infra TLS probe |
| `FORWARDED_ALLOW_IPS` | Actual proxy IP/CIDR trusted by Uvicorn; never `*` |

Existing deployments retain the previous defaults unless these variables are set.
Changing the session lifetime applies to new sessions; it does not shorten old ones.
Restore clears copied sessions. Deactivation or role changes revoke current sessions.
The frontend no longer fetches fonts from a third-party service.

## VM or Docker

For a VM, use `deploy/nexuschat.service`, an unprivileged `nexuschat` user, local
storage, and nginx. Copy the exact reviewed commit, install `requirements.txt` into
a new virtual environment, test that environment, and keep the previous environment
with the previous code. A code-only rollback cannot undo a dependency upgrade.

For updates to the reference `/opt/nexuschat` systemd installation, package a
reviewed commit with `git archive` (include `nexus`, `deploy`, `docs`,
`requirements.txt` and `README.md`) and run the matching `deploy/release.py` as root
with that archive during maintenance. It builds a separate virtual environment,
checks startup against temporary databases, stops the service, backs up the two
reference database paths and LDAP secret, and switches code and dependencies
together. Failed activation restores both previous runtime components. Recovery
material is retained in `.releases/<release-id>/`; restrict access to its `backup`
directory and apply your retention policy. Database restoration remains manual.
Adapt and rehearse this procedure before using non-reference paths or services.

For Docker, copy `deploy/corporate.env.example` to `.env`, fill the values, then run:

```sh
docker compose build
docker compose up -d
docker compose exec nexus python -m nexus.cli --database /opt/nexuschat/data/nexus.sqlite3 create-admin --name 'Operations Admin' --email 'admin@example.com'
```

The CLI prompts for the password; avoid putting it in shell history. The container
runs as UID/GID 10001, with a read-only root filesystem, dropped capabilities,
bounded resources, and only the data volume writable. Back up that volume's
databases using SQLite's backup API. Do not copy a live `.sqlite3` file without its
WAL state. For bind mounts, provision ownership for UID/GID 10001 before startup.

The proxy must forward the real Host and scheme and redirect the bare prefix to
its slash-terminated form (`/nexus` → `/nexus/`). Keep port 8300 restricted to the
proxy. Allow a 64 MiB HTTP body for RAG JSON; the raw upload batch remains 50 MiB.
Use a proxy read timeout suitable for the complete SQL planner/report path;
300 seconds is the reference. Validate the proxy trust chain with real HTTPS login.

Container Infra LIVE observes the **container**, not the physical host. To monitor
the host, generate the sanitized snapshot outside the container and mount that
single file read-only. Do not mount the Docker socket or enable privileged mode.
Set the snapshot unit's environment for the corporate hostname; independently
review the static service/health allowlist in `nexus/infra.py` for the new host.

For multiple managed hosts, enrol a dedicated restricted SSH observer as described
in [Multiple infrastructure servers](INFRA_CONNECTIONS.md). Transfer
`infra-connections.json` and verified `infra-known-hosts` through the approved
configuration channel; restore private keys from the secret manager, never from
the application repository or an unencrypted migration archive.

## LDAP / Active Directory

Keep a tested local administrator as a recovery account. In A6, enter the server,
Base DN and a least-privileged directory reader. Use LDAPS or StartTLS with valid
hostname/chain verification. Install the corporate CA instead of disabling TLS
verification. Referrals are disabled to prevent credential forwarding to another
directory. Search and bind operations have bounded timeouts.

Examples: OpenLDAP `(uid={username})`; AD
`(&(objectClass=user)(sAMAccountName={username}))`. Restrict access with the Base DN
or an organization-approved group filter. User input is escaped before substitution.
The test button checks the **draft** without changing saved settings or secrets.
Save explicitly after testing. New directory accounts receive the user role only.
An existing local identity or a directory identity with a different DN cannot be
silently reassigned. Directory renames require an explicit identity migration.

The bind secret is stored outside SQLite in a mode-0600 file, atomically replaced,
never returned by the API. Include it separately in encrypted backups/secret-manager
recovery. A directory account disabled in AD can retain an already issued Nexus
session until expiry; deactivate it in Nexus for immediate session revocation.
OIDC/SAML SSO, MFA, SCIM and periodic group synchronization are not implemented.

## Data transfer and recovery rehearsal

1. Record the source Git SHA, Python/dependency versions, configuration, counts,
   service account and permission settings. Reserve a maintenance window.
2. Stop application writes for the final cutover. Keep the source host intact.
3. Create and verify backups for both databases with the matching source code:

   ```sh
   python -m nexus.backup backup /opt/nexuschat/data/nexus.sqlite3 /secure-backup/nexus.sqlite3
   python -m nexus.backup backup /opt/nexuschat/data/synthetic-business.sqlite3 /secure-backup/synthetic.sqlite3
   ```

4. Transfer backups through the approved encrypted channel. Transfer the LDAP bind
   secret and configuration separately. Record SHA-256 checksums on both hosts.
5. Restore to **new, absent paths** on the target:

   ```sh
   python -m nexus.backup restore /secure-backup/nexus.sqlite3 /opt/nexuschat/data/nexus.sqlite3
   python -m nexus.backup restore /secure-backup/synthetic.sqlite3 /opt/nexuschat/data/synthetic-business.sqlite3
   ```

   Restore checks SQLite integrity and foreign keys and invalidates copied sessions.
   It refuses to overwrite any existing destination. A failed copy remains for
   diagnosis. Fix ownership and permissions before starting the unprivileged service.
6. Start the target; startup migrations are additive and forward-only. Verify
   `/health`, `/ready`, local and LDAP login, roles, three isolated histories,
   RAG sources and document counts, blocked SQL, and an approved report prompt.
7. Test from the corporate network and mobile browser through the actual proxy.
   Only then switch DNS/traffic. Retain the old host for the agreed rollback window.

Rollback means the matching previous code **and virtual environment**, with the
verified database backup if a schema change cannot be read by the old code. Keep
the service stopped while restoring. A rollback after new writes requires an
explicit data reconciliation decision; do not silently discard those writes.

## Operations and remaining acceptance criteria

External Data sources are now configured separately in A5. Follow
[External reporting databases](DATABASE_CONNECTIONS.md) before activation. Include
the protected `database-connection.json` in encrypted backups, transfer database
CA trust, install any required vendor driver, and test the target database's
SELECT-only account and network rules. SQLite external files require their own
approved read-only mount and backup plan.

`/health` is liveness; `/ready` checks primary DB access without provider calls.
Every response passing the application security middleware has `X-Request-ID`.
Chat timing logs separate RAG from provider latency. Administrators can retrieve
audit events via `/api/admin/audit?limit=100&before_id=...` for controlled collection.
Audit data is not immutable; ship it to the organization's logging system if
tamper-resistant retention is required. Backups contain sensitive user content.

Configure alerts for health/readiness failure, disk/inode pressure, backup failure,
stale infra snapshots, sustained 429/5xx and elevated provider latency. Set RPO/RTO,
retention and an owner, then perform a timed recovery rehearsal on target storage.
The test suite uses synthetic data/fake providers and cannot establish the target
network's capacity or the real directory's correctness.

RAG is **shared across authorized users of this installation**. Do not ingest
documents requiring per-department permissions; separate deployments or document
ACL retrieval are required. Chat content, RAG passages, infra snapshots and SQL
results may leave the host for the configured model provider. Obtain approval for
that provider, retention, region and egress policy before using company data.

High availability/multiple workers requires shared rate/admission limits and a
server database/search design. There is no PostgreSQL migration adapter, tenant
isolation, DLP engine or corporate SSO in this release. These are explicit scope
limits, not features inferred from the presence of LDAP or Docker.
