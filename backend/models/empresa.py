from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Nome = Column(String(150), nullable=False)
    CNPJ = Column(String(20), nullable=False)
    Status = Column(Boolean, default=True)

    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())
    UpdatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    plano_contas = relationship("PlanoDeContas", back_populates="empresa")
    conciliacoes = relationship("Conciliacao", back_populates="empresa")