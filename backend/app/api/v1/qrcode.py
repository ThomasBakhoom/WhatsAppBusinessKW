"""WhatsApp QR Code generator API."""

import io
import base64
from fastapi import APIRouter, Query
from fastapi.responses import Response
from app.dependencies import AuthUser, TenantDbSession

router = APIRouter()


@router.get("/whatsapp")
async def generate_whatsapp_qr(
    db: TenantDbSession, user: AuthUser,
    phone: str = Query(..., description="WhatsApp number with country code"),
    message: str = Query(default="", description="Pre-filled message"),
):
    """Generate a WhatsApp QR code that opens a chat with pre-filled message."""
    import urllib.parse
    wa_url = f"https://wa.me/{phone.replace('+', '')}"
    if message:
        wa_url += f"?text={urllib.parse.quote(message)}"

    try:
        import qrcode
        qr = qrcode.make(wa_url)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")
    except ImportError:
        # qrcode not installed - return URL-based QR via external service
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={wa_url}"
        return {"qr_url": qr_url, "whatsapp_url": wa_url}


@router.get("/link")
async def generate_whatsapp_link(
    phone: str = Query(...), message: str = Query(default=""),
):
    """Generate a WhatsApp click-to-chat link (no auth required)."""
    import urllib.parse
    wa_url = f"https://wa.me/{phone.replace('+', '')}"
    if message:
        wa_url += f"?text={urllib.parse.quote(message)}"
    return {"url": wa_url}
