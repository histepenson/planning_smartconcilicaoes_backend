# Ajuste: Filtro de Conta Contábil no Razão Geral

## Problema Identificado

A análise detalhada estava processando **TODOS os lançamentos do razão geral**, incluindo lançamentos de **todas as contas contábeis**, quando deveria processar apenas os lançamentos da **conta específica** que está sendo conciliada.

### Exemplo do Problema:

```
Razão Geral (ctbr400.xlsx):
- Conta 1.01.01.001 (Caixa): 50 lançamentos
- Conta 2.01.01.001 (Fornecedores): 30 lançamentos  <- Conta sendo conciliada
- Conta 3.01.01.001 (Vendas): 40 lançamentos

❌ ANTES: Processava todos os 120 lançamentos
✅ AGORA: Processa apenas os 30 lançamentos da conta 2.01.01.001
```

---

## Solução Implementada

### 1. Adição do Método de Filtro

**Arquivo**: `services/conciliacao_service.py`

```python
def _filtrar_razao_por_conta(self, df_razao_geral: pd.DataFrame, conta_contabil: str) -> pd.DataFrame:
    """
    Filtra o razão geral pela conta contábil que está sendo conciliada.

    Exemplo:
    --------
    Entrada:
    - df_razao_geral: 120 lançamentos de várias contas
    - conta_contabil: "2.01.01.001"

    Saída:
    - DataFrame com apenas 30 lançamentos da conta 2.01.01.001
    """
```

**Como funciona:**

1. Identifica a coluna de "Conta Contábil" no razão geral
2. Filtra apenas os registros da conta que está sendo conciliada
3. Preserva as colunas originais do DataFrame
4. Registra logs detalhados do processo de filtragem

---

### 2. Integração no Processo de Conciliação

**Antes:**
```python
# Converter base_contabil_geral para DataFrame
df_razao_geral = pd.DataFrame(request.base_contabil_geral.registros)

# Processar análise detalhada (ERRADO - processa todas as contas)
analise_detalhada = analise_service.processar_analise_detalhada(
    df_completo=df_completo,
    df_razao_geral=df_razao_geral  # ❌ Todas as contas
)
```

**Depois:**
```python
# Converter base_contabil_geral para DataFrame
df_razao_geral = pd.DataFrame(request.base_contabil_geral.registros)
logger.info(f"[INFO] Razão geral carregado: {len(df_razao_geral)} registros (TODAS as contas)")

# Filtrar apenas pela conta contábil que está sendo conciliada
conta_contabil_conciliada = request.base_contabil_filtrada.conta_contabil
logger.info(f"[INFO] Conta contábil sendo conciliada: {conta_contabil_conciliada}")

df_razao_filtrado = self._filtrar_razao_por_conta(df_razao_geral, conta_contabil_conciliada)
logger.info(f"[INFO] Razão filtrado: {len(df_razao_filtrado)} registros")

# Processar análise detalhada com razão FILTRADO
analise_detalhada = analise_service.processar_analise_detalhada(
    df_completo=df_completo,
    df_razao_geral=df_razao_filtrado  # ✅ Apenas a conta específica
)
```

---

## Teste Implementado

**Arquivo**: `test_filtro_conta.py`

### Cenário de Teste:

```python
# Razão com 5 lançamentos de 4 contas diferentes
dados_razao = [
    {'Conta Contábil': '1.01.01.001', 'Crédito': 100.0},  # Conta 1
    {'Conta Contábil': '2.01.01.001', 'Crédito': 500.0},  # Conta 2 (alvo)
    {'Conta Contábil': '2.01.01.001', 'Débito': 200.0},   # Conta 2 (alvo)
    {'Conta Contábil': '3.01.01.001', 'Débito': 300.0},   # Conta 3
    {'Conta Contábil': '2.01.01.001', 'Crédito': 150.0}   # Conta 2 (alvo)
]
```

### Resultado do Teste:

```
Razão Geral COMPLETO: 5 registros

Contas no razão:
  - 1.01.01.001: 1 lançamento(s)
  - 2.01.01.001: 3 lançamento(s)  ✅
  - 3.01.01.001: 1 lançamento(s)

Filtrando pela conta: 2.01.01.001

Resultado:
  Total de registros filtrados: 3  ✅

Lançamentos encontrados:
  1. CRÉDITO R$ 500.00 - CFOP 1933 NF. 456 FORN 002
  2. DÉBITO  R$ 200.00 - BX.PAG. NF456 FORN 002
  3. CRÉDITO R$ 150.00 - CFOP 1933 NF. 999 FORN 004

Totais para a conta 2.01.01.001:
  Total DÉBITO:  R$ 200.00
  Total CRÉDITO: R$ 650.00
  Saldo (Crédito - Débito): R$ 450.00  ✅

[OK] Filtro funcionando corretamente!
```

