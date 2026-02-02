"""
Schemas para o Dashboard.
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class DashboardStats(BaseModel):
    """Estatisticas gerais do dashboard."""
    total_contas: int
    contas_conciliadas: int
    contas_pendentes: int
    taxa_sucesso: float  # Percentual 0-100


class ConciliacaoRecente(BaseModel):
    """Conciliacao recente para exibicao no dashboard."""
    id: int
    conta_contabil: str
    descricao: str
    periodo: str
    data_efetivacao: datetime
    situacao: str


class GraficoMensal(BaseModel):
    """Dados para grafico de conciliacoes por mes."""
    mes: str  # "Jan", "Fev", etc.
    ano: int
    quantidade: int


class AlertaPendencia(BaseModel):
    """Alerta de pendencia."""
    tipo: str  # "warning", "info", "error"
    mensagem: str
    acao_url: Optional[str] = None


class DashboardResponse(BaseModel):
    """Response completo do dashboard."""
    saudacao: str
    data_atual: str
    empresa_nome: str
    stats: DashboardStats
    conciliacoes_recentes: List[ConciliacaoRecente]
    grafico_mensal: List[GraficoMensal]
    alertas: List[AlertaPendencia]
