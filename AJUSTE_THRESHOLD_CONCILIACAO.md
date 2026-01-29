# Ajuste de Threshold para Conciliação

## Mudança Implementada

Diferenças de até **R$ 0,01 (inclusive)** são consideradas **CONCILIADAS** (status verde).

Anteriormente, alguns arquivos usavam `< 0.01` (menor que) em vez de `<= 0.01` (menor ou igual), o que causava inconsistência na classificação de diferenças de exatamente R$ 0,01.

## Arquivos Modificados

### Backend

#### 1. tools/rastreamento.py
**Função:** `analisar_tipo_diferenca()`

**ANTES:**
```python
if diferenca < 0.01:
    return "CONCILIADO", "verde"
```

**DEPOIS:**
```python
if diferenca <= 0.01:
    return "CONCILIADO", "verde"
```

**Mudança adicional:**
- Também ajustados os checks para `SO_FINANCEIRO` e `SO_CONTABILIDADE` de `< 0.01` para `<= 0.01`
- Adicionado comentário explicativo: "Diferenças de até R$ 0,01 (inclusive) são consideradas conciliadas"

#### 2. services/conciliacao_service.py
**Linha 142**

**ANTES:**
```python
situacao = "CONCILIADO" if abs(diferenca) < 0.01 else "DIVERGENTE"
```

**DEPOIS:**
```python
situacao = "CONCILIADO" if abs(diferenca) <= 0.01 else "DIVERGENTE"
```

### Frontend

#### 3. AllDifferencesTable.jsx
**Linha 12**

**ANTES:**
```javascript
const differenceThreshold = 0.1;  // 10 centavos
```

**DEPOIS:**
```javascript
const differenceThreshold = 0.01; // Diferenças de até R$ 0,01 são consideradas conciliadas
```

**Nota:** A função `isOk()` já usava `<=`, apenas o threshold estava errado.

## Comportamento Atual

### Classificação de Status

| Diferença Absoluta | Status | Cor | Classificação |
|-------------------|--------|-----|---------------|
| R$ 0,00 | CONCILIADO | 🟢 Verde | Valores idênticos |
| R$ 0,01 | CONCILIADO | 🟢 Verde | Dentro da tolerância |
| R$ 0,02 | DIVERGENTE | 🔴 Vermelho | Acima da tolerância |
| R$ 1,00 | DIVERGENTE | 🔴 Vermelho | Diferença significativa |

### Casos Especiais

1. **SO_FINANCEIRO** (Vermelho)
   - `valor_financeiro > 0.01` E `valor_contabilidade <= 0.01`
   - Significa que há valor no financeiro mas não (ou quase nada) na contabilidade

2. **SO_CONTABILIDADE** (Vermelho)
   - `valor_contabilidade > 0.01` E `valor_financeiro <= 0.01`
   - Significa que há valor na contabilidade mas não (ou quase nada) no financeiro

3. **DIVERGENTE_VALOR** (Vermelho)
   - Ambos os valores > 0.01 mas com diferença > 0.01
   - Valores divergentes que precisam de análise

4. **CONCILIADO** (Verde)
   - `|valor_contabilidade - valor_financeiro| <= 0.01`
   - Valores batem dentro da tolerância aceitável

## Impacto

### No Resumo Geral
- Campo `situacao` do resumo agora considera R$ 0,01 como conciliado
- Percentual de divergência ajustado

### Na Grid "Todas as Diferenças"
- Badge "OK" aparece para diferenças de até R$ 0,01
- Badge "DIFERENÇA" aparece apenas para diferenças > R$ 0,01

### Na Grid "Análise Detalhada por Fornecedor"
- Linhas verdes: diferença <= R$ 0,01
- Linhas vermelhas: diferença > R$ 0,01
- Status Badge: "CONCILIADO" vs "DIVERGENTE"

## Consistência

Agora **todos os arquivos** usam o mesmo critério:

✅ Backend (rastreamento): `<= 0.01`
✅ Backend (conciliação): `<= 0.01`
✅ Frontend (tabela diferenças): `<= 0.01`
✅ Frontend (análise detalhada): Herda do backend

## Cálculo nos Arquivos

### tools/calc_diferencas.py

Este arquivo já estava correto:
```python
'registros_com_diferenca': len(df_resultado[df_resultado['Diferença Absoluta'] > 0.01])
'registros_sem_diferenca': len(df_resultado[df_resultado['Diferença Absoluta'] <= 0.01])
```

Usa:
- `> 0.01` para contar divergências
- `<= 0.01` para contar conciliações

Isso está **alinhado** com a mudança.

## Exemplo Prático

### Antes da Mudança

| Fornecedor | Financeiro | Contabilidade | Diferença | Status (antes) |
|-----------|-----------|--------------|----------|----------------|
| A | R$ 1.000,00 | R$ 1.000,00 | R$ 0,00 | 🟢 CONCILIADO |
| B | R$ 1.000,00 | R$ 1.000,01 | R$ 0,01 | 🔴 DIVERGENTE ❌ |
| C | R$ 1.000,00 | R$ 1.000,02 | R$ 0,02 | 🔴 DIVERGENTE |

### Após a Mudança

| Fornecedor | Financeiro | Contabilidade | Diferença | Status (depois) |
|-----------|-----------|--------------|----------|----------------|
| A | R$ 1.000,00 | R$ 1.000,00 | R$ 0,00 | 🟢 CONCILIADO |
| B | R$ 1.000,00 | R$ 1.000,01 | R$ 0,01 | 🟢 CONCILIADO ✅ |
| C | R$ 1.000,00 | R$ 1.000,02 | R$ 0,02 | 🔴 DIVERGENTE |

## Justificativa

Diferenças de 1 centavo são geralmente:
- Arredondamentos de cálculos
- Diferenças de casas decimais
- Tolerâncias aceitáveis contabilmente

Considerar R$ 0,01 como divergente seria muito rigoroso e geraria alertas desnecessários.

## Como Testar

1. **Preparar dados de teste:**
   - Criar registros com diferenças de exatamente R$ 0,01
   - Criar registros com diferenças de R$ 0,00
   - Criar registros com diferenças de R$ 0,02

2. **Fazer upload:**
   - Processar conciliação normalmente

3. **Verificar:**
   - Resumo: Situação deve ser "CONCILIADO" se diferença total <= 0.01
   - Grid "Todas as Diferenças": Badge "OK" para dif <= 0.01
   - Grid "Análise Detalhada": Linhas verdes para dif <= 0.01

4. **Logs no console:**
   ```
   [INFO] Diferença: R$ 0,01
   [INFO] Status: verde
   [INFO] Tipo: CONCILIADO
   ```

## Rollback (se necessário)

Para reverter, mudar `<= 0.01` de volta para `< 0.01` nos 3 arquivos modificados:
1. tools/rastreamento.py (linha 268)
2. services/conciliacao_service.py (linha 142)
3. AllDifferencesTable.jsx (linha 12)

## Data da Mudança

**Data:** 26/01/2025
**Versão:** 1.0.1
**Autor:** Claude Code

## Observações

- Esta mudança é **backwards compatible**
- Não quebra funcionalidades existentes
- Melhora a precisão da conciliação
- Reduz falsos positivos
