"""
Rotas de Conciliacao Bancaria CarVia
=====================================

Tela 1 - Conciliacao Ativa:
  GET  /carvia/conciliacao                          - Tela principal dual-panel
  POST /carvia/api/conciliacao/importar-ofx         - Upload OFX
  GET  /carvia/api/conciliacao/documentos-elegiveis - Docs filtrados por tipo
  POST /carvia/api/conciliacao/conciliar            - Criar links N:N
  POST /carvia/api/conciliacao/desconciliar         - Remover link(s)

Tela 2 - Extrato Bancario:
  GET  /carvia/extrato-bancario                     - Visao extrato full-width
  GET  /carvia/api/conciliacao/matches/<linha_id>   - Docs elegiveis para modal inline
"""

import logging
from datetime import date

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_conciliacao_routes(bp):

    # ===================================================================
    # Tela 1: Conciliacao Ativa (dual-panel)
    # ===================================================================

    @bp.route('/conciliacao')
    @login_required
    def conciliacao():
        """Tela principal de conciliacao bancaria."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        import json
        from app.carvia.services.carvia_conciliacao_service import CarviaConciliacaoService

        resumo = CarviaConciliacaoService.obter_resumo()

        # Carregar todas as linhas para popular o painel esquerdo via JS
        linhas = CarviaConciliacaoService.obter_linhas_extrato()
        linhas_json = json.dumps([{
            'id': l.id,
            'data': l.data.strftime('%d/%m/%Y') if l.data else '',
            'valor': float(l.valor),
            'tipo': l.tipo,
            'descricao': l.descricao or '',
            'status': l.status_conciliacao,
            'saldo_a_conciliar': l.saldo_a_conciliar,
        } for l in linhas])

        return render_template(
            'carvia/conciliacao.html',
            resumo=resumo,
            linhas_json=linhas_json,
        )

    # ===================================================================
    # Tela 2: Extrato Bancario
    # ===================================================================

    @bp.route('/extrato-bancario')
    @login_required
    def extrato_bancario():
        """Tela de extrato bancario com filtros."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.carvia_conciliacao_service import CarviaConciliacaoService

        # Filtros
        hoje = date.today()
        status = request.args.get('status', '')
        data_inicio_str = request.args.get('data_inicio', '')
        data_fim_str = request.args.get('data_fim', '')
        busca = request.args.get('busca', '')

        filtros = {}
        if status:
            filtros['status'] = status

        try:
            if data_inicio_str:
                filtros['data_inicio'] = date.fromisoformat(data_inicio_str)
            else:
                filtros['data_inicio'] = hoje.replace(day=1)
                data_inicio_str = filtros['data_inicio'].isoformat()
        except ValueError:
            filtros['data_inicio'] = hoje.replace(day=1)
            data_inicio_str = filtros['data_inicio'].isoformat()

        try:
            if data_fim_str:
                filtros['data_fim'] = date.fromisoformat(data_fim_str)
            else:
                filtros['data_fim'] = hoje
                data_fim_str = hoje.isoformat()
        except ValueError:
            filtros['data_fim'] = hoje
            data_fim_str = hoje.isoformat()

        if busca:
            filtros['busca'] = busca

        linhas = CarviaConciliacaoService.obter_linhas_extrato(filtros)
        resumo = CarviaConciliacaoService.obter_resumo()

        return render_template(
            'carvia/extrato_bancario.html',
            linhas=linhas,
            resumo=resumo,
            status_filtro=status,
            data_inicio=data_inicio_str,
            data_fim=data_fim_str,
            busca=busca,
        )

    # ===================================================================
    # API: Importar OFX
    # ===================================================================

    @bp.route('/api/conciliacao/importar-ofx', methods=['POST'])
    @login_required
    def api_importar_ofx():
        """Upload e importacao de arquivo OFX."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        if 'arquivo' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']
        if not arquivo.filename:
            return jsonify({'erro': 'Arquivo sem nome'}), 400

        nome = arquivo.filename.lower()
        if not nome.endswith('.ofx'):
            return jsonify({'erro': 'Arquivo deve ser .ofx'}), 400

        try:
            from app.carvia.services.carvia_ofx_service import importar_extrato_ofx

            conteudo = arquivo.read()
            resultado = importar_extrato_ofx(
                conteudo,
                arquivo.filename,
                current_user.email,
            )

            db.session.commit()

            logger.info(
                f"OFX importado: {resultado['total_importadas']} novas, "
                f"{resultado['total_duplicadas']} duplicadas, "
                f"por {current_user.email}"
            )

            return jsonify({
                'sucesso': True,
                **resultado,
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao importar OFX: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # API: Documentos elegiveis
    # ===================================================================

    @bp.route('/api/conciliacao/documentos-elegiveis')
    @login_required
    def api_documentos_elegiveis():
        """Retorna documentos elegiveis para conciliacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        tipo_match = request.args.get('tipo', 'receber')
        if tipo_match not in ('receber', 'pagar'):
            return jsonify({'erro': 'Tipo deve ser receber ou pagar'}), 400

        from app.carvia.services.carvia_conciliacao_service import CarviaConciliacaoService

        docs = CarviaConciliacaoService.obter_documentos_elegiveis(tipo_match)
        return jsonify({'documentos': docs})

    # ===================================================================
    # API: Conciliar
    # ===================================================================

    @bp.route('/api/conciliacao/conciliar', methods=['POST'])
    @login_required
    def api_conciliar():
        """Cria vinculos de conciliacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        extrato_linha_id = data.get('extrato_linha_id')
        documentos = data.get('documentos', [])

        if not extrato_linha_id:
            return jsonify({'erro': 'extrato_linha_id obrigatorio'}), 400
        if not documentos:
            return jsonify({'erro': 'Nenhum documento selecionado'}), 400

        try:
            from app.carvia.services.carvia_conciliacao_service import CarviaConciliacaoService

            resultado = CarviaConciliacaoService.conciliar(
                int(extrato_linha_id),
                documentos,
                current_user.email,
            )
            db.session.commit()
            return jsonify(resultado)

        except ValueError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao conciliar: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # API: Desconciliar
    # ===================================================================

    @bp.route('/api/conciliacao/desconciliar', methods=['POST'])
    @login_required
    def api_desconciliar():
        """Remove conciliacoes."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        # Pode desconciliar uma conciliacao especifica ou toda a linha
        conciliacao_id = data.get('conciliacao_id')
        extrato_linha_id = data.get('extrato_linha_id')

        try:
            from app.carvia.services.carvia_conciliacao_service import CarviaConciliacaoService

            if conciliacao_id:
                resultado = CarviaConciliacaoService.desconciliar(
                    int(conciliacao_id), current_user.email
                )
            elif extrato_linha_id:
                resultado = CarviaConciliacaoService.desconciliar_linha(
                    int(extrato_linha_id), current_user.email
                )
            else:
                return jsonify({
                    'erro': 'conciliacao_id ou extrato_linha_id obrigatorio'
                }), 400

            db.session.commit()
            return jsonify(resultado)

        except ValueError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desconciliar: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # API: Matches para modal inline (Tela 2)
    # ===================================================================

    @bp.route('/api/conciliacao/matches/<int:linha_id>')
    @login_required
    def api_matches_linha(linha_id):
        """Retorna docs elegiveis para conciliacao inline de uma linha."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaExtratoLinha
        from app.carvia.services.carvia_conciliacao_service import CarviaConciliacaoService

        linha = db.session.get(CarviaExtratoLinha, linha_id)
        if not linha:
            return jsonify({'erro': 'Linha nao encontrada'}), 404

        tipo_match = 'receber' if linha.tipo == 'CREDITO' else 'pagar'
        docs = CarviaConciliacaoService.obter_documentos_elegiveis(tipo_match)

        # Conciliacoes existentes desta linha
        conciliacoes_existentes = []
        for c in linha.conciliacoes.all():
            conciliacoes_existentes.append({
                'id': c.id,
                'tipo_documento': c.tipo_documento,
                'documento_id': c.documento_id,
                'valor_alocado': float(c.valor_alocado),
            })

        return jsonify({
            'linha': {
                'id': linha.id,
                'data': linha.data.strftime('%d/%m/%Y') if linha.data else '',
                'valor': float(linha.valor),
                'tipo': linha.tipo,
                'descricao': linha.descricao or '',
                'saldo_a_conciliar': linha.saldo_a_conciliar,
            },
            'documentos': docs,
            'conciliacoes_existentes': conciliacoes_existentes,
        })
