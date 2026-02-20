"""
Serviço para detectar mudanças em POs e marcar DFEs para revalidação.
=====================================================================

Fluxo:
1. Busca POs modificados nos últimos N minutos (via PedidoCompras.atualizado_em)
2. Busca DFEs aprovados que usaram esses POs (via MatchAlocacao.odoo_po_id)
3. Marca po_modificada_apos_validacao = True nos DFEs afetados

Gatilho:
- Executado após sincronização de POs no scheduler
- Garante que DFEs que usaram POs modificadas serão revalidados

Referência:
- Plano em /.claude/plans/hashed-noodling-zebra.md
"""

import logging
from datetime import timedelta
from typing import Dict, Any, List, Set

from app import db
from app.utils.timezone import agora_utc_naive
from app.manufatura.models import PedidoCompras
from app.recebimento.models import ValidacaoNfPoDfe, MatchNfPoItem, MatchAlocacao

logger = logging.getLogger(__name__)


class PoChangesDetectorService:
    """
    Detecta POs modificadas e marca DFEs aprovados para revalidação.

    Este serviço é a peça-chave do skip inteligente:
    - PO modificada → DFE que usou a PO precisa revalidar
    - PO não modificada → DFE pode ser skipped
    """

    def detectar_e_marcar_revalidacoes(self, minutos_janela: int = 90) -> Dict[str, Any]:
        """
        Detecta POs modificadas e marca DFEs aprovados que usaram essas POs.

        Args:
            minutos_janela: Quantos minutos olhar para trás (padrão: 90 = 1.5h)
                           Deve ser maior que a frequência do sync de POs

        Returns:
            Dict com estatísticas da execução:
            - status: 'ok' ou 'erro'
            - pos_verificadas: Número de POs modificadas encontradas
            - dfes_marcados: Número de DFEs marcados para revalidação
            - validacoes_afetadas: Número total de validações que tinham essas POs

        Exemplo de retorno:
            {
                'status': 'ok',
                'pos_verificadas': 5,
                'dfes_marcados': 2,
                'validacoes_afetadas': 3
            }
        """
        data_limite = agora_utc_naive() - timedelta(minutes=minutos_janela)

        logger.info(
            f"🔍 Detectando mudanças em POs desde {data_limite.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # 1. Buscar POs modificados recentemente
        pos_modificados = PedidoCompras.query.filter(
            PedidoCompras.atualizado_em >= data_limite
        ).all()

        if not pos_modificados:
            logger.info("✓ Nenhuma PO modificada no período")
            return {'status': 'ok', 'pos_verificadas': 0, 'dfes_marcados': 0}

        # 2. Extrair odoo_purchase_order_ids das POs (ID do header purchase.order)
        # CORRECAO: Usar odoo_purchase_order_id (header) em vez de odoo_id (linha)
        # para comparar com MatchAlocacao.odoo_po_id que armazena o ID do header
        po_odoo_ids: Set[int] = set()
        for po in pos_modificados:
            if po.odoo_purchase_order_id:
                try:
                    po_odoo_ids.add(int(po.odoo_purchase_order_id))
                except (ValueError, TypeError):
                    continue

        if not po_odoo_ids:
            logger.info("✓ POs modificadas não têm odoo_purchase_order_id válido")
            return {'status': 'ok', 'pos_verificadas': len(pos_modificados), 'dfes_marcados': 0}

        logger.info(f"📦 Encontradas {len(po_odoo_ids)} POs modificadas com odoo_purchase_order_id válido")

        # 3. Buscar alocações que usam essas POs
        alocacoes = MatchAlocacao.query.filter(
            MatchAlocacao.odoo_po_id.in_(list(po_odoo_ids))
        ).all()

        if not alocacoes:
            logger.info("✓ Nenhuma alocação usa as POs modificadas")
            return {
                'status': 'ok',
                'pos_verificadas': len(po_odoo_ids),
                'dfes_marcados': 0,
                'validacoes_afetadas': 0
            }

        # 4. Agrupar por validação_id (via match_item)
        validacao_ids_afetados: Set[int] = set()
        for aloc in alocacoes:
            if aloc.match_item_id:
                # Buscar o match_item para pegar validacao_id
                match_item = MatchNfPoItem.query.get(aloc.match_item_id)
                if match_item and match_item.validacao_id:
                    validacao_ids_afetados.add(match_item.validacao_id)

        if not validacao_ids_afetados:
            logger.info("✓ Alocações encontradas mas sem validação associada")
            return {
                'status': 'ok',
                'pos_verificadas': len(po_odoo_ids),
                'dfes_marcados': 0,
                'validacoes_afetadas': 0
            }

        logger.info(f"🔗 {len(validacao_ids_afetados)} validações usam POs modificadas")

        # 5. Marcar validações aprovadas para revalidação
        dfes_marcados = 0
        for val_id in validacao_ids_afetados:
            validacao = ValidacaoNfPoDfe.query.get(val_id)
            if not validacao:
                continue

            # Marca se status é 'aprovado' ou 'bloqueado' (outros status já serão reprocessados)
            if validacao.status in ('aprovado', 'bloqueado'):
                if not validacao.po_modificada_apos_validacao:
                    validacao.po_modificada_apos_validacao = True
                    validacao.atualizado_em = agora_utc_naive()
                    dfes_marcados += 1
                    logger.warning(
                        f"⚠️  DFE {validacao.odoo_dfe_id} (NF {validacao.numero_nf}) "
                        f"marcado para revalidação - PO modificada"
                    )

        if dfes_marcados > 0:
            db.session.commit()

        logger.info(
            f"✅ Detecção concluída: {len(po_odoo_ids)} POs verificadas, "
            f"{dfes_marcados} DFEs marcados para revalidação"
        )

        return {
            'status': 'ok',
            'pos_verificadas': len(po_odoo_ids),
            'dfes_marcados': dfes_marcados,
            'validacoes_afetadas': len(validacao_ids_afetados)
        }

    def extrair_pos_usadas(self, validacao_id: int) -> List[Dict[str, Any]]:
        """
        Extrai lista de POs usadas em uma validação.

        Usado após validação bem-sucedida para guardar po_ids_usados.

        Args:
            validacao_id: ID da validação

        Returns:
            Lista de dicts: [{"id": 123, "name": "PO00456"}, ...]
        """
        matches = MatchNfPoItem.query.filter_by(
            validacao_id=validacao_id,
            status_match='match'
        ).all()

        po_ids_usados: List[Dict[str, Any]] = []
        po_ids_vistos: Set[int] = set()

        for match in matches:
            alocacoes = MatchAlocacao.query.filter_by(
                match_item_id=match.id
            ).all()

            for aloc in alocacoes:
                if aloc.odoo_po_id and aloc.odoo_po_id not in po_ids_vistos:
                    po_ids_usados.append({
                        'id': aloc.odoo_po_id,
                        'name': aloc.odoo_po_name or f'PO{aloc.odoo_po_id}'
                    })
                    po_ids_vistos.add(aloc.odoo_po_id)

        return po_ids_usados
