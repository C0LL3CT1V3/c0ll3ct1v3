"""Schemas for cloud provider OAuth and import."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CloudProviderStatus(BaseModel):
    connected: bool = False
    account_label: str | None = None
    configured: bool = False


class CloudStatusOut(BaseModel):
    google: CloudProviderStatus
    dropbox: CloudProviderStatus


class OAuthAuthorizeOut(BaseModel):
    url: str


class CloudFileOut(BaseModel):
    id: str
    name: str
    mime_type: str | None = None
    size: int | None = None
    is_folder: bool = False


class CloudFileListOut(BaseModel):
    files: list[CloudFileOut]
    next_page_token: str | None = None


class CloudImportBody(BaseModel):
    file_id: str = Field(..., min_length=1, max_length=1024)


class CloudDropboxImportBody(BaseModel):
    path: str = Field(..., min_length=1, max_length=2048)


class CloudImportOut(BaseModel):
    asset_id: str
    title: str | None
