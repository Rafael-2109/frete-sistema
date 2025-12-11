# -*- coding: utf-8 -*-
"""
Rotas de Baixa de Titulos via Excel
===================================

Funcionalidades:
- Hub de baixas (listagem, filtros, selecao)
- Download do template Excel com journals
- Upload e validacao do Excel
- Deteccao de duplicidades (warning, nao bloqueia)
- Ativar/inativar itens (individual ou em lote)
- Processamento das baixas no Odoo
- Auditoria completa

Autor: Sistema de Fretes
Data: 2025-12-10
Atualizado: 2025-12-11
"""

import hashlib
import unicodedata
from io import BytesIO
from datetime import datetime, date

from flask import render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
import pandas as pd

from app import db
from app.financeiro.routes import financeiro_bp
from app.financeiro.models import BaixaTituloLote, BaixaTituloItem


# =============================================================================
# CONSTANTES - JOURNALS DISPONIVEIS
# =============================================================================

# Mapeamento de journals por nome PT-BR (mais usados primeiro)
# Frequencia calculada de 01/07/2024 ate hoje (7431 pagamentos totais)
# Filtros: payment_type='inbound', state='posted'
# Contexto: lang='pt_BR' (nomes em portugues)
JOURNALS_DISPONIVEIS = [
    {'id': 883, 'code': 'GRA1', 'name': 'GRAFENO', 'type': 'bank', 'freq': 3473},
    {'id': 985, 'code': 'AGIS', 'name': 'AGIS', 'type': 'cash', 'freq': 798},
    {'id': 879, 'code': 'DEVOL', 'name': 'DEVOLUÇÃO', 'type': 'cash', 'freq': 556},
    {'id': 902, 'code': 'BNK1', 'name': 'Atacadao', 'type': 'cash', 'freq': 470},
    {'id': 10, 'code': 'SIC', 'name': 'SICOOB', 'type': 'bank', 'freq': 422},
    {'id': 980, 'code': 'SENDA', 'name': 'SENDAS(ASSAI)', 'type': 'cash', 'freq': 307},
    {'id': 885, 'code': 'ACORD', 'name': 'ACORDO COMERCIAL', 'type': 'cash', 'freq': 242},
    {'id': 388, 'code': 'BRAD', 'name': 'BRADESCO', 'type': 'bank', 'freq': 222},
    {'id': 966, 'code': 'WMS', 'name': 'WMS', 'type': 'cash', 'freq': 202},
    {'id': 886, 'code': 'DESCO', 'name': 'DESCONTO CONCEDIDO', 'type': 'cash', 'freq': 161},
    {'id': 968, 'code': 'TENDA', 'name': 'TENDA', 'type': 'cash', 'freq': 133},
    {'id': 1020, 'code': 'SOGIM', 'name': 'SOGIMA SECURITIZADORA', 'type': 'cash', 'freq': 98},
    {'id': 386, 'code': 'SIC', 'name': 'SICOOB', 'type': 'bank', 'freq': 63},
    {'id': 975, 'code': 'DVA -', 'name': 'DVA - B2M - TACADAO DIA A DIA', 'type': 'cash', 'freq': 59},
    {'id': 976, 'code': 'Merc.', 'name': 'Merc. Ataca', 'type': 'cash', 'freq': 43},
    {'id': 1030, 'code': 'SANT', 'name': 'SANTANDER', 'type': 'bank', 'freq': 30},
    {'id': 967, 'code': 'WMB', 'name': 'WMB', 'type': 'cash', 'freq': 23},
    {'id': 982, 'code': 'Cenco', 'name': 'Cencosud/ Merc. Rodrigues', 'type': 'cash', 'freq': 19},
    {'id': 1056, 'code': 'NG', 'name': 'NG PROMOÇÕES', 'type': 'cash', 'freq': 18},
    {'id': 984, 'code': 'Oesa', 'name': 'Oesa', 'type': 'cash', 'freq': 16},
    {'id': 1057, 'code': 'FORT', 'name': 'GRUPO FORT ATAC', 'type': 'cash', 'freq': 11},
    {'id': 1032, 'code': 'SIC1', 'name': 'CARTÃO DE CRÉDITO - SICOOB', 'type': 'bank', 'freq': 9},
    {'id': 972, 'code': 'SDB', 'name': 'SDB', 'type': 'cash', 'freq': 6},
    {'id': 981, 'code': 'Zarag', 'name': 'Zaragoza', 'type': 'cash', 'freq': 5},
    {'id': 971, 'code': 'Ataka', 'name': 'Atakarejo', 'type': 'cash', 'freq': 4},
    {'id': 1046, 'code': 'AGISG', 'name': 'AGIS GARANTIDA', 'type': 'bank', 'freq': 2},
    {'id': 1018, 'code': 'BRAD1', 'name': 'BRADESCO APLICAÇÃO AUTOMATICA', 'type': 'bank', 'freq': 2},
    {'id': 974, 'code': 'ROLDA', 'name': 'ROLDAO', 'type': 'cash', 'freq': 2},
    {'id': 1055, 'code': 'SRMG', 'name': 'SRM GARANTIDA', 'type': 'bank', 'freq': 2},
    {'id': 1054, 'code': 'VORTX', 'name': 'VORTX', 'type': 'bank', 'freq': 2},
    {'id': 389, 'code': 'CAIXA', 'name': 'CAIXA ECONÔMICA', 'type': 'bank', 'freq': 1},
    {'id': 1061, 'code': 'GRA2', 'name': 'GRAFENO 2', 'type': 'bank', 'freq': 1},
    {'id': 973, 'code': 'STO A', 'name': 'STO ATAC DE ALIM EIRELI', 'type': 'cash', 'freq': 1},
    # Journals sem uso no periodo (freq = 0)
    {'id': 1040, 'code': 'CSH2', 'name': 'ADIANTAMENTOS A FORNECEDORES', 'type': 'cash', 'freq': 0},
    {'id': 1064, 'code': 'ADTO', 'name': 'ADIANTAMENTOS DE FORNECEDORES NACIONAIS', 'type': 'cash', 'freq': 0},
    {'id': 1017, 'code': 'ADDES', 'name': 'ADIANTAMENTOS DESPACHANTE ADUANEIRO', 'type': 'cash', 'freq': 0},
    {'id': 1015, 'code': 'ADTEX', 'name': 'ADIANTAMENTOS FORNECEDORES EXTERIOR', 'type': 'cash', 'freq': 0},
    {'id': 1058, 'code': 'APLIC', 'name': 'APLICAÇÃO SANTANDER', 'type': 'bank', 'freq': 0},
    {'id': 969, 'code': 'ARMAZ', 'name': 'ARMAZEM MATEUS SA', 'type': 'cash', 'freq': 0},
    {'id': 854, 'code': 'BRAD', 'name': 'BRADESCO', 'type': 'bank', 'freq': 0},
    {'id': 867, 'code': 'CSH1', 'name': 'CAIXA COMERCIAL - REATIVAR', 'type': 'cash', 'freq': 0},
    {'id': 6, 'code': 'CSH1', 'name': 'CAIXA COMERCIAL - REATIVAR', 'type': 'cash', 'freq': 0},
    {'id': 851, 'code': 'CAIXA', 'name': 'CAIXA ECONÔMICA', 'type': 'bank', 'freq': 0},
    {'id': 986, 'code': 'CLIEN', 'name': 'CLIENTE CESTA', 'type': 'cash', 'freq': 0},
    {'id': 1025, 'code': 'DESAG', 'name': 'DESAGIO', 'type': 'cash', 'freq': 0},
    {'id': 979, 'code': 'DICA/', 'name': 'DICA/OURO AZUL (RICOY)', 'type': 'cash', 'freq': 0},
    {'id': 978, 'code': 'GIGA', 'name': 'GIGA', 'type': 'cash', 'freq': 0},
    {'id': 1062, 'code': 'Muff', 'name': 'Irmãos Muffato', 'type': 'cash', 'freq': 0},
    {'id': 970, 'code': 'MATEU', 'name': 'MATEUS SUP', 'type': 'cash', 'freq': 0},
    {'id': 977, 'code': 'Rede', 'name': 'Rede Confiança(JED ZOGHEIB)', 'type': 'cash', 'freq': 0},
    {'id': 983, 'code': 'Super', 'name': 'Supermercados Cavicchiolli', 'type': 'cash', 'freq': 0},
    {'id': 4, 'code': 'VARCA', 'name': 'VARIAÇÃO CAMBIAL ATIVA', 'type': 'cash', 'freq': 0},
    {'id': 1016, 'code': 'VARCP', 'name': 'VARIAÇÃO CAMBIAL PASSIVA', 'type': 'cash', 'freq': 0},
]


