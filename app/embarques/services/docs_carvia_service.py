"""
Service de impressao consolidada dos documentos CarVia de um item de embarque.

Dado um EmbarqueItem CarVia (separacao_lote_id == 'CARVIA-NF-{nf_id}'), resolve e
concatena num UNICO PDF: NF (DANFE) + CTe CarVia (DACTE) + Fatura Cliente CarVia,
precedidos de uma folha de rosto com o checklist do que foi incluido/faltou.

Vinculos (verificados nos modelos CarVia):
  EmbarqueItem.separacao_lote_id == 'CARVIA-NF-{nf_id}'  -> CarviaNf.id
  CarviaNf.arquivo_pdf_path                              -> DANFE
  CarviaNf.operacoes (N:N, status != CANCELADO)          -> CarviaOperacao.cte_pdf_path (DACTE)
  CarviaOperacao.fatura_cliente.arquivo_pdf_path         -> Fatura (fallback: CarviaNf.get_faturas_cliente())

REGRA R1 do modulo CarVia: CarVia NAO importa de embarques. O sentido inverso
(embarques -> carvia) e permitido e usa imports LAZY (dentro das funcoes) para
evitar circular imports e overhead de boot.

Decisao do usuario (2026-06-11): 1 PDF unico (merge) + gerar com os disponiveis
+ aviso embutido na folha de rosto.
"""

import logging
from io import BytesIO

from flask import render_template

logger = logging.getLogger(__name__)

# Prefixo de lote dos itens CarVia que ja tem NF (os unicos com documentos).
# Itens CARVIA-PED-/CARVIA-COT- sao provisorios (sem NF) — nao entram aqui.
PREFIXO_LOTE_NF = 'CARVIA-NF-'

# Rotulos das 3 secoes (ordem do PDF final, apos a capa)
DOC_NF = 'NF (DANFE)'
DOC_CTE = 'CTe CarVia (DACTE)'
DOC_FATURA = 'Fatura CarVia'


def _nf_id_do_lote(separacao_lote_id):
    """Extrai o CarviaNf.id embutido no separacao_lote_id 'CARVIA-NF-{nf_id}'.

    Retorna int ou None se o lote nao seguir o padrao esperado.
    """
    lote = str(separacao_lote_id or '')
    if not lote.startswith(PREFIXO_LOTE_NF):
        return None
    sufixo = lote[len(PREFIXO_LOTE_NF):]
    try:
        return int(sufixo)
    except (ValueError, TypeError):
        return None


def _baixar_pdf(path):
    """Resolve um *_pdf_path (chave S3, caminho local ou URL http) para bytes.

    Best-effort: qualquer falha retorna None (o documento vira 'faltante' no
    resumo) — NUNCA propaga excecao para nao quebrar a geracao do PDF inteiro.
    """
    if not path:
        return None
    path = str(path)
    try:
        if path.startswith('http'):
            import requests
            resp = requests.get(path, timeout=30)
            resp.raise_for_status()
            return resp.content

        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        if not storage.file_exists(path):
            logger.warning(f"[DOCS_CARVIA] arquivo nao existe no storage: {path}")
            return None
        return storage.download_file(path)
    except Exception as e:
        logger.warning(f"[DOCS_CARVIA] falha ao baixar PDF '{path}': {e}")
        return None


def _append_pdf(writer, pdf_bytes, rotulo, resumo):
    """Anexa os bytes de um PDF ao writer; registra status em resumo[rotulo].

    Status possiveis: 'incluido' | 'faltante' | 'erro'. PDF corrompido/invalido
    nao quebra o merge — vira 'erro' e e pulado.
    """
    if not pdf_bytes:
        resumo[rotulo]['status'] = 'faltante'
        return
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(pdf_bytes))
        writer.append(reader)
        resumo[rotulo]['status'] = 'incluido'
        resumo[rotulo]['paginas'] = len(reader.pages)
    except Exception as e:
        logger.warning(f"[DOCS_CARVIA] PDF invalido para '{rotulo}': {e}")
        resumo[rotulo]['status'] = 'erro'


def _resolver_operacao_ativa(nf):
    """Retorna a CarviaOperacao ativa (status != CANCELADO) preferindo a que ja
    tem cte_pdf_path. Retorna None se nao houver operacao ativa."""
    from app.carvia.models.documentos import CarviaOperacao
    operacoes_ativas = nf.operacoes.filter(
        CarviaOperacao.status != 'CANCELADO'
    ).all()
    if not operacoes_ativas:
        return None
    for op in operacoes_ativas:
        if op.cte_pdf_path:
            return op
    # Tem operacao ativa mas CTe ainda nao emitido (sem PDF)
    return operacoes_ativas[0]


def _resolver_fatura(nf, operacao):
    """Retorna a CarviaFaturaCliente nao-cancelada vinculada (via operacao,
    fallback via itens da NF). Retorna None se nao houver."""
    def _valida(fat):
        if fat is None:
            return False
        if fat.status == 'CANCELADA' or getattr(fat, 'cancelada', False):
            return False
        return True

    if operacao is not None and operacao.fatura_cliente_id:
        fat = operacao.fatura_cliente
        if _valida(fat):
            return fat

    # Fallback: faturas que referenciam a NF via itens (CarviaFaturaClienteItem.nf_id)
    for fat in nf.get_faturas_cliente():
        if _valida(fat):
            return fat
    return None


