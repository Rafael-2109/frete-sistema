"""
API de Faturamentos Parciais - Dashboard de Justificativas
==========================================================

Dashboard para gestão de faturamentos parciais e suas justificativas.
Permite visualizar e gerenciar divergências entre separação e faturamento.
"""

import logging
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import and_, or_
from app import db
from app.carteira.models import FaturamentoParcialJustificativa
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.separacao.models import Separacao
from app.utils.text_utils import truncar_observacao

logger = logging.getLogger(__name__)

faturamentos_parciais_bp = Blueprint('faturamentos_parciais', __name__, url_prefix='/carteira')


@faturamentos_parciais_bp.route('/faturamentos-parciais')
@login_required
def dashboard_faturamentos_parciais():
    """Dashboard principal de faturamentos parciais"""
    try:
        # Buscar justificativas pendentes (sem motivo ou classificação)
        justificativas_pendentes = FaturamentoParcialJustificativa.query.filter(
            or_(
                FaturamentoParcialJustificativa.motivo_nao_faturamento == '',
                FaturamentoParcialJustificativa.motivo_nao_faturamento.is_(None),
                FaturamentoParcialJustificativa.classificacao_saldo == '',
                FaturamentoParcialJustificativa.classificacao_saldo.is_(None)
            )
        ).order_by(FaturamentoParcialJustificativa.id.desc()).all()
        
        # Buscar justificativas resolvidas (com motivo e classificação)
        justificativas_resolvidas = FaturamentoParcialJustificativa.query.filter(
            and_(
                FaturamentoParcialJustificativa.motivo_nao_faturamento != '',
                FaturamentoParcialJustificativa.motivo_nao_faturamento.isnot(None),
                FaturamentoParcialJustificativa.classificacao_saldo != '',
                FaturamentoParcialJustificativa.classificacao_saldo.isnot(None)
            )
        ).order_by(FaturamentoParcialJustificativa.id.desc()).limit(100).all()
        
        # Enriquecer com dados do cliente
        justificativas_detalhadas = []
        for just in justificativas_pendentes:
            # Buscar dados da NF para obter o cliente
            nf_info = RelatorioFaturamentoImportado.query.filter_by(
                numero_nf=just.numero_nf
            ).first()
            
            # Buscar nome do produto
            produto_info = FaturamentoProduto.query.filter_by(
                numero_nf=just.numero_nf,
                cod_produto=just.cod_produto
            ).first()
            
            just_dict = {
                'id': just.id,
                'separacao_lote_id': just.separacao_lote_id,
                'num_pedido': just.num_pedido,
                'cod_produto': just.cod_produto,
                'nome_produto': produto_info.nome_produto if produto_info else 'Produto não encontrado',
                'numero_nf': just.numero_nf,
                'qtd_separada': float(just.qtd_separada),
                'qtd_faturada': float(just.qtd_faturada),
                'qtd_saldo': float(just.qtd_saldo),
                'percentual_divergencia': ((float(just.qtd_separada) - float(just.qtd_faturada)) / float(just.qtd_separada) * 100) if just.qtd_separada > 0 else 0,
                'motivo_nao_faturamento': just.motivo_nao_faturamento,
                'classificacao_saldo': just.classificacao_saldo,
                'descricao_detalhada': just.descricao_detalhada,
                'nome_cliente': nf_info.nome_cliente if nf_info else 'Cliente não encontrado',
                'cnpj_cliente': nf_info.cnpj_cliente if nf_info else '-'
            }
            justificativas_detalhadas.append(just_dict)
        
        # Estatísticas
        total_pendentes = len(justificativas_pendentes)
        total_resolvidas = len(justificativas_resolvidas)
        total_saldo = sum(j['qtd_saldo'] for j in justificativas_detalhadas)
        
        # Agrupar por motivo
        motivos_count = {}
        for just in justificativas_resolvidas:
            motivo = just.motivo_nao_faturamento or 'SEM_MOTIVO'
            motivos_count[motivo] = motivos_count.get(motivo, 0) + 1
        
        return render_template('carteira/faturamentos_parciais_dashboard.html',
                             justificativas=justificativas_detalhadas,
                             justificativas_resolvidas=justificativas_resolvidas,
                             total_pendentes=total_pendentes,
                             total_resolvidas=total_resolvidas,
                             total_saldo=total_saldo,
                             motivos_count=motivos_count)
                             
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard de faturamentos parciais: {e}")
        return render_template('carteira/faturamentos_parciais_dashboard.html',
                             erro=str(e),
                             justificativas=[],
                             justificativas_resolvidas=[],
                             total_pendentes=0,
                             total_resolvidas=0,
                             total_saldo=0,
                             motivos_count={})


