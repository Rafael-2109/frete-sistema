"""
Rotas para processamento de arquivos CNAB400 (Retorno Bancário).

Funcionalidades:
- Upload de arquivos .ret
- Visualização de lotes e itens
- Matching automático com Contas a Receber
- Execução de baixas
- Análise de itens sem match
"""

import uuid
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from app import db
from app.financeiro.models import CnabRetornoLote, CnabRetornoItem, ContasAReceber
from app.financeiro.services.cnab400_processor_service import Cnab400ProcessorService


cnab400_bp = Blueprint('cnab400', __name__, url_prefix='/cnab400')


# =============================================================================
# VIEWS HTML
# =============================================================================

@cnab400_bp.route('/')
@login_required
def index():
    """Hub principal de CNAB400 - Lista de lotes"""
    lotes = CnabRetornoLote.query.order_by(
        CnabRetornoLote.data_processamento.desc()
    ).limit(50).all()

    # Estatísticas gerais
    stats = {
        'total_lotes': CnabRetornoLote.query.count(),
        'lotes_pendentes': CnabRetornoLote.query.filter(
            CnabRetornoLote.status.in_(['IMPORTADO', 'AGUARDANDO_REVISAO', 'APROVADO'])
        ).count(),
        'lotes_concluidos': CnabRetornoLote.query.filter(
            CnabRetornoLote.status == 'CONCLUIDO'
        ).count(),
    }

    return render_template(
        'financeiro/cnab400_hub.html',
        lotes=lotes,
        stats=stats
    )


@cnab400_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload de arquivo CNAB400"""
    if request.method == 'POST':
        # Verifica se arquivo foi enviado
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)

        arquivo = request.files['arquivo']

        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)

        # Verifica extensão
        if not arquivo.filename.lower().endswith('.ret'):
            flash('Arquivo deve ter extensão .ret', 'error')
            return redirect(request.url)

        try:
            # Lê conteúdo com encoding latin-1 (padrão CNAB)
            conteudo = arquivo.read().decode('latin-1')

            # Processa arquivo
            processor = Cnab400ProcessorService()
            lote = processor.processar_arquivo(
                arquivo_conteudo=conteudo,
                arquivo_nome=secure_filename(arquivo.filename),
                usuario=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
            )

            flash(
                f'Arquivo processado com sucesso! '
                f'{lote.total_registros} registros importados, '
                f'{lote.registros_com_match} com match, '
                f'{lote.registros_sem_match} sem match.',
                'success'
            )
            return redirect(url_for('cnab400.lote_detalhe', lote_id=lote.id))

        except Exception as e:
            flash(f'Erro ao processar arquivo: {str(e)}', 'error')
            return redirect(request.url)

    return render_template('financeiro/cnab400_upload.html')


@cnab400_bp.route('/lote/<int:lote_id>')
@login_required
def lote_detalhe(lote_id):
    """Detalhes de um lote processado"""
    lote = CnabRetornoLote.query.get_or_404(lote_id)

    # Buscar itens agrupados por status
    itens = CnabRetornoItem.query.filter_by(lote_id=lote_id).order_by(
        CnabRetornoItem.numero_linha
    ).all()

    # Estatísticas locais
    stats = {
        'total': len(itens),
        'liquidados': sum(1 for i in itens if i.codigo_ocorrencia == '06'),
        'confirmados': sum(1 for i in itens if i.codigo_ocorrencia == '02'),
        'baixados': sum(1 for i in itens if i.codigo_ocorrencia in ('09', '10')),
        'com_match': sum(1 for i in itens if i.status_match == 'MATCH_ENCONTRADO'),
        'sem_match': sum(1 for i in itens if i.status_match == 'SEM_MATCH'),
        'ja_pagos': sum(1 for i in itens if i.status_match == 'JA_PAGO'),
        'nao_aplicavel': sum(1 for i in itens if i.status_match == 'NAO_APLICAVEL'),
        'processados': sum(1 for i in itens if i.processado),
        'valor_liquidado': sum(
            float(i.valor_pago or i.valor_titulo or 0)
            for i in itens if i.codigo_ocorrencia == '06' and i.status_match == 'MATCH_ENCONTRADO'
        ),
        # Estatísticas de extrato (Fase 2)
        'extrato_vinculados': sum(1 for i in itens if i.status_match_extrato == 'MATCH_ENCONTRADO'),
        'extrato_sem_match': sum(1 for i in itens if i.status_match_extrato == 'SEM_MATCH'),
        'extrato_conciliados': sum(1 for i in itens if i.status_match_extrato == 'CONCILIADO'),
    }

    return render_template(
        'financeiro/cnab400_lote_detalhe.html',
        lote=lote,
        itens=itens,
        stats=stats
    )


@cnab400_bp.route('/lote/<int:lote_id>/sem-match')
@login_required
def lote_sem_match(lote_id):
    """Lista itens sem match para análise"""
    lote = CnabRetornoLote.query.get_or_404(lote_id)

    processor = Cnab400ProcessorService()
    itens = processor.obter_itens_sem_match(lote_id)

    return render_template(
        'financeiro/cnab400_sem_match.html',
        lote=lote,
        itens=itens
    )


# =============================================================================
# APIs JSON
# =============================================================================

@cnab400_bp.route('/api/lotes')
@login_required
def api_listar_lotes():
    """API: Lista lotes com paginação"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = CnabRetornoLote.query.order_by(CnabRetornoLote.data_processamento.desc())

    # Filtros opcionais
    status = request.args.get('status')
    if status:
        query = query.filter(CnabRetornoLote.status == status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'lotes': [lote.to_dict() for lote in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
    })


