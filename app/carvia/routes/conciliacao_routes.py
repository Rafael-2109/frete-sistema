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
  GET  /carvia/api/conciliacao/detalhe-documento/<tipo>/<doc_id> - Detalhes de doc conciliado

CSV Razao Social:
  POST /carvia/api/conciliacao/importar-csv         - Upload CSV bancario
  GET  /carvia/revisar-csv?job_id=UUID              - Pagina review pos-importacao
  POST /carvia/api/conciliacao/aplicar-csv           - Aplicar auto-matches
  POST /carvia/api/conciliacao/match-csv-manual      - Match manual individual
  POST /carvia/api/extrato/editar                    - Editar razao_social ou observacao
"""

import logging
import uuid
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# Storage temporario de jobs CSV (module-level, sem Redis)
# Formato: {uuid_str: {resultado: dict, criado_em: datetime, usuario: str}}
_csv_jobs = {}
_CSV_TTL_MINUTOS = 30


def _limpar_jobs_expirados():
    """Remove jobs com mais de 30 minutos."""
    agora = agora_utc_naive()
    expirados = [
        k for k, v in _csv_jobs.items()
        if (agora - v['criado_em']).total_seconds() > _CSV_TTL_MINUTOS * 60
    ]
    for k in expirados:
        del _csv_jobs[k]


def register_conciliacao_routes(bp):

    # ===================================================================
    # Tela 1: Conciliacao Ativa (dual-panel)
    # ===================================================================

    @bp.route('/conciliacao') # type: ignore
    @login_required
    def conciliacao(): # type: ignore
        """Tela principal de conciliacao bancaria."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        import json
        from app.carvia.services.financeiro.carvia_conciliacao_service import CarviaConciliacaoService

        resumo = CarviaConciliacaoService.obter_resumo()

        # Carregar todas as linhas para popular o painel esquerdo via JS
        linhas = CarviaConciliacaoService.obter_linhas_extrato()
        linhas_json = json.dumps([{
            'id': linha.id,
            'data': linha.data.strftime('%d/%m/%Y') if linha.data else '',
            'valor': float(linha.valor),
            'tipo': linha.tipo,
            'descricao': linha.descricao or '',
            'memo': linha.memo or '',
            'razao_social': linha.razao_social or '',
            'observacao': linha.observacao or '',
            'status': linha.status_conciliacao,
            'saldo_a_conciliar': linha.saldo_a_conciliar,
        } for linha in linhas])

        return render_template(
            'carvia/conciliacao.html',
            resumo=resumo,
            linhas_json=linhas_json,
        )

    # ===================================================================
    # Tela 2: Extrato Bancario
    # ===================================================================

    @bp.route('/extrato-bancario') # type: ignore
    @login_required
    def extrato_bancario(): # type: ignore
        """Tela de extrato bancario com filtros."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.financeiro.carvia_conciliacao_service import CarviaConciliacaoService

        # Filtros
        hoje = date.today()
        default_inicio = hoje - timedelta(days=30)
        tipo = request.args.get('tipo', '')
        status = request.args.get('status', '')
        origem = request.args.get('origem', '')  # OFX | CSV | MANUAL
        data_inicio_str = request.args.get('data_inicio', '')
        data_fim_str = request.args.get('data_fim', '')
        busca = request.args.get('busca', '')
        valor_min_str = request.args.get('valor_min', '')
        valor_max_str = request.args.get('valor_max', '')
        razao_social = request.args.get('razao_social', '')
        fatura = request.args.get('fatura', '')

        filtros = {}
        if tipo:
            filtros['tipo'] = tipo
        if status:
            filtros['status'] = status
        if origem in ('OFX', 'CSV', 'MANUAL'):
            filtros['origem'] = origem

        try:
            if data_inicio_str:
                filtros['data_inicio'] = date.fromisoformat(data_inicio_str)
            else:
                filtros['data_inicio'] = default_inicio
                data_inicio_str = default_inicio.isoformat()
        except ValueError:
            filtros['data_inicio'] = default_inicio
            data_inicio_str = default_inicio.isoformat()

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
        if valor_min_str:
            try:
                filtros['valor_min'] = float(valor_min_str)
            except ValueError:
                pass
        if valor_max_str:
            try:
                filtros['valor_max'] = float(valor_max_str)
            except ValueError:
                pass
        if razao_social:
            filtros['razao_social'] = razao_social
        if fatura:
            filtros['fatura'] = fatura

        linhas = CarviaConciliacaoService.obter_linhas_extrato(filtros)
        resumo = CarviaConciliacaoService.obter_resumo()

        return render_template(
            'carvia/extrato_bancario.html',
            linhas=linhas,
            resumo=resumo,
            tipo_filtro=tipo,
            status_filtro=status,
            origem_filtro=origem,
            data_inicio=data_inicio_str,
            data_fim=data_fim_str,
            busca=busca,
            valor_min=valor_min_str,
            valor_max=valor_max_str,
            razao_social=razao_social,
            fatura=fatura,
        )

    # ===================================================================
    # API: Importar OFX
    # ===================================================================

    @bp.route('/api/conciliacao/importar-ofx', methods=['POST']) # type: ignore
    @login_required
    def api_importar_ofx(): # type: ignore
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
            from app.carvia.services.financeiro.carvia_ofx_service import importar_extrato_ofx

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

    @bp.route('/api/conciliacao/documentos-elegiveis') # type: ignore
    @login_required
    def api_documentos_elegiveis(): # type: ignore
        """Retorna documentos elegiveis para conciliacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        tipo_match = request.args.get('tipo', 'receber')
        if tipo_match not in ('receber', 'pagar'):
            return jsonify({'erro': 'Tipo deve ser receber ou pagar'}), 400

        from app.carvia.services.financeiro.carvia_conciliacao_service import CarviaConciliacaoService

        docs = CarviaConciliacaoService.obter_documentos_elegiveis(tipo_match)

        # Scoring sugestivo (opcional — quando linha_id informado)
        linha_id = request.args.get('linha_id', type=int)
        if linha_id:
            from app.carvia.models import CarviaExtratoLinha
            from app.carvia.services.financeiro.carvia_sugestao_service import pontuar_documentos
            from app.carvia.services.financeiro.carvia_historico_match_service import (
                CarviaHistoricoMatchService,
            )

            linha = db.session.get(CarviaExtratoLinha, linha_id)
            if linha:
                # R17: boost por historico aprendido
                cnpjs_hist = CarviaHistoricoMatchService.cnpjs_aprendidos(linha)
                docs = pontuar_documentos(linha, docs, cnpjs_historico=cnpjs_hist)

        return jsonify({'documentos': docs})

    # ===================================================================
    # API: Conciliar
    # ===================================================================

    @bp.route('/api/conciliacao/conciliar', methods=['POST']) # type: ignore
    @login_required
    def api_conciliar(): # type: ignore
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
            from app.carvia.services.financeiro.carvia_conciliacao_service import CarviaConciliacaoService

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

    @bp.route('/api/conciliacao/desconciliar', methods=['POST']) # type: ignore
    @login_required
    def api_desconciliar(): # type: ignore  
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
            from app.carvia.services.financeiro.carvia_conciliacao_service import CarviaConciliacaoService

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

    @bp.route('/api/conciliacao/matches/<int:linha_id>') # type: ignore
    @login_required
    def api_matches_linha(linha_id): # type: ignore
        """Retorna docs elegiveis para conciliacao inline de uma linha."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaExtratoLinha
        from app.carvia.services.financeiro.carvia_conciliacao_service import CarviaConciliacaoService

        linha = db.session.get(CarviaExtratoLinha, linha_id)
        if not linha:
            return jsonify({'erro': 'Linha nao encontrada'}), 404

        tipo_match = 'receber' if linha.tipo == 'CREDITO' else 'pagar'
        docs = CarviaConciliacaoService.obter_documentos_elegiveis(tipo_match)

        # Scoring sugestivo (com boost R17 por historico aprendido)
        from app.carvia.services.financeiro.carvia_sugestao_service import pontuar_documentos
        from app.carvia.services.financeiro.carvia_historico_match_service import (
            CarviaHistoricoMatchService,
        )
        cnpjs_hist = CarviaHistoricoMatchService.cnpjs_aprendidos(linha)
        docs = pontuar_documentos(linha, docs, cnpjs_historico=cnpjs_hist)

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
                'razao_social': linha.razao_social or '',
                'observacao': linha.observacao or '',
                'saldo_a_conciliar': linha.saldo_a_conciliar,
            },
            'documentos': docs,
            'conciliacoes_existentes': conciliacoes_existentes,
        })

    # ===================================================================
    # API: Matches por documento (document-first, para Fluxo de Caixa)
    # ===================================================================

    @bp.route('/api/conciliacao/matches-por-documento') # type: ignore
    @login_required
    def api_matches_por_documento(): # type: ignore
        """Busca linhas de extrato candidatas para conciliar um documento.

        Inverso de api_matches_linha: recebe tipo_doc+doc_id e retorna
        CarviaExtratoLinha candidatas com scoring.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        tipo_doc = request.args.get('tipo_doc', '')
        doc_id = request.args.get('doc_id', type=int)

        if not tipo_doc or not doc_id:
            return jsonify({'erro': 'tipo_doc e doc_id sao obrigatorios'}), 400

        from app.carvia.models import (
            CarviaFaturaCliente, CarviaFaturaTransportadora,
            CarviaDespesa, CarviaCustoEntrega, CarviaReceita,
            CarviaExtratoLinha,
        )

        # Carregar documento e determinar direcao/valor
        doc_info = {}
        if tipo_doc == 'fatura_cliente':
            doc = db.session.get(CarviaFaturaCliente, doc_id)
            if not doc:
                return jsonify({'erro': 'Fatura cliente nao encontrada'}), 404
            doc_info = {
                'tipo_doc': tipo_doc,
                'id': doc.id,
                'numero': doc.numero_fatura,
                'nome': doc.cnpj_cliente or '',
                'valor': float(doc.valor_total or 0),
                'total_conciliado': float(doc.total_conciliado or 0),
                'saldo': float(doc.valor_total or 0) - float(doc.total_conciliado or 0),
                'vencimento': doc.vencimento.strftime('%d/%m/%Y') if doc.vencimento else '',
                'direcao': 'CREDITO',
            }
        elif tipo_doc == 'fatura_transportadora':
            doc = db.session.get(CarviaFaturaTransportadora, doc_id)
            if not doc:
                return jsonify({'erro': 'Fatura transportadora nao encontrada'}), 404
            nome = ''
            if doc.transportadora:
                nome = doc.transportadora.razao_social or ''
            doc_info = {
                'tipo_doc': tipo_doc,
                'id': doc.id,
                'numero': doc.numero_fatura,
                'nome': nome,
                'valor': float(doc.valor_total or 0),
                'total_conciliado': float(doc.total_conciliado or 0),
                'saldo': float(doc.valor_total or 0) - float(doc.total_conciliado or 0),
                'vencimento': doc.vencimento.strftime('%d/%m/%Y') if doc.vencimento else '',
                'direcao': 'DEBITO',
            }
        elif tipo_doc == 'despesa':
            doc = db.session.get(CarviaDespesa, doc_id)
            if not doc:
                return jsonify({'erro': 'Despesa nao encontrada'}), 404
            doc_info = {
                'tipo_doc': tipo_doc,
                'id': doc.id,
                'numero': f'DESP-{doc.id:03d}',
                'nome': doc.tipo_despesa or doc.descricao or '',
                'valor': float(doc.valor or 0),
                'total_conciliado': float(doc.total_conciliado or 0),
                'saldo': float(doc.valor or 0) - float(doc.total_conciliado or 0),
                'vencimento': doc.data_vencimento.strftime('%d/%m/%Y') if doc.data_vencimento else '',
                'direcao': 'DEBITO',
            }
        elif tipo_doc == 'custo_entrega':
            doc = db.session.get(CarviaCustoEntrega, doc_id)
            if not doc:
                return jsonify({'erro': 'Custo de entrega nao encontrado'}), 404
            doc_info = {
                'tipo_doc': tipo_doc,
                'id': doc.id,
                'numero': doc.numero_custo or f'CE-{doc.id:03d}',
                'nome': doc.tipo_custo or '',
                'valor': float(doc.valor or 0),
                'total_conciliado': float(doc.total_conciliado or 0),
                'saldo': float(doc.valor or 0) - float(doc.total_conciliado or 0),
                'vencimento': doc.data_vencimento.strftime('%d/%m/%Y') if doc.data_vencimento else '',
                'direcao': 'DEBITO',
            }
        elif tipo_doc == 'receita':
            doc = db.session.get(CarviaReceita, doc_id)
            if not doc:
                return jsonify({'erro': 'Receita nao encontrada'}), 404
            doc_info = {
                'tipo_doc': tipo_doc,
                'id': doc.id,
                'numero': f'REC-{doc.id:03d}',
                'nome': doc.descricao or '',
                'valor': float(doc.valor or 0),
                'total_conciliado': float(doc.total_conciliado or 0),
                'saldo': float(doc.valor or 0) - float(doc.total_conciliado or 0),
                'vencimento': doc.data_vencimento.strftime('%d/%m/%Y') if doc.data_vencimento else '',
                'direcao': 'CREDITO',
            }
        else:
            return jsonify({'erro': f'Tipo de documento invalido: {tipo_doc}'}), 400

        # Buscar linhas de extrato candidatas (mesma direcao, com saldo)
        direcao = doc_info['direcao']
        valor_doc = doc_info['saldo']
        if valor_doc <= 0:
            return jsonify({
                'documento': doc_info,
                'linhas': [],
                'total_pendentes': 0,
                'mensagem': 'Documento ja totalmente conciliado.',
            })

        # CNPJ do documento para boost historico R17 (graceful se ausente).
        # Aplica para: fatura_cliente (cnpj_cliente), fatura_transportadora
        # (transportadora.cnpj), custo_entrega (fornecedor_cnpj).
        # NAO aplica: despesa/receita (sem CNPJ de contraparte no modelo).
        cnpj_doc = ''
        if tipo_doc == 'fatura_cliente':
            cnpj_doc = (doc.cnpj_cliente or '').strip()
        elif tipo_doc == 'fatura_transportadora':
            if doc.transportadora and getattr(doc.transportadora, 'cnpj', None):
                cnpj_doc = (doc.transportadora.cnpj or '').strip()
        elif tipo_doc == 'custo_entrega':
            cnpj_doc = (getattr(doc, 'fornecedor_cnpj', None) or '').strip()

        # REFATOR R17 (fix bug modal vazio): trazer TODAS as linhas
        # PENDENTE/PARCIAL da direcao correta. Filtro de valor (era +-30%)
        # foi REMOVIDO — agora o valor entra no scoring, nao como criterio
        # de exclusao. Usuario precisa ver pagamentos parciais e depositos
        # agregados, que ficavam de fora.
        base_query = CarviaExtratoLinha.query.filter(
            CarviaExtratoLinha.tipo == direcao,
            CarviaExtratoLinha.status_conciliacao.in_(['PENDENTE', 'PARCIAL']),
        )

        # Total real para contador UI (antes do limit)
        total_pendentes = base_query.count()

        # Ceiling generoso — 99% dos casos tem <100 linhas pendentes.
        # 200 da folga sem estourar DOM render.
        LIMIT_CEILING = 200
        linhas_candidatas = base_query.order_by(
            CarviaExtratoLinha.data.desc()
        ).limit(LIMIT_CEILING).all()

        # R17: historico aprendido por linha (batch — evita N+1 queries).
        # Se a tabela carvia_historico_match_extrato nao existir (migration
        # nao rodada), retorna dict vazio graciosamente.
        from app.carvia.services.financeiro.carvia_historico_match_service import (
            CarviaHistoricoMatchService,
        )
        hist_por_linha = CarviaHistoricoMatchService.cnpjs_aprendidos_batch(
            linhas_candidatas
        )

        # Construir resposta com scoring simplificado + boost historico
        linhas_result = []
        for ln in linhas_candidatas:
            # Score por cobertura (trata pagamentos parciais de forma justa):
            #   - Linha <= doc: pontua pela PROPORCAO coberta (R$3k/R$10k = 0.30)
            #     Linhas parciais NAO sao penalizadas por serem menores —
            #     sao ordenadas pela capacidade de contribuir ao saldo.
            #   - Linha > doc: penaliza o EXCESSO (50% excesso = score 0.5).
            #     Depositos muito maiores que o doc sao menos prováveis.
            valor_linha = abs(float(ln.valor))
            if valor_doc <= 0:
                score_valor = 0.0
            elif valor_linha <= valor_doc:
                score_valor = valor_linha / valor_doc
            else:
                excesso_pct = (valor_linha - valor_doc) / valor_doc
                score_valor = max(0, 1 - excesso_pct)

            # Score por proximidade de data (se temos vencimento)
            score_data = 0.3  # neutro
            if ln.data and doc_info.get('vencimento'):
                from datetime import datetime
                try:
                    venc = datetime.strptime(doc_info['vencimento'], '%d/%m/%Y').date()
                    delta = abs((ln.data - venc).days)
                    score_data = max(0, 1 - delta / 30)
                except (ValueError, TypeError):
                    pass

            score = score_valor * 0.60 + score_data * 0.40

            # R17: boost 1.4x se CNPJ do doc aparece no historico aprendido
            # da linha (mesma estrategia aplicada em pontuar_documentos).
            score_historico = False
            if cnpj_doc:
                hist = hist_por_linha.get(ln.id, {})
                if cnpj_doc in hist:
                    score = min(1.0, score * 1.4)
                    score_historico = True

            if score >= 0.80:
                label = 'ALTO'
            elif score >= 0.50:
                label = 'MEDIO'
            else:
                label = 'BAIXO'

            linhas_result.append({
                'id': ln.id,
                'data': ln.data.strftime('%d/%m/%Y') if ln.data else '',
                'valor': float(ln.valor),
                'tipo': ln.tipo,
                'descricao': ln.descricao or '',
                'razao_social': ln.razao_social or '',
                'observacao': ln.observacao or '',
                'saldo_a_conciliar': ln.saldo_a_conciliar,
                'origem': ln.origem,
                'conta_origem': ln.conta_origem or '',
                'score': round(score, 2),
                'score_label': label,
                'score_historico': score_historico,
            })

        # Ordenar por score desc — desempate natural vem da query
        # (ja ordenada por data desc no SQL). Top matches no topo.
        linhas_result.sort(key=lambda x: x['score'], reverse=True)

        return jsonify({
            'documento': doc_info,
            'linhas': linhas_result,
            'total_pendentes': total_pendentes,
        })

    # ===================================================================
    # CSV Razao Social: Upload
    # ===================================================================

    @bp.route('/api/conciliacao/importar-csv', methods=['POST']) # type: ignore
    @login_required
    def api_importar_csv(): # type: ignore
        """Upload e processamento de CSV bancario para enriquecer razao social."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        _limpar_jobs_expirados()

        if 'arquivo' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']
        if not arquivo.filename:
            return jsonify({'erro': 'Arquivo sem nome'}), 400

        nome = arquivo.filename.lower()
        if not nome.endswith('.csv'):
            return jsonify({'erro': 'Arquivo deve ser .csv'}), 400

        try:
            from app.carvia.services.financeiro.carvia_csv_razao_service import (
                parsear_csv_banco,
                match_csv_com_extrato,
            )

            conteudo = arquivo.read()
            csv_linhas = parsear_csv_banco(conteudo)
            resultado = match_csv_com_extrato(csv_linhas)

            # Armazenar resultado com TTL
            job_id = str(uuid.uuid4())
            _csv_jobs[job_id] = {
                'resultado': resultado,
                'criado_em': agora_utc_naive(),
                'usuario': current_user.email,
            }

            logger.info(
                f"CSV importado: {resultado['resumo']['total_csv']} linhas, "
                f"{resultado['resumo']['total_auto']} auto-matches, "
                f"por {current_user.email}"
            )

            return jsonify({
                'sucesso': True,
                'job_id': job_id,
                'resumo': resultado['resumo'],
                'redirect_url': url_for('carvia.revisar_csv', job_id=job_id),
            })

        except ValueError as e:
            logger.warning(f"Erro ao parsear CSV: {e}")
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            logger.error(f"Erro ao processar CSV: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # CSV Razao Social: Pagina de Review
    # ===================================================================

    @bp.route('/revisar-csv') # type: ignore
    @login_required
    def revisar_csv(): # type: ignore
        """Pagina de review pos-importacao CSV."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        _limpar_jobs_expirados()

        job_id = request.args.get('job_id', '')
        if not job_id or job_id not in _csv_jobs:
            flash('Sessao de importacao CSV expirada ou invalida. Importe novamente.', 'warning')
            return redirect(url_for('carvia.extrato_bancario'))

        job = _csv_jobs[job_id]
        resultado = job['resultado']

        return render_template(
            'carvia/revisar_csv.html',
            job_id=job_id,
            auto_matched=resultado['auto_matched'],
            pendentes_manual=resultado['pendentes_manual'],
            sem_correspondencia=resultado['sem_correspondencia'],
            resumo=resultado['resumo'],
        )

    # ===================================================================
    # CSV Razao Social: Aplicar Auto-matches
    # ===================================================================

    @bp.route('/api/conciliacao/aplicar-csv', methods=['POST']) # type: ignore
    @login_required
    def api_aplicar_csv(): # type: ignore
        """Aplica todos auto-matches de um job CSV no banco."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        job_id = data.get('job_id', '')
        if not job_id or job_id not in _csv_jobs:
            return jsonify({'erro': 'Job expirado ou invalido'}), 400

        try:
            from app.carvia.services.financeiro.carvia_csv_razao_service import aplicar_matches

            job = _csv_jobs[job_id]
            matches = job['resultado']['auto_matched']

            total = aplicar_matches(matches, current_user.email)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'total_aplicados': total,
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao aplicar auto-matches CSV: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # CSV Razao Social: Match Manual Individual
    # ===================================================================

    @bp.route('/api/conciliacao/match-csv-manual', methods=['POST']) # type: ignore
    @login_required
    def api_match_csv_manual(): # type: ignore
        """Aplica match manual individual de CSV para extrato."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        job_id = data.get('job_id', '')
        csv_index = data.get('csv_index')
        extrato_id = data.get('extrato_id')

        if not job_id or job_id not in _csv_jobs:
            return jsonify({'erro': 'Job expirado ou invalido'}), 400
        if csv_index is None or extrato_id is None:
            return jsonify({'erro': 'csv_index e extrato_id obrigatorios'}), 400

        try:
            from app.carvia.services.financeiro.carvia_csv_razao_service import aplicar_matches

            job = _csv_jobs[job_id]
            pendentes = job['resultado']['pendentes_manual']

            # Encontrar o item CSV
            item = None
            item_idx = None
            for i, p in enumerate(pendentes):
                if p['csv_index'] == csv_index:
                    item = p
                    item_idx = i
                    break

            if item is None:
                return jsonify({'erro': 'Item CSV nao encontrado no job'}), 400

            # Aplicar match
            total = aplicar_matches([{
                'extrato_id': int(extrato_id),
                'razao_social': item['razao_social'],
            }], current_user.email)

            db.session.commit()

            # Remover do job
            if item_idx is not None:
                pendentes.pop(item_idx)

            return jsonify({
                'sucesso': True,
                'razao_social': item['razao_social'],
                'extrato_id': extrato_id,
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao aplicar match CSV manual: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # API: Detalhe de Documento Conciliado
    # ===================================================================

    @bp.route('/api/conciliacao/detalhe-documento/<tipo>/<int:doc_id>') # type: ignore
    @login_required
    def api_detalhe_documento(tipo, doc_id): # type: ignore 
        """Retorna detalhes de um documento conciliado para exibicao em modal."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        tipos_validos = ('fatura_cliente', 'fatura_transportadora', 'despesa', 'custo_entrega', 'receita')
        if tipo not in tipos_validos:
            return jsonify({'erro': f'Tipo invalido: {tipo}'}), 400

        def _fmt_valor(v):
            if v is None:
                return '-'
            return f'R$ {float(v):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

        def _fmt_data(d):
            if d is None:
                return '-'
            return d.strftime('%d/%m/%Y')

        def _calc_saldo(valor_total, total_conciliado):
            vt = float(valor_total or 0)
            tc = float(total_conciliado or 0)
            return _fmt_valor(vt - tc)

        try:
            if tipo == 'fatura_cliente':
                from app.carvia.models import CarviaFaturaCliente
                from app.carvia.services.financeiro.carvia_conciliacao_service import CarviaConciliacaoService
                doc = db.session.get(CarviaFaturaCliente, doc_id)
                if not doc:
                    return jsonify({'erro': 'Fatura cliente nao encontrada'}), 404

                # Enriquecer com CTes, NFs, remetente, destinatarios
                enrichment = CarviaConciliacaoService._enriquecer_fatura_cliente_para_conciliacao(doc)
                cond = CarviaConciliacaoService._buscar_condicoes_comerciais_fatura(doc)

                campos = [
                    {'label': 'Cliente', 'valor': doc.nome_cliente or '-'},
                    {'label': 'CNPJ', 'valor': doc.cnpj_cliente or '-'},
                    {'label': 'Data Emissao', 'valor': _fmt_data(doc.data_emissao)},
                    {'label': 'Vencimento', 'valor': _fmt_data(doc.vencimento)},
                    {'label': 'Valor Total', 'valor': _fmt_valor(doc.valor_total)},
                    {'label': 'Conciliado', 'valor': _fmt_valor(doc.total_conciliado)},
                    {'label': 'Saldo', 'valor': _calc_saldo(doc.valor_total, doc.total_conciliado)},
                    {'label': 'Status', 'valor': doc.status or '-'},
                ]

                # Remetente
                if enrichment.get('remetente_nome'):
                    campos.append({
                        'label': 'Embarcador (Rem.)',
                        'valor': f"{enrichment['remetente_nome']} ({enrichment.get('remetente_cnpj', '')})",
                    })

                # Destinatarios
                if enrichment.get('destinatarios'):
                    dests = [d.get('nome') or d.get('cnpj', '') for d in enrichment['destinatarios']]
                    campos.append({'label': 'Destinatario(s)', 'valor': ', '.join(dests)})

                # Condicoes comerciais
                if cond.get('condicao_pagamento'):
                    campos.append({'label': 'Cond. Pagamento', 'valor': cond['condicao_pagamento']})
                if cond.get('responsavel_frete_label'):
                    campos.append({'label': 'Resp. Frete', 'valor': cond['responsavel_frete_label']})

                return jsonify({
                    'titulo': 'Fatura Cliente',
                    'numero': doc.numero_fatura,
                    'url': f'/carvia/faturas-cliente/{doc.id}',
                    'campos': campos,
                    'cte_numeros': enrichment.get('cte_numeros', []),
                    'nf_numeros': enrichment.get('nf_numeros', []),
                })

            elif tipo == 'fatura_transportadora':
                from app.carvia.models import CarviaFaturaTransportadora, CarviaSubcontrato
                doc = db.session.get(CarviaFaturaTransportadora, doc_id)
                if not doc:
                    return jsonify({'erro': 'Fatura transportadora nao encontrada'}), 404
                nome_transp = doc.transportadora.razao_social if doc.transportadora else '-'
                cnpj_transp = doc.transportadora.cnpj if doc.transportadora else '-'

                # CTes dos subcontratos vinculados
                subs = CarviaSubcontrato.query.filter_by(
                    fatura_transportadora_id=doc.id
                ).all()
                cte_numeros = [s.cte_numero for s in subs if s.cte_numero]

                campos = [
                    {'label': 'Transportadora', 'valor': nome_transp},
                    {'label': 'CNPJ Transportadora', 'valor': cnpj_transp},
                    {'label': 'Data Emissao', 'valor': _fmt_data(doc.data_emissao)},
                    {'label': 'Vencimento', 'valor': _fmt_data(doc.vencimento)},
                    {'label': 'Valor Total', 'valor': _fmt_valor(doc.valor_total)},
                    {'label': 'Conciliado', 'valor': _fmt_valor(doc.total_conciliado)},
                    {'label': 'Saldo', 'valor': _calc_saldo(doc.valor_total, doc.total_conciliado)},
                    {'label': 'Status Pagamento', 'valor': doc.status_pagamento or '-'},
                ]

                return jsonify({
                    'titulo': 'Fatura Transportadora',
                    'numero': doc.numero_fatura,
                    'url': f'/carvia/faturas-transportadora/{doc.id}',
                    'campos': campos,
                    'cte_numeros': cte_numeros,
                })

            elif tipo == 'despesa':
                from app.carvia.models import CarviaDespesa
                doc = db.session.get(CarviaDespesa, doc_id)
                if not doc:
                    return jsonify({'erro': 'Despesa nao encontrada'}), 404
                return jsonify({
                    'titulo': 'Despesa',
                    'numero': f'DESP-{doc.id:03d}',
                    'url': f'/carvia/despesas/{doc.id}',
                    'campos': [
                        {'label': 'Tipo', 'valor': doc.tipo_despesa or '-'},
                        {'label': 'Descricao', 'valor': doc.descricao or '-'},
                        {'label': 'Data Despesa', 'valor': _fmt_data(doc.data_despesa)},
                        {'label': 'Vencimento', 'valor': _fmt_data(doc.data_vencimento)},
                        {'label': 'Valor', 'valor': _fmt_valor(doc.valor)},
                        {'label': 'Conciliado', 'valor': _fmt_valor(doc.total_conciliado)},
                        {'label': 'Saldo', 'valor': _calc_saldo(doc.valor, doc.total_conciliado)},
                        {'label': 'Status', 'valor': doc.status or '-'},
                    ],
                })

            elif tipo == 'custo_entrega':
                from app.carvia.models import CarviaCustoEntrega
                doc = db.session.get(CarviaCustoEntrega, doc_id)
                if not doc:
                    return jsonify({'erro': 'Custo de entrega nao encontrado'}), 404
                return jsonify({
                    'titulo': 'Custo de Entrega',
                    'numero': doc.numero_custo,
                    'url': f'/carvia/custos-entrega/{doc.id}',
                    'campos': [
                        {'label': 'Tipo', 'valor': doc.tipo_custo or '-'},
                        {'label': 'Descricao', 'valor': doc.descricao or '-'},
                        {'label': 'Fornecedor', 'valor': doc.fornecedor_nome or '-'},
                        {'label': 'CNPJ Fornecedor', 'valor': doc.fornecedor_cnpj or '-'},
                        {'label': 'Data Custo', 'valor': _fmt_data(doc.data_custo)},
                        {'label': 'Vencimento', 'valor': _fmt_data(doc.data_vencimento)},
                        {'label': 'Valor', 'valor': _fmt_valor(doc.valor)},
                        {'label': 'Conciliado', 'valor': _fmt_valor(doc.total_conciliado)},
                        {'label': 'Saldo', 'valor': _calc_saldo(doc.valor, doc.total_conciliado)},
                        {'label': 'Status', 'valor': doc.status or '-'},
                    ],
                })

            elif tipo == 'receita':
                from app.carvia.models import CarviaReceita
                doc = db.session.get(CarviaReceita, doc_id)
                if not doc:
                    return jsonify({'erro': 'Receita nao encontrada'}), 404
                return jsonify({
                    'titulo': 'Receita',
                    'numero': f'REC-{doc.id:03d}',
                    'url': f'/carvia/receitas/{doc.id}',
                    'campos': [
                        {'label': 'Tipo', 'valor': doc.tipo_receita or '-'},
                        {'label': 'Descricao', 'valor': doc.descricao or '-'},
                        {'label': 'Data Receita', 'valor': _fmt_data(doc.data_receita)},
                        {'label': 'Vencimento', 'valor': _fmt_data(doc.data_vencimento)},
                        {'label': 'Valor', 'valor': _fmt_valor(doc.valor)},
                        {'label': 'Conciliado', 'valor': _fmt_valor(doc.total_conciliado)},
                        {'label': 'Saldo', 'valor': _calc_saldo(doc.valor, doc.total_conciliado)},
                        {'label': 'Status', 'valor': doc.status or '-'},
                    ],
                })

        except Exception as e:
            logger.error(f"Erro ao buscar detalhe documento {tipo}/{doc_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # API: Conciliacoes de um Documento (rastreabilidade reversa)
    # ===================================================================

    @bp.route('/api/conciliacao/conciliacoes-documento/<tipo>/<int:doc_id>') # type: ignore
    @login_required
    def api_conciliacoes_documento(tipo, doc_id): # type: ignore
        """Retorna conciliacoes bancarias vinculadas a um documento.

        Usado pelas paginas de detalhe dos 5 tipos de documento para exibir
        a secao 'Conciliacoes Bancarias' com links de volta ao extrato.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        tipos_validos = (
            'fatura_cliente', 'fatura_transportadora', 'despesa',
            'custo_entrega', 'receita',
        )
        if tipo not in tipos_validos:
            return jsonify({'erro': f'Tipo invalido: {tipo}'}), 400

        try:
            from app.carvia.services.financeiro.carvia_conciliacao_service import (
                CarviaConciliacaoService,
            )
            conciliacoes = CarviaConciliacaoService.obter_conciliacoes_documento(
                tipo, doc_id
            )
            return jsonify({'conciliacoes': conciliacoes})
        except Exception as e:
            logger.error(f"Erro ao buscar conciliacoes do documento {tipo}/{doc_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # Editar Razao Social / Observacao
    # ===================================================================

    @bp.route('/api/extrato/editar', methods=['POST']) # type: ignore
    @login_required
    def api_editar_extrato(): # type: ignore
        """Edita razao_social ou observacao de uma linha do extrato."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        extrato_id = data.get('extrato_id')
        campo = data.get('campo', '')
        valor = data.get('valor', '')

        if not extrato_id:
            return jsonify({'erro': 'extrato_id obrigatorio'}), 400
        if not campo:
            return jsonify({'erro': 'campo obrigatorio'}), 400

        try:
            from app.carvia.services.financeiro.carvia_csv_razao_service import atualizar_campo_extrato

            resultado = atualizar_campo_extrato(int(extrato_id), campo, valor)
            db.session.commit()

            return jsonify(resultado)

        except ValueError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar extrato: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # Custo Fiscal — Criar CE a partir de linha fiscal (GNRE/SEFAZ)
    # ===================================================================

    _TIPOS_CUSTO_VALIDOS = [
        'DIARIA', 'REENTREGA', 'ARMAZENAGEM', 'DEVOLUCAO', 'AVARIA',
        'PEDAGIO_EXTRA', 'TAXA_DESCARGA', 'OUTROS',
    ]

    @bp.route('/api/conciliacao/ctes-para-custo')  # type: ignore
    @login_required
    def api_ctes_para_custo():  # type: ignore
        """Lista CTes com info rica para seleção no modal de custo fiscal.

        Filtra apenas CTes com uf_origem != SP (GNRE aplica-se a CTes de fora de SP).
        Enriquece com dados do destinatário via NF vinculada.

        D11 (2026-04-19): Quando o caller passa `valor_extrato` (linha DEBITO
        de GNRE/SEFAZ), ordena CTes por proximidade de `icms_valor`. CTes com
        diferenca <= 5% recebem `match_icms=True` e aparecem no topo.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaOperacao

        busca = request.args.get('busca', '').strip()
        # D11: valor do extrato para sugestao automatica (opcional)
        valor_extrato_raw = request.args.get('valor_extrato', '').strip()
        valor_extrato = None
        if valor_extrato_raw:
            try:
                valor_extrato = float(valor_extrato_raw.replace(',', '.'))
                if valor_extrato <= 0:
                    valor_extrato = None
            except (ValueError, TypeError):
                valor_extrato = None

        query = db.session.query(CarviaOperacao).filter(
            CarviaOperacao.status != 'CANCELADO',
            db.or_(
                CarviaOperacao.uf_origem != 'SP',
                CarviaOperacao.uf_origem.is_(None),
            ),
        )

        if busca:
            bl = f'%{busca}%'
            query = query.filter(db.or_(
                CarviaOperacao.cte_numero.ilike(bl),
                CarviaOperacao.nome_cliente.ilike(bl),
                CarviaOperacao.cidade_destino.ilike(bl),
                CarviaOperacao.cidade_origem.ilike(bl),
            ))

        operacoes = query.order_by(
            CarviaOperacao.cte_data_emissao.desc().nullslast()
        ).limit(100).all()

        resultado = []
        for op in operacoes:
            # Primeiro NF para dados do destinatário
            primeiro_nf = op.nfs.first()

            icms_valor_float = float(op.icms_valor) if op.icms_valor else None
            icms_base_float = (
                float(op.icms_base_calculo) if op.icms_base_calculo else None
            )
            icms_aliq_float = (
                float(op.icms_aliquota) if op.icms_aliquota else None
            )

            # D11: score de similaridade de valor ICMS com a linha do extrato
            match_icms = False
            delta_icms_pct = None
            if valor_extrato is not None and icms_valor_float:
                delta = abs(icms_valor_float - valor_extrato)
                delta_icms_pct = (delta / valor_extrato) * 100 if valor_extrato else None
                if delta_icms_pct is not None and delta_icms_pct <= 5.0:
                    match_icms = True

            resultado.append({
                'id': op.id,
                'cte_numero': op.cte_numero or f'OP-{op.id}',
                'nome_cliente': op.nome_cliente or '',
                'cnpj_cliente': op.cnpj_cliente or '',
                'uf_origem': op.uf_origem or '',
                'cidade_origem': op.cidade_origem or '',
                'uf_destino': op.uf_destino or '',
                'cidade_destino': op.cidade_destino or '',
                'valor_mercadoria': float(op.valor_mercadoria) if op.valor_mercadoria else None,
                'peso_utilizado': float(op.peso_utilizado) if op.peso_utilizado else None,
                'cte_valor': float(op.cte_valor) if op.cte_valor else None,
                # D11: dados ICMS persistidos (antes em runtime via XML)
                'icms_valor': icms_valor_float,
                'icms_base_calculo': icms_base_float,
                'icms_aliquota': icms_aliq_float,
                'match_icms': match_icms,
                'delta_icms_pct': delta_icms_pct,
                'cte_data_emissao': (
                    op.cte_data_emissao.strftime('%d/%m/%Y')
                    if op.cte_data_emissao else ''
                ),
                'status': op.status,
                'destinatario_nome': (
                    primeiro_nf.nome_destinatario if primeiro_nf else ''
                ),
                'destinatario_uf': (
                    primeiro_nf.uf_destinatario if primeiro_nf else ''
                ),
                'destinatario_cidade': (
                    primeiro_nf.cidade_destinatario if primeiro_nf else ''
                ),
                'nf_data_emissao': (
                    primeiro_nf.data_emissao.strftime('%d/%m/%Y')
                    if primeiro_nf and primeiro_nf.data_emissao else ''
                ),
            })

        # D11: reordenar priorizando match_icms, depois por delta_icms_pct
        # ascendente (menor diferenca = mais relevante). CTes sem ICMS ou
        # sem valor_extrato vao ao final na ordem original (por data desc).
        if valor_extrato is not None:
            def _sort_key(item):
                # Menor delta primeiro; None vai pro final
                delta = item.get('delta_icms_pct')
                has_delta = delta is not None
                return (
                    0 if item['match_icms'] else 1,  # matches primeiro
                    0 if has_delta else 1,           # com delta primeiro
                    delta if has_delta else 999999,  # menor delta primeiro
                )
            resultado.sort(key=_sort_key)

        return jsonify({
            'sucesso': True,
            'ctes': resultado,
            'valor_extrato_usado': valor_extrato,
        })

    @bp.route('/api/conciliacao/criar-custo-fiscal', methods=['POST'])  # type: ignore
    @login_required
    def api_criar_custo_fiscal():  # type: ignore
        """Cria CarviaCustoEntrega a partir de linha fiscal e auto-concilia.

        Fluxo atômico: cria CE → vincula frete → concilia com linha extrato.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import (
            CarviaExtratoLinha,
            CarviaOperacao,
            CarviaCustoEntrega,
            CarviaFrete,
        )
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )

        data = request.get_json(silent=True) or {}
        extrato_linha_id = data.get('extrato_linha_id')
        operacao_id = data.get('operacao_id')
        tipo_custo = data.get('tipo_custo', 'OUTROS')
        descricao = data.get('descricao', '')

        # Validações de entrada
        if not extrato_linha_id or not operacao_id:
            return jsonify({
                'erro': 'extrato_linha_id e operacao_id sao obrigatorios',
            }), 400

        if tipo_custo not in _TIPOS_CUSTO_VALIDOS:
            return jsonify({'erro': f'Tipo de custo invalido: {tipo_custo}'}), 400

        try:
            # Carregar e validar linha do extrato
            linha = db.session.get(CarviaExtratoLinha, int(extrato_linha_id))
            if not linha:
                return jsonify({'erro': 'Linha de extrato nao encontrada'}), 404

            if linha.tipo != 'DEBITO':
                return jsonify({
                    'erro': 'Custo fiscal so pode ser criado para linhas DEBITO',
                }), 400

            saldo = linha.saldo_a_conciliar
            if saldo <= 0:
                return jsonify({
                    'erro': 'Linha ja esta totalmente conciliada',
                }), 400

            # Carregar e validar operação (CTe)
            operacao = db.session.get(CarviaOperacao, int(operacao_id))
            if not operacao:
                return jsonify({'erro': 'Operacao (CTe) nao encontrada'}), 404

            if operacao.status == 'CANCELADO':
                return jsonify({'erro': 'Operacao esta cancelada'}), 400

            # Criar CarviaCustoEntrega
            numero_custo = CarviaCustoEntrega.gerar_numero_custo()

            custo = CarviaCustoEntrega(
                numero_custo=numero_custo,
                operacao_id=int(operacao_id),
                tipo_custo=tipo_custo,
                descricao=descricao or None,
                valor=saldo,
                data_custo=linha.data,
                status='PENDENTE',
                criado_por=current_user.email,
            )
            db.session.add(custo)
            db.session.flush()

            # Auto-link frete (mesmo padrão de custo_entrega_routes.py)
            frete = CarviaFrete.query.filter_by(
                operacao_id=custo.operacao_id
            ).first()
            if frete:
                custo.frete_id = frete.id

            # Auto-conciliar com a linha do extrato
            resultado_conc = CarviaConciliacaoService.conciliar(
                extrato_linha_id=int(extrato_linha_id),
                documentos=[{
                    'tipo_documento': 'custo_entrega',
                    'documento_id': custo.id,
                    'valor_alocado': float(saldo),
                }],
                usuario=current_user.email,
            )

            db.session.commit()

            logger.info(
                f"Custo fiscal {numero_custo} criado e conciliado "
                f"com linha {extrato_linha_id} por {current_user.email}"
            )

            return jsonify({
                'sucesso': True,
                'custo_id': custo.id,
                'numero_custo': custo.numero_custo,
                'valor': float(saldo),
                'status_linha': resultado_conc.get('status_linha', ''),
            })

        except ValueError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar custo fiscal: {e}", exc_info=True)
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # PATCH/DELETE de linha MANUAL (W10 Nivel 2 — Sprint 4)
    # ===================================================================
    #
    # Linhas com origem='MANUAL' sao criadas pelo CarviaPagamentoService
    # (pagamento fora do extrato bancario — conta pessoal, dinheiro, etc.).
    # Podem ser editadas/deletadas enquanto nao conciliadas.
    # OFX/CSV sao imutaveis.

    @bp.route('/api/extrato/linha/<int:linha_id>', methods=['PATCH'])
    @login_required
    def api_extrato_linha_editar(linha_id):  # type: ignore
        """Edita linha MANUAL (data, valor, descricao, conta_origem).

        Bloqueado para OFX/CSV (imutaveis) e para linhas ja conciliadas.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaExtratoLinha

        linha = db.session.get(CarviaExtratoLinha, linha_id)
        if not linha:
            return jsonify({'erro': 'Linha nao encontrada'}), 404

        pode, razao = linha.pode_editar()
        if not pode:
            return jsonify({'erro': razao}), 400

        data = request.get_json() or {}

        # Campos editaveis (todos opcionais — atualiza apenas os presentes)
        try:
            if 'data' in data and data['data']:
                try:
                    nova_data = date.fromisoformat(str(data['data']))
                except (ValueError, TypeError):
                    return jsonify({
                        'erro': 'Data invalida (formato: YYYY-MM-DD)'
                    }), 400
                hoje = date.today()
                limite_inf = hoje - relativedelta(years=5)
                limite_sup = hoje + relativedelta(years=2)
                if not (limite_inf <= nova_data <= limite_sup):
                    return jsonify({
                        'erro': (
                            f'Data fora do intervalo permitido '
                            f'({limite_inf} a {limite_sup}).'
                        )
                    }), 400
                linha.data = nova_data

            if 'valor' in data and data['valor'] is not None:
                novo_valor = float(data['valor'])
                if novo_valor <= 0:
                    return jsonify({'erro': 'Valor deve ser positivo'}), 400
                linha.valor = novo_valor

            if 'descricao' in data:
                desc = data['descricao']
                if desc is None or (isinstance(desc, str) and desc.strip() == ''):
                    linha.descricao = None
                else:
                    linha.descricao = str(desc).strip()[:500]

            if 'conta_origem' in data:
                conta = (data['conta_origem'] or '').strip()
                if not conta:
                    return jsonify({
                        'erro': 'conta_origem e obrigatorio para linha MANUAL'
                    }), 400
                linha.conta_origem = conta[:100]
                linha.memo = f'Pagamento manual — {conta[:100]}'

            if 'tipo' in data and data['tipo']:
                if data['tipo'] not in ('CREDITO', 'DEBITO'):
                    return jsonify({'erro': 'tipo deve ser CREDITO ou DEBITO'}), 400
                linha.tipo = data['tipo']

            db.session.commit()

            logger.info(
                "Linha MANUAL #%s editada por %s", linha_id, current_user.email
            )

            return jsonify({
                'sucesso': True,
                'linha': {
                    'id': linha.id,
                    'data': linha.data.isoformat() if linha.data else None,
                    'valor': float(linha.valor or 0),
                    'tipo': linha.tipo,
                    'descricao': linha.descricao,
                    'conta_origem': linha.conta_origem,
                    'origem': linha.origem,
                    'status_conciliacao': linha.status_conciliacao,
                },
            })

        except ValueError as e:
            db.session.rollback()
            return jsonify({'erro': f'Dados invalidos: {e}'}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao editar linha MANUAL #{linha_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/extrato/linha/<int:linha_id>', methods=['DELETE'])
    @login_required
    def api_extrato_linha_deletar(linha_id):  # type: ignore
        """Deleta linha MANUAL (se nao conciliada).

        Bloqueado para OFX/CSV (imutaveis) e para linhas com conciliacao.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaExtratoLinha

        linha = db.session.get(CarviaExtratoLinha, linha_id)
        if not linha:
            return jsonify({'erro': 'Linha nao encontrada'}), 404

        pode, razao = linha.pode_deletar()
        if not pode:
            return jsonify({'erro': razao}), 400

        try:
            db.session.delete(linha)
            db.session.commit()

            logger.info(
                "Linha MANUAL #%s deletada por %s",
                linha_id, current_user.email,
            )

            return jsonify({'sucesso': True})

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao deletar linha MANUAL #{linha_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # Pre-Vinculo Extrato <-> Cotacao (frete CarVia pre-pago)
    # ===================================================================

    @bp.route('/api/cotacoes/<int:cotacao_id>/linhas-extrato-candidatas')  # type: ignore
    @login_required
    def api_previnculo_linhas_candidatas(cotacao_id):  # type: ignore
        """Lista linhas de extrato candidatas para pre-vincular a uma cotacao.

        Filtra: tipo=CREDITO, status IN (PENDENTE, PARCIAL), valor absoluto
        na margem +-30% do valor final aprovado. Aplica scoring sugestivo.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaCotacao
        from app.carvia.services.financeiro.previnculo_service import (
            CarviaPreVinculoService,
        )

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return jsonify({'erro': 'Cotacao nao encontrada'}), 404
        if cotacao.status != 'APROVADO':
            return jsonify({
                'erro': f'Cotacao esta {cotacao.status}, pre-vinculo aceita apenas APROVADO'
            }), 400

        try:
            margem = float(request.args.get('margem_pct', 0.30))
            linhas = CarviaPreVinculoService.listar_candidatos_extrato(
                cotacao_id, margem_pct=margem,
            )
            return jsonify({
                'cotacao': {
                    'id': cotacao.id,
                    'numero_cotacao': cotacao.numero_cotacao,
                    'valor_final_aprovado': float(
                        cotacao.valor_final_aprovado or 0
                    ),
                    'cliente_nome': (
                        cotacao.cliente.nome_comercial if cotacao.cliente else ''
                    ),
                    'data_cotacao': (
                        cotacao.data_cotacao.strftime('%d/%m/%Y')
                        if cotacao.data_cotacao else ''
                    ),
                },
                'linhas': linhas,
                'total': len(linhas),
            })
        except ValueError as e:
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            logger.exception(f'Erro listar linhas candidatas cotacao {cotacao_id}: {e}')
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/previncular-extrato', methods=['POST'])  # type: ignore
    @login_required
    def api_previncular_extrato(cotacao_id):  # type: ignore
        """Cria pre-vinculo(s) entre linha(s) do extrato e esta cotacao.

        Body: {
            'vinculos': [
                {'extrato_linha_id': int, 'valor_alocado': float, 'observacao': str?}
            ],
        }
        Aceita 1 ou N vinculos no mesmo POST.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json() or {}
        vinculos = data.get('vinculos') or []
        if not vinculos:
            return jsonify({'erro': 'Nenhum vinculo enviado'}), 400

        from app.carvia.services.financeiro.previnculo_service import (
            CarviaPreVinculoService,
        )

        criados = []
        try:
            for v in vinculos:
                linha_id = v.get('extrato_linha_id')
                valor = v.get('valor_alocado')
                observacao = v.get('observacao')
                if not linha_id or valor is None:
                    raise ValueError(
                        'Cada vinculo precisa de extrato_linha_id e valor_alocado'
                    )
                pv = CarviaPreVinculoService.criar(
                    cotacao_id=cotacao_id,
                    extrato_linha_id=int(linha_id),
                    valor_alocado=float(valor),
                    observacao=observacao,
                    usuario=current_user.email,
                )
                criados.append(CarviaPreVinculoService._serializar(pv))

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'criados': len(criados),
                'previnculos': criados,
            })

        except ValueError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro criar pre-vinculo cotacao {cotacao_id}: {e}')
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/previnculos')  # type: ignore
    @login_required
    def api_listar_previnculos_cotacao(cotacao_id):  # type: ignore
        """Lista pre-vinculos de uma cotacao (ATIVO + RESOLVIDO + CANCELADO)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.services.financeiro.previnculo_service import (
            CarviaPreVinculoService,
        )
        try:
            lista = CarviaPreVinculoService.listar_por_cotacao(
                cotacao_id, incluir_resolvidos=True,
            )
            return jsonify({'previnculos': lista, 'total': len(lista)})
        except Exception as e:
            logger.exception(f'Erro listar previnculos cotacao {cotacao_id}: {e}')
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/previnculos/<int:previnculo_id>', methods=['DELETE'])  # type: ignore
    @login_required
    def api_cancelar_previnculo(previnculo_id):  # type: ignore
        """Cancela (soft) um pre-vinculo ATIVO. Exige motivo no body."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json() or {}
        motivo = (data.get('motivo') or '').strip()
        if not motivo:
            return jsonify({'erro': 'Motivo do cancelamento e obrigatorio'}), 400

        from app.carvia.services.financeiro.previnculo_service import (
            CarviaPreVinculoService,
        )
        try:
            resultado = CarviaPreVinculoService.cancelar(
                previnculo_id, motivo, current_user.email,
            )
            db.session.commit()
            return jsonify(resultado)
        except ValueError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro cancelar previnculo {previnculo_id}: {e}')
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/previnculos/tentar-resolver-todos', methods=['POST'])  # type: ignore
    @login_required
    def api_tentar_resolver_todos_previnculos():  # type: ignore
        """Botao manual: varre pre-vinculos ATIVOS e tenta resolver contra
        faturas cliente dos ultimos 90 dias (casos tardios)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.services.financeiro.previnculo_service import (
            CarviaPreVinculoService,
        )
        try:
            resultado = CarviaPreVinculoService.tentar_resolver_todos_ativos(
                current_user.email,
            )
            db.session.commit()
            return jsonify(resultado)
        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro tentar_resolver_todos: {e}')
            return jsonify({'erro': str(e)}), 500
