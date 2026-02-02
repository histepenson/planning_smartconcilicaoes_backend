# models/__init__.py
"""
Importações dos modelos em ordem correta para evitar problemas de relacionamento.

ORDEM IMPORTANTE:
1. Base (do db.py)
2. Modelos independentes (Usuario, Perfil)
3. Modelos de empresa
4. Modelos de associação (UsuarioEmpresa)
5. Modelos que dependem de múltiplos anteriores
"""

# Importa Base do db.py
from db import Base

# 1. Modelos independentes (sem FK ou com FK circular)
from .usuario import Usuario
from .perfil import Perfil

# 2. Modelos de empresa
from .empresa import Empresa

# 3. Modelos de associação
from .usuario_empresa import UsuarioEmpresa

# 4. Modelos com 1 FK
from .planodecontas import PlanoDeContas

# 5. Modelos com múltiplas FK
from .conciliacao import Conciliacao

# 6. Modelos que dependem dos anteriores
from .arquivoconciliacao import ArquivoConciliacao

# 7. Modelos de autenticação
from .password_reset import PasswordReset
from .user_session import UserSession
from .audit_log import AuditLog, AuditAction

# Lista todos os modelos exportados
__all__ = [
    "Base",
    # Auth
    "Usuario",
    "Perfil",
    "UsuarioEmpresa",
    "PasswordReset",
    "UserSession",
    "AuditLog",
    "AuditAction",
    # Business
    "Empresa",
    "PlanoDeContas",
    "Conciliacao",
    "ArquivoConciliacao",
]
