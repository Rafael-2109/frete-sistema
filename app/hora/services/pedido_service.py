"""Service de HoraPedido: criação a partir de lista de chassis esperados."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Mapping, Optional

from sqlalchemy.orm import aliased, selectinload

from app import db
from app.hora.models import HoraPedido, HoraPedidoItem
from app.hora.services.moto_service import get_or_create_moto


# Pedidos com este status sao desconsiderados na deteccao de duplicidade
# cross-pedidos: se foi cancelado, o chassi voltou ao mercado e nao representa
# conflito. Status validos: ABERTO, PARCIALMENTE_FATURADO, FATURADO, CANCELADO.
_STATUS_IGNORADOS_DUPLICIDADE = ('CANCELADO',)


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
    origem: str = 'MANUAL',
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

    if origem not in ('XLSX', 'IMAGEM', 'MANUAL'):
        raise ValueError(
            f"origem inválido: '{origem}' — deve ser XLSX, IMAGEM ou MANUAL"
        )

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
        origem=origem,
    )
    db.session.add(pedido)
    db.session.flush()

    from app.hora.services.modelo_resolver_service import resolver_ou_pendenciar
    from app.hora.models import PENDENTE_ORIGEM_PEDIDO_MANUAL

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
            # Caso com chassi: get_or_create HoraMoto + referenciar.
            # fallback_sentinela=True: se o modelo nao resolve, cria a moto com
            # o sentinela DESCONHECIDO e registra a pendencia — NAO levanta
            # ModeloPendenteError. Assim o import (batch XLSX/imagem) NUNCA
            # aborta no 1o modelo desconhecido deixando o pedido sem itens
            # (header orfao — o bug dos pedidos 119/124/125/126). A
            # retroatividade (propagar_resolucao) corrige modelo_id da moto e do
            # item ao resolver a pendencia, via modelo_texto_original.
            moto = get_or_create_moto(
                numero_chassi=chassi,
                modelo_nome=item.get('modelo'),
                cor=item.get('cor') or 'NAO_INFORMADA',
                criado_por=criado_por,
                origem_pendencia=PENDENTE_ORIGEM_PEDIDO_MANUAL,
                origem_id=pedido.id,
                fallback_sentinela=True,
            )
            modelo_id = moto.modelo_id
            chassi_final = moto.numero_chassi
        else:
            # Pedido pre-NF: chassi pendente. Resolve modelo_id pelo nome.
            # Se nao bate em alias, cria pendencia em hora_modelo_pendente
            # e item fica com modelo_id=NULL. Operador resolve via tela
            # /hora/modelos/pendencias; retroatividade corrige.
            modelo_id = None
            nome_modelo = item.get('modelo')
            if nome_modelo:
                modelo, _pendente = resolver_ou_pendenciar(
                    nome_modelo,
                    origem=PENDENTE_ORIGEM_PEDIDO_MANUAL,
                    origem_id=pedido.id,
                )
                if modelo is not None:
                    modelo_id = modelo.id
            chassi_final = None

        db.session.add(HoraPedidoItem(
            pedido_id=pedido.id,
            numero_chassi=chassi_final,
            modelo_id=modelo_id,
            cor=item.get('cor'),
            preco_compra_esperado=Decimal(str(preco)),
            modelo_texto_original=item.get('modelo'),
        ))

    db.session.commit()
    return pedido


def criar_pedido_a_partir_de_extracao(
    pedido_extraido,
    cnpj_destino_override: Optional[str] = None,
    loja_destino_id: Optional[int] = None,
    arquivo_origem_s3_key: Optional[str] = None,
    criado_por: Optional[str] = None,
    origem: str = 'XLSX',
):
    """Cria HoraPedido a partir de um PedidoExtraido (output do parser XLSX ou imagem).

    Args:
        pedido_extraido: instância de PedidoExtraido.
        cnpj_destino_override: se o parser não achou CNPJ ou achou errado,
            permite forçar (ex.: CNPJ da loja HORA resolvido via lookup).
        loja_destino_id: OBRIGATÓRIO. Loja HORA que receberá fisicamente as motos.
            Selecionado manualmente na UI (pode ser auto-sugerido via apelido_detectado).
        arquivo_origem_s3_key: chave S3/local do arquivo original
            (XLSX se origem='XLSX', imagem JPG/PNG se origem='IMAGEM').
        criado_por: usuário que importou.
        origem: 'XLSX' (default) ou 'IMAGEM'. Usado para o campo HoraPedido.origem.
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
        origem=origem,
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
    # selectinload evita N+1 ao acessar p.itens no template (uma query agregada
    # em vez de 1-por-pedido). Fix Sentry PYTHON-FLASK-R2.
    query = (
        HoraPedido.query
        .options(selectinload(HoraPedido.itens))
        .order_by(HoraPedido.data_pedido.desc(), HoraPedido.id.desc())
    )
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

    from app.hora.services.modelo_resolver_service import resolver_ou_pendenciar
    from app.hora.models import PENDENTE_ORIGEM_PEDIDO_MANUAL

    if chassi:
        moto = get_or_create_moto(
            numero_chassi=chassi,
            modelo_nome=modelo_nome,
            cor=cor or 'NAO_INFORMADA',
            criado_por=operador,
            origem_pendencia=PENDENTE_ORIGEM_PEDIDO_MANUAL,
            origem_id=pedido.id,
        )
        modelo_id = moto.modelo_id
        chassi_final = moto.numero_chassi
    else:
        modelo_id = None
        if modelo_nome:
            modelo, _pendente = resolver_ou_pendenciar(
                modelo_nome,
                origem=PENDENTE_ORIGEM_PEDIDO_MANUAL,
                origem_id=pedido.id,
            )
            if modelo is not None:
                modelo_id = modelo.id
        chassi_final = None

    item = HoraPedidoItem(
        pedido_id=pedido.id,
        numero_chassi=chassi_final,
        modelo_id=modelo_id,
        cor=cor,
        preco_compra_esperado=Decimal(str(preco_compra_esperado)),
        modelo_texto_original=modelo_nome,
    )
    db.session.add(item)
    db.session.commit()
    # Mudar a composicao do pedido pode trocar o status (ex: absorver chassi
    # extra de NF ja vinculada deve passar de PARCIAL -> FATURADO).
    atualizar_status_pedido_por_faturamento(pedido.id)
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
    # Defesa: a funcao filtra itens-peca, entao adicionar peca em pedido
    # so-de-motos nao muda status. Mas se a regra de status passar a
    # considerar pecas no futuro, o caller ja esta correto.
    atualizar_status_pedido_por_faturamento(pedido.id)
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
    atualizar_status_pedido_por_faturamento(pedido_id)


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
    # Remover item-moto pode passar pedido de PARCIAL -> FATURADO
    # (se o item removido era o unico chassi nao faturado).
    atualizar_status_pedido_por_faturamento(pedido_id)


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


