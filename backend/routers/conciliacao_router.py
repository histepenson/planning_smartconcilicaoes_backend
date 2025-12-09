from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.models import Conciliacao
import schemas.schemas as schemas

router = APIRouter(prefix="/conciliacao", tags=["Conciliação"])

@router.post("/", response_model=schemas.Conciliacao)
def create(data: schemas.ConciliacaoCreate, db: Session = Depends(get_db)):
    obj = Conciliacao(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{id}", response_model=schemas.Conciliacao)
def get_by_id(id: int, db: Session = Depends(get_db)):
    return db.query(Conciliacao).filter(Conciliacao.Id == id).first()
