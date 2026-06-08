"""FastAPI server for the FX agent pipeline."""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from ..infrastructure.llm import make_anthropic_llm
from ..infrastructure.settings import Settings
from ..orchestrator.graph import run_pipeline
from .models import RunEntry, RunStatus, RunSummary, StartRunRequest
from .store import RunStore

logger = logging.getLogger(__name__)
UTC = timezone.utc

settings = Settings()
store = RunStore()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("FX Agent server starting on port %d", settings.server_port)
    yield
    logger.info("FX Agent server stopping")


app = FastAPI(title="FX Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


# ── Runs ────────────────────────────────────────────────────────────────────

@app.get("/api/runs", response_model=list[RunSummary], tags=["runs"])
def list_runs():
    summaries = []
    for entry in store.all():
        final = entry.result.get("final_decision", {})
        summaries.append(
            RunSummary(
                run_id=entry.run_id,
                pair=entry.pair,
                date=entry.date,
                status=entry.status,
                created_at=entry.created_at,
                completed_at=entry.completed_at,
                direction=final.get("final_direction") if final else None,
                confidence=final.get("confidence") if final else None,
            )
        )
    return summaries


@app.post("/api/runs", response_model=RunSummary, tags=["runs"])
async def start_run(req: StartRunRequest):
    pair = req.pair.upper().replace("/", "").replace("-", "")
    run_id = uuid.uuid4().hex
    entry = RunEntry(
        run_id=run_id,
        pair=pair,
        date=date.today().isoformat(),
        status=RunStatus.PENDING,
    )
    store.create(entry)
    asyncio.create_task(_run_pipeline(run_id, pair))
    return RunSummary(
        run_id=run_id,
        pair=pair,
        date=entry.date,
        status=RunStatus.PENDING,
        created_at=entry.created_at,
    )


@app.get("/api/runs/{run_id}", response_model=RunEntry, tags=["runs"])
def get_run(run_id: str):
    entry = store.get(run_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return entry


@app.delete("/api/runs/{run_id}", tags=["runs"])
def delete_run(run_id: str):
    if not store.delete(run_id):
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {"deleted": run_id}


@app.get("/api/runs/{run_id}/pdf", tags=["runs"])
def download_pdf(run_id: str):
    entry = store.get(run_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    if entry.status != RunStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Run is not yet complete")
    try:
        from .pdf import generate_pdf
        pdf_bytes = generate_pdf(entry)
    except Exception:
        logger.exception("PDF generation failed run_id=%s", run_id)
        raise HTTPException(status_code=500, detail="PDF generation failed")
    filename = f"{entry.pair}_{entry.date}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── SSE progress stream ─────────────────────────────────────────────────────

@app.get("/api/runs/{run_id}/stream", tags=["runs"])
async def stream_run(run_id: str):
    async def event_gen():
        import json
        last_log_idx = 0
        while True:
            entry = store.get(run_id)
            if not entry:
                yield f"data: {json.dumps({'error': 'not found'})}\n\n"
                break
            new_logs = entry.log[last_log_idx:]
            last_log_idx = len(entry.log)
            for msg in new_logs:
                yield f"data: {json.dumps({'type': 'log', 'message': msg})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'status': entry.status})}\n\n"
            if entry.status in (RunStatus.COMPLETED, RunStatus.FAILED):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ── Static UI ───────────────────────────────────────────────────────────────

import os
_UI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ui", "dist")
if os.path.isdir(_UI_DIR):
    app.mount("/", StaticFiles(directory=_UI_DIR, html=True), name="ui")


# ── Pipeline runner ─────────────────────────────────────────────────────────

async def _run_pipeline(run_id: str, pair: str) -> None:
    entry = store.get(run_id)
    if not entry:
        return

    entry.status = RunStatus.RUNNING
    entry.log.append(f"Starting analysis for {pair}")
    store.update(entry)

    def _log(msg: str) -> None:
        e = store.get(run_id)
        if e:
            e.log.append(msg)
            store.update(e)

    try:
        llm_factory = make_anthropic_llm(settings.anthropic_api_key)

        _log("Running macro analyst...")
        _log("Running carry analyst...")
        _log("Running technical analyst...")
        _log("Running sentiment analyst...")
        _log("Running news analyst...")

        final_state = await run_pipeline(pair, llm_factory, settings)

        _log("Research debate complete")
        _log("Trade recommendation generated")
        _log("Risk analysis complete")
        _log("Fund manager decision complete")

        entry = store.get(run_id)
        entry.status = RunStatus.COMPLETED
        entry.completed_at = datetime.now(UTC)
        entry.result = dict(final_state)
        entry.log.append("Analysis complete")
        store.update(entry)
        logger.info("Pipeline completed run_id=%s pair=%s", run_id, pair)

    except Exception as exc:
        logger.exception("Pipeline failed run_id=%s", run_id)
        entry = store.get(run_id)
        if entry:
            entry.status = RunStatus.FAILED
            entry.error = str(exc)
            entry.log.append(f"Error: {exc}")
            store.update(entry)
