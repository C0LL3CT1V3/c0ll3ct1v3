"""Pydantic models for manager threads and EPK builder."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ManagerThreadCreate(BaseModel):
    mode: str = Field(default="general", pattern="^(general|epk_builder)$")


class ManagerThreadOut(BaseModel):
    id: str
    mode: str
    created_at: Any

    model_config = {"from_attributes": True}


class ManagerMessageOut(BaseModel):
    id: str
    role: str
    content: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: Any

    model_config = {"from_attributes": True}


class ManagerThreadDetailOut(BaseModel):
    thread: ManagerThreadOut
    messages: list[ManagerMessageOut]


class ManagerChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    thread_id: str | None = None
    channel: str = Field(default="portal", max_length=32)
    mode: str | None = None


class ManagerChatResponse(BaseModel):
    reply: str
    thread_id: str
    message_id: str | None = None
    draft_updated: bool = False
    iteration_id: str | None = None
    reasoning_summary: str | None = None
    # Internal/debug — not used for v1 UI branching (use draft_updated).
    tool_used: str | None = Field(
        default=None,
        description="Internal: reply_to_artist | update_epk_draft",
    )


class ManagerStatusOut(BaseModel):
    configured: bool
    provider: str
    model: str


class EpkPreviewMediaItem(BaseModel):
    asset_id: str
    title: str | None = None
    url: str | None = None
    mime_type: str | None = None


class EpkDraftOut(BaseModel):
    design: dict[str, Any]
    site: dict[str, Any]
    tracks: list[EpkPreviewMediaItem] = Field(default_factory=list)
    photos: list[EpkPreviewMediaItem] = Field(default_factory=list)


class EpkComponentMapOut(BaseModel):
    components: list[dict[str, Any]]


class EpkIterateBody(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    thread_id: str | None = None


class EpkIterateOut(BaseModel):
    iteration_id: str
    thread_id: str
    reasoning_summary: str | None = None
    design: dict[str, Any]
    site: dict[str, Any]
    tracks: list[EpkPreviewMediaItem] = Field(default_factory=list)
    photos: list[EpkPreviewMediaItem] = Field(default_factory=list)
    screenshot_upload_url: str | None = None
    screenshot_storage_key: str | None = None


class EpkAnnotationItem(BaseModel):
    note: str = Field(..., min_length=1, max_length=4000)
    bbox_norm: dict[str, float] | None = None
    component_ids: list[str] = Field(default_factory=list)


class EpkAnnotateBody(BaseModel):
    annotations: list[EpkAnnotationItem] = Field(..., min_length=1)
    screenshot_storage_key: str | None = None


class EpkRefineOut(BaseModel):
    iteration_id: str
    parent_iteration_id: str
    reasoning_summary: str | None = None
    design: dict[str, Any]
    site: dict[str, Any]
    tracks: list[EpkPreviewMediaItem] = Field(default_factory=list)
    photos: list[EpkPreviewMediaItem] = Field(default_factory=list)
    annotations_resolved: list[dict[str, Any]] = Field(default_factory=list)
    screenshot_upload_url: str | None = None
    screenshot_storage_key: str | None = None


class EpkAcceptBody(BaseModel):
    consent_for_training: bool = False


class EpkTrainingConsentBody(BaseModel):
    allow_training_contribution: bool


class EpkPublishOut(BaseModel):
    epk_config: dict[str, Any]
