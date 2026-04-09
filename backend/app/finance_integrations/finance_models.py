
"""API models for finance integration workflows."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StepUpChallengeRequest(BaseModel):
    reason: str = Field(default="plaid_link")


class StepUpChallengeResponse(BaseModel):
    challenge_id: str
    allowed_methods: list[str]


class StepUpVerifyRequest(BaseModel):
    challenge_id: str
    otp_code: str


class StepUpVerifyResponse(BaseModel):
    mfa_verified_at: int
    expires_at: int


class PlaidLinkTokenRequest(BaseModel):
    client_name: str = "C0LL3CT1V3 Finance"
    language: str = "en"
    redirect_uri: str | None = None


class PlaidLinkTokenResponse(BaseModel):
    link_token: str
    expiration: str
    request_id: str


class PlaidDisconnectRequest(BaseModel):
    access_token: str
    source_account_id: str | None = None


class PlaidDisconnectResponse(BaseModel):
    removed: bool
    request_id: str
    purge_queued: bool = True


class PlaidPublicTokenExchangeRequest(BaseModel):
    public_token: str
    metadata: dict = Field(default_factory=dict)


class PlaidPublicTokenExchangeResponse(BaseModel):
    linked: bool
    item_id: str
    request_id: str
    institution_name: str | None = None
    account_count: int = 0
    model_config = ConfigDict(extra="ignore")


class WebhookAckResponse(BaseModel):
    accepted: bool
    replayed: bool = False
    event_id: str
    source: str
