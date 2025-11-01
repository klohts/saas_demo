from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from saas_demo.app..database import get_db
from saas_demo.app.. import models

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.get("/")
def list_clients(db: Session = Depends(get_db)):
    return db.query(models.Client).all()

@router.post("/")
def create_client(name: str, email: str, db: Session = Depends(get_db)):
    new_client = models.Client(name=name, email=email)
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return new_client
