"""Service de HoraNfEntrada: parsea PDF, cria NF e itens."""
from __future__ import annotations

import io
from typing import Optional

from flask import current_app

from app import db
from app.hora.models import HoraNfEntrada, HoraNfEntradaItem, HoraPedido
from app.hora.services.moto_service import get_or_create_moto
from app.hora.services.parsers import parse_danfe_to_hora_payload
from app.hora.services.pedido_service import atualizar_status_pedido_por_faturamento
from app.utils.file_storage import FileStorage
from app.utils.timezone import agora_utc_naive


def _salvar_pdf_danfe_storage(
    pdf_bytes: bytes, chave_44: str, nome_arquivo_origem: Optional[str]
) -> Optional[str]:
    """Persiste bytes do DANFE em hora/nfs/ e retorna s3_key salvo (ou None).

    Falha de storage nao aborta o import — loga e continua (NF ja importou).
    """
    try:
        buf = io.BytesIO(pdf_bytes)
        buf.name = (nome_arquivo_origem or f'nf_{chave_44}.pdf')
        s3_key = FileStorage().save_file(
            buf, folder='hora/nfs', filename=f'{chave_44}.pdf',
            allowed_extensions=['pdf'],
        )
        return s3_key
    except Exception as exc:
        # storage opcional — import nao pode falhar por causa disso
        current_app.logger.warning(
            f'hora: falha ao persistir PDF DANFE da NF chave={chave_44}: {exc}'
        )
        return None


class NfEntradaJaImportada(Exception):
    """NF com mesma chave_44 já existe."""


def importar_danfe_pdf(
    pdf_bytes: bytes,
    nome_arquivo_origem: Optional[str] = None,
    pedido_id_sugerido: Optional[int] = None,
    loja_destino_id: Optional[int] = None,
    criado_por: Optional[str] = None,
) -> HoraNfEntrada:
    """Parseia PDF e cria HoraNfEntrada + itens + get-or-create de motos.

    Não gera evento RECEBIDA — isso acontece no fluxo de recebimento físico.

    Args:
        pdf_bytes: bytes do DANFE.
        nome_arquivo_origem: nome original do arquivo (para log).
        pedido_id_sugerido: se informado, tenta vincular a esse pedido.
        criado_por: usuário que importou.

    Returns:
        HoraNfEntrada criada.

    Raises:
        NfEntradaJaImportada: se chave_44 já existe.
        DanfeParseError: se parser falhar.
    """
    payload = parse_danfe_to_hora_payload(
        pdf_bytes=pdf_bytes,
        nome_arquivo_origem=nome_arquivo_origem,
    )
    nf_data = payload['nf']
    itens_data = payload['itens']

    # Checagem de duplicidade por chave_44
    existente = HoraNfEntrada.query.filter_by(chave_44=nf_data['chave_44']).first()
    if existente:
        raise NfEntradaJaImportada(
            f"NF com chave {nf_data['chave_44']} já importada (id={existente.id})"
        )

    pedido_id_vinculo = pedido_id_sugerido
    if pedido_id_vinculo:
        # Valida existência
        pedido = HoraPedido.query.get(pedido_id_vinculo)
        if not pedido:
            pedido_id_vinculo = None
        elif loja_destino_id is None and pedido.loja_destino_id:
            # Herda loja_destino do pedido vinculado
            loja_destino_id = pedido.loja_destino_id

    # Valida loja_destino
    if not loja_destino_id:
        raise ValueError(
            'Loja de destino é obrigatória para NF. Todas as NFs da HORA são emitidas '
            'para o CNPJ da matriz; selecione a loja física que receberá as motos.'
        )
    from app.hora.models import HoraLoja
    if not HoraLoja.query.get(loja_destino_id):
        raise ValueError(f'loja_destino_id={loja_destino_id} inexistente')

    # Persiste PDF DANFE no storage (S3 ou local). Falha nao aborta o import.
    s3_key_pdf = _salvar_pdf_danfe_storage(
        pdf_bytes=pdf_bytes,
        chave_44=nf_data['chave_44'],
        nome_arquivo_origem=nome_arquivo_origem,
    )

    nf = HoraNfEntrada(
        chave_44=nf_data['chave_44'],
        numero_nf=nf_data['numero_nf'],
        serie_nf=nf_data.get('serie_nf'),
        cnpj_emitente=nf_data['cnpj_emitente'],
        nome_emitente=nf_data.get('nome_emitente'),
        cnpj_destinatario=nf_data.get('cnpj_destinatario') or '',
        loja_destino_id=loja_destino_id,
        data_emissao=nf_data['data_emissao'],
        valor_total=nf_data['valor_total'],
        arquivo_pdf_s3_key=s3_key_pdf,
        pedido_id=pedido_id_vinculo,
        parser_usado=nf_data.get('parser_usado', 'danfe_pdf_parser_v1'),
        parseada_em=agora_utc_naive(),
        qtd_declarada_itens=nf_data.get('qtd_declarada_itens'),
    )
    db.session.add(nf)
    db.session.flush()

    for item in itens_data:
        moto = get_or_create_moto(
            numero_chassi=item['numero_chassi'],
            modelo_nome=item.get('modelo_texto_original'),
            cor=item.get('cor_texto_original') or 'NAO_INFORMADA',
            numero_motor=item.get('numero_motor'),
            ano_modelo=item.get('ano_modelo'),
            criado_por=criado_por,
        )

        db.session.add(HoraNfEntradaItem(
            nf_id=nf.id,
            numero_chassi=moto.numero_chassi,
            preco_real=item['preco_real'],
            modelo_texto_original=item.get('modelo_texto_original'),
            cor_texto_original=item.get('cor_texto_original'),
            numero_motor_texto_original=item.get('numero_motor'),
        ))

    db.session.commit()

    if pedido_id_vinculo:
        atualizar_status_pedido_por_faturamento(pedido_id_vinculo)

    return nf


