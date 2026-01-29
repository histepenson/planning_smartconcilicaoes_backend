# CLAUDE.md - Backend API

Este arquivo fornece orientações para o Claude Code ao trabalhar com código neste repositório.

## Visão Geral do Projeto

**conciliacao-api** é o backend de um sistema de conciliação contábil e financeira, desenvolvido com FastAPI e PostgreSQL. Processa arquivos Excel contendo dados financeiros e contábeis para identificar discrepâncias e gerar relatórios detalhados de conciliação.

**Frontend:** React em `C:\conciliacao-app`

### Fluxo Principal da Aplicação
1. Cadastro de empresa
2. Importação do plano de contas (Excel)
3. Upload de 3 arquivos de conciliação (Origem, Contábil Filtrado, Contábil Geral)
4. Processamento e geração de relatório de conciliação

## Comandos Principais

```bash
# Ativar ambiente virtual
.\venv\Scripts\activate     # Windows
source venv/bin/activate    # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Desenvolvimento (com reload automático)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Produção
uvicorn main:app --host 0.0.0.0 --port 8000

# Testar conexão com banco
python db.py
```

### Migrações (Alembic)
```bash
alembic revision --autogenerate -m "descrição"  # Criar migração
alembic upgrade head                             # Aplicar pendentes
alembic downgrade -1                             # Reverter última
alembic history                                  # Ver histórico
alembic current                                  # Status atual
```

## Arquitetura

### Estrutura de Camadas

```
Requisição HTTP
    ↓
Router (routers/)           → Endpoints da API
    ↓
Schema Pydantic (schemas/)  → Validação de entrada/saída
    ↓
Service (services/)         → Lógica de negócio e orquestração
    ↓
Tools (tools/)              → Processamento de dados (normalização, cálculos)
    ↓
Model SQLAlchemy (models/)  → Acesso ao banco
    ↓
PostgreSQL (schema: concilia)
```

### Estrutura de Pastas

```
conciliacao-api/
├── main.py                              # Ponto de entrada FastAPI, CORS, routers
├── db.py                                # Configuração SQLAlchemy, pool de conexões
├── requirements.txt                     # Dependências Python
├── alembic.ini                          # Configuração de migrações
├── alembic/
│   ├── env.py                           # Config do ambiente de migração
│   └── versions/                        # Scripts de migração
│
├── routers/                             # Endpoints da API
│   ├── empresa_router.py                # CRUD de empresas
│   ├── planodecontas_router.py          # CRUD + importação de plano de contas
│   ├── conciliacao_router.py            # Processamento de conciliação
│   └── arquivo_router.py                # Upload e gestão de arquivos
│
├── schemas/                             # Validação Pydantic
│   ├── empresa_schema.py                # Create, Update, Out para empresa
│   ├── planodecontas_schema.py          # Create, Update, Out + ImportacaoResultado
│   ├── conciliacao_schema.py            # RequestConciliacao, RelatorioConsolidacao
│   └── arquivo_conciliacao_schema.py    # Create, Update, Out para arquivos
│
├── services/                            # Lógica de negócio
│   ├── empresa_services.py              # CRUD empresas
│   ├── planodecontas_services.py        # CRUD + importação hierárquica
│   ├── conciliacao_service.py           # Orquestração da conciliação
│   └── analise_diferencas_service.py    # Análise detalhada por código
│
├── models/                              # Modelos SQLAlchemy
│   ├── __init__.py                      # Imports na ordem correta
│   ├── empresa.py                       # Entidade raiz
│   ├── planodecontas.py                 # Plano de contas
│   ├── conciliacao.py                   # Registros de conciliação
│   ├── arquivoconciliacao.py            # Metadados de arquivos
│   ├── request_models.py                # Schemas de request (legacy)
│   └── response_models.py               # Schemas de response (legacy)
│
├── tools/                               # Utilitários de processamento
│   ├── financeiro.py                    # Normalização de planilha financeira
│   ├── contabilidade.py                 # Normalização de planilha contábil
│   ├── calc_diferencas.py               # Cálculo de diferenças + export Excel
│   └── mappers.py                       # Conversão de dados para schemas
│
└── uploads/                             # Arquivos enviados pelo usuário
```

## Banco de Dados

**PostgreSQL** com schema `concilia`

### Tabelas e Relacionamentos