@cnab400_bp.route('/api/lote/<int:lote_id>')
@login_required
def api_lote_detalhe(lote_id):
    """API: Detalhes de um lote"""
    lote = CnabRetornoLote.query.get_or_404(lote_id)

    processor = Cnab400ProcessorService()
    stats = processor.obter_estatisticas_lote(lote)

    return jsonify({
        'success': True,
        'data': stats
    })


@cnab400_bp.route('/api/lote/<int:lote_id>/itens')
@login_required
def api_lote_itens(lote_id):
    """API: Itens de um lote"""
    lote = CnabRetornoLote.query.get_or_404(lote_id)

    # Filtros
    status_match = request.args.get('status_match')
    codigo_ocorrencia = request.args.get('codigo_ocorrencia')

    query = CnabRetornoItem.query.filter_by(lote_id=lote_id)

    if status_match:
        query = query.filter(CnabRetornoItem.status_match == status_match)
    if codigo_ocorrencia:
        query = query.filter(CnabRetornoItem.codigo_ocorrencia == codigo_ocorrencia)

    itens = query.order_by(CnabRetornoItem.numero_linha).all()

    return jsonify({
        'success': True,
        'itens': [item.to_dict() for item in itens],
        'total': len(itens)
    })


@cnab400_bp.route('/api/lote/<int:lote_id>/baixar', methods=['POST'])
@login_required
def api_baixar_lote(lote_id):
    """
    API: Executa baixa UNIFICADA de todos os itens com match do lote.

    Esta versão estendida (Fase 2) executa:
    1. Baixa de títulos (ContasAReceber.parcela_paga = True)
    2. Conciliação de extrato (ExtratoItem.status = 'CONCILIADO')
    3. Reconciliação no Odoo (se disponível)
    """
    lote = CnabRetornoLote.query.get_or_404(lote_id)

    # Verifica status
    if lote.status not in ('IMPORTADO', 'AGUARDANDO_REVISAO', 'APROVADO'):
        return jsonify({
            'success': False,
            'error': f'Lote com status {lote.status} não pode ser processado'
        }), 400

    try:
        processor = Cnab400ProcessorService()
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        # Usa versão unificada que baixa título + extrato + Odoo
        stats = processor.baixar_lote_unificado(lote, usuario=usuario)

        # Mensagem detalhada
        mensagem_partes = [f'{stats["sucesso"]} baixas']
        if stats.get('extratos_conciliados', 0) > 0:
            mensagem_partes.append(f'{stats["extratos_conciliados"]} extratos conciliados')
        if stats.get('odoo_reconciliados', 0) > 0:
            mensagem_partes.append(f'{stats["odoo_reconciliados"]} reconciliados no Odoo')
        if stats['erros'] > 0:
            mensagem_partes.append(f'{stats["erros"]} erros')

        return jsonify({
            'success': True,
            'message': f'Processamento concluído: {", ".join(mensagem_partes)}',
            'stats': stats,
            'lote': lote.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cnab400_bp.route('/api/lote/<int:lote_id>/matching-extrato', methods=['POST'])
@login_required
def api_matching_extrato_lote(lote_id):
    """
    API: Executa matching com extrato para todos os itens do lote.

    Deve ser chamado APÓS o matching de títulos.
    Vincula itens CNAB com linhas de ExtratoItem por Data + Valor + CNPJ.
    """
    lote = CnabRetornoLote.query.get_or_404(lote_id)

    try:
        processor = Cnab400ProcessorService()
        stats = processor.executar_matching_extrato_lote(lote)

        return jsonify({
            'success': True,
            'message': f'{stats["com_match"]} extratos vinculados, {stats["sem_match"]} sem match',
            'stats': stats,
            'lote': lote.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cnab400_bp.route('/api/lote/<int:lote_id>/reprocessar-matching', methods=['POST'])
@login_required
def api_reprocessar_matching(lote_id):
    """API: Reprocessa matching dos itens sem match"""
    lote = CnabRetornoLote.query.get_or_404(lote_id)

    try:
        processor = Cnab400ProcessorService()
        stats = processor.reprocessar_matching(lote)

        return jsonify({
            'success': True,
            'message': f'{stats["novos_matches"]} novos matches encontrados',
            'stats': stats,
            'lote': lote.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cnab400_bp.route('/api/item/<int:item_id>/baixar', methods=['POST'])
@login_required
def api_baixar_item(item_id):
    """
    API: Executa baixa UNIFICADA de um item específico.

    Esta versão estendida (Fase 2) executa:
    1. Baixa do título (ContasAReceber.parcela_paga = True)
    2. Conciliação do extrato vinculado (se houver)
    3. Reconciliação no Odoo (se disponível)
    """
    item = CnabRetornoItem.query.get_or_404(item_id)

    if item.status_match != 'MATCH_ENCONTRADO':
        return jsonify({
            'success': False,
            'error': f'Item com status {item.status_match} não pode ser baixado'
        }), 400

    try:
        processor = Cnab400ProcessorService()
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        # Usa versão unificada que baixa título + extrato + Odoo
        resultado = processor.baixar_titulo_e_extrato(item, usuario=usuario)

        if resultado['success']:
            # Mensagem detalhada
            detalhes = []
            if resultado['titulo']:
                detalhes.append('título baixado')
            if resultado['extrato']:
                detalhes.append('extrato conciliado')
            if resultado['odoo']:
                detalhes.append('Odoo reconciliado')

            return jsonify({
                'success': True,
                'message': f'Baixa executada: {", ".join(detalhes)}',
                'resultado': resultado,
                'item': item.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('mensagem', 'Erro desconhecido')
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cnab400_bp.route('/api/item/<int:item_id>/vincular', methods=['POST'])
@login_required
def api_vincular_item(item_id):
    """API: Vincula manualmente um item a um título"""
    item = CnabRetornoItem.query.get_or_404(item_id)

    data = request.get_json()
    titulo_id = data.get('titulo_id')

    if not titulo_id:
        return jsonify({
            'success': False,
            'error': 'titulo_id é obrigatório'
        }), 400

    titulo = ContasAReceber.query.get(titulo_id)
    if not titulo:
        return jsonify({
            'success': False,
            'error': 'Título não encontrado'
        }), 404

    try:
        item.conta_a_receber_id = titulo_id
        item.status_match = 'MATCH_ENCONTRADO'
        item.match_score = 100
        item.match_criterio = 'VINCULACAO_MANUAL'
        item.erro_mensagem = None

        # Atualizar estatísticas do lote
        item.lote.atualizar_estatisticas()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Item vinculado com sucesso',
            'item': item.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cnab400_bp.route('/api/buscar-titulos')
@login_required
def api_buscar_titulos():
    """API: Busca títulos para vinculação manual"""
    nf = request.args.get('nf', '').strip()
    parcela = request.args.get('parcela', '').strip()
    cnpj = request.args.get('cnpj', '').strip()
    valor = request.args.get('valor', type=float)

    query = ContasAReceber.query.filter(ContasAReceber.parcela_paga == False)

    if nf:
        query = query.filter(ContasAReceber.titulo_nf.ilike(f'%{nf}%'))
    if parcela:
        query = query.filter(ContasAReceber.parcela == parcela)
    if cnpj:
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        query = query.filter(ContasAReceber.cnpj.ilike(f'%{cnpj_limpo}%'))
    if valor:
        # Tolerância de 1%
        tolerancia = valor * 0.01
        query = query.filter(
            ContasAReceber.valor_titulo.between(valor - tolerancia, valor + tolerancia)
        )

    titulos = query.limit(50).all()

    return jsonify({
        'success': True,
        'titulos': [
            {
                'id': t.id,
                'empresa': t.empresa,
                'titulo_nf': t.titulo_nf,
                'parcela': t.parcela,
                'cnpj': t.cnpj,
                'raz_social_red': t.raz_social_red,
                'valor_titulo': float(t.valor_titulo) if t.valor_titulo else None,
                'vencimento': t.vencimento.isoformat() if t.vencimento else None,
            }
            for t in titulos
        ],
        'total': len(titulos)
    })


@cnab400_bp.route('/api/lote/<int:lote_id>/excluir', methods=['DELETE'])
@login_required
def api_excluir_lote(lote_id):
    """API: Exclui um lote e seus itens"""
    lote = CnabRetornoLote.query.get_or_404(lote_id)

    # Verifica se pode excluir (não pode excluir se já tem itens processados)
    itens_processados = CnabRetornoItem.query.filter_by(
        lote_id=lote_id,
        processado=True
    ).count()

    if itens_processados > 0:
        return jsonify({
            'success': False,
            'error': f'Não é possível excluir: {itens_processados} itens já foram processados'
        }), 400

    try:
        # O cascade delete cuida dos itens
        db.session.delete(lote)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Lote excluído com sucesso'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# SINCRONIZAÇÃO DE EXTRATOS
# =============================================================================

@cnab400_bp.route('/api/sincronizar-extratos', methods=['POST'])
@login_required
def api_sincronizar_extratos():
    """
    API: Sincroniza extratos pendentes com baixas já realizadas (CNAB/Odoo).

    Parâmetros JSON (opcionais):
        janela_minutos: Janela de tempo para buscar extratos (default 120)
        limite: Limite de registros (default 500)

    Retorna:
        JSON com estatísticas da sincronização
    """
    from app.financeiro.services.sincronizacao_extratos_service import SincronizacaoExtratosService

    try:
        data = request.get_json() or {}
        janela_minutos = data.get('janela_minutos', 120)
        limite = data.get('limite', 500)

        service = SincronizacaoExtratosService()
        resultado = service.sincronizar_extratos_pendentes(
            janela_minutos=janela_minutos,
            limite=limite
        )

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cnab400_bp.route('/api/lote/<int:lote_id>/sincronizar-extratos', methods=['POST'])
@login_required
def api_sincronizar_extratos_lote(lote_id):
    """
    API: Sincroniza extratos especificamente para itens de um lote CNAB.

    Útil após processar baixas para garantir que extratos
    correspondentes sejam atualizados.
    """
    from app.financeiro.services.sincronizacao_extratos_service import SincronizacaoExtratosService

    try:
        lote = CnabRetornoLote.query.get_or_404(lote_id)

        service = SincronizacaoExtratosService()
        resultado = service.sincronizar_extratos_por_cnab(lote_id=lote_id)

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cnab400_bp.route('/api/revalidar-extratos', methods=['POST'])
@login_required
def api_revalidar_extratos():
    """
    API: Revalida TODOS os extratos pendentes (sem limite de janela).

    ⚠️ CUIDADO: Pode ser lento em bases grandes.
    Use apenas em situações de manutenção ou primeira execução.
    """
    from app.financeiro.services.sincronizacao_extratos_service import SincronizacaoExtratosService

    try:
        service = SincronizacaoExtratosService()
        resultado = service.revalidar_todos_extratos_pendentes()

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# UPLOAD EM BATCH (MÚLTIPLOS ARQUIVOS)
# =============================================================================

@cnab400_bp.route('/api/upload-batch', methods=['POST'])
@login_required
def api_upload_batch():
    """
    API: Upload de múltiplos arquivos CNAB400 para processamento assíncrono.

    Aceita N arquivos .ret via multipart/form-data.
    Enfileira job no Redis Queue e retorna batch_id para acompanhamento.

    Parâmetros:
        arquivos: Lista de arquivos .ret (via request.files.getlist)

    Retorna:
        JSON com batch_id, job_id e total de arquivos enfileirados
    """
    from app.portal.workers import enqueue_job
    from app.financeiro.workers.cnab400_batch_jobs import processar_batch_cnab400_job

    # Verificar se arquivos foram enviados
    arquivos = request.files.getlist('arquivos')

    if not arquivos or len(arquivos) == 0:
        return jsonify({
            'success': False,
            'error': 'Nenhum arquivo enviado'
        }), 400

    # Verificar se pelo menos um arquivo é válido
    arquivos_validos = [
        a for a in arquivos
        if a.filename and a.filename.lower().endswith('.ret')
    ]

    if not arquivos_validos:
        return jsonify({
            'success': False,
            'error': 'Nenhum arquivo válido (.ret) enviado'
        }), 400

    try:
        # Gerar batch_id único
        batch_id = str(uuid.uuid4())

        # Preparar dados dos arquivos (ler conteúdo antes de enfileirar)
        arquivos_data = []
        for arquivo in arquivos_validos:
            try:
                conteudo = arquivo.read().decode('latin-1')
                arquivos_data.append({
                    'nome': secure_filename(arquivo.filename),
                    'conteudo': conteudo
                })
            except Exception as e:
                # Se não conseguir ler um arquivo, ignorar e continuar
                pass

        if not arquivos_data:
            return jsonify({
                'success': False,
                'error': 'Não foi possível ler nenhum arquivo'
            }), 400

        # Nome do usuário para registro
        usuario_nome = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        # Enfileirar job
        job = enqueue_job(
            processar_batch_cnab400_job,
            batch_id,
            arquivos_data,
            usuario_nome,
            queue_name='default',
            timeout='30m'  # 30 minutos
        )

        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'job_id': job.id if job else None,
            'total_arquivos': len(arquivos_data),
            'arquivos': [a['nome'] for a in arquivos_data],
            'message': f'{len(arquivos_data)} arquivo(s) enfileirado(s) para processamento'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao enfileirar processamento: {str(e)}'
        }), 500


@cnab400_bp.route('/api/batch/<batch_id>/status')
@login_required
def api_batch_status(batch_id):
    """
    API: Retorna status de um batch de arquivos CNAB400.

    Consulta primeiro o Redis (progresso em tempo real) e depois o banco.

    Parâmetros:
        batch_id: UUID do batch

    Retorna:
        JSON com status completo do batch, incluindo:
        - status: 'processando' | 'concluido' | 'erro' | 'parcial' | 'nao_encontrado'
        - total_arquivos, arquivos_processados, arquivos_sucesso, arquivos_erro
        - lotes: lista de lotes criados com seus IDs e status
    """
    from app.financeiro.workers.cnab400_batch_jobs import verificar_status_batch

    try:
        resultado = verificar_status_batch(batch_id)
        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'success': False,
            'batch_id': batch_id,
            'status': 'erro',
            'error': str(e)
        }), 500


@cnab400_bp.route('/api/batch/<batch_id>/arquivos')
@login_required
def api_batch_arquivos(batch_id):
    """
    API: Retorna lista detalhada dos arquivos de um batch.

    Busca lotes no banco que possuem o batch_id especificado.

    Parâmetros:
        batch_id: UUID do batch

    Retorna:
        JSON com lista de lotes e seus detalhes
    """
    try:
        lotes = CnabRetornoLote.query.filter_by(batch_id=batch_id).order_by(
            CnabRetornoLote.data_processamento.asc()
        ).all()

        if not lotes:
            return jsonify({
                'success': True,
                'batch_id': batch_id,
                'total': 0,
                'lotes': [],
                'message': 'Nenhum lote encontrado para este batch'
            })

        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'total': len(lotes),
            'lotes': [lote.to_dict() for lote in lotes]
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
