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

    @bp.route('/configuracoes/grupos-cliente')
    @login_required
    def listar_grupos_cliente():
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

    @bp.route('/api/grupos-cliente', methods=['POST'])
    @login_required
    def criar_grupo_cliente():
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

    @bp.route('/api/grupos-cliente/<int:gid>', methods=['PUT'])
    @login_required
    def atualizar_grupo_cliente(gid):
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

    @bp.route('/api/grupos-cliente/<int:gid>', methods=['DELETE'])
    @login_required
    def desativar_grupo_cliente(gid):
        """Desativa grupo de cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaGrupoCliente

        grupo = db.session.get(CarviaGrupoCliente, gid)
        if not grupo:
            return jsonify({'erro': 'Grupo nao encontrado.'}), 404

        try:
            grupo.ativo = False
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'mensagem': f'Grupo "{grupo.nome}" desativado.',
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao desativar grupo #%s: %s", gid, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # --- Membros do grupo ---

    @bp.route('/api/grupos-cliente/<int:gid>/membros', methods=['POST'])
    @login_required
    def adicionar_membro_grupo(gid):
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

    @bp.route('/api/grupos-cliente/<int:gid>/membros/<int:mid>', methods=['DELETE'])
    @login_required
    def remover_membro_grupo(gid, mid):
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

    @bp.route('/configuracoes/tabelas-frete')
    @login_required
    def listar_tabelas_carvia():
        """Lista tabelas de frete CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaTabelaFrete, CarviaGrupoCliente

        uf_filtro = request.args.get('uf', '')
        tipo_filtro = request.args.get('tipo_carga', '')

        query = CarviaTabelaFrete.query.order_by(
            CarviaTabelaFrete.uf_origem.asc(),
            CarviaTabelaFrete.uf_destino.asc(),
            CarviaTabelaFrete.nome_tabela.asc(),
        )

        if uf_filtro:
            query = query.filter(
                db.or_(
                    CarviaTabelaFrete.uf_origem == uf_filtro,
                    CarviaTabelaFrete.uf_destino == uf_filtro,
                )
            )

        if tipo_filtro:
            query = query.filter(CarviaTabelaFrete.tipo_carga == tipo_filtro)

        tabelas = query.all()
        grupos = CarviaGrupoCliente.query.filter_by(ativo=True).order_by(
            CarviaGrupoCliente.nome.asc()
        ).all()

        return render_template(
            'carvia/configuracoes/tabelas_frete_carvia.html',
            tabelas=tabelas,
            grupos=grupos,
            ufs=UFS_BRASIL,
            uf_filtro=uf_filtro,
            tipo_filtro=tipo_filtro,
        )

    @bp.route('/api/tabelas-frete-carvia', methods=['POST'])
    @login_required
    def criar_tabela_carvia():
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

    @bp.route('/api/tabelas-frete-carvia/<int:tid>', methods=['PUT'])
    @login_required
    def atualizar_tabela_carvia(tid):
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

    @bp.route('/api/tabelas-frete-carvia/<int:tid>', methods=['DELETE'])
    @login_required
    def desativar_tabela_carvia(tid):
        """Desativa tabela de frete CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaTabelaFrete

        tabela = db.session.get(CarviaTabelaFrete, tid)
        if not tabela:
            return jsonify({'erro': 'Tabela nao encontrada.'}), 404

        try:
            tabela.ativo = False
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'mensagem': f'Tabela "{tabela.nome_tabela}" desativada.',
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao desativar tabela #%s: %s", tid, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # =================================================================
    # CIDADES ATENDIDAS CARVIA
    # =================================================================

    @bp.route('/configuracoes/cidades-atendidas')
    @login_required
    def listar_cidades_carvia():
        """Lista cidades atendidas CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaCidadeAtendida

        uf_filtro = request.args.get('uf', '')

        query = CarviaCidadeAtendida.query.order_by(
            CarviaCidadeAtendida.uf.asc(),
            CarviaCidadeAtendida.nome_cidade.asc(),
        )

        if uf_filtro:
            query = query.filter(CarviaCidadeAtendida.uf == uf_filtro)

        cidades = query.all()

        return render_template(
            'carvia/configuracoes/cidades_atendidas_carvia.html',
            cidades=cidades,
            ufs=UFS_BRASIL,
            uf_filtro=uf_filtro,
        )

    @bp.route('/api/cidades-atendidas-carvia', methods=['POST'])
    @login_required
    def criar_cidade_carvia():
        """Cria cidade atendida CarVia (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCidadeAtendida

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        codigo_ibge = (data.get('codigo_ibge') or '').strip()
        nome_cidade = (data.get('nome_cidade') or '').strip()
        uf = (data.get('uf') or '').strip().upper()
        nome_tabela = (data.get('nome_tabela') or '').strip().upper()

        if not all([codigo_ibge, nome_cidade, uf, nome_tabela]):
            return jsonify({'erro': 'Campos obrigatorios: codigo IBGE, '
                           'cidade, UF, nome tabela.'}), 400

        # Verificar duplicata
        existente = CarviaCidadeAtendida.query.filter_by(
            codigo_ibge=codigo_ibge, nome_tabela=nome_tabela
        ).first()
        if existente:
            return jsonify({'erro': f'Cidade {nome_cidade} ja vinculada '
                           f'a tabela {nome_tabela}.'}), 409

        try:
            cidade = CarviaCidadeAtendida(
                codigo_ibge=codigo_ibge,
                nome_cidade=nome_cidade,
                uf=uf,
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
                'mensagem': f'{nome_cidade}/{uf} vinculada a {nome_tabela}.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar cidade atendida: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cidades-atendidas-carvia/<int:cid>', methods=['PUT'])
    @login_required
    def atualizar_cidade_carvia(cid):
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

    @bp.route('/api/cidades-atendidas-carvia/<int:cid>', methods=['DELETE'])
    @login_required
    def desativar_cidade_carvia(cid):
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
