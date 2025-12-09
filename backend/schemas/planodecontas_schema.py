from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PlanoContasBase(BaseModel):
    empresa_id: int
    conta_contabil: str
    tipo: str  # "Analitica" ou "Sintetica"
    conciliavel: bool


class PlanoContasCreate(PlanoContasBase):
    pass


class PlanoContasUpdate(BaseModel):
    conta_contabil: Optional[str] = None
    tipo: Optional[str] = None
    conciliavel: Optional[bool] = None


class PlanoContasResponse(PlanoContasBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
