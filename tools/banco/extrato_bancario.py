"""
Modulo de normalizacao de Extrato Bancario (FINR470).

Processa planilha de extrato bancario extraindo:
- Data do movimento
- Documento (prefixo + numero)
- Entradas e saidas
- Descricao

Layout esperado FINR470:
BANCO,AGENCIA,CONTA,SALDO INICIAL,DATA,OPERACAO,DOCUMENTO,PREFIXO/TITULO,
ENTRADAS,SAIDAS,SALDO ATUAL,CONCILIADOS,DESCRICAO,NAO CONCILIADOS,CONCILIADOS,TOTAL
"""

import pandas as pd
import re
import logging
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# FUNCOES DE NORMALIZACAO
# =============================================================================

def normalizar_nome_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza os nomes das colunas de um DataFrame.

    Transformacoes aplicadas:
    - Remove acentos
    - Converte para minusculas
    - Remove quebras de linha
    - Substitui caracteres especiais por underscore
    - Remove underscores duplicados e nas extremidades
    """
    import unicodedata
    df = df.copy()

    # Primeiro, remover acentos
    def remove_acentos(s):
        return ''.join(
            c for c in unicodedata.normalize('NFD', str(s))
            if unicodedata.category(c) != 'Mn'
        )

    df.columns = [remove_acentos(col) for col in df.columns]

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[\r\n]+", "", regex=True)
        .str.replace(r"[^a-z0-9_]+", "_", regex=True)
        .str.replace(" ", "_")
        .str.replace("-", "_")
        .str.replace(r"_+", "_", regex=True)
        .str.strip("_")
    )
    return df


def parse_numero_brasileiro(valor: Any) -> float:
    """
    Converte numeros em formato brasileiro para float.

    Formatos suportados:
    - 1.234.567,89 (BR com milhar)
    - 1234,89 (BR sem milhar)
    - (1.234,89) (negativo por parenteses)
    - 1234,89- (negativo por sufixo)
    - -1234,89 (negativo por prefixo)
    - R$ 1.234,89 (com simbolo de moeda)
    """
    if pd.isna(valor):
        return 0.0

    if isinstance(valor, (int, float)):
        return float(valor)

    s = str(valor).strip()
    if not s:
        return 0.0

    # Remover espacos e simbolos comuns
    s = s.replace("\u00a0", "").replace(" ", "")

    # Remover R$ e outros prefixos de moeda
    s = s.replace("R$", "").replace("r$", "").strip()

    # Detectar negativo
    negativo = False
    if s.startswith("(") and s.endswith(")"):
        negativo = True
        s = s[1:-1]
    if s.endswith("-"):
        negativo = True
        s = s[:-1]
    if s.startswith("-"):
        negativo = True
        s = s[1:]

    # Remover caracteres nao numericos (exceto , . -)
    s = re.sub(r"[^0-9,\.\-]", "", s)

    if not s:
        return 0.0

    # Converter formato BR para formato internacional
    # Detectar se e formato brasileiro (1.234,56) ou internacional (1,234.56)
    if "," in s and "." in s:
        # Se a virgula vem depois do ponto, e formato BR
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            # Formato internacional
            s = s.replace(",", "")
    elif "," in s:
        # Apenas virgula - formato BR (1234,56)
        s = s.replace(",", ".")
    elif s.count(".") > 1:
        # Multiplos pontos - separador de milhar
        s = s.replace(".", "")

    try:
        valor_float = float(s)
        if negativo:
            valor_float = -valor_float
        return valor_float
    except Exception:
        return 0.0


def extrair_prefixo_numero(prefixo_titulo: str) -> Tuple[str, str]:
    """
    Extrai prefixo e numero do campo PREFIXO/TITULO.

    Formatos esperados:
    - RA -01120253
    - DV -127112025
    - FT -101100848
    - BOL-501819069
    - NF9-000034395

    Returns:
        Tupla (prefixo, numero) normalizados
    """
    if pd.isna(prefixo_titulo) or not str(prefixo_titulo).strip():
        return "", ""

    texto = str(prefixo_titulo).strip().upper()

    # Remover espacos extras e normalizar separadores
    texto = re.sub(r"\s+", "", texto)  # Remove todos os espacos
    texto = texto.replace("/", "-")

    # Tentar separar por hifen
    if "-" in texto:
        partes = texto.split("-", 1)
        prefixo = partes[0].strip()
        numero_raw = partes[1].strip() if len(partes) > 1 else ""
    else:
        # Tenta extrair letras iniciais como prefixo
        match = re.match(r"^([A-Z]+)(\d+)$", texto)
        if match:
            prefixo = match.group(1)
            numero_raw = match.group(2)
        else:
            prefixo = ""
            numero_raw = texto

    # Normalizar numero: remover zeros a esquerda
    numero = re.sub(r"^0+", "", numero_raw) or "0"

    return prefixo, numero


def formatar_data(data: Any) -> str:
    """Formata data para string padrao DD/MM/YYYY."""
    from datetime import datetime, timedelta

    if pd.isna(data):
        return ""

    try:
        # Se for numero (serial do Excel), converter
        if isinstance(data, (int, float)):
            # Excel usa epoch 30/12/1899
            # Numeros grandes (> 1000) sao provavelmente serial do Excel
            if data > 1000:
                base_excel = datetime(1899, 12, 30)
                data_dt = base_excel + timedelta(days=int(data))
                return data_dt.strftime("%d/%m/%Y")
            else:
                return str(int(data))

        if isinstance(data, str):
            # Verificar se e numero em formato string
            try:
                num = float(data)
                if num > 1000:
                    base_excel = datetime(1899, 12, 30)
                    data_dt = base_excel + timedelta(days=int(num))
                    return data_dt.strftime("%d/%m/%Y")
            except ValueError:
                pass

            # Tentar converter string para datetime
            data_dt = pd.to_datetime(data, dayfirst=True, errors="coerce")
            if pd.isna(data_dt):
                return str(data).strip()
            return data_dt.strftime("%d/%m/%Y")
        else:
            data_dt = pd.to_datetime(data, errors="coerce")
            if pd.isna(data_dt):
                return str(data).strip()
            return data_dt.strftime("%d/%m/%Y")
    except Exception:
        return str(data).strip()


def obter_coluna(df: pd.DataFrame, possiveis: list) -> Optional[str]:
    """Busca a primeira coluna existente de uma lista de possibilidades."""
    for col in possiveis:
        if col in df.columns:
            return col
    # Tentar busca parcial (substring)
    for col in possiveis:
        for df_col in df.columns:
            if col in df_col:
                return df_col
    return None


# =============================================================================
# FUNCAO PRINCIPAL
# =============================================================================

def normalizar_extrato_bancario(entrada: Any) -> pd.DataFrame:
    """
    Normaliza relatorio de Extrato Bancario (FINR470).

    Layout esperado:
    BANCO,AGENCIA,CONTA,SALDO INICIAL,DATA,OPERACAO,DOCUMENTO,PREFIXO/TITULO,
    ENTRADAS,SAIDAS,SALDO ATUAL,CONCILIADOS,DESCRICAO,...

    Retorna DataFrame com colunas:
    - data: Data do movimento
    - documento: Documento original
    - prefixo: Prefixo extraido (RA, DV, FT, BOL, NF, etc)
    - numero: Numero sem zeros a esquerda
    - chave_documento: Chave normalizada (PREFIXO_NUMERO)
    - descricao: Descricao do movimento
    - entrada: Valor de entrada
    - saida: Valor de saida
    - valor: Valor (positivo=entrada, negativo=saida)
    - tipo: ENTRADA ou SAIDA
    - saldo_atual: Saldo apos movimento

    Args:
        entrada: DataFrame ou caminho para arquivo Excel

    Returns:
        DataFrame normalizado com movimentos do extrato
    """
    logger.info("[EXTRATO BANCARIO] Iniciando normalizacao")

    # ==========================
    # 1. CARREGAR DATAFRAME
    # ==========================
    if isinstance(entrada, pd.DataFrame):
        df = entrada.copy()
    elif isinstance(entrada, str):
        df = pd.read_excel(entrada)
    else:
        raise ValueError("entrada deve ser DataFrame ou caminho de arquivo")

    logger.info(f"[EXTRATO BANCARIO] Registros lidos: {len(df)}")
    logger.info(f"[EXTRATO BANCARIO] Colunas originais: {list(df.columns)}")

    # ==========================
    # 2. NORMALIZAR COLUNAS
    # ==========================
    df = normalizar_nome_colunas(df)
    logger.info(f"[EXTRATO BANCARIO] Colunas normalizadas: {list(df.columns)}")

    # ==========================
    # 3. MAPEAR COLUNAS
    # ==========================
    col_data = obter_coluna(df, ["data", "dt", "data_movimento"])
    col_documento = obter_coluna(df, ["documento", "doc", "num_documento"])
    col_prefixo_titulo = obter_coluna(df, ["prefixo_titulo", "prefixo", "titulo"])
    col_entradas = obter_coluna(df, ["entradas", "entrada", "credito", "creditos"])
    col_saidas = obter_coluna(df, ["saidas", "saida", "debito", "debitos"])
    col_saldo = obter_coluna(df, ["saldo_atual", "saldo", "saldo_final"])
    col_descricao = obter_coluna(df, ["descricao", "historico", "desc"])

    # Log das colunas encontradas
    logger.info(f"[EXTRATO BANCARIO] Coluna DATA: {col_data}")
    logger.info(f"[EXTRATO BANCARIO] Coluna ENTRADAS: {col_entradas}")
    logger.info(f"[EXTRATO BANCARIO] Coluna SAIDAS: {col_saidas}")

    # Debug: mostrar valores brutos das colunas de valores
    if col_entradas:
        logger.info(f"[EXTRATO BANCARIO] Tipos na coluna ENTRADAS: {df[col_entradas].apply(type).value_counts().to_dict()}")
        logger.info(f"[EXTRATO BANCARIO] Valores brutos ENTRADAS (10 primeiros): {df[col_entradas].head(10).tolist()}")
    if col_saidas:
        logger.info(f"[EXTRATO BANCARIO] Tipos na coluna SAIDAS: {df[col_saidas].apply(type).value_counts().to_dict()}")
        logger.info(f"[EXTRATO BANCARIO] Valores brutos SAIDAS (10 primeiros): {df[col_saidas].head(10).tolist()}")

    # Validar colunas obrigatorias
    if not col_data:
        raise ValueError(f"Coluna de DATA nao encontrada. Colunas: {list(df.columns)}")
    if not col_prefixo_titulo and not col_documento:
        raise ValueError(f"Coluna de PREFIXO/TITULO ou DOCUMENTO nao encontrada. Colunas: {list(df.columns)}")

    # ==========================
    # 4. PROCESSAR DADOS
    # ==========================
    df_norm = pd.DataFrame()

    # Data
    df_norm["data"] = df[col_data].apply(formatar_data)

    # Documento original
    if col_documento:
        df_norm["documento"] = df[col_documento].astype(str).str.strip()
    else:
        df_norm["documento"] = ""

    # Prefixo e numero do PREFIXO/TITULO
    if col_prefixo_titulo:
        prefixo_numero = df[col_prefixo_titulo].apply(extrair_prefixo_numero)
        df_norm["prefixo"] = prefixo_numero.apply(lambda x: x[0])
        df_norm["numero"] = prefixo_numero.apply(lambda x: x[1])
    else:
        # Tentar extrair do documento
        prefixo_numero = df_norm["documento"].apply(extrair_prefixo_numero)
        df_norm["prefixo"] = prefixo_numero.apply(lambda x: x[0])
        df_norm["numero"] = prefixo_numero.apply(lambda x: x[1])

    # Chave de documento normalizada para matching
    df_norm["chave_documento"] = df_norm["prefixo"] + "_" + df_norm["numero"]

    # Descricao
    if col_descricao:
        df_norm["descricao"] = df[col_descricao].astype(str).str.strip()
    else:
        df_norm["descricao"] = ""

    # Valores de entrada e saida
    if col_entradas:
        df_norm["entrada"] = df[col_entradas].apply(parse_numero_brasileiro)
    else:
        df_norm["entrada"] = 0.0

    if col_saidas:
        df_norm["saida"] = df[col_saidas].apply(parse_numero_brasileiro)
    else:
        df_norm["saida"] = 0.0

    # Valor liquido (positivo = entrada, negativo = saida)
    # Entrada no extrato = Debito na conta Banco = valor positivo
    # Saida no extrato = Credito na conta Banco = valor negativo
    df_norm["valor"] = df_norm["entrada"] - df_norm["saida"]

    # Tipo de movimento
    df_norm["tipo"] = "ENTRADA"
    df_norm.loc[df_norm["saida"] > 0, "tipo"] = "SAIDA"

    # Saldo atual
    if col_saldo:
        df_norm["saldo_atual"] = df[col_saldo].apply(parse_numero_brasileiro)
    else:
        df_norm["saldo_atual"] = 0.0

    # ==========================
    # 5. LIMPAR REGISTROS
    # ==========================
    # Remover registros sem movimento (entrada = 0 e saida = 0)
    df_norm = df_norm[(df_norm["entrada"] != 0) | (df_norm["saida"] != 0)].copy()

    # Para registros sem chave de documento valida, criar chave unica (nao remover)
    mask_sem_doc = df_norm["chave_documento"].str.len() <= 1
    if mask_sem_doc.any():
        df_norm.loc[mask_sem_doc, "chave_documento"] = [
            "SEM_DOC_" + str(i) for i in df_norm.loc[mask_sem_doc].index
        ]
        logger.info(f"[EXTRATO BANCARIO] Registros sem documento identificavel: {mask_sem_doc.sum()}")

    logger.info(f"[EXTRATO BANCARIO] Movimentos normalizados: {len(df_norm)}")
    logger.info(f"[EXTRATO BANCARIO] Total entradas: {df_norm['entrada'].sum():,.2f}")
    logger.info(f"[EXTRATO BANCARIO] Total saidas: {df_norm['saida'].sum():,.2f}")

    return df_norm
