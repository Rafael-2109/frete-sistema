"""Estoque HORA: calcula estoque por loja a partir do ultimo evento de cada moto.

Regra (invariante 4): estado atual = ultimo HoraMotoEvento por chassi.
"Em estoque" = chassi cujo ultimo evento esta em `EVENTOS_EM_ESTOQUE` e a loja
do evento e a loja onde a moto esta.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import and_, func

from app import db
from app.hora.models import (
    HoraLoja,
    HoraModelo,
    HoraMoto,
    HoraMotoEvento,
)


# Eventos que significam "moto esta no estoque da loja do evento"
EVENTOS_EM_ESTOQUE = (
    'RECEBIDA', 'CONFERIDA', 'TRANSFERIDA',
    'CANCELADA',  # transferencia cancelada — moto voltou a origem
    'AVARIADA', 'FALTANDO_PECA',
    # Emprestimo: chassi externo recebido entra como disponivel para venda;
    # ressarcimento que CHEGA tambem (chassi novo entra resolvendo SAIDA).
    'EMPRESTIMO_ENTRADA', 'RESSARCIMENTO_SAIDA',
)
# Eventos que tiram a moto do estoque
# - RESERVADA: pedido de venda em COTACAO/CONFIRMADO. Reservada por hora_venda.
# - VENDIDA, NF_EMITIDA: pedido FATURADO (NFe emitida via TagPlus ou DANFE legado).
# - DEVOLVIDA: moto saiu por devolucao ao fornecedor OU pedido cancelado.
# - NF_CANCELADA: NFe foi cancelada na SEFAZ; pedido pode estar em CONFIRMADO.
# - EMPRESTIMO_SAIDA: chassi nosso emprestado para loja externa (fora estoque).
# - RESSARCIMENTO_ENTRADA: chassi nosso enviado para fechar emprestimo ENTRADA.
EVENTOS_FORA_ESTOQUE = (
    'RESERVADA', 'VENDIDA', 'DEVOLVIDA', 'NF_EMITIDA', 'NF_CANCELADA',
    'EMPRESTIMO_SAIDA', 'RESSARCIMENTO_ENTRADA',
)
# Eventos "em limbo" — nao estao no estoque de nenhuma loja
EVENTOS_EM_TRANSITO = ('EM_TRANSITO',)

# Eventos que indicam chassi declarado em NF mas que NAO chegou fisicamente.
# Emitido por finalizar_recebimento no batch de faltantes. Categoria propria:
# nao conta como disponivel para venda, nao e "fora de estoque" (a moto nunca
# saiu — ela nunca chegou). UI mostra via filtro de status para operador
# resolver (ajuste no recebimento ou correcao na NF — recebimento e SOT).
EVENTOS_FALTANDO_FISICAMENTE = ('MOTO_FALTANDO',)


def _subquery_ultimo_evento_id():
    """Subquery: para cada chassi, o id do evento mais recente."""
    return (
        db.session.query(
            HoraMotoEvento.numero_chassi.label('chassi'),
            func.max(HoraMotoEvento.id).label('max_id'),
        )
        .group_by(HoraMotoEvento.numero_chassi)
        .subquery()
    )


def _nf_recebimento_por_chassi(chassis: List[str]) -> Dict[str, dict]:
    """Para cada chassi, retorna {nf_id, nf_numero, nf_serie, recebimento_id}
    do recebimento/conferencia de entrada mais recente. Silenciosamente omite
    chassis sem conferencia.
    """
    if not chassis:
        return {}
    from app.hora.models import HoraNfEntrada, HoraRecebimento, HoraRecebimentoConferencia

    chassis_norm = [c.strip().upper() for c in chassis]
    # Pega a conferencia ativa mais recente por chassi.
    sub = (
        db.session.query(
            HoraRecebimentoConferencia.numero_chassi.label('chassi'),
            func.max(HoraRecebimentoConferencia.id).label('max_id'),
        )
        .filter(
            HoraRecebimentoConferencia.numero_chassi.in_(chassis_norm),
            HoraRecebimentoConferencia.substituida.is_(False),
        )
        .group_by(HoraRecebimentoConferencia.numero_chassi)
        .subquery()
    )
    rows = (
        db.session.query(
            HoraRecebimentoConferencia.numero_chassi,
            HoraRecebimento.id.label('recebimento_id'),
            HoraNfEntrada.id.label('nf_id'),
            HoraNfEntrada.numero_nf.label('nf_numero'),
            HoraNfEntrada.serie_nf.label('nf_serie'),
        )
        .join(sub, HoraRecebimentoConferencia.id == sub.c.max_id)
        .join(HoraRecebimento, HoraRecebimento.id == HoraRecebimentoConferencia.recebimento_id)
        .join(HoraNfEntrada, HoraNfEntrada.id == HoraRecebimento.nf_id)
        .all()
    )
    return {
        r.numero_chassi: {
            'nf_id': r.nf_id,
            'nf_numero': r.nf_numero,
            'nf_serie': r.nf_serie,
            'recebimento_id': r.recebimento_id,
        }
        for r in rows
    }


def _venda_nf_saida_por_chassi(chassis: List[str]) -> Dict[str, dict]:
    """Para cada chassi, retorna {venda_id, nf_saida_numero, nf_saida_chave_44,
    venda_status, tem_pdf, tem_nfe_tagplus, nfe_status} da venda ATIVA.

    - `tem_pdf`: HoraVenda.arquivo_pdf_s3_key (DANFE legado importado via PDF)
    - `tem_nfe_tagplus`: existe HoraTagPlusNfeEmissao APROVADA com tagplus_nfe_id
      (NFe emitida pelo TagPlus — DANFE servido on-the-fly por
      `hora.venda_nfe_danfe_pdf` via proxy `/nfes/pdf/recibo_a4/{id}`)
    - `nfe_status`: status atual da emissao TagPlus (None se sem emissao)

    Inclui pedidos em qualquer status (COTACAO, CONFIRMADO, FATURADO, CANCELADO)
    para que a UI possa exibir badge apropriado. UI deve filtrar por status para
    decidir como exibir (ex.: "Reservado em pedido #X COTACAO" vs "Vendido na NF").
    """
    if not chassis:
        return {}
    from app.hora.models import HoraVenda, HoraVendaItem
    from app.hora.models.tagplus import HoraTagPlusNfeEmissao

    chassis_norm = [c.strip().upper() for c in chassis]
    rows = (
        db.session.query(
            HoraVendaItem.numero_chassi,
            HoraVenda.id.label('venda_id'),
            HoraVenda.nf_saida_numero,
            HoraVenda.nf_saida_chave_44,
            HoraVenda.status.label('venda_status'),
            HoraVenda.arquivo_pdf_s3_key,
            HoraTagPlusNfeEmissao.status.label('nfe_status'),
            HoraTagPlusNfeEmissao.tagplus_nfe_id,
        )
        .join(HoraVenda, HoraVenda.id == HoraVendaItem.venda_id)
        .outerjoin(
            HoraTagPlusNfeEmissao,
            HoraTagPlusNfeEmissao.venda_id == HoraVenda.id,
        )
        .filter(HoraVendaItem.numero_chassi.in_(chassis_norm))
        .all()
    )
    # Em caso de multiplas vendas (chassi reservado, cancelado, re-reservado),
    # priorizar a ATIVA (nao-CANCELADO) sobre CANCELADO. Como UNIQUE em
    # numero_chassi e em hora_venda_item, na pratica so havera 1 — mas se uma
    # venda for cancelada via cancelar_venda, o chassi volta ao estoque e pode
    # ser reservado de novo, criando um novo item com mesmo chassi (a UNIQUE
    # em hora_venda_item.numero_chassi REJEITA isso). Workaround: hoje o item
    # antigo permanece com a venda CANCELADA. Aceitar 1 por chassi.
    return {
        r.numero_chassi: {
            'venda_id': r.venda_id,
            'nf_saida_numero': r.nf_saida_numero,
            'nf_saida_chave_44': r.nf_saida_chave_44,
            'venda_status': r.venda_status,
            'tem_pdf': bool(r.arquivo_pdf_s3_key),
            'tem_nfe_tagplus': bool(r.tagplus_nfe_id and r.nfe_status == 'APROVADA'),
            'nfe_status': r.nfe_status,
        }
        for r in rows
    }


def chassis_reservados_em_pedido(venda_id: int) -> List[str]:
    """Lista chassis atualmente reservados (ultimo evento RESERVADA) para o pedido."""
    from app.hora.models import HoraVendaItem
    sub = _subquery_ultimo_evento_id()
    rows = (
        db.session.query(HoraVendaItem.numero_chassi)
        .join(
            HoraMotoEvento,
            and_(
                HoraMotoEvento.numero_chassi == HoraVendaItem.numero_chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(sub, HoraVendaItem.numero_chassi == sub.c.chassi)
        .filter(
            HoraVendaItem.venda_id == venda_id,
            HoraMotoEvento.tipo == 'RESERVADA',
        )
        .all()
    )
    return [r[0] for r in rows]


def _pecas_abertas_por_chassi(chassis: List[str]) -> Dict[str, int]:
    """Count de pecas faltando ABERTA por chassi."""
    if not chassis:
        return {}
    from app.hora.models import HoraPecaFaltando

    chassis_norm = [c.strip().upper() for c in chassis]
    rows = (
        db.session.query(
            HoraPecaFaltando.numero_chassi,
            func.count(HoraPecaFaltando.id),
        )
        .filter(
            HoraPecaFaltando.numero_chassi.in_(chassis_norm),
            HoraPecaFaltando.status == 'ABERTA',
        )
        .group_by(HoraPecaFaltando.numero_chassi)
        .all()
    )
    return {chassi: count for chassi, count in rows}


def _transferencias_em_transito_por_chassi(chassis: List[str]) -> Dict[str, int]:
    """Count de transferencias cujo item aponta para chassi e ainda nao
    foi confirmado no destino (conferido_destino_em IS NULL).
    Conta apenas transferencias com status EM_TRANSITO.
    """
    if not chassis:
        return {}
    from app.hora.models import HoraTransferencia, HoraTransferenciaItem

    chassis_norm = [c.strip().upper() for c in chassis]
    rows = (
        db.session.query(
            HoraTransferenciaItem.numero_chassi,
            func.count(HoraTransferenciaItem.id),
        )
        .join(HoraTransferencia, HoraTransferencia.id == HoraTransferenciaItem.transferencia_id)
        .filter(
            HoraTransferenciaItem.numero_chassi.in_(chassis_norm),
            HoraTransferencia.status == 'EM_TRANSITO',
            HoraTransferenciaItem.conferido_destino_em.is_(None),
        )
        .group_by(HoraTransferenciaItem.numero_chassi)
        .all()
    )
    return {chassi: count for chassi, count in rows}


def listar_estoque(
    loja_id: Optional[int] = None,
    modelo_id: Optional[int] = None,
    cor: Optional[str] = None,
    incluir_avariadas: bool = True,
    incluir_faltando_peca: bool = True,
    incluir_fora_estoque: bool = False,
    lojas_permitidas_ids: Optional[List[int]] = None,
    pedido_id: Optional[int] = None,
    nf_entrada_id: Optional[int] = None,
    venda_id: Optional[int] = None,
    chassi: Optional[str] = None,
    status: Optional[str] = None,
) -> List[dict]:
    """Lista motos chassi-a-chassi.

    Comportamento por valor de `status`:
      - None / 'disponivel': default — motos cujo ultimo evento esta em
        EVENTOS_EM_ESTOQUE (respeita flags `incluir_avariadas` e
        `incluir_faltando_peca`).
      - 'MOTO_FALTANDO': apenas chassis cujo ultimo evento e MOTO_FALTANDO
        (declarado em NF mas nao chegou fisicamente).
      - 'AVARIADA' / 'FALTANDO_PECA' / 'EM_TRANSITO' / 'VENDIDA' /
        'DEVOLVIDA' / 'RESERVADA': apenas chassis com aquele ultimo evento.

    Quando `incluir_fora_estoque=True` (compatibilidade): TODAS as motos
    cadastradas (inclusive VENDIDA, DEVOLVIDA, EM_TRANSITO) com flag
    `moto_disponivel`. Ignorado se `status` for explicito.

    Filtros por documento (pedido/NF entrada/venda):
      - `pedido_id`: chassis presentes em HoraPedidoItem.pedido_id=X
      - `nf_entrada_id`: chassis presentes em HoraNfEntradaItem.nf_id=X
      - `venda_id`: chassis presentes em HoraVendaItem.venda_id=X
    Filtro por chassi (substring, case-insensitive): `chassi='ABC123'`.

    Retorna dicts com: chassi, modelo_*, cor, loja_*, ultimo_evento, ...,
    nf_id, nf_numero, nf_serie, recebimento_id, avarias_abertas,
    pecas_faltando_abertas, transferencias_em_transito, moto_disponivel,
    moto_faltando, venda_id, nf_saida_numero.
    """
    from app.hora.models import HoraNfEntradaItem, HoraPedidoItem, HoraVendaItem

    status_norm = (status or '').strip().upper() or None
    # Status explicito sobrescreve incluir_fora_estoque e ignora os flags.
    if status_norm and status_norm != 'DISPONIVEL':
        tipos = [status_norm]
    elif incluir_fora_estoque:
        tipos = None  # sem filtro de tipo
    else:
        tipos = list(EVENTOS_EM_ESTOQUE)
        if not incluir_avariadas:
            tipos = [t for t in tipos if t != 'AVARIADA']
        if not incluir_faltando_peca:
            tipos = [t for t in tipos if t != 'FALTANDO_PECA']

    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(HoraMotoEvento, HoraMoto, HoraModelo, HoraLoja)
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraMoto, HoraMotoEvento.numero_chassi == HoraMoto.numero_chassi)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .outerjoin(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
    )
    if tipos is not None:
        q = q.filter(HoraMotoEvento.tipo.in_(tipos))

    if loja_id:
        q = q.filter(HoraMotoEvento.loja_id == loja_id)
    if modelo_id:
        q = q.filter(HoraMoto.modelo_id == modelo_id)
    if cor:
        q = q.filter(HoraMoto.cor == cor.strip().upper())

    # Filtros por documento — cada um restringe aos chassis presentes no doc.
    if pedido_id:
        chassis_pedido = (
            db.session.query(HoraPedidoItem.numero_chassi)
            .filter(
                HoraPedidoItem.pedido_id == pedido_id,
                HoraPedidoItem.numero_chassi.isnot(None),
            )
            .subquery()
        )
        q = q.filter(HoraMoto.numero_chassi.in_(chassis_pedido))
    if nf_entrada_id:
        chassis_nf = (
            db.session.query(HoraNfEntradaItem.numero_chassi)
            .filter(HoraNfEntradaItem.nf_id == nf_entrada_id)
            .subquery()
        )
        q = q.filter(HoraMoto.numero_chassi.in_(chassis_nf))
    if venda_id:
        chassis_venda = (
            db.session.query(HoraVendaItem.numero_chassi)
            .filter(HoraVendaItem.venda_id == venda_id)
            .subquery()
        )
        q = q.filter(HoraMoto.numero_chassi.in_(chassis_venda))

    # Filtro por chassi (substring case-insensitive).
    if chassi:
        chassi_norm = chassi.strip().upper()
        if chassi_norm:
            q = q.filter(HoraMoto.numero_chassi.ilike(f'%{chassi_norm}%'))
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        if incluir_fora_estoque:
            # Para "fora de estoque": ultimo evento pode ter loja_id NULL
            # (ex.: VENDIDA). Garantir autorizacao via subquery que exige
            # que ESTE chassi ja teve ao menos 1 evento em loja permitida.
            chassis_permitidos = (
                db.session.query(HoraMotoEvento.numero_chassi)
                .filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))
                .distinct()
                .subquery()
            )
            q = q.filter(HoraMotoEvento.numero_chassi.in_(chassis_permitidos))
        else:
            q = q.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    q = q.order_by(HoraMotoEvento.timestamp.desc())

    resultado = []
    for ev, moto, modelo, loja in q.all():
        resultado.append({
            'chassi': moto.numero_chassi,
            'modelo_id': modelo.id,
            'modelo_nome': modelo.nome_modelo,
            'cor': moto.cor,
            'motor': moto.numero_motor,
            'ano_modelo': moto.ano_modelo,
            'loja_id': loja.id if loja else None,
            'loja_nome': loja.rotulo_display if loja else None,
            'ultimo_evento': ev.tipo,
            'ultimo_evento_em': ev.timestamp,
            'ultimo_evento_detalhe': ev.detalhe,
            'moto_disponivel': ev.tipo in EVENTOS_EM_ESTOQUE,
            'moto_faltando': ev.tipo in EVENTOS_FALTANDO_FISICAMENTE,
        })

    # ------------------------------------------------------------------
    # Chassis "puros" (em hora_moto mas SEM evento ainda) — somente se a
    # listagem foi pedida com `incluir_fora_estoque=True`. Esses chassis
    # vem de pedido/NF entrada/venda mas ainda nao tiveram o primeiro
    # evento (RECEBIDA so nasce no recebimento fisico). Aparecem como
    # "Aguardando NF" na UI.
    # ------------------------------------------------------------------
    if incluir_fora_estoque:
        from app.hora.services.auth_helper import chassis_acessiveis_subquery

        chassis_com_evento_subq = (
            db.session.query(HoraMotoEvento.numero_chassi).distinct().subquery()
        )

        qb = (
            db.session.query(HoraMoto, HoraModelo)
            .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
            .filter(~HoraMoto.numero_chassi.in_(chassis_com_evento_subq))
        )
        if modelo_id:
            qb = qb.filter(HoraMoto.modelo_id == modelo_id)
        if cor:
            qb = qb.filter(HoraMoto.cor == cor.strip().upper())
        if chassi:
            chassi_norm = chassi.strip().upper()
            if chassi_norm:
                qb = qb.filter(HoraMoto.numero_chassi.ilike(f'%{chassi_norm}%'))
        if pedido_id:
            qb = qb.filter(HoraMoto.numero_chassi.in_(
                db.session.query(HoraPedidoItem.numero_chassi)
                .filter(
                    HoraPedidoItem.pedido_id == pedido_id,
                    HoraPedidoItem.numero_chassi.isnot(None),
                )
            ))
        if nf_entrada_id:
            qb = qb.filter(HoraMoto.numero_chassi.in_(
                db.session.query(HoraNfEntradaItem.numero_chassi)
                .filter(HoraNfEntradaItem.nf_id == nf_entrada_id)
            ))
        if venda_id:
            qb = qb.filter(HoraMoto.numero_chassi.in_(
                db.session.query(HoraVendaItem.numero_chassi)
                .filter(HoraVendaItem.venda_id == venda_id)
            ))
        # Filtro explicito por loja_id: aplicar via mesma helper de
        # autorizacao com lista [loja_id] (cobre pedido/NF/venda).
        if loja_id:
            subq_loja = chassis_acessiveis_subquery([loja_id])
            if subq_loja is not None:
                qb = qb.filter(HoraMoto.numero_chassi.in_(subq_loja))
        # Autorizacao por usuario escopado.
        if lojas_permitidas_ids is not None:
            if not lojas_permitidas_ids:
                # Defesa em profundidade: linha 335-336 ja retornou [] antes,
                # mas se algum refactor remover esse return, garantimos que
                # usuario sem acesso a NENHUMA loja recebe lista vazia.
                return resultado
            subq_perm = chassis_acessiveis_subquery(lojas_permitidas_ids)
            if subq_perm is not None:
                qb = qb.filter(HoraMoto.numero_chassi.in_(subq_perm))

        qb = qb.order_by(HoraMoto.numero_chassi)
        for moto, modelo in qb.all():
            resultado.append({
                'chassi': moto.numero_chassi,
                'modelo_id': modelo.id,
                'modelo_nome': modelo.nome_modelo,
                'cor': moto.cor,
                'motor': moto.numero_motor,
                'ano_modelo': moto.ano_modelo,
                'loja_id': None,
                'loja_nome': None,
                'ultimo_evento': None,            # template renderiza "Aguardando NF"
                'ultimo_evento_em': None,
                'ultimo_evento_detalhe': None,
                'moto_disponivel': False,
                'moto_faltando': False,
            })

    if not resultado:
        return resultado

    chassis = [r['chassi'] for r in resultado]

    # Enriquecimento: NF de entrada + recebimento
    nf_map = _nf_recebimento_por_chassi(chassis)
    # Avarias abertas
    from app.hora.services.avaria_service import avarias_abertas_por_chassi
    avarias_map = avarias_abertas_por_chassi(chassis)
    # Pecas faltando abertas
    pecas_map = _pecas_abertas_por_chassi(chassis)
    # Transferencias em transito (nao confirmadas no destino)
    transf_map = _transferencias_em_transito_por_chassi(chassis)
    # Venda / NF saida (so relevante p/ chassi fora de estoque, mas enriquece
    # sempre — overhead e 1 query por listagem).
    venda_map = _venda_nf_saida_por_chassi(chassis)

    for r in resultado:
        nf = nf_map.get(r['chassi']) or {}
        r['nf_id'] = nf.get('nf_id')
        r['nf_numero'] = nf.get('nf_numero')
        r['nf_serie'] = nf.get('nf_serie')
        r['recebimento_id'] = nf.get('recebimento_id')
        r['avarias_abertas'] = avarias_map.get(r['chassi'], 0)
        r['pecas_faltando_abertas'] = pecas_map.get(r['chassi'], 0)
        r['transferencias_em_transito'] = transf_map.get(r['chassi'], 0)
        venda = venda_map.get(r['chassi']) or {}
        r['venda_id'] = venda.get('venda_id')
        r['nf_saida_numero'] = venda.get('nf_saida_numero')
        r['nf_saida_chave_44'] = venda.get('nf_saida_chave_44')
        r['venda_status'] = venda.get('venda_status')
        r['tem_pdf_legado'] = venda.get('tem_pdf', False)
        r['tem_nfe_tagplus'] = venda.get('tem_nfe_tagplus', False)
        r['nfe_status'] = venda.get('nfe_status')

    return resultado


def opcoes_filtro_estoque(
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> dict:
    """Retorna opcoes para SELECTs de filtro: apenas modelos/cores que
    atualmente tem ao menos 1 moto em EVENTOS_EM_ESTOQUE nas lojas permitidas.

    Returns:
        {
            'modelos': [{'id': int, 'nome_modelo': str}, ...],
            'cores': [str, ...],
        }
    """
    sub = _subquery_ultimo_evento_id()
    q_base = (
        db.session.query(
            HoraModelo.id,
            HoraModelo.nome_modelo,
            HoraMoto.cor,
        )
        .join(HoraMoto, HoraMoto.modelo_id == HoraModelo.id)
        .join(sub, HoraMoto.numero_chassi == sub.c.chassi)
        .join(HoraMotoEvento, HoraMotoEvento.id == sub.c.max_id)
        .filter(HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE))
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return {'modelos': [], 'cores': []}
        q_base = q_base.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    modelos_dict: Dict[int, str] = {}
    cores_set = set()
    for mid, mnome, cor in q_base.distinct().all():
        modelos_dict[mid] = mnome
        if cor:
            cores_set.add(cor)

    modelos = [
        {'id': mid, 'nome_modelo': nome}
        for mid, nome in sorted(modelos_dict.items(), key=lambda x: x[1] or '')
    ]
    cores = sorted(cores_set)
    return {'modelos': modelos, 'cores': cores}


def opcoes_documentos_filtro(
    lojas_permitidas_ids: Optional[List[int]] = None,
    limit: int = 200,
) -> dict:
    """Retorna listas de pedidos, NFs de entrada e vendas para popular os
    SELECTs de filtro da tela de estoque.

    Filtra pelo escopo de lojas permitidas (quando aplicavel), e limita a
    `limit` por categoria — mais recentes primeiro. Ordena por data desc.

    Returns:
        {
          'pedidos': [{'id', 'numero_pedido', 'loja_nome', 'data_pedido', 'status'}, ...],
          'nfs_entrada': [{'id', 'numero_nf', 'nome_emitente', 'loja_nome', 'data_emissao'}, ...],
          'vendas': [{'id', 'nf_saida_numero', 'nome_cliente', 'loja_nome', 'data_venda', 'status'}, ...],
        }
    """
    from app.hora.models import HoraNfEntrada, HoraPedido, HoraVenda

    permitidas_set = (
        set(lojas_permitidas_ids) if lojas_permitidas_ids is not None else None
    )
    if permitidas_set is not None and not permitidas_set:
        return {'pedidos': [], 'nfs_entrada': [], 'vendas': []}

    # Pedidos
    q_ped = HoraPedido.query.order_by(
        HoraPedido.data_pedido.desc(), HoraPedido.id.desc()
    )
    if permitidas_set is not None:
        q_ped = q_ped.filter(HoraPedido.loja_destino_id.in_(permitidas_set))
    pedidos = [
        {
            'id': p.id,
            'numero_pedido': p.numero_pedido,
            'loja_nome': (
                p.loja_destino.rotulo_display if p.loja_destino else None
            ),
            'data_pedido': p.data_pedido,
            'status': p.status,
        }
        for p in q_ped.limit(limit).all()
    ]

    # NFs de entrada
    q_nf = HoraNfEntrada.query.order_by(
        HoraNfEntrada.data_emissao.desc(), HoraNfEntrada.id.desc()
    )
    if permitidas_set is not None:
        q_nf = q_nf.filter(HoraNfEntrada.loja_destino_id.in_(permitidas_set))
    nfs_entrada = [
        {
            'id': nf.id,
            'numero_nf': nf.numero_nf,
            'nome_emitente': nf.nome_emitente or nf.cnpj_emitente,
            'loja_nome': (
                nf.loja_destino.rotulo_display if nf.loja_destino else None
            ),
            'data_emissao': nf.data_emissao,
        }
        for nf in q_nf.limit(limit).all()
    ]

    # Vendas (NF saida)
    q_v = HoraVenda.query.order_by(
        HoraVenda.data_venda.desc(), HoraVenda.id.desc()
    )
    if permitidas_set is not None:
        # Vendas com loja_id=NULL (CNPJ_DESCONHECIDO) so aparecem p/ admin.
        q_v = q_v.filter(HoraVenda.loja_id.in_(permitidas_set))
    vendas = [
        {
            'id': v.id,
            'nf_saida_numero': v.nf_saida_numero,
            'nome_cliente': v.nome_cliente,
            'loja_nome': v.loja.rotulo_display if v.loja else None,
            'data_venda': v.data_venda,
            'status': v.status,
        }
        for v in q_v.limit(limit).all()
    ]

    return {
        'pedidos': pedidos,
        'nfs_entrada': nfs_entrada,
        'vendas': vendas,
    }


def autocomplete_chassi(
    q: str,
    lojas_permitidas_ids: Optional[List[int]] = None,
    limit: int = 20,
) -> List[dict]:
    """Busca parcial de chassis no universo das lojas permitidas.

    Filtra para chassis acessiveis (evento OU pedido OU NF entrada OU venda em
    loja permitida) — mesmo criterio de `estoque_chassi_detalhe`. Permite
    sugerir chassis que ainda estao apenas em pedido (sem NF/evento ainda).
    """
    q_norm = (q or '').strip().upper()
    if not q_norm or len(q_norm) < 2:
        return []

    base = (
        db.session.query(HoraMoto, HoraModelo)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .filter(HoraMoto.numero_chassi.ilike(f'%{q_norm}%'))
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        from app.hora.services.auth_helper import chassis_acessiveis_subquery
        subq = chassis_acessiveis_subquery(lojas_permitidas_ids)
        # subq nao deve ser None aqui pois ja checamos `is not None` acima
        base = base.filter(HoraMoto.numero_chassi.in_(subq))

    base = base.order_by(HoraMoto.numero_chassi).limit(limit)
    return [
        {
            'chassi': m.numero_chassi,
            'modelo': modelo.nome_modelo,
            'cor': m.cor,
        }
        for m, modelo in base.all()
    ]


def autocomplete_modelo(
    q: str,
    lojas_permitidas_ids: Optional[List[int]] = None,
    limit: int = 20,
) -> List[dict]:
    """Busca parcial de modelos que tem pelo menos 1 moto no universo permitido."""
    q_norm = (q or '').strip().upper()
    if not q_norm:
        return []

    base = (
        db.session.query(HoraModelo)
        .join(HoraMoto, HoraMoto.modelo_id == HoraModelo.id)
        .filter(HoraModelo.nome_modelo.ilike(f'%{q_norm}%'))
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        chassis_permitidos = (
            db.session.query(HoraMotoEvento.numero_chassi)
            .filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))
            .distinct()
            .subquery()
        )
        base = base.filter(HoraMoto.numero_chassi.in_(chassis_permitidos))

    base = base.distinct().order_by(HoraModelo.nome_modelo).limit(limit)
    return [
        {'id': m.id, 'nome_modelo': m.nome_modelo}
        for m in base.all()
    ]


def autocomplete_cor(
    q: str,
    lojas_permitidas_ids: Optional[List[int]] = None,
    limit: int = 20,
) -> List[str]:
    """Busca parcial de cores que tem pelo menos 1 moto no universo permitido."""
    q_norm = (q or '').strip().upper()
    if not q_norm:
        return []

    base = (
        db.session.query(HoraMoto.cor)
        .filter(HoraMoto.cor.ilike(f'%{q_norm}%'))
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        chassis_permitidos = (
            db.session.query(HoraMotoEvento.numero_chassi)
            .filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))
            .distinct()
            .subquery()
        )
        base = base.filter(HoraMoto.numero_chassi.in_(chassis_permitidos))

    base = base.distinct().order_by(HoraMoto.cor).limit(limit)
    return [row[0] for row in base.all() if row[0]]


def cores_disponiveis_por_modelo(
    modelo_id: int,
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[str]:
    """Lista cores distintas com pelo menos 1 chassi em EVENTOS_EM_ESTOQUE
    para o modelo informado.

    Usado pelo SELECT cascateado da tela "Novo Pedido de Venda" (Faturamento):
    operador escolhe modelo -> aparecem cores -> aparecem chassis. Filtra por
    lojas permitidas ao usuario quando `lojas_permitidas_ids` nao e None.
    """
    if not modelo_id:
        return []

    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(HoraMoto.cor)
        .join(sub, HoraMoto.numero_chassi == sub.c.chassi)
        .join(HoraMotoEvento, HoraMotoEvento.id == sub.c.max_id)
        .filter(
            HoraMoto.modelo_id == modelo_id,
            HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE),
            HoraMoto.cor.isnot(None),
        )
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    cores = sorted({row[0] for row in q.distinct().all() if row[0]})
    return cores


def chassis_disponiveis_para_venda(
    modelo_id: int,
    cor: Optional[str] = None,
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Lista chassis disponiveis para venda manual (tela Faturamento ->
    Novo Pedido de Venda).

    Considera "disponivel" = ultimo evento em EVENTOS_EM_ESTOQUE. Inclui
    AVARIADA e FALTANDO_PECA com flag para o operador decidir; UI deve
    mostrar badge.

    Retorna lista de dicts ordenada por chassi:
        [{chassi, modelo_id, modelo_nome, cor, motor, ano_modelo,
          loja_id, loja_nome, ultimo_evento, avarias_abertas,
          pecas_faltando_abertas, preco_tabela_sugerido}, ...]
    `preco_tabela_sugerido` e o preco da tabela vigente HOJE para o modelo
    (None se nao houver tabela vigente).
    """
    from datetime import date

    if not modelo_id:
        return []

    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(HoraMotoEvento, HoraMoto, HoraModelo, HoraLoja)
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraMoto, HoraMotoEvento.numero_chassi == HoraMoto.numero_chassi)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .outerjoin(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
        .filter(
            HoraMoto.modelo_id == modelo_id,
            HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE),
        )
    )
    if cor:
        q = q.filter(HoraMoto.cor == cor.strip().upper())
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    q = q.order_by(HoraMoto.numero_chassi)
    rows = q.all()
    if not rows:
        return []

    # Enriquecimento.
    chassis = [moto.numero_chassi for _, moto, _, _ in rows]
    from app.hora.services.avaria_service import avarias_abertas_por_chassi
    avarias_map = avarias_abertas_por_chassi(chassis)
    pecas_map = _pecas_abertas_por_chassi(chassis)

    # Preco sugerido (A vista preferencial) — usa _buscar_preco_modelo (novo fluxo
    # migration hora_33). Quando ainda nao se sabe a forma de pagamento, prefere
    # preco_a_vista do modelo; fallback preco_a_prazo; ultimo recurso HoraTabelaPreco.
    # Atualizado dinamicamente no JS quando o operador escolhe forma de pagamento.
    from app.hora.services.venda_service import _buscar_preco_modelo
    hoje = date.today()
    preco_dec, _fonte, _tab_id = _buscar_preco_modelo(
        modelo_id, forma_pagamento_hora=None, na_data=hoje,
    )
    preco_sugerido = float(preco_dec) if preco_dec is not None else None

    resultado = []
    for ev, moto, modelo, loja in rows:
        resultado.append({
            'chassi': moto.numero_chassi,
            'modelo_id': modelo.id,
            'modelo_nome': modelo.nome_modelo,
            'cor': moto.cor,
            'motor': moto.numero_motor,
            'ano_modelo': moto.ano_modelo,
            'loja_id': loja.id if loja else None,
            'loja_nome': loja.rotulo_display if loja else None,
            'ultimo_evento': ev.tipo,
            'avarias_abertas': avarias_map.get(moto.numero_chassi, 0),
            'pecas_faltando_abertas': pecas_map.get(moto.numero_chassi, 0),
            'preco_tabela_sugerido': preco_sugerido,
        })
    return resultado


