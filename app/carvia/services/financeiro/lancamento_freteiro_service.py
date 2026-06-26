# etapa: integracao lancamento freteiros Nacom+CarVia (2026-06-12)
# doc-dono: app/carvia/CLAUDE.md + app/fretes/CLAUDE.md secao "Lancamento de Freteiros"
"""LancamentoFreteiroCarviaService — espelho CarVia do fluxo de freteiros Nacom.

Contexto (decisao Rafael 2026-06-12, origem IMP-2026-06-10-005): a MESMA equipe
confere e paga freteiros das duas empresas. Num embarque compartilhado (carga
Nacom + motos CarVia), o freteiro alega o frete TOTAL — a tela de Lancamento de
Freteiros (app/fretes) passa a exibir e EMITIR para ambas: o lado Nacom grava
em Frete/FaturaFrete como sempre; o lado CarVia grava AQUI (CarviaFrete +
CarviaSubcontrato + CarviaFaturaTransportadora), preservando as invariantes do
modulo (Phase C conferencia no frete, Gate 1 da FT, R4 status irreversivel,
R11 pagamento via conciliacao — a emissao NAO marca a FT como paga).

Direcao de import permitida: app/fretes -> app/carvia via LAZY import (R1/R2
do CarVia; precedente verificar_cte_existente_para_embarque). Este service NAO
importa nada de app/fretes.

REGRA DE TRANSACAO: este service NAO comita — apenas flush. O caller
(emitir_fatura_freteiro em app/fretes/routes.py) comita os dois lados na MESMA
transacao (rollback conjunto se um lado falhar).
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Espelho do criterio de pendencia da tela Nacom (valor_cte ausente = nao
# acertado com o freteiro), aprovado pelo Rafael 2026-06-12 (item 1).
STATUS_EXCLUIDOS_PENDENCIA = ('CANCELADO',)


def listar_fretes_carvia_pendentes_freteiro(
    transportadora_id: int,
) -> List[Dict[str, Any]]:
    """Fretes CarVia pendentes de acerto de um freteiro, p/ a tela unificada.

    Pendente = valor_cte IS NULL + status nao cancelado + embarque vinculado
    (espelha o criterio Nacom: Frete sem numero_cte/valor_cte). Valores SEMPRE
    de CarviaFrete (decisao Rafael); exibir valor_cotado (gravado na portaria
    via lancar_frete_carvia).

    Returns:
        lista de dicts {id, embarque_id, nome_destino, cidade_destino,
        uf_destino, numeros_nfs, quantidade_nfs, peso_total, valor_total_nfs,
        valor_cotado, valor_considerado}
    """
    from app.carvia.models import CarviaFrete

    fretes = (
        CarviaFrete.query
        .filter(
            CarviaFrete.transportadora_id == transportadora_id,
            CarviaFrete.embarque_id.isnot(None),
            CarviaFrete.valor_cte.is_(None),
            ~CarviaFrete.status.in_(STATUS_EXCLUIDOS_PENDENCIA),
        )
        .order_by(CarviaFrete.embarque_id, CarviaFrete.id)
        .all()
    )
    return [
        {
            'id': f.id,
            'embarque_id': f.embarque_id,
            'nome_destino': f.nome_destino or '',
            'cidade_destino': f.cidade_destino or '',
            'uf_destino': f.uf_destino or '',
            'numeros_nfs': f.numeros_nfs or '',
            'quantidade_nfs': f.quantidade_nfs or 0,
            'peso_total': float(f.peso_total or 0),
            'valor_total_nfs': float(f.valor_total_nfs or 0),
            'valor_cotado': float(f.valor_cotado or 0),
            'valor_considerado': float(f.valor_considerado or f.valor_cotado or 0),
        }
        for f in fretes
    ]


def listar_custos_entrega_carvia_pendentes_freteiro(
    transportadora_id: int,
) -> List[Dict[str, Any]]:
    """Custos de entrega CarVia pendentes de um freteiro (xerox DespesaExtra Nacom).

    Espelha o criterio Nacom de despesas pendentes (lancamento_freteiros): CE
    PENDENTE, sem fatura, transportadora efetiva = freteiro, com frete em embarque
    (agrupamento por embarque na tela). Transportadora efetiva = override
    (`CarviaCustoEntrega.transportadora_id`) OU a do frete (paridade Nacom
    `transportadora_efetiva`).

    Returns:
        lista de dicts {id, frete_id, embarque_id, tipo_custo, descricao, valor,
        numeros_nfs, nome_destino}
    """
    from app import db
    from app.carvia.models import CarviaCustoEntrega, CarviaFrete

    ces = (
        CarviaCustoEntrega.query
        .join(CarviaFrete, CarviaCustoEntrega.frete_id == CarviaFrete.id)
        .filter(
            CarviaCustoEntrega.status == 'PENDENTE',
            CarviaCustoEntrega.fatura_transportadora_id.is_(None),
            CarviaFrete.embarque_id.isnot(None),
            db.or_(
                CarviaCustoEntrega.transportadora_id == transportadora_id,
                db.and_(
                    CarviaCustoEntrega.transportadora_id.is_(None),
                    CarviaFrete.transportadora_id == transportadora_id,
                ),
            ),
        )
        .order_by(CarviaFrete.embarque_id, CarviaCustoEntrega.id)
        .all()
    )
    resultado = []
    for ce in ces:
        frete = ce.frete  # backref CarviaFrete.custos_entrega
        resultado.append({
            'id': ce.id,
            'frete_id': ce.frete_id,
            'embarque_id': frete.embarque_id if frete else None,
            'tipo_custo': ce.tipo_custo or '',
            'descricao': ce.descricao or '',
            'valor': float(ce.valor or 0),
            'numeros_nfs': (frete.numeros_nfs if frete else '') or '',
            'nome_destino': (frete.nome_destino if frete else '') or '',
        })
    return resultado


def _gerar_numero_fatura_unico(transportadora, data_vencimento) -> str:
    """Nome sintetico espelhando o Nacom ("Fech {nome} {venc}"), com sufixo
    sequencial se colidir (UNIQUE numero_fatura+transportadora_id)."""
    from app.carvia.models import CarviaFaturaTransportadora

    data_venc_str = data_vencimento.strftime('%d/%m/%Y')
    max_chars_nome = 50 - 5 - 1 - 10 - 1  # "Fech " + nome + " " + data
    nome_base = f"Fech {transportadora.razao_social[:max_chars_nome]} {data_venc_str}"[:50]

    nome = nome_base
    seq = 1
    while CarviaFaturaTransportadora.query.filter_by(
        numero_fatura=nome, transportadora_id=transportadora.id,
    ).first():
        seq += 1
        sufixo = f" ({seq})"
        nome = (nome_base[: 50 - len(sufixo)] + sufixo)[:50]
    return nome


def emitir_fatura_freteiro_carvia(
    transportadora_id: int,
    itens: List[Dict[str, Any]],
    data_vencimento,
    usuario_nome: str,
    observacoes: str = '',
    custos_entrega: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Emite o lado CarVia do fechamento de freteiro (espelho do Nacom).

    Para cada item {frete_id, valor_considerado} (valor ja re-rateado pelo
    caller quando o usuario alterou o total do embarque):
      1. valida frete (transportadora, nao cancelado, sem FT previa);
      2. grava valor_considerado/valor_cte/valor_pago (paridade Nacom — o
         valor_cte sintetico tira o frete da lista de pendentes) + cte_numero
         sintetico no subcontrato ("Frete (data) NFs ...");
      3. conferencia automatica do custo (Phase C): status_conferencia=
         APROVADO + conferido_por/em + detalhes_conferencia snapshot;
      4. cria CarviaSubcontrato se ausente (cte_numero sintetico — freteiro
         nao emite CTe; pattern frete_routes lancar_cte) e vincula ambos a FT;
      5. frete.status -> FATURADO (lifecycle Phase C: vinculado a FT conferida).
    Cria 1 CarviaFaturaTransportadora CONFERIDA (Gate 1 satisfeito: todos os
    fretes APROVADO; Gate 2 exato: valor_total = soma considerados) e gera os
    itens de detalhe via LinkingService. Pagamento segue o fluxo normal
    (conciliacao R11) — status_pagamento permanece PENDENTE.

    Args:
        transportadora_id: freteiro (Transportadora.freteiro=True — validado
            pelo caller).
        itens: [{'frete_id': int, 'valor_considerado': float}] — valores
            re-rateados ("diferenca ambas pagam").
        data_vencimento: date do form da tela.
        usuario_nome: autor (conferido_por/criado_por).
        observacoes: texto livre do form.

    Returns:
        {'fatura_id', 'numero_fatura', 'valor_total', 'fretes': N,
         'subcontratos_criados': N}

    Raises:
        ValueError: validacao de dado (frete inexistente/cancelado/de outra
            transportadora/ja faturado). Caller faz rollback conjunto.
    """
    from decimal import Decimal

    from app import db
    from app.carvia.models import (
        CarviaCustoEntrega, CarviaFaturaTransportadora, CarviaFrete,
        CarviaSubcontrato,
    )
    from app.carvia.services.documentos.linking_service import LinkingService
    from app.transportadoras.models import Transportadora
    from app.utils.timezone import agora_utc_naive

    custos_entrega = custos_entrega or []
    if not itens and not custos_entrega:
        raise ValueError('Nenhum frete ou custo CarVia informado para emissao.')

    transportadora = db.session.get(Transportadora, transportadora_id)
    if not transportadora:
        raise ValueError(f'Transportadora {transportadora_id} nao encontrada.')

    agora = agora_utc_naive()

    # --- 1. Validar e carregar fretes ---
    fretes_validados: List[Dict[str, Any]] = []
    valor_total = Decimal('0')
    for item in itens:
        frete = db.session.get(CarviaFrete, int(item['frete_id']))
        if not frete:
            raise ValueError(f"CarviaFrete {item['frete_id']} nao encontrado.")
        if frete.transportadora_id != transportadora_id:
            raise ValueError(
                f'CarviaFrete {frete.id} pertence a outra transportadora '
                f'({frete.transportadora_id} != {transportadora_id}).'
            )
        if frete.status in STATUS_EXCLUIDOS_PENDENCIA:
            raise ValueError(f'CarviaFrete {frete.id} esta cancelado.')
        if frete.fatura_transportadora_id:
            raise ValueError(
                f'CarviaFrete {frete.id} ja vinculado a fatura '
                f'{frete.fatura_transportadora_id}.'
            )
        valor = Decimal(str(item['valor_considerado'] or 0)).quantize(Decimal('0.01'))
        if valor <= 0:
            raise ValueError(f'CarviaFrete {frete.id}: valor considerado invalido ({valor}).')
        fretes_validados.append({'frete': frete, 'valor': valor})
        valor_total += valor

    # --- 1b. Validar e carregar custos de entrega (xerox DespesaExtra Nacom) ---
    custos_validados: List[Dict[str, Any]] = []
    for c in custos_entrega:
        ce = db.session.get(CarviaCustoEntrega, int(c['ce_id']))
        if not ce:
            raise ValueError(f"CarviaCustoEntrega {c['ce_id']} nao encontrado.")
        frete_ce = db.session.get(CarviaFrete, ce.frete_id) if ce.frete_id else None
        # transportadora efetiva = override OU a do frete (paridade Nacom)
        transp_efetiva = ce.transportadora_id or (
            frete_ce.transportadora_id if frete_ce else None
        )
        if transp_efetiva != transportadora_id:
            raise ValueError(
                f'CarviaCustoEntrega {ce.id} pertence a outra transportadora '
                f'({transp_efetiva} != {transportadora_id}).'
            )
        if ce.status in ('CANCELADO', 'PAGO'):
            raise ValueError(f'CarviaCustoEntrega {ce.id} esta {ce.status}.')
        if ce.fatura_transportadora_id:
            raise ValueError(
                f'CarviaCustoEntrega {ce.id} ja vinculado a fatura '
                f'{ce.fatura_transportadora_id}.'
            )
        valor_ce_in = c.get('valor')
        valor_ce = Decimal(
            str(valor_ce_in if valor_ce_in is not None else (ce.valor or 0))
        ).quantize(Decimal('0.01'))
        if valor_ce <= 0:
            raise ValueError(f'CarviaCustoEntrega {ce.id}: valor invalido ({valor_ce}).')
        custos_validados.append({'ce': ce, 'valor': valor_ce})
        valor_total += valor_ce

    # --- 2. Criar a FT sintetica (espelho FaturaFrete Nacom CONFERIDA) ---
    fatura = CarviaFaturaTransportadora(
        transportadora_id=transportadora_id,
        numero_fatura=_gerar_numero_fatura_unico(transportadora, data_vencimento),
        data_emissao=agora.date(),
        valor_total=valor_total,
        vencimento=data_vencimento,
        status_conferencia='CONFERIDO',  # Gate 1: todos os fretes APROVADO abaixo
        conferido_por=usuario_nome,
        conferido_em=agora,
        observacoes_conferencia=(
            'Fatura criada automaticamente via lancamento freteiros '
            f'(Nacom+CarVia). {observacoes}'.strip()
        ),
        criado_por=usuario_nome,
    )
    db.session.add(fatura)
    db.session.flush()  # fatura.id

    # --- 3. Por frete: valores + conferencia + subcontrato + vinculos ---
    subs_criados = 0
    sub_ids: List[int] = []
    for fv in fretes_validados:
        frete, valor = fv['frete'], fv['valor']

        # Identificacao sintetica (paridade Nacom — freteiro nao emite CTe).
        # cte_numero do subcontrato e varchar(20): usar o gerador nativo R8
        # (Sub-###); o descritivo longo "Frete (data) NFs ..." vai p/ observacoes.
        nfs = frete.numeros_nfs or ''
        nfs_str = nfs[:50] + ('...' if len(nfs) > 50 else '')
        descritivo = f"Frete ({agora.date().strftime('%d/%m/%Y')}) NFs {nfs_str}"

        frete.valor_considerado = float(valor)
        frete.valor_cte = float(valor)   # criterio de pendencia (item 1 Rafael)
        frete.valor_pago = float(valor)  # referencia do acerto (paridade Nacom)
        frete.status_conferencia = 'APROVADO'
        frete.conferido_por = usuario_nome
        frete.conferido_em = agora
        frete.detalhes_conferencia = {
            'origem': 'lancamento_freteiros_unificado',
            'valor_cotado': float(frete.valor_cotado or 0),
            'valor_rateado': float(valor),
            'embarque_id': frete.embarque_id,
            'data': agora.isoformat(timespec='seconds'),
        }
        frete.fatura_transportadora_id = fatura.id
        frete.status = 'FATURADO'

        # Subcontrato: reusar existente (novo path frete_id, fallback deprecated)
        sub = frete.subcontratos.first()
        if not sub and frete.subcontrato_id:
            sub = db.session.get(CarviaSubcontrato, frete.subcontrato_id)
        if sub:
            if not sub.fatura_transportadora_id:
                sub.fatura_transportadora_id = fatura.id
            if not sub.cte_numero:
                sub.cte_numero = CarviaSubcontrato.gerar_numero_sub()
            # Sempre sincroniza o valor acertado (sub sintetico de freteiro nao tem
            # CTe real; resultado_frete usa valor_acertado como custo). Na re-emissao
            # apos reversao, o `is None` antigo deixava o valor defasado.
            sub.valor_acertado = valor
            sub.status = 'FATURADO'
        else:
            sub = CarviaSubcontrato(
                operacao_id=frete.operacao_id,  # pode ser NULL
                transportadora_id=frete.transportadora_id,
                cte_numero=CarviaSubcontrato.gerar_numero_sub(),  # R8 (varchar(20))
                valor_cotado=Decimal(str(frete.valor_cotado)) if frete.valor_cotado else None,
                valor_acertado=valor,
                fatura_transportadora_id=fatura.id,
                status='FATURADO',
                criado_por=usuario_nome,
                criado_em=agora,
                observacoes=(
                    f'Criado via Lancamento Freteiros (Nacom+CarVia) — '
                    f'frete #{frete.id} — {descritivo}'
                ),
                frete_id=frete.id,
            )
            db.session.add(sub)
            db.session.flush()
            frete.subcontrato_id = sub.id  # backward compat (FK deprecated)
            subs_criados += 1
        sub_ids.append(sub.id)

    # --- 3b. Vincular custos de entrega a FT (paridade DespesaExtra Nacom) ---
    for cv in custos_validados:
        ce, valor_ce = cv['ce'], cv['valor']
        ce.valor = valor_ce
        ce.fatura_transportadora_id = fatura.id
        ce.tipo_documento = 'CTE'
        ce.numero_documento = f'Custo {ce.tipo_custo}'
        ce.data_vencimento = data_vencimento

    # --- 4. Itens de detalhe da FT (pattern lancar_cte) ---
    linker = LinkingService()
    linker.criar_itens_fatura_transportadora_incremental(fatura.id, sub_ids)

    db.session.flush()
    logger.info(
        f'[FRETEIRO_CARVIA] FT {fatura.id} ({fatura.numero_fatura}) emitida: '
        f'{len(fretes_validados)} fretes, {len(custos_validados)} custos, '
        f'R$ {valor_total}, {subs_criados} subcontratos criados, por {usuario_nome}'
    )
    return {
        'fatura_id': fatura.id,
        'numero_fatura': fatura.numero_fatura,
        'valor_total': float(valor_total),
        'fretes': len(fretes_validados),
        'custos_entrega': len(custos_validados),
        'subcontratos_criados': subs_criados,
    }
