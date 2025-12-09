from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ArquivoConciliacaoBase(BaseModel):
    conciliacao_id: int
    caminho_arquivo: str
    data_conciliacao: datetime


class ArquivoConciliacaoCreate(ArquivoConciliacaoBase):
    pass


class ArquivoConciliacaoResponse(ArquivoConciliacaoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
