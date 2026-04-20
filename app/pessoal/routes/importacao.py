"""Rotas de importacao de CSV — upload e processamento multi-file com auto-detect."""
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user

from app import db
from app.pessoal import pode_acessar_pessoal
from app.pessoal.models import PessoalConta, PessoalImportacao, PessoalTransacao
from app.pessoal.forms import ImportarCSVForm
from app.pessoal.services.parsers.base_parser import (
    gerar_hash_transacao, detectar_tipo_csv, resolver_conta, normalizar_historico,
    extrair_cpf_cnpj,
)
from app.pessoal.services.parsers.bradesco_cc_parser import BradescoExtratoCC
from app.pessoal.services.parsers.bradesco_cartao_parser import BradescoFaturaCartao
from app.pessoal.services.categorizacao_service import categorizar_transacao, atribuir_membro

importacao_bp = Blueprint('pessoal_importacao', __name__)


@importacao_bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar():
    """Upload e processamento de CSVs Bradesco (multi-file, auto-detect)."""
    if not pode_acessar_pessoal(current_user):
        flash('Acesso restrito.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = ImportarCSVForm()
    resultados = []

    if request.method == 'POST':
        arquivos = request.files.getlist('arquivos')
        ano_referencia = request.form.get('ano_referencia', type=int)

        # Filtrar arquivos validos (nao-vazios, .csv)
        arquivos_validos = [
            a for a in arquivos
            if a and a.filename and a.filename.lower().endswith('.csv')
        ]

        if not arquivos_validos:
            flash('Selecione pelo menos um arquivo CSV.', 'warning')
        else:
            total_importadas = 0
            total_duplicadas = 0
            total_erros = 0

            for arquivo in arquivos_validos:
                resultado = _processar_um_arquivo(arquivo, ano_referencia)
                resultados.append(resultado)

                if resultado['sucesso']:
                    total_importadas += resultado['importadas']
                    total_duplicadas += resultado['duplicadas']
                else:
                    total_erros += 1

            # Flash resumo geral
            if len(arquivos_validos) > 1:
                if total_erros == 0:
                    flash(
                        f'{len(arquivos_validos)} arquivos processados: '
                        f'{total_importadas} transacoes importadas, '
                        f'{total_duplicadas} duplicadas ignoradas.',
                        'success',
                    )
                else:
                    flash(
                        f'{len(arquivos_validos)} arquivos processados: '
                        f'{len(arquivos_validos) - total_erros} com sucesso, '
                        f'{total_erros} com erro.',
                        'warning',
                    )
            elif len(arquivos_validos) == 1 and resultados[0]['sucesso']:
                r = resultados[0]
                flash(
                    f'Importacao concluida: {r["importadas"]} transacoes importadas, '
                    f'{r["duplicadas"]} duplicadas ignoradas, '
                    f'{r["filtradas_empresa"]} empresariais filtradas.',
                    'success',
                )

    # Historico de importacoes
    importacoes = PessoalImportacao.query.order_by(
        PessoalImportacao.criado_em.desc()
    ).limit(20).all()

    return render_template(
        'pessoal/importar.html',
        form=form,
        resultados=resultados,
        importacoes=importacoes,
    )


def _processar_um_arquivo(arquivo, ano_referencia: int = None) -> dict:
    """Processa um unico arquivo CSV. Retorna dict com resultado.

    Fluxo:
    1. Ler conteudo (latin-1)
    2. detectar_tipo_csv() -> ResultadoDeteccao
    3. resolver_conta() -> conta_id
    4. _parsear_conteudo() -> (tipo_arquivo, transacoes_raw, parser)
    5. _importar_transacoes() -> resultado

    Args:
        ano_referencia: ano a usar quando datas no CSV sao DD/MM (sem ano).
    """
    nome_arquivo = arquivo.filename

    try:
        # Ler conteudo com latin-1 (padrao Bradesco)
        conteudo_bytes = arquivo.read()
        conteudo = conteudo_bytes.decode('latin-1')

        # Auto-detectar tipo
        deteccao = detectar_tipo_csv(conteudo)

        if deteccao.tipo == 'desconhecido':
            return {
                'sucesso': False,
                'arquivo': nome_arquivo,
                'erro': (
                    'Formato nao reconhecido. '
                    'O arquivo nao parece ser extrato CC nem fatura de cartao Bradesco.'
                ),
            }

        # Resolver conta automaticamente
        conta_id = resolver_conta(deteccao)
        if conta_id is None:
            if deteccao.tipo == 'extrato_cc':
                detalhe = (
                    f'Conta corrente nao identificada '
                    f'(agencia: {deteccao.agencia or "?"}, conta: {deteccao.conta or "?"}).'
                )
            else:
                detalhe = (
                    f'Cartao nao identificado '
                    f'(digitos: {", ".join(deteccao.digitos_cartao) if deteccao.digitos_cartao else "?"}).'
                )
            return {
                'sucesso': False,
                'arquivo': nome_arquivo,
                'erro': f'Conta nao encontrada. {detalhe} Cadastre a conta antes de importar.',
            }

        conta = db.session.get(PessoalConta, conta_id)
        if not conta:
            return {
                'sucesso': False,
                'arquivo': nome_arquivo,
                'erro': 'Conta resolvida nao existe no banco de dados.',
            }

        # Parsear conteudo
        tipo_arquivo, transacoes_raw, parser = _parsear_conteudo(
            conteudo, deteccao.tipo, ano_referencia
        )

        if not transacoes_raw:
            return {
                'sucesso': False,
                'arquivo': nome_arquivo,
                'erro': 'Nenhuma transacao encontrada no arquivo.',
            }

        # Importar transacoes (commit per-file)
        return _importar_transacoes(nome_arquivo, tipo_arquivo, conta, transacoes_raw, parser)

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return {
            'sucesso': False,
            'arquivo': nome_arquivo,
            'erro': f'Erro ao processar: {str(e)}',
        }


def _parsear_conteudo(conteudo: str, tipo: str, ano_referencia: int = None) -> tuple:
    """Instancia o parser correto e parseia.

    Retorna (tipo_arquivo, transacoes_raw, parser).
    O parser e retornado junto para acessar atributos como parser.situacao
    sem precisar parsear 2 vezes.

    Args:
        ano_referencia: ano a usar quando datas no CSV sao DD/MM (sem ano).
    """
    if tipo == 'fatura_cartao':
        parser = BradescoFaturaCartao()
        transacoes = parser.parsear(conteudo, ano_referencia=ano_referencia)
        return ('fatura_cartao', transacoes, parser)

    # Default: extrato CC
    parser = BradescoExtratoCC()
    transacoes = parser.parsear(conteudo, ano_referencia=ano_referencia)
    return ('extrato_cc', transacoes, parser)


def _importar_transacoes(nome_arquivo: str, tipo_arquivo: str, conta, transacoes_raw, parser) -> dict:
    """Cria PessoalImportacao + PessoalTransacoes. Commit per-file.

    Retorna dict resultado com metricas.
    """
    conta_id = conta.id

    # Criar registro de importacao
    importacao = PessoalImportacao(
        conta_id=conta_id,
        nome_arquivo=nome_arquivo,
        tipo_arquivo=tipo_arquivo,
        total_linhas=len(transacoes_raw),
        criado_por=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id),
    )

    # Extrair periodo
    datas = [t.data for t in transacoes_raw if t.data]
    if datas:
        importacao.periodo_inicio = min(datas)
        importacao.periodo_fim = max(datas)

    # Se cartao, extrair situacao do parser (ja parseado, sem re-parse)
    if tipo_arquivo == 'fatura_cartao' and hasattr(parser, 'situacao'):
        importacao.situacao_fatura = parser.situacao

    db.session.add(importacao)
    db.session.flush()  # Obter ID

    # Processar transacoes
    importadas = 0
    duplicadas = 0
    filtradas_empresa = 0

    # Contador para diferenciar transacoes identicas no mesmo dia (dedup)
    contagem_chaves = {}

    for t_raw in transacoes_raw:
        # Gerar chave base para contagem de sequencia
        chave_base = f"{conta_id}|{t_raw.data.isoformat()}|{normalizar_historico(t_raw.historico)}|{t_raw.valor}|{t_raw.tipo}|{t_raw.documento or ''}"
        seq = contagem_chaves.get(chave_base, 0)
        contagem_chaves[chave_base] = seq + 1

        # Gerar hash para deduplicacao (sequencia diferencia transacoes identicas)
        hash_t = gerar_hash_transacao(
            conta_id, t_raw.data, t_raw.historico,
            t_raw.valor, t_raw.tipo, t_raw.documento or '', sequencia=seq
        )

        # Verificar duplicata
        existente = PessoalTransacao.query.filter_by(hash_transacao=hash_t).first()
        if existente:
            duplicadas += 1
            continue

        # F1: extrair CPF/CNPJ do historico + descricao (fonte mais ampla)
        fonte_cpf = ' '.join(filter(None, [
            t_raw.historico_completo, t_raw.historico, t_raw.descricao,
        ]))
        cpf_cnpj = extrair_cpf_cnpj(fonte_cpf) if fonte_cpf else None

        # Criar transacao
        transacao = PessoalTransacao(
            importacao_id=importacao.id,
            conta_id=conta_id,
            data=t_raw.data,
            historico=t_raw.historico,
            descricao=t_raw.descricao,
            historico_completo=t_raw.historico_completo,
            documento=t_raw.documento,
            valor=t_raw.valor,
            tipo=t_raw.tipo,
            saldo=t_raw.saldo,
            valor_dolar=t_raw.valor_dolar,
            parcela_atual=t_raw.parcela_atual,
            parcela_total=t_raw.parcela_total,
            identificador_parcela=t_raw.identificador_parcela,
            cpf_cnpj_parte=cpf_cnpj,
            hash_transacao=hash_t,
        )

        db.session.add(transacao)
        db.session.flush()

        # Categorizar
        resultado_cat = categorizar_transacao(transacao)
        transacao.categoria_id = resultado_cat.categoria_id
        transacao.regra_id = resultado_cat.regra_id
        transacao.categorizacao_auto = resultado_cat.categorizacao_auto
        transacao.categorizacao_confianca = resultado_cat.categorizacao_confianca
        transacao.excluir_relatorio = resultado_cat.excluir_relatorio
        transacao.eh_pagamento_cartao = resultado_cat.eh_pagamento_cartao
        transacao.eh_transferencia_propria = resultado_cat.eh_transferencia_propria
        transacao.status = resultado_cat.status

        if resultado_cat.excluir_relatorio:
            filtradas_empresa += 1

        # Atribuir membro
        membro_id, membro_auto = atribuir_membro(
            transacao,
            titular_cartao=t_raw.titular_cartao,
            ultimos_digitos=t_raw.ultimos_digitos_cartao,
        )
        transacao.membro_id = membro_id
        transacao.membro_auto = membro_auto

        importadas += 1

    # Atualizar estatisticas da importacao
    importacao.linhas_importadas = importadas
    importacao.linhas_duplicadas = duplicadas
    importacao.linhas_empresa_filtradas = filtradas_empresa

    db.session.commit()

    periodo = ''
    if importacao.periodo_inicio and importacao.periodo_fim:
        periodo = (
            f"{importacao.periodo_inicio.strftime('%d/%m/%Y')} a "
            f"{importacao.periodo_fim.strftime('%d/%m/%Y')}"
        )

    return {
        'sucesso': True,
        'importacao_id': importacao.id,
        'arquivo': nome_arquivo,
        'tipo': tipo_arquivo,
        'conta_nome': conta.nome,
        'total': len(transacoes_raw),
        'importadas': importadas,
        'duplicadas': duplicadas,
        'filtradas_empresa': filtradas_empresa,
        'periodo': periodo,
    }
