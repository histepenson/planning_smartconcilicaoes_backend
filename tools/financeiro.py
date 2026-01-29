import pandas as pd
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


def obter_coluna(df: pd.DataFrame, possiveis: list[str]) -> str:
    for col in possiveis:
        if col in df.columns:
            return col
    raise ValueError(
        f"Nenhuma das colunas esperadas foi encontrada. "
        f"Esperadas: {possiveis} | Encontradas: {list(df.columns)}"
    )


def _normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
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


def _parse_numero_br(v: object) -> float:
    """Converte números em formato BR/EN sem inflar valores com ponto decimal."""
    if pd.isna(v):
        return float("nan")
    if isinstance(v, (int, float)):
        return float(v)

    s = str(v).strip()
    if not s:
        return float("nan")

    # Remover espaços e símbolos comuns
    s = s.replace("\u00a0", "").replace(" ", "")
    s = re.sub(r"[^0-9,\.\-()]", "", s)

    # Negativo por parênteses ou sufixo '-'
    negativo = False
    if s.startswith("(") and s.endswith(")"):
        negativo = True
        s = s[1:-1]
    if s.endswith("-"):
        negativo = True
        s = s[:-1]

    if "," in s:
        # Formato BR: 1.234.567,89
        s = s.replace(".", "").replace(",", ".")
    else:
        # Sem vírgula: pode ser decimal com ponto ou milhar com vários pontos
        if s.count(".") > 1:
            s = s.replace(".", "")
        # se for apenas um ponto, mantemos como decimal

    try:
        valor = float(s)
        return -valor if negativo else valor
    except Exception:
        return float("nan")


def _serie_numerica(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].apply(_parse_numero_br)


def _encontrar_coluna_por_substrings(df: pd.DataFrame, substrings: list[str]) -> str | None:
    for col in df.columns:
        if all(sub in col for sub in substrings):
            return col
    return None


def _extrair_base_loja(texto: str) -> tuple[str, str]:
    """Extrai base(6) e loja(2) a partir de um texto com ou sem separadores."""
    digitos = re.sub(r"\D+", "", texto or "")
    if not digitos:
        return "000000", "00"

    if len(digitos) >= 8:
        base = digitos[:6]
        loja = digitos[6:8]
    elif len(digitos) >= 6:
        base = digitos[:6]
        loja = "00"
    else:
        base = digitos.zfill(6)
        loja = "00"

    return base.zfill(6), loja.zfill(2)


