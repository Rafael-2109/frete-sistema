"""
Rotas de Gestão do Histórico de Pedidos
========================================

Funcionalidades:
- Visualização do histórico importado do Odoo
- Exportação para Excel
- Sincronização com Odoo por período
"""
from flask import render_template, jsonify, request, send_file
from flask_login import login_required, current_user
from app import db
from app.manufatura.models import HistoricoPedidos, GrupoEmpresarial
from app.odoo.utils.connection import get_odoo_connection
from datetime import datetime
from sqlalchemy import func, or_, extract
import pandas as pd
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


def register_historico_routes(bp):

    @bp.route('/historico-pedidos')
    @login_required
    def historico_pedidos():
        """Tela de gestão do histórico de pedidos"""
        return render_template('manufatura/historico_pedidos.html')

    @bp.route('/api/historico-pedidos/listar')
    @login_required
    def listar_historico():
        """Lista histórico de pedidos com filtros"""
        try:
            # Parâmetros de filtro
            data_inicio = request.args.get('data_inicio')
            data_fim = request.args.get('data_fim')
            grupo = request.args.get('grupo')
            cod_produto = request.args.get('cod_produto')
            num_pedido = request.args.get('num_pedido')
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 50))

            # Query base
            query = HistoricoPedidos.query

            # Filtros
            if data_inicio:
                query = query.filter(HistoricoPedidos.data_pedido >= data_inicio)
            if data_fim:
                query = query.filter(HistoricoPedidos.data_pedido <= data_fim)
            if grupo:
                query = query.filter(HistoricoPedidos.nome_grupo == grupo)
            if cod_produto:
                query = query.filter(HistoricoPedidos.cod_produto.ilike(f'%{cod_produto}%'))
            if num_pedido:
                query = query.filter(HistoricoPedidos.num_pedido.ilike(f'%{num_pedido}%'))

            # Paginação
            pagination = query.order_by(
                HistoricoPedidos.data_pedido.desc(),
                HistoricoPedidos.num_pedido
            ).paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )

            # Formata resultado
            registros = []
            for h in pagination.items:
                registros.append({
                    'id': h.id,
                    'num_pedido': h.num_pedido,
                    'data_pedido': h.data_pedido.strftime('%d/%m/%Y') if h.data_pedido else None,
                    'cnpj_cliente': h.cnpj_cliente,
                    'raz_social_red': h.raz_social_red,
                    'nome_grupo': h.nome_grupo,
                    'cod_produto': h.cod_produto,
                    'nome_produto': h.nome_produto,
                    'qtd_produto_pedido': float(h.qtd_produto_pedido or 0),
                    'preco_produto_pedido': float(h.preco_produto_pedido or 0),
                    'valor_produto_pedido': float(h.valor_produto_pedido or 0),
                    'nome_cidade': h.nome_cidade,
                    'cod_uf': h.cod_uf
                })

            return jsonify({
                'sucesso': True,
                'registros': registros,
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'total_pages': pagination.pages
            })

        except Exception as e:
            logger.error(f"Erro ao listar histórico: {e}", exc_info=True)
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/historico-pedidos/estatisticas')
    @login_required
    def estatisticas_historico():
        """Retorna estatísticas do histórico"""
        try:
            data_inicio = request.args.get('data_inicio')
            data_fim = request.args.get('data_fim')
            grupo = request.args.get('grupo')

            # Query base
            query = HistoricoPedidos.query

            # Filtros
            if data_inicio:
                query = query.filter(HistoricoPedidos.data_pedido >= data_inicio)
            if data_fim:
                query = query.filter(HistoricoPedidos.data_pedido <= data_fim)
            if grupo:
                query = query.filter(HistoricoPedidos.nome_grupo == grupo)

            # Estatísticas
            total_registros = query.count()
            total_pedidos = query.with_entities(
                func.count(func.distinct(HistoricoPedidos.num_pedido))
            ).scalar()
            total_produtos = query.with_entities(
                func.count(func.distinct(HistoricoPedidos.cod_produto))
            ).scalar()
            valor_total = query.with_entities(
                func.sum(HistoricoPedidos.valor_produto_pedido)
            ).scalar() or 0

            # Data do registro mais antigo e mais recente
            registro_mais_antigo = query.order_by(
                HistoricoPedidos.data_pedido.asc()
            ).first()
            registro_mais_recente = query.order_by(
                HistoricoPedidos.data_pedido.desc()
            ).first()

            return jsonify({
                'total_registros': total_registros,
                'total_pedidos': total_pedidos,
                'total_produtos': total_produtos,
                'valor_total': float(valor_total),
                'data_mais_antiga': registro_mais_antigo.data_pedido.strftime('%d/%m/%Y') if registro_mais_antigo else None,
                'data_mais_recente': registro_mais_recente.data_pedido.strftime('%d/%m/%Y') if registro_mais_recente else None
            })

        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}", exc_info=True)
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/historico-pedidos/exportar-excel')
    @login_required
    def exportar_historico_excel():
        """Exporta histórico para Excel"""
        try:
            # Parâmetros de filtro
            data_inicio = request.args.get('data_inicio')
            data_fim = request.args.get('data_fim')
            grupo = request.args.get('grupo')

            logger.info(f"[EXPORTAR] Período: {data_inicio} até {data_fim}, Grupo: {grupo}")

            # Query base
            query = HistoricoPedidos.query

            # Filtros
            if data_inicio:
                query = query.filter(HistoricoPedidos.data_pedido >= data_inicio)
            if data_fim:
                query = query.filter(HistoricoPedidos.data_pedido <= data_fim)
            if grupo:
                query = query.filter(HistoricoPedidos.nome_grupo == grupo)

            # Busca dados
            registros = query.order_by(
                HistoricoPedidos.data_pedido.desc(),
                HistoricoPedidos.num_pedido
            ).all()

            if not registros:
                return jsonify({'erro': 'Nenhum registro encontrado para exportar'}), 404

            logger.info(f"[EXPORTAR] Total de registros: {len(registros)}")

            # Monta dados para DataFrame
            dados = []
            for h in registros:
                dados.append({
                    'Número Pedido': h.num_pedido,
                    'Data Pedido': h.data_pedido.strftime('%d/%m/%Y') if h.data_pedido else '',
                    'CNPJ Cliente': h.cnpj_cliente,
                    'Razão Social': h.raz_social_red,
                    'Grupo': h.nome_grupo,
                    'Cidade': h.nome_cidade,
                    'UF': h.cod_uf,
                    'Código Produto': h.cod_produto,
                    'Nome Produto': h.nome_produto,
                    'Quantidade': float(h.qtd_produto_pedido or 0),
                    'Preço Unitário': float(h.preco_produto_pedido or 0),
                    'Valor Total': float(h.valor_produto_pedido or 0)
                })

            # Cria DataFrame
            df = pd.DataFrame(dados)

            # Cria arquivo Excel em memória
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Histórico Pedidos')

                # Ajusta largura das colunas
                worksheet = writer.sheets['Histórico Pedidos']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

            output.seek(0)

            # Nome do arquivo
            grupo_nome = grupo if grupo else 'TODOS'
            periodo = f"{data_inicio or 'inicio'}_{data_fim or 'fim'}"
            nome_arquivo = f'historico_pedidos_{periodo}_{grupo_nome}.xlsx'

            logger.info(f"[EXPORTAR] Arquivo gerado: {nome_arquivo}")

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=nome_arquivo
            )

        except Exception as e:
            logger.error(f"[EXPORTAR] Erro: {e}", exc_info=True)
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/historico-pedidos/sincronizar-odoo', methods=['POST'])
    @login_required
    def sincronizar_odoo():
        """Sincroniza histórico com Odoo (UPSERT)"""
        try:
            dados = request.json
            data_inicio = dados.get('data_inicio')
            data_fim = dados.get('data_fim')

            if not data_fim:
                return jsonify({'erro': 'Data fim é obrigatória'}), 400

            logger.info(f"[SYNC] Iniciando sincronização: {data_inicio} até {data_fim}")

            # Importa função do script
            from importar_historico_odoo import importar_historico_odoo, identificar_grupo_por_cnpj

            # Executa importação
            sucesso = importar_historico_odoo(
                data_inicio=data_inicio,
                data_fim=data_fim,
                lote=50
            )

            if sucesso:
                # Busca estatísticas após importação
                query = HistoricoPedidos.query.filter(
                    HistoricoPedidos.data_pedido <= data_fim
                )
                if data_inicio:
                    query = query.filter(HistoricoPedidos.data_pedido >= data_inicio)

                total_registros = query.count()

                return jsonify({
                    'sucesso': True,
                    'mensagem': f'Sincronização concluída com sucesso!',
                    'total_registros': total_registros
                })
            else:
                return jsonify({'erro': 'Falha na sincronização'}), 500

        except Exception as e:
            logger.error(f"[SYNC] Erro: {e}", exc_info=True)
            return jsonify({'erro': str(e)}), 500
