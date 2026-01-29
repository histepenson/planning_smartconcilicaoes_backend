# Implementação de Análise Detalhada de Diferenças

## Visão Geral

Foi implementada uma nova funcionalidade de **análise detalhada de diferenças** que rastreia onde cada valor foi contabilizado no razão geral, permitindo identificar exatamente onde ocorreram as divergências entre financeiro e contabilidade.

## O Que Foi Implementado

### 1. Novos Schemas (schemas/conciliacao_schema.py)

**LancamentoRastreado**
- Representa um lançamento encontrado no razão contábil
- Campos: conta_contabil, data_lancamento, historico, valor, tipo_lancamento, confianca_match, criterio_match

**AnaliseDiferencaDetalhada**
- Análise detalhada de uma diferença por fornecedor
- Campos principais:
  - `codigo_fornecedor`: Código do fornecedor (ex: C00067201)
  - `nome_fornecedor`: Nome do fornecedor
  - `valor_financeiro`: Valor na base financeira
  - `valor_contabilidade`: Valor na base contábil
  - `diferenca`: Diferença calculada
  - `tipo_diferenca`: CONCILIADO | SO_FINANCEIRO | SO_CONTABILIDADE | DIVERGENTE_VALOR
  - `status`: "verde" (conciliado) ou "vermelho" (divergente)
  - `lancamentos_encontrados`: Lista de lançamentos rastreados no razão
  - `total_rastreado`: Total dos valores rastreados
  - `diferenca_nao_localizada`: Valor que não foi possível localizar
  - `observacao`: Descrição da situação
  - `recomendacao`: Ação recomendada

### 2. Ferramenta de Rastreamento (tools/rastreamento.py)

Novo módulo com funções para rastrear lançamentos no razão contábil:

**normalizar_razao_geral()**
- Normaliza o DataFrame do razão contábil geral
- Padroniza nomes de colunas

**buscar_lancamentos_por_codigo()**
- Busca lançamentos no razão por código de fornecedor
- Procura no histórico/descrição dos lançamentos
- Retorna lista de lançamentos encontrados com confiança ALTA

**buscar_lancamentos_por_valor()**
- Busca lançamentos por valor aproximado
- Usa tolerância percentual (padrão: 5%)
- Classifica confiança: ALTA (<1%), MÉDIA (1-3%), BAIXA (>3%)

**rastrear_diferenca()**
- Função principal que rastreia uma diferença
- Tenta primeiro por código, depois por valor
- Retorna resultado completo do rastreamento

**analisar_tipo_diferenca()**
- Classifica o tipo de diferença
- Retorna tupla (tipo_diferenca, status)

### 3. Serviço de Análise Detalhada (services/analise_diferencas_service.py)

**AnaliseDiferencasService**

Classe principal com os métodos:

**processar_analise_detalhada()**
- Processa todas as diferenças do DataFrame completo
- Rastreia cada diferença no razão geral
- Retorna lista ordenada de análises (divergentes primeiro)

**_analisar_registro()**
- Analisa um registro individual
- Chama rastreamento no razão
- Monta análise detalhada completa

**_gerar_observacao()**
- Gera observação descritiva baseada no tipo de diferença
- Mensagens específicas para cada tipo:
  - CONCILIADO: Valores batem
  - SO_FINANCEIRO: Não encontrado na contabilidade
  - SO_CONTABILIDADE: Não há registro no financeiro
  - DIVERGENTE_VALOR: Detalha o excedente ou falta

**gerar_resumo_analise()**
- Gera estatísticas da análise detalhada
- Total conciliados vs divergentes
- Percentual de conciliação
- Distribuição por tipo

### 4. Integração no Serviço de Conciliação (services/conciliacao_service.py)

**Mudanças no método executar()**:

1. Importado `AnaliseDiferencasService`
2. Após calcular diferenças (passo 8), adicionado novo passo:
   - Carrega `base_contabil_geral` (razão completo)
   - Instancia `AnaliseDiferencasService`
   - Processa análise detalhada com rastreamento
   - Gera resumo da análise
3. Adicionado campo `analise_detalhada` no retorno final
4. Tratamento de erros para continuar mesmo se análise falhar

## Tipos de Diferenças Identificadas