def kpis_estoque_por_loja(
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Agrupa estoque por loja (contagem total + avariadas + faltando_peca)."""
    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(
            HoraLoja.id.label('loja_id'),
            HoraLoja.apelido,
            HoraLoja.nome,
            HoraLoja.nome_fantasia,
            HoraMotoEvento.tipo,
            func.count().label('total'),
        )
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
        .filter(HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE))
        .group_by(HoraLoja.id, HoraLoja.apelido, HoraLoja.nome,
                  HoraLoja.nome_fantasia, HoraMotoEvento.tipo)
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraLoja.id.in_(lojas_permitidas_ids))

    acum = {}
    for row in q.all():
        k = row.loja_id
        if k not in acum:
            acum[k] = {
                'loja_id': row.loja_id,
                'loja_nome': row.apelido or row.nome_fantasia or row.nome,
                'total': 0,
                'disponivel': 0,
                'avariada': 0,
                'faltando_peca': 0,
            }
        acum[k]['total'] += row.total
        if row.tipo == 'AVARIADA':
            acum[k]['avariada'] += row.total
        elif row.tipo == 'FALTANDO_PECA':
            acum[k]['faltando_peca'] += row.total
        else:
            acum[k]['disponivel'] += row.total

    return sorted(acum.values(), key=lambda x: x['loja_nome'] or '')


def kpis_loja_modelo_cor(
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Estrutura hierarquica Loja -> Modelo -> Cor -> Qtd, somente
    EVENTOS_EM_ESTOQUE (motos disponiveis fisicamente).

    Returns:
        [
          {
            'loja_id': int, 'loja_nome': str, 'total_loja': int,
            'modelos': [
              {
                'modelo_id': int, 'modelo_nome': str, 'total_modelo': int,
                'cores': [{'cor': str, 'qtd': int}, ...],
              }, ...
            ],
          }, ...
        ]
    """
    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(
            HoraLoja.id.label('loja_id'),
            HoraLoja.apelido,
            HoraLoja.nome,
            HoraLoja.nome_fantasia,
            HoraModelo.id.label('modelo_id'),
            HoraModelo.nome_modelo,
            HoraMoto.cor,
            func.count().label('qtd'),
        )
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraMoto, HoraMotoEvento.numero_chassi == HoraMoto.numero_chassi)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .join(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
        .filter(HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE))
        .group_by(
            HoraLoja.id, HoraLoja.apelido, HoraLoja.nome, HoraLoja.nome_fantasia,
            HoraModelo.id, HoraModelo.nome_modelo, HoraMoto.cor,
        )
        .order_by(HoraLoja.nome, HoraModelo.nome_modelo, HoraMoto.cor)
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraLoja.id.in_(lojas_permitidas_ids))

    # Acumula em estrutura hierarquica.
    lojas_dict: Dict[int, dict] = {}
    for row in q.all():
        loja_id = row.loja_id
        if loja_id not in lojas_dict:
            lojas_dict[loja_id] = {
                'loja_id': loja_id,
                'loja_nome': row.apelido or row.nome_fantasia or row.nome,
                'total_loja': 0,
                '_modelos_idx': {},  # modelo_id -> dict
            }
        loja_entry = lojas_dict[loja_id]
        loja_entry['total_loja'] += row.qtd

        modelo_id = row.modelo_id
        if modelo_id not in loja_entry['_modelos_idx']:
            loja_entry['_modelos_idx'][modelo_id] = {
                'modelo_id': modelo_id,
                'modelo_nome': row.nome_modelo,
                'total_modelo': 0,
                'cores': [],
            }
        modelo_entry = loja_entry['_modelos_idx'][modelo_id]
        modelo_entry['total_modelo'] += row.qtd
        modelo_entry['cores'].append({'cor': row.cor, 'qtd': row.qtd})

    # Materializa ordenado.
    resultado = []
    for loja in sorted(lojas_dict.values(), key=lambda x: x['loja_nome'] or ''):
        modelos = sorted(
            loja.pop('_modelos_idx').values(),
            key=lambda m: m['modelo_nome'] or '',
        )
        loja['modelos'] = modelos
        resultado.append(loja)
    return resultado