# =============================================================================
# FUNCOES AUXILIARES - JOURNALS
# =============================================================================

def normalizar_texto(texto: str) -> str:
    """Remove acentos e converte para uppercase para comparacao."""
    if not texto:
        return ''
    texto_norm = unicodedata.normalize('NFD', texto)
    texto_sem_acento = ''.join(c for c in texto_norm if unicodedata.category(c) != 'Mn')
    return texto_sem_acento.upper().strip()


def _criar_dict_priorizado(journals: list, key_func) -> dict:
    """
    Cria dicionario priorizando journals com maior frequencia.
    Quando ha duplicatas de chave, mantem o journal com maior freq.
    """
    resultado = {}
    for j in journals:
        chave = key_func(j)
        if chave not in resultado or j['freq'] > resultado[chave]['freq']:
            resultado[chave] = j
    return resultado


# Criar dicionarios para busca rapida (priorizando maior frequencia)
JOURNAL_POR_NOME = _criar_dict_priorizado(JOURNALS_DISPONIVEIS, lambda j: j['name'].upper())
JOURNAL_POR_NOME_NORMALIZADO = _criar_dict_priorizado(JOURNALS_DISPONIVEIS, lambda j: normalizar_texto(j['name']))
JOURNAL_POR_CODIGO = _criar_dict_priorizado(JOURNALS_DISPONIVEIS, lambda j: j['code'].upper())
JOURNAL_POR_ID = {j['id']: j for j in JOURNALS_DISPONIVEIS}


