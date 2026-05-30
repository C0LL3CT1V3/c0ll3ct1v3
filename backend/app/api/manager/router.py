"""Artist manager chat (Auth0)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ...database import get_db
from ...models.user import User
from ...schemas.artist_schemas import ManagerChatBody, ManagerChatResponse
from ...services.artist_service import get_or_create_artist
from ...services.manager_llm import build_system_prompt, generate_manager_reply

router = APIRouter(prefix="/manager", tags=["manager"])


@router.post("/chat", response_model=ManagerChatResponse)
def manager_chat(
    body: ManagerChatBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManagerChatResponse:
    artist = get_or_create_artist(db, current_user)
    epk = artist.epk_config or {}
    system = build_system_prompt(
        artist.display_name,
        epk,
        artist.manager_system_prompt,
    )
    reply = generate_manager_reply(system, body.message.strip())
    return ManagerChatResponse(reply=reply)