---

## Logs de Execução

Durante a execução da conciliação, os logs agora mostram:

```
[INFO] Razão geral carregado: 1200 registros (TODAS as contas)
[INFO] Conta contábil sendo conciliada: 2.01.01.001
[FILTRO] Coluna de conta contábil identificada: 'Conta Contábil'
[FILTRO] Total antes do filtro: 1200 registros
[FILTRO] Total após filtro (conta '2.01.01.001'): 350 registros
[INFO] Razão filtrado pela conta 2.01.01.001: 350 registros
[OK] Análise detalhada concluída: 45 registros processados
```

---

## Impacto na Análise Detalhada

### Antes (INCORRETO):
- Buscava lançamentos do fornecedor em **TODAS as contas**
- Poderia encontrar lançamentos do mesmo fornecedor em outras contas (ex: Caixa, Bancos)
- Resultados **não faziam sentido** para conciliação de Fornecedores

### Depois (CORRETO):
- Busca lançamentos do fornecedor **APENAS na conta sendo conciliada**
- Ex: Se conciliando "2.01.01.001 - Fornecedores", só procura nessa conta
- Resultados **fazem sentido contábil**

---

## Exemplo Prático

### Situação Real:

**Conciliando Conta**: 2.01.01.001 - Fornecedores a Pagar

**Razão Geral (antes do filtro):**
```
Conta 1.01.01.001 (Caixa):
- DÉBITO  R$ 500,00 - PAG. FORN 004111 (pagamento)
- DÉBITO  R$ 300,00 - PAG. FORN 067201 (pagamento)

Conta 2.01.01.001 (Fornecedores):
- CRÉDITO R$ 500,00 - NF 456 FORN 004111 (compra)
- DÉBITO  R$ 500,00 - BX.PAG. NF 456 FORN 004111 (baixa)
- CRÉDITO R$ 300,00 - NF 789 FORN 067201 (compra)

Conta 3.01.01.001 (Vendas):
- CRÉDITO R$ 1.000,00 - VENDA NF 999
```

**Razão Filtrado (após filtro):**
```
Conta 2.01.01.001 (Fornecedores):  ✅ Apenas essa conta
- CRÉDITO R$ 500,00 - NF 456 FORN 004111
- DÉBITO  R$ 500,00 - BX.PAG. NF 456 FORN 004111
- CRÉDITO R$ 300,00 - NF 789 FORN 067201
```

**Análise Detalhada para Fornecedor 004111:**
```json
{
  "codigo_fornecedor": "004111",
  "lancamentos_credito": [
    {
      "conta_contabil": "2.01.01.001",
      "credito": 500.0,
      "historico": "NF 456 FORN 004111"
    }
  ],
  "lancamentos_debito": [
    {
      "conta_contabil": "2.01.01.001",
      "debito": 500.0,
      "historico": "BX.PAG. NF 456 FORN 004111"
    }
  ],
  "total_credito": 500.0,
  "total_debito": 500.0,
  "total_rastreado": 0.0,
  "status": "verde",
  "recomendacao": "✓ Valores conciliam. Financeiro = Contabilidade."
}
```

---

## Arquivos Modificados

1. **`services/conciliacao_service.py`**
   - Adição do método `_filtrar_razao_por_conta()`
   - Integração do filtro no processo de análise detalhada

2. **`test_filtro_conta.py`** (NOVO)
   - Teste unitário do filtro de conta contábil

---

## Como Executar o Teste

```bash
python test_filtro_conta.py
```

Espera-se ver:
- ✅ 3 lançamentos filtrados (de 5 totais)
- ✅ Total CRÉDITO: R$ 650,00
- ✅ Total DÉBITO: R$ 200,00
- ✅ Saldo: R$ 450,00

---

## Benefícios

1. **Precisão**: Análise detalhada agora processa apenas lançamentos relevantes
2. **Performance**: Redução significativa no volume de dados processados
3. **Lógica Correta**: Matching entre financeiro e contabilidade faz sentido contábil
4. **Rastreabilidade**: Logs detalhados do processo de filtragem

---

## Data de Implementação

**Data**: 2026-01-26
**Versão**: 2.1