def resolver_journal(nome_journal: str) -> dict:
    """
    Resolve o journal pelo nome, codigo ou ID.
    Retorna dict com id, code, name ou None se nao encontrar.
    """
    if not nome_journal:
        return None #type: ignore

    entrada = str(nome_journal).strip()
    entrada_upper = entrada.upper()
    entrada_norm = normalizar_texto(entrada)

    # 1. Busca exata por nome
    if entrada_upper in JOURNAL_POR_NOME:
        return JOURNAL_POR_NOME[entrada_upper]

    # 2. Busca por nome normalizado
    if entrada_norm in JOURNAL_POR_NOME_NORMALIZADO:
        return JOURNAL_POR_NOME_NORMALIZADO[entrada_norm]

    # 3. Busca por codigo
    if entrada_upper in JOURNAL_POR_CODIGO:
        return JOURNAL_POR_CODIGO[entrada_upper]

    # 4. Busca por ID
    if entrada.isdigit():
        journal_id = int(entrada)
        if journal_id in JOURNAL_POR_ID:
            return JOURNAL_POR_ID[journal_id]

    # 5. Busca parcial
    for nome_norm, journal in JOURNAL_POR_NOME_NORMALIZADO.items():
        if entrada_norm in nome_norm or nome_norm in entrada_norm:
            return journal

    return None #type: ignore


# =============================================================================
# FUNCOES AUXILIARES - DUPLICIDADE
# =============================================================================

def verificar_duplicidade_no_arquivo(itens_novos: list) -> dict:
    """
    Verifica duplicidades dentro do proprio arquivo.
    Retorna dict com chave (nf, parcela, valor) e lista de indices.
    """
    chaves_vistas = {}
    duplicados = set()

    for idx, item in enumerate(itens_novos):
        chave = (item['nf'], item['parcela'], item['valor'])
        if chave in chaves_vistas:
            duplicados.add(chaves_vistas[chave])
            duplicados.add(idx)
        else:
            chaves_vistas[chave] = idx

    return duplicados #type: ignore


def verificar_duplicidade_banco(nf: str, parcela: int, valor: float) -> bool:
    """
    Verifica se existe item identico ja processado com sucesso no banco.
    """
    existente = BaixaTituloItem.query.filter(
        BaixaTituloItem.nf_excel == nf,
        BaixaTituloItem.parcela_excel == parcela,
        BaixaTituloItem.valor_excel == valor,
        BaixaTituloItem.status == 'SUCESSO'
    ).first()

    return existente is not None


