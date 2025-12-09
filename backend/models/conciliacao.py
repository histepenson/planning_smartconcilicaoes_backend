from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Conciliacao(Base):
    __tablename__ = "conciliacoes"

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    EmpresaId = Column(Integer, ForeignKey("empresas.Id"))
    ContaContabilId = Column(Integer, ForeignKey("plano_contas.Id"))
    Periodo = Column(String(20), nullable=False)
    Saldo = Column(DECIMAL(18, 2), nullable=False)

    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())
    UpdatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="conciliacoes")
    conta_contabil = relationship("PlanoDeContas", back_populates="conciliacoes")
    arquivo = relationship("ArquivoConciliacao", back_populates="conciliacao", uselist=False)
