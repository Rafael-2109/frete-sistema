"""
Módulo universal para processar retorno de agendamentos Sendas
Atende todos os 3 fluxos: programacao_lote, carteira_agrupada, listar_entregas
"""

from typing import Dict, Any, List, Optional
from datetime import date, datetime
from sqlalchemy import and_
import logging

from app import db
from app.separacao.models import Separacao
from app.faturamento.models import FaturamentoProduto
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega

logger = logging.getLogger(__name__)


def processar_retorno_agendamento(resultado: Dict[str, Any]) -> bool:
    """
    Processa o retorno do agendamento universal, identificando origem e salvando protocolo

    Args:
        resultado: Dicionário com:
            - protocolo: Protocolo gerado
            - cnpj: CNPJ agendado
            - data_agendamento: Data de agendamento
            - data_expedicao: Data de expedição (opcional)
            - itens: Lista de itens processados com tipo_origem e id
            - tipo_fluxo: 'programacao_lote', 'carteira_agrupada', 'listar_entregas'
            - documento_origem: ID ou número do documento (para fluxos 2 e 3)

    Returns:
        True se processado com sucesso
    """
    try:
        protocolo = resultado.get('protocolo')
        data_agendamento = resultado.get('data_agendamento')
        data_expedicao = resultado.get('data_expedicao')
        itens = resultado.get('itens', [])
        tipo_fluxo = resultado.get('tipo_fluxo')
        documento_origem = resultado.get('documento_origem')

        if not protocolo:
            logger.error("❌ Protocolo não encontrado no resultado")
            return False

        logger.info(f"📝 Processando retorno do agendamento - Protocolo: {protocolo}, Fluxo: {tipo_fluxo}")

        # Processar baseado no tipo de fluxo
        if tipo_fluxo == 'programacao_lote':
            return _processar_fluxo_programacao_lote(
                itens, protocolo, data_agendamento, data_expedicao
            )

        elif tipo_fluxo == 'carteira_agrupada':
            return _processar_fluxo_carteira_agrupada(
                documento_origem, protocolo, data_agendamento, data_expedicao
            )

        elif tipo_fluxo == 'listar_entregas':
            return _processar_fluxo_listar_entregas(
                documento_origem, protocolo, data_agendamento
            )

        else:
            # Tentar identificar pela estrutura dos dados
            logger.warning(f"⚠️ Tipo de fluxo não especificado, tentando identificar...")
            return _processar_fluxo_generico(
                itens, protocolo, data_agendamento, data_expedicao, documento_origem
            )

    except Exception as e:
        logger.error(f"❌ Erro ao processar retorno do agendamento: {e}")
        db.session.rollback()
        return False


def _processar_fluxo_programacao_lote(_itens: List[Dict], protocolo: str,
                                      data_agendamento: date, data_expedicao: date) -> bool:
    """
    FLUXO 1: Programação em Lote
    UNIFICADO com Fluxo 2 - Ambos agora usam protocolo
    """
    # Parâmetro itens não é mais necessário pois usamos protocolo
    # Redireciona para o processamento unificado
    return _processar_fluxo_unificado_separacao(protocolo, data_agendamento, data_expedicao)


def _processar_fluxo_carteira_agrupada(_separacao_lote_id: str, protocolo: str,
                                       data_agendamento: date, data_expedicao: date) -> bool:
    """
    FLUXO 2: Carteira Agrupada
    UNIFICADO com Fluxo 1 - Ambos agora usam protocolo
    """
    # Parâmetro separacao_lote_id não é mais necessário pois usamos protocolo
    # Redireciona para o processamento unificado
    return _processar_fluxo_unificado_separacao(protocolo, data_agendamento, data_expedicao)


def _processar_fluxo_unificado_separacao(protocolo: str, data_agendamento: date,
                                         data_expedicao: date) -> bool:
    """
    FLUXO UNIFICADO 1+2: Programação em Lote e Carteira Agrupada
    - Busca SEMPRE por protocolo (agora ambos os fluxos criam Separações com protocolo)
    - Muda status='PREVISAO' para 'ABERTO' confirmando o agendamento
    - Preenche datas de agendamento e expedição
    - Define agendamento_confirmado=False inicialmente (será True quando confirmado)
    """
    try:
        # 1. Atualizar Separações com status='PREVISAO' para 'ABERTO'
        # Estas são as criadas especificamente para este agendamento
        resultado_previsao = Separacao.query.filter_by(
            protocolo=protocolo,
            status='PREVISAO'
        ).update({
            'status': 'ABERTO',  # Confirma que foi agendado com sucesso
            'agendamento': data_agendamento,
            'expedicao': data_expedicao,
            'agendamento_confirmado': False  # Aguarda confirmação posterior
            # NÃO mexer em observ_ped_1
        })

        # 2. Atualizar outras Separações com o mesmo protocolo
        # Estas já existiam (status != PREVISAO) mas receberam o protocolo
        resultado_outras = Separacao.query.filter(
            and_(
                Separacao.protocolo == protocolo,
                Separacao.status != 'PREVISAO'  # Corrigido: era != 'ABERTO' (bug)
            )
        ).update({
            'agendamento': data_agendamento,
            'expedicao': data_expedicao,
            'agendamento_confirmado': False  # Aguarda confirmação posterior
            # NÃO mexer em observ_ped_1 nem status
        })

        db.session.commit()

        total_atualizado = resultado_previsao + resultado_outras
        logger.info(f"✅ FLUXO UNIFICADO - Atualizado {total_atualizado} Separações com protocolo {protocolo}")
        logger.info(f"    {resultado_previsao} mudaram de PREVISAO para ABERTO")
        logger.info(f"    {resultado_outras} já existentes atualizadas com datas")

        return True

    except Exception as e:
        logger.error(f"❌ Erro no fluxo unificado de separação: {e}")
        db.session.rollback()
        return False


