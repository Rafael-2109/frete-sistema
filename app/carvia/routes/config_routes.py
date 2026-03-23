"""
Rotas de Configuracoes CarVia — CRUD modelos moto + empresas cubagem + parametros globais
"""

import logging
import re
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def _auto_gerar_regex(nome: str) -> str:
    """Gera regex a partir do nome do modelo.

    Exemplos:
        "CG 160"  -> "(?i)cg\\s*160"
        "BOB"     -> "(?i)bob"
        "X12-10"  -> "(?i)x12[\\s\\-]*10"
    """
    if not nome or not nome.strip():
        return ''
    nome = nome.strip()
    # Escapar caracteres regex especiais (exceto espacos e hifens)
    partes = re.split(r'[\s\-]+', nome)
    regex_parts = [re.escape(p) for p in partes if p]
    return '(?i)' + r'[\s\-]*'.join(regex_parts)


def register_config_routes(bp):

    # ==================== MODELOS MOTO ====================

    @bp.route('/configuracoes/modelos-moto') # type: ignore
    @login_required
    def listar_modelos_moto(): # type: ignore
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

    @bp.route('/api/modelos-moto', methods=['POST']) # type: ignore
    @login_required
    def criar_modelo_moto(): # type: ignore
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
            regex_pattern = (data.get('regex_pattern') or '').strip()
            if not regex_pattern:
                regex_pattern = _auto_gerar_regex(nome)

            cat_id = data.get('categoria_moto_id')

            modelo = CarviaModeloMoto(
                nome=nome,
                comprimento=data.get('comprimento', 0),
                largura=data.get('largura', 0),
                altura=data.get('altura', 0),
                peso_medio=data.get('peso_medio'),
                cubagem_minima=data.get('cubagem_minima', 300),
                regex_pattern=regex_pattern or None,
                categoria_moto_id=int(cat_id) if cat_id else None,
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

    @bp.route('/api/modelos-moto/<int:modelo_id>', methods=['PUT']) # type: ignore
    @login_required
    def atualizar_modelo_moto(modelo_id): # type: ignore
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
                regex_val = (data['regex_pattern'] or '').strip()
                if not regex_val:
                    # Auto-gerar do nome atual (ou novo nome se editado)
                    regex_val = _auto_gerar_regex(modelo.nome)
                modelo.regex_pattern = regex_val or None
            if 'categoria_moto_id' in data:
                cat_id = data['categoria_moto_id']
                modelo.categoria_moto_id = int(cat_id) if cat_id else None
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

    @bp.route('/api/modelos-moto/<int:modelo_id>', methods=['DELETE']) # type: ignore
    @login_required
    def deletar_modelo_moto(modelo_id): # type: ignore
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

    @bp.route('/api/modelos-moto/testar-regex', methods=['POST']) # type: ignore
    @login_required
    def api_testar_regex_moto(): # type: ignore
        """Testa regex e/ou match por nome contra texto de produto."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        pattern = (data.get('regex', '') or '').strip()
        texto = (data.get('texto', '') or '').strip()
        nome = (data.get('nome', '') or '').strip()

        if not texto:
            return jsonify({'erro': 'Texto para teste e obrigatorio.'}), 400

        # 1. Testar regex
        if pattern:
            try:
                if re.search(pattern, texto):
                    return jsonify({
                        'sucesso': True,
                        'match': True,
                        'metodo': 'regex',
                        'mensagem': f'Match por regex: "{pattern}"',
                    })
            except re.error as e:
                return jsonify({
                    'sucesso': True,
                    'match': False,
                    'metodo': 'nenhum',
                    'mensagem': f'Regex invalido: {e}',
                })

        # 2. Testar match por nome (fallback do moto_recognition_service)
        if nome and nome.upper() in texto.upper():
            return jsonify({
                'sucesso': True,
                'match': True,
                'metodo': 'nome',
                'mensagem': f'Match por nome: "{nome}"',
            })

        return jsonify({
            'sucesso': True,
            'match': False,
            'metodo': 'nenhum',
            'mensagem': 'Nenhum match encontrado.',
        })

    # ==================== CATEGORIAS MOTO ====================

    @bp.route('/configuracoes/categorias-moto') # type: ignore
    @login_required
    def listar_categorias_moto(): # type: ignore
        """Lista categorias de moto cadastradas"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaCategoriaMoto
        categorias = CarviaCategoriaMoto.query.order_by(
            CarviaCategoriaMoto.ordem.asc(),
            CarviaCategoriaMoto.nome.asc(),
        ).all()

        return render_template(
            'carvia/configuracoes/categorias_moto.html',
            categorias=categorias,
        )

    @bp.route('/api/categorias-moto', methods=['POST']) # type: ignore
    @login_required
    def criar_categoria_moto(): # type: ignore
        """Cria nova categoria de moto (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCategoriaMoto
        from app.utils.timezone import agora_utc_naive

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        nome = (data.get('nome') or '').strip()
        if not nome:
            return jsonify({'erro': 'Nome e obrigatorio.'}), 400

        existente = CarviaCategoriaMoto.query.filter_by(nome=nome).first()
        if existente:
            return jsonify({'erro': f'Categoria "{nome}" ja existe.'}), 409

        try:
            categoria = CarviaCategoriaMoto(
                nome=nome,
                descricao=(data.get('descricao') or '').strip() or None,
                ordem=data.get('ordem', 0),
                criado_em=agora_utc_naive(),
                criado_por=current_user.email,
            )
            db.session.add(categoria)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': categoria.id,
                'nome': categoria.nome,
                'mensagem': f'Categoria "{categoria.nome}" criada com sucesso.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar categoria moto: %s", e)
            return jsonify({'erro': f'Erro ao criar categoria: {e}'}), 500

    @bp.route('/api/categorias-moto/<int:cat_id>', methods=['PUT']) # type: ignore
    @login_required
    def atualizar_categoria_moto(cat_id): # type: ignore
        """Atualiza categoria de moto (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCategoriaMoto

        categoria = db.session.get(CarviaCategoriaMoto, cat_id)
        if not categoria:
            return jsonify({'erro': 'Categoria nao encontrada.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            if 'nome' in data:
                nome = (data['nome'] or '').strip()
                if not nome:
                    return jsonify({'erro': 'Nome e obrigatorio.'}), 400
                existente = CarviaCategoriaMoto.query.filter(
                    CarviaCategoriaMoto.nome == nome,
                    CarviaCategoriaMoto.id != cat_id,
                ).first()
                if existente:
                    return jsonify({'erro': f'Categoria "{nome}" ja existe.'}), 409
                categoria.nome = nome

            if 'descricao' in data:
                categoria.descricao = (data['descricao'] or '').strip() or None
            if 'ordem' in data:
                categoria.ordem = data['ordem']
            if 'ativo' in data:
                categoria.ativo = data['ativo']

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': categoria.id,
                'nome': categoria.nome,
                'mensagem': f'Categoria "{categoria.nome}" atualizada.',
            })

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar categoria moto #%s: %s", cat_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/categorias-moto/<int:cat_id>', methods=['DELETE']) # type: ignore
    @login_required
    def desativar_categoria_moto(cat_id): # type: ignore
        """Soft-delete categoria de moto (ativo=False)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCategoriaMoto

        categoria = db.session.get(CarviaCategoriaMoto, cat_id)
        if not categoria:
            return jsonify({'erro': 'Categoria nao encontrada.'}), 404

        try:
            categoria.ativo = False
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'mensagem': f'Categoria "{categoria.nome}" desativada.',
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao desativar categoria moto #%s: %s", cat_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/categorias-moto-lista') # type: ignore
    @login_required
    def api_categorias_moto_lista(): # type: ignore
        """Lista categorias ativas (para dropdowns)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCategoriaMoto
        categorias = CarviaCategoriaMoto.query.filter_by(ativo=True).order_by(
            CarviaCategoriaMoto.ordem.asc(),
            CarviaCategoriaMoto.nome.asc(),
        ).all()

        return jsonify({
            'categorias': [
                {'id': c.id, 'nome': c.nome, 'descricao': c.descricao}
                for c in categorias
            ]
        })

    # ==================== PRECOS CATEGORIA MOTO (por Tabela) ====================

    @bp.route('/api/tabela-carvia/<int:tid>/precos-moto') # type: ignore
    @login_required
    def listar_precos_moto(tid): # type: ignore
        """Lista precos por categoria de uma tabela"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.carvia_tabela_service import CarviaTabelaService
        svc = CarviaTabelaService()
        precos = svc.buscar_precos_categoria(tid)
        return jsonify({'sucesso': True, 'precos': precos})

    @bp.route('/api/tabela-carvia/<int:tid>/precos-moto', methods=['POST']) # type: ignore
    @login_required
    def criar_preco_moto(tid): # type: ignore
        """Define preco para categoria em tabela"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaPrecoCategoriaMoto, CarviaTabelaFrete
        from app.utils.timezone import agora_utc_naive

        tabela = db.session.get(CarviaTabelaFrete, tid)
        if not tabela:
            return jsonify({'erro': 'Tabela nao encontrada.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        categoria_id = data.get('categoria_moto_id')
        valor_unitario = data.get('valor_unitario')

        if not categoria_id or valor_unitario is None:
            return jsonify({'erro': 'categoria_moto_id e valor_unitario obrigatorios.'}), 400

        try:
            valor = float(valor_unitario)
            if valor <= 0:
                return jsonify({'erro': 'Valor unitario deve ser positivo.'}), 400
        except (ValueError, TypeError):
            return jsonify({'erro': 'Valor unitario invalido.'}), 400

        # Verificar duplicata
        existente = CarviaPrecoCategoriaMoto.query.filter_by(
            tabela_frete_id=tid,
            categoria_moto_id=int(categoria_id),
        ).first()
        if existente:
            return jsonify({'erro': 'Ja existe preco para esta categoria nesta tabela.'}), 409

        try:
            preco = CarviaPrecoCategoriaMoto(
                tabela_frete_id=tid,
                categoria_moto_id=int(categoria_id),
                valor_unitario=valor,
                criado_em=agora_utc_naive(),
                criado_por=current_user.email,
            )
            db.session.add(preco)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': preco.id,
                'mensagem': 'Preco adicionado.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar preco moto: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/precos-moto/<int:preco_id>', methods=['PUT']) # type: ignore    
    @login_required
    def atualizar_preco_moto(preco_id): # type: ignore
        """Atualiza preco de categoria"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaPrecoCategoriaMoto

        preco = db.session.get(CarviaPrecoCategoriaMoto, preco_id)
        if not preco:
            return jsonify({'erro': 'Preco nao encontrado.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            if 'valor_unitario' in data:
                valor = float(data['valor_unitario'])
                if valor <= 0:
                    return jsonify({'erro': 'Valor deve ser positivo.'}), 400
                preco.valor_unitario = valor

            if 'ativo' in data:
                preco.ativo = data['ativo']

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'id': preco.id,
                'mensagem': 'Preco atualizado.',
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar preco moto #%s: %s", preco_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/precos-moto/<int:preco_id>', methods=['DELETE']) # type: ignore
    @login_required
    def remover_preco_moto(preco_id): # type: ignore
        """Remove preco de categoria (soft-delete)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaPrecoCategoriaMoto

        preco = db.session.get(CarviaPrecoCategoriaMoto, preco_id)
        if not preco:
            return jsonify({'erro': 'Preco nao encontrado.'}), 404

        try:
            preco.ativo = False
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'mensagem': 'Preco removido.',
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao remover preco moto #%s: %s", preco_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== EMPRESAS CUBAGEM ====================

    @bp.route('/configuracoes/empresas-cubagem') # type: ignore
    @login_required
    def listar_empresas_cubagem(): # type: ignore
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

    @bp.route('/api/empresas-cubagem', methods=['POST']) # type: ignore
    @login_required
    def criar_empresa_cubagem(): # type: ignore
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

    @bp.route('/api/empresas-cubagem/<int:empresa_id>', methods=['PUT']) # type: ignore
    @login_required
    def atualizar_empresa_cubagem(empresa_id): # type: ignore
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

    @bp.route('/api/empresas-cubagem/<int:empresa_id>', methods=['DELETE']) # type: ignore
    @login_required
    def deletar_empresa_cubagem(empresa_id): # type: ignore
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

    @bp.route('/api/transportadoras-ativas') # type: ignore 
    @login_required
    def listar_transportadoras_ativas(): # type: ignore
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

    # ==================== PARAMETROS GLOBAIS (CarviaConfig) ====================

    @bp.route('/configuracoes/parametros') # type: ignore
    @login_required
    def listar_parametros(): # type: ignore
        """Lista parametros globais do modulo CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.config_service import CarviaConfigService
        configs = CarviaConfigService.listar_todas()

        return render_template(
            'carvia/configuracoes/parametros.html',
            configs=configs,
        )

    @bp.route('/api/parametros', methods=['POST']) # type: ignore
    @login_required
    def criar_parametro(): # type: ignore
        """Cria novo parametro (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.config_service import CarviaConfigService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        chave = (data.get('chave') or '').strip()
        valor = (data.get('valor') or '').strip()

        if not chave:
            return jsonify({'erro': 'Chave e obrigatoria.'}), 400
        if not valor:
            return jsonify({'erro': 'Valor e obrigatorio.'}), 400

        # Verificar se ja existe
        from app.carvia.models import CarviaConfig
        existente = CarviaConfig.query.filter_by(chave=chave).first()
        if existente:
            return jsonify({'erro': f'Parametro "{chave}" ja existe.'}), 409

        try:
            CarviaConfigService.set(
                chave=chave,
                valor=valor,
                descricao=(data.get('descricao') or '').strip() or None,
                atualizado_por=current_user.email,
            )
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'chave': chave,
                'mensagem': f'Parametro "{chave}" criado.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar parametro: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/parametros/<int:config_id>', methods=['PUT']) # type: ignore
    @login_required
    def atualizar_parametro(config_id): # type: ignore
        """Atualiza parametro existente (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaConfig
        from app.utils.timezone import agora_utc_naive

        config = db.session.get(CarviaConfig, config_id)
        if not config:
            return jsonify({'erro': 'Parametro nao encontrado.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            if 'valor' in data:
                valor = (data['valor'] or '').strip()
                if not valor:
                    return jsonify({'erro': 'Valor e obrigatorio.'}), 400
                config.valor = valor

            if 'descricao' in data:
                config.descricao = (data['descricao'] or '').strip() or None

            config.atualizado_por = current_user.email
            config.atualizado_em = agora_utc_naive()
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'chave': config.chave,
                'mensagem': f'Parametro "{config.chave}" atualizado.',
            })

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar parametro #%s: %s", config_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/parametros/<int:config_id>', methods=['DELETE']) # type: ignore
    @login_required
    def deletar_parametro(config_id): # type: ignore
        """Remove parametro (hard delete)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        # Somente admin pode deletar parametros
        if not getattr(current_user, 'perfil', '') == 'administrador':
            return jsonify({'erro': 'Apenas administradores podem excluir parametros.'}), 403

        from app.carvia.models import CarviaConfig

        config = db.session.get(CarviaConfig, config_id)
        if not config:
            return jsonify({'erro': 'Parametro nao encontrado.'}), 404

        try:
            chave = config.chave
            db.session.delete(config)
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'mensagem': f'Parametro "{chave}" excluido.',
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao excluir parametro #%s: %s", config_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500
