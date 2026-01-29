# Implementação da Análise Detalhada - Versão 2

## Resumo

Implementação da lógica correta de conciliação contábil-financeira para a grid de **Análise Detalhada por Fornecedor**, conforme as regras contábeis:

1. **Título gerado** → Lançamento a **CRÉDITO** na contabilidade
2. **Título pago** (baixa) → Lançamento a **DÉBITO** na contabilidade para zerar
3. **Matching**: Se existe no financeiro → deve existir lançamento a CRÉDITO na contabilidade
4. **Identificação de lançamentos órfãos** e não contabilizados

---

## Arquivos Modificados

### 1. `/tools/rastreamento.py`

#### Novas Funções Adicionadas:

**`extrair_nf_do_historico(historico: str)`**
- Extrai número da Nota Fiscal do histórico contábil
- Suporta diversos formatos: "NF. 020252443", "NF354753007", "NOTA FISCAL 123456"
- Retorna: `Optional[str]` com o número da NF

**`extrair_codigo_fornecedor_do_historico(historico: str)`**
- Extrai código do fornecedor do histórico
- Padrões: "FORN 004111", "FORNECEDOR 067201"
- Retorna: `Optional[str]` com o código

**`identificar_colunas_razao(df_razao: pd.DataFrame)`**
- Identifica automaticamente as colunas do razão contábil
- Mapeia: conta, data, historico, filial, item_contabil, debito, credito, lote, centro_custo
- Retorna: `Dict[str, Optional[str]]`

**`processar_lancamento(row: pd.Series, colunas_mapa: Dict)`**
- Processa uma linha do razão e extrai informações estruturadas
- Identifica automaticamente se é DÉBITO ou CRÉDITO
- Extrai NF e código do fornecedor do histórico
- Retorna: `Dict` com todas as informações do lançamento

**`rastrear_diferenca()` - REESCRITA COMPLETA**
- Nova lógica que separa lançamentos por tipo (DÉBITO/CRÉDITO)
- Calcula: total_credito, total_debito, saldo contábil
- Identifica lançamentos não contabilizados no financeiro
- Identifica lançamentos órfãos na contabilidade
- Retorna estrutura detalhada com:
  - `lancamentos_credito`: Lista de lançamentos a crédito
  - `lancamentos_debito`: Lista de lançamentos a débito
  - `lancamentos_nao_contabilizados`: Faltam na contabilidade
  - `lancamentos_orfaos_contabilidade`: Estão na contab mas não no financeiro
  - `total_credito`, `total_debito`, `total_rastreado`
  - `observacao`, `recomendacao`

**`buscar_lancamentos_faltantes()`**
- Busca lançamentos que deveriam existir mas não foram contabilizados
- Exemplo: Financeiro R$ 500, Contabilidade R$ 400 → Busca CRÉDITO de R$ 100

**`identificar_lancamentos_orfaos()`**
- Identifica lançamentos na contabilidade sem correspondência no financeiro
- Exemplo: Contabilidade R$ 500, Financeiro R$ 400 → Identifica CRÉDITO órfão de R$ 100

**`gerar_observacao_rastreamento()`**
- Gera observação descritiva do rastreamento

**`gerar_recomendacao_rastreamento()`**
- Gera recomendação baseada na análise (conciliado, faltante, órfão)

---

### 2. `/schemas/conciliacao_schema.py`

#### `LancamentoRastreado` - EXPANDIDO:

```python
class LancamentoRastreado(BaseModel):
    conta_contabil: str
    data_lancamento: Optional[str] = None
    lote: Optional[str] = None
    historico: Optional[str] = None
    filial_origem: Optional[str] = None
    centro_custo: Optional[str] = None
    item_contabil: Optional[str] = None
    debito: float = 0.0                          # NOVO
    credito: float = 0.0                         # NOVO
    valor: float
    tipo_lancamento: str                         # DÉBITO, CRÉDITO, INDEFINIDO
    nf_extraida: Optional[str] = None            # NOVO
    codigo_fornecedor_historico: Optional[str] = None  # NOVO
    confianca_match: Optional[str] = "ALTA"
    criterio_match: Optional[str] = ""
```

