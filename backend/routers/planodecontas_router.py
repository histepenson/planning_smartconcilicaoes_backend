from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.models import PlanoDeContas
import schemas.schemas as schemas

router = APIRouter(prefix="/plano", tags=["Plano de Contas"])

@router.post("/", response_model=schemas.Plano)
def create(plano: schemas.PlanoCreate, db: Session = Depends(get_db)):
    obj = PlanoDeContas(**plano.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{empresa_id}", response_model=list[schemas.Plano])
def list_by_empresa(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(PlanoDeContas).filter(PlanoDeContas.EmpresaId == empresa_id).all()
