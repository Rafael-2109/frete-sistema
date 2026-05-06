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
    loja_destino_id: Optional[int] = None,
    apelido_detectado: Optional[str] = None,
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

    # Valida loja_destino_id se fornecido
    if loja_destino_id:
        from app.hora.models import HoraLoja
        if not HoraLoja.query.get(loja_destino_id):
            raise ValueError(f'loja_destino_id={loja_destino_id} inexistente')

    pedido = HoraPedido(
        numero_pedido=numero_pedido,
        cnpj_destino=cnpj_norm,
        loja_destino_id=loja_destino_id,
        apelido_detectado=apelido_detectado,
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
    loja_destino_id: Optional[int] = None,
    arquivo_origem_s3_key: Optional[str] = None,
    criado_por: Optional[str] = None,
):
    """Cria HoraPedido a partir de um PedidoExtraido (output do parser XLSX).

    Args:
        pedido_extraido: instância de PedidoExtraido.
        cnpj_destino_override: se o parser não achou CNPJ ou achou errado,
            permite forçar (ex.: CNPJ da loja HORA resolvido via lookup).
        loja_destino_id: OBRIGATÓRIO. Loja HORA que receberá fisicamente as motos.
            Selecionado manualmente na UI (pode ser auto-sugerido via apelido_detectado).
        arquivo_origem_s3_key: chave S3/local do XLSX original (para download).
        criado_por: usuário que importou.
    """
    cnpj = cnpj_destino_override or pedido_extraido.cnpj_destino
    if not cnpj:
        raise ValueError(
            "CNPJ destino não identificado e nenhum override fornecido."
        )
    if not loja_destino_id:
        raise ValueError(
            "Loja de destino é obrigatória. Selecione a loja HORA que vai receber as motos "
            "(ex: Motochefe Bragança)."
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
        loja_destino_id=loja_destino_id,
        apelido_detectado=pedido_extraido.apelido_detectado,
        data_pedido=pedido_extraido.data_pedido or date.today(),
        itens=itens,
        arquivo_origem_s3_key=arquivo_origem_s3_key,
        observacoes='\n'.join(pedido_extraido.avisos) if pedido_extraido.avisos else None,
        criado_por=criado_por,
    )


def listar_pedidos(
    status: Optional[str] = None,
    limit: int = 100,
    lojas_permitidas_ids=None,
    cnpjs_permitidos=None,  # legacy, mantido por compat
    *,
    numero_pedido=None,
    loja_id=None,
    data_inicio=None,
    data_fim=None,
) -> List[HoraPedido]:
    """Lista pedidos. lojas_permitidas_ids=None → todos; [id] → filtra por loja_destino_id.

    Filtros opcionais:
    - numero_pedido: substring (ilike) em numero_pedido
    - loja_id: id especifico de loja_destino_id
    - data_inicio / data_fim: faixa em data_pedido
    """
    query = HoraPedido.query.order_by(HoraPedido.data_pedido.desc(), HoraPedido.id.desc())
    if status:
        query = query.filter_by(status=status)
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        query = query.filter(HoraPedido.loja_destino_id.in_(list(lojas_permitidas_ids)))
    elif cnpjs_permitidos is not None:
        if not cnpjs_permitidos:
            return []
        query = query.filter(HoraPedido.cnpj_destino.in_(list(cnpjs_permitidos)))

    if numero_pedido:
        query = query.filter(
            HoraPedido.numero_pedido.ilike(f'%{numero_pedido.strip()}%')
        )
    if loja_id:
        query = query.filter(HoraPedido.loja_destino_id == loja_id)
    if data_inicio:
        query = query.filter(HoraPedido.data_pedido >= data_inicio)
    if data_fim:
        query = query.filter(HoraPedido.data_pedido <= data_fim)

    return query.limit(limit).all()


def _pedido_tem_nf_vinculada(pedido) -> bool:
    """True se ha pelo menos uma NF de entrada vinculada ao pedido."""
    from app.hora.models import HoraNfEntrada
    return db.session.query(
        HoraNfEntrada.query.filter_by(pedido_id=pedido.id).exists()
    ).scalar()


def excluir_pedido(pedido_id: int, operador: Optional[str] = None) -> str:
    """Exclui pedido (e seus itens via cascade). Bloqueia se tem NF vinculada."""
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')
    if _pedido_tem_nf_vinculada(pedido):
        raise ValueError(
            f'Pedido {pedido.numero_pedido} tem NF(s) vinculada(s) — '
            f'desvincule antes de excluir.'
        )
    numero = pedido.numero_pedido
    db.session.delete(pedido)
    db.session.commit()
    return numero


