from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

# =======================
# ENTRADA
# =======================

class BaseOrigem(BaseModel):
    registros: List[Dict[str, Any]]


class BaseContabilFiltrada(BaseModel):
    registros: List[Dict[str, Any]]
    conta_contabil: str


class BaseContabilGeral(BaseModel):
    registros: List[Dict[str, Any]]


class RequestConciliacao(BaseModel):
    base_origem: BaseOrigem
    base_contabil_filtrada: BaseContabilFiltrada
    base_contabil_geral: BaseContabilGeral
    parametros: Optional[Dict[str, Any]] = Field(default_factory=dict)


# =======================
# SAÍDA
# =======================

class DiferencaOrigemMaior(BaseModel):
    identificador: str
    data: str
    valor: float
    cliente_fornecedor: str
    descricao: str
    encontrado_lancamentos: bool = False
    conta_contabil_encontrada: str = ""
    conta_contabil_esperada: str = ""
    historico_lancamento: str = ""
    data_lancamento: str = ""
    criterio_match: str = ""
    confianca_match: str = ""
    situacao: str = ""


class DiferencaContabilidadeMaior(BaseModel):
    identificador: str
    data: str
    valor: float
    conta_contabil: str
    historico: str
    existe_origem: bool = False
    verificacoes_realizadas: List[str] = []
    situacao: str = ""


class OrigemLancamento(BaseModel):
    """Representa uma origem identificada no razão geral para um lançamento SO_CONTABILIDADE."""
    conta_origem: str
    descricao_conta: str = ""
    valor: float
    tipo_lancamento: str = ""  # DEBITO | CREDITO
    data_lancamento: str = ""
    documento: str = ""
    historico: str = ""
    tipo_movimento: str  # TRANSFERENCIA | ALOCACAO | RECLASSIFICACAO | LANCAMENTO_AUTOMATICO | NAO_IDENTIFICADO


class AnaliseContabilProfunda(BaseModel):
    """Análise detalhada de um registro SO_CONTABILIDADE com busca no razão geral."""
    codigo: str
    nome: str
    valor_contabilidade: float
    conta_analisada: str
    origens_identificadas: List[OrigemLancamento] = []
    total_origens: int = 0
    status_analise: str  # ORIGEM_IDENTIFICADA | ORIGEM_NAO_IDENTIFICADA | MULTIPLAS_ORIGENS
    nota_explicativa: str = ""


class AnaliseDiferencaDetalhada(BaseModel):
    codigo: str
    nome: str
    conta_contabil: str
    valor_financeiro: float
    valor_contabilidade: float
    diferenca: float
    tipo_diferenca: str
    status: str
    lancamentos_razao: int = 0
    lancamentos_razao_detalhes: List[OrigemLancamento] = []
    lancamentos_financeiro_detalhes: List[OrigemLancamento] = []
    sem_lancamentos_razao: bool = False
    nota_razao: str = ""


class ResumoAnaliseDetalhada(BaseModel):
    total_registros: int
    conciliados: int
    divergentes: int
    percentual_conciliacao: float


class ResumoConsolidacao(BaseModel):
    total_origem: float
    total_destino: float
    diferenca: float
    situacao: str
    percentual_divergencia: float
    quantidade_registros_origem: int
    quantidade_registros_destino: int
    data_processamento: str


class RelatorioConsolidacao(BaseModel):
    resumo: ResumoConsolidacao
    diferencas_origem_maior: List[DiferencaOrigemMaior]
    diferencas_contabilidade_maior: List[DiferencaContabilidadeMaior]
    analise_detalhada: List[AnaliseDiferencaDetalhada] = []
    resumo_analise: Optional[ResumoAnaliseDetalhada] = None
    analise_profunda_contabil: List[AnaliseContabilProfunda] = []
    observacoes: List[str] = []
    alertas: List[str] = []