def vincular_nf_a_pedido(nf_id: int, pedido_id: int) -> None:
    """Vincula retroativamente uma NF a um pedido (caso não tenha sido informado no upload)."""
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f"NF {nf_id} não encontrada")
    if not HoraPedido.query.get(pedido_id):
        raise ValueError(f"Pedido {pedido_id} não encontrado")
    nf.pedido_id = pedido_id
    db.session.commit()
    atualizar_status_pedido_por_faturamento(pedido_id)


def editar_nf_item_manual(
    nf_id: int,
    nf_item_id: int,
    numero_chassi: Optional[str] = None,
    numero_motor_texto_original: Optional[str] = None,
    operador: Optional[str] = None,
) -> dict:
    """Corrige numero_chassi e/ou numero_motor_texto_original de um item de NF.

    Casos de uso:
      - Parser LLM inverteu chassi<->motor (historico pre-fix #2).
      - NF emitida com chassi divergente do pedido (digito invertido no DANFE).
      - Chassi padronizado (remover hifens/espacos) manualmente.

    Regras:
      - `numero_chassi` e obrigatorio (FK NOT NULL em hora_nf_entrada_item).
      - Se o novo chassi ja existe em hora_moto, reaproveita (mantem motor/modelo/cor).
      - Se nao existe, cria (get_or_create) herdando modelo/cor do item atual.
      - Apos trocar a FK, se a hora_moto antiga ficou orfa (sem NF, pedido, eventos),
        e removida. Isso evita lixo acumulando.
      - Unicidade (nf_id, numero_chassi) e garantida pelo UNIQUE da tabela.
    """
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')

    item = HoraNfEntradaItem.query.get(nf_item_id)
    if not item or item.nf_id != nf.id:
        raise ValueError(f'Item {nf_item_id} nao pertence a NF {nf_id}')

    chassi_antigo = item.numero_chassi
    motor_antigo = item.numero_motor_texto_original  # preservado p/ audit no retorno
    chassi_norm = (numero_chassi or '').strip().upper() or None
    if not chassi_norm:
        raise ValueError('numero_chassi e obrigatorio no item de NF.')
    if len(chassi_norm) > 30:
        raise ValueError('chassi excede 30 caracteres.')

    # Unicidade (nf_id, numero_chassi)
    if chassi_norm != chassi_antigo:
        dup = (
            HoraNfEntradaItem.query
            .filter(
                HoraNfEntradaItem.nf_id == nf.id,
                HoraNfEntradaItem.numero_chassi == chassi_norm,
                HoraNfEntradaItem.id != item.id,
            )
            .first()
        )
        if dup:
            raise ValueError(
                f'Chassi {chassi_norm} ja esta em outro item (#{dup.id}) desta NF.'
            )

        # Garante hora_moto do chassi novo; preserva o numero_motor textual.
        get_or_create_moto(
            numero_chassi=chassi_norm,
            modelo_nome=item.modelo_texto_original,
            cor=item.cor_texto_original or 'NAO_INFORMADA',
            numero_motor=numero_motor_texto_original if numero_motor_texto_original else None,
            criado_por=operador,
        )

    item.numero_chassi = chassi_norm
    if numero_motor_texto_original is not None:
        item.numero_motor_texto_original = numero_motor_texto_original or None

    db.session.flush()

    # Se o chassi antigo ficou orfao, remove a hora_moto dele.
    # Checa TODAS as tabelas que tem FK para hora_moto.numero_chassi — se
    # alguma ainda referencia, NAO deleta (evita FK violation).
    if chassi_antigo and chassi_antigo != chassi_norm:
        from app.hora.models import (
            HoraMoto, HoraMotoEvento, HoraPedidoItem,
            HoraRecebimentoConferencia, HoraVendaItem, HoraAvaria,
            HoraTransferenciaItem, HoraPecaFaltando,
        )
        def _existe(modelo):
            return db.session.query(
                db.exists().where(modelo.numero_chassi == chassi_antigo)
            ).scalar()

        ainda_referenciado = (
            _existe(HoraNfEntradaItem)
            or _existe(HoraPedidoItem)
            or _existe(HoraMotoEvento)
            or _existe(HoraRecebimentoConferencia)
            or _existe(HoraVendaItem)
            or _existe(HoraAvaria)
            or _existe(HoraTransferenciaItem)
            or _existe(HoraPecaFaltando)
        )
        if not ainda_referenciado:
            HoraMoto.query.filter_by(numero_chassi=chassi_antigo).delete(
                synchronize_session=False
            )

    db.session.commit()

    # ---------------------------------------------------------------
    # Re-validacao pos-edicao
    # ---------------------------------------------------------------
    # 1) Recalcula status do pedido vinculado a esta NF (se houver).
    # 2) Se o chassi ANTIGO aparecia em outro pedido (HoraPedidoItem), recalcula
    #    esse pedido tambem — ele pode ter perdido um chassi faturado.
    # 3) Se o chassi NOVO aparece em outro pedido, recalcula esse pedido tambem
    #    — ele pode ter ganhado um chassi faturado que antes estava "extra".
    # 4) Revalida match NF<->Pedido (flag `itens_divergem_declaracao` re-lida).
    # 5) Retorna diagnostico de vinculos apos edicao (chassi casa ou nao).
    from app.hora.models import HoraPedidoItem  # local p/ evitar ciclo
    from app.hora.services.matching_service import vinculo_por_chassi_nf

    pedidos_a_revalidar = set()
    if nf.pedido_id:
        pedidos_a_revalidar.add(nf.pedido_id)

    if chassi_antigo and chassi_antigo != chassi_norm:
        rows_antigo = (
            db.session.query(HoraPedidoItem.pedido_id)
            .filter(HoraPedidoItem.numero_chassi == chassi_antigo)
            .distinct()
            .all()
        )
        pedidos_a_revalidar.update(r[0] for r in rows_antigo)

    rows_novo = (
        db.session.query(HoraPedidoItem.pedido_id)
        .filter(HoraPedidoItem.numero_chassi == chassi_norm)
        .distinct()
        .all()
    )
    pedidos_a_revalidar.update(r[0] for r in rows_novo)

    for pid in pedidos_a_revalidar:
        if pid:
            atualizar_status_pedido_por_faturamento(pid)

    # Diagnostico de vinculo apos edicao (para exibir no toast de confirmacao)
    vinculos = vinculo_por_chassi_nf(nf.id)
    v = vinculos.get(chassi_norm)
    if v and v.get('vinculado_a_nf'):
        vinculo_status = 'casa com pedido vinculado'
    elif v:
        vinculo_status = f"casa com outro pedido ({v['pedido'].numero_pedido})"
    else:
        vinculo_status = 'sem pedido (chassi nao encontrado em nenhum pedido)'

    return {
        'ok': True,
        'nf_item_id': item.id,
        'numero_chassi': item.numero_chassi,
        'numero_motor_texto_original': item.numero_motor_texto_original,
        'chassi_antigo': chassi_antigo,
        'motor_antigo': motor_antigo,
        'vinculo_status': vinculo_status,
        'pedidos_revalidados': sorted(p for p in pedidos_a_revalidar if p),
    }


def listar_nfs_entrada(limit: int = 100, lojas_permitidas_ids=None, cnpjs_permitidos=None):
    """Lista NFs de entrada. lojas_permitidas_ids=None → todas; filtra por loja_destino_id."""
    query = HoraNfEntrada.query.order_by(
        HoraNfEntrada.data_emissao.desc(), HoraNfEntrada.id.desc()
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        query = query.filter(HoraNfEntrada.loja_destino_id.in_(list(lojas_permitidas_ids)))
    elif cnpjs_permitidos is not None:
        if not cnpjs_permitidos:
            return []
        query = query.filter(HoraNfEntrada.cnpj_destinatario.in_(list(cnpjs_permitidos)))
    return query.limit(limit).all()
