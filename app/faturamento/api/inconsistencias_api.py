"""
API de Inconsistências - Dashboard Unificado
============================================

Dashboard centralizado para gestão de todas as inconsistências do sistema.
Unifica inconsistências de faturamento e embarques com erro.
"""

import logging
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from datetime import datetime
from sqlalchemy import and_
from app.utils.timezone import agora_utc_naive
from app import db
from app.carteira.models import InconsistenciaFaturamento
from app.embarques.models import EmbarqueItem, Embarque
from app.faturamento.models import RelatorioFaturamentoImportado
from app.faturamento.services.atualizar_nf_embarque import buscar_nf_por_lote

logger = logging.getLogger(__name__)

inconsistencias_bp = Blueprint('inconsistencias', __name__, url_prefix='/faturamento')


@inconsistencias_bp.route('/inconsistencias')
@login_required
def dashboard_inconsistencias():
    """Dashboard principal de inconsistências"""
    try:
        # Debug - verificar total de registros
        total_registros = InconsistenciaFaturamento.query.count()
        logger.info(f"Total de inconsistências no banco: {total_registros}")
        
        # 1. Buscar inconsistências de faturamento não resolvidas
        inconsistencias = InconsistenciaFaturamento.query.filter_by(
            resolvida=False
        ).order_by(InconsistenciaFaturamento.id.desc()).all()
        
        logger.info(f"Inconsistências não resolvidas: {len(inconsistencias)}")
        
        # Enriquecer inconsistências com dados do cliente
        inconsistencias_detalhadas = []
        for inc in inconsistencias:
            # Buscar dados da NF para obter o cliente
            nf_info = RelatorioFaturamentoImportado.query.filter_by(
                numero_nf=inc.numero_nf
            ).first()
            
            # Criar objeto enriquecido mantendo a estrutura original
            inc.nome_cliente = nf_info.nome_cliente if nf_info else 'Cliente não encontrado'
            inconsistencias_detalhadas.append(inc)
        
        # Contar por tipo
        total_inconsistencias = len(inconsistencias)
        total_sem_separacao = len([i for i in inconsistencias if i.tipo == 'NF_SEM_SEPARACAO'])
        total_divergencia = len([i for i in inconsistencias if i.tipo == 'DIVERGENCIA_NF_EMBARQUE'])
        
        logger.info(f"Tipos encontrados: {set(i.tipo for i in inconsistencias)}")
        
        # 2. Buscar embarques com erro
        embarques_erro = db.session.query(EmbarqueItem).join(
            Embarque, EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            and_(
                EmbarqueItem.erro_validacao.isnot(None),
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            )
        ).all()
        
        # Enriquecer dados dos embarques com NF sugerida
        embarques_erro_detalhados = []
        for item in embarques_erro:
            nf_sugerida = buscar_nf_por_lote(item.separacao_lote_id) if item.separacao_lote_id else None
            embarques_erro_detalhados.append({
                'id': item.id,
                'embarque_id': item.embarque_id,
                'separacao_lote_id': item.separacao_lote_id,
                'num_pedido': item.pedido,
                'nome_cliente': item.cliente,  # Já está correto como nome_cliente
                'erro_validacao': item.erro_validacao,
                'nf_sugerida': nf_sugerida
            })
        
        total_embarques_erro = len(embarques_erro)
        
        # 3. Contar resolvidas hoje (como não há campo de data, usar 0)
        resolvidas_hoje = 0
        
        return render_template('faturamento/inconsistencias_dashboard.html',
                             inconsistencias=inconsistencias_detalhadas,
                             total_inconsistencias=total_inconsistencias,
                             total_sem_separacao=total_sem_separacao,
                             total_divergencia=total_divergencia,
                             total_embarques_erro=total_embarques_erro,
                             embarques_erro=embarques_erro_detalhados,
                             resolvidas_hoje=resolvidas_hoje)
                             
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard de inconsistências: {e}")
        return render_template('faturamento/inconsistencias_dashboard.html',
                             erro=str(e),
                             inconsistencias=[],
                             total_inconsistencias=0,
                             total_sem_separacao=0,
                             total_divergencia=0,
                             total_embarques_erro=0,
                             embarques_erro=[],
                             resolvidas_hoje=0)


