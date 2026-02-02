# ConciliaAI - Arquitetura de Autenticação e Multi-Tenancy

## 1. Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Login Page  │  Admin Panel  │  User Dashboard  │  Company Selector         │
└──────────────┴───────────────┴──────────────────┴───────────────────────────┘
                                      │
                                      │ HTTPS + JWT
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                     │
│                     (Rate Limiting, CORS, Logging)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MIDDLEWARE LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Auth Middleware  │  Tenant Middleware  │  Permission Middleware            │
│  (JWT Validation)    (Company Context)     (Role/Permission Check)          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICE LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  AuthService  │  UserService  │  CompanyService  │  PermissionService       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA ACCESS LAYER                                  │
│                    (All queries filtered by empresa_id)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL (schema: concilia)                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Schema do Banco de Dados

### 2.1 Diagrama de Entidades

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│     usuario      │       │  usuario_empresa │       │     empresa      │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │       │ id (PK)          │
│ email (unique)   │◄──────│ usuario_id (FK)  │───────►│ nome             │
│ senha_hash       │       │ empresa_id (FK)  │       │ cnpj (unique)    │
│ nome             │       │ perfil_id (FK)   │       │ status           │
│ is_admin         │       │ is_active        │       │ created_at       │
│ is_active        │       │ created_at       │       │ updated_at       │
│ email_verified   │       │ updated_at       │       └────────┬─────────┘
│ created_at       │       │ created_by       │                │
│ updated_at       │       └──────────────────┘                │
│ last_login       │                │                          │
└──────────────────┘                │                          │
         │                          ▼                          │
         │               ┌──────────────────┐                  │
         │               │      perfil      │                  │
         │               ├──────────────────┤                  │
         │               │ id (PK)          │                  │
         │               │ nome             │                  │
         │               │ descricao        │                  │
         │               │ permissoes (JSON)│                  │
         │               │ is_system        │                  │
         │               │ created_at       │                  │
         │               └──────────────────┘                  │
         │                                                     │
         ▼                                                     ▼
┌──────────────────┐                              ┌──────────────────────┐
│  password_reset  │                              │ Todas as tabelas de  │
├──────────────────┤                              │ negócio incluem:     │
│ id (PK)          │                              ├──────────────────────┤
│ usuario_id (FK)  │                              │ empresa_id (FK)      │
│ token_hash       │                              │ created_by (FK)      │
│ expires_at       │                              │ updated_by (FK)      │
│ used_at          │                              │ created_at           │
│ created_at       │                              │ updated_at           │
└──────────────────┘                              └──────────────────────┘

┌──────────────────┐
│   audit_log      │
├──────────────────┤
│ id (PK)          │
│ usuario_id (FK)  │
│ empresa_id (FK)  │
│ action           │
│ entity_type      │
│ entity_id        │
│ old_values (JSON)│
│ new_values (JSON)│
│ ip_address       │
│ user_agent       │
│ created_at       │
└──────────────────┘
```

### 2.2 SQL de Criação das Tabelas

```sql
-- Schema
CREATE SCHEMA IF NOT EXISTS concilia;

