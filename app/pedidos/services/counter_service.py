"""
Servico de contadores para lista de pedidos.
Consolida ~26 queries em ~4 queries e cacheia no Redis com TTL de 45s.

Uso:
    from app.pedidos.services.counter_service import PedidosCounterService
    dados = PedidosCounterService.obter_contadores()
"""
import hashlib
import json
import logging
from datetime import timedelta
from typing import Dict, Any, List, Tuple

from sqlalchemy import func, distinct, case

from app import db
from app.pedidos.models import Pedido, PedidoMV
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from app.cadastros_agendamento.models import ContatoAgendamento
from app.utils.redis_cache import redis_cache
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# Raiz CNPJ (8 primeiros dígitos) de clientes excluídos do filtro Agend. Pendente
CNPJS_EXCLUIR_AGENDAMENTO = ['93209765', '75315333', '00063960', '01157555', '06057223']

CACHE_KEY = "pedidos:contadores:v4"
CACHE_TTL = 45  # segundos

FACETED_CACHE_PREFIX = "pedidos:contadores:filtros:"
FACETED_CACHE_TTL = 30  # segundos

ROTAS_CACHE_KEY = "pedidos:rotas_choices:v2"
ROTAS_CACHE_TTL = 300  # 5 minutos

# Flag cacheada: mv_pedidos existe no banco?
_mv_disponivel = None


def _get_model():
    """Retorna PedidoMV se mv_pedidos existe, senao Pedido (VIEW).
    Resultado cacheado em memoria — verificado 1x por processo."""
    global _mv_disponivel
    if _mv_disponivel is None:
        try:
            from sqlalchemy import text
            result = db.session.execute(
                text("SELECT 1 FROM pg_matviews WHERE matviewname = 'mv_pedidos'")
            )
            _mv_disponivel = result.scalar() is not None
            db.session.rollback()  # limpar transacao de verificacao
        except Exception:
            _mv_disponivel = False
            try:
                db.session.rollback()
            except Exception:
                pass
    if _mv_disponivel:
        return PedidoMV
    logger.info("mv_pedidos nao disponivel — usando VIEW pedidos (fallback)")
    return Pedido


