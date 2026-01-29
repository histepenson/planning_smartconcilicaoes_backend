# Estrutura de Dados: Financeiro vs Contabilidade

## Objetivo

Documentar a estrutura dos dados financeiros e contábeis para garantir matching correto na análise detalhada.

---

## Relatório Financeiro (Origem)

### Colunas Disponíveis:

1. **Codigo_Li** - Código do cliente/fornecedor
2. **Nome do Cliente** - Nome completo
3. **Prf-NumeroParcela** - Prefixo e número da parcela (pode conter NF)
4. **TP** - Tipo do título
5. **Natureza** - Natureza da operação
6. **Data de Emissao** - Data de emissão do título
7. **Venc toTitulo** - Vencimento do título
8. **Venc toReal** - Vencimento real
9. **Venc toOrig** - Vencimento original
10. **Bco St** - Banco/Status
11. **Valor Original** - Valor original do título
12. **Tit Vencidos Valor Atual** - Valor atual dos títulos vencidos
13. **Tit Vencidos Valor Corrigido** - Valor corrigido dos vencidos
14. **Titulos a Vencer Valor Atual** - Valor dos títulos a vencer
15. **NumBanco** - Número do banco
16. **Vlr juros supermanencia** - Juros
17. **DiasAtraso** - Dias de atraso
18. **Historico** - Histórico/observações do título
19. **(Vencidos+Vencer)** - Valor total (vencidos + a vencer)

### Formato do Código do Cliente/Fornecedor:

```
Exemplo: 000672-01-A A DANTAS RIBEIRO
         ^^^^^^ ^^ ^^^^^^^^^^^^^^^^^^^
         código loja  nome

Normalizado: C00067201
             ^^^^^^^^^^
             C + código(6) + loja(2)
```

### Processamento Atual:

1. Lê colunas do Excel
2. Normaliza nomes: lowercase, substitui espaços por `_`
3. Extrai código do fornecedor de "Codigo_Li" ou "codigo_lj_nome_do_cliente"
4. Agrupa por código do fornecedor
5. Soma valores por fornecedor

---

## Razão Contábil (Destino)

### Colunas do Razão (ctbr400.xlsx):

1. **Conta Contábil** - Conta sendo conciliada (ex: 2.01.01.001)
2. **Data** - Data do lançamento
3. **Lote** - Número do lote
4. **Histórico** - Contém CFOP, NF, descrição
5. **Filial Origem** - Código da filial
6. **Centro de Custo** - Centro de custo
7. **Item Contábil** - Código do fornecedor (ex: C00067201)
8. **Débito** - Valor a débito
9. **Crédito** - Valor a crédito

### Formato do Histórico Contábil:

```
Exemplo 1: CFOP 1933 NF. 020252443 - RODA MAIS RENO | COMP. 1
           ^^^^^^^^^ ^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^   ^^^^^^^^
           CFOP      NF               Nome              Complemento

Exemplo 2: BX.PAG. NF354753007 FORN 004111 - FUNDAC | COMP. DV
           ^^^^^^^ ^^^^^^^^^^^^ ^^^^^^^^^^^   ^^^^^^   ^^^^^^^^^
           Operação NF          Código Forn   Nome     Complemento
```

### Processamento Atual:

1. Filtra razão pela **conta contábil** sendo conciliada
2. Normaliza colunas
3. Identifica débito e crédito
4. Extrai NF do histórico
5. Extrai código do fornecedor do histórico
6. Busca lançamentos por "Item Contábil" ou pelo histórico

---

## Matching: Financeiro ↔ Contabilidade

### Estratégia de Matching:

```
FINANCEIRO (Títulos a Pagar)          CONTABILIDADE (Razão)
├─ Código: C00067201                  ├─ Item Contábil: C00067201
├─ Nome: A DANTAS RIBEIRO             ├─ Histórico: "... FORN 004111 ..."
├─ Valor Total: R$ 500,00             ├─ Crédito: R$ 500,00 (compra)
├─ Prf-NumeroParcela: NF 123456       ├─ Débito: R$ 200,00 (baixa)
└─ Historico: "Compra material"       └─ NF extraída: 123456
```

### Critérios de Match:

1. **Match por Código (ALTA confiança)**
   - Financeiro: `Codigo_Li` → `C00067201`
   - Contabilidade: `Item Contábil` → `C00067201`

2. **Match por NF (ALTA confiança)**
   - Financeiro: `Prf-NumeroParcela` → pode conter NF
   - Contabilidade: Extraído do `Histórico` → `NF. 020252443`

3. **Match por Valor (MÉDIA confiança)**
   - Tolerância de 10%
   - Usado quando código não encontrado diretamente

4. **Match por Data (COMPLEMENTAR)**
   - Financeiro: `Data de Emissao` ou `Venc toReal`
   - Contabilidade: `Data`

---

## Lógica de Conciliação Implementada

### Regra Contábil:

```
1. Título Gerado (Compra)     → Lançamento a CRÉDITO na contabilidade
2. Título Pago (Baixa)        → Lançamento a DÉBITO na contabilidade
3. Saldo Contábil             = Total CRÉDITO - Total DÉBITO
```

### Cenários de Análise:

