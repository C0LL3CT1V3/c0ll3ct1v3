"""Artist Homebase (events calendar + Square pay) schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HomebaseEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    start: str = ""
    end: str | None = None
    venue: str = ""
    city: str = ""
    ticket_url: str = ""
    notes: str = ""
    image_asset_id: str | None = None


class HomebasePay(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    blurb: str = ""
    amounts: list[int] = Field(default_factory=lambda: [5, 10, 20])
    button_label: str = "Pay"


class HomebaseConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    published: bool = False
    headline: str = ""
    events: list[HomebaseEvent] = Field(default_factory=list)
    pay: HomebasePay = Field(default_factory=HomebasePay)


class HomebasePayPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool | None = None
    blurb: str | None = None
    amounts: list[int] | None = None
    button_label: str | None = None


class HomebasePatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    headline: str | None = None
    events: list[HomebaseEvent] | None = None
    pay: HomebasePayPatch | None = None


class HomebaseOut(BaseModel):
    config: HomebaseConfig
    public_homebase_url: str | None = None
    checkout_available: bool = False


class PublicHomebasePayOut(BaseModel):
    enabled: bool = True
    blurb: str = ""
    amounts: list[int] = Field(default_factory=list)
    button_label: str = "Pay"


class PublicHomebaseOut(BaseModel):
    tenant_slug: str
    display_name: str
    published: bool = True
    headline: str = ""
    events: list[dict[str, Any]] = Field(default_factory=list)
    pay: PublicHomebasePayOut = Field(default_factory=PublicHomebasePayOut)
    checkout_available: bool = False
    page_url: str | None = None
