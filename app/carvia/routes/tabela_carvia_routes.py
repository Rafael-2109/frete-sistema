"""
Rotas CRUD para Cotacao CarVia v2
==================================
- Grupos de Cliente (CNPJ-based)
- Tabelas de Frete CarVia (preco de venda)
- Cidades Atendidas CarVia
"""

import logging
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# UFs brasileiras para selects
UFS_BRASIL = [
    'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
    'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
    'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO',
]


def register_tabela_carvia_routes(bp):

    # =================================================================
    # GRUPOS DE CLIENTE
    # =================================================================

    @bp.route('/configuracoes/grupos-cliente') # type: ignore
    @login_required
    def listar_grupos_cliente(): # type: ignore
        """Lista grupos de cliente com membros"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaGrupoCliente
        grupos = CarviaGrupoCliente.query.order_by(
            CarviaGrupoCliente.nome.asc()
        ).all()

        return render_template(
            'carvia/configuracoes/grupos_cliente.html',
            grupos=grupos,
        )

    @bp.route('/api/grupos-cliente', methods=['POST']) # type: ignore
    @login_required
    def criar_grupo_cliente(): # type: ignore
        """Cria novo grupo de cliente (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaGrupoCliente

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        nome = (data.get('nome') or '').strip()
        if not nome:
            return jsonify({'erro': 'Nome e obrigatorio.'}), 400

        existente = CarviaGrupoCliente.query.filter_by(nome=nome).first()
        if existente:
            return jsonify({'erro': f'Grupo "{nome}" ja existe.'}), 409

        try:
            grupo = CarviaGrupoCliente(
                nome=nome,
                descricao=(data.get('descricao') or '').strip() or None,
                criado_em=agora_utc_naive(),
                criado_por=current_user.email,
            )
            db.session.add(grupo)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': grupo.id,
                'nome': grupo.nome,
                'mensagem': f'Grupo "{grupo.nome}" criado com sucesso.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar grupo cliente: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/grupos-cliente/<int:gid>', methods=['PUT']) # type: ignore
    @login_required
    def atualizar_grupo_cliente(gid): # type: ignore
        """Atualiza grupo de cliente (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaGrupoCliente

        grupo = db.session.get(CarviaGrupoCliente, gid)
        if not grupo:
            return jsonify({'erro': 'Grupo nao encontrado.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            if 'nome' in data:
                nome = (data['nome'] or '').strip()
                if not nome:
                    return jsonify({'erro': 'Nome e obrigatorio.'}), 400
                existente = CarviaGrupoCliente.query.filter(
                    CarviaGrupoCliente.nome == nome,
                    CarviaGrupoCliente.id != gid,
                ).first()
                if existente:
                    return jsonify({'erro': f'Grupo "{nome}" ja existe.'}), 409
                grupo.nome = nome

            if 'descricao' in data:
                grupo.descricao = (data['descricao'] or '').strip() or None

            if 'ativo' in data:
                grupo.ativo = data['ativo']

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'id': grupo.id,
                'mensagem': f'Grupo "{grupo.nome}" atualizado.',
            })

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar grupo #%s: %s", gid, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/grupos-cliente/<int:gid>', methods=['DELETE']) # type: ignore
    @login_required
    def desativar_grupo_cliente(gid): # type: ignore
        """Desativa grupo de cliente.

        W7 (Sprint 2): checa referencias ativas em CarviaTabelaFrete.
        Nao bloqueia (soft-delete e reversivel), mas informa quantas
        tabelas continuam usando o grupo.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaGrupoCliente, CarviaTabelaFrete

        grupo = db.session.get(CarviaGrupoCliente, gid)
        if not grupo:
            return jsonify({'erro': 'Grupo nao encontrado.'}), 404

        # W7: Verificar referencias ativas
        refs_tabelas = CarviaTabelaFrete.query.filter_by(
            grupo_cliente_id=gid,
            ativo=True,
        ).count()

        try:
            grupo.ativo = False
            db.session.commit()

            mensagem = f'Grupo "{grupo.nome}" desativado.'
            if refs_tabelas > 0:
                mensagem += (
                    f' AVISO: {refs_tabelas} tabela(s) de frete ainda '
                    f'referenciam este grupo — considere reavaliar.'
                )
            return jsonify({
                'sucesso': True,
                'mensagem': mensagem,
                'refs_tabelas': refs_tabelas,
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao desativar grupo #%s: %s", gid, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # --- Membros do grupo ---

    @bp.route('/api/grupos-cliente/<int:gid>/membros', methods=['POST']) # type: ignore
    @login_required
    def adicionar_membro_grupo(gid): # type: ignore
        """Adiciona CNPJ membro ao grupo"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaGrupoCliente, CarviaGrupoClienteMembro

        grupo = db.session.get(CarviaGrupoCliente, gid)
        if not grupo:
            return jsonify({'erro': 'Grupo nao encontrado.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        cnpj = (data.get('cnpj') or '').strip()
        cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())
        if not cnpj_limpo or len(cnpj_limpo) < 11:
            return jsonify({'erro': 'CNPJ invalido.'}), 400

        # Verificar duplicata
        existente = CarviaGrupoClienteMembro.query.filter_by(
            grupo_id=gid, cnpj=cnpj_limpo
        ).first()
        if existente:
            return jsonify({'erro': 'CNPJ ja esta no grupo.'}), 409

        try:
            membro = CarviaGrupoClienteMembro(
                grupo_id=gid,
                cnpj=cnpj_limpo,
                nome_empresa=(data.get('nome_empresa') or '').strip() or None,
                criado_em=agora_utc_naive(),
                criado_por=current_user.email,
            )
            db.session.add(membro)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': membro.id,
                'cnpj': membro.cnpj,
                'nome_empresa': membro.nome_empresa,
                'mensagem': f'CNPJ {cnpj_limpo} adicionado ao grupo.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao adicionar membro: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/grupos-cliente/<int:gid>/membros/<int:mid>', methods=['DELETE']) # type: ignore
    @login_required
    def remover_membro_grupo(gid, mid): # type: ignore
        """Remove membro do grupo"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaGrupoClienteMembro

        membro = db.session.get(CarviaGrupoClienteMembro, mid)
        if not membro or membro.grupo_id != gid:
            return jsonify({'erro': 'Membro nao encontrado.'}), 404

        try:
            cnpj = membro.cnpj
            db.session.delete(membro)
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'mensagem': f'CNPJ {cnpj} removido do grupo.',
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao remover membro #%s: %s", mid, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # =================================================================
    # TABELAS DE FRETE CARVIA
    # =================================================================

    @bp.route('/configuracoes/tabelas-frete') # type: ignore
    @login_required
    def listar_tabelas_carvia(): # type: ignore
        """Lista tabelas de frete CarVia — agrupada por combinacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaTabelaFrete, CarviaGrupoCliente

        grupo_filtro = request.args.get('grupo_cliente_id', '')
        uf_destino_filtro = request.args.get('uf_destino', '').strip().upper()
        uf_origem_filtro = request.args.get('uf_origem', '').strip().upper()
        tipo_carga_filtro = request.args.get('tipo_carga', '').strip()
        busca_filtro = request.args.get('busca', '').strip()

        query = db.session.query(
            CarviaTabelaFrete.nome_tabela,
            CarviaTabelaFrete.uf_origem,
            CarviaTabelaFrete.uf_destino,
            CarviaTabelaFrete.tipo_carga,
        ).filter(
            CarviaTabelaFrete.ativo == True,  # noqa: E712
        )

        if grupo_filtro:
            gid = int(grupo_filtro) if grupo_filtro != 'standard' else None
            if gid:
                query = query.filter(CarviaTabelaFrete.grupo_cliente_id == gid)
            else:
                query = query.filter(CarviaTabelaFrete.grupo_cliente_id.is_(None))

        if uf_destino_filtro:
            query = query.filter(CarviaTabelaFrete.uf_destino == uf_destino_filtro)

        if uf_origem_filtro:
            query = query.filter(CarviaTabelaFrete.uf_origem == uf_origem_filtro)

        if tipo_carga_filtro:
            query = query.filter(CarviaTabelaFrete.tipo_carga == tipo_carga_filtro)

        if busca_filtro:
            query = query.filter(
                CarviaTabelaFrete.nome_tabela.ilike(f'%{busca_filtro}%')
            )

        combos = query.group_by(
            CarviaTabelaFrete.nome_tabela,
            CarviaTabelaFrete.uf_origem,
            CarviaTabelaFrete.uf_destino,
            CarviaTabelaFrete.tipo_carga,
        ).order_by(
            CarviaTabelaFrete.uf_destino,
            CarviaTabelaFrete.nome_tabela,
            CarviaTabelaFrete.uf_origem,
        ).all()

        grupos = CarviaGrupoCliente.query.filter_by(ativo=True).order_by(
            CarviaGrupoCliente.nome.asc()
        ).all()

        return render_template(
            'carvia/configuracoes/tabelas_frete_carvia.html',
            combos=combos,
            grupos=grupos,
            ufs=UFS_BRASIL,
            grupo_filtro=grupo_filtro,
            uf_destino_filtro=uf_destino_filtro,
            uf_origem_filtro=uf_origem_filtro,
            tipo_carga_filtro=tipo_carga_filtro,
            busca_filtro=busca_filtro,
        )

    @bp.route('/api/tabelas-frete-carvia', methods=['POST']) # type: ignore
    @login_required
    def criar_tabela_carvia(): # type: ignore
        """Cria tabela de frete CarVia (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaTabelaFrete

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        # Validacoes
        uf_origem = (data.get('uf_origem') or '').strip().upper()
        uf_destino = (data.get('uf_destino') or '').strip().upper()
        nome_tabela = (data.get('nome_tabela') or '').strip().upper()
        tipo_carga = (data.get('tipo_carga') or '').strip().upper()
        modalidade = (data.get('modalidade') or '').strip().upper()

        if not all([uf_origem, uf_destino, nome_tabela, tipo_carga, modalidade]):
            return jsonify({'erro': 'Campos obrigatorios: UF origem, UF destino, '
                           'nome tabela, tipo carga, modalidade.'}), 400

        if tipo_carga not in ('DIRETA', 'FRACIONADA'):
            return jsonify({'erro': 'Tipo carga deve ser DIRETA ou FRACIONADA.'}), 400

        try:
            tabela = CarviaTabelaFrete(
                uf_origem=uf_origem,
                uf_destino=uf_destino,
                nome_tabela=nome_tabela,
                tipo_carga=tipo_carga,
                modalidade=modalidade,
                grupo_cliente_id=data.get('grupo_cliente_id') or None,
                valor_kg=data.get('valor_kg'),
                frete_minimo_peso=data.get('frete_minimo_peso'),
                percentual_valor=data.get('percentual_valor'),
                frete_minimo_valor=data.get('frete_minimo_valor'),
                percentual_gris=data.get('percentual_gris'),
                percentual_adv=data.get('percentual_adv'),
                percentual_rca=data.get('percentual_rca'),
                pedagio_por_100kg=data.get('pedagio_por_100kg'),
                valor_despacho=data.get('valor_despacho'),
                valor_cte=data.get('valor_cte'),
                valor_tas=data.get('valor_tas'),
                icms_incluso=data.get('icms_incluso', False),
                gris_minimo=data.get('gris_minimo', 0),
                adv_minimo=data.get('adv_minimo', 0),
                icms_proprio=data.get('icms_proprio'),
                criado_em=agora_utc_naive(),
                criado_por=current_user.email,
            )
            db.session.add(tabela)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': tabela.id,
                'mensagem': f'Tabela "{nome_tabela}" criada.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar tabela CarVia: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/tabelas-frete-carvia/<int:tid>', methods=['PUT']) # type: ignore
    @login_required
    def atualizar_tabela_carvia(tid): # type: ignore
        """Atualiza tabela de frete CarVia (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaTabelaFrete

        tabela = db.session.get(CarviaTabelaFrete, tid)
        if not tabela:
            return jsonify({'erro': 'Tabela nao encontrada.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            campos_str = ['uf_origem', 'uf_destino', 'nome_tabela', 'tipo_carga', 'modalidade']
            for campo in campos_str:
                if campo in data:
                    val = (data[campo] or '').strip().upper()
                    if not val:
                        return jsonify({'erro': f'{campo} e obrigatorio.'}), 400
                    setattr(tabela, campo, val)

            if 'tipo_carga' in data and tabela.tipo_carga not in ('DIRETA', 'FRACIONADA'):
                return jsonify({'erro': 'Tipo carga deve ser DIRETA ou FRACIONADA.'}), 400

            campos_num = [
                'valor_kg', 'frete_minimo_peso', 'percentual_valor', 'frete_minimo_valor',
                'percentual_gris', 'percentual_adv', 'percentual_rca', 'pedagio_por_100kg',
                'valor_despacho', 'valor_cte', 'valor_tas', 'gris_minimo', 'adv_minimo',
                'icms_proprio',
            ]
            for campo in campos_num:
                if campo in data:
                    setattr(tabela, campo, data[campo])

            if 'grupo_cliente_id' in data:
                tabela.grupo_cliente_id = data['grupo_cliente_id'] or None

            if 'icms_incluso' in data:
                tabela.icms_incluso = data['icms_incluso']

            if 'ativo' in data:
                tabela.ativo = data['ativo']

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'id': tabela.id,
                'mensagem': f'Tabela "{tabela.nome_tabela}" atualizada.',
            })

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar tabela #%s: %s", tid, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/tabelas-frete-carvia/<int:tid>', methods=['DELETE']) # type: ignore
    @login_required
    def desativar_tabela_carvia(tid): # type: ignore
        """Desativa tabela de frete CarVia.

        W7 (Sprint 2): checa referencias ativas em CarviaCotacao e
        CarviaCidadeAtendida. Nao bloqueia (soft-delete e reversivel),
        mas alerta sobre o impacto.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import (
            CarviaTabelaFrete, CarviaCotacao, CarviaCidadeAtendida,
        )

        tabela = db.session.get(CarviaTabelaFrete, tid)
        if not tabela:
            return jsonify({'erro': 'Tabela nao encontrada.'}), 404

        # W7: Verificar referencias ativas
        refs_cotacoes = CarviaCotacao.query.filter_by(
            tabela_carvia_id=tid,
        ).filter(
            CarviaCotacao.status.notin_(['CANCELADO', 'RECUSADO']),
        ).count()

        refs_cidades = CarviaCidadeAtendida.query.filter_by(
            nome_tabela=tabela.nome_tabela,
            ativo=True,
        ).count()

        try:
            tabela.ativo = False
            db.session.commit()

            mensagem = f'Tabela "{tabela.nome_tabela}" desativada.'
            avisos = []
            if refs_cotacoes > 0:
                avisos.append(f'{refs_cotacoes} cotacao(oes) ativa(s)')
            if refs_cidades > 0:
                avisos.append(f'{refs_cidades} cidade(s) atendida(s) ativa(s)')
            if avisos:
                mensagem += f' AVISO: ainda referenciada por {", ".join(avisos)}.'

            return jsonify({
                'sucesso': True,
                'mensagem': mensagem,
                'refs_cotacoes': refs_cotacoes,
                'refs_cidades': refs_cidades,
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao desativar tabela #%s: %s", tid, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # =================================================================
    # APIS COMBINACAO (listagem agrupada)
    # =================================================================

    @bp.route('/api/tabelas-frete-carvia/nomes-tabela') # type: ignore
    @login_required
    def api_nomes_tabela(): # type: ignore
        """Retorna nomes de tabela disponiveis de CarviaCidadeAtendida"""
        from app.carvia.models import CarviaCidadeAtendida

        uf_origem = request.args.get('uf_origem', '').strip().upper()
        uf_destino = request.args.get('uf_destino', '').strip().upper()

        if not uf_origem or not uf_destino:
            return jsonify({'nomes': []})

        nomes = db.session.query(
            CarviaCidadeAtendida.nome_tabela
        ).filter(
            CarviaCidadeAtendida.uf_origem == uf_origem,
            CarviaCidadeAtendida.uf_destino == uf_destino,
            CarviaCidadeAtendida.ativo == True,  # noqa: E712
        ).distinct().order_by(
            CarviaCidadeAtendida.nome_tabela
        ).all()

        return jsonify({'nomes': [n[0] for n in nomes]})

    @bp.route('/api/tabelas-frete-carvia/combinacao') # type: ignore
    @login_required
    def api_combinacao(): # type: ignore
        """Retorna dados de preco para uma combinacao + grupo"""
        from app.carvia.models import (
            CarviaTabelaFrete, CarviaPrecoCategoriaMoto, CarviaCategoriaMoto,
        )

        nome_tabela = request.args.get('nome_tabela', '').strip().upper()
        uf_origem = request.args.get('uf_origem', '').strip().upper()
        uf_destino = request.args.get('uf_destino', '').strip().upper()
        tipo_carga = request.args.get('tipo_carga', '').strip().upper()
        grupo_id_str = request.args.get('grupo_cliente_id', '')
        grupo_id = int(grupo_id_str) if grupo_id_str else None

        if not all([nome_tabela, uf_origem, uf_destino, tipo_carga]):
            return jsonify({'erro': 'Parametros obrigatorios faltando.'}), 400

        base_filter = [
            CarviaTabelaFrete.nome_tabela == nome_tabela,
            CarviaTabelaFrete.uf_origem == uf_origem,
            CarviaTabelaFrete.uf_destino == uf_destino,
            CarviaTabelaFrete.tipo_carga == tipo_carga,
            CarviaTabelaFrete.ativo == True,  # noqa: E712
        ]
        if grupo_id:
            base_filter.append(CarviaTabelaFrete.grupo_cliente_id == grupo_id)
        else:
            base_filter.append(CarviaTabelaFrete.grupo_cliente_id.is_(None))

        if tipo_carga == 'FRACIONADA':
            # Buscar registro FRETE PESO
            tab = CarviaTabelaFrete.query.filter(
                *base_filter,
                CarviaTabelaFrete.modalidade == 'FRETE PESO',
            ).first()

            frete_peso = None
            frete_moto = []

            if tab:
                campos = [
                    'id', 'valor_kg', 'frete_minimo_peso', 'percentual_valor',
                    'frete_minimo_valor', 'percentual_gris', 'gris_minimo',
                    'percentual_adv', 'adv_minimo', 'percentual_rca',
                    'pedagio_por_100kg', 'valor_despacho', 'valor_cte',
                    'valor_tas', 'icms_incluso', 'icms_proprio',
                ]
                frete_peso = {c: getattr(tab, c) for c in campos}

                # Precos moto vinculados a este registro
                precos = CarviaPrecoCategoriaMoto.query.filter_by(
                    tabela_frete_id=tab.id, ativo=True,
                ).all()
                for p in precos:
                    frete_moto.append({
                        'id': p.id,
                        'categoria_id': p.categoria_moto_id,
                        'categoria_nome': p.categoria.nome if p.categoria else '?',
                        'valor_unitario': float(p.valor_unitario) if p.valor_unitario else None,
                    })

            # Todas as categorias ativas (para mostrar campos vazios)
            categorias = CarviaCategoriaMoto.query.filter_by(
                ativo=True
            ).order_by(CarviaCategoriaMoto.ordem, CarviaCategoriaMoto.nome).all()
            todas_categorias = [{'id': c.id, 'nome': c.nome} for c in categorias]

            return jsonify({
                'frete_peso': frete_peso,
                'frete_moto': frete_moto,
                'todas_categorias': todas_categorias,
            })

        else:  # DIRETA
            from app.veiculos.models import Veiculo

            veiculos_db = Veiculo.query.order_by(Veiculo.nome).all()
            resultado = []

            for v in veiculos_db:
                tab = CarviaTabelaFrete.query.filter(
                    *base_filter,
                    CarviaTabelaFrete.modalidade == v.nome,
                ).first()

                resultado.append({
                    'nome': v.nome,
                    'id': tab.id if tab else None,
                    'frete_minimo_valor': float(tab.frete_minimo_valor)
                        if tab and tab.frete_minimo_valor else None,
                    'icms_incluso': tab.icms_incluso if tab else False,
                })

            return jsonify({'veiculos': resultado})

    @bp.route('/api/tabelas-frete-carvia/salvar-combinacao', methods=['POST']) # type: ignore
    @login_required
    def api_salvar_combinacao(): # type: ignore
        """Salva (upsert) combinacao completa de precos"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import (
            CarviaTabelaFrete, CarviaPrecoCategoriaMoto,
        )

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        nome_tabela = (data.get('nome_tabela') or '').strip().upper()
        uf_origem = (data.get('uf_origem') or '').strip().upper()
        uf_destino = (data.get('uf_destino') or '').strip().upper()
        tipo_carga = (data.get('tipo_carga') or '').strip().upper()
        grupo_id = data.get('grupo_cliente_id') or None

        if not all([nome_tabela, uf_origem, uf_destino, tipo_carga]):
            return jsonify({'erro': 'Campos de identificacao obrigatorios.'}), 400

        if tipo_carga not in ('DIRETA', 'FRACIONADA'):
            return jsonify({'erro': 'Tipo carga invalido.'}), 400

        try:
            base_kw = dict(
                nome_tabela=nome_tabela, uf_origem=uf_origem,
                uf_destino=uf_destino, tipo_carga=tipo_carga,
            )
            grupo_filter = (
                CarviaTabelaFrete.grupo_cliente_id == grupo_id
                if grupo_id
                else CarviaTabelaFrete.grupo_cliente_id.is_(None)
            )

            if tipo_carga == 'FRACIONADA':
                frete_peso_data = data.get('frete_peso', {})
                frete_moto_data = data.get('frete_moto', [])

                # Upsert FRETE PESO
                tab = CarviaTabelaFrete.query.filter_by(
                    **base_kw, modalidade='FRETE PESO', ativo=True,
                ).filter(grupo_filter).first()

                campos_num = [
                    'valor_kg', 'frete_minimo_peso', 'percentual_valor',
                    'frete_minimo_valor', 'percentual_gris', 'gris_minimo',
                    'percentual_adv', 'adv_minimo', 'percentual_rca',
                    'pedagio_por_100kg', 'valor_despacho', 'valor_cte',
                    'valor_tas', 'icms_proprio',
                ]

                # Verificar se ha algum valor real de frete peso
                tem_frete_peso = any(
                    frete_peso_data.get(c) is not None
                    for c in campos_num
                )

                if tab:
                    # Update: so sobrescrever campos que tem valor
                    # (preserva dados existentes quando campo vem null)
                    for c in campos_num:
                        if c in frete_peso_data and frete_peso_data[c] is not None:
                            setattr(tab, c, frete_peso_data[c])
                    if 'icms_incluso' in frete_peso_data:
                        tab.icms_incluso = frete_peso_data['icms_incluso']
                elif tem_frete_peso or frete_moto_data:
                    # Create: precisa do registro para vincular precos moto
                    tab = CarviaTabelaFrete(
                        **base_kw, modalidade='FRETE PESO',
                        grupo_cliente_id=grupo_id,
                        criado_em=agora_utc_naive(),
                        criado_por=current_user.email,
                    )
                    for c in campos_num:
                        if c in frete_peso_data and frete_peso_data[c] is not None:
                            setattr(tab, c, frete_peso_data[c])
                    if 'icms_incluso' in frete_peso_data:
                        tab.icms_incluso = frete_peso_data['icms_incluso']
                    db.session.add(tab)

                if tab:
                    db.session.flush()  # Garante tab.id

                # Upsert precos moto — update/insert/soft-delete
                if tab:
                    existing = {
                        p.categoria_moto_id: p
                        for p in CarviaPrecoCategoriaMoto.query.filter_by(
                            tabela_frete_id=tab.id
                        ).all()
                    }
                    received_cat_ids = set()

                    for pm in (frete_moto_data or []):
                        cat_id = pm.get('categoria_moto_id')
                        valor = pm.get('valor_unitario')
                        if cat_id is not None and valor is not None:
                            cat_id = int(cat_id)
                            received_cat_ids.add(cat_id)
                            if cat_id in existing:
                                existing[cat_id].valor_unitario = float(valor)
                                existing[cat_id].ativo = True
                            else:
                                preco = CarviaPrecoCategoriaMoto(
                                    tabela_frete_id=tab.id,
                                    categoria_moto_id=cat_id,
                                    valor_unitario=float(valor),
                                    ativo=True,
                                    criado_em=agora_utc_naive(),
                                    criado_por=current_user.email,
                                )
                                db.session.add(preco)

                    # Soft-delete categorias removidas pelo usuario
                    if frete_moto_data:
                        for cat_id, preco in existing.items():
                            if cat_id not in received_cat_ids and preco.ativo:
                                preco.ativo = False

            else:  # DIRETA
                veiculos_data = data.get('veiculos', [])

                for vd in veiculos_data:
                    modalidade = vd.get('nome', '').strip()
                    if not modalidade:
                        continue

                    tab = CarviaTabelaFrete.query.filter_by(
                        **base_kw, modalidade=modalidade,
                    ).filter(grupo_filter).first()

                    frete_min = vd.get('frete_minimo_valor')
                    icms = vd.get('icms_incluso', False)

                    if tab:
                        tab.frete_minimo_valor = frete_min
                        tab.icms_incluso = icms
                    elif frete_min:
                        tab = CarviaTabelaFrete(
                            **base_kw, modalidade=modalidade,
                            grupo_cliente_id=grupo_id,
                            frete_minimo_valor=frete_min,
                            icms_incluso=icms,
                            criado_em=agora_utc_naive(),
                            criado_por=current_user.email,
                        )
                        db.session.add(tab)

            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Combinacao salva.'})

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao salvar combinacao: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/tabelas-frete-carvia/desativar-combinacao', methods=['POST']) # type: ignore
    @login_required
    def api_desativar_combinacao(): # type: ignore
        """Desativa TODOS os registros de uma combinacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaTabelaFrete

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        nome_tabela = (data.get('nome_tabela') or '').strip().upper()
        uf_origem = (data.get('uf_origem') or '').strip().upper()
        uf_destino = (data.get('uf_destino') or '').strip().upper()
        tipo_carga = (data.get('tipo_carga') or '').strip().upper()

        if not all([nome_tabela, uf_origem, uf_destino, tipo_carga]):
            return jsonify({'erro': 'Parametros obrigatorios faltando.'}), 400

        try:
            count = CarviaTabelaFrete.query.filter_by(
                nome_tabela=nome_tabela, uf_origem=uf_origem,
                uf_destino=uf_destino, tipo_carga=tipo_carga,
            ).update({'ativo': False})
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'mensagem': f'{count} registro(s) desativados.',
            })

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao desativar combinacao: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/veiculos-lista') # type: ignore
    @login_required
    def api_veiculos_lista(): # type: ignore
        """Lista veiculos cadastrados para modalidades DIRETA"""
        from app.veiculos.models import Veiculo

        veiculos = Veiculo.query.order_by(Veiculo.nome).all()
        return jsonify({
            'veiculos': [{'id': v.id, 'nome': v.nome} for v in veiculos]
        })

    # =================================================================
    # CIDADES ATENDIDAS CARVIA
    # =================================================================

    @bp.route('/configuracoes/cidades-atendidas') # type: ignore
    @login_required
    def listar_cidades_carvia(): # type: ignore
        """Lista cidades atendidas CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaCidadeAtendida

        uf_filtro = request.args.get('uf', '').strip().upper()
        uf_origem_filtro = request.args.get('uf_origem', '').strip().upper()
        tabela_filtro = request.args.get('tabela', '').strip()
        busca_filtro = request.args.get('busca', '').strip()
        ativo_filtro = request.args.get('ativo', '')

        query = CarviaCidadeAtendida.query.order_by(
            CarviaCidadeAtendida.uf_destino.asc(),
            CarviaCidadeAtendida.nome_cidade.asc(),
        )

        if uf_filtro:
            query = query.filter(CarviaCidadeAtendida.uf_destino == uf_filtro)

        if uf_origem_filtro:
            query = query.filter(CarviaCidadeAtendida.uf_origem == uf_origem_filtro)

        if tabela_filtro:
            query = query.filter(
                CarviaCidadeAtendida.nome_tabela.ilike(f'%{tabela_filtro}%')
            )

        if busca_filtro:
            query = query.filter(
                CarviaCidadeAtendida.nome_cidade.ilike(f'%{busca_filtro}%')
            )

        if ativo_filtro == '1':
            query = query.filter(CarviaCidadeAtendida.ativo == True)  # noqa: E712
        elif ativo_filtro == '0':
            query = query.filter(CarviaCidadeAtendida.ativo == False)  # noqa: E712

        cidades = query.all()

        return render_template(
            'carvia/configuracoes/cidades_atendidas_carvia.html',
            cidades=cidades,
            ufs=UFS_BRASIL,
            uf_filtro=uf_filtro,
            uf_origem_filtro=uf_origem_filtro,
            tabela_filtro=tabela_filtro,
            busca_filtro=busca_filtro,
            ativo_filtro=ativo_filtro,
        )

    @bp.route('/api/cidades-atendidas-carvia', methods=['POST']) # type: ignore
    @login_required
    def criar_cidade_carvia(): # type: ignore
        """Cria cidade atendida CarVia (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCidadeAtendida

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        codigo_ibge = (data.get('codigo_ibge') or '').strip()
        nome_cidade = (data.get('nome_cidade') or '').strip()
        uf_origem = (data.get('uf_origem') or '').strip().upper()
        uf_destino = (data.get('uf_destino') or data.get('uf') or '').strip().upper()
        nome_tabela = (data.get('nome_tabela') or '').strip().upper()

        if not all([codigo_ibge, nome_cidade, uf_origem, uf_destino, nome_tabela]):
            return jsonify({'erro': 'Campos obrigatorios: codigo IBGE, '
                           'cidade, UF origem, UF destino, nome tabela.'}), 400

        # Verificar duplicata
        existente = CarviaCidadeAtendida.query.filter_by(
            codigo_ibge=codigo_ibge, nome_tabela=nome_tabela, uf_origem=uf_origem
        ).first()
        if existente:
            return jsonify({'erro': f'Cidade {nome_cidade} ja vinculada '
                           f'a tabela {nome_tabela} (origem {uf_origem}).'}), 409

        try:
            cidade = CarviaCidadeAtendida(
                codigo_ibge=codigo_ibge,
                nome_cidade=nome_cidade,
                uf_origem=uf_origem,
                uf_destino=uf_destino,
                nome_tabela=nome_tabela,
                lead_time=data.get('lead_time'),
                criado_em=agora_utc_naive(),
                criado_por=current_user.email,
            )
            db.session.add(cidade)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': cidade.id,
                'mensagem': f'{nome_cidade}/{uf_destino} vinculada a {nome_tabela}.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar cidade atendida: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cidades-atendidas-carvia/<int:cid>', methods=['PUT']) # type: ignore
    @login_required
    def atualizar_cidade_carvia(cid): # type: ignore
        """Atualiza cidade atendida CarVia (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCidadeAtendida

        cidade = db.session.get(CarviaCidadeAtendida, cid)
        if not cidade:
            return jsonify({'erro': 'Cidade nao encontrada.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            if 'nome_tabela' in data:
                cidade.nome_tabela = (data['nome_tabela'] or '').strip().upper()
            if 'lead_time' in data:
                cidade.lead_time = data['lead_time']
            if 'ativo' in data:
                cidade.ativo = data['ativo']

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'id': cidade.id,
                'mensagem': f'{cidade.nome_cidade} atualizada.',
            })

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar cidade #%s: %s", cid, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cidades-atendidas-carvia/<int:cid>', methods=['DELETE']) # type: ignore
    @login_required
    def desativar_cidade_carvia(cid): # type: ignore
        """Desativa cidade atendida CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCidadeAtendida

        cidade = db.session.get(CarviaCidadeAtendida, cid)
        if not cidade:
            return jsonify({'erro': 'Cidade nao encontrada.'}), 404

        try:
            cidade.ativo = False
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'mensagem': f'{cidade.nome_cidade} desativada.',
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao desativar cidade #%s: %s", cid, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