def gerar_pdf_docs_carvia(embarque_item):
    """Gera um unico PDF com NF + CTe CarVia + Fatura CarVia do item de embarque.

    Args:
        embarque_item: instancia de EmbarqueItem (deve ser CarVia com NF —
            separacao_lote_id == 'CARVIA-NF-{nf_id}').

    Returns:
        tuple[bytes, dict]: (pdf_bytes, resumo)
            resumo = {
                'nf_id': int,
                'numero_nf': str,
                DOC_NF:     {'status': 'incluido'|'faltante'|'erro', 'paginas': int, 'ref': str},
                DOC_CTE:    {...},
                DOC_FATURA: {...},
            }

    Raises:
        ValueError: se o item nao for CarVia-com-NF ou a NF nao existir.
    """
    from app import db
    from app.carvia.models.documentos import CarviaNf

    nf_id = _nf_id_do_lote(getattr(embarque_item, 'separacao_lote_id', None))
    if nf_id is None:
        raise ValueError(
            "Item nao e CarVia com NF (separacao_lote_id fora do padrao "
            f"'{PREFIXO_LOTE_NF}{{nf_id}}'): {getattr(embarque_item, 'separacao_lote_id', None)!r}"
        )

    nf = db.session.get(CarviaNf, nf_id)
    if nf is None:
        raise ValueError(f"CarviaNf id={nf_id} nao encontrada (lote do item).")

    operacao = _resolver_operacao_ativa(nf)
    fatura = _resolver_fatura(nf, operacao)

    # Estrutura do resumo (preenchida durante o merge)
    resumo = {
        'nf_id': nf_id,
        'numero_nf': nf.numero_nf,
        DOC_NF: {
            'status': None, 'paginas': 0,
            'ref': f"NF {nf.numero_nf}" + (f"-{nf.serie_nf}" if nf.serie_nf else ""),
        },
        DOC_CTE: {
            'status': None, 'paginas': 0,
            'ref': (operacao.cte_numero or operacao.ctrc_numero or '—') if operacao else '—',
        },
        DOC_FATURA: {
            'status': None, 'paginas': 0,
            'ref': fatura.numero_fatura if fatura else '—',
        },
    }

    # Baixa os 3 PDFs (best-effort)
    danfe_bytes = _baixar_pdf(nf.arquivo_pdf_path)
    dacte_bytes = _baixar_pdf(operacao.cte_pdf_path) if operacao else None
    fatura_bytes = _baixar_pdf(fatura.arquivo_pdf_path) if fatura else None

    # Pre-marca status de quem nem chegou a ter PDF (capa precisa do status final)
    # — os helpers _append_pdf abaixo gravam o status real.
    from pypdf import PdfWriter
    writer = PdfWriter()

    # Folha de rosto: precisa do checklist final, mas o status so e conhecido
    # apos tentar anexar. Resolvemos anexando primeiro os 3 docs num writer
    # temporario, computando o resumo, gerando a capa e entao montando o final
    # na ordem [capa, NF, CTe, Fatura].
    _append_pdf(writer, danfe_bytes, DOC_NF, resumo)
    _append_pdf(writer, dacte_bytes, DOC_CTE, resumo)
    _append_pdf(writer, fatura_bytes, DOC_FATURA, resumo)

    capa_bytes = _gerar_capa(embarque_item, nf, resumo)

    # Monta o PDF final: capa primeiro, depois os documentos ja anexados.
    final = PdfWriter()
    if capa_bytes:
        try:
            from pypdf import PdfReader
            final.append(PdfReader(BytesIO(capa_bytes)))
        except Exception as e:
            logger.warning(f"[DOCS_CARVIA] falha ao anexar capa: {e}")
    final.append(writer)

    out = BytesIO()
    final.write(out)
    out.seek(0)
    return out.read(), resumo


def _gerar_capa(embarque_item, nf, resumo):
    """Renderiza a folha de rosto (HTML -> PDF via weasyprint). Best-effort:
    se falhar, retorna None (PDF segue sem capa)."""
    try:
        from weasyprint import HTML  # lazy import (custo de boot)
        embarque = getattr(embarque_item, 'embarque', None)
        html_str = render_template(
            'embarques/imprimir_docs_carvia_capa.html',
            item=embarque_item,
            embarque=embarque,
            nf=nf,
            resumo=resumo,
            docs=[
                (DOC_NF, resumo[DOC_NF]),
                (DOC_CTE, resumo[DOC_CTE]),
                (DOC_FATURA, resumo[DOC_FATURA]),
            ],
        )
        return HTML(string=html_str).write_pdf()
    except Exception as e:
        logger.warning(f"[DOCS_CARVIA] falha ao gerar capa: {e}")
        return None