def kpis_estoque_por_modelo(
    loja_id: Optional[int] = None,
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Agrupa estoque por modelo (contagem total)."""
    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(
            HoraModelo.id,
            HoraModelo.nome_modelo,
            HoraMoto.cor,
            func.count().label('total'),
        )
        .join(HoraMoto, HoraMoto.modelo_id == HoraModelo.id)
        .join(
            sub,
            HoraMoto.numero_chassi == sub.c.chassi,
        )
        .join(HoraMotoEvento, HoraMotoEvento.id == sub.c.max_id)
        .filter(HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE))
        .group_by(HoraModelo.id, HoraModelo.nome_modelo, HoraMoto.cor)
        .order_by(HoraModelo.nome_modelo, HoraMoto.cor)
    )
    if loja_id:
        q = q.filter(HoraMotoEvento.loja_id == loja_id)
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    return [
        {
            'modelo_id': r.id,
            'modelo_nome': r.nome_modelo,
            'cor': r.cor,
            'total': r.total,
        }
        for r in q.all()
    ]


def historico_chassi(numero_chassi: str) -> List[dict]:
    """Retorna todos os eventos de um chassi, mais recentes primeiro.

    Mantido por compatibilidade com quem ainda consome. A tela de detalhe
    usa agora `rastreamento_completo` (mais rico).
    """
    chassi = numero_chassi.strip().upper()
    eventos = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .all()
    )
    return [
        {
            'id': e.id,
            'tipo': e.tipo,
            'timestamp': e.timestamp,
            'loja_id': e.loja_id,
            'loja_nome': e.loja.rotulo_display if e.loja else None,
            'operador': e.operador,
            'detalhe': e.detalhe,
            'origem_tabela': e.origem_tabela,
            'origem_id': e.origem_id,
        }
        for e in eventos
    ]


def rastreamento_completo(numero_chassi: str) -> dict:
    """Cruza dados de TODAS as entidades que tocam o chassi, gerando o
    "raio-x" usado na tela de detalhe. Sem eventos crus — entidades reais.

    Returns dict com chaves: pedido, pedido_item, pedido_da_nf,
    chassi_no_pedido_da_nf, nf, nf_item, recebimento, conferencia,
    conferencia_divergencias, transferencias, avarias, pecas_faltando, venda,
    devolucoes, ultimo_evento, moto_disponivel.
    Campos ausentes vem como None (ou [] para coleções).

    Regra (corrigida 2026-05-05): `pedido` so e populado se o chassi REALMENTE
    consta em `HoraPedidoItem` (i.e. faz parte dos itens do pedido). Se a NF do
    chassi esta vinculada a um pedido que NAO contem este chassi nos itens
    (chassi extra na NF), o pedido vai em `pedido_da_nf` com flag
    `chassi_no_pedido_da_nf=False` — para que o template indique a situacao
    sem enganar o usuario dizendo que e o "pedido de origem" do chassi.
    """
    from app.hora.models import (
        HoraAvaria, HoraDevolucaoFornecedor, HoraDevolucaoFornecedorItem,
        HoraNfEntradaItem, HoraPecaFaltando, HoraPedido,
        HoraPedidoItem, HoraRecebimento, HoraRecebimentoConferencia,
        HoraTransferencia, HoraTransferenciaItem, HoraVendaItem,
    )

    chassi = numero_chassi.strip().upper()
    resultado = {
        'pedido': None,
        'pedido_item': None,
        'pedido_da_nf': None,            # Pedido vinculado a NF, mas chassi NAO nos itens
        'chassi_no_pedido_da_nf': False,  # True se chassi consta nos itens do pedido_da_nf
        'nf': None,
        'nf_item': None,
        'recebimento': None,
        'conferencia': None,
        'conferencia_divergencias': [],
        'transferencias': [],
        'avarias': [],
        'pecas_faltando': [],
        'venda': None,
        'venda_item': None,
        'devolucoes': [],
        'ultimo_evento': None,
        'moto_disponivel': False,
    }

    # 1) Pedido REAL do chassi: aquele cujo HoraPedidoItem tem este chassi.
    item_pedido = (
        HoraPedidoItem.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraPedidoItem.id.desc())
        .first()
    )
    if item_pedido:
        resultado['pedido'] = item_pedido.pedido
        resultado['pedido_item'] = item_pedido

    # 2) NF item + NF + pedido_da_nf (informativo, separado).
    nf_item = (
        HoraNfEntradaItem.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraNfEntradaItem.id.desc())
        .first()
    )
    if nf_item:
        resultado['nf_item'] = nf_item
        resultado['nf'] = nf_item.nf
        if nf_item.nf and nf_item.nf.pedido_id:
            ped_da_nf = HoraPedido.query.get(nf_item.nf.pedido_id)
            if ped_da_nf:
                # Verifica se o chassi consta nos itens deste pedido.
                chassis_do_pedido = {
                    pi.numero_chassi for pi in ped_da_nf.itens if pi.numero_chassi
                }
                consta = chassi in chassis_do_pedido
                resultado['chassi_no_pedido_da_nf'] = consta
                if not resultado['pedido']:
                    # Nao havia pedido_item para este chassi: o pedido_da_nf
                    # e a unica referencia. Mostrar so se o chassi consta.
                    if consta:
                        resultado['pedido'] = ped_da_nf
                        # pedido_item pode existir mesmo sem ter sido pego no
                        # passo 1 (caso `numero_chassi` tenha capitalizacao
                        # diferente, etc.). Re-busca dentro do pedido.
                        for pi in ped_da_nf.itens:
                            if pi.numero_chassi == chassi:
                                resultado['pedido_item'] = pi
                                break
                    else:
                        resultado['pedido_da_nf'] = ped_da_nf
                else:
                    # Ja temos pedido real (passo 1). Se for outro pedido,
                    # registra pedido_da_nf como informacao adicional.
                    if ped_da_nf.id != resultado['pedido'].id:
                        resultado['pedido_da_nf'] = ped_da_nf

    # Recebimento + Conferencia (ativa mais recente)
    conf = (
        HoraRecebimentoConferencia.query
        .filter_by(numero_chassi=chassi, substituida=False)
        .order_by(HoraRecebimentoConferencia.id.desc())
        .first()
    )
    if conf:
        resultado['conferencia'] = conf
        resultado['conferencia_divergencias'] = list(conf.divergencias)
        resultado['recebimento'] = HoraRecebimento.query.get(conf.recebimento_id)

    # Transferencias
    resultado['transferencias'] = (
        HoraTransferencia.query
        .join(HoraTransferenciaItem,
              HoraTransferenciaItem.transferencia_id == HoraTransferencia.id)
        .filter(HoraTransferenciaItem.numero_chassi == chassi)
        .distinct()
        .order_by(HoraTransferencia.emitida_em.desc())
        .all()
    )

    # Avarias
    resultado['avarias'] = (
        HoraAvaria.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraAvaria.criado_em.desc())
        .all()
    )

    # Pecas faltando
    resultado['pecas_faltando'] = (
        HoraPecaFaltando.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraPecaFaltando.criado_em.desc())
        .all()
    )

    # Venda
    venda_item = (
        HoraVendaItem.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraVendaItem.id.desc())
        .first()
    )
    if venda_item:
        resultado['venda_item'] = venda_item
        resultado['venda'] = venda_item.venda

    # Devolucoes (ao fornecedor)
    resultado['devolucoes'] = (
        HoraDevolucaoFornecedor.query
        .join(HoraDevolucaoFornecedorItem,
              HoraDevolucaoFornecedorItem.devolucao_id == HoraDevolucaoFornecedor.id)
        .filter(HoraDevolucaoFornecedorItem.numero_chassi == chassi)
        .distinct()
        .order_by(HoraDevolucaoFornecedor.criado_em.desc())
        .all()
    )

    # Ultimo evento para status geral
    ult = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .first()
    )
    if ult:
        resultado['ultimo_evento'] = {
            'tipo': ult.tipo,
            'timestamp': ult.timestamp,
            'loja_id': ult.loja_id,
            'loja_nome': ult.loja.rotulo_display if ult.loja else None,
            'detalhe': ult.detalhe,
        }
        resultado['moto_disponivel'] = ult.tipo in EVENTOS_EM_ESTOQUE

    return resultado


def listar_em_transito(
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Motos com ultimo evento EM_TRANSITO, visiveis para origem OU destino.

    Interpretacao: evento EM_TRANSITO e emitido com loja_id=destino. Para que
    a loja origem tambem enxergue o que saiu, fazemos JOIN com
    hora_transferencia_item -> hora_transferencia e filtramos onde
    loja_origem_id ou loja_destino_id esta em lojas_permitidas_ids.
    """
    from app.hora.models import HoraTransferencia, HoraTransferenciaItem
    from sqlalchemy import or_

    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(
            HoraMotoEvento, HoraMoto, HoraModelo,
            HoraTransferencia, HoraLoja,
        )
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraMoto, HoraMotoEvento.numero_chassi == HoraMoto.numero_chassi)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .outerjoin(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
        .join(
            HoraTransferenciaItem,
            and_(
                HoraTransferenciaItem.id == HoraMotoEvento.origem_id,
                HoraMotoEvento.origem_tabela == 'hora_transferencia_item',
            ),
        )
        .join(
            HoraTransferencia,
            HoraTransferencia.id == HoraTransferenciaItem.transferencia_id,
        )
        .filter(HoraMotoEvento.tipo == 'EM_TRANSITO')
    )

    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(or_(
            HoraTransferencia.loja_origem_id.in_(lojas_permitidas_ids),
            HoraTransferencia.loja_destino_id.in_(lojas_permitidas_ids),
        ))

    q = q.order_by(HoraMotoEvento.timestamp.desc())

    return [
        {
            'numero_chassi': moto.numero_chassi,
            'modelo_id': modelo.id,
            'modelo_nome': modelo.nome_modelo,
            'cor': moto.cor,
            'loja_destino_id': loja.id if loja else None,
            'loja_destino_nome': loja.rotulo_display if loja else None,
            'loja_origem_id': transferencia.loja_origem_id,
            'transferencia_id': transferencia.id,
            'emitido_em': ev.timestamp,
            'detalhe': ev.detalhe,
        }
        for ev, moto, modelo, transferencia, loja in q.all()
    ]