```
┌─────────────────┐
│     empresa     │  (raiz)
├─────────────────┤
│ id (PK)         │
│ nome            │
│ cnpj (unique)   │
│ status          │
│ created_at      │
│ updated_at      │
└────────┬────────┘
         │
         ├──────────────────────────────┐
         │                              │
         ▼                              ▼
┌─────────────────┐            ┌─────────────────┐
│  plano_contas   │            │  conciliacoes   │
├─────────────────┤            ├─────────────────┤
│ id (PK)         │            │ id (PK)         │
│ empresa_id (FK) │◄───────────│ empresa_id (FK) │
│ conta_contabil  │            │ conta_contabil_id (FK)
│ descricao       │            │ periodo         │
│ tipo_conta      │            │ saldo           │
│ conciliavel     │            │ created_at      │
│ conta_superior  │            │ updated_at      │
│ created_at      │            └────────┬────────┘
│ updated_at      │                     │
└─────────────────┘                     ▼
                               ┌─────────────────────┐
                               │ arquivos_conciliacao│
                               ├─────────────────────┤
                               │ id (PK)             │
                               │ conciliacao_id (FK) │
                               │ caminho_arquivo     │
                               │ data_conciliacao    │
                               │ created_at          │
                               │ updated_at          │
                               └─────────────────────┘
```

### Convenções de Nomenclatura
| Elemento | Padrão | Exemplo |
|----------|--------|---------|
| Classes (models) | Singular, PascalCase | `Empresa`, `PlanoDeContas` |
| Tabelas | Singular, snake_case | `empresa`, `plano_contas` |
| Schema | Sempre `concilia` | `__table_args__ = {"schema": "concilia"}` |
| Colunas | snake_case | `created_at`, `conta_contabil` |
| FKs | Full path | `"concilia.empresa.id"` |

## Endpoints da API

Base URL: `http://localhost:8000/api`

### Empresas (`/empresas`)
| Método | Endpoint | Função |
|--------|----------|--------|
| POST | `/empresas/` | Criar empresa (valida CNPJ duplicado) |
| GET | `/empresas/` | Listar todas |
| GET | `/empresas/{id}` | Obter por ID |
| PUT | `/empresas/{id}` | Atualizar (parcial) |
| DELETE | `/empresas/{id}` | Excluir (cascade) |

### Plano de Contas (`/plano-contas`)
| Método | Endpoint | Função |
|--------|----------|--------|
| GET | `/plano-contas/?empresa_id=X` | Listar contas (paginação) |
| GET | `/plano-contas/{id}` | Obter por ID |
| POST | `/plano-contas/` | Criar conta |
| PUT | `/plano-contas/{id}` | Atualizar |
| DELETE | `/plano-contas/{id}` | Excluir |
| POST | `/plano-contas/importar` | **Importar Excel** |

### Conciliação (`/conciliacoes`)
| Método | Endpoint | Função |
|--------|----------|--------|
| POST | `/conciliacoes/contabil` | **Processar conciliação** (endpoint principal) |

### Arquivos (`/arquivos`)
| Método | Endpoint | Função |
|--------|----------|--------|
| GET | `/arquivos/` | Listar (filtro por empresa_id) |
| GET | `/arquivos/{id}` | Obter por ID |
| POST | `/arquivos/` | Criar registro |
| POST | `/arquivos/upload` | **Upload de arquivo** |
| PUT | `/arquivos/{id}` | Atualizar |
| DELETE | `/arquivos/{id}` | Excluir (arquivo + registro) |

### Documentação
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Fluxo de Processamento da Conciliação

```
POST /conciliacoes/contabil
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ RequestConciliacao                                      │
│ ├── base_origem: {registros: [...]}       → Financeiro  │
│ ├── base_contabil_filtrada: {registros, conta_contabil} │
│ ├── base_contabil_geral: {registros: [...]}             │
│ └── parametros: {data_base, ...}                        │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ ConciliacaoService.executar()           │
│                                         │
│ 1. Valida dados de entrada              │
│ 2. normalizar_planilha_financeira()     │
│    └── Output: codigo | cliente | valor │
│ 3. normalizar_planilha_contabilidade()  │
│    └── Output: codigo | cliente | valor │
│ 4. calcular_diferencas()                │
│    └── Merge + cálculo de diferenças    │
│ 5. Filtra por tipo_diferenca            │
│ 6. AnaliseDiferencasService             │
│    └── Análise detalhada por código     │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ RelatorioConsolidacao (Response)        │
│ ├── resumo                              │
│ ├── diferencas_origem_maior             │
│ ├── diferencas_contabilidade_maior      │
│ ├── analise_detalhada                   │
│ ├── resumo_analise                      │
│ ├── observacoes                         │
│ └── alertas                             │
└─────────────────────────────────────────┘
```

## Tools - Processamento de Dados

### financeiro.py
**Função:** `normalizar_planilha_financeira(entrada) → DataFrame`

Processa planilha financeira com:
- Normalização de nomes de colunas
- Extração de código cliente: `"CODIGO-LOJA-NOME"` → `C{base}{loja}`
- Cálculo de valor: vencidos + a vencer
- Parse de números BR: `1.234.567,89`, `(100,00)`, sufixos D/C
- Cálculo de dias vencidos
- Classificação: "CURTO PRAZO" (≤365 dias) ou "LONGO PRAZO"
- Agregação por código

**Output:** `codigo | cliente | valor | dias_vencidos | TIPO`

### contabilidade.py
**Função:** `normalizar_planilha_contabilidade(entrada) → DataFrame`

