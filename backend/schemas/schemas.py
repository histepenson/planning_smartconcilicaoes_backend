from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# EMPRESA
class EmpresaBase(BaseModel):
    Nome: str
    CNPJ: str
    Status: bool = True

class EmpresaCreate(EmpresaBase):
    pass

class Empresa(EmpresaBase):
    Id: int
    CreatedAt: Optional[datetime]
    UpdatedAt: Optional[datetime]
    class Config:
        orm_mode = True


# PLANO DE CONTAS
class PlanoBase(BaseModel):
    EmpresaId: int
    ContaContabil: str
    TipoConta: str
    Conciliavel: bool

class PlanoCreate(PlanoBase):
    pass

class Plano(PlanoBase):
    Id: int
    CreatedAt: Optional[datetime]
    UpdatedAt: Optional[datetime]
    class Config:
        orm_mode = True


# ARQUIVO CONCILIAÇÃO
class ArquivoBase(BaseModel):
    ConciliacaoId: int
    CaminhoArquivo: str
    DataConciliacao: datetime

class ArquivoCreate(ArquivoBase):
    pass

class Arquivo(ArquivoBase):
    Id: int
    class Config:
        orm_mode = True


# CONCILIAÇÃO
class ConciliacaoBase(BaseModel):
    EmpresaId: int
    ContaContabilId: int
    Periodo: str
    Saldo: float

class ConciliacaoCreate(ConciliacaoBase):
    pass

class Conciliacao(ConciliacaoBase):
    Id: int
    CreatedAt: Optional[datetime]
    UpdatedAt: Optional[datetime]
    class Config:
        orm_mode = True
