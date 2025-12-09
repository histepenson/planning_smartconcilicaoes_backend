# routers/arquivo_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import ArquivoConciliacao

router = APIRouter(prefix="/arquivos", tags=["Arquivos"])

@router.get("/")
def listar_arquivos(db: Session = Depends(get_db)):
    return db.query(ArquivoConciliacao).all()

@router.post("/")
def criar_arquivo(arquivo: ArquivoConciliacao, db: Session = Depends(get_db)):
    db.add(arquivo)
    db.commit()
    db.refresh(arquivo)
    return arquivo
