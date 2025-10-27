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

            # Buscar separações não sincronizadas (saídas)
            separacoes = Separacao.query.filter(
                Separacao.cod_produto == cod_produto,
                Separacao.sincronizado_nf == False
            ).order_by(Separacao.expedicao).all()

            # Buscar estoque atual usando ServicoEstoqueSimples
            from app.estoque.services.estoque_simples import ServicoEstoqueSimples
            from app.producao.models import ProgramacaoProducao
            from datetime import date

            estoque_service = ServicoEstoqueSimples()
            estoque_atual = estoque_service.calcular_estoque_atual(cod_produto)

            # Calcular total sem separação
            total_carteira_raw = db.session.query(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
            ).filter(CarteiraPrincipal.cod_produto == cod_produto).scalar()

            total_carteira = float(total_carteira_raw) if total_carteira_raw is not None else 0.0
            total_separado = sum(float(sep.qtd_saldo or 0) for sep in separacoes)
            total_sem_separacao = total_carteira - total_separado

            # Buscar programações de produção (entradas futuras)
            hoje = date.today()
            programacoes = ProgramacaoProducao.query.filter(
                ProgramacaoProducao.cod_produto == cod_produto,
                ProgramacaoProducao.data_programacao >= hoje
            ).order_by(ProgramacaoProducao.data_programacao).all()

            # Agrupar programações por dia
            entradas_por_dia = defaultdict(float)
            for prog in programacoes:
                dia_key = prog.data_programacao.strftime('%Y-%m-%d')
                entradas_por_dia[dia_key] += float(prog.qtd_programada)

            # Agrupar saídas por dia
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

            # Calcular estoque acumulado dia a dia
            # ✅ CORREÇÃO: Filtrar apenas dias com data válida (ignorar 'sem_data')
            dias_validos = [d for d in por_dia.keys() if d != 'sem_data']
            dias_ordenados = sorted(dias_validos)
            saldo_acumulado = estoque_atual

            dia_anterior = None
            for dia in dias_ordenados:
                # Estoque inicial do dia = saldo acumulado do dia anterior
                por_dia[dia]['estoque_inicial'] = saldo_acumulado

                # Entradas acumuladas desde o dia posterior ao anterior até o dia atual
                entradas_acumuladas = 0.0
                if dia_anterior:
                    # Buscar entradas entre dia_anterior+1 e dia atual
                    data_inicio = date.fromisoformat(dia_anterior)
                    data_fim = date.fromisoformat(dia)

                    # Iterar pelos dias intermediários
                    from datetime import timedelta
                    data_atual = data_inicio + timedelta(days=1)
                    while data_atual <= data_fim:
                        dia_key_intermediario = data_atual.strftime('%Y-%m-%d')
                        entradas_acumuladas += entradas_por_dia.get(dia_key_intermediario, 0.0)
                        data_atual += timedelta(days=1)
                else:
                    # Primeiro dia: incluir entradas do próprio dia
                    entradas_acumuladas = entradas_por_dia.get(dia, 0.0)

                por_dia[dia]['entradas'] = entradas_acumuladas

                # Saldo final = estoque inicial + entradas - saídas
                por_dia[dia]['saldo_final'] = (
                    por_dia[dia]['estoque_inicial'] +
                    por_dia[dia]['entradas'] -
                    por_dia[dia]['saidas']
                )

                # Atualizar saldo acumulado para próxima iteração
                saldo_acumulado = por_dia[dia]['saldo_final']
                dia_anterior = dia

            # ✅ Para 'sem_data': deixar valores zerados (já está no defaultdict)
            # Não calcular estoque para separações sem data de expedição

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
            import traceback
            logging.error(f"[SEPARACOES] Erro ao listar: {str(e)}")
            logging.error(f"[SEPARACOES] Traceback: {traceback.format_exc()}")
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

    @bp.route('/api/necessidade-producao/recursos-produtivos')
    @login_required
    def recursos_produtivos():
        """Retorna dados para modal de Recursos Produtivos"""
        try:
            from app.manufatura.models import RecursosProducao
            from app.producao.models import ProgramacaoProducao
            from app.estoque.services.estoque_simples import ServicoEstoqueSimples
            from datetime import date, timedelta
            from collections import defaultdict

            cod_produto = request.args.get('cod_produto')
            mes = request.args.get('mes', type=int)
            ano = request.args.get('ano', type=int)

            if not cod_produto:
                return jsonify({'erro': 'Código do produto é obrigatório'}), 400

            # Usar mês/ano atual se não fornecido
            hoje = date.today()
            if not mes:
                mes = hoje.month
            if not ano:
                ano = hoje.year

            # 1. Buscar recursos de produção para o produto
            recursos = RecursosProducao.query.filter_by(
                cod_produto=cod_produto,
                disponivel=True
            ).all()

            if not recursos:
                return jsonify({
                    'recursos': [],
                    'linhas': [],
                    'mensagem': 'Produto não possui linhas de produção cadastradas'
                }), 200

            # 2. Buscar primeiro dia com falta de estoque (estoque < 0) e calcular estoque por dia
            estoque_service = ServicoEstoqueSimples()
            projecao_resultado = estoque_service.calcular_projecao(cod_produto, dias=60)

            # ✅ CORREÇÃO: O serviço retorna 'projecao' (array) e 'dia_ruptura'
            primeiro_dia_falta = projecao_resultado.get('dia_ruptura')  # Já vem no formato correto
            estoque_por_dia = {}

            # Converter array de projeção para dict por data
            for dia_dados in projecao_resultado.get('projecao', []):
                data_key = dia_dados.get('data')  # Já vem em formato ISO 'YYYY-MM-DD'
                if data_key:
                    estoque_por_dia[data_key] = {
                        'estoque_inicial': float(dia_dados.get('saldo_inicial', 0)),
                        'saidas': float(dia_dados.get('saida', 0)),
                        'entradas': float(dia_dados.get('entrada', 0)),
                        'saldo_final': float(dia_dados.get('saldo_final', 0))
                    }

            # 3. Buscar programação de produção para o mês solicitado
            data_inicio = date(ano, mes, 1)
            if mes == 12:
                data_fim = date(ano + 1, 1, 1) - timedelta(days=1)
            else:
                data_fim = date(ano, mes + 1, 1) - timedelta(days=1)

            # Buscar programações de TODAS as linhas (não filtrar por produto)
            # para mostrar ocupação total de cada linha
            programacoes = ProgramacaoProducao.query.filter(
                ProgramacaoProducao.data_programacao >= data_inicio,
                ProgramacaoProducao.data_programacao <= data_fim,
                ProgramacaoProducao.linha_producao.isnot(None)  # Apenas com linha definida
            ).order_by(ProgramacaoProducao.data_programacao).all()

            # 4. Agrupar programações por linha e data
            prog_por_linha = defaultdict(lambda: defaultdict(list))
            produtos_programados = set()  # ✅ NOVO: Coletar produtos únicos

            for prog in programacoes:
                if prog.linha_producao:
                    dia_key = prog.data_programacao.strftime('%Y-%m-%d')
                    prog_por_linha[prog.linha_producao][dia_key].append({
                        'cod_produto': prog.cod_produto,
                        'nome_produto': prog.nome_produto,
                        'qtd_programada': float(prog.qtd_programada)
                    })
                    produtos_programados.add(prog.cod_produto)  # ✅ NOVO

            # 4.5. ✅ NOVO: Buscar projeção de estoque de TODOS os produtos programados
            estoque_por_produto = {}
            for cod_prod in produtos_programados:
                try:
                    proj = estoque_service.calcular_projecao(cod_prod, dias=60)
                    estoque_por_produto[cod_prod] = {}

                    for dia_dados in proj.get('projecao', []):
                        data_key = dia_dados.get('data')
                        if data_key:
                            estoque_por_produto[cod_prod][data_key] = {
                                'estoque_inicial': float(dia_dados.get('saldo_inicial', 0)),
                                'saidas': float(dia_dados.get('saida', 0)),
                                'entradas': float(dia_dados.get('entrada', 0)),
                                'saldo_final': float(dia_dados.get('saldo_final', 0))
                            }
                except Exception as e:
                    import logging
                    logging.warning(f"[RECURSOS] Erro ao buscar estoque de {cod_prod}: {e}")
                    estoque_por_produto[cod_prod] = {}

            # 5. Preparar dados das linhas
            linhas = []
            for recurso in recursos:
                linhas.append({
                    'linha_producao': recurso.linha_producao,
                    'capacidade_unidade_minuto': float(recurso.capacidade_unidade_minuto),
                    'qtd_unidade_por_caixa': int(recurso.qtd_unidade_por_caixa),  # ✅ NOVO
                    'qtd_lote_ideal': float(recurso.qtd_lote_ideal) if recurso.qtd_lote_ideal else 0,
                    'qtd_lote_minimo': float(recurso.qtd_lote_minimo) if recurso.qtd_lote_minimo else 0,
                    'eficiencia_media': float(recurso.eficiencia_media) if recurso.eficiencia_media else 85.0,
                    'tempo_setup': int(recurso.tempo_setup) if recurso.tempo_setup else 30,
                    'programacoes': dict(prog_por_linha.get(recurso.linha_producao, {}))
                })

            # 6. Dados do produto
            produto_info = {
                'cod_produto': cod_produto,
                'nome_produto': recursos[0].nome_produto if recursos[0].nome_produto else f'Produto {cod_produto}'
            }

            # LOG DE DEBUG
            import logging
            logging.info(f"[RECURSOS] ========================================")
            logging.info(f"[RECURSOS] Produto: {cod_produto}")
            logging.info(f"[RECURSOS] Mês solicitado: {mes}/{ano}")
            logging.info(f"[RECURSOS] Linhas encontradas: {len(linhas)}")
            logging.info(f"[RECURSOS] Dias com estoque: {len(estoque_por_dia)}")
            logging.info(f"[RECURSOS] Primeiro dia falta: {primeiro_dia_falta}")
            if estoque_por_dia:
                primeiros_dias = list(estoque_por_dia.keys())[:3]
                logging.info(f"[RECURSOS] Primeiras 3 datas com estoque: {primeiros_dias}")
            if linhas:
                logging.info(f"[RECURSOS] Linha exemplo: {linhas[0].get('linha_producao')} - qtd_unidade_por_caixa={linhas[0].get('qtd_unidade_por_caixa')}")
            logging.info(f"[RECURSOS] ========================================")

            return jsonify({
                'produto': produto_info,
                'linhas': linhas,
                'primeiro_dia_falta': primeiro_dia_falta,
                'estoque_por_dia': estoque_por_dia,  # Estoque do produto selecionado
                'estoque_por_produto': estoque_por_produto,  # ✅ NOVO: Estoque de TODOS os produtos
                'mes': mes,
                'ano': ano
            })

        except Exception as e:
            import logging
            logging.error(f"[RECURSOS] Erro ao buscar recursos produtivos: {str(e)}")
            return jsonify({'erro': str(e)}), 500
