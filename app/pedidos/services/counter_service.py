"""
Servico de contadores para lista de pedidos.
Consolida ~26 queries em ~4 queries e cacheia no Redis com TTL de 45s.

Uso:
    from app.pedidos.services.counter_service import PedidosCounterService
    dados = PedidosCounterService.obter_contadores()
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from sqlalchemy import func, distinct, case

from app import db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from app.cadastros_agendamento.models import ContatoAgendamento
from app.utils.redis_cache import redis_cache

logger = logging.getLogger(__name__)

CACHE_KEY = "pedidos:contadores:v1"
CACHE_TTL = 45  # segundos


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
        hoje = datetime.now().date()

        # 1. Contadores de data (D+0 a D+3) - 1 query em vez de 8
        contadores_data = PedidosCounterService._calcular_contadores_data(hoje)

        # 2. Contadores de status - 1 query em vez de 7
        contadores_status = PedidosCounterService._calcular_contadores_status(hoje)

        # 3. Dados auxiliares de agendamento
        contatos_por_cnpj, cnpjs_agendamento = PedidosCounterService._obter_dados_agendamento()

        # 4. Lotes com falta_item
        lotes_falta_item = PedidosCounterService._obter_lotes_falta_item()

        # 5. Lotes com falta_pagamento
        lotes_falta_pgto = PedidosCounterService._obter_lotes_falta_pgto()

        # 6. Contadores que dependem dos auxiliares
        contadores_status['agend_pendente'] = PedidosCounterService._contar_agend_pendente(
            cnpjs_agendamento)

        if lotes_falta_item:
            contadores_status['ag_item'] = db.session.query(
                func.count(distinct(Pedido.separacao_lote_id))
            ).filter(
                Pedido.separacao_lote_id.in_(lotes_falta_item),
                Pedido.nf_cd == False,
                (Pedido.nf.is_(None)) | (Pedido.nf == "")
            ).scalar() or 0
        else:
            contadores_status['ag_item'] = 0

        if lotes_falta_pgto:
            contadores_status['ag_pagamento'] = db.session.query(
                func.count(distinct(Pedido.separacao_lote_id))
            ).filter(
                Pedido.separacao_lote_id.in_(lotes_falta_pgto),
                Pedido.nf_cd == False,
                (Pedido.nf.is_(None)) | (Pedido.nf == "")
            ).scalar() or 0
        else:
            contadores_status['ag_pagamento'] = 0

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
        datas = [hoje + timedelta(days=i) for i in range(4)]

        # Construir as expressoes CASE WHEN
        cases = []
        for d in datas:
            # Total da data
            cases.append(
                func.count(case(
                    (func.date(Pedido.expedicao) == d, 1)
                ))
            )
            # Abertos da data
            cases.append(
                func.count(case(
                    ((func.date(Pedido.expedicao) == d) & (Pedido.status == 'ABERTO'), 1)
                ))
            )

        resultado = db.session.query(*cases).one()

        contadores_data = {}
        for i in range(4):
            contadores_data[f'd{i}'] = {
                'data': datas[i].isoformat(),
                'total': resultado[i * 2] or 0,
                'abertos': resultado[i * 2 + 1] or 0,
            }
        return contadores_data

    @staticmethod
    def _calcular_contadores_status(hoje) -> Dict:
        """
        Calcula contadores de status em UMA UNICA QUERY com CASE WHEN.
        Substitui ~7 queries individuais.
        """
        resultado = db.session.query(
            # 0: todos
            func.count(),
            # 1: abertos
            func.count(case(
                (Pedido.status == 'ABERTO', 1)
            )),
            # 2: cotados
            func.count(case(
                (
                    (Pedido.cotacao_id.isnot(None)) &
                    (Pedido.data_embarque.is_(None)) &
                    ((Pedido.nf.is_(None)) | (Pedido.nf == "")) &
                    (Pedido.nf_cd == False),
                    1
                )
            )),
            # 3: nf_cd
            func.count(case(
                (Pedido.nf_cd == True, 1)
            )),
            # 4: atrasados
            func.count(case(
                (
                    (
                        ((Pedido.cotacao_id.isnot(None)) & (Pedido.data_embarque.is_(None)) & ((Pedido.nf.is_(None)) | (Pedido.nf == ""))) |
                        ((Pedido.cotacao_id.is_(None)) & ((Pedido.nf.is_(None)) | (Pedido.nf == "")))
                    ) &
                    (Pedido.nf_cd == False) &
                    (Pedido.expedicao < hoje) &
                    ((Pedido.nf.is_(None)) | (Pedido.nf == "")),
                    1
                )
            )),
            # 5: atrasados_abertos
            func.count(case(
                (
                    (Pedido.status == 'ABERTO') & (Pedido.expedicao < hoje),
                    1
                )
            )),
            # 6: sem_data
            func.count(case(
                (
                    (Pedido.expedicao.is_(None)) &
                    (Pedido.nf_cd == False) &
                    ((Pedido.nf.is_(None)) | (Pedido.nf == "")) &
                    (Pedido.data_embarque.is_(None)),
                    1
                )
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
        }

    @staticmethod
    def _obter_dados_agendamento():
        """
        Carrega contatos de agendamento e retorna:
        - contatos_por_cnpj: dict {cnpj: contato_obj} para enrichment
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
    def _contar_agend_pendente(cnpjs_agendamento: List[str]) -> int:
        """Conta pedidos com agendamento pendente."""
        if not cnpjs_agendamento:
            return 0

        return Pedido.query.filter(
            Pedido.cnpj_cpf.in_(cnpjs_agendamento),
            Pedido.agendamento.is_(None),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.data_embarque.is_(None)
        ).count()

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
        """Retorna IDs de lotes com falta_pagamento=True para pedidos ANTECIPADOS."""
        try:
            num_pedidos_antecipados = [r[0] for r in db.session.query(
                distinct(CarteiraPrincipal.num_pedido)
            ).filter(
                CarteiraPrincipal.cond_pgto_pedido.ilike('%ANTECIPADO%')
            ).all() if r[0]]

            if not num_pedidos_antecipados:
                return []

            return [r[0] for r in db.session.query(Separacao.separacao_lote_id).filter(
                Separacao.num_pedido.in_(num_pedidos_antecipados),
                Separacao.falta_pagamento == True,
                Separacao.sincronizado_nf == False
            ).distinct().all()]
        except Exception as e:
            logger.error(f"Erro ao buscar lotes_falta_pgto: {e}")
            return []

    @staticmethod
    def invalidar_cache():
        """Invalida o cache de contadores. Chamar apos mudancas de status/NF/expedicao."""
        redis_cache.delete(CACHE_KEY)
        logger.info("🗑️ Cache de contadores pedidos invalidado")