### 1. CONCILIADO (Verde)
- Financeiro = Contabilidade
- Diferença < R$ 0,01
- Status: "verde"
- Observação: "Valores conciliam. Financeiro = Contabilidade."

### 2. SO_FINANCEIRO (Vermelho)
- Valor existe apenas no financeiro
- Contabilidade = R$ 0,00
- Status: "vermelho"
- Observação: "Valor de R$ X existe apenas no financeiro. Não foi encontrado lançamento correspondente na contabilidade."
- Rastreamento: Busca no razão se há algum lançamento relacionado

### 3. SO_CONTABILIDADE (Vermelho)
- Valor existe apenas na contabilidade
- Financeiro = R$ 0,00
- Status: "vermelho"
- Observação: "Valor de R$ X existe apenas na contabilidade. Não há registro correspondente no financeiro."
- Rastreamento: Localiza onde foi contabilizado

### 4. DIVERGENTE_VALOR (Vermelho)
- Valores diferentes entre financeiro e contabilidade
- Ambos > R$ 0,01
- Status: "vermelho"
- Observação: Detalha se contabilidade tem excedente ou falta
- Rastreamento: Localiza onde caiu o valor divergente

## Formato de Retorno da API

O endpoint `/conciliacoes/contabil` agora retorna:

```json
{
  "resumo": { ... },
  "diferencas": [ ... ],
  "diferencas_origem_maior": [ ... ],
  "diferencas_contabilidade_maior": [ ... ],
  "analise_detalhada": [
    {
      "codigo_fornecedor": "C00067201",
      "nome_fornecedor": "FORNECEDOR XYZ LTDA",
      "valor_financeiro": 5000.00,
      "valor_contabilidade": 5300.00,
      "diferenca": 300.00,
      "tipo_diferenca": "DIVERGENTE_VALOR",
      "status": "vermelho",
      "lancamentos_encontrados": [
        {
          "conta_contabil": "1.01.01.001",
          "data_lancamento": "2025-01-15",
          "historico": "Lançamento referente ao fornecedor 000672",
          "valor": 5300.00,
          "tipo_lancamento": "DÉBITO",
          "confianca_match": "ALTA",
          "criterio_match": "Código encontrado no histórico: 000672"
        }
      ],
      "total_rastreado": 5300.00,
      "diferenca_nao_localizada": 0.00,
      "observacao": "Divergência de valores. Contabilidade possui R$ 300.00 a mais que o financeiro. Total contábil: R$ 5300.00, Total financeiro: R$ 5000.00.",
      "recomendacao": "Valor contábil totalmente rastreado no razão geral"
    }
  ],
  "observacoes": [ ... ],
  "alertas": [ ... ]
}
```

## Como Funciona o Rastreamento

### Estratégia de Busca

1. **Busca por Código (Prioridade 1)**
   - Extrai código do fornecedor (ex: C00067201 → 000672)
   - Busca no campo histórico/descrição do razão
   - Confiança: ALTA

2. **Busca por Valor (Prioridade 2)**
   - Quando não encontra por código
   - Busca valores próximos com tolerância de 10%
   - Confiança: ALTA (<1%), MÉDIA (1-3%), BAIXA (>3%)

### Critérios de Match

- **Código encontrado no histórico**: Match mais confiável
- **Valor aproximado**: Útil quando código não está explícito
- **Não localizado**: Quando nenhum critério encontra resultado

## Próximos Passos para o Frontend

### Grid de Análise Detalhada

Criar uma nova grid abaixo do resumo com as seguintes colunas:

| Coluna | Descrição | Formatação |
|--------|-----------|------------|
| **Fornecedor** | codigo_fornecedor + nome_fornecedor | Texto |
| **Valor Financeiro** | valor_financeiro | R$ 0.000,00 |
| **Valor Contabilidade** | valor_contabilidade | R$ 0.000,00 |
| **Diferenças** | diferenca | R$ 0.000,00 |
| **Status** | Indicador visual | 🟢 verde / 🔴 vermelho |

### Cores e Estilos

- **Verde (`status: "verde"`)**: Linha inteira com fundo verde claro
- **Vermelho (`status: "vermelho"`)**: Linha inteira com fundo vermelho claro

### Detalhamento (Expandível)