#### `AnaliseDiferencaDetalhada` - EXPANDIDO:

```python
class AnaliseDiferencaDetalhada(BaseModel):
    codigo_fornecedor: str
    nome_fornecedor: Optional[str] = None
    valor_financeiro: float
    valor_contabilidade: float
    diferenca: float
    tipo_diferenca: str
    status: str

    # Lançamentos separados por tipo
    lancamentos_encontrados: List[LancamentoRastreado] = []
    lancamentos_credito: List[LancamentoRastreado] = []      # NOVO
    lancamentos_debito: List[LancamentoRastreado] = []       # NOVO
    lancamentos_nao_contabilizados: List[LancamentoRastreado] = []  # NOVO
    lancamentos_orfaos_contabilidade: List[LancamentoRastreado] = []  # NOVO

    # Totais
    total_credito: float = 0.0                               # NOVO
    total_debito: float = 0.0                                # NOVO
    total_rastreado: float = 0.0
    diferenca_nao_localizada: float = 0.0

    # Observações
    observacao: str = ""
    recomendacao: str = ""
```

---

### 3. `/services/analise_diferencas_service.py`

#### `_analisar_registro()` - ATUALIZADO:

- Agora retorna todos os novos campos da análise
- Separa lançamentos por tipo (crédito/débito)
- Inclui lançamentos não contabilizados e órfãos
- Calcula totais separados de crédito e débito

#### `_gerar_observacao()` - REMOVIDO:

- Substituído pela observação gerada no rastreamento

---

## Lógica de Conciliação Implementada

### Estrutura do Razão Contábil

O razão possui as seguintes colunas:
1. Conta Contábil
2. Data
3. Lote
4. Histórico (contém CFOP, NF, descrição)
5. Filial Origem
6. Centro de Custo
7. Item Contábil (código do fornecedor)
8. **Débito**
9. **Crédito**

### Regras de Lançamento

- **Geração de título** → Lançamento a **CRÉDITO**
- **Baixa de título** (pagamento) → Lançamento a **DÉBITO**

### Processo de Matching

1. **Buscar todos os lançamentos do fornecedor** no razão contábil
2. **Separar** por tipo: DÉBITO e CRÉDITO
3. **Calcular saldo contábil**: Créditos - Débitos
4. **Comparar** com valor do financeiro

### Cenários de Análise

#### Cenário 1: Financeiro > Contabilidade

```
Financeiro: R$ 500,00 (títulos a pagar)
Contabilidade: R$ 400,00 (créditos - débitos)
Diferença: R$ 100,00

Ação:
- Buscar lançamento a CRÉDITO de R$ 100 que deveria existir
- Classificar como "Lançamento não contabilizado"
- Alertar que faltam R$ 100 em créditos na contabilidade
```

#### Cenário 2: Contabilidade > Financeiro

```
Financeiro: R$ 400,00 (títulos a pagar)
Contabilidade: R$ 500,00 (créditos - débitos)
Diferença: R$ 100,00

Ação:
- Identificar lançamento a CRÉDITO de R$ 100 órfão
- Classificar como "Lançamento órfão na contabilidade"
- Alertar que existe crédito sem correspondência no financeiro
```

#### Cenário 3: Valores Conciliam

```
Financeiro: R$ 500,00
Contabilidade: R$ 500,00
Diferença: R$ 0,00

Resultado:
- Status: CONCILIADO (verde)
- Recomendação: "Valores conciliam. Financeiro = Contabilidade."
```

---

## Exemplos de Uso

### Exemplo de Lançamento Processado

```json
{
  "conta_contabil": "2.01.01.001",
  "data_lancamento": "2024-01-15",
  "lote": "00001",
  "historico": "CFOP 1933 NF. 020252443 FORN 004111 - RODA MAIS RENO",
  "filial_origem": "01",
  "centro_custo": "ADM",
  "item_contabil": "C00067201",
  "debito": 0.0,
  "credito": 500.0,
  "valor": 500.0,
  "tipo_lancamento": "CRÉDITO",
  "nf_extraida": "020252443",
  "codigo_fornecedor_historico": "004111",
  "confianca_match": "ALTA",
  "criterio_match": "Código encontrado no histórico"
}
```