-- Tabela de Usuários
CREATE TABLE concilia.usuario (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,          -- Admin master do sistema
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_usuario_email ON concilia.usuario(email);
CREATE INDEX idx_usuario_active ON concilia.usuario(is_active);

-- Tabela de Perfis (Roles)
CREATE TABLE concilia.perfil (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    permissoes JSONB NOT NULL DEFAULT '[]',   -- Lista de permissões
    is_system BOOLEAN DEFAULT FALSE,          -- Perfis do sistema (não editáveis)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Perfis padrão do sistema
INSERT INTO concilia.perfil (nome, descricao, permissoes, is_system) VALUES
('admin_empresa', 'Administrador da Empresa', '["*"]', true),
('analista', 'Analista de Conciliação', '["conciliacao:read", "conciliacao:write", "relatorio:read"]', true),
('visualizador', 'Apenas Visualização', '["conciliacao:read", "relatorio:read"]', true);

-- Tabela de Associação Usuário-Empresa (Multi-tenant)
CREATE TABLE concilia.usuario_empresa (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES concilia.usuario(id) ON DELETE CASCADE,
    empresa_id INTEGER NOT NULL REFERENCES concilia.empresa(id) ON DELETE CASCADE,
    perfil_id INTEGER NOT NULL REFERENCES concilia.perfil(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by INTEGER REFERENCES concilia.usuario(id),

    UNIQUE(usuario_id, empresa_id)
);

CREATE INDEX idx_usuario_empresa_usuario ON concilia.usuario_empresa(usuario_id);
CREATE INDEX idx_usuario_empresa_empresa ON concilia.usuario_empresa(empresa_id);
CREATE INDEX idx_usuario_empresa_active ON concilia.usuario_empresa(is_active);

-- Tabela de Reset de Senha
CREATE TABLE concilia.password_reset (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES concilia.usuario(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,         -- Hash do token (nunca armazenar plain)
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,         -- NULL = não usado
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_password_reset_token ON concilia.password_reset(token_hash);
CREATE INDEX idx_password_reset_expires ON concilia.password_reset(expires_at);

-- Tabela de Sessões (opcional, para invalidação)
CREATE TABLE concilia.user_session (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES concilia.usuario(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    empresa_id INTEGER REFERENCES concilia.empresa(id),  -- Empresa ativa na sessão
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_session_token ON concilia.user_session(token_hash);
CREATE INDEX idx_session_usuario ON concilia.user_session(usuario_id);

-- Tabela de Auditoria
CREATE TABLE concilia.audit_log (
    id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES concilia.usuario(id),
    empresa_id INTEGER REFERENCES concilia.empresa(id),
    action VARCHAR(50) NOT NULL,              -- CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.
    entity_type VARCHAR(100),                 -- Nome da tabela/entidade
    entity_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_usuario ON concilia.audit_log(usuario_id);
CREATE INDEX idx_audit_empresa ON concilia.audit_log(empresa_id);
CREATE INDEX idx_audit_action ON concilia.audit_log(action);
CREATE INDEX idx_audit_created ON concilia.audit_log(created_at);

-- Adicionar colunas de auditoria na tabela empresa existente
ALTER TABLE concilia.empresa ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES concilia.usuario(id);
ALTER TABLE concilia.empresa ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES concilia.usuario(id);

-- Adicionar empresa_id em todas as tabelas de negócio
ALTER TABLE concilia.plano_contas ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES concilia.usuario(id);
ALTER TABLE concilia.plano_contas ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES concilia.usuario(id);

ALTER TABLE concilia.conciliacoes ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES concilia.usuario(id);
ALTER TABLE concilia.conciliacoes ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES concilia.usuario(id);

ALTER TABLE concilia.arquivos_conciliacao ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES concilia.usuario(id);
ALTER TABLE concilia.arquivos_conciliacao ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES concilia.usuario(id);
```

---

## 3. Sistema de Permissões

### 3.1 Estrutura de Permissões

```python
# Formato: "recurso:ação"
PERMISSIONS = {
    # Administração
    "admin:users": "Gerenciar usuários do sistema",
    "admin:companies": "Gerenciar empresas",
    "admin:roles": "Gerenciar perfis",

    # Empresa
    "empresa:read": "Visualizar dados da empresa",
    "empresa:write": "Editar dados da empresa",

    # Plano de Contas
    "plano_contas:read": "Visualizar plano de contas",
    "plano_contas:write": "Editar plano de contas",
    "plano_contas:import": "Importar plano de contas",

    # Conciliação
    "conciliacao:read": "Visualizar conciliações",
    "conciliacao:write": "Criar/editar conciliações",
    "conciliacao:delete": "Excluir conciliações",
    "conciliacao:export": "Exportar relatórios",

    # Arquivos
    "arquivo:read": "Visualizar arquivos",
    "arquivo:upload": "Fazer upload de arquivos",
    "arquivo:delete": "Excluir arquivos",

    # Relatórios
    "relatorio:read": "Visualizar relatórios",
    "relatorio:export": "Exportar relatórios",

    # Wildcard
    "*": "Acesso total (admin)"
}
```

### 3.2 Perfis Padrão

| Perfil | Permissões |
|--------|------------|
| **admin_empresa** | `*` (todas) |
| **analista** | `conciliacao:*`, `arquivo:*`, `relatorio:*`, `plano_contas:read` |
| **visualizador** | `conciliacao:read`, `relatorio:read`, `plano_contas:read` |

---

## 4. Fluxos de Autenticação

### 4.1 Login

```
┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌──────────┐
│ Browser │     │   API   │     │ AuthService │     │    DB    │
└────┬────┘     └────┬────┘     └──────┬──────┘     └────┬─────┘
     │               │                 │                  │
     │ POST /auth/login               │                  │
     │ {email, password}              │                  │
     │──────────────►│                │                  │
     │               │                │                  │
     │               │ validate()     │                  │
     │               │───────────────►│                  │
     │               │                │                  │
     │               │                │ get_user(email)  │
     │               │                │─────────────────►│
     │               │                │                  │
     │               │                │◄─────────────────│
     │               │                │     user         │
     │               │                │                  │
     │               │                │ verify_password()│
     │               │                │ (bcrypt)         │
     │               │                │                  │
     │               │                │ get_empresas()   │
     │               │                │─────────────────►│
     │               │                │                  │
     │               │                │◄─────────────────│
     │               │                │   empresas[]     │
     │               │                │                  │
     │               │                │ create_session() │
     │               │                │─────────────────►│
     │               │                │                  │
     │               │◄───────────────│                  │
     │               │  {token, user, empresas}         │
     │◄──────────────│                │                  │
     │  200 OK       │                │                  │
     │  {access_token, refresh_token, │                  │
     │   user, empresas}              │                  │
```

### 4.2 Reset de Senha

```
┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌──────────┐     ┌─────────┐
│ Browser │     │   API   │     │ AuthService │     │    DB    │     │  Email  │
└────┬────┘     └────┬────┘     └──────┬──────┘     └────┬─────┘     └────┬────┘
     │               │                 │                  │               │
     │ POST /auth/forgot-password     │                  │               │
     │ {email}       │                │                  │               │
     │──────────────►│                │                  │               │
     │               │                │                  │               │
     │               │ request_reset()│                  │               │
     │               │───────────────►│                  │               │
     │               │                │                  │               │
     │               │                │ get_user(email)  │               │
     │               │                │─────────────────►│               │
     │               │                │                  │               │
     │               │                │ generate_token() │               │
     │               │                │ (crypto random)  │               │
     │               │                │                  │               │
     │               │                │ save_token_hash()│               │
     │               │                │─────────────────►│               │
     │               │                │                  │               │
     │               │                │ send_email()     │               │
     │               │                │──────────────────┼──────────────►│
     │               │                │                  │               │
     │               │◄───────────────│                  │               │
     │◄──────────────│                │                  │               │
     │ 200 OK        │                │                  │               │
     │ (sempre, por segurança)        │                  │               │
     │               │                │                  │               │
     │═══════════════════════════════════════════════════════════════════│
     │               │                │                  │               │
     │ POST /auth/reset-password      │                  │               │
     │ {token, new_password}          │                  │               │
     │──────────────►│                │                  │               │
     │               │                │                  │               │
     │               │ reset()        │                  │               │
     │               │───────────────►│                  │               │
     │               │                │                  │               │
     │               │                │ validate_token() │               │
     │               │                │─────────────────►│               │
     │               │                │                  │               │
     │               │                │ update_password()│               │
     │               │                │─────────────────►│               │
     │               │                │                  │               │
     │               │                │ invalidate_token()               │
     │               │                │─────────────────►│               │
     │               │◄───────────────│                  │               │
     │◄──────────────│                │                  │               │
     │ 200 OK        │                │                  │               │
```

### 4.3 Seleção de Empresa (Context Switch)

```
┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌──────────┐
│ Browser │     │   API   │     │ AuthService │     │    DB    │
└────┬────┘     └────┬────┘     └──────┬──────┘     └────┬─────┘
     │               │                 │                  │
     │ POST /auth/select-empresa      │                  │
     │ {empresa_id}  │                │                  │
     │ Header: Authorization: Bearer <token>             │
     │──────────────►│                │                  │
     │               │                │                  │
     │               │ validate_access()                 │
     │               │───────────────►│                  │
     │               │                │                  │
     │               │                │ check_permission()
     │               │                │─────────────────►│
     │               │                │                  │
     │               │                │ get_user_empresa()
     │               │                │─────────────────►│
     │               │                │                  │
     │               │                │ generate_new_token()
     │               │                │ (com empresa_id) │
     │               │◄───────────────│                  │
     │◄──────────────│                │                  │
     │ 200 OK        │                │                  │
     │ {access_token, empresa, permissoes}               │
```

---

## 5. Estrutura de Pastas (Backend)

```
conciliacao-api/
├── routers/
│   ├── auth_router.py           # Login, logout, reset password
│   ├── admin_router.py          # Painel administrativo
│   │   ├── users.py             # CRUD de usuários
│   │   ├── companies.py         # CRUD de empresas
│   │   └── roles.py             # CRUD de perfis
│   └── ... (routers existentes)
│
├── services/
│   ├── auth_service.py          # Lógica de autenticação
│   ├── user_service.py          # Lógica de usuários
│   ├── permission_service.py    # Verificação de permissões
│   ├── email_service.py         # Envio de emails
│   └── ... (services existentes)
│
├── models/
│   ├── usuario.py               # Model Usuario
│   ├── usuario_empresa.py       # Model UsuarioEmpresa
│   ├── perfil.py                # Model Perfil
│   ├── password_reset.py        # Model PasswordReset
│   ├── user_session.py          # Model UserSession
│   ├── audit_log.py             # Model AuditLog
│   └── ... (models existentes)
│
├── schemas/
│   ├── auth_schema.py           # Schemas de autenticação
│   ├── user_schema.py           # Schemas de usuário
│   ├── permission_schema.py     # Schemas de permissão
│   └── ... (schemas existentes)
│
├── middleware/
│   ├── auth_middleware.py       # Validação de JWT
│   ├── tenant_middleware.py     # Contexto de empresa
│   └── permission_middleware.py # Verificação de permissões
│
├── core/
│   ├── security.py              # Funções de hash, JWT, etc.
│   ├── config.py                # Configurações
│   └── dependencies.py          # Dependencies do FastAPI
│
└── utils/
    ├── email_templates/         # Templates de email
    │   ├── password_reset.html
    │   └── welcome.html
    └── audit.py                 # Funções de auditoria
```

---

## 6. Implementação dos Middlewares

### 6.1 Auth Middleware

```python
# middleware/auth_middleware.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime
from core.config import settings

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """Valida o token JWT e retorna o usuário atual."""
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id: int = payload.get("sub")
        empresa_id: int = payload.get("empresa_id")
        exp: int = payload.get("exp")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")

        if datetime.utcnow().timestamp() > exp:
            raise HTTPException(status_code=401, detail="Token expirado")

    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Buscar usuário no banco
    user = db.query(Usuario).filter(
        Usuario.id == user_id,
        Usuario.is_active == True
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    return {
        "user_id": user.id,
        "email": user.email,
        "nome": user.nome,
        "is_admin": user.is_admin,
        "empresa_id": empresa_id
    }
```

### 6.2 Tenant Middleware

```python
# middleware/tenant_middleware.py
from fastapi import Request, HTTPException, Depends
from typing import Optional

async def get_empresa_context(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Obtém o contexto da empresa atual do usuário."""

    empresa_id = current_user.get("empresa_id")

    if not empresa_id and not current_user.get("is_admin"):
        raise HTTPException(
            status_code=400,
            detail="Nenhuma empresa selecionada"
        )

    # Admin pode não ter empresa selecionada
    if current_user.get("is_admin") and not empresa_id:
        return {**current_user, "empresa_id": None, "permissoes": ["*"]}

    # Verificar se usuário tem acesso à empresa
    usuario_empresa = db.query(UsuarioEmpresa).filter(
        UsuarioEmpresa.usuario_id == current_user["user_id"],
        UsuarioEmpresa.empresa_id == empresa_id,
        UsuarioEmpresa.is_active == True
    ).first()

    if not usuario_empresa:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado a esta empresa"
        )

    # Carregar permissões do perfil
    perfil = db.query(Perfil).filter(Perfil.id == usuario_empresa.perfil_id).first()
    permissoes = perfil.permissoes if perfil else []

    return {
        **current_user,
        "empresa_id": empresa_id,
        "perfil_id": usuario_empresa.perfil_id,
        "permissoes": permissoes
    }
```

### 6.3 Permission Middleware

```python
# middleware/permission_middleware.py
from functools import wraps
from fastapi import HTTPException, Depends

def require_permission(permission: str):
    """Decorator para verificar permissão específica."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, context: dict = Depends(get_empresa_context), **kwargs):
            permissoes = context.get("permissoes", [])

            # Admin tem todas as permissões
            if "*" in permissoes:
                return await func(*args, context=context, **kwargs)

            # Verificar permissão específica
            if permission not in permissoes:
                # Verificar wildcard do recurso (ex: "conciliacao:*")
                resource = permission.split(":")[0]
                if f"{resource}:*" not in permissoes:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permissão negada: {permission}"
                    )

            return await func(*args, context=context, **kwargs)

        return wrapper
    return decorator


# Uso no router:
@router.get("/conciliacoes")
@require_permission("conciliacao:read")
async def listar_conciliacoes(context: dict = Depends(get_empresa_context)):
    # A query DEVE filtrar por empresa_id
    return db.query(Conciliacao).filter(
        Conciliacao.empresa_id == context["empresa_id"]
    ).all()
```

---

## 7. Considerações de Segurança

### 7.1 Senhas

```python
# core/security.py
from passlib.context import CryptContext
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash da senha usando bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica senha."""
    return pwd_context.verify(plain_password, hashed_password)

def generate_reset_token() -> tuple[str, str]:
    """Gera token de reset e seu hash."""
    token = secrets.token_urlsafe(32)
    token_hash = pwd_context.hash(token)
    return token, token_hash
```

### 7.2 JWT

```python
# core/security.py
from jose import jwt
from datetime import datetime, timedelta
from core.config import settings

def create_access_token(
    user_id: int,
    empresa_id: int = None,
    expires_delta: timedelta = None
) -> str:
    """Cria token JWT."""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))

    payload = {
        "sub": user_id,
        "empresa_id": empresa_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: int) -> str:
    """Cria refresh token (validade maior)."""
    expire = datetime.utcnow() + timedelta(days=7)

    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

### 7.3 Validações de Segurança

```python
# Política de senhas
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Valida força da senha."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Senha deve ter no mínimo {PASSWORD_MIN_LENGTH} caracteres"

    if PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, "Senha deve conter letra maiúscula"

    if PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        return False, "Senha deve conter letra minúscula"

    if PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        return False, "Senha deve conter número"

    if PASSWORD_REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Senha deve conter caractere especial"

    return True, ""

# Rate limiting para login
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

# Token de reset
RESET_TOKEN_EXPIRY_MINUTES = 30
RESET_TOKEN_SINGLE_USE = True
```

### 7.4 Headers de Segurança

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# Em produção, forçar HTTPS
if settings.ENVIRONMENT == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# CORS restrito
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # Lista específica
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Headers de segurança
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

---

## 8. Estrutura de UI / UX

### 8.1 Paleta de Cores

```css
:root {
  /* Primary - Azul Corporativo */
  --primary-50: #eff6ff;
  --primary-100: #dbeafe;
  --primary-200: #bfdbfe;
  --primary-300: #93c5fd;
  --primary-400: #60a5fa;
  --primary-500: #3b82f6;   /* Principal */
  --primary-600: #2563eb;
  --primary-700: #1d4ed8;
  --primary-800: #1e40af;
  --primary-900: #1e3a8a;

  /* Neutral - Cinzas */
  --neutral-50: #fafafa;
  --neutral-100: #f4f4f5;
  --neutral-200: #e4e4e7;
  --neutral-300: #d4d4d8;
  --neutral-400: #a1a1aa;
  --neutral-500: #71717a;
  --neutral-600: #52525b;
  --neutral-700: #3f3f46;
  --neutral-800: #27272a;
  --neutral-900: #18181b;

  /* Success */
  --success-500: #22c55e;
  --success-600: #16a34a;

  /* Warning */
  --warning-500: #f59e0b;
  --warning-600: #d97706;

  /* Error */
  --error-500: #ef4444;
  --error-600: #dc2626;

  /* Menu - Tons do Primary */
  --menu-bg: var(--primary-900);
  --menu-hover: var(--primary-800);
  --menu-active: var(--primary-700);
  --menu-text: var(--primary-100);
  --menu-text-muted: var(--primary-300);
}
```

### 8.2 Layout do Sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HEADER                                          │
│  ┌──────────┐                                    ┌─────────────────────────┐ │
│  │ ConciliaAI│                                   │ Empresa: ACME Corp ▼   │ │
│  └──────────┘                                    │ João Silva | Sair      │ │
└─────────────────────────────────────────────────────────────────────────────┘
│                               │                                              │
│  ┌─────────────────────────┐  │  ┌────────────────────────────────────────┐  │
│  │        MENU             │  │  │              CONTEÚDO                   │  │
│  │  ─────────────────────  │  │  │                                        │  │
│  │  📊 Dashboard           │  │  │                                        │  │
│  │  📁 Conciliações        │  │  │                                        │  │
│  │  📋 Plano de Contas     │  │  │                                        │  │
│  │  📄 Relatórios          │  │  │                                        │  │
│  │  ─────────────────────  │  │  │                                        │  │
│  │  ⚙️ Configurações       │  │  │                                        │  │
│  │                         │  │  │                                        │  │
│  │  (Se Admin:)            │  │  │                                        │  │
│  │  ─────────────────────  │  │  │                                        │  │
│  │  👥 Usuários            │  │  │                                        │  │
│  │  🏢 Empresas            │  │  │                                        │  │
│  │  🔐 Perfis              │  │  │                                        │  │
│  └─────────────────────────┘  │  └────────────────────────────────────────┘  │
└───────────────────────────────┴──────────────────────────────────────────────┘
```

### 8.3 Tela de Login

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                                                                              │
│                         ┌───────────────────────┐                            │
│                         │                       │                            │
│                         │      ConciliaAI       │                            │
│                         │   Sistema de          │                            │
│                         │   Conciliação         │                            │
│                         │                       │                            │
│                         │  ┌─────────────────┐  │                            │
│                         │  │ Email           │  │                            │
│                         │  └─────────────────┘  │                            │
│                         │                       │                            │
│                         │  ┌─────────────────┐  │                            │
│                         │  │ Senha        👁  │  │                            │
│                         │  └─────────────────┘  │                            │
│                         │                       │                            │
│                         │  ☐ Lembrar-me         │                            │
│                         │                       │                            │
│                         │  ┌─────────────────┐  │                            │
│                         │  │     ENTRAR      │  │                            │
│                         │  └─────────────────┘  │                            │
│                         │                       │                            │
│                         │  Esqueceu a senha?    │                            │
│                         │                       │                            │
│                         └───────────────────────┘                            │
│                                                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.4 Painel Administrativo - Usuários

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Gerenciamento de Usuários                              [+ Novo Usuário]    │
├─────────────────────────────────────────────────────────────────────────────┤
│  🔍 Buscar usuário...                    Status: [Todos ▼]                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Nome            │ Email              │ Empresas  │ Status │ Ações    │   │
│  ├──────────────────────────────────────────────────────────────────────│   │
│  │ João Silva      │ joao@email.com     │ 2         │ Ativo  │ ✏️ 🗑️    │   │
│  │ Maria Santos    │ maria@email.com    │ 1         │ Ativo  │ ✏️ 🗑️    │   │
│  │ Pedro Costa     │ pedro@email.com    │ 3         │ Inativo│ ✏️ 🗑️    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Mostrando 1-10 de 45 usuários                      < 1 2 3 4 5 >          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.5 Modal - Editar Usuário

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Editar Usuário                                                    [X]      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Nome *                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ João Silva                                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Email *                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ joao@email.com                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Status                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ [✓] Ativo                                                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Permissões por Empresa                                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Empresa              │ Perfil                │ Status    │ Ação     │    │
│  ├─────────────────────────────────────────────────────────────────────│    │
│  │ ACME Corporation     │ [Admin Empresa ▼]     │ [✓] Ativo │   🗑️    │    │
│  │ XYZ Ltda             │ [Analista ▼]          │ [✓] Ativo │   🗑️    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  [+ Adicionar Empresa]                                                       │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│                                        [Cancelar]    [Salvar Alterações]    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Endpoints da API

### 9.1 Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| POST | `/api/auth/refresh` | Renovar token |
| POST | `/api/auth/forgot-password` | Solicitar reset |
| POST | `/api/auth/reset-password` | Redefinir senha |
| POST | `/api/auth/select-empresa` | Selecionar empresa |
| GET | `/api/auth/me` | Dados do usuário logado |

### 9.2 Administração - Usuários

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/admin/usuarios` | Listar usuários |
| GET | `/api/admin/usuarios/{id}` | Obter usuário |
| POST | `/api/admin/usuarios` | Criar usuário |
| PUT | `/api/admin/usuarios/{id}` | Atualizar usuário |
| DELETE | `/api/admin/usuarios/{id}` | Desativar usuário |
| POST | `/api/admin/usuarios/{id}/empresas` | Adicionar empresa ao usuário |
| DELETE | `/api/admin/usuarios/{id}/empresas/{empresa_id}` | Remover empresa |

### 9.3 Administração - Empresas

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/admin/empresas` | Listar empresas |
| GET | `/api/admin/empresas/{id}` | Obter empresa |
| POST | `/api/admin/empresas` | Criar empresa |
| PUT | `/api/admin/empresas/{id}` | Atualizar empresa |
| DELETE | `/api/admin/empresas/{id}` | Desativar empresa |
| GET | `/api/admin/empresas/{id}/usuarios` | Usuários da empresa |

### 9.4 Administração - Perfis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/admin/perfis` | Listar perfis |
| GET | `/api/admin/perfis/{id}` | Obter perfil |
| POST | `/api/admin/perfis` | Criar perfil |
| PUT | `/api/admin/perfis/{id}` | Atualizar perfil |
| DELETE | `/api/admin/perfis/{id}` | Excluir perfil |

---

## 10. Checklist de Implementação

### Fase 1 - Infraestrutura de Auth
- [ ] Criar tabelas no banco
- [ ] Implementar models SQLAlchemy
- [ ] Implementar core/security.py (hash, JWT)
- [ ] Implementar middleware de autenticação
- [ ] Implementar middleware de tenant
- [ ] Implementar middleware de permissão

### Fase 2 - Endpoints de Auth
- [ ] POST /auth/login
- [ ] POST /auth/logout
- [ ] POST /auth/refresh
- [ ] POST /auth/forgot-password
- [ ] POST /auth/reset-password
- [ ] POST /auth/select-empresa
- [ ] GET /auth/me

### Fase 3 - Admin Panel Backend
- [ ] CRUD Usuários
- [ ] CRUD Empresas (adaptar existente)
- [ ] CRUD Perfis
- [ ] Associação usuário-empresa

### Fase 4 - Frontend Auth
- [ ] Tela de Login
- [ ] Tela de Forgot Password
- [ ] Tela de Reset Password
- [ ] Context de autenticação (React)
- [ ] Protected Routes
- [ ] Interceptor de requisições (token)

### Fase 5 - Frontend Admin
- [ ] Layout admin
- [ ] Listagem de usuários
- [ ] Form de usuário
- [ ] Listagem de empresas
- [ ] Form de empresa
- [ ] Listagem de perfis
- [ ] Form de perfil

### Fase 6 - Integração
- [ ] Seletor de empresa no header
- [ ] Filtro de empresa em todas as queries
- [ ] Validação de permissões nos endpoints existentes
- [ ] Auditoria de ações

---

## 11. Variáveis de Ambiente

```env
# Segurança
JWT_SECRET_KEY=sua-chave-secreta-muito-longa-e-aleatoria
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-app
SMTP_FROM_NAME=ConciliaAI
SMTP_FROM_EMAIL=noreply@conciliaai.com

# URLs
FRONTEND_URL=http://localhost:3000
RESET_PASSWORD_URL=${FRONTEND_URL}/reset-password

# Ambiente
ENVIRONMENT=development  # development | production
```

---

Este documento serve como especificação técnica completa para implementação do sistema de autenticação e multi-tenancy do ConciliaAI.
