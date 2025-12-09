from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.models import Empresa
import schemas.schemas as schemas

router = APIRouter(prefix="/empresa", tags=["Empresa"])

@router.post("/", response_model=schemas.Empresa)
def create(empresa: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    obj = Empresa(**empresa.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/", response_model=list[schemas.Empresa])
def list_all(db: Session = Depends(get_db)):
    return db.query(Empresa).all()