def _processar_fluxo_listar_entregas(numero_nf: str, protocolo: str, data_agendamento: date) -> bool:
    """
    FLUXO 3: Listar Entregas (NF)
    - Cria AgendamentoEntrega vinculado à EntregaMonitorada
    - Atualiza EntregaMonitorada com data_agenda
    - Fallback: atualiza FaturamentoProduto ou Separacao
    """
    try:
        # Buscar entrega monitorada
        entrega = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()

        if entrega:
            # Verificar se já existe agendamento
            agendamento_existente = AgendamentoEntrega.query.filter_by(
                entrega_id=entrega.id,
                protocolo_agendamento=protocolo,
                status='aguardando'
            ).first()

            if not agendamento_existente:
                # Criar AgendamentoEntrega
                agendamento = AgendamentoEntrega(
                    entrega_id=entrega.id,
                    data_agendada=data_agendamento,
                    forma_agendamento='Portal Sendas',
                    protocolo_agendamento=protocolo,
                    status='aguardando',
                    autor='Sistema',
                    criado_em=datetime.utcnow()
                )
                db.session.add(agendamento)
                logger.info(f"✅ Criado AgendamentoEntrega para NF {numero_nf}")

            # Atualizar EntregaMonitorada - APENAS data_agenda
            entrega.data_agenda = data_agendamento
            # NÃO ALTERAR: reagendar, status_entrega, status_finalização
            # Esses campos devem ser controlados por outras partes do sistema

        else:
            logger.warning(f"⚠️ EntregaMonitorada não encontrada para NF {numero_nf}, tentando fallbacks...")

            # Fallback 1: Atualizar FaturamentoProduto
            faturamentos = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()
            if faturamentos:
                for fat in faturamentos:
                    fat.observacoes = f"Protocolo Sendas: {protocolo} | Agendado: {data_agendamento.strftime('%d/%m/%Y')}"
                logger.info(f"✅ Atualizado {len(faturamentos)} itens de FaturamentoProduto")

            # Fallback 2: Atualizar Separacao
            separacoes = Separacao.query.filter_by(numero_nf=numero_nf).all()
            if separacoes:
                for sep in separacoes:
                    sep.protocolo = protocolo
                    sep.agendamento = data_agendamento
                    sep.agendamento_confirmado = False  # Aguarda confirmação
                    # NÃO mexer em observ_ped_1
                logger.info(f"✅ Atualizado {len(separacoes)} itens de Separacao")

        db.session.commit()
        logger.info(f"✅ FLUXO 3 - Processado agendamento para NF {numero_nf}")
        return True

    except Exception as e:
        logger.error(f"❌ Erro no fluxo listar entregas: {e}")
        db.session.rollback()
        return False


def _processar_fluxo_generico(itens: List[Dict], protocolo: str,
                              data_agendamento: date, data_expedicao: date,
                              documento_origem: Optional[str]) -> bool:
    """
    Processamento genérico quando o tipo de fluxo não é especificado
    Tenta identificar pela estrutura dos dados
    """
    try:
        # Se tem documento_origem e parece ser NF
        if documento_origem and isinstance(documento_origem, str):
            if documento_origem.isdigit() and len(documento_origem) >= 6:
                logger.info("📋 Identificado como possível NF, usando fluxo listar_entregas")
                return _processar_fluxo_listar_entregas(documento_origem, protocolo, data_agendamento)

        # Se tem itens com tipo_origem
        if itens and any(item.get('tipo_origem') for item in itens):
            logger.info("📋 Identificado como fluxo com itens detalhados, usando fluxo programação_lote")
            return _processar_fluxo_programacao_lote(itens, protocolo, data_agendamento, data_expedicao)

        # Se tem documento_origem que parece ser separacao_lote_id
        if documento_origem and '_' in str(documento_origem):
            logger.info("📋 Identificado como possível separacao_lote_id, usando fluxo carteira_agrupada")
            return _processar_fluxo_carteira_agrupada(documento_origem, protocolo, data_agendamento, data_expedicao)

        logger.error("❌ Não foi possível identificar o tipo de fluxo")
        return False

    except Exception as e:
        logger.error(f"❌ Erro no processamento genérico: {e}")
        db.session.rollback()
        return False


def marcar_agendamento_confirmado(protocolo: str) -> bool:
    """
    Marca agendamento como confirmado após processamento bem-sucedido
    Atualiza APENAS Separacao e AgendamentoEntrega (não mais CarteiraPrincipal)

    Args:
        protocolo: Protocolo do agendamento

    Returns:
        True se marcado com sucesso
    """
    try:
        # Atualizar Separacao - marca como confirmado
        separacao_count = Separacao.query.filter_by(
            protocolo=protocolo
        ).update({
            'agendamento_confirmado': True  # Confirma o agendamento
        })

        # Atualizar AgendamentoEntrega (para Fluxo 3)
        agendamento_count = AgendamentoEntrega.query.filter_by(
            protocolo_agendamento=protocolo
        ).update({
            'status': 'confirmado'
        })

        db.session.commit()
        logger.info(f"✅ Confirmado agendamento {protocolo}: {separacao_count} separações, {agendamento_count} entregas")
        return True

    except Exception as e:
        logger.error(f"❌ Erro ao confirmar agendamento: {e}")
        db.session.rollback()
        return False