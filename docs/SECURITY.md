# Security Model

NexusChat is designed for a small private deployment. The controls below reduce risk, but operators must still provide host hardening, TLS, monitoring, backups, and timely dependency updates.

## Authentication and sessions

- Passwords are hashed with bcrypt; plaintext passwords are never stored.
- Administrator-created accounts use a unique username and require no user e-mail;
  legacy and self-registered accounts continue to accept their e-mail address.
- Browser-generated temporary passwords use `crypto.getRandomValues()` and include
  upper-case, lower-case, numeric, and symbol characters.
- Sessions use cryptographically random bearer tokens.
- Only a SHA-256 token hash is persisted in SQLite.
- Cookies are HTTP-only, `SameSite=Lax`, and `Secure` in the production configuration.
- Disabled users cannot create new authenticated sessions.
- Admin self-demotion and self-deactivation are rejected.

## HTTP protections

- Trusted-host validation restricts accepted host headers.
- State-changing cross-origin requests are rejected when the `Origin` header does not match the effective host.
- Security headers include CSP, frame denial, MIME sniffing prevention, restricted referrer policy, permissions policy, and cross-origin isolation headers.
- Authentication, registration, chat, and LIVE Infra paths are rate-limited in memory.
- API responses and the SPA shell use `Cache-Control: no-store` where sensitive state may be involved.

## Authorization and tenant boundaries

- Every conversation lookup includes the authenticated user ID.
- Conversation agent mode is stored server-side and must match every message request.
- Admin routes use a server-side role dependency; hiding controls in the UI is not treated as authorization.
- LIVE Infra requires the admin role regardless of the ordinary Infra policy.

## Infra boundary

The model has no SSH session and receives no general command-execution tool.

The snapshot service and LIVE collector expose a fixed sanitized structure containing load, uptime, memory, root-disk usage, selected service states, health checks, listening TCP port numbers, TLS expiry, and nginx validation availability.

LIVE collection:

- takes no command string from the user;
- invokes subprocesses without a shell;
- uses a fixed service list and fixed command arguments;
- truncates command output;
- applies per-command timeouts and a per-user rate limit;
- runs inside the unprivileged web-service account in the reference deployment;
- records successful reads in the audit log.

Do not add arbitrary shell execution, user-controlled subprocess arguments, unrestricted log access, or passwordless sudo to this boundary.

## SQL report boundary

The Data agent operates on a separate synthetic database. Defense in depth includes:

- deterministic fictional seed data;
- acceptance of only `SELECT` and `WITH` statements;
- one statement per request;
- a keyword denylist for mutations and administrative SQL;
- URI read-only mode and `PRAGMA query_only=ON`;
- a SQLite authorizer that denies mutation opcodes;
- an unsafe-function denylist;
- execution time, row, column, and cell-size limits.

Never point `NEXUS_SYNTHETIC_DATABASE` at the application database or a production business database without designing a separate authorization and governance layer.

## RAG boundary

- Uploads are restricted to text-oriented extensions.
- File names and content are validated server-side.
- Document size and RAG result counts are bounded.
- Retrieved text is treated as context, not trusted executable instructions.

## Secrets and repository hygiene

- Keep environment files outside the repository.
- Do not commit databases, session cookies, API keys, backup archives, production screenshots, or private SSH material.
- Rotate any credential that may have been exposed in logs or commits.
- Use a dedicated API key with appropriate provider-side limits.

## Reporting a vulnerability

For a public deployment, establish a private vulnerability-reporting channel before advertising the service. Avoid posting exploitable details in a public issue until a fix is available.
