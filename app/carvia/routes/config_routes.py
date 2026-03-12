"""
Rotas de Configuracoes CarVia — CRUD modelos moto + empresas cubagem
"""

import logging
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_config_routes(bp):

    # ==================== MODELOS MOTO ====================

    @bp.route('/configuracoes/modelos-moto')
    @login_required
    def listar_modelos_moto():
        """Lista modelos de moto cadastrados"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaModeloMoto
        modelos = CarviaModeloMoto.query.order_by(
            CarviaModeloMoto.nome.asc()
        ).all()

        return render_template(
            'carvia/configuracoes/modelos_moto.html',
            modelos=modelos,
        )

    @bp.route('/api/modelos-moto', methods=['POST'])
    @login_required
    def criar_modelo_moto():
        """Cria novo modelo de moto (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaModeloMoto
        from app.utils.timezone import agora_utc_naive

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        nome = (data.get('nome') or '').strip()
        if not nome:
            return jsonify({'erro': 'Nome e obrigatorio.'}), 400

        # Verificar duplicata
        existente = CarviaModeloMoto.query.filter_by(nome=nome).first()
        if existente:
            return jsonify({'erro': f'Modelo "{nome}" ja existe.'}), 409

        try:
            modelo = CarviaModeloMoto(
                nome=nome,
                comprimento=data.get('comprimento', 0),
                largura=data.get('largura', 0),
                altura=data.get('altura', 0),
                peso_medio=data.get('peso_medio'),
                cubagem_minima=data.get('cubagem_minima', 300),
                regex_pattern=data.get('regex_pattern'),
                criado_em=agora_utc_naive(),
                criado_por=current_user.email,
            )
            db.session.add(modelo)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': modelo.id,
                'nome': modelo.nome,
                'mensagem': f'Modelo "{modelo.nome}" criado com sucesso.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar modelo moto: {e}")
            return jsonify({'erro': f'Erro ao criar modelo: {e}'}), 500

    @bp.route('/api/modelos-moto/<int:modelo_id>', methods=['PUT'])
    @login_required
    def atualizar_modelo_moto(modelo_id):
        """Atualiza modelo de moto existente (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaModeloMoto

        modelo = db.session.get(CarviaModeloMoto, modelo_id)
        if not modelo:
            return jsonify({'erro': 'Modelo nao encontrado.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            if 'nome' in data:
                nome = (data['nome'] or '').strip()
                if not nome:
                    return jsonify({'erro': 'Nome e obrigatorio.'}), 400
                # Verificar duplicata (excluindo o proprio)
                existente = CarviaModeloMoto.query.filter(
                    CarviaModeloMoto.nome == nome,
                    CarviaModeloMoto.id != modelo_id,
                ).first()
                if existente:
                    return jsonify({'erro': f'Modelo "{nome}" ja existe.'}), 409
                modelo.nome = nome

            if 'comprimento' in data:
                modelo.comprimento = data['comprimento']
            if 'largura' in data:
                modelo.largura = data['largura']
            if 'altura' in data:
                modelo.altura = data['altura']
            if 'peso_medio' in data:
                modelo.peso_medio = data['peso_medio']
            if 'cubagem_minima' in data:
                modelo.cubagem_minima = data['cubagem_minima']
            if 'regex_pattern' in data:
                modelo.regex_pattern = data['regex_pattern']
            if 'ativo' in data:
                modelo.ativo = data['ativo']

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': modelo.id,
                'nome': modelo.nome,
                'mensagem': f'Modelo "{modelo.nome}" atualizado com sucesso.',
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar modelo moto #{modelo_id}: {e}")
            return jsonify({'erro': f'Erro ao atualizar modelo: {e}'}), 500

    @bp.route('/api/modelos-moto/<int:modelo_id>', methods=['DELETE'])
    @login_required
    def deletar_modelo_moto(modelo_id):
        """Soft-delete modelo de moto (ativo=False)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaModeloMoto

        modelo = db.session.get(CarviaModeloMoto, modelo_id)
        if not modelo:
            return jsonify({'erro': 'Modelo nao encontrado.'}), 404

        try:
            modelo.ativo = False
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'mensagem': f'Modelo "{modelo.nome}" desativado.',
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desativar modelo moto #{modelo_id}: {e}")
            return jsonify({'erro': f'Erro ao desativar modelo: {e}'}), 500

    # ==================== EMPRESAS CUBAGEM ====================

    @bp.route('/configuracoes/empresas-cubagem')
    @login_required
    def listar_empresas_cubagem():
        """Lista empresas com configuracao de cubagem"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaEmpresaCubagem
        empresas = CarviaEmpresaCubagem.query.order_by(
            CarviaEmpresaCubagem.nome_empresa.asc()
        ).all()

        return render_template(
            'carvia/configuracoes/empresas_cubagem.html',
            empresas=empresas,
        )

    @bp.route('/api/empresas-cubagem', methods=['POST'])
    @login_required
    def criar_empresa_cubagem():
        """Cria nova empresa cubagem (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaEmpresaCubagem
        from app.utils.timezone import agora_utc_naive

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        cnpj_empresa = (data.get('cnpj_empresa') or '').strip()
        nome_empresa = (data.get('nome_empresa') or '').strip()

        if not cnpj_empresa:
            return jsonify({'erro': 'CNPJ e obrigatorio.'}), 400
        if not nome_empresa:
            return jsonify({'erro': 'Nome da empresa e obrigatorio.'}), 400

        # Verificar duplicata por CNPJ
        existente = CarviaEmpresaCubagem.query.filter_by(
            cnpj_empresa=cnpj_empresa
        ).first()
        if existente:
            return jsonify({
                'erro': f'Empresa com CNPJ {cnpj_empresa} ja cadastrada.'
            }), 409

        try:
            empresa = CarviaEmpresaCubagem(
                cnpj_empresa=cnpj_empresa,
                nome_empresa=nome_empresa,
                considerar_cubagem=data.get('considerar_cubagem', False),
                criado_em=agora_utc_naive(),
                criado_por=current_user.email,
            )
            db.session.add(empresa)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': empresa.id,
                'cnpj_empresa': empresa.cnpj_empresa,
                'nome_empresa': empresa.nome_empresa,
                'mensagem': f'Empresa "{empresa.nome_empresa}" criada com sucesso.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar empresa cubagem: {e}")
            return jsonify({'erro': f'Erro ao criar empresa: {e}'}), 500

    @bp.route('/api/empresas-cubagem/<int:empresa_id>', methods=['PUT'])
    @login_required
    def atualizar_empresa_cubagem(empresa_id):
        """Atualiza empresa cubagem existente (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaEmpresaCubagem

        empresa = db.session.get(CarviaEmpresaCubagem, empresa_id)
        if not empresa:
            return jsonify({'erro': 'Empresa nao encontrada.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            if 'cnpj_empresa' in data:
                cnpj = (data['cnpj_empresa'] or '').strip()
                if not cnpj:
                    return jsonify({'erro': 'CNPJ e obrigatorio.'}), 400
                # Verificar duplicata (excluindo a propria)
                existente = CarviaEmpresaCubagem.query.filter(
                    CarviaEmpresaCubagem.cnpj_empresa == cnpj,
                    CarviaEmpresaCubagem.id != empresa_id,
                ).first()
                if existente:
                    return jsonify({
                        'erro': f'Empresa com CNPJ {cnpj} ja cadastrada.'
                    }), 409
                empresa.cnpj_empresa = cnpj

            if 'nome_empresa' in data:
                nome = (data['nome_empresa'] or '').strip()
                if not nome:
                    return jsonify({'erro': 'Nome da empresa e obrigatorio.'}), 400
                empresa.nome_empresa = nome

            if 'considerar_cubagem' in data:
                empresa.considerar_cubagem = data['considerar_cubagem']

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': empresa.id,
                'cnpj_empresa': empresa.cnpj_empresa,
                'nome_empresa': empresa.nome_empresa,
                'mensagem': f'Empresa "{empresa.nome_empresa}" atualizada com sucesso.',
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar empresa cubagem #{empresa_id}: {e}")
            return jsonify({'erro': f'Erro ao atualizar empresa: {e}'}), 500

    @bp.route('/api/empresas-cubagem/<int:empresa_id>', methods=['DELETE'])
    @login_required
    def deletar_empresa_cubagem(empresa_id):
        """Deleta empresa cubagem"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaEmpresaCubagem

        empresa = db.session.get(CarviaEmpresaCubagem, empresa_id)
        if not empresa:
            return jsonify({'erro': 'Empresa nao encontrada.'}), 404

        try:
            nome = empresa.nome_empresa
            db.session.delete(empresa)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'mensagem': f'Empresa "{nome}" removida.',
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao deletar empresa cubagem #{empresa_id}: {e}")
            return jsonify({'erro': f'Erro ao deletar empresa: {e}'}), 500

    # ==================== TRANSPORTADORAS ATIVAS ====================

    @bp.route('/api/transportadoras-ativas')
    @login_required
    def listar_transportadoras_ativas():
        """Lista todas transportadoras ativas (para dropdown cotacao manual)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.transportadoras.models import Transportadora

        transportadoras = Transportadora.query.filter_by(
            ativo=True
        ).order_by(
            Transportadora.razao_social.asc()
        ).all()

        return jsonify([
            {
                'id': t.id,
                'nome': t.razao_social,
                'cnpj': t.cnpj,
            }
            for t in transportadoras
        ])
