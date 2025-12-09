from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class PlanoDeContas(Base):
    __tablename__ = "plano_contas"

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    EmpresaId = Column(Integer, ForeignKey("empresas.Id"))
    ContaContabil = Column(String(50), nullable=False)
    TipoConta = Column(String(20), nullable=False)
    Conciliavel = Column(Boolean, default=False)

    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())
    UpdatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="plano_contas")
    conciliacoes = relationship("Conciliacao", back_populates="conta_contabil")