Processa planilha contábil com:
- Normalização de nomes de colunas
- Extração de código: 6+2 dígitos → `C{base}{loja}`
- Parse de números BR
- Agregação por código

**Output:** `codigo | cliente | valor`

### calc_diferencas.py
**Função:** `calcular_diferencas(df_fin, df_cont, salvar_arquivo=True) → dict`

Calcula diferenças entre financeiro e contabilidade:
- Outer merge por código
- `diferenca = valor_cont - valor_fin`
- `diferenca_abs = |diferenca|`
- `diferenca_perc = (diferenca / valor_fin) * 100`

Classificação:
- `tipo_diferenca`: "Sem diferença" (≤0.01), "Contabilidade > Financeiro", "Financeiro > Contabilidade", "Exclusivo"
- `origem`: "Ambos", "Só Contabilidade", "Só Financeiro"

**Export Excel** (se salvar_arquivo=True):
- Sheet 1: Total das Diferenças
- Sheet 2: Com Diferenças
- Sheet 3: Só Financeiro
- Sheet 4: Só Contabilidade
- Sheet 5: Resumo

### mappers.py
Funções de mapeamento para schemas de resposta:
- `map_origem_maior(row)` → DiferencaOrigemMaior
- `map_contabilidade_maior(df, conta)` → List[DiferencaContabilidadeMaior]
- `classificar_prazo(codigo)` → "Curto" | "Longo"

## Services - Lógica de Negócio

### conciliacao_service.py
Classe `ConciliacaoService` - orquestra o fluxo de conciliação:
- `validar_dados()` - Valida estrutura do request
- `executar()` - Método principal de processamento
- `_filtrar_razao_por_conta()` - Filtra razão contábil
- `_formatar_resumo_analise()` - Formata resumo de análise

### analise_diferencas_service.py
Classe `AnaliseDiferencasService` - análise detalhada:
- `processar_analise_detalhada()` - Análise por código
- `gerar_resumo_analise()` - Totais e percentuais
- `_classificar_tipo()` - CONCILIADO | SO_FINANCEIRO | SO_CONTABILIDADE | DIVERGENTE_VALOR
- `_status()` - "verde" (≤0.01) | "vermelho"

**Threshold de conciliação:** `0.01` (R$ 0,01)

## Padrões de Código

### Routers
```python
@router.post("/", response_model=EmpresaOut)
def criar_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    # Validação de duplicidade no service
    # HTTPException(400) para erros de negócio
    # HTTPException(404) para não encontrado
```

### Services
```python
def criar_empresa(db: Session, empresa: EmpresaCreate) -> Empresa:
    # Verifica duplicidade
    if db.query(Empresa).filter(Empresa.cnpj == empresa.cnpj).first():
        raise HTTPException(400, "CNPJ já cadastrado")
    # Cria e retorna
```

### Models
```python
class Empresa(Base):
    __tablename__ = "empresa"
    __table_args__ = {"schema": "concilia"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships com cascade
    planos = relationship("PlanoDeContas", back_populates="empresa", cascade="all, delete-orphan")
```

### Schemas
```python
class EmpresaCreate(BaseModel):
    nome: str
    cnpj: str
    status: bool = True

class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    status: Optional[bool] = None

class EmpresaOut(BaseModel):
    id: int
    nome: str
    cnpj: str
    status: bool
    created_at: datetime

    class Config:
        from_attributes = True
```

## Configuração

### Arquivo .env
```env
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require
```

### db.py - Pool de Conexões
```python
Pool size: 10
Max overflow: 20
SSL: via DATABASE_URL
```

### Dependências Principais
- **FastAPI** 0.109.0 - Framework web
- **SQLAlchemy** ≥2.0.25 - ORM
- **Alembic** - Migrações
- **Uvicorn** 0.27.0 - Servidor ASGI
- **Pandas** ≥2.2.0 - Processamento de dados
- **openpyxl** 3.1.2 - Leitura/escrita Excel
- **psycopg2-binary** ≥2.9 - Driver PostgreSQL
- **python-dotenv** ≥1.0.0 - Variáveis de ambiente
- **python-multipart** 0.0.6 - Upload de arquivos

## Notas Importantes

1. **Schema do banco:** Sempre usar `concilia` em todas as operações
2. **Tabelas:** Nomes no SINGULAR (diferente do padrão Django)
3. **Uploads:** Salvos em `uploads/`
4. **Threshold:** Diferenças ≤ R$ 0,01 são consideradas conciliadas
5. **Alembic:** URL do banco hardcoded em `alembic.ini` - ajustar se necessário
6. **Testes:** Não implementados
7. **CORS:** Configurado para aceitar qualquer origem (desenvolvimento)

## Integração com Frontend

O frontend React está em `C:\conciliacao-app` e consome esta API via:
- Base URL: `http://localhost:8000/api`
- Formato: JSON
- Upload: multipart/form-data
