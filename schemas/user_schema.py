# schemas/user_schema.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


# ============================================================
# USUARIO - CREATE
# ============================================================

class UsuarioCreate(BaseModel):
    """Schema para criação de usuário."""
    email: EmailStr
    nome: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)
    is_admin: bool = False

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        if not any(c.isupper() for c in v):
            raise ValueError("Senha deve conter pelo menos uma letra maiúscula")
        if not any(c.islower() for c in v):
            raise ValueError("Senha deve conter pelo menos uma letra minúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("Senha deve conter pelo menos um número")
        return v


# ============================================================
# USUARIO - UPDATE
# ============================================================

class UsuarioUpdate(BaseModel):
    """Schema para atualização de usuário."""
    email: Optional[EmailStr] = None
    nome: Optional[str] = Field(None, min_length=2, max_length=255)
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class UsuarioUpdatePassword(BaseModel):
    """Schema para atualização de senha pelo admin."""
    password: str = Field(..., min_length=8)


# ============================================================
# USUARIO - OUTPUT
# ============================================================

class UsuarioOut(BaseModel):
    """Schema de saída de usuário."""
    id: int
    email: str
    nome: str
    is_admin: bool
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UsuarioListOut(BaseModel):
    """Schema de saída para listagem de usuários."""
    id: int
    email: str
    nome: str
    is_admin: bool
    is_active: bool
    empresas_count: int = 0
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UsuarioDetailOut(BaseModel):
    """Schema de saída detalhada de usuário."""
    id: int
    email: str
    nome: str
    is_admin: bool
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    empresas: List["UsuarioEmpresaOut"]

    class Config:
        from_attributes = True


# ============================================================
# USUARIO EMPRESA
# ============================================================

class UsuarioEmpresaCreate(BaseModel):
    """Schema para adicionar usuário a uma empresa."""
    empresa_id: int
    perfil_id: int


class UsuarioEmpresaUpdate(BaseModel):
    """Schema para atualizar associação usuário-empresa."""
    perfil_id: Optional[int] = None
    is_active: Optional[bool] = None


class UsuarioEmpresaOut(BaseModel):
    """Schema de saída de associação usuário-empresa."""
    id: int
    usuario_id: int
    usuario_nome: Optional[str] = None
    usuario_email: Optional[str] = None
    empresa_id: int
    empresa_nome: str
    empresa_cnpj: str
    perfil_id: int
    perfil_nome: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# PERFIL
# ============================================================

class PerfilCreate(BaseModel):
    """Schema para criação de perfil."""
    nome: str = Field(..., min_length=2, max_length=100)
    descricao: Optional[str] = None
    permissoes: List[str] = []


class PerfilUpdate(BaseModel):
    """Schema para atualização de perfil."""
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    descricao: Optional[str] = None
    permissoes: Optional[List[str]] = None


class PerfilOut(BaseModel):
    """Schema de saída de perfil."""
    id: int
    nome: str
    descricao: Optional[str]
    permissoes: List[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# PAGINATION
# ============================================================

class PaginatedResponse(BaseModel):
    """Schema genérico para respostas paginadas."""
    items: List
    total: int
    page: int
    per_page: int
    pages: int


class UsuariosPaginatedResponse(BaseModel):
    """Schema para listagem paginada de usuários."""
    items: List[UsuarioListOut]
    total: int
    page: int
    per_page: int
    pages: int


# Rebuild models para resolver forward references
UsuarioDetailOut.model_rebuild()
