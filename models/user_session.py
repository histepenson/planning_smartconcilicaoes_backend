# models/user_session.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, text
from sqlalchemy.orm import relationship
from db import Base


class UserSession(Base):
    """Modelo para sessões de usuário (para invalidação)."""

    __tablename__ = "user_session"
    __table_args__ = {"schema": "concilia"}

    # Colunas principais
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(
        Integer,
        ForeignKey("concilia.usuario.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(255), nullable=False, index=True)
    empresa_id = Column(
        Integer,
        ForeignKey("concilia.empresa.id", ondelete="SET NULL"),
        nullable=True,
    )
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)

    # Relacionamentos
    usuario = relationship(
        "Usuario",
        back_populates="sessions",
    )
    empresa = relationship("Empresa")

    def __repr__(self):
        return f"<UserSession(id={self.id}, usuario_id={self.usuario_id})>"

    @property
    def is_expired(self) -> bool:
        """Verifica se a sessão expirou."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_revoked(self) -> bool:
        """Verifica se a sessão foi revogada."""
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        """Verifica se a sessão é válida."""
        return not self.is_expired and not self.is_revoked
