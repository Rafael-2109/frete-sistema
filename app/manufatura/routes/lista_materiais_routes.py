"""
Rotas de Lista de Materiais (BOM - Bill of Materials)
CRUD para estrutura de produtos COM AUDITORIA
"""
from flask import render_template, jsonify, request, flash, redirect, url_for, make_response
from flask_login import login_required, current_user
from app import db
from app.manufatura.models import ListaMateriais, ListaMateriaisHistorico
from app.producao.models import CadastroPalletizacao
from app.manufatura.services.bom_service import ServicoBOM
from app.manufatura.services.auditoria_service import ServicoAuditoria
from datetime import datetime
from io import BytesIO
import pandas as pd
import tempfile
import os
import logging

logger = logging.getLogger(__name__)


def register_lista_materiais_routes(bp):
    """Registra rotas de Lista de Materiais"""

    # ==========================================
    # ROTAS DE VISUALIZAÇÃO (HTML)
    # ==========================================

    @bp.route('/lista-materiais')
    @login_required
    def lista_materiais_index():
        """Tela principal de gestão de estrutura de produtos"""
        return render_template('manufatura/lista_materiais/index.html')

    @bp.route('/lista-materiais/estrutura/<cod_produto>')
    @login_required
    def lista_materiais_estrutura(cod_produto):
        """Tela de visualização detalhada da estrutura de um produto"""
        return render_template(
            'manufatura/lista_materiais/estrutura.html',
            cod_produto=cod_produto
        )

    # ==========================================
    # API - CONSULTAS
    # ==========================================

    @bp.route('/api/lista-materiais/<cod_produto>')
    @login_required
    def listar_estrutura(cod_produto):
        """
        Lista todos os componentes diretos de um produto

        Args:
            cod_produto: Código do produto produzido

        Returns:
            {
                'sucesso': bool,
                'produto': {
                    'cod_produto': str,
                    'nome_produto': str,
                    'tipo': str
                },
                'componentes': [
                    {
                        'id': int,
                        'cod_produto_componente': str,
                        'nome_produto_componente': str,
                        'qtd_utilizada': float,
                        'tipo_componente': str,
                        'status': str,
                        'versao': str
                    }
                ],
                'total_componentes': int
            }
        """
        try:
            # Buscar dados do produto principal
            produto = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto,
                ativo=True
            ).first()

            if not produto:
                return jsonify({
                    'sucesso': False,
                    'erro': f'Produto {cod_produto} não encontrado'
                }), 404

            # Classificar produto
            classificacao = ServicoBOM._classificar_produto(cod_produto)

            # Buscar componentes
            componentes_db = ListaMateriais.query.filter_by(
                cod_produto_produzido=cod_produto,
                status='ativo'
            ).order_by(ListaMateriais.cod_produto_componente).all()

            componentes = []
            for comp in componentes_db:
                # Buscar dados do componente
                comp_cadastro = CadastroPalletizacao.query.filter_by(
                    cod_produto=comp.cod_produto_componente,
                    ativo=True
                ).first()

                # Classificar componente
                comp_classificacao = ServicoBOM._classificar_produto(comp.cod_produto_componente)

                componentes.append({
                    'id': comp.id,
                    'cod_produto_componente': comp.cod_produto_componente,
                    'nome_produto_componente': comp.nome_produto_componente or (
                        comp_cadastro.nome_produto if comp_cadastro else f'Produto {comp.cod_produto_componente}'
                    ),
                    'qtd_utilizada': float(comp.qtd_utilizada),
                    'tipo_componente': comp_classificacao['tipo'],
                    'produto_produzido': comp_classificacao['produto_produzido'],
                    'produto_comprado': comp_classificacao['produto_comprado'],
                    'status': comp.status,
                    'versao': comp.versao
                })

            return jsonify({
                'sucesso': True,
                'produto': {
                    'cod_produto': cod_produto,
                    'nome_produto': produto.nome_produto,
                    'tipo': classificacao['tipo'],
                    'produto_produzido': classificacao['produto_produzido'],
                    'produto_vendido': classificacao['produto_vendido']
                },
                'componentes': componentes,
                'total_componentes': len(componentes)
            })

        except Exception as e:
            logger.error(f"Erro ao listar estrutura de {cod_produto}: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    @bp.route('/api/lista-materiais/explodir/<cod_produto>')
    @login_required
    def explodir_estrutura(cod_produto):
        """
        Explode estrutura BOM completa de um produto (todos os níveis)

        Query Params:
            - qtd_necessaria: Quantidade a produzir (default: 1)
            - incluir_estoque: Se True, inclui análise de estoque (default: False)

        Returns:
            {
                'sucesso': bool,
                'estrutura_completa': Dict,  # BOM explodido
                'intermediarios_necessarios': List[Dict],  # Se incluir_estoque=True
                'componentes_necessarios': List[Dict],  # Se incluir_estoque=True
                'viabilidade': Dict  # Se incluir_estoque=True
            }
        """
        try:
            qtd_necessaria = request.args.get('qtd_necessaria', 1.0, type=float)
            incluir_estoque = request.args.get('incluir_estoque', 'false').lower() == 'true'

            if qtd_necessaria <= 0:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Quantidade deve ser maior que zero'
                }), 400

            if not incluir_estoque:
                # Apenas explosão BOM sem análise de estoque
                estrutura = ServicoBOM.explodir_bom(cod_produto, qtd_necessaria)

                return jsonify({
                    'sucesso': True,
                    'estrutura_completa': estrutura
                })
            else:
                # Explosão BOM com análise de estoque e sugestões
                resultado = ServicoBOM.sugerir_programacao_intermediarios(
                    cod_produto=cod_produto,
                    qtd_necessaria=qtd_necessaria,
                    incluir_componentes_completos=True
                )

                return jsonify({
                    'sucesso': True,
                    **resultado
                })

        except Exception as e:
            logger.error(f"Erro ao explodir estrutura de {cod_produto}: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    @bp.route('/api/lista-materiais/validar/<cod_produto>')
    @login_required
    def validar_estrutura(cod_produto):
        """
        Valida estrutura BOM (detecta loops, inconsistências)

        Returns:
            {
                'sucesso': bool,
                'valido': bool,
                'erros': List[str],
                'avisos': List[str],
                'estrutura_valida': bool
            }
        """
        try:
            resultado = ServicoBOM.validar_hierarquia_bom(cod_produto)

            return jsonify({
                'sucesso': True,
                **resultado
            })

        except Exception as e:
            logger.error(f"Erro ao validar estrutura de {cod_produto}: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    # ==========================================
    # API - CRUD
    # ==========================================

    @bp.route('/api/lista-materiais', methods=['POST'])
    @login_required
    def criar_componente():
        """
        Cria um novo componente na estrutura de um produto

        Body JSON:
            {
                'cod_produto_produzido': str (obrigatório),
                'cod_produto_componente': str (obrigatório),
                'qtd_utilizada': float (obrigatório),
                'versao': str (opcional)
            }

        Returns:
            {
                'sucesso': bool,
                'id': int,
                'mensagem': str
            }
        """
        try:
            dados = request.get_json()

            # Validar campos obrigatórios
            if not dados.get('cod_produto_produzido'):
                return jsonify({
                    'sucesso': False,
                    'erro': 'Código do produto produzido é obrigatório'
                }), 400

            if not dados.get('cod_produto_componente'):
                return jsonify({
                    'sucesso': False,
                    'erro': 'Código do componente é obrigatório'
                }), 400

            if not dados.get('qtd_utilizada'):
                return jsonify({
                    'sucesso': False,
                    'erro': 'Quantidade utilizada é obrigatória'
                }), 400

            qtd_utilizada = float(dados['qtd_utilizada'])
            if qtd_utilizada <= 0:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Quantidade deve ser maior que zero'
                }), 400

            # Verificar se produto produzido existe
            produto = CadastroPalletizacao.query.filter_by(
                cod_produto=dados['cod_produto_produzido'],
                ativo=True
            ).first()

            if not produto:
                return jsonify({
                    'sucesso': False,
                    'erro': f"Produto {dados['cod_produto_produzido']} não encontrado"
                }), 404

            # Verificar se componente existe
            componente = CadastroPalletizacao.query.filter_by(
                cod_produto=dados['cod_produto_componente'],
                ativo=True
            ).first()

            if not componente:
                return jsonify({
                    'sucesso': False,
                    'erro': f"Componente {dados['cod_produto_componente']} não encontrado"
                }), 404

            # Verificar se já existe (duplicidade)
            versao = dados.get('versao', 'v1')
            existente = ListaMateriais.query.filter_by(
                cod_produto_produzido=dados['cod_produto_produzido'],
                cod_produto_componente=dados['cod_produto_componente'],
                versao=versao,
                status='ativo'
            ).first()

            if existente:
                return jsonify({
                    'sucesso': False,
                    'erro': f"Componente {dados['cod_produto_componente']} já existe na estrutura de {dados['cod_produto_produzido']}"
                }), 409

            # Criar novo componente
            novo = ListaMateriais(
                cod_produto_produzido=dados['cod_produto_produzido'],
                nome_produto_produzido=produto.nome_produto,
                cod_produto_componente=dados['cod_produto_componente'],
                nome_produto_componente=componente.nome_produto,
                qtd_utilizada=qtd_utilizada,
                versao=versao,
                status='ativo',
                criado_em=datetime.utcnow(),
                criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )

            db.session.add(novo)
            db.session.commit()

            # ✅ AUDITORIA: Registrar criação no histórico
            usuario = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            ServicoAuditoria.registrar_criacao(
                componente=novo,
                usuario=usuario,
                motivo='Componente adicionado à estrutura'
            )

            logger.info(
                f"✅ Componente criado: {dados['cod_produto_componente']} "
                f"na estrutura de {dados['cod_produto_produzido']} "
                f"por {usuario}"
            )

            return jsonify({
                'sucesso': True,
                'id': novo.id,
                'mensagem': 'Componente criado com sucesso'
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar componente: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    @bp.route('/api/lista-materiais/<int:id>', methods=['PUT'])
    @login_required
    def editar_componente(id):
        """
        Edita um componente existente

        Body JSON:
            {
                'qtd_utilizada': float (opcional),
                'versao': str (opcional),
                'status': str (opcional)
            }

        Returns:
            {
                'sucesso': bool,
                'mensagem': str
            }
        """
        try:
            componente = ListaMateriais.query.get(id)

            if not componente:
                return jsonify({
                    'sucesso': False,
                    'erro': f'Componente com ID {id} não encontrado'
                }), 404

            dados = request.get_json()

            # ✅ AUDITORIA: Guardar valor anterior da quantidade
            qtd_anterior = componente.qtd_utilizada

            # Verificar se houve alguma mudança significativa
            houve_mudanca = False

            # Atualizar quantidade se fornecida
            if 'qtd_utilizada' in dados:
                qtd_nova = float(dados['qtd_utilizada'])
                if qtd_nova <= 0:
                    return jsonify({
                        'sucesso': False,
                        'erro': 'Quantidade deve ser maior que zero'
                    }), 400
                if qtd_nova != componente.qtd_utilizada:
                    componente.qtd_utilizada = qtd_nova
                    houve_mudanca = True

            # Atualizar versão se fornecida
            if 'versao' in dados:
                componente.versao = dados['versao']

            # Atualizar status se fornecido
            if 'status' in dados:
                if dados['status'] not in ['ativo', 'inativo']:
                    return jsonify({
                        'sucesso': False,
                        'erro': "Status deve ser 'ativo' ou 'inativo'"
                    }), 400
                componente.status = dados['status']

            # ✅ AUDITORIA: Atualizar campos de auditoria
            usuario = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            componente.atualizado_em = datetime.utcnow()
            componente.atualizado_por = usuario

            db.session.commit()

            # ✅ AUDITORIA: Registrar edição no histórico (se houve mudança)
            if houve_mudanca:
                ServicoAuditoria.registrar_edicao(
                    componente=componente,
                    usuario=usuario,
                    qtd_anterior=float(qtd_anterior),
                    motivo='Quantidade utilizada atualizada'
                )

            logger.info(
                f"✅ Componente {id} editado por {usuario}"
            )

            return jsonify({
                'sucesso': True,
                'mensagem': 'Componente atualizado com sucesso'
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar componente {id}: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    @bp.route('/api/lista-materiais/<int:id>', methods=['DELETE'])
    @login_required
    def deletar_componente(id):
        """
        Deleta um componente (soft delete - muda status para 'inativo')

        Returns:
            {
                'sucesso': bool,
                'mensagem': str
            }
        """
        try:
            componente = ListaMateriais.query.get(id)

            if not componente:
                return jsonify({
                    'sucesso': False,
                    'erro': f'Componente com ID {id} não encontrado'
                }), 404

            # ✅ AUDITORIA: Soft delete COM registro de auditoria
            componente.status = 'inativo'
            usuario = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'

            # Registrar inativação no histórico (já atualiza campos de auditoria)
            ServicoAuditoria.registrar_inativacao(
                componente=componente,
                usuario=usuario,
                motivo='Componente removido da estrutura'
            )

            logger.info(
                f"✅ Componente {id} ({componente.cod_produto_componente}) "
                f"removido da estrutura de {componente.cod_produto_produzido} "
                f"por {usuario}"
            )

            return jsonify({
                'sucesso': True,
                'mensagem': 'Componente removido com sucesso'
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao deletar componente {id}: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    # ==========================================
    # API - HISTÓRICO E AUDITORIA
    # ==========================================

    @bp.route('/api/lista-materiais/historico/<int:lista_materiais_id>')
    @login_required
    def historico_componente(lista_materiais_id):
        """
        Retorna histórico de alterações de um componente específico

        Args:
            lista_materiais_id: ID do registro em lista_materiais

        Returns:
            {
                'sucesso': bool,
                'historico': [
                    {
                        'id': int,
                        'operacao': str,
                        'alterado_em': str,
                        'alterado_por': str,
                        'qtd_utilizada_antes': float,
                        'qtd_utilizada_depois': float,
                        ...
                    }
                ],
                'total': int
            }
        """
        try:
            historico = ServicoAuditoria.buscar_historico_componente(lista_materiais_id)

            return jsonify({
                'sucesso': True,
                'historico': [h.to_dict() for h in historico],
                'total': len(historico)
            })

        except Exception as e:
            logger.error(f"Erro ao buscar histórico do componente {lista_materiais_id}: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    @bp.route('/api/lista-materiais/historico-produto/<cod_produto>')
    @login_required
    def historico_produto(cod_produto):
        """
        Retorna histórico de alterações de um produto (todas as mudanças na estrutura)

        Query Params:
            - limit: Número máximo de registros (default: 100)

        Returns:
            {
                'sucesso': bool,
                'historico': [...],
                'total': int
            }
        """
        try:
            limit = request.args.get('limit', 100, type=int)
            historico = ServicoAuditoria.buscar_historico_produto(cod_produto, limit)

            return jsonify({
                'sucesso': True,
                'historico': [h.to_dict() for h in historico],
                'total': len(historico)
            })

        except Exception as e:
            logger.error(f"Erro ao buscar histórico do produto {cod_produto}: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    @bp.route('/api/lista-materiais/historico-usuario/<usuario>')
    @login_required
    def historico_usuario(usuario):
        """
        Retorna histórico de alterações feitas por um usuário

        Query Params:
            - limit: Número máximo de registros (default: 100)

        Returns:
            {
                'sucesso': bool,
                'historico': [...],
                'total': int
            }
        """
        try:
            limit = request.args.get('limit', 100, type=int)
            historico = ServicoAuditoria.buscar_historico_usuario(usuario, limit)

            return jsonify({
                'sucesso': True,
                'historico': [h.to_dict() for h in historico],
                'total': len(historico)
            })

        except Exception as e:
            logger.error(f"Erro ao buscar histórico do usuário {usuario}: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    @bp.route('/api/lista-materiais/estatisticas-historico')
    @login_required
    def estatisticas_historico_lista_materiais():
        """
        Retorna estatísticas gerais do histórico de lista de materiais

        Returns:
            {
                'sucesso': bool,
                'estatisticas': {
                    'total_registros': int,
                    'por_operacao': {...},
                    'usuarios_mais_ativos': [...]
                }
            }
        """
        try:
            estatisticas = ServicoAuditoria.estatisticas_historico()

            return jsonify({
                'sucesso': True,
                'estatisticas': estatisticas
            })

        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    # ==========================================
    # API - LISTAGENS
    # ==========================================

    @bp.route('/api/lista-materiais/produtos-produzidos')
    @login_required
    def listar_produtos_produzidos():
        """
        Lista todos os produtos que podem ter estrutura (produto_produzido=True)

        Query Params:
            - busca: Texto para filtrar por código ou nome (opcional)

        Returns:
            {
                'sucesso': bool,
                'produtos': [
                    {
                        'cod_produto': str,
                        'nome_produto': str,
                        'tipo': str,
                        'tem_estrutura': bool
                    }
                ],
                'total': int
            }
        """
        try:
            busca = request.args.get('busca', '').strip()

            # Query base
            query = CadastroPalletizacao.query.filter_by(
                produto_produzido=True,
                ativo=True
            )

            # Filtro de busca
            if busca:
                query = query.filter(
                    db.or_(
                        CadastroPalletizacao.cod_produto.ilike(f'%{busca}%'),
                        CadastroPalletizacao.nome_produto.ilike(f'%{busca}%')
                    )
                )

            produtos_db = query.order_by(CadastroPalletizacao.nome_produto).all()

            produtos = []
            for prod in produtos_db:
                # Verificar se tem estrutura cadastrada
                tem_estrutura = db.session.query(
                    db.exists().where(
                        db.and_(
                            ListaMateriais.cod_produto_produzido == prod.cod_produto,
                            ListaMateriais.status == 'ativo'
                        )
                    )
                ).scalar()

                classificacao = ServicoBOM._classificar_produto(prod.cod_produto)

                produtos.append({
                    'cod_produto': prod.cod_produto,
                    'nome_produto': prod.nome_produto,
                    'tipo': classificacao['tipo'],
                    'tem_estrutura': tem_estrutura
                })

            return jsonify({
                'sucesso': True,
                'produtos': produtos,
                'total': len(produtos)
            })

        except Exception as e:
            logger.error(f"Erro ao listar produtos produzidos: {e}")
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 500

    # ==========================================
    # IMPORTAÇÃO / EXPORTAÇÃO
    # ==========================================

    @bp.route('/lista-materiais/importar')
    @login_required
    def importar_lista_materiais():
        """Tela para importar Lista de Materiais via Excel"""
        return render_template('manufatura/lista_materiais/importar.html')

    @bp.route('/lista-materiais/importar', methods=['POST'])
    @login_required
    def processar_importacao_lista_materiais():
        """
        Processar importação de Lista de Materiais via Excel/CSV

        Formato esperado:
        - cod_produto_produzido (obrigatório)
        - cod_produto_componente (obrigatório)
        - qtd_utilizada (obrigatório)
        - versao (opcional, default='v1')
        """
        try:
            if 'arquivo' not in request.files:
                flash('Nenhum arquivo selecionado!', 'error')
                return redirect(url_for('manufatura.importar_lista_materiais'))

            arquivo = request.files['arquivo']
            if arquivo.filename == '':
                flash('Nenhum arquivo selecionado!', 'error')
                return redirect(url_for('manufatura.importar_lista_materiais'))

            if not arquivo.filename.lower().endswith(('.xlsx', '.csv')):
                flash('Tipo de arquivo não suportado! Use apenas .xlsx ou .csv', 'error')
                return redirect(url_for('manufatura.importar_lista_materiais'))

            # Processar arquivo temporário
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                    arquivo.save(temp_file.name)

                    if arquivo.filename.lower().endswith('.xlsx'):
                        df = pd.read_excel(temp_file.name)
                    else:
                        df = pd.read_csv(temp_file.name, encoding='utf-8', sep=';')

                    os.unlink(temp_file.name)
            except Exception as e:
                flash(f'Erro ao processar arquivo: {str(e)}', 'error')
                return redirect(url_for('manufatura.importar_lista_materiais'))

            # Validar colunas obrigatórias
            colunas_obrigatorias = ['cod_produto_produzido', 'cod_produto_componente', 'qtd_utilizada']
            colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]

            if colunas_faltando:
                flash(f'❌ Colunas obrigatórias não encontradas: {", ".join(colunas_faltando)}', 'error')
                return redirect(url_for('manufatura.importar_lista_materiais'))

            # Processar dados
            importados = 0
            atualizados = 0
            erros = []
            usuario = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'

            for index, row in df.iterrows():
                try:
                    cod_produzido = str(row.get('cod_produto_produzido', '')).strip()
                    cod_componente = str(row.get('cod_produto_componente', '')).strip()

                    if not cod_produzido or not cod_componente:
                        continue

                    qtd_utilizada = float(row.get('qtd_utilizada', 0))
                    if qtd_utilizada <= 0:
                        erros.append(f"Linha {index + 1}: Quantidade deve ser maior que zero")
                        continue

                    versao = str(row.get('versao', 'v1')).strip() or 'v1'

                    # Verificar se produto produzido existe
                    produto = CadastroPalletizacao.query.filter_by(
                        cod_produto=cod_produzido,
                        ativo=True
                    ).first()

                    if not produto:
                        erros.append(f"Linha {index + 1}: Produto {cod_produzido} não encontrado")
                        continue

                    # Verificar se componente existe
                    componente_cadastro = CadastroPalletizacao.query.filter_by(
                        cod_produto=cod_componente,
                        ativo=True
                    ).first()

                    if not componente_cadastro:
                        erros.append(f"Linha {index + 1}: Componente {cod_componente} não encontrado")
                        continue

                    # Verificar se já existe
                    existente = ListaMateriais.query.filter_by(
                        cod_produto_produzido=cod_produzido,
                        cod_produto_componente=cod_componente,
                        versao=versao
                    ).first()

                    if existente:
                        # Atualizar
                        qtd_anterior = existente.qtd_utilizada
                        existente.qtd_utilizada = qtd_utilizada
                        existente.atualizado_em = datetime.utcnow()
                        existente.atualizado_por = usuario

                        # Registrar auditoria
                        if qtd_anterior != qtd_utilizada:
                            ServicoAuditoria.registrar_edicao(
                                componente=existente,
                                usuario=usuario,
                                qtd_anterior=float(qtd_anterior),
                                motivo='Atualizado via importação'
                            )

                        atualizados += 1
                    else:
                        # Criar novo
                        novo = ListaMateriais(
                            cod_produto_produzido=cod_produzido,
                            nome_produto_produzido=produto.nome_produto,
                            cod_produto_componente=cod_componente,
                            nome_produto_componente=componente_cadastro.nome_produto,
                            qtd_utilizada=qtd_utilizada,
                            versao=versao,
                            status='ativo',
                            criado_em=datetime.utcnow(),
                            criado_por=usuario
                        )

                        db.session.add(novo)
                        db.session.flush()  # Para ter o ID

                        # Registrar auditoria
                        ServicoAuditoria.registrar_criacao(
                            componente=novo,
                            usuario=usuario,
                            motivo='Criado via importação'
                        )

                        importados += 1

                except Exception as e:
                    erros.append(f"Linha {index + 1}: {str(e)}")
                    continue

            # Commit das alterações
            db.session.commit()

            # Mensagens de resultado
            if importados > 0 or atualizados > 0:
                mensagem = f"✅ Importação concluída: {importados} novos componentes, {atualizados} atualizados"
                if erros:
                    mensagem += f". {len(erros)} erros encontrados."
                flash(mensagem, 'success')
            else:
                flash("⚠️ Nenhum componente foi importado.", 'warning')

            if erros[:5]:  # Mostrar apenas os primeiros 5 erros
                for erro in erros[:5]:
                    flash(f"❌ {erro}", 'error')

            return redirect(url_for('manufatura.lista_materiais_index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro durante importação: {str(e)}', 'error')
            return redirect(url_for('manufatura.importar_lista_materiais'))

    @bp.route('/lista-materiais/baixar-modelo')
    @login_required
    def baixar_modelo_lista_materiais():
        """Baixar modelo Excel para importação de Lista de Materiais"""
        try:
            # Dados de exemplo
            dados_exemplo = {
                'cod_produto_produzido': ['4080177', '4080177', '4729098'],
                'cod_produto_componente': ['MP001', 'MP002', 'MP003'],
                'qtd_utilizada': [2.5, 1.0, 0.5],
                'versao': ['v1', 'v1', 'v1']
            }

            df = pd.DataFrame(dados_exemplo)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Dados', index=False)

                # Instruções
                instrucoes = pd.DataFrame({
                    'INSTRUÇÕES IMPORTANTES': [
                        '1. Use as colunas EXATAMENTE como estão nomeadas',
                        '2. Campos obrigatórios: cod_produto_produzido, cod_produto_componente, qtd_utilizada',
                        '3. cod_produto_produzido: Código do produto que será fabricado',
                        '4. cod_produto_componente: Código do componente/matéria-prima',
                        '5. qtd_utilizada: Quantidade do componente necessária para produzir 1 unidade',
                        '6. versao: Versão da estrutura (opcional, default=v1)',
                        '7. Ambos os produtos devem existir em Cadastro de Palletização',
                        '8. Comportamento: CRIA novos ou ATUALIZA existentes'
                    ]
                })
                instrucoes.to_excel(writer, sheet_name='Instruções', index=False)

            output.seek(0)

            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = 'attachment; filename=modelo_lista_materiais.xlsx'

            return response

        except Exception as e:
            flash(f'Erro ao gerar modelo: {str(e)}', 'error')
            return redirect(url_for('manufatura.lista_materiais_index'))

    @bp.route('/lista-materiais/exportar-dados')
    @login_required
    def exportar_dados_lista_materiais():
        """Exportar dados existentes de Lista de Materiais"""
        try:
            # Buscar dados ativos
            componentes = ListaMateriais.query.filter_by(status='ativo').order_by(
                ListaMateriais.cod_produto_produzido,
                ListaMateriais.cod_produto_componente
            ).all()

            if not componentes:
                flash('Nenhum dado encontrado para exportar.', 'warning')
                return redirect(url_for('manufatura.lista_materiais_index'))

            # Converter para Excel
            dados_export = []
            for comp in componentes:
                dados_export.append({
                    'cod_produto_produzido': comp.cod_produto_produzido,
                    'nome_produto_produzido': comp.nome_produto_produzido,
                    'cod_produto_componente': comp.cod_produto_componente,
                    'nome_produto_componente': comp.nome_produto_componente,
                    'qtd_utilizada': float(comp.qtd_utilizada),
                    'versao': comp.versao,
                    'status': comp.status,
                    'criado_em': comp.criado_em.strftime('%d/%m/%Y %H:%M') if comp.criado_em else '',
                    'criado_por': comp.criado_por or '',
                    'atualizado_em': comp.atualizado_em.strftime('%d/%m/%Y %H:%M') if comp.atualizado_em else '',
                    'atualizado_por': comp.atualizado_por or ''
                })

            df = pd.DataFrame(dados_export)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Lista de Materiais', index=False)

                # Estatísticas
                stats = pd.DataFrame({
                    'Estatística': [
                        'Total de Componentes',
                        'Produtos com Estrutura',
                        'Componentes Únicos Utilizados'
                    ],
                    'Valor': [
                        len(componentes),
                        len(set(c.cod_produto_produzido for c in componentes)),
                        len(set(c.cod_produto_componente for c in componentes))
                    ]
                })
                stats.to_excel(writer, sheet_name='Estatísticas', index=False)

            output.seek(0)

            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = f'attachment; filename=lista_materiais_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

            return response

        except Exception as e:
            flash(f'Erro ao exportar dados: {str(e)}', 'error')
            return redirect(url_for('manufatura.lista_materiais_index'))
