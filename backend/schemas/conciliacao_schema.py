from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ConciliacaoBase(BaseModel):
    conta_contabil: str
    periodo: str  # Ex: "2025-01"
    saldo: float
    arquivo_id: Optional[int] = None


class ConciliacaoCreate(ConciliacaoBase):
    pass


class ConciliacaoUpdate(BaseModel):
    conta_contabil: Optional[str] = None
    periodo: Optional[str] = None
    saldo: Optional[float] = None
    arquivo_id: Optional[int] = None


class ConciliacaoResponse(ConciliacaoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
