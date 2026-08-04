# NexusChat Architecture

## 1. System overview

NexusChat is a single FastAPI service serving both JSON APIs and a static single-page interface. SQLite is used for application state, retrieval, and the isolated synthetic reporting dataset. The deployment deliberately avoids a separate JavaScript build pipeline.

The service has five principal boundaries:

1. **Web client** — authentication, workspace selection, conversation rendering, admin controls, and responsive mobile navigation.
2. **Application API** — validation, authorization, rate limiting, agent routing, and atomic persistence.
3. **Primary SQLite database** — accounts, sessions, conversations, messages, settings, audit events, and RAG documents.
4. **Synthetic SQLite database** — deterministic fictional business data available only to the Data agent.
5. **Infrastructure data plane** — a persisted sanitized snapshot and an admin-only bounded LIVE collector.

## 2. Request flow

### General Nexus assistant

1. The API verifies the server-side session and conversation owner.
2. It confirms that the conversation belongs to the `general` workspace.
3. If RAG is enabled, an FTS5 query selects a bounded number of relevant chunks.
4. The system instructions, optional knowledge context, and recent messages are sent to the model provider.
5. The user and assistant messages are committed in one SQLite transaction.

### RAG ingestion

Administrators can select or drag up to 50 files per batch. The browser validates a
10 MiB per-file limit and a 50 MiB batch limit, then uploads up to four documents in
parallel. Each document is independently validated and committed, so one rejected
file does not roll back successful files from the same selection. The application
does not impose a global document-count ceiling.

### Infra assistant

Infra uses the same isolated `infra` conversation history with one of two data sources:

- **Snapshot** reads one sanitized JSON file generated approximately every minute by a hardened systemd one-shot service.
- **LIVE** invokes `collect_infra_state()` at request time. The function takes no user-provided command and executes only fixed read-only checks.

LIVE access is enforced server-side: the Infra agent must be enabled, LIVE must be enabled, and the authenticated user must have the `admin` role. Each successful collection writes an `infra.live.read` audit event. Source mode and collection time are saved with the assistant message.

### Data report agent

1. A direct `SELECT`/`WITH` statement is accepted, or the model generates one from the question and exposed synthetic schema.
2. The SQL validator rejects multiple statements and all DDL, DML, PRAGMA, attach, and transaction operations.
3. SQLite is opened with `mode=ro` and `query_only=ON`.
4. An authorizer denies mutation opcodes and unsafe functions.
5. A progress handler enforces execution time; row, column, and cell limits bound output.
6. The model transforms the bounded query result into a management report.

The reporting connection never points at the Nexus application database.

## 3. Conversation isolation

`conversations.agent_mode` is authoritative and can be `general`, `infra`, or `data`. List endpoints filter by mode, and the message endpoint rejects any mismatch between the requested agent and the conversation workspace.

Older databases are migrated automatically. If one legacy conversation contains messages from multiple agents, initialization retains one mode on the original record and moves the other modes into new conversations without deleting messages.

## 4. Persistence model

| Table | Responsibility |
| --- | --- |
| `users` | Account identity, bcrypt hash, role, activation state |
| `sessions` | SHA-256 hashes of opaque session tokens and expiry |
| `conversations` | Owner, workspace mode, title, timestamps |
| `messages` | Role, content, model, usage, structured source metadata |
| `settings` | Model routing, prompts, RAG and agent policy flags |
| `audit_log` | Administrative changes and LIVE Infra reads |
| `rag_documents` / `rag_chunks` | Knowledge-base metadata and chunks |
| `rag_chunks_fts` | SQLite FTS5 search index |

## 5. Model provider abstraction

`OpenAIProvider` offers a narrow application-facing interface:

- `reply()` for ordinary and Infra responses
- `generate_sql()` for schema-constrained SQL planning
- `create_sql_report()` for result summarization

With no `OPENAI_BASE_URL`, it uses the OpenAI Responses API with `store=False`. With a base URL, it uses OpenAI-compatible Chat Completions.

## 6. Frontend state model

The browser maintains separate conversation lists and active conversation objects for all three agents. Switching workspaces changes history, active chat, empty-state prompts, labels, and composer behavior. Infra additionally maintains a `snapshot` or `live` source selector.

The client renders model output through a deliberately small rich-text renderer supporting headings, paragraphs, lists, quotes, fenced code, and Markdown-style tables. It does not inject model HTML.

## 7. Failure behavior

- Model failures do not leave orphaned user messages.
- Missing or malformed snapshots return a service-unavailable response.
- LIVE collection errors are logged server-side and returned as a sanitized error.
- Data query rejections do not persist a partial exchange.
- Session, conversation-owner, agent-mode, and admin checks occur before privileged behavior.