def editar_pedido_header(
    pedido_id: int,
    data_pedido: Optional[date] = None,
    loja_destino_id: Optional[int] = None,
    observacoes: Optional[str] = None,
    operador: Optional[str] = None,
) -> HoraPedido:
    """Atualiza campos do header. numero_pedido e cnpj_destino sao imutaveis."""
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')

    if data_pedido is not None:
        pedido.data_pedido = data_pedido
    if loja_destino_id is not None:
        from app.hora.models import HoraLoja
        if not HoraLoja.query.get(loja_destino_id):
            raise ValueError(f'loja_destino_id={loja_destino_id} inexistente')
        pedido.loja_destino_id = loja_destino_id
    if observacoes is not None:
        pedido.observacoes = observacoes or None

    db.session.commit()
    return pedido


def adicionar_item_pedido(
    pedido_id: int,
    numero_chassi: Optional[str],
    modelo_nome: Optional[str],
    cor: Optional[str],
    preco_compra_esperado,
    operador: Optional[str] = None,
) -> HoraPedidoItem:
    """Cria novo HoraPedidoItem em pedido existente.

    chassi opcional (pedido pre-NF). Valida chassi nao duplicado no pedido.
    """
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')

    chassi = (numero_chassi or '').strip().upper() or None

    if chassi:
        ja_no_pedido = any(
            (i.numero_chassi or '').upper() == chassi for i in pedido.itens
        )
        if ja_no_pedido:
            raise ValueError(f'Chassi {chassi} ja existe neste pedido')

    if preco_compra_esperado is None:
        raise ValueError('preco_compra_esperado obrigatorio')

    if chassi:
        moto = get_or_create_moto(
            numero_chassi=chassi,
            modelo_nome=modelo_nome,
            cor=cor or 'NAO_INFORMADA',
            criado_por=operador,
        )
        modelo_id = moto.modelo_id
        chassi_final = moto.numero_chassi
    else:
        modelo_id = None
        if modelo_nome:
            from app.hora.services.cadastro_service import buscar_ou_criar_modelo
            modelo = buscar_ou_criar_modelo(modelo_nome)
            modelo_id = modelo.id
        chassi_final = None

    item = HoraPedidoItem(
        pedido_id=pedido.id,
        numero_chassi=chassi_final,
        modelo_id=modelo_id,
        cor=cor,
        preco_compra_esperado=Decimal(str(preco_compra_esperado)),
    )
    db.session.add(item)
    db.session.commit()
    return item


def adicionar_item_peca_pedido(
    pedido_id: int,
    peca_id: int,
    qtd_pedida,
    preco_compra_esperado,
    operador: Optional[str] = None,
) -> HoraPedidoItem:
    """Adiciona item peca em pedido (XOR moto/peca).

    CHECK no banco garante que peca_id e qtd_pedida juntos sao incompativeis com
    numero_chassi/modelo_id.
    """
    from app.hora.models import HoraPeca

    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')
    if pedido.status not in ('ABERTO',):
        raise ValueError(
            f'Pedido em status {pedido.status} nao aceita novos itens (apenas ABERTO).'
        )
    if not HoraPeca.query.get(peca_id):
        raise ValueError(f'Peca {peca_id} nao existe')
    qtd = Decimal(str(qtd_pedida or 0))
    if qtd <= 0:
        raise ValueError('qtd_pedida deve ser positiva')
    preco = Decimal(str(preco_compra_esperado or 0))
    if preco <= 0:
        raise ValueError('preco_compra_esperado deve ser positivo')

    item = HoraPedidoItem(
        pedido_id=pedido.id,
        peca_id=peca_id,
        qtd_pedida=qtd,
        preco_compra_esperado=preco,
        # numero_chassi, modelo_id e cor ficam NULL (CHECK XOR satisfeito)
    )
    db.session.add(item)
    db.session.commit()
    return item


def remover_item_peca_pedido(
    pedido_id: int,
    item_id: int,
    operador: Optional[str] = None,
) -> None:
    """Remove item peca de pedido. Bloqueia se pedido nao esta ABERTO."""
    item = HoraPedidoItem.query.get(item_id)
    if not item or item.pedido_id != pedido_id:
        raise ValueError(f'Item {item_id} nao encontrado neste pedido')
    if item.peca_id is None:
        raise ValueError(f'Item {item_id} nao e de peca')
    if item.pedido.status != 'ABERTO':
        raise ValueError(
            f'Pedido em status {item.pedido.status} nao permite remocao (apenas ABERTO).'
        )
    if len(item.pedido.itens) <= 1:
        raise ValueError('Pedido precisa ter pelo menos 1 item')
    db.session.delete(item)
    db.session.commit()


