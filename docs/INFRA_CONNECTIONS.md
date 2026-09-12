# Multiple infrastructure servers

Nexus administrators can save up to 20 named Linux SSH, Windows SSH or Windows
WinRM HTTPS connections in A4 and
select one for each Infra chat. The local Nexus host is always available as
`Local Nexus server`. A chat stores an immutable server ID: changing the selector
starts a new chat, while old messages remain attached to their original server.
Snapshot/LIVE is selected independently. Nexus never combines measurements from
different servers in one request.

External servers and their chat histories are administrator-only, even if the
local snapshot Infra agent is made available to ordinary users. Unknown or
deleted IDs fail closed and never fall back to the local host. A profile cannot
be deleted or pointed at a new host, port or SSH user while a chat references it.

## Restricted Linux SSH setup

This integration does not grant the model a shell. Nexus invokes only the fixed
command `/usr/local/bin/nexus-infra-readonly snapshot|live`; its bounded JSON is
validated and passed to the model. Install `deploy/nexus-infra-readonly` on each
managed Linux server and give a dedicated unprivileged account only the read
permissions required by the collector. The collector itself uses a fixed set of
checks for CPU/load, RAM, root disk, listening TCP ports, TLS, health endpoints
and approved systemd services. It cannot accept arbitrary commands.

Put the Nexus-side private key in `NEXUS_INFRA_SSH_KEY_ROOT`. In the GUI enter
only its filename; paths, traversal and symlinks are rejected. Store host keys in
`NEXUS_INFRA_KNOWN_HOSTS`. Nexus forces `BatchMode`, `IdentitiesOnly`,
`StrictHostKeyChecking`, one connection attempt and short timeouts.
Install an OpenSSH client on a native deployment; the reference container image
already includes it.

Restrict the public key on each target in `authorized_keys`:

```text
restrict,command="/usr/local/bin/nexus-infra-readonly" ssh-ed25519 AAAA... nexus-observer
```

The forced entrypoint validates `SSH_ORIGINAL_COMMAND` against exactly the two
allowed invocations. Do not reuse an administrator/root key, enable password
authentication, add sudo, permit forwarding, or give this account an interactive
shell. Apply firewall rules so only the Nexus host can reach SSH. Enrol the host
key through an authenticated operational process; never use `ssh-keyscan` output
without independently checking its fingerprint.

## Persistence and operations

Profiles are stored atomically with mode `0600` in
`NEXUS_INFRA_CONNECTION_PATH` (default `infra-connections.json` beside the Nexus
SQLite database). The file contains endpoints and identity filenames, not private
key material. Every profile has an optimistic revision to prevent concurrent
admin overwrites. The release helper backs up this file and `infra-known-hosts`;
private keys require a separate encrypted secret-management and recovery plan.

`snapshot` reads the target's `/opt/nexuschat/data/infra-snapshot.json`, normally
refreshed by the provided systemd timer. `live` collects a new sanitized view for
the request. A save operation performs a LIVE connectivity test before committing
the profile. Test every target from the Nexus service account, then verify both
modes in the GUI. Monitor SSH failures and `infra.connection.*`/`infra.live.read`
audit events without logging key contents or remote stderr.

These reference paths assume the same Nexus layout on managed Linux servers.

## Windows collector

Install `deploy/nexus-infra-readonly.ps1` as
`C:\ProgramData\NexusChat\nexus-infra-readonly.ps1`, restrict the directory and
script ACL to administrators plus the dedicated observer account, and sign the
script with a trusted code-signing certificate. Nexus always invokes PowerShell
with `-NoProfile`, `-NonInteractive` and `-ExecutionPolicy AllSigned`; neither the
administrator's question nor model output is placed in the command line.

The collector accepts only `snapshot` or `live`. LIVE returns sanitized OS,
uptime, CPU, memory, fixed-disk, listening-port, selected-service, recent System
event-count and reboot-pending data. Snapshot reads only
`C:\ProgramData\NexusChat\infra-snapshot.json`. Give the observer account only
the CIM, service, network and Event Log read permissions needed by those checks.

For Windows SSH, install and configure Microsoft OpenSSH Server, enrol the host
key in `NEXUS_INFRA_KNOWN_HOSTS`, and use a dedicated key from
`NEXUS_INFRA_SSH_KEY_ROOT`. Restrict that key/account to the signed collector;
do not grant an administrative interactive shell.

For WinRM, Nexus always constructs an `https://HOST:PORT/wsman` endpoint (port
5986 by default), validates the certificate and hostname, and supports NTLM or
Basic authentication over that verified TLS channel. Put a private CA PEM file
in `NEXUS_INFRA_CA_ROOT` when the
certificate is not issued by the system trust store. The password is stored in a
separate mode-`0600` file under `NEXUS_INFRA_WINRM_SECRET_ROOT`; it is omitted
from `infra-connections.json`, API responses, audit records and logs. Back this
secret directory up through the organization's encrypted secrets process.

Windows remote profiles remain admin-only and read-only, just like Linux remote
profiles. Kubernetes APIs, cloud control planes and arbitrary SSH, PowerShell or
WinRM commands remain outside this adapter.
