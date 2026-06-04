"""Artist manager chat and EPK builder (Auth0 portal + scoped in-process agent)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..manager_auth import get_manager_artist
from ...config import settings
from ...database import get_db
from ...models.artist import Artist
from ...models.manager import EpkIteration, ManagerThread
from ...schemas.manager_schemas import (
    EpkAcceptBody,
    EpkAnnotateBody,
    EpkComponentMapOut,
    EpkDraftOut,
    EpkIterateBody,
    EpkIterateOut,
    EpkPublishOut,
    EpkRefineOut,
    EpkTrainingConsentBody,
    ManagerChatBody,
    ManagerChatResponse,
    ManagerStatusOut,
    ManagerThreadCreate,
    ManagerThreadDetailOut,
    ManagerThreadOut,
)
from ...services.manager_llm import effective_manager_provider, manager_llm_configured, resolved_manager_model
from ...services.manager_rate_limit import enforce_manager_chat_rate_limit
from ...services.epk_component_registry import get_component_map
from ...services.epk_draft import get_or_init_draft
from ...services.manager_epk_service import (
    accept_iteration,
    annotate_iteration,
    build_preview_payload,
    chat_with_history,
    export_training_jsonl,
    get_or_create_thread,
    iterate_epk,
    list_thread_messages,
    publish_draft,
    refine_iteration,
)

router = APIRouter(prefix="/manager", tags=["manager"])


@router.get("/status", response_model=ManagerStatusOut)
def manager_status(
    artist: Artist = Depends(get_manager_artist),
) -> ManagerStatusOut:
    _ = artist
    provider = effective_manager_provider() or "none"
    return ManagerStatusOut(
        configured=manager_llm_configured(),
        provider=provider,
        model=resolved_manager_model(),
    )


@router.get("/threads", response_model=list[ManagerThreadOut])
def list_threads(
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> list[ManagerThread]:
    return (
        db.query(ManagerThread)
        .filter(ManagerThread.artist_id == artist.id)
        .order_by(ManagerThread.created_at.desc())
        .limit(20)
        .all()
    )


@router.post("/threads", response_model=ManagerThreadOut)
def create_thread(
    body: ManagerThreadCreate,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> ManagerThread:
    return get_or_create_thread(db, artist, body.mode, None)


@router.get("/threads/{thread_id}", response_model=ManagerThreadDetailOut)
def get_thread(
    thread_id: str,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> ManagerThreadDetailOut:
    thread = get_or_create_thread(db, artist, "general", thread_id)
    messages = list_thread_messages(db, thread.id, artist.id)
    return ManagerThreadDetailOut(thread=thread, messages=messages)


@router.post("/chat", response_model=ManagerChatResponse)
def manager_chat(
    body: ManagerChatBody,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> ManagerChatResponse:
    enforce_manager_chat_rate_limit(artist.id)
    mode = "epk_builder" if body.mode == "epk_builder" else "general"
    thread = get_or_create_thread(db, artist, mode, body.thread_id)
    turn = chat_with_history(
        db,
        artist,
        thread,
        body.message.strip(),
        channel=(body.channel or "portal").strip() or "portal",
    )
    last = list_thread_messages(db, thread.id, artist.id)[-1]
    reasoning = turn.reasoning_summary
    if turn.draft_updated and not reasoning:
        reasoning = "Draft updated."
    return ManagerChatResponse(
        reply=turn.reply,
        thread_id=thread.id,
        message_id=last.id,
        draft_updated=turn.draft_updated,
        iteration_id=turn.iteration_id,
        reasoning_summary=reasoning,
        tool_used=turn.tool_used,
    )


@router.get("/epk/draft", response_model=EpkDraftOut)
def get_epk_draft(
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> EpkDraftOut:
    design = get_or_init_draft(artist)
    if not artist.epk_draft:
        artist.epk_draft = design
        db.commit()
    payload = build_preview_payload(db, artist, design)
    return EpkDraftOut(**payload)


@router.get("/epk/component-map", response_model=EpkComponentMapOut)
def epk_component_map(
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> EpkComponentMapOut:
    design = get_or_init_draft(artist)
    return EpkComponentMapOut(components=get_component_map(design))


@router.post("/epk/iterate", response_model=EpkIterateOut)
def epk_iterate(
    body: EpkIterateBody,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> EpkIterateOut:
    thread = get_or_create_thread(db, artist, "epk_builder", body.thread_id)
    iteration, preview, upload_url, storage_key = iterate_epk(db, artist, body.prompt.strip(), thread)
    return EpkIterateOut(
        iteration_id=iteration.id,
        thread_id=thread.id,
        reasoning_summary=iteration.reasoning_summary,
        design=preview["design"],
        site=preview["site"],
        tracks=preview["tracks"],
        photos=preview["photos"],
        screenshot_upload_url=upload_url,
        screenshot_storage_key=storage_key,
    )


@router.post("/epk/iterations/{iteration_id}/annotate")
def epk_annotate(
    iteration_id: str,
    body: EpkAnnotateBody,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> dict:
    raw = [a.model_dump() for a in body.annotations]
    row = annotate_iteration(db, artist, iteration_id, raw, body.screenshot_storage_key)
    return {"iteration_id": row.id, "annotations_resolved": row.annotations_resolved}


@router.post("/epk/iterations/{iteration_id}/refine", response_model=EpkRefineOut)
def epk_refine(
    iteration_id: str,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> EpkRefineOut:
    parent = (
        db.query(EpkIteration)
        .filter(EpkIteration.id == iteration_id, EpkIteration.artist_id == artist.id)
        .first()
    )
    if not parent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Iteration not found.")
    child, preview, upload_url, storage_key = refine_iteration(db, artist, parent)
    return EpkRefineOut(
        iteration_id=child.id,
        parent_iteration_id=parent.id,
        reasoning_summary=child.reasoning_summary,
        design=preview["design"],
        site=preview["site"],
        tracks=preview["tracks"],
        photos=preview["photos"],
        annotations_resolved=child.annotations_resolved or [],
        screenshot_upload_url=upload_url,
        screenshot_storage_key=storage_key,
    )


@router.post("/epk/iterations/{iteration_id}/accept")
def epk_accept(
    iteration_id: str,
    body: EpkAcceptBody,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> dict:
    row = accept_iteration(db, artist, iteration_id, body.consent_for_training)
    return {"iteration_id": row.id, "accepted": True}


@router.post("/epk/draft/publish", response_model=EpkPublishOut)
def epk_publish(
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> EpkPublishOut:
    cfg = publish_draft(db, artist)
    return EpkPublishOut(epk_config=cfg)


@router.patch("/training/consent")
def training_consent(
    body: EpkTrainingConsentBody,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> dict:
    artist.allow_training_contribution = body.allow_training_contribution
    db.commit()
    return {"allow_training_contribution": artist.allow_training_contribution}


@router.get("/training/export")
def training_export(
    consent_only: bool = True,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> PlainTextResponse:
    body = export_training_jsonl(db, artist, consent_only=consent_only)
    return PlainTextResponse(content=body, media_type="application/x-ndjson")