Ao clicar em uma linha divergente, mostrar:

1. **Observação**: Campo `observacao`
2. **Recomendação**: Campo `recomendacao`
3. **Lançamentos Encontrados**: Tabela com:
   - Conta Contábil
   - Data
   - Histórico
   - Valor
   - Confiança do Match

### Exemplo de Interface

```
┌─────────────────────────────────────────────────────────────────────┐
│ RESUMO DA CONCILIAÇÃO                                               │
│ Total Financeiro: R$ 100.000,00                                     │
│ Total Contabilidade: R$ 102.000,00                                  │
│ Diferença: R$ 2.000,00                                              │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ ANÁLISE DETALHADA POR FORNECEDOR                                    │
├──────────────┬────────────┬──────────────┬───────────┬──────────────┤
│ Fornecedor   │ Financeiro │ Contabilidade│ Diferença │ Status       │
├──────────────┼────────────┼──────────────┼───────────┼──────────────┤
│ C00067201    │ 5.000,00   │ 5.300,00     │ 300,00    │ 🔴 Divergente│
│ Fornecedor A │            │              │           │              │
├──────────────┼────────────┼──────────────┼───────────┼──────────────┤
│ C00123401    │ 2.500,00   │ 2.500,00     │ 0,00      │ 🟢 Conciliado│
│ Fornecedor B │            │              │           │              │
└──────────────┴────────────┴──────────────┴───────────┴──────────────┘

▼ Detalhes do Fornecedor C00067201
   Observação: Divergência de valores. Contabilidade possui R$ 300,00
               a mais que o financeiro.

   Lançamentos Encontrados no Razão:
   ┌─────────────┬────────────┬──────────────┬─────────┬────────────┐
   │ Conta       │ Data       │ Histórico    │ Valor   │ Confiança  │
   ├─────────────┼────────────┼──────────────┼─────────┼────────────┤
   │ 1.01.01.001 │ 15/01/2025 │ Lançamento...│ 5.300,00│ ALTA       │
   └─────────────┴────────────┴──────────────┴─────────┴────────────┘
```

## Testes Recomendados

1. **Teste com valores conciliados**: Verificar se aparece verde
2. **Teste com diferença só no financeiro**: Verificar rastreamento
3. **Teste com diferença só na contabilidade**: Verificar origem
4. **Teste com divergência de valores**: Verificar localização do excedente
5. **Teste com razão vazio**: Verificar tratamento de erro
6. **Teste com muitos registros**: Verificar performance

## Logs e Debugging

A implementação inclui logs detalhados:

```
[ANÁLISE DETALHADA] Iniciando processamento
[ANÁLISE DETALHADA] Total de registros a analisar: 150
[RASTREAMENTO] Colunas disponíveis no razão: [...]
[RASTREAMENTO] Encontrados 3 lançamentos para código C00067201
[ANÁLISE DETALHADA] Total de análises geradas: 150
[ANÁLISE DETALHADA] Resumo: {...}
```

## Arquivos Modificados/Criados

### Novos Arquivos
- `tools/rastreamento.py` - Ferramentas de rastreamento
- `services/analise_diferencas_service.py` - Serviço de análise detalhada
- `IMPLEMENTACAO_ANALISE_DETALHADA.md` - Esta documentação

### Arquivos Modificados
- `schemas/conciliacao_schema.py` - Adicionados novos schemas
- `services/conciliacao_service.py` - Integrada análise detalhada

## Observações Importantes

1. **Compatibilidade**: A implementação não quebra o que já funciona
2. **Performance**: Análise detalhada pode ser demorada com muitos registros
3. **Tolerância a Erros**: Se análise detalhada falhar, retorna array vazio
4. **Flexibilidade**: Rastreamento adapta-se a diferentes layouts de razão
5. **Logging**: Todos os passos são logados para debugging

## Melhorias Futuras Sugeridas

1. **Cache**: Cachear razão normalizado para múltiplas consultas
2. **Async**: Processar análise detalhada de forma assíncrona
3. **Filtros**: Permitir filtrar análise por tipo de diferença
4. **Exportação**: Exportar análise detalhada para Excel
5. **Match Inteligente**: Usar NLP para melhorar match por histórico
6. **Visualizações**: Gráficos de distribuição de diferenças
