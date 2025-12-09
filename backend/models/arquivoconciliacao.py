from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class ArquivoConciliacao(Base):
    __tablename__ = "arquivos_conciliacao"

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ConciliacaoId = Column(Integer, ForeignKey("conciliacoes.Id"))
    CaminhoArquivo = Column(String(300), nullable=False)
    DataConciliacao = Column(DateTime, nullable=False)

    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())
    UpdatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    conciliacao = relationship("Conciliacao", back_populates="arquivo")