# =============================================================================
# HUB DE BAIXAS - LISTAGEM PRINCIPAL
# =============================================================================

@financeiro_bp.route('/contas-receber/baixas')
@login_required
def baixas_hub():
    """
    Hub de Baixa de Titulos via Excel.
    Listagem de itens com filtros, selecao e acoes.
    """
    # Capturar filtros
    filtro_lote = request.args.get('lote', type=int)
    filtro_status = request.args.get('status', '')
    filtro_ativo = request.args.get('ativo', '')
    filtro_nf = request.args.get('nf', '')

    # Query base
    query = BaixaTituloItem.query

    # Aplicar filtros
    if filtro_lote:
        query = query.filter(BaixaTituloItem.lote_id == filtro_lote)
    if filtro_status:
        query = query.filter(BaixaTituloItem.status == filtro_status)
    if filtro_ativo:
        query = query.filter(BaixaTituloItem.ativo == (filtro_ativo == '1'))
    if filtro_nf:
        query = query.filter(BaixaTituloItem.nf_excel.ilike(f'%{filtro_nf}%'))

    # Ordenar: mais recentes primeiro
    itens = query.order_by(
        BaixaTituloItem.criado_em.desc(),
        BaixaTituloItem.linha_excel.asc()
    ).limit(500).all()

    # Verificar duplicidades para cada item
    for item in itens:
        # Verifica se existe outro item identico
        outros = BaixaTituloItem.query.filter(
            BaixaTituloItem.nf_excel == item.nf_excel,
            BaixaTituloItem.parcela_excel == item.parcela_excel,
            BaixaTituloItem.valor_excel == item.valor_excel,
            BaixaTituloItem.id != item.id
        ).count()
        item.duplicidade = outros > 0

    # Buscar lotes para filtro
    lotes = BaixaTituloLote.query.order_by(BaixaTituloLote.criado_em.desc()).limit(20).all()

    # Estatisticas gerais
    stats = {
        'total': BaixaTituloItem.query.count(),
        'pendentes': BaixaTituloItem.query.filter_by(status='PENDENTE').count(),
        'validos': BaixaTituloItem.query.filter_by(status='VALIDO').count(),
        'invalidos': BaixaTituloItem.query.filter_by(status='INVALIDO').count(),
        'sucesso': BaixaTituloItem.query.filter_by(status='SUCESSO').count(),
        'erro': BaixaTituloItem.query.filter_by(status='ERRO').count(),
    }

    # IDs de todos os itens processaveis (para "Selecionar Todos")
    todos_ids = [i.id for i in BaixaTituloItem.query.filter(
        BaixaTituloItem.status.in_(['PENDENTE', 'VALIDO', 'ERRO']),
        BaixaTituloItem.ativo == True
    ).all()]

    return render_template(
        'financeiro/baixas_hub.html',
        itens=itens,
        lotes=lotes,
        stats=stats,
        todos_ids=todos_ids,
        filtro_lote=filtro_lote,
        filtro_status=filtro_status,
        filtro_ativo=filtro_ativo,
        filtro_nf=filtro_nf
    )


# =============================================================================
# DOWNLOAD DO TEMPLATE EXCEL
# =============================================================================

@financeiro_bp.route('/contas-receber/baixas/template')
@login_required
def baixas_download_template():
    """
    Gera e envia o template Excel para baixa de titulos.
    """
    try:
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Aba 1: Baixas (template para preenchimento)
            df_baixas = pd.DataFrame({
                'NF': ['92234', '92235', '92236'],
                'PARCELA': [1, 1, 2],
                'VALOR': [1500.00, 2000.00, 3500.50],
                'JOURNAL': ['GRAFENO', 'DEVOLUCAO', 'SICOOB'],
                'DATA': [date.today().strftime('%Y-%m-%d')] * 3
            })
            df_baixas.to_excel(writer, index=False, sheet_name='Baixas')

            ws_baixas = writer.sheets['Baixas']
            for col in ws_baixas.columns:
                column_letter = col[0].column_letter
                ws_baixas.column_dimensions[column_letter].width = 15

            # Aba 2: Journals (referencia)
            df_journals = pd.DataFrame([
                {
                    'NOME_JOURNAL': j['name'],
                    'CODIGO': j['code'],
                    'TIPO': 'Banco' if j['type'] == 'bank' else 'Caixa',
                    'FREQUENCIA': j['freq'] if j['freq'] > 0 else '-'
                }
                for j in JOURNALS_DISPONIVEIS
            ])
            df_journals.to_excel(writer, index=False, sheet_name='Journals')

            ws_journals = writer.sheets['Journals']
            ws_journals.column_dimensions['A'].width = 40
            ws_journals.column_dimensions['B'].width = 12
            ws_journals.column_dimensions['C'].width = 10
            ws_journals.column_dimensions['D'].width = 12

        output.seek(0)
        filename = f'template_baixa_titulos_{date.today().strftime("%Y%m%d")}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        flash(f'Erro ao gerar template: {str(e)}', 'danger')
        return redirect(url_for('financeiro.baixas_hub'))


