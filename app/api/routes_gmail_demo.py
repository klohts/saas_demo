from fastapi import APIRouter
from pydantic import BaseModel
from app.services.reply_engine import generate_reply
from app.services.gmail_service import draft_or_send_email

router = APIRouter()

class DemoReplyIn(BaseModel):
    subject: str
    body: str
    customer_email: str
    dry_run: bool = False

@router.post("/draft-reply")
def draft_reply(payload: DemoReplyIn):
    reply = generate_reply(payload.subject, payload.body)
    try:
        result = draft_or_send_email(
            to=payload.customer_email,
            subject=f"Re: {payload.subject}",
            body_text=reply,
            dry_run=payload.dry_run
        )
        return {
            "status": result.get("status"),
            "to": payload.customer_email,
            "subject": f"Re: {payload.subject}",
            "reply": reply,
            "result": result
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "reply": reply}
