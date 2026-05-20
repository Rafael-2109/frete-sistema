"""Rastreamento 360 de um chassi no modulo Motos Assai.

Cruza TODAS as entidades transacionais ligadas ao chassi (chave universal do
modulo — ver app/motos_assai/CLAUDE.md "Invariante central"): recibo Motochefe,
eventos de montagem/pendencia, separacao, carregamento, NF Q.P.A., Carta de
Correcao (CCe) e divergencias.

Read-only. Consumido por GET /motos-assai/resumo/rastrear-chassi (modal da
tela Resumo).

Datas sao formatadas em pt-BR (dd/mm/YYYY HH:MM) no service para simplificar o
JS consumidor. Valores Numeric viram float; colunas JSON/JSONB retornam tipos
nativos (ja desserializados pelo SQLAlchemy na leitura) e portanto sao seguros
para jsonify.

Notas de modelagem (fontes verificadas):
- AssaiDivergencia possui coluna `chassi` indexada (busca direta) —
  models/divergencia.py:65.
- AssaiCce NAO possui coluna `chassi`; o vinculo se da via `nf_id` (NF do chassi)
  ou via JSON `chassis_aplicados` / `dados_parsed` (busca textual) —
  models/cce.py.
- AssaiCarregamentoItem NAO tem relacionamento `escaneado_por`; o nome do
  operador e obtido via JOIN explicito com Usuario.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import cast, or_, Text

from app import db
from app.motos_assai.models import (
    AssaiMoto,
    AssaiReciboItem,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiCarregamento, AssaiCarregamentoItem,
    AssaiNfQpa, AssaiNfQpaItem,
    AssaiCce, AssaiDivergencia,
    EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA,
    EVENTO_REVERTIDA_PARA_MONTADA,
)
from app.motos_assai.services.moto_evento_service import (
    eventos_chassi, status_efetivo,
)


# Eventos que representam o ciclo de montagem (chao de fabrica).
_TIPOS_MONTAGEM = (
    EVENTO_MONTADA, EVENTO_PENDENCIA_RESOLVIDA, EVENTO_REVERTIDA_PARA_MONTADA,
)

_FMT_DATA_HORA = '%d/%m/%Y %H:%M'
_FMT_DATA = '%d/%m/%Y'


def _dt(valor, fmt: str = _FMT_DATA_HORA) -> Optional[str]:
    """Formata datetime/date em pt-BR. None -> None."""
    return valor.strftime(fmt) if valor else None


def _operador_nome(ev) -> str:
    return ev.operador.nome if ev and ev.operador else '-'


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def rastrear_chassi(chassi: str) -> Dict[str, Any]:
    """Monta a visao 360 de um chassi. Retorna dict pronto para jsonify.

    Estrutura:
        {ok, encontrado, chassi, [mensagem], moto, status_efetivo,
         recibos[], montagem[], pendencias[], separacoes[], carregamentos[],
         nfs[], cces[], divergencias[], eventos[], contadores{}}
    """
    chassi_norm = (chassi or '').strip().upper()
    if not chassi_norm:
        return {
            'ok': False,
            'encontrado': False,
            'erro': 'Informe um chassi para pesquisar.',
        }

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).first()
    eventos = eventos_chassi(chassi_norm, limit=200)

    recibos = _buscar_recibos(chassi_norm)
    separacoes = _buscar_separacoes(chassi_norm)
    carregamentos = _buscar_carregamentos(chassi_norm)
    nfs = _buscar_nfs(chassi_norm)
    nf_ids = [n['nf_id'] for n in nfs]
    cces = _buscar_cces(chassi_norm, nf_ids)
    divergencias = _buscar_divergencias(chassi_norm)

    montagem = [_evento_dict(e) for e in eventos if e.tipo in _TIPOS_MONTAGEM]
    pendencias = [_pendencia_dict(e) for e in eventos if e.tipo == EVENTO_PENDENTE]
    timeline = [_evento_dict(e) for e in eventos]

    encontrado = bool(
        moto or eventos or recibos or separacoes or carregamentos
        or nfs or cces or divergencias
    )

    if not encontrado:
        return {
            'ok': True,
            'encontrado': False,
            'chassi': chassi_norm,
            'mensagem': f'Nenhum registro encontrado para o chassi {chassi_norm}.',
        }

    return {
        'ok': True,
        'encontrado': True,
        'chassi': chassi_norm,
        'moto': _moto_dict(moto) if moto else None,
        'status_efetivo': status_efetivo(chassi_norm),
        'recibos': recibos,
        'montagem': montagem,
        'pendencias': pendencias,
        'separacoes': separacoes,
        'carregamentos': carregamentos,
        'nfs': nfs,
        'cces': cces,
        'divergencias': divergencias,
        'eventos': timeline,
        'contadores': {
            'recibos': len(recibos),
            'montagem': len(montagem),
            'pendencias': len(pendencias),
            'separacoes': len(separacoes),
            'carregamentos': len(carregamentos),
            'nfs': len(nfs),
            'cces': len(cces),
            'divergencias': len(divergencias),
            'eventos': len(timeline),
        },
    }


# ---------------------------------------------------------------------------
# Helpers de serializacao
# ---------------------------------------------------------------------------

def _moto_dict(m: AssaiMoto) -> Dict[str, Any]:
    return {
        'id': m.id,
        'modelo_id': m.modelo_id,
        'modelo_codigo': m.modelo.codigo if m.modelo else None,
        'modelo_nome': m.modelo.nome if m.modelo else None,
        'cor': m.cor or '-',
        'motor': m.motor or '-',
        'ano': m.ano,
        'criada_em': _dt(m.criada_em),
    }


def _evento_dict(e) -> Dict[str, Any]:
    return {
        'tipo': e.tipo,
        'ocorrido_em': _dt(e.ocorrido_em),
        'operador': _operador_nome(e),
        'observacao': e.observacao or '',
    }


def _pendencia_dict(e) -> Dict[str, Any]:
    obs = e.observacao
    if not obs and isinstance(e.dados_extras, dict):
        obs = e.dados_extras.get('descricao')
    return {
        'tipo': e.tipo,
        'ocorrido_em': _dt(e.ocorrido_em),
        'operador': _operador_nome(e),
        'observacao': obs or '(sem observacao)',
    }


# ---------------------------------------------------------------------------
# Buscas por entidade (todas a partir do chassi)
# ---------------------------------------------------------------------------

def _buscar_recibos(chassi: str) -> List[Dict[str, Any]]:
    """Itens de recibo Motochefe que declararam o chassi (origem da moto)."""
    itens = (
        AssaiReciboItem.query
        .filter_by(chassi=chassi)
        .order_by(AssaiReciboItem.id.asc())
        .all()
    )
    result = []
    for it in itens:
        recibo = it.recibo  # backref de AssaiReciboMotochefe.itens
        result.append({
            'recibo_id': it.recibo_id,
            'numero_recibo': (recibo.numero_recibo if recibo else None) or '-',
            'data_recibo': _dt(recibo.data_recibo, _FMT_DATA) if recibo else None,
            'equipe': (recibo.equipe if recibo else None) or '-',
            'conferente': (recibo.conferente_motochefe if recibo else None) or '-',
            'status': recibo.status if recibo else '-',
            'compra_id': recibo.compra_id if recibo else None,
            'modelo_texto_recibo': it.modelo_texto_recibo or '-',
            'cor_texto': it.cor_texto or '-',
            'motor': it.motor or '-',
            'conferido': it.conferido,
            'tipo_divergencia': it.tipo_divergencia,
            'qr_code_lido': it.qr_code_lido,
            'ativo': it.ativo,
        })
    return result


def _buscar_separacoes(chassi: str) -> List[Dict[str, Any]]:
    """Separacoes (qualquer status, inclusive CANCELADA) que contem o chassi."""
    rows = (
        db.session.query(AssaiSeparacaoItem, AssaiSeparacao)
        .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
        .filter(AssaiSeparacaoItem.chassi == chassi)
        .order_by(AssaiSeparacaoItem.id.desc())
        .all()
    )
    result = []
    for item, sep in rows:
        result.append({
            'sep_id': sep.id,
            'status': sep.status,
            'pedido_id': sep.pedido_id,
            'pedido_numero': sep.pedido.numero if sep.pedido else '-',
            'loja_numero': sep.loja.numero if sep.loja else '-',
            'loja_nome': sep.loja.nome if sep.loja else '-',
            'registrada_em': _dt(item.registrada_em),
            'operador': item.registrada_por.nome if item.registrada_por else '-',
            'expedicao': _dt(sep.expedicao, _FMT_DATA),
            'agendamento': _dt(sep.agendamento, _FMT_DATA),
            'protocolo': sep.protocolo or '-',
            'valor_unitario_qpa': float(item.valor_unitario_qpa) if item.valor_unitario_qpa is not None else None,
        })
    return result


def _buscar_carregamentos(chassi: str) -> List[Dict[str, Any]]:
    """Carregamentos (etapa fisica) que escanearam o chassi.

    AssaiCarregamentoItem nao tem relacionamento com Usuario; usamos JOIN
    explicito para obter o nome do operador.
    """
    from app.auth.models import Usuario  # import tardio (fora do modulo)

    rows = (
        db.session.query(AssaiCarregamentoItem, AssaiCarregamento, Usuario.nome)
        .join(AssaiCarregamento,
              AssaiCarregamento.id == AssaiCarregamentoItem.carregamento_id)
        .outerjoin(Usuario, Usuario.id == AssaiCarregamentoItem.escaneado_por_id)
        .filter(AssaiCarregamentoItem.chassi == chassi)
        .order_by(AssaiCarregamentoItem.id.desc())
        .all()
    )
    result = []
    for item, car, operador_nome in rows:
        result.append({
            'carregamento_id': car.id,
            'status': car.status,
            'pedido_numero': car.pedido.numero if car.pedido else '-',
            'loja_numero': car.loja.numero if car.loja else '-',
            'loja_nome': car.loja.nome if car.loja else '-',
            'separacao_id': car.separacao_id,
            'escaneado_em': _dt(item.escaneado_em),
            'operador': operador_nome or '-',
        })
    return result


def _buscar_nfs(chassi: str) -> List[Dict[str, Any]]:
    """NFs Q.P.A. (qualquer status, inclusive CANCELADA) que contem o chassi."""
    rows = (
        db.session.query(AssaiNfQpaItem, AssaiNfQpa)
        .join(AssaiNfQpa, AssaiNfQpa.id == AssaiNfQpaItem.nf_id)
        .filter(AssaiNfQpaItem.chassi == chassi)
        .order_by(AssaiNfQpa.id.desc())
        .all()
    )
    result = []
    for item, nf in rows:
        result.append({
            'nf_id': nf.id,
            'numero': nf.numero or '-',
            'serie': nf.serie or '-',
            'chave_44': nf.chave_44,
            'loja_numero': nf.loja.numero if nf.loja else '-',
            'loja_nome': nf.loja.nome if nf.loja else '-',
            'data_emissao': _dt(nf.data_emissao, _FMT_DATA),
            'status_match': nf.status_match,
            'valor_total': float(nf.valor_total) if nf.valor_total is not None else None,
            'valor_item': float(item.valor_extraido) if item.valor_extraido is not None else None,
            'modelo_extraido': item.modelo_extraido or '-',
            'tipo_divergencia': item.tipo_divergencia,
            'devolvido': item.devolvido,
            'devolvido_em': _dt(item.devolvido_em),
            'cancelada_em': _dt(nf.cancelada_em),
            'motivo_cancelamento': nf.motivo_cancelamento or '',
        })
    return result


def _buscar_cces(chassi: str, nf_ids: List[int]) -> List[Dict[str, Any]]:
    """Cartas de Correcao (CCe) relacionadas ao chassi.

    Sem coluna `chassi`: combina (a) `nf_id` nas NFs do chassi e (b) busca
    textual do chassi em `chassis_aplicados` e `dados_parsed` (JSON -> Text).
    Dedup natural pela query unica com OR.
    """
    condicoes = [
        cast(AssaiCce.chassis_aplicados, Text).ilike(f'%{chassi}%'),
        cast(AssaiCce.dados_parsed, Text).ilike(f'%{chassi}%'),
    ]
    if nf_ids:
        condicoes.append(AssaiCce.nf_id.in_(nf_ids))

    cces = (
        AssaiCce.query
        .filter(or_(*condicoes))
        .order_by(AssaiCce.id.desc())
        .all()
    )
    result = []
    for c in cces:
        result.append({
            'cce_id': c.id,
            'protocolo_cce': c.protocolo_cce,
            'numero_cce': c.numero_cce or '-',
            'tipo_correcao': c.tipo_correcao,
            'status': c.status,
            'sequencia_cce': c.sequencia_cce,
            'tem_nf': c.tem_nf,
            'nf_id': c.nf_id,
            'nf_numero': c.nf.numero if c.nf else None,
            'numero_nf_referenciada': c.numero_nf_referenciada,
            'chassis_aplicados': c.chassis_aplicados or [],
            'data_emissao_cce': _dt(c.data_emissao_cce, _FMT_DATA),
            'criado_em': _dt(c.criado_em),
            'aplicada_em': _dt(c.aplicada_em),
            'observacao': c.observacao or '',
        })
    return result


def _buscar_divergencias(chassi: str) -> List[Dict[str, Any]]:
    """Divergencias do chassi (coluna `chassi` indexada)."""
    divs = (
        AssaiDivergencia.query
        .filter_by(chassi=chassi)
        .order_by(AssaiDivergencia.id.desc())
        .all()
    )
    result = []
    for d in divs:
        result.append({
            'div_id': d.id,
            'tipo': d.tipo,
            'separacao_id': d.separacao_id,
            'carregamento_id': d.carregamento_id,
            'nf_id': d.nf_id,
            'nf_numero': d.nf.numero if d.nf else None,
            'detalhes': d.detalhes or {},
            'criada_em': _dt(d.criada_em),
            'resolvida_em': _dt(d.resolvida_em),
            'tipo_resolucao': d.tipo_resolucao,
            'observacao_resolucao': d.observacao_resolucao or '',
            'resolvida': d.resolvida_em is not None,
        })
    return result