class PedidosCounterService:
    """Calcula e cacheia contadores da lista de pedidos."""

    @staticmethod
    def obter_contadores() -> Dict[str, Any]:
        """
        Retorna todos os contadores + dados auxiliares.
        Tenta Redis primeiro; se miss, calcula tudo e cacheia.
        """
        cached = redis_cache.get(CACHE_KEY)
        if cached is not None:
            logger.debug("✅ Contadores pedidos: CACHE HIT")
            return cached

        logger.debug("💨 Contadores pedidos: CACHE MISS - calculando")
        resultado = PedidosCounterService._calcular_tudo()

        redis_cache.set(CACHE_KEY, resultado, CACHE_TTL)
        return resultado

    @staticmethod
    def _calcular_tudo() -> Dict[str, Any]:
        """Calcula todos os contadores em queries otimizadas."""
        M = _get_model()  # PedidoMV se mv_pedidos existe, senao Pedido (VIEW)
        hoje = agora_utc_naive().date()

        # 1. Dados auxiliares de agendamento (necessario ANTES dos contadores de status)
        _contatos_por_cnpj, cnpjs_agendamento = PedidosCounterService._obter_dados_agendamento()

        # 2. Contadores de data (D+0 a D+3) - 1 query em vez de 8
        contadores_data = PedidosCounterService._calcular_contadores_data(hoje)

        # 3. Contadores de status + agend_pendente - 1 query em vez de 8
        contadores_status = PedidosCounterService._calcular_contadores_status(
            hoje, cnpjs_agendamento)

        # 4. Lotes com falta_item
        lotes_falta_item = PedidosCounterService._obter_lotes_falta_item()

        # 5. Lotes com falta_pagamento
        lotes_falta_pgto = PedidosCounterService._obter_lotes_falta_pgto()

        # ag_item + ag_pagamento em 1 unica query (era 2 scans da VIEW)
        contadores_status['ag_item'] = 0
        contadores_status['ag_pagamento'] = 0
        combined_lotes = list(set((lotes_falta_item or []) + (lotes_falta_pgto or [])))
        if combined_lotes:
            ag_result = db.session.query(
                func.count(distinct(case(
                    (M.separacao_lote_id.in_(lotes_falta_item or []), M.separacao_lote_id),
                    else_=None
                ))),
                func.count(distinct(case(
                    (M.separacao_lote_id.in_(lotes_falta_pgto or []), M.separacao_lote_id),
                    else_=None
                ))),
            ).filter(
                M.separacao_lote_id.in_(combined_lotes),
                M.nf_cd == False,
                (M.nf.is_(None)) | (M.nf == "")
            ).one()
            contadores_status['ag_item'] = ag_result[0] or 0
            contadores_status['ag_pagamento'] = ag_result[1] or 0

        return {
            'contadores_data': contadores_data,
            'contadores_status': contadores_status,
            'cnpjs_agendamento': cnpjs_agendamento,
            'lotes_falta_item': lotes_falta_item,
            'lotes_falta_pgto': lotes_falta_pgto,
        }

    @staticmethod
    def _calcular_contadores_data(hoje) -> Dict:
        """
        Calcula contadores D+0 a D+3 em UMA UNICA QUERY com CASE WHEN.
        Substitui 8 queries individuais.
        """
        M = _get_model()
        datas = [hoje + timedelta(days=i) for i in range(4)]

        # Construir as expressoes CASE WHEN (3 por data: total, pend_embarque, abertos)
        cases = []
        for d in datas:
            # Total da data
            cases.append(
                func.count(case(
                    (M.expedicao == d, 1)
                ))
            )
            # Pend embarque da data (sem data_embarque — inclui NF no CD)
            cases.append(
                func.count(case(
                    ((M.expedicao == d) & (M.data_embarque.is_(None)), 1)
                ))
            )
            # Abertos da data (inclui nf_cd=True)
            cases.append(
                func.count(case(
                    ((M.expedicao == d) & ((M.status == 'ABERTO') | (M.nf_cd == True)), 1)
                ))
            )

        resultado = db.session.query(*cases).one()

        contadores_data = {}
        for i in range(4):
            contadores_data[f'd{i}'] = {
                'data': datas[i].isoformat(),
                'total': resultado[i * 3] or 0,
                'pend_embarque': resultado[i * 3 + 1] or 0,
                'abertos': resultado[i * 3 + 2] or 0,
            }
        return contadores_data

    @staticmethod
    def _calcular_contadores_status(hoje, cnpjs_agendamento: List[str] = None) -> Dict:
        """
        Calcula contadores de status + agend_pendente em UMA UNICA QUERY com CASE WHEN.
        Substitui ~8 queries individuais (inclui agend_pendente que era query separada).
        """
        M = _get_model()
        # Expressao agend_pendente (incorporada aqui para evitar scan extra da VIEW)
        cnpj_raiz = func.left(func.regexp_replace(M.cnpj_cpf, '[^0-9]', '', 'g'), 8)
        if cnpjs_agendamento:
            agend_expr = (
                (M.cnpj_cpf.in_(cnpjs_agendamento)) &
                (M.agendamento.is_(None)) &
                (M.nf_cd == False) &
                ((M.nf.is_(None)) | (M.nf == "")) &
                (M.data_embarque.is_(None)) &
                ((M.cod_uf == 'SP') | (M.rota == 'FOB')) &
                (~cnpj_raiz.in_(CNPJS_EXCLUIR_AGENDAMENTO))
            )
        else:
            agend_expr = M.separacao_lote_id == 'IMPOSSIVEL'

        resultado = db.session.query(
            # 0: todos
            func.count(),
            # 1: abertos (inclui nf_cd=True)
            func.count(case(
                ((M.status == 'ABERTO') | (M.nf_cd == True), 1)
            )),
            # 2: cotados
            func.count(case(
                (
                    (M.cotacao_id.isnot(None)) &
                    (M.data_embarque.is_(None)) &
                    ((M.nf.is_(None)) | (M.nf == "")) &
                    (M.nf_cd == False),
                    1
                )
            )),
            # 3: nf_cd
            func.count(case(
                (M.nf_cd == True, 1)
            )),
            # 4: atrasados
            func.count(case(
                (
                    (
                        ((M.cotacao_id.isnot(None)) & (M.data_embarque.is_(None)) & ((M.nf.is_(None)) | (M.nf == ""))) |
                        ((M.cotacao_id.is_(None)) & ((M.nf.is_(None)) | (M.nf == "")))
                    ) &
                    (M.nf_cd == False) &
                    (M.expedicao < hoje) &
                    ((M.nf.is_(None)) | (M.nf == "")),
                    1
                )
            )),
            # 5: atrasados_abertos
            func.count(case(
                (
                    (M.status == 'ABERTO') & (M.expedicao < hoje),
                    1
                )
            )),
            # 6: sem_data
            func.count(case(
                (
                    (M.expedicao.is_(None)) &
                    (M.nf_cd == False) &
                    ((M.nf.is_(None)) | (M.nf == "")) &
                    (M.data_embarque.is_(None)),
                    1
                )
            )),
            # 7: pend_embarque (sem data_embarque — inclui NF no CD)
            func.count(case(
                (M.data_embarque.is_(None), 1)
            )),
            # 8: faturados (tem NF preenchida, nao esta no CD)
            func.count(case(
                (
                    (M.nf.isnot(None)) & (M.nf != "") &
                    (M.nf_cd == False),
                    1
                )
            )),
            # 9: agend_pendente (era query separada — _contar_agend_pendente)
            func.count(case(
                (agend_expr, 1)
            )),
        ).one()

        return {
            'todos': resultado[0] or 0,
            'abertos': resultado[1] or 0,
            'cotados': resultado[2] or 0,
            'nf_cd': resultado[3] or 0,
            'atrasados': resultado[4] or 0,
            'atrasados_abertos': resultado[5] or 0,
            'sem_data': resultado[6] or 0,
            'pend_embarque': resultado[7] or 0,
            'faturados': resultado[8] or 0,
            'agend_pendente': resultado[9] or 0,
        }

    @staticmethod
    def _obter_dados_agendamento():
        """
        Carrega contatos de agendamento e retorna:
        - contatos_por_cnpj: dict {cnpj: contato_id} (IDs, nao objetos ORM)
        - cnpjs_agendamento: lista de CNPJs validos para filtro
        """
        contatos = ContatoAgendamento.query.filter(
            ContatoAgendamento.forma.isnot(None),
            ContatoAgendamento.forma != '',
            ContatoAgendamento.forma != 'SEM AGENDAMENTO'
        ).all()

        contatos_por_cnpj = {c.cnpj: c.id for c in contatos if c.cnpj}
        cnpjs_agendamento = list(contatos_por_cnpj.keys())

        return contatos_por_cnpj, cnpjs_agendamento

    @staticmethod
    def _obter_lotes_falta_item() -> List[str]:
        """Retorna IDs de lotes com falta_item=True."""
        try:
            return [r[0] for r in db.session.query(Separacao.separacao_lote_id).filter(
                Separacao.falta_item == True,
                Separacao.sincronizado_nf == False
            ).distinct().all()]
        except Exception as e:
            logger.error(f"Erro ao buscar lotes_falta_item: {e}")
            return []

    @staticmethod
    def _obter_lotes_falta_pgto() -> List[str]:
        """Retorna IDs de lotes com falta_pagamento=True para pedidos ANTECIPADOS.
        1 query com JOIN (era 2 queries sequenciais)."""
        try:
            return [r[0] for r in db.session.query(
                distinct(Separacao.separacao_lote_id)
            ).join(
                CarteiraPrincipal,
                Separacao.num_pedido == CarteiraPrincipal.num_pedido
            ).filter(
                CarteiraPrincipal.cond_pgto_pedido.ilike('%ANTECIPADO%'),
                Separacao.falta_pagamento == True,
                Separacao.sincronizado_nf == False
            ).all()]
        except Exception as e:
            logger.error(f"Erro ao buscar lotes_falta_pgto: {e}")
            return []

    # ---------------------------------------------------------------
    # CONTADORES FACETADOS (cache por fingerprint de filtros)
    # ---------------------------------------------------------------
    @staticmethod
    def _build_filter_fingerprint(args) -> str:
        """Gera hash MD5 dos parametros de filtro (exclui page/sort)."""
        filter_keys = sorted([
            'status', 'cond_atrasados', 'cond_sem_data', 'cond_pend_embarque',
            'cond_agend_pendente', 'cond_ag_pagamento', 'cond_ag_item',
            'expedicao_de', 'expedicao_ate', 'uf', 'rota', 'sub_rota',
            'numero_pedido', 'cnpj_cpf', 'cliente', 'data',
        ])
        params = {k: args.get(k, '') for k in filter_keys if args.get(k)}
        raw = json.dumps(params, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def obter_contadores_filtrados(args, hoje,
                                    cnpjs_agendamento=None,
                                    lotes_item=None,
                                    lotes_pgto=None) -> Dict[str, Any]:
        """
        Contadores facetados com cache Redis (TTL=30s).
        Chave = fingerprint dos filtros ativos.
        """
        fingerprint = PedidosCounterService._build_filter_fingerprint(args)
        cache_key = f"{FACETED_CACHE_PREFIX}{fingerprint}"

        cached = redis_cache.get(cache_key)
        if cached is not None:
            logger.debug("Contadores facetados: CACHE HIT (%s)", fingerprint[:8])
            return cached

        logger.debug("Contadores facetados: CACHE MISS (%s) - calculando", fingerprint[:8])
        from app.pedidos.services.lista_service import ListaPedidosService as Svc
        resultado = Svc.calcular_contadores_filtrados(
            args, hoje,
            cnpjs_agendamento=cnpjs_agendamento,
            lotes_item=lotes_item,
            lotes_pgto=lotes_pgto,
        )

        redis_cache.set(cache_key, resultado, FACETED_CACHE_TTL)
        return resultado

    # ---------------------------------------------------------------
    # CHOICES DE ROTA/SUB-ROTA (cache 5 min)
    # ---------------------------------------------------------------
    @staticmethod
    def obter_rotas_choices() -> Tuple[List[str], List[str]]:
        """
        Retorna (rotas_choices, sub_rotas_choices) com cache Redis (TTL=5min).
        """
        cached = redis_cache.get(ROTAS_CACHE_KEY)
        if cached is not None:
            logger.debug("Rotas choices: CACHE HIT")
            return cached['rotas'], cached['sub_rotas']

        logger.debug("Rotas choices: CACHE MISS - calculando")
        M = _get_model()  # rotas sao dados estaveis — MV aceitavel
        # 1 query em vez de 2 (era 2 scans da VIEW)
        result = db.session.query(
            M.rota, M.sub_rota
        ).filter(
            db.or_(M.rota.isnot(None), M.sub_rota.isnot(None))
        ).distinct().all()

        rotas_choices = sorted(set(r[0] for r in result if r[0]))
        sub_rotas_choices = sorted(set(r[1] for r in result if r[1]))

        redis_cache.set(ROTAS_CACHE_KEY, {
            'rotas': rotas_choices,
            'sub_rotas': sub_rotas_choices,
        }, ROTAS_CACHE_TTL)

        return rotas_choices, sub_rotas_choices

    # ---------------------------------------------------------------
    # INVALIDACAO
    # ---------------------------------------------------------------
    @staticmethod
    def invalidar_cache():
        """Invalida todos os caches de contadores e choices."""
        redis_cache.delete(CACHE_KEY)
        redis_cache.flush_pattern(f"{FACETED_CACHE_PREFIX}*")
        redis_cache.delete(ROTAS_CACHE_KEY)
        logger.info("Cache de contadores pedidos invalidado (global + facetados + rotas)")