# =============================================================================
# UPLOAD DO EXCEL
# =============================================================================

@financeiro_bp.route('/contas-receber/baixas/upload', methods=['POST'])
@login_required
def baixas_upload():
    """
    Recebe o arquivo Excel e cria o lote de importacao.
    Detecta duplicidades (warning, nao bloqueia).
    """
    try:
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']

        if arquivo.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400

        if not arquivo.filename.endswith('.xlsx'):
            return jsonify({'success': False, 'error': 'Arquivo deve ser .xlsx'}), 400

        # Ler arquivo
        conteudo = arquivo.read()
        hash_arquivo = hashlib.sha256(conteudo).hexdigest()

        # Verificar se ja foi importado
        lote_existente = BaixaTituloLote.query.filter_by(hash_arquivo=hash_arquivo).first()
        if lote_existente:
            return jsonify({
                'success': False,
                'error': f'Este arquivo ja foi importado (Lote #{lote_existente.id})'
            }), 400

        # Ler Excel
        df = pd.read_excel(BytesIO(conteudo), sheet_name='Baixas')

        # Validar colunas
        colunas_esperadas = ['NF', 'PARCELA', 'VALOR', 'JOURNAL', 'DATA']
        colunas_faltando = [c for c in colunas_esperadas if c not in df.columns]
        if colunas_faltando:
            return jsonify({
                'success': False,
                'error': f'Colunas faltando: {", ".join(colunas_faltando)}'
            }), 400

        # Remover linhas vazias
        df = df.dropna(subset=['NF', 'VALOR'])

        if len(df) == 0:
            return jsonify({'success': False, 'error': 'Nenhuma linha valida encontrada'}), 400

        # Preparar itens para verificar duplicidade
        itens_parse = []
        for idx, row in df.iterrows():
            nf = str(row['NF']).strip() if pd.notna(row['NF']) else ''
            try:
                parcela = int(row['PARCELA']) if pd.notna(row['PARCELA']) else 1
            except (ValueError, TypeError):
                parcela = 1
            try:
                valor = round(float(row['VALOR']), 2) if pd.notna(row['VALOR']) else 0
            except (ValueError, TypeError):
                valor = 0

            itens_parse.append({'nf': nf, 'parcela': parcela, 'valor': valor})

        # Verificar duplicidades no arquivo
        duplicados_arquivo = verificar_duplicidade_no_arquivo(itens_parse)

        # Criar lote
        lote = BaixaTituloLote(
            nome_arquivo=arquivo.filename,
            hash_arquivo=hash_arquivo,
            total_linhas=len(df),
            status='IMPORTADO',
            criado_por=current_user.nome if current_user else 'Sistema'
        )
        db.session.add(lote)
        db.session.flush()

        # Criar itens
        linhas_validas = 0
        linhas_invalidas = 0
        duplicidades_total = 0

        for idx, row in df.iterrows():
            linha = idx + 2  #type: ignore # +2 porque Excel comeca em 1 e tem cabecalho

            # Converter NF
            nf = str(row['NF']).strip() if pd.notna(row['NF']) else ''

            # Converter parcela
            try:
                parcela = int(row['PARCELA']) if pd.notna(row['PARCELA']) else 1
            except (ValueError, TypeError):
                parcela = 1

            # Converter valor
            try:
                valor = round(float(row['VALOR']), 2) if pd.notna(row['VALOR']) else 0
            except (ValueError, TypeError):
                valor = 0

            # Journal
            journal_nome = str(row['JOURNAL']).strip() if pd.notna(row['JOURNAL']) else ''

            # Data
            try:
                if pd.notna(row['DATA']):
                    if isinstance(row['DATA'], str):
                        data_baixa = datetime.strptime(row['DATA'], '%Y-%m-%d').date()
                    else:
                        data_baixa = pd.to_datetime(row['DATA']).date()
                else:
                    data_baixa = date.today()
            except Exception:
                data_baixa = date.today()

            # Resolver journal
            journal_info = resolver_journal(journal_nome)

            # Validar
            erros = []
            if not nf:
                erros.append('NF vazia')
            if valor <= 0:
                erros.append('Valor invalido')
            if not journal_info:
                erros.append(f'Journal "{journal_nome}" nao encontrado')

            status = 'VALIDO' if not erros else 'INVALIDO'
            mensagem = '; '.join(erros) if erros else None

            # Verificar duplicidade
            is_duplicado = idx in duplicados_arquivo or verificar_duplicidade_banco(nf, parcela, valor)
            if is_duplicado:
                duplicidades_total += 1
                if mensagem:
                    mensagem += '; Possivel duplicidade'
                else:
                    mensagem = 'Possivel duplicidade'

            if status == 'VALIDO':
                linhas_validas += 1
            else:
                linhas_invalidas += 1

            # Criar item
            item = BaixaTituloItem(
                lote_id=lote.id,
                linha_excel=linha,
                nf_excel=nf,
                parcela_excel=parcela,
                valor_excel=valor,
                journal_excel=journal_nome,
                data_excel=data_baixa,
                journal_odoo_id=journal_info['id'] if journal_info else None,
                journal_odoo_code=journal_info['code'] if journal_info else None,
                ativo=status == 'VALIDO',
                status=status,
                mensagem=mensagem
            )
            db.session.add(item)

        # Atualizar estatisticas do lote
        lote.linhas_validas = linhas_validas
        lote.linhas_invalidas = linhas_invalidas
        lote.status = 'VALIDADO'

        db.session.commit()

        return jsonify({
            'success': True,
            'lote_id': lote.id,
            'nome_arquivo': lote.nome_arquivo,
            'total_linhas': lote.total_linhas,
            'linhas_validas': linhas_validas,
            'linhas_invalidas': linhas_invalidas,
            'duplicidades': duplicidades_total
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# TOGGLE ATIVO/INATIVO - INDIVIDUAL
# =============================================================================

@financeiro_bp.route('/contas-receber/baixas/item/<int:item_id>/toggle', methods=['POST'])
@login_required
def baixas_toggle_item(item_id):
    """
    Ativa ou inativa um item de baixa.
    """
    try:
        item = BaixaTituloItem.query.get_or_404(item_id)

        # Verificar se o lote ainda pode ser editado
        if item.lote.status in ['PROCESSANDO']:
            return jsonify({
                'success': False,
                'error': 'Lote esta em processamento'
            }), 400

        # Verificar se item pode ser modificado
        if item.status in ['SUCESSO', 'PROCESSANDO']:
            return jsonify({
                'success': False,
                'error': 'Item ja foi processado'
            }), 400

        # Verificar se item invalido pode ser ativado
        if item.status == 'INVALIDO':
            return jsonify({
                'success': False,
                'error': 'Item invalido nao pode ser ativado'
            }), 400

        # Obter novo valor do JSON ou inverter
        data = request.get_json() if request.is_json else {}
        novo_ativo = data.get('ativo', not item.ativo)

        item.ativo = novo_ativo
        db.session.commit()

        return jsonify({
            'success': True,
            'item_id': item.id,
            'ativo': item.ativo
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# ATIVAR/INATIVAR EM LOTE
# =============================================================================

@financeiro_bp.route('/contas-receber/baixas/ativar-lote', methods=['POST'])
@login_required
def baixas_ativar_lote():
    """
    Ativa ou inativa multiplos itens de uma vez.
    """
    try:
        data = request.get_json()
        ids = data.get('ids', [])
        ativo = data.get('ativo', True)

        if not ids:
            return jsonify({'success': False, 'error': 'Nenhum item informado'}), 400

        # Atualizar itens que podem ser modificados
        atualizados = 0
        for item_id in ids:
            item = BaixaTituloItem.query.get(item_id)
            if item and item.status not in ['SUCESSO', 'PROCESSANDO', 'INVALIDO']:
                item.ativo = ativo
                atualizados += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'atualizados': atualizados
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# PROCESSAR ITENS SELECIONADOS
# =============================================================================

@financeiro_bp.route('/contas-receber/baixas/processar-itens', methods=['POST'])
@login_required
def baixas_processar_itens():
    """
    Processa os itens selecionados no Odoo.
    """
    try:
        from app.financeiro.services.baixa_titulos_service import BaixaTitulosService

        data = request.get_json()
        ids = data.get('ids', [])

        if not ids:
            return jsonify({'success': False, 'error': 'Nenhum item selecionado'}), 400

        # Buscar itens
        itens = BaixaTituloItem.query.filter(
            BaixaTituloItem.id.in_(ids),
            BaixaTituloItem.ativo == True,
            BaixaTituloItem.status.in_(['PENDENTE', 'VALIDO', 'ERRO'])
        ).all()

        if not itens:
            return jsonify({'success': False, 'error': 'Nenhum item valido para processar'}), 400

        # Processar
        service = BaixaTitulosService()
        estatisticas = {
            'processados': 0,
            'sucesso': 0,
            'erro': 0
        }

        for item in itens:
            try:
                service._processar_item(item)
                item.status = 'SUCESSO'
                item.processado_em = datetime.utcnow()
                estatisticas['sucesso'] += 1
            except Exception as e:
                item.status = 'ERRO'
                item.mensagem = str(e)
                item.processado_em = datetime.utcnow()
                estatisticas['erro'] += 1

            estatisticas['processados'] += 1
            db.session.commit()

        return jsonify({
            'success': True,
            'resultado': estatisticas
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# BUSCAR LOTE (API)
# =============================================================================

@financeiro_bp.route('/contas-receber/baixas/lote/<int:lote_id>')
@login_required
def baixas_get_lote(lote_id):
    """
    Retorna os dados de um lote para exibicao.
    """
    try:
        lote = BaixaTituloLote.query.get_or_404(lote_id)

        itens = [{
            'id': item.id,
            'linha': item.linha_excel,
            'nf': item.nf_excel,
            'parcela': item.parcela_excel,
            'valor': item.valor_excel,
            'journal': item.journal_excel,
            'journal_id': item.journal_odoo_id,
            'data': item.data_excel.strftime('%Y-%m-%d') if item.data_excel else None,
            'status': item.status,
            'mensagem': item.mensagem,
            'ativo': item.ativo,
            'payment_name': item.payment_odoo_name,
            'saldo_antes': item.saldo_antes,
            'saldo_depois': item.saldo_depois
        } for item in lote.itens.order_by(BaixaTituloItem.linha_excel).all()]

        return jsonify({
            'success': True,
            'lote': lote.to_dict(),
            'itens': itens
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# PROCESSAR LOTE COMPLETO (LEGADO - manter para compatibilidade)
# =============================================================================

@financeiro_bp.route('/contas-receber/baixas/lote/<int:lote_id>/processar', methods=['POST'])
@login_required
def baixas_processar_lote(lote_id):
    """
    Processa todas as baixas ativas de um lote no Odoo.
    """
    try:
        from app.financeiro.services.baixa_titulos_service import BaixaTitulosService

        lote = BaixaTituloLote.query.get_or_404(lote_id)

        if lote.status not in ['IMPORTADO', 'VALIDADO']:
            return jsonify({
                'success': False,
                'error': f'Lote nao pode ser processado (status: {lote.status})'
            }), 400

        lote.status = 'PROCESSANDO'
        lote.processado_por = current_user.nome if current_user else 'Sistema'
        db.session.commit()

        service = BaixaTitulosService()
        resultado = service.processar_lote(lote_id)

        return jsonify({
            'success': True,
            'resultado': resultado
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# LISTAR JOURNALS (API)
# =============================================================================

@financeiro_bp.route('/contas-receber/baixas/journals')
@login_required
def baixas_listar_journals():
    """
    Retorna lista de journals disponiveis.
    """
    return jsonify({
        'success': True,
        'journals': JOURNALS_DISPONIVEIS
    })
