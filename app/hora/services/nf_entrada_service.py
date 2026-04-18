"""Service de HoraNfEntrada: parsea PDF, cria NF e itens."""
from __future__ import annotations

from typing import Optional

from app import db
from app.hora.models import HoraNfEntrada, HoraNfEntradaItem, HoraPedido
from app.hora.services.moto_service import get_or_create_moto
from app.hora.services.parsers import parse_danfe_to_hora_payload
from app.hora.services.pedido_service import atualizar_status_pedido_por_faturamento
from app.utils.timezone import agora_utc_naive


class NfEntradaJaImportada(Exception):
    """NF com mesma chave_44 já existe."""


def importar_danfe_pdf(
    pdf_bytes: bytes,
    nome_arquivo_origem: Optional[str] = None,
    pedido_id_sugerido: Optional[int] = None,
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
        if not HoraPedido.query.get(pedido_id_vinculo):
            pedido_id_vinculo = None

    nf = HoraNfEntrada(
        chave_44=nf_data['chave_44'],
        numero_nf=nf_data['numero_nf'],
        serie_nf=nf_data.get('serie_nf'),
        cnpj_emitente=nf_data['cnpj_emitente'],
        nome_emitente=nf_data.get('nome_emitente'),
        cnpj_destinatario=nf_data.get('cnpj_destinatario') or '',
        data_emissao=nf_data['data_emissao'],
        valor_total=nf_data['valor_total'],
        pedido_id=pedido_id_vinculo,
        parser_usado=nf_data.get('parser_usado', 'danfe_pdf_parser_v1'),
        parseada_em=agora_utc_naive(),
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


def listar_nfs_entrada(limit: int = 100, cnpjs_permitidos=None):
    """Lista NFs de entrada. cnpjs_permitidos=None → todas; filtra por cnpj_destinatario."""
    query = HoraNfEntrada.query.order_by(
        HoraNfEntrada.data_emissao.desc(), HoraNfEntrada.id.desc()
    )
    if cnpjs_permitidos is not None:
        if not cnpjs_permitidos:
            return []
        query = query.filter(HoraNfEntrada.cnpj_destinatario.in_(list(cnpjs_permitidos)))
    return query.limit(limit).all()
