"""Service de Devolucao de Venda (cliente final -> HORA).

Distinto de `devolucao_service` (devolucao ao fornecedor / Motochefe).

Fluxo:
    1. criar_devolucao_de_venda(venda_id, chassis, motivo, ...) — header + N
       itens em 1 commit. Para cada chassi: emite evento DEVOLVIDA. Devolucao
       nasce PENDENTE.
    2. resolver_item(item_id, acao, ...) — uma de:
         - DISPONIVEL    -> emite CONFERIDA (volta ao estoque vendavel)
         - AVARIA        -> avaria_service.registrar_avaria + AVARIADA
         - PECA_FALTANDO -> peca_faltando_service.registrar_peca_faltando + FALTANDO_PECA
       Marca item RESOLVIDA. Quando TODOS os itens estao RESOLVIDA, header vira
       RESOLVIDA automaticamente.
    3. cancelar_devolucao(id) — reverte TODOS os itens cujo ultimo evento ainda
       e DEVOLVIDA emitindo CONFERIDA. Itens ja resolvidos com outra acao
       NAO sao revertidos (preserva consistencia do historico).

Listagem com filtros e helper para buscar motos elegiveis para devolucao
a partir de uma venda (apenas chassis com ultimo evento em VENDIDA/NF_EMITIDA
para nao permitir devolver moto que esta cancelada/devolvida).
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import joinedload

from app import db
from app.hora.models import (
    DEV_VENDA_ACAO_AVARIA,
    DEV_VENDA_ACAO_DISPONIVEL,
    DEV_VENDA_ACAO_PECA_FALTANDO,
    DEV_VENDA_ACOES_VALIDAS,
    DEV_VENDA_ITEM_STATUS_PENDENTE,
    DEV_VENDA_ITEM_STATUS_RESOLVIDA,
    DEV_VENDA_STATUS_CANCELADA,
    DEV_VENDA_STATUS_PENDENTE,
    DEV_VENDA_STATUS_RESOLVIDA,
    HoraDevolucaoVenda,
    HoraDevolucaoVendaItem,
    HoraLoja,
    HoraMoto,
    HoraVenda,
    HoraVendaItem,
    VENDA_STATUS_FATURADO,
)
from app.hora.services.moto_service import registrar_evento, status_atual
from app.utils.timezone import agora_utc_naive


# Eventos que indicam que a moto FOI vendida e portanto pode ser devolvida.
# Inclui tambem RESERVADA por simetria com cancelar_venda (que tambem emite
# DEVOLVIDA), embora o caso pratico de devolucao seja apos VENDIDA/NF_EMITIDA.
_EVENTOS_VENDIDA_DEVOLVIVEL = {'VENDIDA', 'NF_EMITIDA'}


# ---------------------------------------------------------------------------
# Criacao
# ---------------------------------------------------------------------------
def criar_devolucao_de_venda(
    venda_id: int,
    chassis: List[dict],
    motivo: str,
    criado_por: Optional[str] = None,
    loja_id_override: Optional[int] = None,
) -> HoraDevolucaoVenda:
    """Cria header + N itens em 1 transacao + emite DEVOLVIDA por chassi.

    Args:
        venda_id: HoraVenda.id (NF de saida).
        chassis: lista de dicts:
            [{'numero_chassi': str, 'motivo_especifico': str|None}, ...]
        motivo: texto livre OBRIGATORIO (motivo geral da devolucao).
        criado_por: nome do operador.
        loja_id_override: por padrao usa HoraVenda.loja_id; pode ser
            sobrescrito (ex.: cliente devolveu em loja diferente).

    Raises:
        ValueError: motivo vazio, venda inexistente, chassis vazios,
            chassi nao existe, chassi nao pertence a venda, chassi
            duplicado no payload, ou chassi nao esta em estado vendido
            (ultimo evento != VENDIDA/NF_EMITIDA).
    """
    motivo_limpo = (motivo or '').strip()
    if len(motivo_limpo) < 3:
        raise ValueError('motivo da devolucao e obrigatorio (min 3 chars)')

    if not chassis:
        raise ValueError('Selecione ao menos 1 chassi para devolucao.')

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'venda {venda_id} nao encontrada')

    loja_id_efetiva = loja_id_override or venda.loja_id
    if loja_id_efetiva is None:
        raise ValueError(
            'venda sem loja_id e nenhum loja_id_override foi fornecido'
        )
    if not HoraLoja.query.get(loja_id_efetiva):
        raise ValueError(f'loja {loja_id_efetiva} nao encontrada')

    # Map chassi -> venda_item da venda atual (1 query).
    venda_itens = HoraVendaItem.query.filter_by(venda_id=venda.id).all()
    chassis_da_venda = {vi.numero_chassi: vi for vi in venda_itens}

    # Pre-validacao de duplicados e existencia.
    # Lock pessimista (SELECT FOR UPDATE) em hora_moto serializa concorrencia
    # com cancelar_venda / outra criar_devolucao_de_venda no mesmo chassi —
    # mesmo padrao de venda_service._lock_chassi_e_validar_disponivel.
    chassis_vistos = set()
    chassis_normalizados: List[dict] = []
    for c in chassis:
        chassi = (c.get('numero_chassi') or '').strip().upper()
        if not chassi:
            raise ValueError('chassi vazio no payload de devolucao')
        if chassi in chassis_vistos:
            raise ValueError(f'chassi {chassi} duplicado no payload')
        chassis_vistos.add(chassi)
        if chassi not in chassis_da_venda:
            raise ValueError(
                f'chassi {chassi} nao pertence a venda #{venda.id}'
            )

        # SELECT FOR UPDATE: bloqueia a linha em hora_moto durante esta
        # transacao. Outras transacoes que tentem ler a mesma linha com
        # FOR UPDATE ficam em wait. Releitura de status_atual depois do
        # lock garante que ninguem mudou o ultimo evento entre nossa
        # decisao e o INSERT da DEVOLVIDA.
        moto = HoraMoto.query.with_for_update().get(chassi)
        if not moto:
            raise ValueError(f'chassi {chassi} nao existe em hora_moto')

        ult = status_atual(chassi)
        if ult not in _EVENTOS_VENDIDA_DEVOLVIVEL:
            raise ValueError(
                f'chassi {chassi} nao esta em estado vendido (ultimo '
                f'evento: {ult}). Nao pode ser devolvido.'
            )

        chassis_normalizados.append({
            'numero_chassi': chassi,
            'motivo_especifico': (c.get('motivo_especifico') or '').strip() or None,
            'venda_item_id': chassis_da_venda[chassi].id,
        })

    # Cria header.
    dev = HoraDevolucaoVenda(
        venda_id=venda.id,
        loja_id=loja_id_efetiva,
        motivo=motivo_limpo,
        status=DEV_VENDA_STATUS_PENDENTE,
        data_devolucao=agora_utc_naive().date(),
        criado_por=criado_por,
    )
    db.session.add(dev)
    db.session.flush()  # gera dev.id

    # Cria itens + emite eventos DEVOLVIDA.
    for c in chassis_normalizados:
        item = HoraDevolucaoVendaItem(
            devolucao_id=dev.id,
            numero_chassi=c['numero_chassi'],
            venda_item_id=c['venda_item_id'],
            motivo_especifico=c['motivo_especifico'],
        )
        db.session.add(item)
        db.session.flush()
        registrar_evento(
            numero_chassi=c['numero_chassi'],
            tipo='DEVOLVIDA',
            origem_tabela='hora_devolucao_venda_item',
            origem_id=item.id,
            loja_id=loja_id_efetiva,
            operador=criado_por,
            detalhe=(
                f'Devolucao de venda #{dev.id} '
                f'(NF venda #{venda.id}). Motivo: {motivo_limpo[:120]}'
            ),
        )

    db.session.commit()
    return dev


# ---------------------------------------------------------------------------
# Resolucao
# ---------------------------------------------------------------------------
def resolver_item(
    item_id: int,
    acao: str,
    operador: Optional[str] = None,
    observacoes: Optional[str] = None,
    avaria_descricao: Optional[str] = None,
    peca_descricao: Optional[str] = None,
) -> dict:
    """Aplica resolucao em UM item de devolucao de venda.

    Args:
        item_id: id do HoraDevolucaoVendaItem.
        acao: DEV_VENDA_ACAO_DISPONIVEL | _AVARIA | _PECA_FALTANDO.
        operador: nome do usuario.
        observacoes: texto livre (opcional para DISPONIVEL,
            obrigatorio para AVARIA/PECA_FALTANDO se especifica nao for fornecida).
        avaria_descricao: obrigatorio se acao=AVARIA. Texto que ira em
            HoraAvaria.descricao.
        peca_descricao: obrigatorio se acao=PECA_FALTANDO. Texto que ira
            em HoraPecaFaltando.descricao.

    Returns: dict com {ok, item_id, acao, avaria_id?, peca_faltando_id?}.

    Raises:
        ValueError: acao invalida, item nao encontrado, item ja resolvido,
            devolucao cancelada, descricao obrigatoria ausente, ou ultimo
            evento do chassi nao e DEVOLVIDA (estado inconsistente —
            algum outro processo tocou o chassi entre criar e resolver).
    """
    if acao not in DEV_VENDA_ACOES_VALIDAS:
        raise ValueError(
            f'acao invalida: {acao}. Aceitos: {DEV_VENDA_ACOES_VALIDAS}'
        )

    item = HoraDevolucaoVendaItem.query.get(item_id)
    if not item:
        raise ValueError(f'item {item_id} nao encontrado')
    if item.status_item == DEV_VENDA_ITEM_STATUS_RESOLVIDA:
        raise ValueError(
            f'item {item_id} ja esta resolvido (acao={item.resolucao_acao})'
        )

    dev = HoraDevolucaoVenda.query.get(item.devolucao_id)
    if not dev:
        raise ValueError(f'devolucao do item {item_id} nao encontrada')
    if dev.status == DEV_VENDA_STATUS_CANCELADA:
        raise ValueError(
            f'devolucao #{dev.id} esta CANCELADA — nao e possivel resolver itens'
        )

    # Defesa: o ultimo evento do chassi precisa ser DEVOLVIDA, senao algo
    # tocou o chassi entre criar e resolver (race / acao manual).
    ult = status_atual(item.numero_chassi)
    if ult != 'DEVOLVIDA':
        raise ValueError(
            f'chassi {item.numero_chassi} nao esta DEVOLVIDA (ultimo '
            f'evento: {ult}). Resolucao bloqueada para evitar inconsistencia.'
        )

    obs_limpa = (observacoes or '').strip() or None

    resultado = {'ok': True, 'item_id': item.id, 'acao': acao}

    if acao == DEV_VENDA_ACAO_DISPONIVEL:
        # Volta ao estoque: emite CONFERIDA na loja da devolucao.
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='CONFERIDA',
            origem_tabela='hora_devolucao_venda_item',
            origem_id=item.id,
            loja_id=dev.loja_id,
            operador=operador,
            detalhe=(
                f'Devolucao venda #{dev.id} resolvida como DISPONIVEL. '
                f'{obs_limpa or ""}'
            ).strip(),
        )

    elif acao == DEV_VENDA_ACAO_AVARIA:
        desc = (avaria_descricao or obs_limpa or '').strip()
        if len(desc) < 3:
            raise ValueError(
                'Para acao AVARIA: avaria_descricao (ou observacoes) >= 3 chars.'
            )
        # avaria_service exige que o ultimo evento esteja em EVENTOS_EM_ESTOQUE,
        # mas o nosso atual e DEVOLVIDA. Estrategia: emitir CONFERIDA primeiro
        # (volta ao estoque), depois registrar a avaria — que emite AVARIADA.
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='CONFERIDA',
            origem_tabela='hora_devolucao_venda_item',
            origem_id=item.id,
            loja_id=dev.loja_id,
            operador=operador,
            detalhe=f'Devolucao venda #{dev.id} -> reentrada para registrar avaria.',
        )
        # Import tardio evita ciclo.
        from app.hora.services.avaria_service import registrar_avaria
        avaria = registrar_avaria(
            numero_chassi=item.numero_chassi,
            descricao=desc,
            fotos=[],  # fotos podem ser anexadas depois pela tela de avaria
            usuario=operador or 'sistema',
            loja_id=dev.loja_id,
        )
        item.avaria_id = avaria.id
        resultado['avaria_id'] = avaria.id

    elif acao == DEV_VENDA_ACAO_PECA_FALTANDO:
        desc = (peca_descricao or obs_limpa or '').strip()
        if len(desc) < 3:
            raise ValueError(
                'Para acao PECA_FALTANDO: peca_descricao (ou observacoes) >= 3 chars.'
            )
        # Mesma estrategia: CONFERIDA primeiro para sair do estado DEVOLVIDA.
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='CONFERIDA',
            origem_tabela='hora_devolucao_venda_item',
            origem_id=item.id,
            loja_id=dev.loja_id,
            operador=operador,
            detalhe=f'Devolucao venda #{dev.id} -> reentrada para registrar peca faltando.',
        )
        from app.hora.services.peca_faltando_service import registrar_peca_faltando
        # commit=False mantem atomicidade: peca_faltando_service so flush,
        # commit final ocorre apenas no db.session.commit() ao fim deste
        # resolver_item. Sem isso, o commit interno do peca_faltando_service
        # tornaria a CONFERIDA + HoraPecaFaltando + FALTANDO_PECA permanentes
        # antes de marcarmos item.status_item=RESOLVIDA — risco de estado
        # inconsistente se algo falhar entre as duas etapas.
        peca = registrar_peca_faltando(
            numero_chassi=item.numero_chassi,
            descricao=desc,
            loja_id=dev.loja_id,
            observacoes=f'Originada de devolucao de venda #{dev.id}.',
            criado_por=operador,
            commit=False,
        )
        item.peca_faltando_id = peca.id
        resultado['peca_faltando_id'] = peca.id

    # Marca item resolvido.
    item.status_item = DEV_VENDA_ITEM_STATUS_RESOLVIDA
    item.resolucao_acao = acao
    item.resolucao_observacoes = obs_limpa
    item.resolvida_em = agora_utc_naive()
    item.resolvida_por = operador

    # Recalcula status do header: se TODOS itens resolvidos, marca RESOLVIDA.
    pendentes_restantes = (
        HoraDevolucaoVendaItem.query
        .filter(
            HoraDevolucaoVendaItem.devolucao_id == dev.id,
            HoraDevolucaoVendaItem.id != item.id,
            HoraDevolucaoVendaItem.status_item == DEV_VENDA_ITEM_STATUS_PENDENTE,
        )
        .count()
    )
    if pendentes_restantes == 0:
        dev.status = DEV_VENDA_STATUS_RESOLVIDA
        dev.data_resolucao = agora_utc_naive().date()
        dev.resolvida_por = operador

    db.session.commit()
    return resultado


# ---------------------------------------------------------------------------
# Cancelamento
# ---------------------------------------------------------------------------
def cancelar_devolucao(
    devolucao_id: int,
    motivo_cancelamento: str,
    operador: Optional[str] = None,
) -> HoraDevolucaoVenda:
    """Cancela a devolucao. Para cada item cuja moto AINDA esta DEVOLVIDA
    (resolucao nao foi aplicada), emite CONFERIDA para devolver ao estoque.
    Itens ja resolvidos com outra acao (AVARIA/PECA_FALTANDO/DISPONIVEL)
    permanecem como estao — o cancelamento nao tenta desfazer historico.
    """
    motivo_limpo = (motivo_cancelamento or '').strip()
    if len(motivo_limpo) < 3:
        raise ValueError('motivo do cancelamento e obrigatorio (min 3 chars)')

    dev = HoraDevolucaoVenda.query.get(devolucao_id)
    if not dev:
        raise ValueError(f'devolucao {devolucao_id} nao encontrada')
    if dev.status == DEV_VENDA_STATUS_CANCELADA:
        raise ValueError('devolucao ja esta CANCELADA')

    skipped: List[tuple] = []
    revertidos: List[str] = []

    for item in dev.itens:
        ult = status_atual(item.numero_chassi)
        if ult == 'DEVOLVIDA':
            registrar_evento(
                numero_chassi=item.numero_chassi,
                tipo='CONFERIDA',
                origem_tabela='hora_devolucao_venda_item',
                origem_id=item.id,
                loja_id=dev.loja_id,
                operador=operador,
                detalhe=f'Cancelamento devolucao venda #{dev.id}',
            )
            revertidos.append(item.numero_chassi)
        else:
            skipped.append((item.numero_chassi, ult))

    dev.status = DEV_VENDA_STATUS_CANCELADA
    dev.cancelamento_motivo = motivo_limpo
    dev.cancelada_por = operador

    nota_extra = ''
    if skipped:
        nota_extra = (
            '\n[CANCELAMENTO] Chassis com evento posterior (NAO restaurados): '
            + ', '.join(f'{c}={st}' for c, st in skipped)
        )
    if nota_extra:
        dev.motivo = (dev.motivo or '') + nota_extra

    db.session.commit()
    return dev


# ---------------------------------------------------------------------------
# Consulta
# ---------------------------------------------------------------------------
def listar_devolucoes(
    status: Optional[str] = None,
    loja_id: Optional[int] = None,
    lojas_permitidas_ids: Optional[List[int]] = None,
    chassi: Optional[str] = None,
    venda_id: Optional[int] = None,
    nf_saida: Optional[str] = None,
    motivo: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limit: int = 200,
) -> List[HoraDevolucaoVenda]:
    q = (
        HoraDevolucaoVenda.query
        .options(
            joinedload(HoraDevolucaoVenda.venda),
            joinedload(HoraDevolucaoVenda.loja),
            joinedload(HoraDevolucaoVenda.itens),
        )
        .order_by(
            HoraDevolucaoVenda.data_devolucao.desc(),
            HoraDevolucaoVenda.id.desc(),
        )
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraDevolucaoVenda.loja_id.in_(lojas_permitidas_ids))
    if loja_id:
        q = q.filter(HoraDevolucaoVenda.loja_id == loja_id)
    if status:
        q = q.filter(HoraDevolucaoVenda.status == status)
    if venda_id:
        q = q.filter(HoraDevolucaoVenda.venda_id == venda_id)
    if motivo:
        q = q.filter(HoraDevolucaoVenda.motivo.ilike(f'%{motivo.strip()}%'))
    if data_inicio:
        q = q.filter(HoraDevolucaoVenda.data_devolucao >= data_inicio)
    if data_fim:
        q = q.filter(HoraDevolucaoVenda.data_devolucao <= data_fim)

    if nf_saida:
        nf_norm = nf_saida.strip()
        sub = (
            db.session.query(HoraVenda.id)
            .filter(HoraVenda.nf_saida_numero.ilike(f'%{nf_norm}%'))
            .subquery()
        )
        q = q.filter(HoraDevolucaoVenda.venda_id.in_(sub))

    if chassi:
        c = chassi.strip().upper()
        sub = (
            db.session.query(HoraDevolucaoVendaItem.devolucao_id)
            .filter(HoraDevolucaoVendaItem.numero_chassi.ilike(f'%{c}%'))
            .distinct()
            .subquery()
        )
        q = q.filter(HoraDevolucaoVenda.id.in_(sub))

    return q.limit(limit).all()


def buscar_vendas_para_devolucao(
    termo: str,
    lojas_permitidas_ids: Optional[List[int]] = None,
    limit: int = 30,
) -> List[dict]:
    """Pesquisa NFs de venda elegiveis para devolucao.

    Aceita termo livre que tenta casar:
      - nf_saida_numero (ilike substring)
      - nome_cliente (ilike)
      - cpf_cliente (digits-only contains)
      - id da venda (se termo e numerico)

    Considera apenas vendas FATURADO (NF emitida) — nao faz sentido devolver
    pedido em COTACAO/CONFIRMADO (cliente ainda nao recebeu) nem CANCELADO.
    """
    termo = (termo or '').strip()
    if not termo:
        return []

    q = HoraVenda.query.filter(HoraVenda.status == VENDA_STATUS_FATURADO)
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraVenda.loja_id.in_(lojas_permitidas_ids))

    from sqlalchemy import or_

    cond = []
    cond.append(HoraVenda.nf_saida_numero.ilike(f'%{termo}%'))
    cond.append(HoraVenda.nome_cliente.ilike(f'%{termo}%'))
    digits = ''.join(c for c in termo if c.isdigit())
    if digits:
        cond.append(HoraVenda.cpf_cliente.ilike(f'%{digits}%'))
        # ID exato so casa se termo inteiro for numerico (evita confundir com CPF).
        if termo.isdigit():
            try:
                cond.append(HoraVenda.id == int(termo))
            except (TypeError, ValueError):
                pass

    q = (
        q.filter(or_(*cond))
        .order_by(HoraVenda.data_venda.desc(), HoraVenda.id.desc())
        .limit(limit)
    )

    return [
        {
            'id': v.id,
            'nf_saida_numero': v.nf_saida_numero,
            'nome_cliente': v.nome_cliente,
            'cpf_cliente': v.cpf_cliente,
            'data_venda': (
                v.data_venda.strftime('%d/%m/%Y') if v.data_venda else None
            ),
            'loja_id': v.loja_id,
            'loja_nome': v.loja.rotulo_display if v.loja else None,
            'valor_total': float(v.valor_total) if v.valor_total else None,
            'status': v.status,
        }
        for v in q.all()
    ]


def motos_da_venda_devolviveis(venda_id: int) -> List[dict]:
    """Lista chassis da venda elegiveis para devolucao.

    Elegivel = ultimo evento do chassi esta em VENDIDA ou NF_EMITIDA.
    Chassis ja DEVOLVIDA (em devolucao anterior pendente) ou em outro estado
    sao retornados com flag `elegivel=False` para a UI exibir e bloquear
    selecao.
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        return []

    itens = (
        HoraVendaItem.query
        .filter_by(venda_id=venda.id)
        .options(joinedload(HoraVendaItem.moto))
        .all()
    )
    if not itens:
        return []

    resultado = []
    for vi in itens:
        ult = status_atual(vi.numero_chassi)
        elegivel = ult in _EVENTOS_VENDIDA_DEVOLVIVEL
        resultado.append({
            'venda_item_id': vi.id,
            'numero_chassi': vi.numero_chassi,
            'modelo_nome': (
                vi.moto.modelo.nome_modelo if vi.moto and vi.moto.modelo else None
            ),
            'cor': vi.moto.cor if vi.moto else None,
            'preco_final': float(vi.preco_final) if vi.preco_final else None,
            'ultimo_evento': ult,
            'elegivel': elegivel,
            'motivo_inelegivel': (
                None if elegivel
                else f'ultimo evento e {ult or "—"}, esperado VENDIDA/NF_EMITIDA'
            ),
        })
    return resultado


def listar_devolucoes_por_chassi(numero_chassi: str) -> List[HoraDevolucaoVenda]:
    """Para `rastreamento_completo` — todas as devolucoes de venda que tocam
    o chassi, mais recentes primeiro."""
    chassi = (numero_chassi or '').strip().upper()
    if not chassi:
        return []
    return (
        HoraDevolucaoVenda.query
        .join(
            HoraDevolucaoVendaItem,
            HoraDevolucaoVendaItem.devolucao_id == HoraDevolucaoVenda.id,
        )
        .filter(HoraDevolucaoVendaItem.numero_chassi == chassi)
        .distinct()
        .order_by(HoraDevolucaoVenda.criado_em.desc())
        .all()
    )