@inconsistencias_bp.route('/api/resolver-inconsistencia/<int:id>', methods=['POST'])
@login_required
def api_resolver_inconsistencia(id):
    """API para marcar inconsistência como resolvida"""
    try:
        from flask_login import current_user
        inconsistencia = InconsistenciaFaturamento.query.get_or_404(id)
        
        # Marcar como resolvida
        inconsistencia.resolvida = True
        inconsistencia.resolvida_em = agora_utc_naive()
        inconsistencia.resolvida_por = current_user.nome if hasattr(current_user, 'nome') else 'sistema'
        
        # Adicionar ação tomada se fornecida
        if request.json and request.json.get('acao_tomada'):
            inconsistencia.acao_tomada = request.json['acao_tomada']
        
        # Adicionar observação de resolução
        if request.json and request.json.get('observacao'):
            obs_adicional = f"\n\nRESOLVIDO: {request.json['observacao']}"
            if inconsistencia.observacao_resolucao:
                inconsistencia.observacao_resolucao += obs_adicional
            else:
                inconsistencia.observacao_resolucao = obs_adicional.strip()
        else:
            obs_adicional = f"\n\nRESOLVIDO em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            if inconsistencia.observacao_resolucao:
                inconsistencia.observacao_resolucao += obs_adicional
            else:
                inconsistencia.observacao_resolucao = obs_adicional.strip()
        
        db.session.commit()
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Inconsistência resolvida com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao resolver inconsistência {id}: {e}")
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@inconsistencias_bp.route('/api/estatisticas-inconsistencias')
@login_required
def api_estatisticas_inconsistencias():
    """API para obter estatísticas de inconsistências"""
    try:
        # Total não resolvidas
        total_abertas = InconsistenciaFaturamento.query.filter_by(resolvida=False).count()
        
        # Por tipo
        por_tipo = db.session.query(
            InconsistenciaFaturamento.tipo,
            db.func.count(InconsistenciaFaturamento.id)
        ).filter_by(
            resolvida=False
        ).group_by(
            InconsistenciaFaturamento.tipo
        ).all()
        
        # Como não há campos de data, retornar 0
        criadas_24h = 0
        resolvidas_24h = 0
        
        return jsonify({
            'sucesso': True,
            'estatisticas': {
                'total_abertas': total_abertas,
                'por_tipo': {tipo: count for tipo, count in por_tipo},
                'criadas_24h': criadas_24h,
                'resolvidas_24h': resolvidas_24h
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@inconsistencias_bp.route('/api/debug-dados')
@login_required
def api_debug_dados():
    """API temporária para verificar dados no banco"""
    try:
        # Contar total de registros
        total_inc = InconsistenciaFaturamento.query.count()
        total_nao_resolvidas = InconsistenciaFaturamento.query.filter_by(resolvida=False).count()
        
        # Buscar algumas inconsistências
        amostra = InconsistenciaFaturamento.query.limit(5).all()
        amostra_dados = []
        for inc in amostra:
            amostra_dados.append({
                'id': inc.id,
                'numero_nf': inc.numero_nf,
                'tipo': inc.tipo,
                'resolvida': inc.resolvida
            })
        
        # Embarques com erro
        total_embarques = EmbarqueItem.query.count()
        embarques_erro = EmbarqueItem.query.filter(
            EmbarqueItem.erro_validacao.isnot(None)
        ).count()
        
        return jsonify({
            'sucesso': True,
            'debug': {
                'inconsistencias': {
                    'total': total_inc,
                    'nao_resolvidas': total_nao_resolvidas,
                    'amostra': amostra_dados
                },
                'embarques': {
                    'total': total_embarques,
                    'com_erro': embarques_erro
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Erro no debug: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@inconsistencias_bp.route('/api/limpar-resolvidas', methods=['POST'])
@login_required
def api_limpar_resolvidas():
    """API para limpar inconsistências resolvidas"""
    try:
        # Como não há campo de data, deletar todas resolvidas
        deletadas = InconsistenciaFaturamento.query.filter(
            InconsistenciaFaturamento.resolvida == True
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'{deletadas} inconsistências antigas removidas'
        })
        
    except Exception as e:
        logger.error(f"Erro ao limpar inconsistências: {e}")
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500