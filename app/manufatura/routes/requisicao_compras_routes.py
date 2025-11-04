"""
Rotas de Requisições de Compras
"""
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from datetime import datetime, timedelta
import logging

from app import db
from app.manufatura.models import RequisicaoCompras, HistoricoRequisicaoCompras
from app.odoo.services.requisicao_compras_service import RequisicaoComprasService

logger = logging.getLogger(__name__)


def register_requisicao_compras_routes(bp):
    """Registra rotas de requisições de compras"""

    @bp.route('/requisicoes-compras')
    @login_required
    def listar_requisicoes():
        """
        Lista todas as requisições de compras com filtros
        """
        try:
            # Filtros
            cod_produto = request.args.get('cod_produto', '').strip()
            status = request.args.get('status', '').strip()
            data_inicio = request.args.get('data_inicio', '').strip()
            data_fim = request.args.get('data_fim', '').strip()
            num_requisicao = request.args.get('num_requisicao', '').strip()

            # Query base
            query = RequisicaoCompras.query

            # Aplicar filtros
            if cod_produto:
                query = query.filter(RequisicaoCompras.cod_produto.like(f'%{cod_produto}%'))

            if status:
                query = query.filter(RequisicaoCompras.status == status)

            if num_requisicao:
                query = query.filter(RequisicaoCompras.num_requisicao.like(f'%{num_requisicao}%'))

            if data_inicio:
                data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                query = query.filter(RequisicaoCompras.data_requisicao_criacao >= data_inicio_dt)

            if data_fim:
                data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d').date()
                query = query.filter(RequisicaoCompras.data_requisicao_criacao <= data_fim_dt)

            # Ordenar por data de criação DESC
            query = query.order_by(RequisicaoCompras.data_requisicao_criacao.desc())

            # Paginação
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)

            requisicoes_paginadas = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )

            # Buscar status únicos para filtro
            status_lista = db.session.query(RequisicaoCompras.status).distinct().all()
            status_lista = [s[0] for s in status_lista if s[0]]

            return render_template(
                'manufatura/requisicoes_compras/listar.html',
                requisicoes=requisicoes_paginadas.items,
                paginacao=requisicoes_paginadas,
                status_lista=status_lista,
                filtros={
                    'cod_produto': cod_produto,
                    'status': status,
                    'data_inicio': data_inicio,
                    'data_fim': data_fim,
                    'num_requisicao': num_requisicao
                }
            )

        except Exception as e:
            logger.error(f"[REQUISICOES] Erro ao listar requisições: {e}")
            flash('Erro ao carregar requisições', 'danger')
            return render_template(
                'manufatura/requisicoes_compras/listar.html',
                requisicoes=[],
                paginacao=None,
                status_lista=[],
                filtros={}
            )

    @bp.route('/requisicoes-compras/sincronizar-manual')
    @login_required
    def tela_sincronizacao_manual():
        """
        Tela para sincronização manual com filtro de datas
        """
        # Sugerir últimos 7 dias como padrão
        data_fim_padrao = datetime.now()
        data_inicio_padrao = data_fim_padrao - timedelta(days=7)

        return render_template(
            'manufatura/requisicoes_compras/sincronizar_manual.html',
            data_inicio_padrao=data_inicio_padrao.strftime('%Y-%m-%d'),
            data_fim_padrao=data_fim_padrao.strftime('%Y-%m-%d')
        )

    @bp.route('/requisicoes-compras/sincronizar-manual', methods=['POST'])
    @login_required
    def executar_sincronizacao_manual():
        """
        Executa sincronização manual com período específico
        """
        try:
            data_inicio = request.form.get('data_inicio')
            data_fim = request.form.get('data_fim')

            if not data_inicio or not data_fim:
                flash('Datas de início e fim são obrigatórias', 'warning')
                return redirect(url_for('manufatura.tela_sincronizacao_manual'))

            # Converter para datetime
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')

            # Validar período
            if data_inicio_dt > data_fim_dt:
                flash('Data inicial não pode ser maior que data final', 'warning')
                return redirect(url_for('manufatura.tela_sincronizacao_manual'))

            diferenca_dias = (data_fim_dt - data_inicio_dt).days
            if diferenca_dias > 90:
                flash('Período máximo de sincronização: 90 dias', 'warning')
                return redirect(url_for('manufatura.tela_sincronizacao_manual'))

            # Calcular janela em minutos
            minutos_janela = diferenca_dias * 24 * 60

            logger.info(f"[REQUISICOES] Sincronização manual: {data_inicio} a {data_fim} ({diferenca_dias} dias)")

            # Executar sincronização
            service = RequisicaoComprasService()
            resultado = service.sincronizar_requisicoes_incremental(
                minutos_janela=minutos_janela,
                primeira_execucao=False  # ✅ SEMPRE aplicar filtro de data
            )

            if resultado.get('sucesso'):
                db.session.commit()

                mensagem = (
                    f"✅ Sincronização concluída! "
                    f"Novas: {resultado.get('requisicoes_novas', 0)}, "
                    f"Atualizadas: {resultado.get('requisicoes_atualizadas', 0)}, "
                    f"Processadas: {resultado.get('linhas_processadas', 0)}, "
                    f"Ignoradas: {resultado.get('linhas_ignoradas', 0)}"
                )
                flash(mensagem, 'success')
            else:
                erro = resultado.get('erro', 'Erro desconhecido')
                flash(f'❌ Erro na sincronização: {erro}', 'danger')

            return redirect(url_for('manufatura.listar_requisicoes'))

        except Exception as e:
            logger.error(f"[REQUISICOES] Erro na sincronização manual: {e}")
            flash(f'❌ Erro ao executar sincronização: {str(e)}', 'danger')
            return redirect(url_for('manufatura.tela_sincronizacao_manual'))

    @bp.route('/requisicoes-compras/<int:requisicao_id>')
    @login_required
    def detalhe_requisicao(requisicao_id):
        """
        Exibe detalhes de uma requisição e seu histórico
        """
        try:
            requisicao = RequisicaoCompras.query.get_or_404(requisicao_id)

            # Buscar histórico
            historico = HistoricoRequisicaoCompras.query.filter_by(
                requisicao_id=requisicao_id
            ).order_by(HistoricoRequisicaoCompras.alterado_em.desc()).all()

            return render_template(
                'manufatura/requisicoes_compras/detalhe.html',
                requisicao=requisicao,
                historico=historico
            )

        except Exception as e:
            logger.error(f"[REQUISICOES] Erro ao carregar detalhe: {e}")
            flash('Erro ao carregar detalhes da requisição', 'danger')
            return redirect(url_for('manufatura.listar_requisicoes'))

    @bp.route('/api/requisicoes-compras/<int:requisicao_id>/historico')
    @login_required
    def historico_requisicao_api(requisicao_id):
        """
        API para buscar histórico completo com comparação entre versões
        """
        try:
            # Buscar requisição
            requisicao = RequisicaoCompras.query.get_or_404(requisicao_id)

            # Buscar todos os snapshots ordenados (mais recente primeiro)
            snapshots = HistoricoRequisicaoCompras.query.filter_by(
                requisicao_id=requisicao_id
            ).order_by(HistoricoRequisicaoCompras.alterado_em.desc()).all()

            if not snapshots:
                return jsonify({
                    'sucesso': True,
                    'versoes': [],
                    'mensagem': 'Nenhum histórico encontrado'
                })

            # Comparar snapshots e identificar alterações
            versoes_com_alteracoes = []

            for i, snapshot_atual in enumerate(snapshots):
                versao = {
                    'id': snapshot_atual.id,
                    'operacao': snapshot_atual.operacao,
                    'data_hora': snapshot_atual.alterado_em.strftime('%d/%m/%Y %H:%M:%S'),
                    'usuario': snapshot_atual.alterado_por,
                    'alteracoes': []
                }

                # Comparar com versão anterior (se existir)
                if i < len(snapshots) - 1:
                    snapshot_anterior = snapshots[i + 1]

                    # Comparar TODOS os campos relevantes
                    campos_comparacao = [
                        ('qtd_produto_requisicao', 'Quantidade', lambda v: f"{float(v):,.3f}" if v else '0'),
                        ('status', 'Status', str),
                        ('data_requisicao_solicitada', 'Data Solicitada', lambda v: v.strftime('%d/%m/%Y') if v else '-'),
                        ('lead_time_requisicao', 'Lead Time', lambda v: f"{v} dias" if v else '-'),
                        ('observacoes_odoo', 'Observações', lambda v: v if v else '-'),
                        ('qtd_produto_sem_requisicao', 'Qtd Sem Requisição', lambda v: f"{float(v):,.3f}" if v else '0'),
                        ('necessidade', 'Necessidade', lambda v: 'Sim' if v else 'Não'),
                        ('data_necessidade', 'Data Necessidade', lambda v: v.strftime('%d/%m/%Y') if v else '-'),
                    ]

                    for campo_db, campo_label, formatar in campos_comparacao:
                        valor_atual = getattr(snapshot_atual, campo_db)
                        valor_anterior = getattr(snapshot_anterior, campo_db)

                        if valor_atual != valor_anterior:
                            versao['alteracoes'].append({
                                'campo': campo_label,
                                'antes': formatar(valor_anterior),
                                'depois': formatar(valor_atual)
                            })

                versoes_com_alteracoes.append(versao)

            return jsonify({
                'sucesso': True,
                'requisicao': {
                    'num_requisicao': requisicao.num_requisicao,
                    'cod_produto': requisicao.cod_produto,
                    'nome_produto': requisicao.nome_produto
                },
                'versoes': versoes_com_alteracoes
            })

        except Exception as e:
            logger.error(f"[REQUISICOES] Erro ao buscar histórico: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/api/requisicoes-compras/estatisticas')
    @login_required
    def estatisticas_requisicoes():
        """
        API para estatísticas do dashboard
        """
        try:
            # Total de requisições
            total = RequisicaoCompras.query.count()

            # Por status
            por_status = db.session.query(
                RequisicaoCompras.status,
                db.func.count(RequisicaoCompras.id)
            ).group_by(RequisicaoCompras.status).all()

            # Últimas 30 dias
            data_limite = datetime.now() - timedelta(days=30)
            ultimas_30_dias = RequisicaoCompras.query.filter(
                RequisicaoCompras.data_requisicao_criacao >= data_limite.date()
            ).count()

            # Produtos mais requisitados
            produtos_top = db.session.query(
                RequisicaoCompras.cod_produto,
                RequisicaoCompras.nome_produto,
                db.func.count(RequisicaoCompras.id).label('total')
            ).group_by(
                RequisicaoCompras.cod_produto,
                RequisicaoCompras.nome_produto
            ).order_by(db.text('total DESC')).limit(10).all()

            return jsonify({
                'sucesso': True,
                'total': total,
                'por_status': [{'status': s, 'total': t} for s, t in por_status],
                'ultimas_30_dias': ultimas_30_dias,
                'produtos_top': [
                    {'cod_produto': p[0], 'nome_produto': p[1], 'total': p[2]}
                    for p in produtos_top
                ]
            })

        except Exception as e:
            logger.error(f"[REQUISICOES] Erro ao buscar estatísticas: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500
