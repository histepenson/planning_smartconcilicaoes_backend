# AGENTS.md

Este arquivo contém diretrizes para agentes de codificação que trabalham neste repositório da API de Conciliação Contábil e Financeira.

## Comandos de Build/Lint/Test

### Ambiente Virtual
```bash
# Ativar ambiente virtual (Windows)
source .venv/Scripts/activate

# Instalar dependências
pip install -r requirements.txt
```

### Execução do Servidor
```bash
# Desenvolvimento com reload automático
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Produção
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Banco de Dados e Migrações
```bash
# Testar conexão com banco
python db.py

# Criar migração após alterar models
alembic revision --autogenerate -m "descrição da alteração"

# Aplicar migrações
alembic upgrade head

# Ver status das migrações
alembic current
```

### Lint e Formatação
Este projeto não possui comandos de lint/teste configurados. Ao adicionar novas funcionalidades:
- Verificar manualmente a sintaxe Python
- Testar endpoints via Swagger UI: http://localhost:8000/docs
- Validar schemas Pydantic e models SQLAlchemy

### Testar Endpoint de Conciliação
```bash
# Acessar Swagger UI para testar endpoint principal
# http://localhost:8000/docs#/Concilia%C3%A7%C3%A3o/contabil_conciliacoes_contabil_post

# Ou usar curl/example diretamente com JSON das 3 bases
curl -X POST "http://localhost:8000/api/conciliacoes/contabil" \
  -H "Content-Type: application/json" \
  -d '{"base_origem": [...], "base_contabil_filtrada": [...], "base_contabil_geral": [...]}'
```

## Diretrizes de Estilo de Código

### Imports e Organização
```python
# 1. Imports padrão Python
from typing import Optional, List
from datetime import datetime

# 2. Imports de terceiros
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

# 3. Imports locais (em ordem alfabética)
from db import get_db
from schemas.empresa_schema import EmpresaCreate, EmpresaOut
from services.empresa_services import criar_empresa
```

### Formatação e Nomenclatura

**Arquivos e Classes:**
- Nomes de arquivos: snake_case (`empresa_router.py`, `plano_de_contas.py`)
- Classes: PascalCase (`Empresa`, `PlanoDeContas`, `EmpresaService`)
- Funções e variáveis: snake_case (`criar_empresa`, `empresa_id`)

**Models SQLAlchemy:**
- Classes: Singular e PascalCase (`Empresa`, `PlanoDeContas`)
- Tabelas: Singular e snake_case (`empresa`, `plano_contas`)
- Schema: Sempre usar `{"schema": "concilia"}` em `__table_args__`
- Colunas: snake_case (`created_at`, `updated_at`, `conta_contabil`)

**Schemas Pydantic:**
- Criar tipos separados: `Base`, `Create`, `Update`, `Out/Response`
- `Out` herda de `BaseModel` com `from_attributes = True`
- `Update` usa campos `Optional` para updates parciais

### Tipagem e Anotações
```python
# sempre tipar parâmetros e retornos
def criar_empresa(db: Session, empresa: EmpresaCreate) -> EmpresaOut:
    pass

def obter_empresa(db: Session, empresa_id: int) -> Optional[Empresa]:
    pass

# usar list[] para listas tipadas
def listar_empresas(db: Session) -> List[EmpresaOut]:
    pass
```

### Tratamento de Erros
```python
# Para recursos não encontrados
if not empresa:
    raise HTTPException(status_code=404, detail="Empresa não encontrada")

# Para conflitos/duplicidade
if empresa_existente:
    raise HTTPException(status_code=409, detail="Empresa já existe")

