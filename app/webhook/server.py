import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Response

from app.cli.commands_ask import create_chat_service
from app.config import get_settings
from app.storage.sqlite_registry import SQLiteRegistry
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)

_chat_service = None
_registry = None
_whatsapp_service: Optional[WhatsAppService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _chat_service, _registry, _whatsapp_service
    settings = get_settings()
    paths = settings.resolve_paths()

    _registry = SQLiteRegistry(paths.sqlite_db_path)
    _chat_service = create_chat_service()

    if (
        settings.whatsapp_enabled
        and settings.twilio_account_sid
        and settings.twilio_auth_token
    ):
        _whatsapp_service = WhatsAppService(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            from_number=settings.twilio_whatsapp_number,
        )
    else:
        logger.warning(
            "Twilio credentials not set or WHATSAPP_ENABLED=false — "
            "/health still serves but messages will not be sent"
        )

    yield


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(
    From: Optional[str] = Form(None),
    Body: str = Form(""),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None),
):
    if not From:
        raise HTTPException(status_code=400, detail="Missing From field")

    phone = From
    session_id = _registry.get_or_create_whatsapp_session(phone)

    result = _chat_service.answer_in_session(
        session_id=session_id,
        question=Body,
        response_style="whatsapp",
    )
    reply = result.answer

    if _whatsapp_service:
        _whatsapp_service.send_message(to=phone, body=reply)
    else:
        logger.warning("WhatsApp service unavailable; reply not sent to %s", phone)

    _registry.update_whatsapp_last_active(phone)

    return Response(content="", media_type="application/xml")


@app.get("/health")
async def health():
    return {"status": "ok"}
