from fastapi import APIRouter

router = APIRouter(prefix="/emails", tags=["Emails"])

@router.get("/")
def get_emails():
    return {"message": "Email routes operational."}