# Para erros de validação
raise HTTPException(status_code=422, detail="Dados inválidos")
```

### Padrões de Arquitetura

**Routers:**
- Prefixo no plural: `/empresas`, `/plano-contas`, `/conciliacoes`
- Tag para Swagger igual ao nome do recurso
- Dependency injection com `Depends(get_db)`
- Sempre retornar models response ou lançar HTTPException

**Services:**
- Uma função por operação CRUD
- Validação de duplicidade antes de criar
- Retornar `None` quando recurso não existe
- Usar `model_dump(exclude_unset=True)` para updates parciais

**Models:**
- Herdar de `Base` (db.py)
- Usar `relationship()` com `back_populates`
- `cascade="all, delete-orphan"` para relacionamentos
- Timestamps automáticos com `server_default=func.now()`

### Validação e Schema
```python
# Validators em schemas Pydantic
@field_validator('cnpj')
def validate_cnpj(cls, v):
    if not re.match(r'^\d{14}$', v):
        raise ValueError('CNPJ deve conter 14 dígitos')
    return v

# Campos obrigatórios vs opcionais
class EmpresaCreate(BaseModel):
    nome: str  # obrigatório
    cnpj: str  # obrigatório

class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None  # opcional para PATCH
    cnpj: Optional[str] = None
```

### Padrões de Banco
- Schema PostgreSQL: `concilia`
- Nomes de tabelas sempre no SINGULAR (diferente de Django)
- Índices em colunas de busca e FKs
- Relacionamentos com cascade delete apropriado
- Colunas timestamp: `created_at`, `updated_at`

### Estrutura de Pastas
```
routers/        # Endpoints FastAPI
schemas/        # Validação Pydantic  
services/       # Lógica de negócio
models/         # Models SQLAlchemy
tools/          # Utilitários de processamento
uploads/        # Arquivos enviados
alembic/        # Migrações de banco
```

### Interação com Frontend
- Base URL: `http://localhost:8000/api`
- CORS configurado para aceitar qualquer origem (desenvolvimento)
- Frontend React localizado em `C:\conciliacao-app`
- Usar response models consistentes para integração

### Endpoints Principais da API

**Upload de Arquivos:**
- `POST /api/arquivos/upload` - Upload de arquivos Excel
- `GET /api/arquivos/` - Listar arquivos
- `GET /api/arquivos/{id}` - Detalhes do arquivo
- `PUT /api/arquivos/{id}` - Atualizar metadados
- `DELETE /api/arquivos/{id}` - Excluir arquivo

**Conciliação:**
- `POST /api/conciliacoes/contabil` - Processamento principal (recebe 3 bases)
- `GET /api/conciliacoes/` - Listar conciliações
- `GET /api/conciliacoes/{id}` - Detalhes da conciliação

**Empresas e Plano de Contas:**
- `GET/POST/PUT/DELETE /api/empresas` - Gerenciamento de empresas
- `GET/POST/PUT/DELETE /api/plano-contas` - Plano de contas
- `POST /api/plano-contas/importar` - Importar plano de contas Excel

### Considerações Específicas
- Arquivos Excel são processados com `pandas` e `openpyxl`
- Lógica de conciliação contábil em `tools/`
- Schema `concilia` deve ser usado em todas as operações de banco
- Não existe testes automatizados - validar manualmente via API docs

### Processo de Conciliação - Fluxo Principal

**Upload de Arquivos:**
- 3 bases principais: Financeiro, Contabilização Financeira, Base Geral Contábil
- Endpoint: `POST /api/arquivos/upload`
- Arquivos salvos em `uploads/` com padrão `{empresa_id}_{tipo_arquivo}_{filename}`

**Normalização e Processamento:**
- `tools/financeiro.py`: Normaliza base financeira, extrai códigos de fornecedor
- `tools/contabilidade.py`: Normaliza base contábil, padroniza códigos
- `tools/calc_diferencas.py`: Calcula diferenças entre valores financeiros e contábeis

**Endpoint Principal de Conciliação:**
- `POST /api/conciliacoes/contabil`: Processa 3 bases e retorna resultados completos
- Retorna: resumo, diferenças (origem maior/contabilidade maior), análise detalhada

**Estrutura de Dados Esperada:**
- Códigos de fornecedor: formato 6 dígitos + 2 dígitos loja
- Valores normalizados: formato decimal brasileiro (1.234,56 → 1234.56)
- Agregação por código de fornecedor para comparação financeiro vs contábil