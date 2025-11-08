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
            linha_producao = request.args.get('linha_producao')
            marca = request.args.get('marca')
            mp = request.args.get('mp')
            embalagem = request.args.get('embalagem')

            service = NecessidadeProducaoService()
            resultado = service.calcular_necessidade_producao(
                mes, ano, cod_produto, linha_producao, marca, mp, embalagem
            )

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

    @bp.route('/api/necessidade-producao/autocomplete-produtos')
    @login_required
    def autocomplete_produtos():
        """Autocomplete para busca de produtos por código ou nome"""
        try:
            from app.producao.models import CadastroPalletizacao
            from sqlalchemy import or_

            termo = request.args.get('termo', '').strip()
            if not termo or len(termo) < 2:
                return jsonify([])

            # Buscar produtos que correspondam ao termo (código ou nome)
            produtos = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True,
                CadastroPalletizacao.produto_produzido == True,
                or_(
                    CadastroPalletizacao.cod_produto.ilike(f'%{termo}%'),
                    CadastroPalletizacao.nome_produto.ilike(f'%{termo}%')
                )
            ).limit(20).all()

            resultado = [{
                'cod_produto': p.cod_produto,
                'nome_produto': p.nome_produto,
                'linha_producao': p.linha_producao,
                'tipo_embalagem': p.tipo_embalagem
            } for p in produtos]

            return jsonify(resultado)

        except Exception as e:
            import logging
            logging.error(f"[AUTOCOMPLETE] Erro: {str(e)}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/necessidade-producao/filtros-opcoes')
    @login_required
    def filtros_opcoes():
        """Retorna opções disponíveis para filtros de select"""
        try:
            from app.producao.models import CadastroPalletizacao
            from sqlalchemy import func, distinct

            # Filtros ativos (para dependências)
            linha_producao = request.args.get('linha_producao')
            marca = request.args.get('marca')
            mp = request.args.get('mp')
            embalagem = request.args.get('embalagem')

            # Base query
            query = db.session.query(CadastroPalletizacao).filter(
                CadastroPalletizacao.ativo == True,
                CadastroPalletizacao.produto_produzido == True
            )

            # Aplicar filtros dependentes
            if linha_producao:
                query = query.filter(CadastroPalletizacao.linha_producao == linha_producao)
            if marca:
                query = query.filter(CadastroPalletizacao.categoria_produto == marca)
            if mp:
                query = query.filter(CadastroPalletizacao.tipo_materia_prima == mp)
            if embalagem:
                query = query.filter(CadastroPalletizacao.tipo_embalagem == embalagem)

            # Buscar opções únicas
            linhas = query.with_entities(
                distinct(CadastroPalletizacao.linha_producao)
            ).filter(
                CadastroPalletizacao.linha_producao.isnot(None)
            ).order_by(CadastroPalletizacao.linha_producao).all()

            marcas = query.with_entities(
                distinct(CadastroPalletizacao.categoria_produto)
            ).filter(
                CadastroPalletizacao.categoria_produto.isnot(None)
            ).order_by(CadastroPalletizacao.categoria_produto).all()

            mps = query.with_entities(
                distinct(CadastroPalletizacao.tipo_materia_prima)
            ).filter(
                CadastroPalletizacao.tipo_materia_prima.isnot(None)
            ).order_by(CadastroPalletizacao.tipo_materia_prima).all()

            embalagens = query.with_entities(
                distinct(CadastroPalletizacao.tipo_embalagem)
            ).filter(
                CadastroPalletizacao.tipo_embalagem.isnot(None)
            ).order_by(CadastroPalletizacao.tipo_embalagem).all()

            return jsonify({
                'linhas_producao': [linha[0] for linha in linhas if linha[0]],
                'marcas': [marca[0] for marca in marcas if marca[0]],
                'mps': [materia_prima[0] for materia_prima in mps if materia_prima[0]],
                'embalagens': [emb[0] for emb in embalagens if emb[0]]
            })

        except Exception as e:
            import logging
            logging.error(f"[FILTROS] Erro: {str(e)}")
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

    @bp.route('/api/necessidade-producao/bom-recursiva-estoque')
    @login_required
    def bom_recursiva_estoque():
        """Retorna estrutura de produto (BOM) recursiva com estoque e projeção D0-D60 dos componentes"""
        try:
            from app.manufatura.models import ListaMateriais
            from app.estoque.services.estoque_simples import ServicoEstoqueSimples
            from app.producao.models import CadastroPalletizacao

            cod_produto = request.args.get('cod_produto')
            if not cod_produto:
                return jsonify({'erro': 'Código do produto é obrigatório'}), 400

            # Função recursiva para buscar componentes COM CONSUMO ACUMULADO
            def buscar_componentes_recursivos(cod_produto_pai, qtd_pai=1.0, nivel=0, visitados=None):
                """
                Busca recursivamente componentes da BOM COM CONSUMO ACUMULADO

                Exemplo:
                Produto A (1 unidade)
                ├─ Componente B (2kg) - Intermediário
                │  └─ Componente C (0.5kg por B) → Consumo total: 2*0.5 = 1kg
                └─ Componente D (3kg) → Consumo total: 3kg

                Args:
                    cod_produto_pai: Código do produto/componente pai
                    qtd_pai: Quantidade acumulada do pai (para calcular consumo total)
                    nivel: Nível na hierarquia (0=raiz)
                    visitados: Set para evitar loops

                Returns:
                    Lista de dicts com consumo acumulado
                """
                if visitados is None:
                    visitados = set()

                # Evitar loop infinito
                if cod_produto_pai in visitados:
                    return []

                visitados.add(cod_produto_pai)
                componentes_flat = []

                # Buscar componentes diretos
                bom_items = ListaMateriais.query.filter_by(
                    cod_produto_produzido=cod_produto_pai,
                    status='ativo'
                ).all()

                for item in bom_items:
                    cod_componente = item.cod_produto_componente
                    qtd_unitaria = float(item.qtd_utilizada)
                    qtd_total_acumulada = qtd_pai * qtd_unitaria  # ✅ CONSUMO ACUMULADO

                    # Buscar dados do cadastro
                    cadastro = CadastroPalletizacao.query.filter_by(
                        cod_produto=cod_componente,
                        ativo=True
                    ).first()

                    # Verificar se é intermediário (tem BOM própria)
                    eh_intermediario = ListaMateriais.query.filter_by(
                        cod_produto_produzido=cod_componente,
                        status='ativo'
                    ).count() > 0

                    componentes_flat.append({
                        'cod_produto': cod_componente,
                        'nome_produto': item.nome_produto_componente or (cadastro.nome_produto if cadastro else ''),
                        'qtd_unitaria': qtd_unitaria,  # ✅ Qtd por unidade do pai direto
                        'qtd_total': qtd_total_acumulada,  # ✅ Consumo acumulado recursivo
                        'nivel': nivel,
                        'eh_intermediario': eh_intermediario
                    })

                    # Se for intermediário, buscar sub-componentes
                    if eh_intermediario:
                        sub_componentes = buscar_componentes_recursivos(
                            cod_componente,
                            qtd_total_acumulada,  # ✅ Propagar quantidade acumulada
                            nivel + 1,
                            visitados
                        )
                        componentes_flat.extend(sub_componentes)

                return componentes_flat

            # Buscar componentes recursivamente (começando com qtd=1)
            componentes = buscar_componentes_recursivos(cod_produto, qtd_pai=1.0)

            if not componentes:
                return jsonify({
                    'componentes': [],
                    'producao_produto_sku': None,
                    'mensagem': 'Produto não possui estrutura (BOM) cadastrada'
                })

            # ✅ Usar ServicoProjecaoEstoque que já calcula recursivamente!
            from app.manufatura.services.projecao_estoque_service import ServicoProjecaoEstoque

            servico_projecao = ServicoProjecaoEstoque()
            componentes_com_estoque = []
            min_producao_possivel = float('inf')

            for comp in componentes:
                cod_comp = comp['cod_produto']

                # Buscar projeção completa do componente (já calcula recursivamente!)
                projecao_comp = servico_projecao.projetar_produto(cod_comp, dias=60)

                # Extrair estoque atual
                estoque_atual = projecao_comp.get('estoque_inicial', 0)

                # Montar dict de projeção D0-D60 (estoque final por dia)
                projecao_por_dia = {}
                projecao_diaria = projecao_comp.get('projecao_diaria', [])
                for dia_dados in projecao_diaria:
                    # Extrair número do dia da string 'YYYY-MM-DD'
                    from datetime import date as date_cls
                    hoje = date_cls.today()
                    data_dia = date_cls.fromisoformat(dia_dados['data'])
                    dia_num = (data_dia - hoje).days
                    if 0 <= dia_num <= 60:
                        projecao_por_dia[f'D{dia_num}'] = float(dia_dados.get('estoque_final', 0))

                # ✅ Calcular quantidade de produto possível usando CONSUMO TOTAL
                qtd_total = comp['qtd_total']
                if qtd_total > 0:
                    qtd_prod_possivel = estoque_atual / qtd_total
                else:
                    qtd_prod_possivel = 0

                # Atualizar mínimo (gargalo) - APENAS para componentes NÃO intermediários
                if not comp['eh_intermediario'] and qtd_prod_possivel < min_producao_possivel:
                    min_producao_possivel = qtd_prod_possivel

                componentes_com_estoque.append({
                    'cod_produto': cod_comp,
                    'nome_produto': comp['nome_produto'],
                    'qtd_unitaria': comp['qtd_unitaria'],
                    'qtd_total': qtd_total,
                    'nivel': comp['nivel'],
                    'eh_intermediario': comp['eh_intermediario'],
                    'estoque_atual': float(estoque_atual),
                    'qtd_prod_possivel': qtd_prod_possivel,
                    'projecao': projecao_por_dia  # ✅ Projeção recursiva completa!
                })

            # Se nenhum componente foi encontrado, producao_sku = None
            producao_sku = min_producao_possivel if min_producao_possivel != float('inf') else 0

            return jsonify({
                'componentes': componentes_com_estoque,
                'producao_produto_sku': round(producao_sku, 3),
                'total_componentes': len(componentes_com_estoque)
            })

        except Exception as e:
            import logging
            import traceback
            logging.error(f"[BOM RECURSIVA] Erro: {str(e)}")
            logging.error(f"[BOM RECURSIVA] Traceback: {traceback.format_exc()}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/necessidade-producao/adicionar-programacao', methods=['POST'])
    @login_required
    def adicionar_programacao():
        """Adiciona uma nova programação de produção"""
        try:
            from app.producao.models import ProgramacaoProducao
            from app.manufatura.models import RecursosProducao
            from datetime import datetime

            dados = request.json
            cod_produto = dados.get('cod_produto')
            data_programacao_str = dados.get('data_programacao')
            linha_producao = dados.get('linha_producao')
            qtd_programada = dados.get('qtd_programada')
            cliente_produto = dados.get('cliente_produto')
            observacao_pcp = dados.get('observacao_pcp')

            # Validações
            if not all([cod_produto, data_programacao_str, linha_producao, qtd_programada]):
                return jsonify({'erro': 'Campos obrigatórios: cod_produto, data_programacao, linha_producao, qtd_programada'}), 400

            # Validar data
            try:
                data_programacao = datetime.strptime(data_programacao_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'erro': 'Formato de data inválido. Use YYYY-MM-DD'}), 400

            # Validar quantidade
            try:
                qtd_programada = float(qtd_programada)
                if qtd_programada <= 0:
                    return jsonify({'erro': 'Quantidade deve ser maior que zero'}), 400
            except ValueError:
                return jsonify({'erro': 'Quantidade inválida'}), 400

            # Validar se a linha de produção existe para este produto
            recurso = RecursosProducao.query.filter_by(
                cod_produto=cod_produto,
                linha_producao=linha_producao,
                disponivel=True
            ).first()

            if not recurso:
                return jsonify({'erro': f'Linha de produção "{linha_producao}" não está disponível para este produto'}), 400

            # Criar programação
            nova_programacao = ProgramacaoProducao(
                cod_produto=cod_produto,
                nome_produto=recurso.nome_produto,
                data_programacao=data_programacao,
                linha_producao=linha_producao,
                qtd_programada=qtd_programada,
                cliente_produto=cliente_produto,
                observacao_pcp=observacao_pcp,
                created_by=current_user.nome if current_user.is_authenticated else 'Sistema'
            )

            db.session.add(nova_programacao)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'mensagem': 'Programação adicionada com sucesso',
                'programacao': {
                    'id': nova_programacao.id,
                    'cod_produto': nova_programacao.cod_produto,
                    'data_programacao': nova_programacao.data_programacao.strftime('%Y-%m-%d'),
                    'linha_producao': nova_programacao.linha_producao,
                    'qtd_programada': float(nova_programacao.qtd_programada)
                }
            })

        except Exception as e:
            db.session.rollback()
            import logging
            import traceback
            logging.error(f"[ADICIONAR PROGRAMACAO] Erro: {str(e)}")
            logging.error(f"[ADICIONAR PROGRAMACAO] Traceback: {traceback.format_exc()}")
            return jsonify({'erro': str(e)}), 500