def excluir_item_pedido(
    pedido_id: int,
    item_id: int,
    operador: Optional[str] = None,
) -> None:
    """Remove item de pedido. Bloqueia se chassi do item ja apareceu em NF vinculada."""
    from app.hora.models import HoraNfEntrada, HoraNfEntradaItem

    item = HoraPedidoItem.query.get(item_id)
    if not item or item.pedido_id != pedido_id:
        raise ValueError(f'Item {item_id} nao encontrado neste pedido')

    pedido = item.pedido
    # Impede deletar item cujo chassi ja foi faturado em NF deste pedido.
    if item.numero_chassi:
        existe_em_nf = db.session.query(
            db.session.query(HoraNfEntradaItem)
            .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
            .filter(HoraNfEntrada.pedido_id == pedido_id)
            .filter(HoraNfEntradaItem.numero_chassi == item.numero_chassi)
            .exists()
        ).scalar()
        if existe_em_nf:
            raise ValueError(
                f'Chassi {item.numero_chassi} ja foi faturado em NF deste pedido — '
                f'desvincule a NF antes de remover o item.'
            )

    if len(pedido.itens) <= 1:
        raise ValueError('Pedido precisa ter pelo menos 1 item')

    db.session.delete(item)
    db.session.commit()


def exportar_pedidos_excel(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    lojas_ids: Optional[List[int]] = None,
    limit: int = 10000,
) -> bytes:
    """Exporta pedidos com itens e vinculo NF por chassi para XLSX.

    Cada linha = 1 item de pedido. Se chassi ja apareceu em NF vinculada,
    mostra dados da NF na mesma linha.
    """
    import io
    import pandas as pd
    from app.hora.models import HoraNfEntrada, HoraNfEntradaItem

    query = HoraPedido.query
    if data_inicio:
        query = query.filter(HoraPedido.data_pedido >= data_inicio)
    if data_fim:
        query = query.filter(HoraPedido.data_pedido <= data_fim)
    if lojas_ids is not None:
        if not lojas_ids:
            pedidos = []
        else:
            query = query.filter(HoraPedido.loja_destino_id.in_(lojas_ids))
            pedidos = query.order_by(HoraPedido.data_pedido.desc(), HoraPedido.id.desc()).limit(limit).all()
    else:
        pedidos = query.order_by(HoraPedido.data_pedido.desc(), HoraPedido.id.desc()).limit(limit).all()

    # Mapa chassi -> (NF, NF item) para os pedidos retornados.
    pedido_ids = [p.id for p in pedidos]
    vinculos: dict[str, tuple] = {}
    if pedido_ids:
        nf_items_query = (
            db.session.query(HoraNfEntradaItem, HoraNfEntrada)
            .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
            .filter(HoraNfEntrada.pedido_id.in_(pedido_ids))
            .all()
        )
        for nf_item, nf in nf_items_query:
            chave = (nf.pedido_id, nf_item.numero_chassi)
            vinculos[chave] = (nf, nf_item)

    linhas = []
    for p in pedidos:
        loja_nome = p.loja_destino.rotulo_display if p.loja_destino else ''
        for item in p.itens:
            chassi = item.numero_chassi or ''
            modelo_nome = item.modelo.nome_modelo if item.modelo else ''
            preco_esp = float(item.preco_compra_esperado) if item.preco_compra_esperado is not None else None

            nf, nf_item = vinculos.get((p.id, chassi), (None, None)) if chassi else (None, None)
            preco_real = float(nf_item.preco_real) if nf_item and nf_item.preco_real is not None else None
            diferenca = (preco_real - preco_esp) if (preco_real is not None and preco_esp is not None) else None

            if nf:
                status_item = 'FATURADO'
            elif chassi:
                status_item = 'AGUARDANDO_NF'
            else:
                status_item = 'CHASSI_PENDENTE'

            linhas.append({
                'Pedido #': p.numero_pedido,
                'Data Pedido': p.data_pedido,
                'Loja Destino': loja_nome,
                'Status Pedido': p.status,
                'Chassi': chassi,
                'Modelo': modelo_nome,
                'Cor': item.cor or '',
                'Preço Esperado': preco_esp,
                'NF Vinculada': nf.numero_nf if nf else '',
                'Série NF': (nf.serie_nf or '') if nf else '',
                'Data NF': nf.data_emissao if nf else None,
                'Emitente NF': (nf.nome_emitente or nf.cnpj_emitente or '') if nf else '',
                'Preço Real (NF)': preco_real,
                'Diferença Preço': diferenca,
                'Status Item': status_item,
            })

    df = pd.DataFrame(linhas, columns=[
        'Pedido #', 'Data Pedido', 'Loja Destino', 'Status Pedido',
        'Chassi', 'Modelo', 'Cor', 'Preço Esperado',
        'NF Vinculada', 'Série NF', 'Data NF', 'Emitente NF',
        'Preço Real (NF)', 'Diferença Preço', 'Status Item',
    ])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Pedidos HORA')
        # Auto-ajusta largura das colunas (heuristica simples).
        ws = writer.sheets['Pedidos HORA']
        for col_idx, col in enumerate(df.columns, start=1):
            max_len = max(
                [len(str(col))] + [len(str(v)) for v in df[col].head(200).astype(str)]
            )
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_len + 2, 40)

    output.seek(0)
    return output.read()


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
