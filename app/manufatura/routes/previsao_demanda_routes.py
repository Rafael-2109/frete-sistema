"""
Rotas de Previsão de Demanda - Versão Limpa
"""
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.manufatura.models import PrevisaoDemanda, GrupoEmpresarial, HistoricoPedidos
from app.manufatura.services.demanda_service import extrair_prefixo_cnpj
from app.producao.models import CadastroPalletizacao
from datetime import datetime
from sqlalchemy import func


def register_previsao_demanda_routes(bp):

    @bp.route('/previsao-demanda') # type: ignore
    @login_required
    def previsao_demanda():
        """Tela de gestão de previsão de demanda"""
        return render_template('manufatura/previsao_demanda_nova.html')
    
    @bp.route('/api/previsao-demanda/listar-grupos') # type: ignore
    @login_required
    def listar_grupos_empresariais():
        """Lista grupos empresariais disponíveis para filtro"""
        try:
            # Busca grupos únicos com pelo menos um prefixo ativo
            grupos = db.session.query(
                GrupoEmpresarial.nome_grupo
            ).filter(
                GrupoEmpresarial.ativo == True
            ).distinct().order_by(
                GrupoEmpresarial.nome_grupo
            ).all()
            
            # Formata resposta incluindo GERAL
            opcoes = [
                {'value': '', 'label': 'Todos os Grupos'}
            ]
            
            for grupo in grupos:
                opcoes.append({
                    'value': grupo.nome_grupo,
                    'label': grupo.nome_grupo
                })
            
            # Adiciona opção GERAL (clientes sem grupo)
            opcoes.append({
                'value': 'GERAL',
                'label': 'GERAL (Sem Grupo)'
            })
            
            return jsonify(opcoes)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/calcular-comparacoes') # type: ignore
    @login_required
    def calcular_comparacoes():
        """Calcula comparações de histórico para análise"""
        try:
            from app.manufatura.services.demanda_service import DemandaService
            import logging
            logger = logging.getLogger(__name__)
            
            mes = int(request.args.get('mes'))
            ano = int(request.args.get('ano'))
            cod_produto = request.args.get('cod_produto')
            grupo = request.args.get('grupo')
            
            logger.info(f"[COMPARACOES] Recebido: mes={mes}, ano={ano}, cod_produto={cod_produto}, grupo={grupo}")
            
            service = DemandaService()
            
            # Calcula as diferentes comparações
            comparacoes = {
                'media_3_meses': service.calcular_media_historica(
                    cod_produto, 3, mes, ano, grupo
                ),
                'media_6_meses': service.calcular_media_historica(
                    cod_produto, 6, mes, ano, grupo
                ),
                'mes_anterior': service.calcular_mes_anterior(
                    cod_produto, mes, ano, grupo
                ),
                'ano_anterior': service.calcular_mesmo_mes_ano_anterior(
                    cod_produto, mes, ano, grupo
                ),
                'demanda_ativa': service.calcular_demanda_ativa(
                    cod_produto, grupo
                ),
                'demanda_realizada': service.calcular_demanda_realizada(
                    cod_produto, mes, ano, grupo
                )
            }
            
            logger.info(f"[COMPARACOES] Retornando: {comparacoes}")
            
            return jsonify(comparacoes)
            
        except Exception as e:
            logger.error(f"[COMPARACOES] Erro: {str(e)}", exc_info=True)
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/buscar-existentes') # type: ignore
    @login_required
    def buscar_previsoes_existentes():
        """Busca previsões já cadastradas para o mês/ano/grupo"""
        try:
            mes = int(request.args.get('mes'))
            ano = int(request.args.get('ano'))
            grupo = request.args.get('grupo', '')
            
            # Busca previsões existentes
            query = PrevisaoDemanda.query.filter_by(
                data_mes=mes,
                data_ano=ano
            )
            
            # Filtro por grupo se especificado
            if grupo:
                query = query.filter_by(nome_grupo=grupo)
            
            previsoes = query.all()
            
            # Retorna dicionário com cod_produto como chave
            resultado = {}
            for p in previsoes:
                resultado[p.cod_produto] = {
                    'qtd_prevista': float(p.qtd_demanda_prevista or 0),
                    'qtd_realizada': float(p.qtd_demanda_realizada or 0),
                    'disparo_producao': p.disparo_producao or 'MTS'
                }
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/salvar', methods=['POST']) # type: ignore
    @login_required
    def salvar_previsao_editada():
        """Salva previsão editada pelo usuário"""
        try:
            dados = request.json

            # CORREÇÃO: Não salvar se qtd_prevista for 0 ou None
            qtd_prevista = dados.get('qtd_prevista', 0)
            if qtd_prevista == 0 or qtd_prevista is None:
                # Se já existe um registro, deleta
                previsao_existente = PrevisaoDemanda.query.filter_by(
                    data_mes=dados['mes'], # type: ignore
                    data_ano=dados['ano'], # type: ignore
                    cod_produto=dados['cod_produto'], # type: ignore
                    nome_grupo=dados.get('grupo', 'GERAL') # type: ignore
                ).first()

                if previsao_existente:
                    db.session.delete(previsao_existente)
                    db.session.commit()
                    return jsonify({
                        'sucesso': True,
                        'mensagem': 'Previsão removida (qtd = 0)'
                    })
                else:
                    return jsonify({
                        'sucesso': True,
                        'mensagem': 'Nada a salvar (qtd = 0)'
                    })

            # ✅ BUSCAR NOME DO PRODUTO DE CadastroPalletizacao
            cod_produto = dados['cod_produto'] # type: ignore
            cadastro = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto,
                ativo=True
            ).first()
            nome_produto = cadastro.nome_produto if cadastro else f'Produto {cod_produto}'

            # Busca ou cria previsão
            previsao = PrevisaoDemanda.query.filter_by(
                data_mes=dados['mes'], # type: ignore
                data_ano=dados['ano'], # type: ignore
                cod_produto=cod_produto,
                nome_grupo=dados.get('grupo', 'GERAL') # type: ignore
            ).first()

            if not previsao:
                previsao = PrevisaoDemanda(
                    data_mes=dados['mes'], # type: ignore
                    data_ano=dados['ano'], # type: ignore
                    cod_produto=cod_produto,
                    nome_produto=nome_produto,  # ✅ Nome de CadastroPalletizacao
                    nome_grupo=dados.get('grupo', 'GERAL') # type: ignore
                )
                db.session.add(previsao)
            else:
                # ✅ Sempre atualizar nome do produto
                previsao.nome_produto = nome_produto

            # Atualiza valores
            previsao.qtd_demanda_prevista = qtd_prevista
            previsao.disparo_producao = dados.get('disparo_producao', 'MTS')
            previsao.criado_por = current_user.nome if current_user.is_authenticated else 'Sistema'
            previsao.criado_em = datetime.utcnow()

            # Se houver demanda realizada, atualiza também
            if 'qtd_realizada' in dados: # type: ignore
                previsao.qtd_demanda_realizada = dados['qtd_realizada'] # type: ignore

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'mensagem': 'Previsão salva com sucesso'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/produtos-historico') # type: ignore
    @login_required
    def listar_produtos_historico():
        """Lista produtos únicos do histórico, opcionalmente filtrados por grupo"""
        try:
            from app.manufatura.models import HistoricoPedidos
            
            grupo = request.args.get('grupo')  # Pode ser nome do grupo ou 'GERAL'
            
            # Query base para produtos únicos
            query = db.session.query(
                HistoricoPedidos.cod_produto,
                func.max(HistoricoPedidos.nome_produto).label('nome_produto'),
                func.sum(HistoricoPedidos.qtd_produto_pedido).label('qtd_total'),
                func.count(func.distinct(HistoricoPedidos.num_pedido)).label('num_pedidos'),
                func.min(HistoricoPedidos.data_pedido).label('primeira_venda'),
                func.max(HistoricoPedidos.data_pedido).label('ultima_venda')
            )
            
            # Filtro por grupo se especificado
            if grupo and grupo != '':
                if grupo == 'GERAL':
                    # Busca todos os prefixos cadastrados
                    todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                        GrupoEmpresarial.ativo == True
                    ).all()
                    
                    # Exclui CNPJs que pertencem a algum grupo
                    if todos_prefixos:
                        for prefixo_tuple in todos_prefixos:
                            prefixo = prefixo_tuple[0]
                            query = query.filter(
                                extrair_prefixo_cnpj(HistoricoPedidos.cnpj_cliente) != prefixo
                            )
                else:
                    # Busca prefixos do grupo específico
                    prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                        GrupoEmpresarial.nome_grupo == grupo,
                        GrupoEmpresarial.ativo == True
                    ).all()
                    
                    if prefixos_grupo:
                        from sqlalchemy import or_
                        prefixos = [p[0] for p in prefixos_grupo]
                        cnpj_filters = []
                        for prefixo in prefixos:
                            cnpj_filters.append(
                                extrair_prefixo_cnpj(HistoricoPedidos.cnpj_cliente) == prefixo
                            )
                        if cnpj_filters:
                            query = query.filter(or_(*cnpj_filters))
            
            # Agrupa por produto e ordena por quantidade total
            produtos = query.group_by(
                HistoricoPedidos.cod_produto
            ).order_by(
                func.sum(HistoricoPedidos.qtd_produto_pedido).desc()
            ).all()
            
            return jsonify([{
                'cod_produto': p.cod_produto,
                'nome_produto': p.nome_produto or 'Produto sem nome',
                'qtd_total': float(p.qtd_total or 0),
                'num_pedidos': p.num_pedidos,
                'primeira_venda': p.primeira_venda.strftime('%d/%m/%Y') if p.primeira_venda else None,
                'ultima_venda': p.ultima_venda.strftime('%d/%m/%Y') if p.ultima_venda else None
            } for p in produtos])
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/grupos-empresariais/listar') # type: ignore
    @login_required
    def listar_grupos_crud():
        """Lista grupos empresariais para CRUD (agrupados por nome)"""
        try:
            # Busca todos os grupos com seus prefixos agrupados
            grupos = db.session.query(
                GrupoEmpresarial.nome_grupo,
                func.string_agg(GrupoEmpresarial.prefixo_cnpj, ',').label('prefixos'),
                func.max(GrupoEmpresarial.descricao).label('descricao'),
                func.max(GrupoEmpresarial.criado_em).label('criado_em'),
                func.max(GrupoEmpresarial.criado_por).label('criado_por'),
                func.bool_and(GrupoEmpresarial.ativo).label('ativo'),
                func.count(GrupoEmpresarial.id).label('num_prefixos')
            ).group_by(
                GrupoEmpresarial.nome_grupo
            ).order_by(
                GrupoEmpresarial.nome_grupo
            ).all()
            
            return jsonify([{
                'nome_grupo': g.nome_grupo,
                'prefixos': sorted(g.prefixos.split(',')) if g.prefixos else [],
                'descricao': g.descricao,
                'num_prefixos': g.num_prefixos,
                'ativo': g.ativo,
                'criado_em': g.criado_em.strftime('%d/%m/%Y %H:%M') if g.criado_em else None,
                'criado_por': g.criado_por
            } for g in grupos])
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/grupos-empresariais/criar', methods=['POST']) # type: ignore
    @login_required
    def criar_grupo_empresarial():
        """Cria ou atualiza grupo empresarial com prefixos"""
        try:
            dados = request.json
            nome_grupo = dados.get('nome_grupo')
            prefixos = dados.get('prefixos', [])
            descricao = dados.get('descricao')
            
            if not nome_grupo:
                return jsonify({'erro': 'Nome do grupo é obrigatório'}), 400
            
            if not prefixos:
                return jsonify({'erro': 'Pelo menos um prefixo é obrigatório'}), 400
            
            # Valida prefixos (8 dígitos)
            for prefixo in prefixos:
                prefixo_limpo = ''.join(filter(str.isdigit, str(prefixo)))
                if len(prefixo_limpo) != 8:
                    return jsonify({'erro': f'Prefixo {prefixo} inválido. Deve ter exatamente 8 dígitos'}), 400
            
            # Verifica se algum prefixo já pertence a outro grupo
            for prefixo in prefixos:
                prefixo_limpo = ''.join(filter(str.isdigit, str(prefixo)))
                existe = GrupoEmpresarial.query.filter(
                    GrupoEmpresarial.prefixo_cnpj == prefixo_limpo,
                    GrupoEmpresarial.nome_grupo != nome_grupo,
                    GrupoEmpresarial.ativo == True
                ).first()
                
                if existe:
                    return jsonify({'erro': f'Prefixo {prefixo} já pertence ao grupo {existe.nome_grupo}'}), 400
            
            # Remove prefixos antigos do grupo (para atualização)
            GrupoEmpresarial.query.filter_by(nome_grupo=nome_grupo).delete()
            
            # Adiciona novos prefixos
            for prefixo in prefixos:
                prefixo_limpo = ''.join(filter(str.isdigit, str(prefixo)))
                
                grupo = GrupoEmpresarial(
                    nome_grupo=nome_grupo,
                    prefixo_cnpj=prefixo_limpo,
                    descricao=descricao,
                    criado_por=current_user.nome if current_user.is_authenticated else 'Sistema',
                    ativo=True
                )
                db.session.add(grupo)
            
            db.session.commit()
            
            return jsonify({
                'sucesso': True,
                'mensagem': f'Grupo {nome_grupo} salvo com {len(prefixos)} prefixo(s)'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
        
    @bp.route('/api/grupos-empresariais/<nome_grupo>', methods=['DELETE']) # type: ignore
    @login_required
    def deletar_grupo_empresarial(nome_grupo):
        """Desativa grupo empresarial (soft delete)"""
        try:
            # Desativa todos os prefixos do grupo
            grupos = GrupoEmpresarial.query.filter_by(
                nome_grupo=nome_grupo,
                ativo=True
            ).all()

            if not grupos:
                return jsonify({'erro': 'Grupo não encontrado'}), 404

            for grupo in grupos:
                grupo.ativo = False

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'mensagem': f'Grupo {nome_grupo} desativado com sucesso'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/previsao-demanda/importar-excel', methods=['POST']) # type: ignore
    @login_required
    def importar_excel():
        """Importa demanda prevista de arquivo Excel (UPSERT)"""
        try:
            import pandas as pd

            # Verificar se arquivo foi enviado
            if 'arquivo' not in request.files:
                return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

            arquivo = request.files['arquivo']

            if arquivo.filename == '':
                return jsonify({'erro': 'Nome de arquivo vazio'}), 400

            # Validar extensão
            if not arquivo.filename.endswith(('.xlsx', '.xls')):
                return jsonify({'erro': 'Arquivo deve ser Excel (.xlsx ou .xls)'}), 400

            # Ler Excel
            df = pd.read_excel(arquivo)

            # Mapeamento de colunas: aceita formato exportado (amigável) ou técnico
            mapeamento_colunas = {
                # Formato exportado → formato técnico
                'Código Produto': 'cod_produto',
                'Nome Produto': 'nome_produto',
                'Mês': 'mes',
                'Ano': 'ano',
                'Grupo': 'grupo',
                'Qtd Prevista': 'qtd_prevista',
                'Disparo': 'disparo',
                'Média 3 Meses': 'media_3_meses',
                'Média 6 Meses': 'media_6_meses',
                'Mês Anterior': 'mes_anterior',
                'Ano Anterior': 'ano_anterior',
                'Demanda Ativa (Carteira)': 'demanda_ativa',
                'Demanda Realizada': 'demanda_realizada'
            }

            # Renomeia colunas se estiverem no formato exportado
            df.rename(columns=mapeamento_colunas, inplace=True)

            # Validar colunas obrigatórias
            colunas_obrigatorias = ['cod_produto', 'mes', 'ano', 'qtd_prevista', 'disparo']
            colunas_faltando = [c for c in colunas_obrigatorias if c not in df.columns]

            if colunas_faltando:
                return jsonify({
                    'erro': f'Colunas obrigatórias faltando: {", ".join(colunas_faltando)}. '
                            f'Aceitos: formato exportado (Código Produto, Mês, Ano, Qtd Prevista, Disparo) '
                            f'ou técnico (cod_produto, mes, ano, qtd_prevista, disparo)'
                }), 400

            # Processar linhas (UPSERT)
            total_linhas = len(df)
            inseridos = 0
            atualizados = 0
            erros = []

            for idx, row in df.iterrows():
                try:
                    cod_produto = str(row['cod_produto']).strip()
                    mes = int(row['mes'])
                    ano = int(row['ano'])
                    qtd_prevista = float(row['qtd_prevista'])
                    disparo = str(row['disparo']).strip().upper()

                    # ✅ NORMALIZAÇÃO: Grupo vazio/nulo → 'GERAL'
                    grupo_raw = str(row.get('grupo', '')).strip() if 'grupo' in row and pd.notna(row.get('grupo')) else ''
                    grupo = 'GERAL' if grupo_raw == '' else grupo_raw

                    # ✅ BUSCAR NOME DO PRODUTO DE CadastroPalletizacao
                    cadastro = CadastroPalletizacao.query.filter_by(
                        cod_produto=cod_produto,
                        ativo=True
                    ).first()
                    nome_produto = cadastro.nome_produto if cadastro else f'Produto {cod_produto}'

                    # Validações
                    if mes < 1 or mes > 12:
                        erros.append(f"Linha {idx+2}: Mês inválido ({mes})") # type: ignore
                        continue

                    if disparo not in ['MTO', 'MTS']:
                        erros.append(f"Linha {idx+2}: Disparo deve ser MTO ou MTS (recebido: {disparo})") # type: ignore
                        continue

                    # ✅ VALIDAÇÃO: Grupo deve existir (exceto 'GERAL')
                    if grupo != 'GERAL':
                        grupo_existe = GrupoEmpresarial.query.filter_by(
                            nome_grupo=grupo,
                            ativo=True
                        ).first()
                        if not grupo_existe:
                            erros.append(f"Linha {idx+2}: Grupo '{grupo}' não está cadastrado. Use 'GERAL' ou cadastre o grupo primeiro.") # type: ignore
                            continue

                    # Buscar existente
                    previsao = PrevisaoDemanda.query.filter_by(
                        data_mes=mes,
                        data_ano=ano,
                        cod_produto=cod_produto,
                        nome_grupo=grupo
                    ).first()

                    if previsao:
                        # Atualizar
                        previsao.qtd_demanda_prevista = qtd_prevista
                        previsao.disparo_producao = disparo
                        previsao.nome_produto = nome_produto  # ✅ Sempre atualizar com nome do cadastro
                        previsao.atualizado_em = datetime.utcnow()
                        atualizados += 1
                    else:
                        # Inserir
                        previsao = PrevisaoDemanda(
                            data_mes=mes,
                            data_ano=ano,
                            cod_produto=cod_produto,
                            nome_produto=nome_produto,  # ✅ Nome de CadastroPalletizacao
                            nome_grupo=grupo,
                            qtd_demanda_prevista=qtd_prevista,
                            disparo_producao=disparo,
                            criado_por=current_user.nome if current_user.is_authenticated else 'Sistema'
                        )
                        db.session.add(previsao)
                        inseridos += 1

                except Exception as e:
                    erros.append(f"Linha {idx+2}: {str(e)}") # type: ignore
                    continue

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'total_linhas': total_linhas,
                'inseridos': inseridos,
                'atualizados': atualizados,
                'erros': erros,
                'mensagem': f'Importação concluída: {inseridos} inseridos, {atualizados} atualizados'
            })

        except Exception as e:
            db.session.rollback()
            import logging
            logging.error(f"[IMPORTAR] Erro: {str(e)}", exc_info=True)
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/previsao-demanda/exportar-excel') # type: ignore
    @login_required
    def exportar_excel():
        """Exporta previsões com comparações e dados históricos para Excel"""
        try:
            import pandas as pd
            from io import BytesIO
            from flask import send_file
            from app.manufatura.services.demanda_service import DemandaService
            import logging
            logger = logging.getLogger(__name__)

            # Parâmetros da requisição
            mes = int(request.args.get('mes'))
            ano = int(request.args.get('ano'))
            grupo = request.args.get('grupo', '')

            logger.info(f"[EXPORTAR] Mês: {mes}, Ano: {ano}, Grupo: {grupo}")

            # Busca todos os produtos do histórico filtrados por grupo
            query = db.session.query(
                HistoricoPedidos.cod_produto,
                func.max(HistoricoPedidos.nome_produto).label('nome_produto')
            )

            # Filtro por grupo se especificado
            if grupo and grupo != '':
                if grupo == 'GERAL':
                    # Busca todos os prefixos cadastrados
                    todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                        GrupoEmpresarial.ativo == True
                    ).all()

                    # Exclui CNPJs que pertencem a algum grupo
                    if todos_prefixos:
                        for prefixo_tuple in todos_prefixos:
                            prefixo = prefixo_tuple[0]
                            query = query.filter(
                                extrair_prefixo_cnpj(HistoricoPedidos.cnpj_cliente) != prefixo
                            )
                else:
                    # Busca prefixos do grupo específico
                    prefixos_grupo = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                        GrupoEmpresarial.nome_grupo == grupo,
                        GrupoEmpresarial.ativo == True
                    ).all()

                    if prefixos_grupo:
                        from sqlalchemy import or_
                        prefixos = [p[0] for p in prefixos_grupo]
                        cnpj_filters = []
                        for prefixo in prefixos:
                            cnpj_filters.append(
                                extrair_prefixo_cnpj(HistoricoPedidos.cnpj_cliente) == prefixo
                            )
                        if cnpj_filters:
                            query = query.filter(or_(*cnpj_filters))

            # Agrupa por produto
            produtos = query.group_by(HistoricoPedidos.cod_produto).all()

            logger.info(f"[EXPORTAR] Total de produtos encontrados: {len(produtos)}")

            if not produtos:
                return jsonify({'erro': 'Nenhum produto encontrado para exportar'}), 404

            # Busca previsões existentes
            previsoes_existentes = {}
            previsoes = PrevisaoDemanda.query.filter_by(
                data_mes=mes,
                data_ano=ano
            )
            if grupo:
                previsoes = previsoes.filter_by(nome_grupo=grupo)

            for p in previsoes.all():
                previsoes_existentes[p.cod_produto] = {
                    'qtd_prevista': float(p.qtd_demanda_prevista or 0),
                    'qtd_realizada': float(p.qtd_demanda_realizada or 0),
                    'disparo': p.disparo_producao or 'MTS'
                }

            logger.info(f"[EXPORTAR] Previsões existentes: {len(previsoes_existentes)}")

            # Inicializa service
            service = DemandaService()

            # Monta dados para exportação
            dados_exportacao = []

            for produto in produtos:
                cod_produto = produto.cod_produto
                nome_produto = produto.nome_produto or 'Produto sem nome'

                logger.info(f"[EXPORTAR] Processando produto: {cod_produto}")

                # Calcula comparações
                comparacoes = {
                    'media_3_meses': service.calcular_media_historica(cod_produto, 3, mes, ano, grupo),
                    'media_6_meses': service.calcular_media_historica(cod_produto, 6, mes, ano, grupo),
                    'mes_anterior': service.calcular_mes_anterior(cod_produto, mes, ano, grupo),
                    'ano_anterior': service.calcular_mesmo_mes_ano_anterior(cod_produto, mes, ano, grupo),
                    'demanda_ativa': service.calcular_demanda_ativa(cod_produto, grupo),
                    'demanda_realizada': service.calcular_demanda_realizada(cod_produto, mes, ano, grupo)
                }

                # Dados da previsão existente (se houver)
                previsao = previsoes_existentes.get(cod_produto, {})

                # Monta linha de dados
                dados_exportacao.append({
                    'cod_produto': cod_produto,
                    'nome_produto': nome_produto,
                    'mes': mes,
                    'ano': ano,
                    'grupo': grupo if grupo else 'GERAL',
                    'qtd_prevista': previsao.get('qtd_prevista', 0),
                    'disparo': previsao.get('disparo', 'MTS'),
                    'media_3_meses': round(comparacoes['media_3_meses'], 3),
                    'media_6_meses': round(comparacoes['media_6_meses'], 3),
                    'mes_anterior': round(comparacoes['mes_anterior'], 3),
                    'ano_anterior': round(comparacoes['ano_anterior'], 3),
                    'demanda_ativa': round(comparacoes['demanda_ativa'], 3),
                    'demanda_realizada': round(comparacoes['demanda_realizada'], 3)
                })

            logger.info(f"[EXPORTAR] Total de linhas para exportar: {len(dados_exportacao)}")

            # Cria DataFrame
            df = pd.DataFrame(dados_exportacao)

            # Renomeia colunas para ficar mais amigável
            df.columns = [
                'Código Produto',
                'Nome Produto',
                'Mês',
                'Ano',
                'Grupo',
                'Qtd Prevista',
                'Disparo',
                'Média 3 Meses',
                'Média 6 Meses',
                'Mês Anterior',
                'Ano Anterior',
                'Demanda Ativa (Carteira)',
                'Demanda Realizada'
            ]

            # Cria arquivo Excel em memória
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Previsão Demanda')

                # Ajusta largura das colunas
                worksheet = writer.sheets['Previsão Demanda']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

            output.seek(0)

            # Nome do arquivo
            grupo_nome = grupo if grupo else 'TODOS'
            nome_arquivo = f'previsao_demanda_{mes:02d}_{ano}_{grupo_nome}.xlsx'

            logger.info(f"[EXPORTAR] Arquivo gerado: {nome_arquivo}")

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=nome_arquivo
            )

        except Exception as e:
            import logging
            logging.error(f"[EXPORTAR] Erro: {str(e)}", exc_info=True)
            return jsonify({'erro': str(e)}), 500