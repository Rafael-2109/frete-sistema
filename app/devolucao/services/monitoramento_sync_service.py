"""
Service para Sincronizacao com Monitoramento
=============================================

OBJETIVO:
    Criar NFDevolucao baseadas em status_finalizacao do Monitoramento.
    Entregas marcadas como "Cancelada", "Devolvida" ou "Troca de NF"
    no monitoramento devem gerar ocorrencias de devolucao.

STATUS DE DEVOLUCAO:
    - Cancelada: Entrega nao concluida, mercadoria voltou
    - Devolvida: Mercadoria foi devolvida pelo cliente
    - Troca de NF: Necessario trocar a NF (problema fiscal)

FLUXO:
    1. Buscar entregas com status_finalizacao de devolucao
    2. Para cada entrega SEM NFDevolucao vinculada:
       a) Criar NFDevolucao com tipo='NF'
       b) Preencher status_monitoramento
       c) Criar OcorrenciaDevolucao automaticamente
    3. Marcar teve_devolucao = True na entrega

AUTOR: Sistema de Fretes - Modulo Devolucoes
DATA: 11/01/2026
"""

import logging
from typing import Dict, List, Optional

from app import db
from app.devolucao.models import NFDevolucao, OcorrenciaDevolucao
from app.monitoramento.models import EntregaMonitorada
from app.utils.timezone import agora_utc, agora_utc_naive

logger = logging.getLogger(__name__)

# Status que indicam devolucao no monitoramento
STATUS_DEVOLUCAO = ['Cancelada', 'Devolvida', 'Troca de NF']