@faturamentos_parciais_bp.route('/api/justificar-faturamento-parcial/<int:id>', methods=['POST'])
@login_required
def api_justificar_faturamento_parcial(id):
    """API para justificar faturamento parcial"""
    try:
        justificativa = FaturamentoParcialJustificativa.query.get_or_404(id)
        
        data = request.json
        
        # Validar campos obrigatórios
        if not data.get('motivo_nao_faturamento'):
            return jsonify({
                'sucesso': False,
                'erro': 'Motivo do não faturamento é obrigatório'
            }), 400
            
        if not data.get('classificacao_saldo'):
            return jsonify({
                'sucesso': False,
                'erro': 'Classificação do saldo é obrigatória'
            }), 400
        
        # Atualizar justificativa
        justificativa.motivo_nao_faturamento = data['motivo_nao_faturamento']
        justificativa.classificacao_saldo = data['classificacao_saldo']
        
        if data.get('descricao_detalhada'):
            justificativa.descricao_detalhada = data['descricao_detalhada']
            
        if data.get('acao_comercial'):
            justificativa.acao_comercial = data['acao_comercial']
            justificativa.data_acao = datetime.now()
            justificativa.executado_por = current_user.nome if hasattr(current_user, 'nome') else 'sistema'
            
        if data.get('observacoes_acao'):
            justificativa.observacoes_acao = data['observacoes_acao']
        
        # Se classificação é RETORNA_CARTEIRA, criar nova separação
        if justificativa.classificacao_saldo == 'RETORNA_CARTEIRA':
            # Buscar dados da carteira para preencher campos obrigatórios
            from app.carteira.models import CarteiraPrincipal
            item_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=justificativa.num_pedido,
                cod_produto=justificativa.cod_produto
            ).first()

            # Criar nova separação com status PREVISAO
            nova_sep = Separacao()
            nova_sep.separacao_lote_id = f"RETORNO_{justificativa.separacao_lote_id}"
            nova_sep.num_pedido = justificativa.num_pedido
            nova_sep.cod_produto = justificativa.cod_produto
            nova_sep.qtd_saldo = justificativa.qtd_saldo
            nova_sep.status = 'PREVISAO'
            nova_sep.observ_ped_1 = truncar_observacao(f"Retorno de faturamento parcial - NF {justificativa.numero_nf}")

            # Campos obrigatórios com fallback
            if item_carteira:
                nova_sep.nome_cidade = item_carteira.municipio or item_carteira.nome_cidade or "São Paulo"
                nova_sep.cod_uf = item_carteira.estado or item_carteira.cod_uf or "SP"
                nova_sep.cnpj_cpf = item_carteira.cnpj_cpf
                nova_sep.raz_social_red = item_carteira.raz_social_red
            else:
                # Fallback se não encontrar na carteira
                nova_sep.nome_cidade = "São Paulo"
                nova_sep.cod_uf = "SP"
                logger.warning(f"⚠️ Usando fallback de localização para retorno de faturamento parcial: {justificativa.num_pedido}/{justificativa.cod_produto}")
            nova_sep.sincronizado_nf = False
            db.session.add(nova_sep)
            
            justificativa.observacoes_acao = (justificativa.observacoes_acao or '') + f"\nCriada nova separação: {nova_sep.separacao_lote_id}"
        
        db.session.commit()
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Justificativa registrada com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao justificar faturamento parcial {id}: {e}")
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@faturamentos_parciais_bp.route('/api/estatisticas-faturamentos-parciais')
@login_required
def api_estatisticas_faturamentos_parciais():
    """API para obter estatísticas de faturamentos parciais"""
    try:
        # Total pendentes
        total_pendentes = FaturamentoParcialJustificativa.query.filter(
            or_(
                FaturamentoParcialJustificativa.motivo_nao_faturamento == '',
                FaturamentoParcialJustificativa.motivo_nao_faturamento.is_(None)
            )
        ).count()
        
        # Por motivo
        por_motivo = db.session.query(
            FaturamentoParcialJustificativa.motivo_nao_faturamento,
            db.func.count(FaturamentoParcialJustificativa.id),
            db.func.sum(FaturamentoParcialJustificativa.qtd_saldo)
        ).filter(
            FaturamentoParcialJustificativa.motivo_nao_faturamento.isnot(None),
            FaturamentoParcialJustificativa.motivo_nao_faturamento != ''
        ).group_by(
            FaturamentoParcialJustificativa.motivo_nao_faturamento
        ).all()
        
        # Por classificação
        por_classificacao = db.session.query(
            FaturamentoParcialJustificativa.classificacao_saldo,
            db.func.count(FaturamentoParcialJustificativa.id),
            db.func.sum(FaturamentoParcialJustificativa.qtd_saldo)
        ).filter(
            FaturamentoParcialJustificativa.classificacao_saldo.isnot(None),
            FaturamentoParcialJustificativa.classificacao_saldo != ''
        ).group_by(
            FaturamentoParcialJustificativa.classificacao_saldo
        ).all()
        
        return jsonify({
            'sucesso': True,
            'estatisticas': {
                'total_pendentes': total_pendentes,
                'por_motivo': [
                    {'motivo': motivo, 'quantidade': count, 'saldo_total': float(saldo or 0)}
                    for motivo, count, saldo in por_motivo
                ],
                'por_classificacao': [
                    {'classificacao': classif, 'quantidade': count, 'saldo_total': float(saldo or 0)}
                    for classif, count, saldo in por_classificacao
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@faturamentos_parciais_bp.route('/api/exportar-faturamentos-parciais')
@login_required
def api_exportar_faturamentos_parciais():
    """API para exportar faturamentos parciais para Excel"""
    try:
        import pandas as pd
        from flask import send_file
        import io
        
        # Buscar todos os registros
        justificativas = FaturamentoParcialJustificativa.query.all()
        
        # Preparar dados para exportação
        dados = []
        for just in justificativas:
            dados.append({
                'Lote': just.separacao_lote_id,
                'Pedido': just.num_pedido,
                'NF': just.numero_nf,
                'Produto': just.cod_produto,
                'Qtd Separada': float(just.qtd_separada),
                'Qtd Faturada': float(just.qtd_faturada),
                'Saldo': float(just.qtd_saldo),
                'Motivo': just.motivo_nao_faturamento or 'PENDENTE',
                'Classificação': just.classificacao_saldo or 'PENDENTE',
                'Ação Comercial': just.acao_comercial or '-',
                'Data Criação': just.criado_em.strftime('%d/%m/%Y %H:%M')
            })
        
        # Criar DataFrame
        df = pd.DataFrame(dados)
        
        # Criar arquivo Excel em memória
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Faturamentos Parciais', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'faturamentos_parciais_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar faturamentos parciais: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500