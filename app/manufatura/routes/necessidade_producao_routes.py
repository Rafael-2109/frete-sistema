"""
Rotas de Necessidade de Produção
"""
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from datetime import datetime


def register_necessidade_producao_routes(bp):

    @bp.route('/necessidade-producao')
    @login_required
    def necessidade_producao():
        """Tela de análise de necessidade de produção"""
        return render_template('manufatura/necessidade_producao/index.html')

    @bp.route('/api/necessidade-producao/calcular')
    @login_required
    def calcular_necessidade():
        """Calcula necessidade de produção por produto"""
        try:
            from app.manufatura.services.necessidade_producao_service import NecessidadeProducaoService

            mes = request.args.get('mes', datetime.now().month, type=int)
            ano = request.args.get('ano', datetime.now().year, type=int)
            cod_produto = request.args.get('cod_produto')

            service = NecessidadeProducaoService()
            resultado = service.calcular_necessidade_producao(mes, ano, cod_produto)

            return jsonify(resultado)

        except Exception as e:
            import logging
            logging.error(f"[NECESSIDADE] Erro ao calcular: {str(e)}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/necessidade-producao/projecao-estoque')
    @login_required
    def projecao_estoque():
        """Retorna projeção de estoque D0-D60 para um produto"""
        try:
            from app.manufatura.services.necessidade_producao_service import NecessidadeProducaoService

            cod_produto = request.args.get('cod_produto')
            if not cod_produto:
                return jsonify({'erro': 'Código do produto é obrigatório'}), 400

            service = NecessidadeProducaoService()
            projecao = service.calcular_projecao_estoque(cod_produto)

            return jsonify(projecao)

        except Exception as e:
            import logging
            logging.error(f"[PROJECAO] Erro ao calcular: {str(e)}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/necessidade-producao/programar', methods=['POST'])
    @login_required
    def programar_producao():
        """Programa produção para um produto"""
        try:
            from app.manufatura.services.necessidade_producao_service import NecessidadeProducaoService

            dados = request.json
            cod_produto = dados.get('cod_produto')
            quantidade = dados.get('quantidade')
            data_programada = dados.get('data_programada')

            if not all([cod_produto, quantidade]):
                return jsonify({'erro': 'Dados incompletos'}), 400

            service = NecessidadeProducaoService()
            resultado = service.programar_producao(
                cod_produto=cod_produto,
                quantidade=quantidade,
                data_programada=data_programada,
                usuario=current_user.nome if current_user.is_authenticated else 'Sistema'
            )

            return jsonify(resultado)

        except Exception as e:
            import logging
            logging.error(f"[PROGRAMAR] Erro ao programar: {str(e)}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/necessidade-producao/separacoes')
    @login_required
    def listar_separacoes():
        """Lista separações (sincronizado_nf=False) de um produto"""
        try:
            from app.separacao.models import Separacao
            from app.carteira.models import CarteiraPrincipal
            from sqlalchemy import func
            from collections import defaultdict

            cod_produto = request.args.get('cod_produto')
            if not cod_produto:
                return jsonify({'erro': 'Código do produto é obrigatório'}), 400

            # Buscar separações não sincronizadas
            separacoes = Separacao.query.filter(
                Separacao.cod_produto == cod_produto,
                Separacao.sincronizado_nf == False
            ).order_by(Separacao.expedicao).all()

            # Calcular total sem separação
            total_carteira = db.session.query(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
            ).filter(CarteiraPrincipal.cod_produto == cod_produto).scalar()

            total_carteira = float(total_carteira) if total_carteira else 0.0
            total_separado = sum(float(sep.qtd_saldo or 0) for sep in separacoes)
            total_sem_separacao = total_carteira - total_separado

            # Agrupar por dia
            por_dia = defaultdict(lambda: {'separacoes': [], 'saidas': 0, 'entradas': 0, 'estoque_inicial': 0, 'saldo_final': 0})

            for sep in separacoes:
                dia_key = sep.expedicao.strftime('%Y-%m-%d') if sep.expedicao else 'sem_data'
                por_dia[dia_key]['separacoes'].append({
                    'separacao_lote_id': sep.separacao_lote_id,
                    'num_pedido': sep.num_pedido,
                    'cnpj_cpf': sep.cnpj_cpf,
                    'raz_social_red': sep.raz_social_red,
                    'nome_cidade': sep.nome_cidade,
                    'cod_uf': sep.cod_uf,
                    'qtd_saldo': float(sep.qtd_saldo) if sep.qtd_saldo else 0,
                    'valor_saldo': float(sep.valor_saldo) if sep.valor_saldo else 0,
                    'peso': float(sep.peso) if sep.peso else 0,
                    'expedicao': sep.expedicao.strftime('%Y-%m-%d') if sep.expedicao else None,
                    'agendamento': sep.agendamento.strftime('%Y-%m-%d') if sep.agendamento else None,
                    'protocolo': sep.protocolo,
                    'status': sep.status,
                    'observ_ped_1': sep.observ_ped_1
                })
                por_dia[dia_key]['saidas'] += float(sep.qtd_saldo) if sep.qtd_saldo else 0

            # Converter defaultdict para dict normal
            por_dia_dict = dict(por_dia)

            return jsonify({
                'separacoes': [s for dia in por_dia_dict.values() for s in dia['separacoes']],
                'por_dia': por_dia_dict,
                'total_sem_separacao': float(total_sem_separacao),
                'total_separado': float(total_separado),
                'total_carteira': float(total_carteira)
            })

        except Exception as e:
            import logging
            logging.error(f"[SEPARACOES] Erro ao listar: {str(e)}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/necessidade-producao/separacao-detalhes')
    @login_required
    def detalhes_separacao():
        """Retorna detalhes completos de uma separação"""
        try:
            from app.separacao.models import Separacao

            separacao_lote_id = request.args.get('separacao_lote_id')
            if not separacao_lote_id:
                return jsonify({'erro': 'ID da separação é obrigatório'}), 400

            # Buscar todas as separações do lote
            separacoes = Separacao.query.filter(
                Separacao.separacao_lote_id == separacao_lote_id
            ).all()

            if not separacoes:
                return jsonify({'erro': 'Separação não encontrada'}), 404

            # Primeira separação tem dados gerais
            sep_principal = separacoes[0]

            resultado = {
                'separacao_lote_id': sep_principal.separacao_lote_id,
                'num_pedido': sep_principal.num_pedido,
                'cnpj_cpf': sep_principal.cnpj_cpf,
                'raz_social_red': sep_principal.raz_social_red,
                'nome_cidade': sep_principal.nome_cidade,
                'cod_uf': sep_principal.cod_uf,
                'expedicao': sep_principal.expedicao.strftime('%Y-%m-%d') if sep_principal.expedicao else None,
                'agendamento': sep_principal.agendamento.strftime('%Y-%m-%d') if sep_principal.agendamento else None,
                'protocolo': sep_principal.protocolo,
                'status': sep_principal.status,
                'observ_ped_1': sep_principal.observ_ped_1,
                'itens': []
            }

            # Todos os itens da separação
            for sep in separacoes:
                resultado['itens'].append({
                    'cod_produto': sep.cod_produto,
                    'nome_produto': getattr(sep, 'nome_produto', ''),
                    'qtd_saldo': float(sep.qtd_saldo) if sep.qtd_saldo else 0,
                    'valor_saldo': float(sep.valor_saldo) if sep.valor_saldo else 0,
                    'peso': float(sep.peso) if sep.peso else 0,
                    'pallet': float(sep.pallet) if sep.pallet else 0
                })

            return jsonify(resultado)

        except Exception as e:
            import logging
            logging.error(f"[DETALHES] Erro ao buscar: {str(e)}")
            return jsonify({'erro': str(e)}), 500
