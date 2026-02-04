"""
Router para endpoints de Conciliacao Bancaria.

Endpoints:
- POST /conciliacoes/bancaria - Processa conciliacao bancaria
"""

from fastapi import APIRouter, HTTPException, Depends
import logging

from schemas.conciliacao_bancaria_schema import (
    RequestConciliacaoBancaria,
    RelatorioConciliacaoBancaria,
    EfetivarConciliacaoBancariaRequest,
)
from services.conciliacao_bancaria_service import ConciliacaoBancariaService
from services.conciliacao_bancaria_efetivacao_service import ConciliacaoBancariaEfetivacaoService
from schemas.efetivacao_schema import EfetivarConciliacaoResponse, StatusConciliacao
from middleware.auth import get_current_user, CurrentUser
from db import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conciliacoes",
    tags=["Conciliacao Bancaria"],
)


@router.post("/bancaria", response_model=None)
def processar_conciliacao_bancaria(request: RequestConciliacaoBancaria):
    """
    Processa conciliacao bancaria.

    Recebe:
    - base_extrato: Extrato bancario (FINR470)
    - base_razao: Razao contabil do banco (CTBR400)
    - parametros: Data-base e configuracoes

    Retorna:
    - Relatorio completo de conciliacao bancaria
    """
    logger.info("="*50)
    logger.info("ENDPOINT: POST /conciliacoes/bancaria")
    logger.info("="*50)

    service = ConciliacaoBancariaService()

    # Validar dados de entrada
    valido, mensagem = service.validar_dados(request)
    if not valido:
        logger.error(f"Validacao falhou: {mensagem}")
        raise HTTPException(status_code=400, detail=mensagem)

    try:
        # Executar conciliacao
        resultado = service.executar(request)
        logger.info("Conciliacao bancaria executada com sucesso")
        return resultado

    except ValueError as e:
        logger.error(f"Erro de validacao: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception(f"Erro interno: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao processar conciliacao bancaria: {str(e)}"
        )


@router.post("/bancaria/efetivar", response_model=EfetivarConciliacaoResponse, status_code=201)
def efetivar_conciliacao_bancaria(
    request: EfetivarConciliacaoBancariaRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = ConciliacaoBancariaEfetivacaoService()
    conciliacao = service.efetivar(
        db=db,
        empresa_id=request.empresa_id,
        conta_contabil_id=request.conta_contabil_id,
        data_base=request.data_base,
        resultado=request.resultado,
        current_user=current_user
    )
    return EfetivarConciliacaoResponse(
        id=conciliacao.id,
        message="Conciliacao bancaria efetivada com sucesso",
        status=StatusConciliacao.EFETIVADA,
        data_efetivacao=conciliacao.data_efetivacao
    )
