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


class ArquivoConciliacao(Base):
    __tablename__ = "arquivos_conciliacao"

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ConciliacaoId = Column(Integer, ForeignKey("conciliacoes.Id"))
    CaminhoArquivo = Column(String(300), nullable=False)
    DataConciliacao = Column(DateTime, nullable=False)

    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())
    UpdatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    conciliacao = relationship("Conciliacao", back_populates="arquivo")


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
