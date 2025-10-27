"""
Rotas de Previsão de Demanda - Versão Limpa
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
    
    @bp.route('/api/previsao-demanda/listar-grupos')
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
            
            # Formata resposta incluindo RESTANTE
            opcoes = [
                {'value': '', 'label': 'Todos os Grupos'}
            ]
            
            for grupo in grupos:
                opcoes.append({
                    'value': grupo.nome_grupo,
                    'label': grupo.nome_grupo
                })
            
            # Adiciona opção RESTANTE (clientes sem grupo)
            opcoes.append({
                'value': 'RESTANTE',
                'label': 'RESTANTE (Sem Grupo)'
            })
            
            return jsonify(opcoes)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/calcular-comparacoes')
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
    
    @bp.route('/api/previsao-demanda/buscar-existentes')
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
    
    @bp.route('/api/previsao-demanda/salvar', methods=['POST'])
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
            
            # Busca ou cria previsão
            previsao = PrevisaoDemanda.query.filter_by(
                data_mes=dados['mes'], # type: ignore
                data_ano=dados['ano'], # type: ignore
                cod_produto=dados['cod_produto'], # type: ignore
                nome_grupo=dados.get('grupo', 'GERAL') # type: ignore
            ).first()
            
            if not previsao:
                previsao = PrevisaoDemanda(
                    data_mes=dados['mes'], # type: ignore
                    data_ano=dados['ano'], # type: ignore
                    cod_produto=dados['cod_produto'], # type: ignore
                    nome_produto=dados.get('nome_produto'), # type: ignore
                    nome_grupo=dados.get('grupo', 'GERAL') # type: ignore
                )
                db.session.add(previsao)
            
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
    
    @bp.route('/api/previsao-demanda/produtos-historico')
    @login_required
    def listar_produtos_historico():
        """Lista produtos únicos do histórico, opcionalmente filtrados por grupo"""
        try:
            from app.manufatura.models import HistoricoPedidos
            
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
    
    @bp.route('/api/previsao-demanda/debug-carteira/<cod_produto>')
    @login_required
    def debug_carteira(cod_produto):
        """Debug endpoint para verificar dados da CarteiraPrincipal"""
        try:
            from app.carteira.models import CarteiraPrincipal
            
            # Total de registros do produto
            total = db.session.query(CarteiraPrincipal).filter(
                CarteiraPrincipal.cod_produto == cod_produto
            ).count()
            
            # Registros com saldo > 0
            com_saldo = db.session.query(CarteiraPrincipal).filter(
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).count()
            
            # Soma total
            soma = db.session.query(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
            ).filter(
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).scalar()
            
            # Primeiros 5 registros
            amostras = db.session.query(
                CarteiraPrincipal.num_pedido,
                CarteiraPrincipal.qtd_saldo_produto_pedido,
                CarteiraPrincipal.cnpj_cpf
            ).filter(
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).limit(5).all()
            
            return jsonify({
                'cod_produto': cod_produto,
                'total_registros': total,
                'registros_com_saldo': com_saldo,
                'soma_total': float(soma or 0),
                'amostras': [{
                    'pedido': a.num_pedido,
                    'saldo': float(a.qtd_saldo_produto_pedido),
                    'cnpj': a.cnpj_cpf
                } for a in amostras]
            })
            
        except Exception as e:
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