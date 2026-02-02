# middleware/auth.py
"""
Middleware de autenticação - Validação de JWT e usuário.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from db import get_db
from core.security import decode_token
from models import Usuario

# Security scheme para Swagger
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Contexto do usuário atual."""

    def __init__(
        self,
        user_id: int,
        email: str,
        nome: str,
        is_admin: bool,
        empresa_id: Optional[int] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.nome = nome
        self.is_admin = is_admin
        self.empresa_id = empresa_id

    def __repr__(self):
        return f"<CurrentUser(id={self.user_id}, email='{self.email}', empresa_id={self.empresa_id})>"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """
    Dependency que valida o token JWT e retorna o usuário atual.

    Raises:
        HTTPException 401: Se token inválido ou usuário não encontrado
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Decodificar token
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar tipo de token
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extrair dados do payload
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Buscar usuário no banco
    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar se usuário está ativo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário desativado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        user_id=user.id,
        email=user.email,
        nome=user.nome,
        is_admin=user.is_admin or payload.get("is_admin", False),
        empresa_id=payload.get("empresa_id"),
    )


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Dependency que garante que o usuário está ativo.
    (Redundante com get_current_user, mas pode ser útil para clareza)
    """
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[CurrentUser]:
    """
    Dependency que retorna o usuário atual se autenticado, ou None.
    Útil para endpoints públicos que têm comportamento diferente para usuários logados.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