### Exemplo de Análise Detalhada

```json
{
  "codigo_fornecedor": "C00067201",
  "nome_fornecedor": "RODA MAIS RENO",
  "valor_financeiro": 500.0,
  "valor_contabilidade": 400.0,
  "diferenca": -100.0,
  "tipo_diferenca": "DIVERGENTE_VALOR",
  "status": "vermelho",

  "lancamentos_credito": [
    { "tipo_lancamento": "CRÉDITO", "valor": 300.0, "nf_extraida": "020252443" },
    { "tipo_lancamento": "CRÉDITO", "valor": 200.0, "nf_extraida": "020252444" }
  ],
  "lancamentos_debito": [
    { "tipo_lancamento": "DÉBITO", "valor": 100.0, "nf_extraida": "020252443" }
  ],
  "lancamentos_nao_contabilizados": [
    { "tipo_lancamento": "CRÉDITO", "valor": 100.0, "confianca_match": "MÉDIA" }
  ],

  "total_credito": 500.0,
  "total_debito": 100.0,
  "total_rastreado": 400.0,
  "diferenca_nao_localizada": -100.0,

  "observacao": "Encontrados 2 lançamentos a CRÉDITO (R$ 500,00) e 1 lançamentos a DÉBITO (R$ 100,00). Financeiro: R$ 500,00 | Contábil: R$ 400,00",
  "recomendacao": "⚠ Faltam lançamentos a CRÉDITO na contabilidade (R$ 100,00). Verificar 1 lançamento(s) identificado(s)."
}
```

---

## Testes Implementados

Arquivo: [`test_nova_logica.py`](./test_nova_logica.py)

### Testes Executados:

1. ✅ **Extração de NF do histórico**
   - Testa diversos formatos de histórico
   - Valida extração correta do número da NF

2. ✅ **Extração de código de fornecedor**
   - Valida padrões "FORN 004111", "FORNECEDOR 067201"

3. ✅ **Processamento de lançamentos**
   - Identifica corretamente DÉBITO vs CRÉDITO
   - Extrai NF e código do fornecedor
   - Processa informações do razão

### Executar Testes:

```bash
python test_nova_logica.py
```

---

## Impacto no Frontend

O frontend agora recebe na resposta de `analise_detalhada`:

1. **Lançamentos separados por tipo**:
   - `lancamentos_credito`: Títulos gerados
   - `lancamentos_debito`: Baixas/pagamentos

2. **Identificação de problemas**:
   - `lancamentos_nao_contabilizados`: Faltam na contabilidade
   - `lancamentos_orfaos_contabilidade`: Estão na contab mas não no financeiro

3. **Totais detalhados**:
   - `total_credito`: Soma de todos os créditos
   - `total_debito`: Soma de todos os débitos
   - `total_rastreado`: Saldo contábil (crédito - débito)

4. **Detalhes de cada lançamento**:
   - NF extraída do histórico
   - Código do fornecedor
   - Data, lote, filial, centro de custo
   - Valores de débito e crédito separados

---

## Próximos Passos (Frontend)

1. **Atualizar a grid de Análise Detalhada** para exibir:
   - Separação de lançamentos a CRÉDITO e DÉBITO
   - Totais de crédito e débito
   - Identificação visual de lançamentos órfãos

2. **Exibir detalhes dos lançamentos**:
   - Mostrar NF extraída
   - Exibir código do fornecedor do histórico
   - Mostrar filial, centro de custo

3. **Indicadores visuais**:
   - Verde: Conciliado
   - Vermelho: Divergente
   - Amarelo: Lançamentos órfãos ou não contabilizados

---

## Observações Técnicas

- A implementação **não** quebra compatibilidade com código existente
- Todos os campos antigos ainda estão presentes
- Novos campos são **opcionais** e têm valores padrão
- A lógica é **retrocompatível** com análises anteriores

---

## Autor

Implementado em: 2026-01-26
Versão da API: 2.0
