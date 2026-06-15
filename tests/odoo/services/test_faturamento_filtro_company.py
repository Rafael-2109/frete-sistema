"""Regressao: o ETL de faturamento (account.move) NAO importa NFs da LF (company 5).

Contexto (2026-06-15): as NFs de industrializacao LF->FB (servico 5124 + insumos
5902) sao inter-company (partner = a propria FB), nao venda a cliente. A NF de
insumos (total=0, journal RETIND 1083) chegava a gerar FaturamentoProduto +
MovimentacaoEstoque espurios em PROD, re-baixando estoque. O fix adiciona
`company_id not in [5]` em TODOS os dominios de busca do ETL.

Estes testes capturam o dominio passado ao Odoo (search_read mockado, retorno
vazio = a funcao retorna cedo sem processar) e garantem o filtro nos 3 caminhos:
incremental, nao-incremental e canceladas.
"""
from unittest.mock import MagicMock, patch

from app.odoo.services.faturamento_service import (
    FaturamentoService,
    COMPANIES_EXCLUIDAS_ETL_FATURAMENTO,
)

FILTRO_LINE = ('move_id.company_id', 'not in', COMPANIES_EXCLUIDAS_ETL_FATURAMENTO)
FILTRO_MOVE = ('company_id', 'not in', COMPANIES_EXCLUIDAS_ETL_FATURAMENTO)


def _dominios_capturados(conn):
    """Todos os dominios (2o arg posicional) das chamadas a search_read."""
    return [c.args[1] for c in conn.search_read.call_args_list if len(c.args) >= 2]


def _make_service():
    with patch('app.odoo.services.faturamento_service.get_odoo_connection') as mock_get:
        conn = MagicMock()
        conn.search_read.return_value = []  # sem dados -> retorno cedo, sem processar
        mock_get.return_value = conn
        svc = FaturamentoService()
    return svc, conn


def test_lf_excluida_no_modo_incremental():
    svc, conn = _make_service()
    svc.obter_faturamento_otimizado(modo_incremental=True, minutos_status=60)
    dominios = _dominios_capturados(conn)
    assert dominios, 'esperava ao menos uma chamada a search_read'
    assert any(FILTRO_LINE in d for d in dominios), \
        f'filtro de company ausente no dominio incremental: {dominios}'


def test_lf_excluida_no_modo_nao_incremental_postado():
    svc, conn = _make_service()
    svc.obter_faturamento_otimizado(modo_incremental=False, usar_filtro_postado=True)
    dominios = _dominios_capturados(conn)
    assert any(FILTRO_LINE in d for d in dominios), \
        f'filtro de company ausente no dominio nao-incremental (postado): {dominios}'


def test_lf_excluida_no_modo_nao_incremental_sem_postado():
    svc, conn = _make_service()
    svc.obter_faturamento_otimizado(modo_incremental=False, usar_filtro_postado=False)
    dominios = _dominios_capturados(conn)
    assert any(FILTRO_LINE in d for d in dominios), \
        f'filtro de company ausente no dominio nao-incremental (sem postado): {dominios}'


def test_lf_excluida_nas_canceladas():
    svc, conn = _make_service()
    svc.processar_nfs_canceladas_existentes()
    dominios = _dominios_capturados(conn)
    assert any(FILTRO_MOVE in d for d in dominios), \
        f'filtro de company ausente no dominio de canceladas: {dominios}'


def test_lf_e_a_unica_company_excluida():
    # guard: nao excluir FB(1)/SC(3)/CD(4) por engano
    assert COMPANIES_EXCLUIDAS_ETL_FATURAMENTO == [5]
