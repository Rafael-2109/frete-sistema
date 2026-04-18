"""Service de HoraPedido: criação a partir de lista de chassis esperados."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable, List, Mapping, Optional

from app import db
from app.hora.models import HoraPedido, HoraPedidoItem
from app.hora.services.moto_service import get_or_create_moto


def criar_pedido(
    numero_pedido: str,
    cnpj_destino: str,
    data_pedido: date,
    itens: Iterable[Mapping],
    arquivo_origem_s3_key: Optional[str] = None,
    observacoes: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> HoraPedido:
    """Cria HoraPedido + N HoraPedidoItem. Get-or-create de HoraMoto para cada chassi.

    `itens` deve ser iterável de dicts com chaves:
        numero_chassi (str, obrigatório)
        modelo (str, opcional — nome do modelo)
        cor (str, opcional)
        preco_compra_esperado (Decimal, obrigatório)
    """
    if HoraPedido.query.filter_by(numero_pedido=numero_pedido).first():
        raise ValueError(f"Pedido já existe: {numero_pedido}")

    cnpj_norm = ''.join(c for c in cnpj_destino if c.isdigit())
    if len(cnpj_norm) != 14:
        raise ValueError(f"cnpj_destino inválido: {cnpj_destino}")

    itens_lista: List[Mapping] = list(itens)
    if not itens_lista:
        raise ValueError("Pedido sem itens — pelo menos um item é obrigatório")

    pedido = HoraPedido(
        numero_pedido=numero_pedido,
        cnpj_destino=cnpj_norm,
        data_pedido=data_pedido,
        status='ABERTO',
        arquivo_origem_s3_key=arquivo_origem_s3_key,
        observacoes=observacoes,
        criado_por=criado_por,
    )
    db.session.add(pedido)
    db.session.flush()

    from app.hora.services.cadastro_service import buscar_ou_criar_modelo

    vistos_chassi = set()
    for item in itens_lista:
        chassi_raw = item.get('numero_chassi')
        chassi = (chassi_raw or '').strip().upper() or None

        if chassi:
            if chassi in vistos_chassi:
                raise ValueError(f"Chassi duplicado no pedido: {chassi}")
            vistos_chassi.add(chassi)

        preco = item.get('preco_compra_esperado')
        if preco is None:
            raise ValueError(f"Item sem preco_compra_esperado: {item}")

        if chassi:
            # Caso com chassi: get_or_create HoraMoto + referenciar
            moto = get_or_create_moto(
                numero_chassi=chassi,
                modelo_nome=item.get('modelo'),
                cor=item.get('cor') or 'NAO_INFORMADA',
                criado_por=criado_por,
            )
            modelo_id = moto.modelo_id
            chassi_final = moto.numero_chassi
        else:
            # Pedido pré-NF: só modelo+cor, chassi pendente.
            # Não cria HoraMoto (não existe ainda). Resolve modelo_id pelo nome.
            modelo_id = None
            if item.get('modelo'):
                modelo = buscar_ou_criar_modelo(item['modelo'])
                modelo_id = modelo.id
            chassi_final = None

        db.session.add(HoraPedidoItem(
            pedido_id=pedido.id,
            numero_chassi=chassi_final,
            modelo_id=modelo_id,
            cor=item.get('cor'),
            preco_compra_esperado=Decimal(str(preco)),
        ))

    db.session.commit()
    return pedido


def criar_pedido_a_partir_de_extracao(
    pedido_extraido,
    cnpj_destino_override: Optional[str] = None,
    criado_por: Optional[str] = None,
):
    """Cria HoraPedido a partir de um PedidoExtraido (output do parser XLSX).

    Args:
        pedido_extraido: instância de PedidoExtraido.
        cnpj_destino_override: se o parser não achou CNPJ ou achou errado,
            permite forçar (ex.: CNPJ da loja HORA resolvido via lookup).
        criado_por: usuário que importou.
    """
    cnpj = cnpj_destino_override or pedido_extraido.cnpj_destino
    if not cnpj:
        raise ValueError(
            "CNPJ destino não identificado e nenhum override fornecido. "
            "Selecione a loja manualmente."
        )

    itens = [
        {
            'numero_chassi': item.numero_chassi,
            'modelo': item.modelo,
            'cor': item.cor,
            'preco_compra_esperado': item.preco_compra_esperado or Decimal('0'),
        }
        for item in pedido_extraido.itens
    ]

    return criar_pedido(
        numero_pedido=pedido_extraido.numero_pedido,
        cnpj_destino=cnpj,
        data_pedido=pedido_extraido.data_pedido or date.today(),
        itens=itens,
        observacoes='\n'.join(pedido_extraido.avisos) if pedido_extraido.avisos else None,
        criado_por=criado_por,
    )


def listar_pedidos(
    status: Optional[str] = None,
    limit: int = 100,
    cnpjs_permitidos=None,
) -> List[HoraPedido]:
    """Lista pedidos. cnpjs_permitidos=None → todos; set/list → filtra por cnpj_destino."""
    query = HoraPedido.query.order_by(HoraPedido.data_pedido.desc(), HoraPedido.id.desc())
    if status:
        query = query.filter_by(status=status)
    if cnpjs_permitidos is not None:
        if not cnpjs_permitidos:
            return []  # usuário tem restrição mas nenhum CNPJ casa
        query = query.filter(HoraPedido.cnpj_destino.in_(list(cnpjs_permitidos)))
    return query.limit(limit).all()


def atualizar_status_pedido_por_faturamento(pedido_id: int) -> None:
    """Recalcula status do pedido com base em quais chassis já foram faturados.

    Regra: se todos os chassis do pedido aparecem em hora_nf_entrada_item ligados
    a uma NF que referencia este pedido → FATURADO. Se alguns → PARCIALMENTE_FATURADO.
    Se nenhum → mantém ABERTO.
    """
    from app.hora.models import HoraNfEntrada, HoraNfEntradaItem

    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        return

    chassis_pedido = {i.numero_chassi for i in pedido.itens}
    if not chassis_pedido:
        return

    chassis_faturados = {
        row.numero_chassi
        for row in (
            db.session.query(HoraNfEntradaItem.numero_chassi)
            .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
            .filter(HoraNfEntrada.pedido_id == pedido_id)
            .all()
        )
    }

    if chassis_pedido.issubset(chassis_faturados):
        novo_status = 'FATURADO'
    elif chassis_faturados:
        novo_status = 'PARCIALMENTE_FATURADO'
    else:
        novo_status = 'ABERTO'

    if pedido.status != novo_status:
        pedido.status = novo_status
        db.session.commit()