class MonitoramentoSyncService:
    """
    Service para criar devolucoes baseadas no status do monitoramento

    Quando uma entrega e finalizada com status de devolucao (Cancelada,
    Devolvida, Troca de NF), mas ainda nao tem NFDevolucao vinculada,
    este service cria a NFDevolucao automaticamente.

    O status_odoo permanece vazio ate que seja enriquecido pelo Odoo.
    """

    # =========================================================================
    # SINCRONIZACAO COM MONITORAMENTO
    # =========================================================================

    def sincronizar_monitoramento(self) -> Dict:
        """
        Cria NFDevolucao para entregas com status de devolucao

        Busca entregas que:
        - Tem status_finalizacao em STATUS_DEVOLUCAO
        - NAO tem NFDevolucao vinculada ainda

        Returns:
            Dict com estatisticas da sincronizacao
        """
        logger.info("=" * 80)
        logger.info("INICIANDO SINCRONIZACAO COM MONITORAMENTO")
        logger.info("=" * 80)

        resultado = {
            'sucesso': False,
            'entregas_processadas': 0,
            'nfds_criadas': 0,
            'ocorrencias_criadas': 0,
            'erros': []
        }

        try:
            # 1. Buscar entregas com status de devolucao SEM NFDevolucao
            entregas = self._buscar_entregas_sem_nfd()

            if not entregas:
                logger.info("Nenhuma entrega pendente de NFDevolucao encontrada")
                resultado['sucesso'] = True
                return resultado

            logger.info(f"Total de entregas pendentes: {len(entregas)}")

            # 2. Processar cada entrega
            for entrega in entregas:
                try:
                    logger.info(f"\nProcessando entrega: {entrega.numero_nf} (ID {entrega.id})")

                    estatisticas = self._processar_entrega(entrega)

                    resultado['entregas_processadas'] += 1

                    if estatisticas.get('nfd_criada'):
                        resultado['nfds_criadas'] += 1
                    if estatisticas.get('ocorrencia_criada'):
                        resultado['ocorrencias_criadas'] += 1

                    # Commit apos cada entrega processada
                    db.session.commit()

                except Exception as e:
                    db.session.rollback()
                    erro_msg = f"Erro ao processar entrega {entrega.id}: {str(e)}"
                    logger.error(f"{erro_msg}")
                    resultado['erros'].append(erro_msg)

            resultado['sucesso'] = True
            logger.info("=" * 80)
            logger.info("SINCRONIZACAO COM MONITORAMENTO CONCLUIDA")
            logger.info(f"   Entregas processadas: {resultado['entregas_processadas']}")
            logger.info(f"   NFDs criadas: {resultado['nfds_criadas']}")
            logger.info(f"   Ocorrencias criadas: {resultado['ocorrencias_criadas']}")
            logger.info(f"   Erros: {len(resultado['erros'])}")
            logger.info("=" * 80)

            return resultado

        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro fatal na sincronizacao: {str(e)}"
            logger.error(f"{erro_msg}")
            resultado['erros'].append(erro_msg)
            resultado['sucesso'] = False
            return resultado

    def _buscar_entregas_sem_nfd(self) -> List[EntregaMonitorada]:
        """
        Busca entregas com status de devolucao que ainda nao tem NFDevolucao

        Returns:
            Lista de EntregaMonitorada
        """
        # Subquery para encontrar IDs de entregas que JA tem NFDevolucao
        entregas_com_nfd = db.session.query(
            NFDevolucao.entrega_monitorada_id
        ).filter(
            NFDevolucao.entrega_monitorada_id.isnot(None),
            NFDevolucao.ativo == True
        ).subquery()

        # Buscar entregas com status de devolucao SEM NFDevolucao
        entregas = EntregaMonitorada.query.filter(
            EntregaMonitorada.status_finalizacao.in_(STATUS_DEVOLUCAO),
            ~EntregaMonitorada.id.in_(entregas_com_nfd)
        ).all()

        return entregas

    def _processar_entrega(self, entrega: EntregaMonitorada) -> Dict:
        """
        Processa uma entrega e cria NFDevolucao

        Args:
            entrega: EntregaMonitorada com status de devolucao

        Returns:
            Dict com estatisticas
        """
        estatisticas = {
            'nfd_criada': False,
            'ocorrencia_criada': False,
        }

        # 1. Criar NFDevolucao
        nfd = self._criar_nfd_monitoramento(entrega)
        estatisticas['nfd_criada'] = True
        logger.info(f"   NFD criada: ID {nfd.id}")

        # 2. Criar OcorrenciaDevolucao
        ocorrencia = self._criar_ocorrencia_automatica(nfd, entrega)
        if ocorrencia:
            estatisticas['ocorrencia_criada'] = True
            logger.info(f"   Ocorrencia criada: {ocorrencia.numero_ocorrencia}")

        # 3. Marcar teve_devolucao na entrega
        if not entrega.teve_devolucao:
            entrega.teve_devolucao = True
            logger.info(f"   Entrega marcada como teve_devolucao=True")

        return estatisticas

    def _criar_nfd_monitoramento(self, entrega: EntregaMonitorada) -> NFDevolucao:
        """
        Cria NFDevolucao baseada na EntregaMonitorada

        Args:
            entrega: EntregaMonitorada

        Returns:
            NFDevolucao criada
        """
        # Definir motivo baseado no status
        motivo_map = {
            'Cancelada': 'CLIENTE',
            'Devolvida': 'OUTROS',
            'Troca de NF': 'OUTROS',
        }
        motivo = motivo_map.get(entrega.status_finalizacao, 'OUTROS')

        # Descricao baseada no status
        descricao_map = {
            'Cancelada': 'Entrega cancelada - mercadoria retornou',
            'Devolvida': 'Mercadoria devolvida pelo cliente',
            'Troca de NF': 'Necessidade de troca de Nota Fiscal',
        }
        descricao = descricao_map.get(entrega.status_finalizacao, 'Devolucao registrada pelo monitoramento')

        nfd = NFDevolucao(
            # Tipo e status
            tipo_documento='NF',
            status_odoo=None,  # Sera preenchido quando sincronizar com Odoo
            status_monitoramento=entrega.status_finalizacao,

            # Numero da NF (da entrega)
            numero_nfd=entrega.numero_nf or 'SEM_NUMERO',
            numero_nf_venda=entrega.numero_nf,

            # Cliente
            cnpj_emitente=getattr(entrega, 'cnpj_cliente', None),
            nome_emitente=getattr(entrega, 'cliente', None),

            # Vinculacao
            entrega_monitorada_id=entrega.id,

            # Controle
            origem_registro='MONITORAMENTO',
            status='REGISTRADA',

            # Motivo
            motivo=motivo,
            descricao_motivo=descricao,

            # Auditoria
            criado_em=agora_utc_naive(),
            criado_por='Sistema Monitoramento',
        )

        db.session.add(nfd)
        db.session.flush()

        return nfd

    def _criar_ocorrencia_automatica(
        self,
        nfd: NFDevolucao,
        entrega: EntregaMonitorada
    ) -> Optional[OcorrenciaDevolucao]:
        """
        Cria OcorrenciaDevolucao automaticamente

        Args:
            nfd: NFDevolucao criada
            entrega: EntregaMonitorada

        Returns:
            OcorrenciaDevolucao criada ou None se ja existir
        """
        # Verificar se ja existe ocorrencia
        ocorrencia_existente = OcorrenciaDevolucao.query.filter_by(
            nf_devolucao_id=nfd.id
        ).first()

        if ocorrencia_existente:
            return None

        # Definir localizacao baseada no status
        localizacao_map = {
            'Cancelada': 'EM_TRANSITO',
            'Devolvida': 'CLIENTE',
            'Troca de NF': 'CLIENTE',
        }
        localizacao = localizacao_map.get(entrega.status_finalizacao, 'INDEFINIDO')

        ocorrencia = OcorrenciaDevolucao(
            nf_devolucao_id=nfd.id,
            numero_ocorrencia=OcorrenciaDevolucao.gerar_numero_ocorrencia(),

            # Secao Logistica
            destino='INDEFINIDO',
            localizacao_atual=localizacao,

            # Secao Comercial
            status='ABERTA',
            responsavel='INDEFINIDO',
            origem='INDEFINIDO',

            # Auditoria
            criado_em=agora_utc_naive(),
            criado_por='Sistema Monitoramento',
        )

        db.session.add(ocorrencia)
        db.session.flush()

        return ocorrencia

    # =========================================================================
    # ATUALIZACAO DE STATUS
    # =========================================================================

    def atualizar_status_monitoramento(self, entrega_id: int) -> Dict:
        """
        Atualiza status_monitoramento de NFDevolucao quando entrega muda

        Chamado quando o status_finalizacao da entrega e atualizado.

        Args:
            entrega_id: ID da EntregaMonitorada

        Returns:
            Dict com resultado
        """
        try:
            from app import db
            entrega = db.session.get(EntregaMonitorada,entrega_id) if entrega_id else None
            if not entrega:
                return {'sucesso': False, 'erro': 'Entrega nao encontrada'}

            # Buscar NFDevolucao vinculada
            nfds = NFDevolucao.query.filter_by(
                entrega_monitorada_id=entrega_id,
                ativo=True
            ).all()

            atualizadas = 0
            for nfd in nfds:
                if entrega.status_finalizacao in STATUS_DEVOLUCAO:
                    nfd.status_monitoramento = entrega.status_finalizacao
                    nfd.atualizado_em = agora_utc_naive()
                    nfd.atualizado_por = 'Sistema Monitoramento'
                    atualizadas += 1

            if atualizadas > 0:
                db.session.commit()
                logger.info(f"Atualizadas {atualizadas} NFDs com status_monitoramento={entrega.status_finalizacao}")

            return {
                'sucesso': True,
                'nfds_atualizadas': atualizadas
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar status_monitoramento: {e}")
            return {'sucesso': False, 'erro': str(e)}


# =============================================================================
# FUNCOES HELPER
# =============================================================================

def get_monitoramento_sync_service() -> MonitoramentoSyncService:
    """Retorna instancia do MonitoramentoSyncService"""
    return MonitoramentoSyncService()


def sincronizar_monitoramento() -> Dict:
    """
    Funcao helper para sincronizar com monitoramento

    Returns:
        Dict com estatisticas
    """
    service = get_monitoramento_sync_service()
    return service.sincronizar_monitoramento()