def _normalizar_financeiro_base(entrada: object) -> pd.DataFrame:
    if isinstance(entrada, pd.DataFrame):
        df = entrada.copy()
    else:
        df = pd.read_excel(entrada)

    logger.info("Total de registros lidos: %s", len(df))

    df = _normalizar_colunas(df)

    col_cliente = obter_coluna(df, [
        "codigo_lj_nome_do_cliente",
        "codigo_lj_nome_do_cliente_",
        "codigo_lj_nome_cliente",
        "cliente",
        "nome_cliente",
    ])

    # ==========================
    # CALCULAR VENCIDOS+VENCER
    # ==========================
    col_vencidos_exato = "tit_vencidos_valor_corrigido"
    col_a_vencer_exato = "titulos_a_vencer_valor_atual"

    if col_vencidos_exato in df.columns and col_a_vencer_exato in df.columns:
        col_vencidos = col_vencidos_exato
        col_a_vencer = col_a_vencer_exato
    else:
        # fallback robusto por substrings
        col_vencidos = _encontrar_coluna_por_substrings(
            df, ["tit", "vencidos", "valor", "corrigido"]
        ) or _encontrar_coluna_por_substrings(df, ["tit", "venc", "valor", "corrig"])

        col_a_vencer = _encontrar_coluna_por_substrings(
            df, ["titulos", "a_vencer", "valor", "atual"]
        ) or _encontrar_coluna_por_substrings(df, ["tit", "a_vencer", "valor", "atual"])

    if col_vencidos and col_a_vencer:
        logger.info("Valor será calculado por soma: %s + %s", col_vencidos, col_a_vencer)
        serie_vencidos = _serie_numerica(df, col_vencidos).fillna(0.0)
        serie_a_vencer = _serie_numerica(df, col_a_vencer).fillna(0.0)
        df["valor"] = serie_vencidos + serie_a_vencer
        logger.info(
            "Soma vencidos: %.2f | soma a vencer: %.2f | total: %.2f",
            float(serie_vencidos.sum()),
            float(serie_a_vencer.sum()),
            float(df["valor"].sum()),
        )
    else:
        possiveis_valor = [
            "tit_vencidos_valor_corrigido",
            "tit_vencidos_valor_atual",
            "valor_corrigido",
            "valor",
        ]

        col_valor = next((c for c in possiveis_valor if c in df.columns), None)
        if not col_valor:
            col_valor = next((c for c in df.columns if "valor" in c), None)
        if not col_valor:
            raise ValueError(f"Nenhuma coluna de valor encontrada. Colunas: {list(df.columns)}")

        logger.info("Valor será lido diretamente da coluna: %s", col_valor)
        df["valor"] = _serie_numerica(df, col_valor)

    col_vencimento = obter_coluna(df, [
        "vencto_real",
        "venctoreal",
        "vencto_titulo",
        "venctotitulo",
        "vencto_orig",
        "vencimento_real",
        "vencimento_titulo",
        "vencimento_orig",
        "data_vencimento",
        "vencimento",
    ])

    if "data_de_emissao" in df.columns:
        col_emissao = "data_de_emissao"
    elif "data_emissao" in df.columns:
        col_emissao = "data_emissao"
    else:
        col_emissao = (
        _encontrar_coluna_por_substrings(df, ["data", "emissao"])
        or _encontrar_coluna_por_substrings(df, ["data", "de", "emissao"])
        or _encontrar_coluna_por_substrings(df, ["dt", "emissao"])
        or _encontrar_coluna_por_substrings(df, ["data", "emiss"])
        or _encontrar_coluna_por_substrings(df, ["data", "de", "emiss"])
        or _encontrar_coluna_por_substrings(df, ["dt", "emiss"])
        or _encontrar_coluna_por_substrings(df, ["emiss"])
        )
    if "prf_numero" in df.columns:
        col_prf_numero = "prf_numero"
    else:
        col_prf_numero = _encontrar_coluna_por_substrings(df, ["prf", "numero"]) or _encontrar_coluna_por_substrings(
            df, ["prf", "num"]
        )
    if "parcela" in df.columns:
        col_parcela = "parcela"
    else:
        col_parcela = _encontrar_coluna_por_substrings(df, ["parcela"])

    # ==========================
    # NORMALIZAR CLIENTE E CÓDIGO
    # ==========================
    serie_cliente = df[col_cliente].astype(str).str.strip()
    partes = serie_cliente.str.split("-", n=2, expand=True)

    base_split = partes[0] if 0 in partes.columns else serie_cliente
    loja_split = partes[1] if 1 in partes.columns else pd.Series("", index=serie_cliente.index)

    base_loja_fallback = serie_cliente.apply(_extrair_base_loja)
    base_fallback = base_loja_fallback.apply(lambda t: t[0])
    loja_fallback = base_loja_fallback.apply(lambda t: t[1])

    # Só usar base do split quando a loja veio separada; senão usar fallback (evita base com loja embutida)
    loja_split_digits = loja_split.astype(str).str.extract(r"(\d+)", expand=False)
    has_loja_split = loja_split_digits.notna() & (loja_split_digits.astype(str).str.len() > 0)

    base_split_digits = base_split.astype(str).str.extract(r"(\d+)", expand=False)

    codigo_base = base_fallback.copy()
    codigo_base.loc[has_loja_split] = base_split_digits.loc[has_loja_split].fillna(base_fallback.loc[has_loja_split])
    codigo_base = codigo_base.astype(str).str.zfill(6)

    loja = loja_fallback.copy()
    loja.loc[has_loja_split] = loja_split_digits.loc[has_loja_split].fillna(loja_fallback.loc[has_loja_split])
    loja = loja.astype(str).str.zfill(2)

    df["codigo"] = "C" + codigo_base + loja

    cliente_split = partes[2] if 2 in partes.columns else None
    if cliente_split is not None:
        df["cliente"] = cliente_split.fillna(serie_cliente).astype(str).str.strip()
    else:
        df["cliente"] = serie_cliente

    # ==========================
    # DATA / DIAS VENCIDOS
    # ==========================
    df["data_vencimento"] = pd.to_datetime(df[col_vencimento], errors="coerce")
    if col_emissao:
        df["data_emissao"] = df[col_emissao]
    else:
        df["data_emissao"] = pd.NaT
    if col_prf_numero:
        df["prf_numero"] = df[col_prf_numero]
    else:
        df["prf_numero"] = None
    if col_parcela:
        df["parcela"] = df[col_parcela]
    else:
        df["parcela"] = None
    hoje = datetime.now()
    df["dias_vencidos"] = (hoje - df["data_vencimento"]).dt.days

    # ==========================
    # LIMPEZA
    # ==========================
    df = df[df["valor"].notna()].copy()

    return df


def normalizar_planilha_financeira_detalhada(entrada: object) -> pd.DataFrame:
    df = _normalizar_financeiro_base(entrada)
    return df[
        ["codigo", "cliente", "valor", "data_emissao", "data_vencimento", "prf_numero", "parcela"]
    ].copy()


def normalizar_planilha_financeira(entrada):
    df = _normalizar_financeiro_base(entrada)

    # ==========================
    # AGRUPAMENTO FINAL
    # ==========================
    df_agrupado = (
        df.groupby("codigo", as_index=False)
        .agg(
            cliente=("cliente", "first"),
            valor=("valor", "sum"),
            dias_vencidos=("dias_vencidos", "max"),
        )
    )

    df_agrupado["TIPO"] = df_agrupado["dias_vencidos"].apply(
        lambda x: "LONGO PRAZO" if pd.notna(x) and x > 365 else "CURTO PRAZO"
    )

    logger.info(
        "Financeiro normalizado: %s códigos | total valor: %.2f",
        df_agrupado["codigo"].nunique(),
        float(df_agrupado["valor"].sum()),
    )

    return df_agrupado