#### Cenário 1: Valores Conciliam ✓

```
Financeiro:     R$ 500,00 (títulos a pagar)
Contabilidade:  R$ 500,00 (crédito - débito)
Resultado:      CONCILIADO (verde)
```

#### Cenário 2: Financeiro > Contabilidade ⚠

```
Financeiro:     R$ 500,00
Contabilidade:  R$ 400,00
Diferença:      R$ 100,00

Ação:
- Buscar lançamento a CRÉDITO de R$ 100 que falta
- Classificar como "Não Contabilizado"
- Verificar se existe NF correspondente
```

#### Cenário 3: Contabilidade > Financeiro ⚠

```
Financeiro:     R$ 400,00
Contabilidade:  R$ 500,00
Diferença:      R$ 100,00

Ação:
- Identificar lançamento a CRÉDITO de R$ 100 órfão
- Classificar como "Lançamento Órfão"
- Verificar se título foi pago e não consta mais no financeiro
```

---

## Melhorias Futuras Possíveis

### 1. Extração de NF do Financeiro

Atualmente apenas somamos valores. Poderíamos:

```python
# Extrair NF de "Prf-NumeroParcela" ou "Historico"
df["nf_financeiro"] = extrair_nf_do_campo(df["Prf-NumeroParcela"])
```

### 2. Matching Detalhado por Título

Em vez de agrupar tudo por fornecedor, poderíamos:

```python
# Manter detalhes individuais de cada título
for titulo in titulos_financeiro:
    # Buscar lançamento correspondente na contabilidade
    # Matching por: código + NF + valor + data
```

### 3. Histórico do Financeiro no Matching

```python
# Usar campo "Historico" do financeiro para melhorar matching
if "NF" in titulo["Historico"]:
    nf_financeiro = extrair_nf(titulo["Historico"])
    # Comparar com NF da contabilidade
```

---

## Fluxo Completo Atual

```
1. ENTRADA
   ├─ Financeiro (Excel com 19 colunas)
   │  └─ Agrupado por código do fornecedor
   │     └─ Soma valores totais
   │
   └─ Razão Contábil (Excel com todas as contas)
      └─ Filtrado pela conta sendo conciliada
         └─ Separado por DÉBITO e CRÉDITO

2. PROCESSAMENTO
   ├─ Normalização dos dados
   ├─ Cálculo de diferenças por fornecedor
   └─ Para cada fornecedor com diferença:
      ├─ Filtrar razão pela conta contábil
      ├─ Buscar lançamentos do fornecedor
      ├─ Separar DÉBITO e CRÉDITO
      ├─ Calcular saldo contábil
      └─ Identificar lançamentos órfãos ou faltantes

3. SAÍDA (Análise Detalhada)
   ├─ Código do fornecedor
   ├─ Valores (financeiro, contabilidade, diferença)
   ├─ Lançamentos a CRÉDITO (compras)
   ├─ Lançamentos a DÉBITO (baixas)
   ├─ Lançamentos não contabilizados
   ├─ Lançamentos órfãos
   └─ Recomendações
```

---

## Exemplo Completo

### Dados de Entrada:

**Financeiro:**
```
Codigo_Li: 000672-01
Nome: A DANTAS RIBEIRO
Prf-NumeroParcela: NF 123456
(Vencidos+Vencer): 500,00
```

**Razão Contábil (Conta 2.01.01.001):**
```
Item Contábil: C00067201
Histórico: "CFOP 1933 NF. 123456 - A DANTAS"
Crédito: 500,00
Débito: 0,00
```

### Processamento:

1. **Normalização:**
   - Financeiro: `C00067201` → R$ 500,00
   - Contabilidade: `C00067201` → Crédito R$ 500,00 - Débito R$ 0,00 = R$ 500,00

2. **Matching:**
   - Código: ✓ Match
   - Valor: ✓ Match
   - NF: ✓ Match (123456)

3. **Resultado:**
```json
{
  "codigo_fornecedor": "C00067201",
  "nome_fornecedor": "A DANTAS RIBEIRO",
  "valor_financeiro": 500.0,
  "valor_contabilidade": 500.0,
  "diferenca": 0.0,
  "status": "verde",
  "lancamentos_credito": [
    {
      "tipo_lancamento": "CRÉDITO",
      "credito": 500.0,
      "nf_extraida": "123456",
      "historico": "CFOP 1933 NF. 123456 - A DANTAS"
    }
  ],
  "total_credito": 500.0,
  "total_debito": 0.0,
  "recomendacao": "✓ Valores conciliam. Financeiro = Contabilidade."
}
```

---

## Conclusão

A estrutura atual está correta e funcional:

1. ✅ Financeiro agrupado por código do fornecedor
2. ✅ Razão filtrado pela conta contábil sendo conciliada
3. ✅ Matching por código do fornecedor
4. ✅ Separação de DÉBITO e CRÉDITO
5. ✅ Identificação de lançamentos órfãos e não contabilizados
6. ✅ Extração de NF do histórico contábil

**Melhorias futuras** poderiam incluir:
- Extração de NF do campo "Prf-NumeroParcela" do financeiro
- Matching individual por título (não agrupado)
- Uso do campo "Historico" do financeiro para enriquecer a análise