def mover_item_para_outro_pedido(
    pedido_origem_id: int,
    item_id: int,
    pedido_destino_id: int,
    tentar_vincular_nfs: bool = True,
    operador: Optional[str] = None,
) -> dict:
    """Move 1 HoraPedidoItem de um pedido para outro e tenta auto-vincular NFs.

    Caso de uso: operador detecta que uma moto (chassi) foi cadastrada no pedido
    errado. Essa funcao permite mover sem deletar/recriar, e ainda aproveita o
    momento para vincular NFs orfas que contem aquele chassi ao pedido destino,
    facilitando o vinculo Pedido x NF.

    Regras:
      - Pedido origem != pedido destino.
      - Mesma loja_destino_id (matching por loja, nunca por CNPJ — todas as NFs
        e pedidos HORA usam o CNPJ da matriz).
      - Pedido destino em status ABERTO ou PARCIALMENTE_FATURADO (FATURADO/CANCELADO
        nao aceita itens novos).
      - Pedido origem precisa ter ao menos 2 itens (1 deve sobrar — mesma regra
        de excluir_item_pedido).
      - Se item tem chassi: nao pode estar duplicado no pedido destino.
      - Se item tem chassi e ja foi faturado em NF vinculada ao pedido ORIGEM:
        bloqueado. Operador precisa desvincular a NF antes (mesma logica de
        excluir_item_pedido).
      - Item peca (peca_id) tambem pode ser movido — sem auto-vinculo de NF.

    Auto-vinculo de NFs (apenas se item tem chassi):
      - Busca NFs cujos itens contem o chassi do item movido.
      - Vincula automaticamente NFs que estao orfas (pedido_id IS NULL) e da
        mesma loja do pedido destino.
      - NFs que estao em outros pedidos OU em outra loja sao retornadas como
        "candidatas_outras" para o operador decidir manualmente.

    Retorna:
        {
          'ok': True,
          'item_id': int,
          'numero_chassi': str | None,
          'pedido_origem_id': int,
          'pedido_destino_id': int,
          'pedido_origem_status': str,   # status apos recalculo
          'pedido_destino_status': str,
          'nfs_auto_vinculadas': [{'nf_id', 'numero_nf', 'data_emissao_iso'}],
          'nfs_candidatas_outras': [{'nf_id', 'numero_nf', 'pedido_id_atual',
                                     'loja_destino_id', 'motivo'}],
        }
    """
    from app.hora.models import HoraNfEntrada, HoraNfEntradaItem

    if pedido_origem_id == pedido_destino_id:
        raise ValueError('Pedido destino deve ser diferente do origem.')

    pedido_origem = HoraPedido.query.get(pedido_origem_id)
    if not pedido_origem:
        raise ValueError(f'Pedido origem {pedido_origem_id} nao encontrado')
    pedido_destino = HoraPedido.query.get(pedido_destino_id)
    if not pedido_destino:
        raise ValueError(f'Pedido destino {pedido_destino_id} nao encontrado')

    if pedido_origem.loja_destino_id != pedido_destino.loja_destino_id:
        raise ValueError(
            f'Lojas divergentes: origem={pedido_origem.loja_destino_id}, '
            f'destino={pedido_destino.loja_destino_id}. '
            f'Os dois pedidos devem ser da mesma loja.'
        )

    # Status FATURADO E aceito como destino: caso tipico e NF com mais chassis
    # do que o pedido (ex: NF=11 motos, pedido=10/10 = FATURADO; operador
    # precisa absorver a 11a moto). Apos mover, atualizar_status_pedido_por_
    # faturamento recalcula o status correto.
    if pedido_destino.status == 'CANCELADO':
        raise ValueError(
            f'Pedido destino "{pedido_destino.numero_pedido}" esta CANCELADO '
            f'e nao aceita novos itens.'
        )

    item = HoraPedidoItem.query.get(item_id)
    if not item or item.pedido_id != pedido_origem.id:
        raise ValueError(
            f'Item {item_id} nao pertence ao pedido origem {pedido_origem_id}.'
        )

    if len(pedido_origem.itens) <= 1:
        raise ValueError(
            'Pedido origem ficaria sem itens. Pedido precisa ter pelo menos 1 item; '
            'exclua o pedido se necessario.'
        )

    chassi = item.numero_chassi  # pode ser None (item pre-NF) ou peca

    # Bloqueio: chassi ja faturado em NF do pedido origem
    if chassi:
        existe_em_nf_origem = db.session.query(
            db.session.query(HoraNfEntradaItem)
            .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
            .filter(HoraNfEntrada.pedido_id == pedido_origem.id)
            .filter(HoraNfEntradaItem.numero_chassi == chassi)
            .exists()
        ).scalar()
        if existe_em_nf_origem:
            raise ValueError(
                f'Chassi {chassi} ja foi faturado em NF do pedido origem '
                f'{pedido_origem.numero_pedido}. Desvincule a NF antes de mover '
                f'o item.'
            )

        # Bloqueio: chassi duplicado no pedido destino
        dup_destino = (
            HoraPedidoItem.query
            .filter(
                HoraPedidoItem.pedido_id == pedido_destino.id,
                HoraPedidoItem.numero_chassi == chassi,
                HoraPedidoItem.id != item.id,
            )
            .first()
        )
        if dup_destino:
            raise ValueError(
                f'Chassi {chassi} ja existe no pedido destino '
                f'{pedido_destino.numero_pedido} (item #{dup_destino.id}).'
            )

    # Move o item
    item.pedido_id = pedido_destino.id
    db.session.flush()

    # Auto-vinculo de NFs orfas com o chassi do item movido
    nfs_auto_vinculadas: List[dict] = []
    nfs_candidatas_outras: List[dict] = []
    if tentar_vincular_nfs and chassi:
        nfs_com_chassi = (
            db.session.query(HoraNfEntrada)
            .join(HoraNfEntradaItem, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
            .filter(HoraNfEntradaItem.numero_chassi == chassi)
            .distinct()
            .all()
        )
        for nf in nfs_com_chassi:
            if nf.pedido_id == pedido_destino.id:
                # Ja vinculada ao destino — nada a fazer.
                continue
            if nf.pedido_id is None and nf.loja_destino_id == pedido_destino.loja_destino_id:
                # Vincula automaticamente: NF orfa, mesma loja.
                nf.pedido_id = pedido_destino.id
                nfs_auto_vinculadas.append({
                    'nf_id': nf.id,
                    'numero_nf': nf.numero_nf,
                    'data_emissao_iso': nf.data_emissao.isoformat() if nf.data_emissao else None,
                })
            else:
                # NF ja vinculada a outro pedido OU loja diferente.
                # Lista para o operador decidir manualmente.
                if nf.pedido_id is not None and nf.pedido_id != pedido_destino.id:
                    motivo = f'ja vinculada ao pedido {nf.pedido_id}'
                elif nf.loja_destino_id and nf.loja_destino_id != pedido_destino.loja_destino_id:
                    motivo = f'loja diferente ({nf.loja_destino_id})'
                else:
                    motivo = 'NF sem loja'
                nfs_candidatas_outras.append({
                    'nf_id': nf.id,
                    'numero_nf': nf.numero_nf,
                    'pedido_id_atual': nf.pedido_id,
                    'loja_destino_id': nf.loja_destino_id,
                    'motivo': motivo,
                })

    db.session.commit()

    # Recalcula status dos dois pedidos
    atualizar_status_pedido_por_faturamento(pedido_origem.id)
    atualizar_status_pedido_por_faturamento(pedido_destino.id)

    # Releitura para devolver status atualizados
    db.session.refresh(pedido_origem)
    db.session.refresh(pedido_destino)

    return {
        'ok': True,
        'item_id': item.id,
        'numero_chassi': chassi,
        'pedido_origem_id': pedido_origem.id,
        'pedido_destino_id': pedido_destino.id,
        'pedido_origem_status': pedido_origem.status,
        'pedido_destino_status': pedido_destino.status,
        'nfs_auto_vinculadas': nfs_auto_vinculadas,
        'nfs_candidatas_outras': nfs_candidatas_outras,
    }


def atualizar_status_pedido_por_faturamento(pedido_id: int) -> None:
    """Recalcula status do pedido com base em quais chassis já foram faturados.

    Regra: se todos os chassis-moto do pedido aparecem em hora_nf_entrada_item
    ligados a uma NF que referencia este pedido → FATURADO. Se alguns →
    PARCIALMENTE_FATURADO. Se nenhum → mantém ABERTO.

    Considera APENAS itens-moto com chassi preenchido. Itens-peca (peca_id IS
    NOT NULL) e itens-moto pre-NF (numero_chassi IS NULL) sao ignorados — nao
    travam o status. Se o pedido nao tem nenhum item-moto com chassi (so
    pecas, ou so motos pre-NF), o status nao e recalculado por esta funcao.
    """
    from app.hora.models import HoraNfEntrada, HoraNfEntradaItem

    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        return

    chassis_pedido = {
        i.numero_chassi for i in pedido.itens
        if i.peca_id is None and i.numero_chassi is not None
    }
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


# ========================================================================
# Deteccao de duplicidade de chassi entre pedidos ATIVOS
# ========================================================================
#
# A constraint UNIQUE parcial (uq_hora_pedido_item_chassi_parcial em
# scripts/migrations/hora_02_pedido_item_chassi_nullable.sql) impede chassi
# duplicado DENTRO do mesmo pedido. Mas o sistema PERMITE intencionalmente que
# o mesmo chassi exista em pedidos diferentes — pedido cancelado libera o
# chassi para reentrada em outro pedido (mesma logica de hora_venda_item).
#
# Estas funcoes detectam o caso problematico: chassi presente em 2+ pedidos
# que NAO foram cancelados — sintoma de pedido duplicado, importacao em
# duplicata ou erro de operador. Sao usadas pela UI (listagem e detalhe) para
# alertar visualmente sem bloquear a operacao.


def chassis_duplicados_em_outros_pedidos(pedido_id: int) -> Dict[str, List[dict]]:
    """Retorna mapa {chassi: [outros pedidos ativos com o mesmo chassi]}.

    Considera duplicidade apenas entre pedidos cujo status nao esta em
    `_STATUS_IGNORADOS_DUPLICIDADE` (atualmente: 'CANCELADO').

    Se o pedido base estiver CANCELADO, retorna mapa vazio — nao alerta
    sobre pedidos cancelados (regra explicita do usuario).

    Cada entrada do mapa lista dicts com chaves: pedido_id, numero_pedido,
    status, item_id (do outro pedido). Util para o template de detalhe
    construir links e tooltips.
    """
    pedido_base = HoraPedido.query.get(pedido_id)
    if not pedido_base or pedido_base.status in _STATUS_IGNORADOS_DUPLICIDADE:
        return {}

    chassis_base = [
        i.numero_chassi for i in pedido_base.itens
        if i.numero_chassi and i.peca_id is None
    ]
    if not chassis_base:
        return {}

    rows = (
        db.session.query(
            HoraPedidoItem.numero_chassi,
            HoraPedidoItem.id,
            HoraPedido.id,
            HoraPedido.numero_pedido,
            HoraPedido.status,
        )
        .join(HoraPedido, HoraPedidoItem.pedido_id == HoraPedido.id)
        .filter(HoraPedidoItem.numero_chassi.in_(chassis_base))
        .filter(HoraPedido.id != pedido_id)
        .filter(~HoraPedido.status.in_(_STATUS_IGNORADOS_DUPLICIDADE))
        .all()
    )

    resultado: Dict[str, List[dict]] = {}
    for chassi, item_id, p_id, num, status in rows:
        resultado.setdefault(chassi, []).append({
            'pedido_id': p_id,
            'numero_pedido': num,
            'status': status,
            'item_id': item_id,
        })
    return resultado


def chassis_duplicados_em_outros_pedidos_batch(
    pedido_ids: List[int],
) -> Dict[int, int]:
    """Versao batch para a listagem: retorna {pedido_id: count_chassis_duplicados}.

    `count_chassis_duplicados` = numero de chassis distintos do pedido_id que
    aparecem em algum OUTRO pedido cujo status nao esta em
    `_STATUS_IGNORADOS_DUPLICIDADE`. Pedidos com status ignorado nao aparecem
    no resultado (regra: nao alerta em pedido cancelado).

    Implementacao: 1 query agregada (self-join + GROUP BY). Evita N+1.
    """
    if not pedido_ids:
        return {}

    pi_local = aliased(HoraPedidoItem, name='pi_local')
    pi_outro = aliased(HoraPedidoItem, name='pi_outro')
    p_local = aliased(HoraPedido, name='p_local')
    p_outro = aliased(HoraPedido, name='p_outro')

    rows = (
        db.session.query(
            pi_local.pedido_id,
            db.func.count(db.distinct(pi_local.numero_chassi)).label('n_dup'),
        )
        .join(p_local, p_local.id == pi_local.pedido_id)
        .join(
            pi_outro,
            db.and_(
                pi_outro.numero_chassi == pi_local.numero_chassi,
                pi_outro.pedido_id != pi_local.pedido_id,
            ),
        )
        .join(p_outro, p_outro.id == pi_outro.pedido_id)
        .filter(pi_local.pedido_id.in_(pedido_ids))
        .filter(pi_local.numero_chassi.isnot(None))
        .filter(~p_local.status.in_(_STATUS_IGNORADOS_DUPLICIDADE))
        .filter(~p_outro.status.in_(_STATUS_IGNORADOS_DUPLICIDADE))
        .group_by(pi_local.pedido_id)
        .all()
    )
    return {pid: int(n) for pid, n in rows if n}
