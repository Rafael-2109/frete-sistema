"""
🔗 Serviço de Registro Local para Rastreamento de Motoristas

Funcionalidades (BANCO LOCAL - SEM ESCRITA NO ODOO):
- Criar NFD (nf_devolucao) quando motorista informar devolução
- Criar DespesaExtra quando houver pagamento de descarga
- Registrar info de pallet no embarque

IMPORTANTE: Este módulo NÃO escreve no Odoo, apenas no banco local.
Os dados gravados aqui podem ser sincronizados posteriormente por outros módulos.

Autor: Sistema de Rastreamento Nacom
Data: 2026-01-18
"""

from flask import current_app
from app import db
from app.utils.timezone import agora_brasil


class OdooRastreamentoIntegrationService:
    """
    Serviço de registro local para funcionalidades do rastreamento GPS.

    NOTA: Apesar do nome "Odoo", este serviço NÃO escreve no Odoo.
    Grava apenas no banco de dados local (PostgreSQL).
    O nome foi mantido por compatibilidade com código existente.
    """

    @staticmethod
    def criar_nfd_devolucao(numero_nfd: str, entrega_id: int, motivo: str = None):
        """
        Cria registro de NFD (Nota Fiscal de Devolução) vinculada à entrega
        no banco de dados LOCAL (não no Odoo).

        Args:
            numero_nfd: Número da NFD informado pelo motorista
            entrega_id: ID da EntregaRastreada
            motivo: Motivo da devolução

        Returns:
            dict: {'success': bool, 'nfd_id': int ou None, 'error': str ou None}
        """
        try:
            from app.rastreamento.models import EntregaRastreada
            from app.devolucao.models import NFDevolucao
            from app.monitoramento.models import EntregaMonitorada

            entrega = db.session.get(EntregaRastreada, entrega_id)
            if not entrega:
                return {'success': False, 'error': 'Entrega não encontrada'}

            # Verificar se NFD já existe
            nfd_existente = NFDevolucao.query.filter_by(numero_nf=numero_nfd).first()
            if nfd_existente:
                current_app.logger.info(f"ℹ️ NFD {numero_nfd} já existe - ID: {nfd_existente.id}")
                return {'success': True, 'nfd_id': nfd_existente.id, 'ja_existia': True}

            # Criar nova NFD no banco local
            nfd = NFDevolucao(
                numero_nf=numero_nfd,
                cnpj_cliente=entrega.cnpj_cliente,
                cliente=entrega.cliente,
                nf_origem=entrega.numero_nf,
                motivo_devolucao=motivo or 'Informado pelo motorista via rastreamento',
                status='PENDENTE',
                data_emissao=agora_brasil().date(),
                criado_por='Rastreamento GPS',
                criado_em=agora_brasil()
            )
            db.session.add(nfd)
            db.session.flush()

            # Atualizar EntregaMonitorada se existir
            if entrega.item and entrega.item.separacao_lote_id:
                entrega_mon = EntregaMonitorada.query.filter_by(
                    separacao_lote_id=entrega.item.separacao_lote_id
                ).first()
                if entrega_mon:
                    entrega_mon.teve_devolucao = True

            db.session.commit()
            current_app.logger.info(f"✅ NFD {numero_nfd} criada no banco local - ID: {nfd.id}")

            return {'success': True, 'nfd_id': nfd.id, 'ja_existia': False}

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Erro ao criar NFD: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def criar_despesa_descarga(entrega_id: int, valor: float, comprovante_path: str = None):
        """
        Cria DespesaExtra para pagamento de descarga no banco LOCAL (não no Odoo).

        Args:
            entrega_id: ID da EntregaRastreada
            valor: Valor pago de descarga
            comprovante_path: Caminho do comprovante (foto)

        Returns:
            dict: {'success': bool, 'despesa_id': int ou None, 'error': str ou None}
        """
        try:
            from app.rastreamento.models import EntregaRastreada
            from app.fretes.models import DespesaExtra, Frete

            entrega = db.session.get(EntregaRastreada, entrega_id)
            if not entrega:
                return {'success': False, 'error': 'Entrega não encontrada'}

            # Buscar embarque e frete relacionado
            rastreamento = entrega.rastreamento
            embarque = rastreamento.embarque

            # Buscar frete do embarque (via EmbarqueItem -> Frete)
            frete = None
            if embarque and embarque.itens:
                # Pegar o primeiro item com frete vinculado
                for item in embarque.itens:
                    if hasattr(item, 'frete_id') and item.frete_id:
                        frete = db.session.get(Frete, item.frete_id)
                        break

            if not frete:
                # Buscar frete pelo embarque_id
                frete = Frete.query.filter_by(embarque_id=embarque.id).first()

            if not frete:
                current_app.logger.warning(
                    f"⚠️ Nenhum frete encontrado para embarque #{embarque.id} - "
                    f"Despesa de descarga será registrada em log"
                )
                return {
                    'success': False,
                    'error': 'Frete não encontrado para vincular despesa',
                    'logged': True
                }

            # Criar DespesaExtra no banco local
            despesa = DespesaExtra(
                frete_id=frete.id,
                tipo_despesa='DESCARGA',
                motivo_despesa='AJUDANTE_ENTREGA',
                setor_responsavel='LOGÍSTICA',
                valor_despesa=valor,
                status='PENDENTE',
                observacoes=f'Pagamento de descarga informado pelo motorista via rastreamento. '
                           f'Entrega: {entrega.descricao_completa}',
                criado_em=agora_brasil(),
                criado_por='Rastreamento GPS'
            )

            # Salvar comprovante se fornecido
            if comprovante_path:
                despesa.observacoes += f'\nComprovante: {comprovante_path}'

            db.session.add(despesa)
            db.session.commit()

            current_app.logger.info(
                f"✅ DespesaExtra criada no banco local - Frete #{frete.id} | "
                f"Valor: R$ {valor:.2f} | ID: {despesa.id}"
            )

            return {'success': True, 'despesa_id': despesa.id, 'frete_id': frete.id}

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Erro ao criar DespesaExtra: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def registrar_pallet_info(embarque_id: int, pallet_data: dict):
        """
        Registra informações de pallet da entrega no banco LOCAL (não no Odoo).

        Args:
            embarque_id: ID do embarque
            pallet_data: {devolveu, quantidade_devolvida, vale_pallet, vale_pallet_path}

        Returns:
            dict: {'success': bool, 'error': str ou None}
        """
        try:
            from app.embarques.models import Embarque

            embarque = db.session.get(Embarque, embarque_id)
            if not embarque:
                return {'success': False, 'error': 'Embarque não encontrado'}

            # Atualizar campos de pallet físico no embarque
            if pallet_data.get('devolveu'):
                qtd_devolvida = pallet_data.get('quantidade_devolvida', 0)
                if embarque.qtd_pallets_trazidos is None:
                    embarque.qtd_pallets_trazidos = 0
                embarque.qtd_pallets_trazidos += qtd_devolvida

            db.session.commit()

            current_app.logger.info(
                f"✅ Info pallet registrada no banco local - Embarque #{embarque_id} | "
                f"Devolvido: {pallet_data.get('quantidade_devolvida', 0)}"
            )

            return {'success': True}

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Erro ao registrar pallet info: {str(e)}")
            return {'success': False, 'error': str(e)}
