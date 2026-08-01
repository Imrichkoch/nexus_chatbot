from __future__ import annotations

import os
import re
import sqlite3
import time
import logging
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from nexus.ai import AIUnavailable, OpenAIProvider
from nexus.data_agent import DataReportAgent, QueryRejected, SyntheticDatabase
from nexus.infra import (
    InfraSnapshotError,
    collect_infra_state,
    infra_prompt,
    read_snapshot,
)
from nexus.models import OpenRouterModelCatalog
from nexus.rag import validate_document
from nexus.store import Store


COOKIE_NAME = "nexus_session"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STATIC_DIR = Path(__file__).resolve().parent / "static"
LOGGER = logging.getLogger("nexuschat")


class RegisterPayload(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=1, max_length=128)


class LoginPayload(BaseModel):
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=1, max_length=128)


class ConversationPayload(BaseModel):
    agent_mode: Literal["general", "infra", "data"] = "general"
    title: str = Field(default="Nová konverzácia", min_length=1, max_length=120)


class MessagePayload(BaseModel):
    content: str = Field(min_length=1, max_length=12000)
    agent_mode: Literal["general", "infra", "data"] = "general"
    infra_source: Literal["snapshot", "live"] = "snapshot"


class UserUpdatePayload(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class SettingsPayload(BaseModel):
    model: str = Field(min_length=3, max_length=80)
    system_prompt: str = Field(min_length=20, max_length=4000)
    rag_enabled: bool = False
    rag_max_chunks: int = Field(default=4, ge=1, le=12)
    infra_agent_enabled: bool = False
    infra_agent_admin_only: bool = True
    infra_live_enabled: bool = True
    infra_model: str = Field(default="gpt-5.6-luna", min_length=3, max_length=80)
    data_agent_enabled: bool = True
    data_agent_admin_only: bool = False
    data_model: str = Field(default="gpt-5.6-luna", min_length=3, max_length=80)


class RagDocumentPayload(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1)


class SlidingWindowLimiter:
    def __init__(self):
        self.events: dict[str, deque[float]] = defaultdict(deque)
        self.lock = Lock()
        self.last_cleanup = 0.0

    def check(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self.lock:
            if now - self.last_cleanup >= 60:
                for event_key, events in list(self.events.items()):
                    while events and events[0] <= now - 3600:
                        events.popleft()
                    if not events:
                        self.events.pop(event_key, None)
                self.last_cleanup = now
            if key not in self.events and len(self.events) >= 50_000:
                return False
            bucket = self.events[key]
            while bucket and bucket[0] <= now - window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


def valid_password(password: str) -> bool:
    return (
        len(password) >= 10
        and any(character.islower() for character in password)
        and any(character.isupper() for character in password)
        and any(character.isdigit() for character in password)
    )


def create_app(
    *,
    database_path: str | None = None,
    ai_provider: Any | None = None,
    model_catalog: Any | None = None,
    infra_snapshot_path: str | None = None,
    live_infra_collector: Any | None = None,
    synthetic_database_path: str | None = None,
    secure_cookies: bool | None = None,
) -> FastAPI:
    app = FastAPI(
        title="NexusChat",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "raizenko.cloud",
            "www.raizenko.cloud",
            "127.0.0.1",
            "localhost",
            "testserver",
        ],
    )
    app.state.store = Store(
        database_path
        or os.getenv("NEXUS_DATABASE", "/opt/nexuschat/data/nexus.sqlite3")
    )
    app.state.ai_provider = ai_provider or OpenAIProvider()
    app.state.model_catalog = model_catalog or OpenRouterModelCatalog()
    app.state.infra_snapshot_path = infra_snapshot_path or os.getenv(
        "NEXUS_INFRA_SNAPSHOT", "/opt/nexuschat/data/infra-snapshot.json"
    )
    app.state.live_infra_collector = live_infra_collector or collect_infra_state
    app.state.synthetic_database = SyntheticDatabase(
        synthetic_database_path
        or os.getenv(
            "NEXUS_SYNTHETIC_DATABASE",
            "/opt/nexuschat/data/synthetic-business.sqlite3",
        )
    )
    app.state.data_agent = DataReportAgent(
        app.state.synthetic_database, app.state.ai_provider
    )
    app.state.secure_cookies = (
        secure_cookies
        if secure_cookies is not None
        else os.getenv("NEXUS_SECURE_COOKIES", "1") == "1"
    )
    app.state.limiter = SlidingWindowLimiter()

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin:
                expected = f"{request.url.scheme}://{request.headers.get('host')}"
                forwarded = request.headers.get("x-forwarded-proto")
                if forwarded:
                    expected = f"{forwarded}://{request.headers.get('host')}"
                if origin.rstrip("/") != expected.rstrip("/"):
                    return JSONResponse(
                        {"detail": "Neplatný pôvod požiadavky."},
                        status_code=403,
                    )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'self'"
        )
        if request.url.path == "/" or request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def current_user(
        nexus_session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    ) -> dict[str, Any]:
        user = app.state.store.user_for_session(nexus_session)
        if not user:
            raise HTTPException(status_code=401, detail="Vyžaduje sa prihlásenie.")
        return user

    def admin_user(
        user: dict[str, Any] = Depends(current_user),
    ) -> dict[str, Any]:
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Prístup len pre administrátora.")
        return user

    def set_session_cookie(response: Response, token: str) -> None:
        cookie_path = "/nexus" if app.state.secure_cookies else "/"
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=7 * 24 * 60 * 60,
            httponly=True,
            secure=app.state.secure_cookies,
            samesite="lax",
            path=cookie_path,
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "nexuschat"}

    @app.post("/api/auth/register", status_code=201)
    def register(payload: RegisterPayload, request: Request, response: Response):
        client_ip = request.client.host if request.client else "unknown"
        if not app.state.limiter.check(f"register:{client_ip}", 6, 60 * 60):
            raise HTTPException(
                status_code=429,
                detail="Príliš veľa registrácií. Skús to neskôr.",
            )
        name = payload.name.strip()
        if len(name) < 2:
            raise HTTPException(
                status_code=422,
                detail="Meno musí mať aspoň 2 znaky.",
            )
        email = payload.email.strip().lower()
        if not EMAIL_PATTERN.match(email):
            raise HTTPException(status_code=422, detail="Neplatná e-mailová adresa.")
        if not valid_password(payload.password):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Heslo musí mať aspoň 10 znakov, veľké a malé písmeno a číslo."
                ),
            )
        try:
            user = app.state.store.create_user(
                name=name,
                email=email,
                password=payload.password,
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409, detail="Účet s týmto e-mailom už existuje."
            )
        token = app.state.store.create_session(user["id"])
        set_session_cookie(response, token)
        return {"user": user}

    @app.post("/api/auth/login")
    def login(payload: LoginPayload, request: Request, response: Response):
        client_ip = request.client.host if request.client else "unknown"
        if not app.state.limiter.check(f"login:{client_ip}", 12, 60):
            raise HTTPException(status_code=429, detail="Príliš veľa pokusov.")
        user_record = app.state.store.get_user_by_email(payload.email)
        if not user_record or not app.state.store.verify_password(
            user_record, payload.password
        ):
            raise HTTPException(status_code=401, detail="Nesprávny e-mail alebo heslo.")
        if not user_record["is_active"]:
            raise HTTPException(status_code=403, detail="Účet je deaktivovaný.")
        token = app.state.store.create_session(user_record["id"])
        set_session_cookie(response, token)
        return {"user": app.state.store.get_user(user_record["id"])}

    @app.post("/api/auth/logout", status_code=204)
    def logout(
        response: Response,
        nexus_session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    ):
        app.state.store.delete_session(nexus_session)
        cookie_path = "/nexus" if app.state.secure_cookies else "/"
        response.delete_cookie(COOKIE_NAME, path=cookie_path)

    @app.get("/api/auth/me")
    def me(user: dict[str, Any] = Depends(current_user)):
        return {"user": user}

    @app.get("/api/capabilities")
    def capabilities(user: dict[str, Any] = Depends(current_user)):
        settings = app.state.store.get_settings()
        infra_enabled = settings.get("infra_agent_enabled") == "1"
        infra_admin_only = settings.get("infra_agent_admin_only", "1") == "1"
        infra_available = infra_enabled and (
            user["role"] == "admin" or not infra_admin_only
        )
        data_enabled = settings.get("data_agent_enabled", "1") == "1"
        data_admin_only = settings.get("data_agent_admin_only", "0") == "1"
        return {
            "model": settings["model"],
            "rag_enabled": settings.get("rag_enabled") == "1",
            "infra_agent_available": infra_available,
            "infra_live_available": (
                infra_available
                and settings.get("infra_live_enabled", "1") == "1"
                and user["role"] == "admin"
            ),
            "data_agent_available": data_enabled
            and (user["role"] == "admin" or not data_admin_only),
        }

    @app.get("/api/conversations")
    def list_conversations(
        agent_mode: Literal["general", "infra", "data"] = "general",
        user: dict[str, Any] = Depends(current_user),
    ):
        return app.state.store.list_conversations(user["id"], agent_mode)

    @app.post("/api/conversations", status_code=201)
    def create_conversation(
        payload: ConversationPayload,
        user: dict[str, Any] = Depends(current_user),
    ):
        title = payload.title.strip() or "Nová konverzácia"
        return app.state.store.create_conversation(
            user["id"], title, payload.agent_mode
        )

    @app.get("/api/conversations/{conversation_id}")
    def get_conversation(
        conversation_id: int,
        user: dict[str, Any] = Depends(current_user),
    ):
        conversation = app.state.store.get_conversation(
            conversation_id, user["id"]
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Konverzácia neexistuje.")
        return conversation

    @app.delete("/api/conversations/{conversation_id}", status_code=204)
    def delete_conversation(
        conversation_id: int,
        user: dict[str, Any] = Depends(current_user),
    ):
        if not app.state.store.delete_conversation(conversation_id, user["id"]):
            raise HTTPException(status_code=404, detail="Konverzácia neexistuje.")

    @app.post("/api/conversations/{conversation_id}/messages", status_code=201)
    def send_message(
        conversation_id: int,
        payload: MessagePayload,
        request: Request,
        user: dict[str, Any] = Depends(current_user),
    ):
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=422, detail="Správa nemôže byť prázdna.")
        if len(content) > 12000:
            raise HTTPException(status_code=422, detail="Správa je príliš dlhá.")
        if not app.state.limiter.check(f"chat:{user['id']}", 30, 60):
            raise HTTPException(status_code=429, detail="Spomaľ, prosím.")
        conversation = app.state.store.get_conversation(
            conversation_id, user["id"]
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Konverzácia neexistuje.")
        settings = app.state.store.get_settings()
        if conversation["agent_mode"] != payload.agent_mode:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Tento chat patrí inému agentovi. "
                    "Prepnite na jeho samostatný chat."
                ),
            )
        if payload.agent_mode != "infra" and payload.infra_source != "snapshot":
            raise HTTPException(
                status_code=422,
                detail="LIVE zdroj je dostupný iba v INFRA chate.",
            )
        if payload.agent_mode == "infra":
            if settings.get("infra_agent_enabled") != "1":
                raise HTTPException(status_code=403, detail="Infra Agent je vypnutý.")
            if (
                settings.get("infra_agent_admin_only", "1") == "1"
                and user["role"] != "admin"
            ):
                raise HTTPException(
                    status_code=403, detail="Infra Agent je dostupný iba adminom."
                )
            if payload.infra_source == "live":
                if settings.get("infra_live_enabled", "1") != "1":
                    raise HTTPException(
                        status_code=403,
                        detail="LIVE Infra je vypnutá administrátorom.",
                    )
                if user["role"] != "admin":
                    raise HTTPException(
                        status_code=403,
                        detail="LIVE Infra je dostupná iba administrátorom.",
                    )
                if not app.state.limiter.check(
                    f"infra-live:{user['id']}", 10, 60
                ):
                    raise HTTPException(
                        status_code=429,
                        detail="Príliš veľa LIVE kontrol. Skús to o chvíľu.",
                    )
        if payload.agent_mode == "data":
            if settings.get("data_agent_enabled", "1") != "1":
                raise HTTPException(status_code=403, detail="Data Agent je vypnutý.")
            if (
                settings.get("data_agent_admin_only", "0") == "1"
                and user["role"] != "admin"
            ):
                raise HTTPException(
                    status_code=403, detail="Data Agent je dostupný iba adminom."
                )
        prompt_messages = [
            *conversation["messages"],
            {"role": "user", "content": content},
        ]
        system_prompt = settings["system_prompt"]
        model = settings["model"]
        rag_sources: list[dict[str, Any]] = []
        if settings.get("rag_enabled") == "1" and payload.agent_mode != "data":
            chunks = app.state.store.search_rag(
                content, int(settings.get("rag_max_chunks", "4"))
            )
            if chunks:
                context = "\n\n".join(
                    f"[KB:{chunk['document']}#{chunk['chunk_index']}]\n{chunk['content']}"
                    for chunk in chunks
                )
                system_prompt += (
                    "\n\nKNOWLEDGE BASE CONTEXT\n"
                    "Použi tento kontext iba ak je relevantný. Pri použití cituj "
                    "značku [KB:názov#chunk].\n\n"
                    f"{context}"
                )
                rag_sources = [
                    {
                        "document": chunk["document"],
                        "chunk": chunk["chunk_index"],
                    }
                    for chunk in chunks
                ]
        if payload.agent_mode == "infra":
            if payload.infra_source == "live":
                try:
                    snapshot = app.state.live_infra_collector()
                except Exception:
                    LOGGER.exception(
                        "Live infrastructure collection failed for user=%s",
                        user["id"],
                    )
                    raise HTTPException(
                        status_code=503,
                        detail="LIVE údaje servera sa nepodarilo bezpečne načítať.",
                    )
                app.state.store.audit(
                    user["id"],
                    "infra.live.read",
                    f"conversation:{conversation_id}",
                )
            else:
                try:
                    snapshot = read_snapshot(app.state.infra_snapshot_path)
                except InfraSnapshotError as error:
                    raise HTTPException(status_code=503, detail=str(error))
            if not isinstance(snapshot, dict) or not snapshot.get("generated_at"):
                raise HTTPException(
                    status_code=503,
                    detail="Infra údaje nemajú platný formát.",
                )
            system_prompt = (
                f"{infra_prompt(snapshot, payload.infra_source)}\n\n{system_prompt}"
            )
            model = settings.get("infra_model", settings["model"])
            rag_sources.append(
                {
                    "type": "infra",
                    "mode": payload.infra_source,
                    "generated_at": snapshot["generated_at"],
                }
            )
        try:
            if payload.agent_mode == "data":
                result = app.state.data_agent.answer(
                    question=content,
                    user_id=user["id"],
                    model=settings.get("data_model", settings["model"]),
                )
                rag_sources = [result["source"]]
            else:
                result = app.state.ai_provider.reply(
                    messages=prompt_messages,
                    user_id=user["id"],
                    model=model,
                    system_prompt=system_prompt,
                )
        except QueryRejected as error:
            raise HTTPException(status_code=422, detail=str(error))
        except AIUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error))
        except Exception:
            LOGGER.exception(
                "AI provider failed for user=%s conversation=%s",
                user["id"],
                conversation_id,
            )
            raise HTTPException(
                status_code=502,
                detail="AI služba momentálne neodpovedá. Skús to znova.",
            )
        response_text = str(result.get("text", "")).strip()
        if not response_text:
            raise HTTPException(
                status_code=502,
                detail="AI vrátila prázdnu odpoveď. Skús požiadavku odoslať znova.",
            )
        user_message, assistant_message = app.state.store.add_exchange(
            conversation_id,
            user_content=content,
            assistant_content=response_text,
            model=result.get("model"),
            input_tokens=result.get("input_tokens", 0),
            output_tokens=result.get("output_tokens", 0),
            sources=rag_sources,
            agent_mode=payload.agent_mode,
        )
        return {"user": user_message, "assistant": assistant_message}

    @app.get("/api/admin/overview")
    def admin_overview(
        user: dict[str, Any] = Depends(admin_user),
    ):
        return app.state.store.overview()

    @app.get("/api/admin/users")
    def admin_users(user: dict[str, Any] = Depends(admin_user)):
        return app.state.store.list_users()

    @app.patch("/api/admin/users/{user_id}")
    def admin_update_user(
        user_id: int,
        payload: UserUpdatePayload,
        actor: dict[str, Any] = Depends(admin_user),
    ):
        if payload.role is not None and payload.role not in {"user", "admin"}:
            raise HTTPException(status_code=422, detail="Neplatná rola.")
        if user_id == actor["id"] and (
            payload.is_active is False or payload.role == "user"
        ):
            raise HTTPException(
                status_code=400,
                detail="Nemôžeš deaktivovať ani degradovať vlastný admin účet.",
            )
        updated = app.state.store.update_user(
            user_id, role=payload.role, is_active=payload.is_active
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Používateľ neexistuje.")
        app.state.store.audit(
            actor["id"],
            "user.update",
            f"user:{user_id}",
        )
        return updated

    @app.get("/api/admin/settings")
    def admin_settings(user: dict[str, Any] = Depends(admin_user)):
        settings = app.state.store.get_settings()
        return {
            "model": settings["model"],
            "system_prompt": settings["system_prompt"],
            "rag_enabled": settings.get("rag_enabled") == "1",
            "rag_max_chunks": int(settings.get("rag_max_chunks", "4")),
            "infra_agent_enabled": settings.get("infra_agent_enabled") == "1",
            "infra_agent_admin_only": settings.get("infra_agent_admin_only", "1")
            == "1",
            "infra_live_enabled": settings.get("infra_live_enabled", "1") == "1",
            "infra_model": settings.get("infra_model", settings["model"]),
            "data_agent_enabled": settings.get("data_agent_enabled", "1") == "1",
            "data_agent_admin_only": settings.get("data_agent_admin_only", "0")
            == "1",
            "data_model": settings.get("data_model", settings["model"]),
            "api_configured": bool(os.getenv("OPENAI_API_KEY")),
        }

    @app.put("/api/admin/settings")
    def admin_update_settings(
        payload: SettingsPayload,
        actor: dict[str, Any] = Depends(admin_user),
    ):
        model_pattern = r"^[a-zA-Z0-9._:/-]+$"
        if not re.match(model_pattern, payload.model):
            raise HTTPException(status_code=422, detail="Neplatné označenie modelu.")
        if not re.match(model_pattern, payload.infra_model):
            raise HTTPException(
                status_code=422, detail="Neplatné označenie infra modelu."
            )
        if not re.match(model_pattern, payload.data_model):
            raise HTTPException(
                status_code=422, detail="Neplatné označenie data modelu."
            )
        settings = app.state.store.update_settings(
            {
                "model": payload.model.strip(),
                "system_prompt": payload.system_prompt.strip(),
                "rag_enabled": "1" if payload.rag_enabled else "0",
                "rag_max_chunks": str(payload.rag_max_chunks),
                "infra_agent_enabled": "1" if payload.infra_agent_enabled else "0",
                "infra_agent_admin_only": (
                    "1" if payload.infra_agent_admin_only else "0"
                ),
                "infra_live_enabled": "1" if payload.infra_live_enabled else "0",
                "infra_model": payload.infra_model.strip(),
                "data_agent_enabled": "1" if payload.data_agent_enabled else "0",
                "data_agent_admin_only": (
                    "1" if payload.data_agent_admin_only else "0"
                ),
                "data_model": payload.data_model.strip(),
            }
        )
        app.state.store.audit(actor["id"], "settings.update", settings["model"])
        return {
            "model": settings["model"],
            "system_prompt": settings["system_prompt"],
            "rag_enabled": settings["rag_enabled"] == "1",
            "rag_max_chunks": int(settings["rag_max_chunks"]),
            "infra_agent_enabled": settings["infra_agent_enabled"] == "1",
            "infra_agent_admin_only": settings["infra_agent_admin_only"] == "1",
            "infra_live_enabled": settings["infra_live_enabled"] == "1",
            "infra_model": settings["infra_model"],
            "data_agent_enabled": settings["data_agent_enabled"] == "1",
            "data_agent_admin_only": settings["data_agent_admin_only"] == "1",
            "data_model": settings["data_model"],
            "api_configured": bool(os.getenv("OPENAI_API_KEY")),
        }

    @app.get("/api/admin/data/schema")
    def admin_data_schema(user: dict[str, Any] = Depends(admin_user)):
        return {
            "database": "Nexus Synthetic Commerce",
            "fictional": True,
            "schema": app.state.synthetic_database.schema_prompt(),
        }

    @app.get("/api/admin/models")
    def admin_models(user: dict[str, Any] = Depends(admin_user)):
        try:
            models = app.state.model_catalog.list_models()
        except Exception:
            LOGGER.exception("Model catalog request failed")
            raise HTTPException(
                status_code=502, detail="Katalóg modelov sa nepodarilo načítať."
            )
        return {"models": models}

    @app.get("/api/admin/infra/status")
    def admin_infra_status(user: dict[str, Any] = Depends(admin_user)):
        try:
            snapshot = read_snapshot(app.state.infra_snapshot_path)
        except InfraSnapshotError:
            return {"available": False, "generated_at": None, "scope": "read_only"}
        return {
            "available": True,
            "generated_at": snapshot.get("generated_at"),
            "scope": snapshot.get("scope", "read_only"),
        }

    @app.get("/api/admin/rag/documents")
    def admin_rag_documents(user: dict[str, Any] = Depends(admin_user)):
        return {"documents": app.state.store.list_rag_documents()}

    @app.post("/api/admin/rag/documents", status_code=201)
    def admin_create_rag_document(
        payload: RagDocumentPayload,
        actor: dict[str, Any] = Depends(admin_user),
    ):
        try:
            name, content = validate_document(payload.name, payload.content)
        except OverflowError as error:
            raise HTTPException(status_code=413, detail=str(error))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))
        document = app.state.store.create_rag_document(name, content)
        app.state.store.audit(actor["id"], "rag.create", f"document:{document['id']}")
        return document

    @app.delete("/api/admin/rag/documents/{document_id}", status_code=204)
    def admin_delete_rag_document(
        document_id: int,
        actor: dict[str, Any] = Depends(admin_user),
    ):
        if not app.state.store.delete_rag_document(document_id):
            raise HTTPException(status_code=404, detail="Dokument neexistuje.")
        app.state.store.audit(actor["id"], "rag.delete", f"document:{document_id}")

    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @app.get("/")
    def spa():
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
