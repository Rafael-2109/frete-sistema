"""Helper para traduzir CarviaOperacao.cte_tomador em label visual.

O campo `cte_tomador` e persistido com valores extraidos do CTe XML
(<ide>/<toma3> ou <toma4>):
    REMETENTE | EXPEDIDOR | RECEBEDOR | DESTINATARIO | TERCEIRO

Na UI, so destacamos REMETENTE (= emitente da NF) e DESTINATARIO.
Os demais casos (raros no fluxo CarVia) persistem no banco mas retornam
None e nao geram destaque visual.
"""

_LABEL_MAP = {
    'REMETENTE': 'emitente',
    'DESTINATARIO': 'destinatario',
}


def tomador_label(cte_tomador):
    """Retorna 'emitente' | 'destinatario' | None."""
    return _LABEL_MAP.get(cte_tomador)


def tomador_label_para_export(cte_tomador):
    """Retorna string para a coluna 'Tomador' do export Excel."""
    label = tomador_label(cte_tomador)
    if label == 'emitente':
        return 'Emitente'
    if label == 'destinatario':
        return 'Destinatario'
    return ''
