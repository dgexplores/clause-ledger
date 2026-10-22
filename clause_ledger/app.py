"""HTTP boundary with optional explicit provider extraction; no legal decisions."""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .analysis import analyze
from .semantic import ProviderError, analyze_semantic, configured
from .models import DocumentInput, Policy, ReviewInput
from .samples import SAMPLES
from .storage import Storage

ROOT = Path(__file__).resolve().parent


class BodyLimit:
    """Bound chunked bodies too, before JSON or multipart parsing allocates."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 1100000:
                return await JSONResponse({"detail": "Request is too large"}, status_code=413)(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()
        return await self.app(scope, replay, send)


def create_app(database_path=None):
    @asynccontextmanager
    async def lifespan(application):
        if database_path or os.getenv("CLAUSE_DB"):
            application.state.store = Storage(database_path or os.environ["CLAUSE_DB"])
            yield
        else:
            with tempfile.TemporaryDirectory(prefix="clause-ledger-") as folder:
                application.state.store = Storage(Path(folder) / "reviews.db")
                yield

    app = FastAPI(title="Clause Ledger", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None,
                  description="Explainable supplier-document checks with evidence and human review. Deterministic baseline; not legal advice.")
    app.add_middleware(BodyLimit)

    @app.middleware("http")
    async def boundaries(request: Request, call_next):
        if request.method in {"POST", "DELETE", "PUT", "PATCH"}:
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse({"detail": "Cross-origin changes are not allowed"}, status_code=403)
            length = request.headers.get("content-length")
            try:
                oversized = length is not None and int(length) > 1100000
            except ValueError:
                return JSONResponse({"detail": "Invalid request length"}, status_code=400)
            if oversized:
                return JSONResponse({"detail": "Request is too large (1 MiB upload limit)"}, status_code=413)
        token = request.cookies.get("clause_session", "")
        fresh = not re.fullmatch(r"[a-f0-9]{64}", token)
        if fresh:
            token = secrets.token_hex(32)
        request.state.owner = hashlib.sha256(token.encode()).hexdigest()
        response = await call_next(request)
        if fresh:
            response.set_cookie("clause_session", token, httponly=True, samesite="strict", secure=os.getenv("COOKIE_SECURE") == "true", max_age=86400)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
        return response

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    @app.get("/docs", include_in_schema=False)
    def reference():
        return FileResponse(ROOT / "static" / "api.html")

    @app.get("/healthz")
    def health():
        return {"status": "ok", "engine": "deterministic-extraction.v1", "llm_enabled": configured(),
                "storage": "persistent" if database_path or os.getenv("CLAUSE_DB") else "ephemeral-demo"}

    @app.get("/api/samples")
    def samples():
        return SAMPLES

    @app.get("/api/documents")
    def listing(request: Request):
        return request.app.state.store.listing(request.state.owner)

    def save(request, title, pages, policy, engine="deterministic"):
        try:
            report = analyze_semantic(pages, policy) if engine == "semantic" else analyze(pages, policy)
            return request.app.state.store.create(request.state.owner, title.strip(), pages, report)
        except ProviderError as error:
            raise HTTPException(502 if configured() else 503, str(error)) from error
        except OverflowError as error:
            raise HTTPException(429, str(error)) from error

    @app.post("/api/documents", status_code=201)
    def create_document(payload: DocumentInput, request: Request):
        if not payload.title.strip() or len(payload.text.strip()) < 30:
            raise HTTPException(422, "Add a title and at least 30 characters of document text")
        return save(request, payload.title, [payload.text], payload.policy, payload.engine)

    @app.post("/api/documents/pdf", status_code=201)
    async def create_pdf(request: Request, file: UploadFile = File(...), title: str = Form(...), policy: str = Form("{}"), engine: str = Form("deterministic")):
        if engine not in {"deterministic", "semantic"}:
            raise HTTPException(422, "Unsupported extraction engine")
        if not 1 <= len(title.strip()) <= 120:
            raise HTTPException(422, "Title must contain 1 to 120 characters")
        raw = await file.read(1024 * 1024 + 1)
        await file.close()
        if len(raw) > 1024 * 1024:
            raise HTTPException(413, "PDF must be at most 1 MiB")
        if not raw.startswith(b"%PDF-"):
            raise HTTPException(422, "Upload a PDF file, or use the text input")
        try:
            selected = Policy.model_validate_json(policy)
        except ValidationError as error:
            raise HTTPException(422, "Review policy is invalid") from error
        try:
            result = await asyncio.to_thread(subprocess.run, [sys.executable, "-m", "clause_ledger.pdf_worker"],
                                             input=raw, capture_output=True, timeout=5, check=False)
            parsed = json.loads(result.stdout)
        except (subprocess.TimeoutExpired, ValueError):
            raise HTTPException(422, "PDF parsing exceeded its limit. Paste the text instead.")
        if result.returncode or "error" in parsed:
            raise HTTPException(422, parsed.get("error", "PDF could not be parsed"))
        return await asyncio.to_thread(save, request, title, parsed["pages"], selected, engine)

    @app.get("/api/documents/{identifier}")
    def get_document(identifier: str, request: Request):
        document = request.app.state.store.get(request.state.owner, identifier)
        if document is None:
            raise HTTPException(404, "Review not found in this browser session")
        return document

    @app.post("/api/documents/{identifier}/review")
    def review(identifier: str, payload: ReviewInput, request: Request):
        if not payload.reviewer.strip() or len(payload.note.strip()) < 5:
            raise HTTPException(422, "Add a reviewer alias and a meaningful review note")
        try:
            return request.app.state.store.review(request.state.owner, identifier, payload)
        except KeyError:
            raise HTTPException(404, "Review not found in this browser session")
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @app.delete("/api/documents/{identifier}", status_code=204)
    def delete(identifier: str, request: Request):
        if not request.app.state.store.delete(request.state.owner, identifier):
            raise HTTPException(404, "Review not found in this browser session")
        return Response(status_code=204)

    return app


app = create_app()
