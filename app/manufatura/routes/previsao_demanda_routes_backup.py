"""
Rotas de Previsão de Demanda
"""
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.manufatura.models import PrevisaoDemanda, GrupoEmpresarial
from datetime import datetime
from sqlalchemy import func


def register_previsao_demanda_routes(bp):
    
    @bp.route('/previsao-demanda')
    @login_required
    def previsao_demanda():
        """Tela de gestão de previsão de demanda"""
        return render_template('manufatura/previsao_demanda_nova.html')
    
    @bp.route('/api/previsao-demanda/listar')
    @login_required
    def listar_previsoes():
        """Lista previsões de demanda"""
        try:
            ano = request.args.get('ano', datetime.now().year, type=int)
            mes = request.args.get('mes', type=int)
            
            query = PrevisaoDemanda.query.filter_by(data_ano=ano)
            if mes:
                query = query.filter_by(data_mes=mes)
            
            previsoes = query.order_by(PrevisaoDemanda.data_mes, PrevisaoDemanda.cod_produto).all()
            
            return jsonify([{
                'id': p.id,
                'mes': p.data_mes,
                'ano': p.data_ano,
                'nome_grupo': p.nome_grupo,
                'cod_produto': p.cod_produto,
                'nome_produto': p.nome_produto,
                'qtd_demanda_prevista': float(p.qtd_demanda_prevista or 0),
                'qtd_demanda_realizada': float(p.qtd_demanda_realizada or 0),
                'disparo_producao': p.disparo_producao
            } for p in previsoes])
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/produtos-historico')
    @login_required
    def listar_produtos_historico():
        """Lista produtos únicos do histórico, opcionalmente filtrados por grupo"""
        try:
            from app.manufatura.models import HistoricoPedidos
            from app.manufatura.services.demanda_service import DemandaService
            
            grupo = request.args.get('grupo')  # Pode ser nome do grupo ou 'RESTANTE'
            
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
                if grupo == 'RESTANTE':
                    # Busca todos os prefixos cadastrados
                    todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                        GrupoEmpresarial.ativo == True
                    ).all()
                    
                    # Exclui CNPJs que pertencem a algum grupo
                    if todos_prefixos:
                        for prefixo_tuple in todos_prefixos:
                            prefixo = prefixo_tuple[0]
                            query = query.filter(
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) != prefixo
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
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) == prefixo
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
    
    @bp.route('/api/grupos-empresariais/listar')
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
    
    @bp.route('/api/grupos-empresariais/criar', methods=['POST'])
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
    
    @bp.route('/api/grupos-empresariais/<nome_grupo>', methods=['DELETE'])
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
    
    @bp.route('/api/previsao-demanda/criar', methods=['POST'])
    @login_required
    def criar_previsao():
        """Cria nova previsão de demanda"""
        try:
            dados = request.json
            
            previsao = PrevisaoDemanda(
                data_mes=dados['mes'],
                data_ano=dados['ano'],
                nome_grupo=dados.get('nome_grupo'),
                cod_produto=dados['cod_produto'],
                nome_produto=dados.get('nome_produto'),
                qtd_demanda_prevista=dados['qtd_prevista'],
                disparo_producao=dados.get('disparo_producao', 'MTS'),
                criado_por=current_user.nome if current_user.is_authenticated else 'Sistema'
            )
            
            db.session.add(previsao)
            db.session.commit()
            
            return jsonify({'sucesso': True, 'id': previsao.id})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/produtos-historico')
    @login_required
    def listar_produtos_historico():
        """Lista produtos únicos do histórico, opcionalmente filtrados por grupo"""
        try:
            from app.manufatura.models import HistoricoPedidos
            from app.manufatura.services.demanda_service import DemandaService
            
            grupo = request.args.get('grupo')  # Pode ser nome do grupo ou 'RESTANTE'
            
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
                if grupo == 'RESTANTE':
                    # Busca todos os prefixos cadastrados
                    todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                        GrupoEmpresarial.ativo == True
                    ).all()
                    
                    # Exclui CNPJs que pertencem a algum grupo
                    if todos_prefixos:
                        for prefixo_tuple in todos_prefixos:
                            prefixo = prefixo_tuple[0]
                            query = query.filter(
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) != prefixo
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
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) == prefixo
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
    
    @bp.route('/api/grupos-empresariais/listar')
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
    
    @bp.route('/api/grupos-empresariais/criar', methods=['POST'])
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
    
    @bp.route('/api/grupos-empresariais/<nome_grupo>', methods=['DELETE'])
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
    
    @bp.route('/api/previsao-demanda/gerar-historico', methods=['POST'])
    @login_required
    def gerar_previsao_historico():
        """Gera previsão baseada no histórico"""
        try:
            from app.manufatura.services.demanda_service import DemandaService
            
            dados = request.json if request.is_json else request.form
            mes = int(dados.get('mes'))
            ano = int(dados.get('ano'))
            multiplicador = float(dados.get('multiplicador', 1.0))
            
            service = DemandaService()
            qtd_criada = service.criar_previsao_por_historico(mes, ano, multiplicador)
            
            return jsonify({
                'sucesso': True,
                'mensagem': f'{qtd_criada} previsões criadas baseadas no histórico'
            })
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/produtos-historico')
    @login_required
    def listar_produtos_historico():
        """Lista produtos únicos do histórico, opcionalmente filtrados por grupo"""
        try:
            from app.manufatura.models import HistoricoPedidos
            from app.manufatura.services.demanda_service import DemandaService
            
            grupo = request.args.get('grupo')  # Pode ser nome do grupo ou 'RESTANTE'
            
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
                if grupo == 'RESTANTE':
                    # Busca todos os prefixos cadastrados
                    todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                        GrupoEmpresarial.ativo == True
                    ).all()
                    
                    # Exclui CNPJs que pertencem a algum grupo
                    if todos_prefixos:
                        for prefixo_tuple in todos_prefixos:
                            prefixo = prefixo_tuple[0]
                            query = query.filter(
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) != prefixo
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
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) == prefixo
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
    
    @bp.route('/api/grupos-empresariais/listar')
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
    
    @bp.route('/api/grupos-empresariais/criar', methods=['POST'])
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
    
    @bp.route('/api/grupos-empresariais/<nome_grupo>', methods=['DELETE'])
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
    
    @bp.route('/api/previsao-demanda/calcular-comparacoes')
    @login_required
    def calcular_comparacoes():
        """Calcula todas as comparações para previsão de demanda"""
        try:
            from app.manufatura.services.demanda_service import DemandaService
            
            # Parâmetros
            mes = request.args.get('mes', type=int)
            ano = request.args.get('ano', type=int)
            cod_produto = request.args.get('cod_produto')
            grupo = request.args.get('grupo')  # Pode ser nome do grupo ou 'RESTANTE'
            
            if not all([mes, ano, cod_produto]):
                return jsonify({'erro': 'Parâmetros obrigatórios: mes, ano, cod_produto'}), 400
            
            service = DemandaService()
            
            # Calcula todas as comparações
            comparacoes = {
                'media_3_meses': service.calcular_media_historica(cod_produto, 3, mes, ano, grupo),
                'media_6_meses': service.calcular_media_historica(cod_produto, 6, mes, ano, grupo),
                'ano_anterior': service.calcular_mesmo_mes_ano_anterior(cod_produto, mes, ano, grupo),
                'demanda_ativa': 0  # Será implementado usando calcular_demanda_ativa existente
            }
            
            # Calcula demanda ativa (carteira)
            demanda_ativa = service.calcular_demanda_ativa(mes, ano, cod_produto)
            if demanda_ativa:
                # Filtra por grupo se necessário
                total_demanda = 0
                for item in demanda_ativa:
                    # Aqui precisaríamos verificar o grupo de cada item
                    # Por ora, soma tudo
                    total_demanda += item.get('qtd_demanda', 0)
                comparacoes['demanda_ativa'] = round(total_demanda, 3)
            
            return jsonify(comparacoes)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/produtos-historico')
    @login_required
    def listar_produtos_historico():
        """Lista produtos únicos do histórico, opcionalmente filtrados por grupo"""
        try:
            from app.manufatura.models import HistoricoPedidos
            from app.manufatura.services.demanda_service import DemandaService
            
            grupo = request.args.get('grupo')  # Pode ser nome do grupo ou 'RESTANTE'
            
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
                if grupo == 'RESTANTE':
                    # Busca todos os prefixos cadastrados
                    todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                        GrupoEmpresarial.ativo == True
                    ).all()
                    
                    # Exclui CNPJs que pertencem a algum grupo
                    if todos_prefixos:
                        for prefixo_tuple in todos_prefixos:
                            prefixo = prefixo_tuple[0]
                            query = query.filter(
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) != prefixo
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
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) == prefixo
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
    
    @bp.route('/api/grupos-empresariais/listar')
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
    
    @bp.route('/api/grupos-empresariais/criar', methods=['POST'])
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
    
    @bp.route('/api/grupos-empresariais/<nome_grupo>', methods=['DELETE'])
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
    
    @bp.route('/api/previsao-demanda/listar-grupos')
    @login_required
    def listar_grupos_empresariais():
        """Lista grupos empresariais com opção RESTANTE"""
        try:
            # Busca grupos únicos (DISTINCT nome_grupo)
            grupos_query = db.session.query(
                GrupoEmpresarial.nome_grupo,
                func.string_agg(GrupoEmpresarial.prefixo_cnpj, ',').label('prefixos'),
                func.max(GrupoEmpresarial.descricao).label('descricao')
            ).filter(
                GrupoEmpresarial.ativo == True
            ).group_by(
                GrupoEmpresarial.nome_grupo
            ).order_by(
                GrupoEmpresarial.nome_grupo
            ).all()
            
            # Monta resultado com RESTANTE primeiro
            resultado = [
                {'value': '', 'label': 'Todos os Grupos', 'prefixos': []},
                {'value': 'RESTANTE', 'label': 'Restante (sem grupo)', 'prefixos': []}
            ]
            
            # Adiciona grupos cadastrados
            for grupo in grupos_query:
                prefixos = grupo.prefixos.split(',') if grupo.prefixos else []
                
                resultado.append({
                    'value': grupo.nome_grupo,
                    'label': grupo.nome_grupo,
                    'prefixos': prefixos,
                    'descricao': grupo.descricao
                })
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/produtos-historico')
    @login_required
    def listar_produtos_historico():
        """Lista produtos únicos do histórico, opcionalmente filtrados por grupo"""
        try:
            from app.manufatura.models import HistoricoPedidos
            from app.manufatura.services.demanda_service import DemandaService
            
            grupo = request.args.get('grupo')  # Pode ser nome do grupo ou 'RESTANTE'
            
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
                if grupo == 'RESTANTE':
                    # Busca todos os prefixos cadastrados
                    todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                        GrupoEmpresarial.ativo == True
                    ).all()
                    
                    # Exclui CNPJs que pertencem a algum grupo
                    if todos_prefixos:
                        for prefixo_tuple in todos_prefixos:
                            prefixo = prefixo_tuple[0]
                            query = query.filter(
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) != prefixo
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
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) == prefixo
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
    
    @bp.route('/api/grupos-empresariais/listar')
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
    
    @bp.route('/api/grupos-empresariais/criar', methods=['POST'])
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
    
    @bp.route('/api/grupos-empresariais/<nome_grupo>', methods=['DELETE'])
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
    
    @bp.route('/api/previsao-demanda/salvar-previsao', methods=['POST'])
    @login_required
    def salvar_previsao_editada():
        """Salva ou atualiza previsão de demanda editada inline"""
        try:
            dados = request.json
            
            # Busca previsão existente ou cria nova
            previsao = PrevisaoDemanda.query.filter_by(
                data_mes=dados['mes'],
                data_ano=dados['ano'],
                cod_produto=dados['cod_produto'],
                nome_grupo=dados.get('grupo') or None
            ).first()
            
            if previsao:
                # Atualiza existente
                previsao.qtd_demanda_prevista = dados['qtd_prevista']
                previsao.disparo_producao = dados.get('disparo_producao', 'MTS')
                previsao.atualizado_em = datetime.now()
            else:
                # Cria nova
                previsao = PrevisaoDemanda(
                    data_mes=dados['mes'],
                    data_ano=dados['ano'],
                    nome_grupo=dados.get('grupo') or None,
                    cod_produto=dados['cod_produto'],
                    nome_produto=dados.get('nome_produto'),
                    qtd_demanda_prevista=dados['qtd_prevista'],
                    disparo_producao=dados.get('disparo_producao', 'MTS'),
                    criado_por=current_user.nome if current_user.is_authenticated else 'Sistema'
                )
                db.session.add(previsao)
            
            db.session.commit()
            
            return jsonify({
                'sucesso': True,
                'id': previsao.id,
                'mensagem': 'Previsão salva com sucesso'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/produtos-historico')
    @login_required
    def listar_produtos_historico():
        """Lista produtos únicos do histórico, opcionalmente filtrados por grupo"""
        try:
            from app.manufatura.models import HistoricoPedidos
            from app.manufatura.services.demanda_service import DemandaService
            
            grupo = request.args.get('grupo')  # Pode ser nome do grupo ou 'RESTANTE'
            
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
                if grupo == 'RESTANTE':
                    # Busca todos os prefixos cadastrados
                    todos_prefixos = db.session.query(GrupoEmpresarial.prefixo_cnpj).filter(
                        GrupoEmpresarial.ativo == True
                    ).all()
                    
                    # Exclui CNPJs que pertencem a algum grupo
                    if todos_prefixos:
                        for prefixo_tuple in todos_prefixos:
                            prefixo = prefixo_tuple[0]
                            query = query.filter(
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) != prefixo
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
                                func.substr(HistoricoPedidos.cnpj_cliente, 1, 8) == prefixo
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
    
    @bp.route('/api/grupos-empresariais/listar')
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
    
    @bp.route('/api/grupos-empresariais/criar', methods=['POST'])
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
    
    @bp.route('/api/grupos-empresariais/<nome_grupo>', methods=['DELETE'])
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