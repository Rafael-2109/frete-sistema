"""Service de HoraNfEntrada: parsea PDF, cria NF e itens."""
from __future__ import annotations

import io
from decimal import Decimal
from typing import Optional

from flask import current_app

from app import db
from app.hora.models import (
    HoraNfEntrada,
    HoraNfEntradaItem,
    HoraNfEntradaItemPeca,
    HoraPeca,
    HoraPedido,
    PECA_DIVERGENCIA_VALIDAS,
    PECA_MOV_TIPO_ENTRADA_NF,
)
from app.hora.services.moto_service import get_or_create_moto
from app.hora.services.parsers import parse_danfe_to_hora_payload
from app.hora.services.pedido_service import atualizar_status_pedido_por_faturamento
from app.utils.file_storage import FileStorage
from app.utils.timezone import agora_utc_naive


_PECA_FOTO_EXT = {'jpg', 'jpeg', 'png', 'webp', 'heic'}


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
    """NF com mesma chave_44 já existe.

    Carrega `chave_44` e `nf_existente_id` para que callers (especialmente
    importacao em lote) possam linkar para a NF ja existente sem reparsear.
    """

    def __init__(self, message: str, chave_44: Optional[str] = None,
                 nf_existente_id: Optional[int] = None):
        super().__init__(message)
        self.chave_44 = chave_44
        self.nf_existente_id = nf_existente_id


class NfEntradaTemDependencias(Exception):
    """NF nao pode ser removida — possui recebimento fisico ou devolucao vinculada."""


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
            f"NF com chave {nf_data['chave_44']} já importada (id={existente.id})",
            chave_44=nf_data['chave_44'],
            nf_existente_id=existente.id,
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

    # Migration hora_29 (REVISTA): NF NUNCA mais bloqueia por modelo
    # desconhecido (decisao 1.b). Itens com modelo nao reconhecido criam
    # HoraMoto apontando para modelo sentinela DESCONHECIDO + pendencia
    # em hora_modelo_pendente. Quando operador resolver pendencia, a
    # retroatividade UPDATE-eara hora_moto.modelo_id para o canonico.
    from app.hora.models import PENDENTE_ORIGEM_NF_ENTRADA

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
        # fallback_sentinela=True: se modelo nao resolver, cria HoraMoto
        # com modelo_id=DESCONHECIDO + pendencia. Operador resolve depois
        # em /hora/modelos/pendencias e retroatividade corrige modelo_id.
        moto = get_or_create_moto(
            numero_chassi=item['numero_chassi'],
            modelo_nome=item.get('modelo_texto_original'),
            cor=item.get('cor_texto_original') or 'NAO_INFORMADA',
            numero_motor=item.get('numero_motor'),
            ano_modelo=item.get('ano_modelo'),
            criado_por=criado_por,
            origem_pendencia=PENDENTE_ORIGEM_NF_ENTRADA,
            origem_id=nf.id,
            fallback_sentinela=True,
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


def _motivo_bloqueio_desconsiderar(item) -> Optional[str]:
    """Retorna o motivo (str) que impede desconsiderar o item, ou None se liberado.

    Bloqueia se: chassi em pedido (HoraPedidoItem); NF já entrou em recebimento;
    chassi conferido; moto tem qualquer evento (recebida/vendida/avariada/...);
    chassi presente em outro item de NF considerado.
    """
    from app.hora.models import (
        HoraPedidoItem, HoraRecebimento, HoraRecebimentoConferencia,
    )
    from app.hora.services.chassi_protecao_service import chassi_em_pedido
    from app.hora.services.moto_service import status_atual

    chassi = (item.numero_chassi or '').strip().upper()

    if chassi_em_pedido(chassi):
        ped = (
            db.session.query(HoraPedidoItem)
            .filter(HoraPedidoItem.numero_chassi == chassi).first()
        )
        ref = ped.pedido.numero_pedido if ped and ped.pedido else (ped.pedido_id if ped else '?')
        return (
            f'Moto {chassi} consta no pedido {ref}; '
            f'desvincule do pedido antes de desconsiderar.'
        )

    if HoraRecebimento.query.filter_by(nf_id=item.nf_id).first():
        return (
            f'NF #{item.nf_id} já entrou em recebimento; '
            f'desconsidere o item antes de iniciar o recebimento.'
        )

    if HoraRecebimentoConferencia.query.filter_by(
        numero_chassi=chassi, substituida=False,
    ).first():
        return f'Moto {chassi} já foi conferida em um recebimento.'

    ev = status_atual(chassi)
    if ev:
        return f"Moto {chassi} tem evento '{ev}'; não pode ser desconsiderada."

    outro = (
        HoraNfEntradaItem.query
        .filter(
            HoraNfEntradaItem.numero_chassi == chassi,
            HoraNfEntradaItem.id != item.id,
            HoraNfEntradaItem.desconsiderado.is_(False),
        ).first()
    )
    if outro:
        return (
            f'Moto {chassi} também consta na NF #{outro.nf_id} (item considerado); '
            f'não é seguro remover o cadastro da moto.'
        )

    return None


def assert_item_moto_consistente(item) -> None:
    """Invariante (substitui a FK): item considerado => moto existe;
    item desconsiderado => moto não existe. Levanta AssertionError se violado.
    """
    from app.hora.models import HoraMoto
    existe = HoraMoto.query.get((item.numero_chassi or '').strip().upper()) is not None
    if item.desconsiderado and existe:
        raise AssertionError(f'item desconsiderado {item.id} ainda tem HoraMoto')
    if not item.desconsiderado and not existe:
        raise AssertionError(f'item considerado {item.id} sem HoraMoto')


def desconsiderar_item_nf(nf_item_id: int, operador: Optional[str] = None) -> dict:
    """Marca um item de NF como desconsiderado e remove a HoraMoto.

    Pré-condições (senão ValueError, sem mutar): não em pedido, NF sem
    recebimento, chassi não conferido, sem evento de moto, sem outro item de
    NF considerado com o mesmo chassi. Reversível via `reconsiderar_item_nf`.

    Faz `flush()` (NÃO commit) — o commit é responsabilidade do caller (rota).
    """
    from app.hora.models import HoraMoto, HoraMotoEvento

    item = HoraNfEntradaItem.query.get(nf_item_id)
    if not item:
        raise ValueError(f'Item de NF {nf_item_id} não encontrado.')
    if item.desconsiderado:
        return {'ok': True, 'ja_desconsiderado': True, 'nf_item_id': nf_item_id,
                'numero_chassi': item.numero_chassi}

    # 1) Validar TUDO antes de mutar
    motivo = _motivo_bloqueio_desconsiderar(item)
    if motivo:
        raise ValueError(motivo)

    chassi = (item.numero_chassi or '').strip().upper()
    moto = HoraMoto.query.get(chassi)
    # Defensivo: nunca remover moto com eventos (já barrado por _motivo via status_atual)
    if moto is not None and HoraMotoEvento.query.filter_by(numero_chassi=chassi).first():
        raise ValueError(f'Moto {chassi} tem eventos; não pode ser removida.')

    # 2) Mutar (somente após validações)
    item.desconsiderado = True
    if moto is not None:
        db.session.delete(moto)
    db.session.flush()

    current_app.logger.info(
        f'hora: item NF #{nf_item_id} (chassi {chassi}) desconsiderado por '
        f'{operador or "?"}; HoraMoto removida.'
    )
    return {'ok': True, 'nf_item_id': nf_item_id, 'numero_chassi': chassi}


def reconsiderar_item_nf(nf_item_id: int, operador: Optional[str] = None) -> dict:
    """Reverte a desconsideração: recria a HoraMoto e zera o flag.

    Faz `flush()` (NÃO commit) — o commit é responsabilidade do caller (rota).
    """
    from app.hora.models import PENDENTE_ORIGEM_NF_ENTRADA
    from app.hora.services.moto_service import get_or_create_moto

    item = HoraNfEntradaItem.query.get(nf_item_id)
    if not item:
        raise ValueError(f'Item de NF {nf_item_id} não encontrado.')
    if not item.desconsiderado:
        raise ValueError('Item não está desconsiderado.')

    get_or_create_moto(
        numero_chassi=item.numero_chassi,
        modelo_nome=item.modelo_texto_original,
        cor=item.cor_texto_original or 'NAO_INFORMADA',
        numero_motor=item.numero_motor_texto_original,
        criado_por=operador,
        origem_pendencia=PENDENTE_ORIGEM_NF_ENTRADA,
        origem_id=item.nf_id,
        fallback_sentinela=True,
    )
    item.desconsiderado = False
    db.session.flush()
    current_app.logger.info(
        f'hora: item NF #{nf_item_id} (chassi {item.numero_chassi}) reconsiderado '
        f'por {operador or "?"}; HoraMoto recriada.'
    )
    return {'ok': True, 'nf_item_id': nf_item_id, 'numero_chassi': item.numero_chassi}


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


def desvincular_nf_de_pedido(nf_id: int, operador: Optional[str] = None) -> dict:
    """Remove o vinculo NF -> Pedido (zera `nf.pedido_id`).

    Operacao inversa de `vincular_nf_a_pedido`. A NF, seus itens, recebimentos
    e devolucoes permanecem intactos — somente o ponteiro para o pedido
    e zerado. Status do pedido ex-vinculado e recalculado em seguida (pode
    descer de FATURADO -> PARCIALMENTE_FATURADO / ABERTO conforme outras NFs).

    Args:
        nf_id: NF a desvincular.
        operador: nome do usuario (para log de auditoria).

    Raises:
        ValueError: NF nao encontrada ou NF nao esta vinculada a pedido algum.

    Returns:
        dict com `ok`, `nf_id`, `pedido_id` (ex-pedido), `status_pedido` (novo
        status apos recalculo).
    """
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')
    if not nf.pedido_id:
        raise ValueError('Esta NF nao esta vinculada a nenhum pedido.')

    pedido_id_antigo = nf.pedido_id
    nf.pedido_id = None
    db.session.commit()

    # Recalcula status do ex-pedido (pode cair de FATURADO -> PARCIAL / ABERTO).
    # Falha aqui nao deve propagar — o desvinculo ja foi commitado.
    try:
        atualizar_status_pedido_por_faturamento(pedido_id_antigo)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(
            f'hora: NF {nf.numero_nf} (id={nf_id}) desvinculada com sucesso, '
            f'mas falha ao revalidar status do pedido {pedido_id_antigo}: '
            f'{exc}. Revalidar manualmente.'
        )

    pedido_atualizado = HoraPedido.query.get(pedido_id_antigo)
    status_pedido = pedido_atualizado.status if pedido_atualizado else None

    current_app.logger.info(
        f'hora: NF {nf.numero_nf} (id={nf_id}) desvinculada do pedido '
        f'{pedido_id_antigo} por {operador or "?"} — status do pedido: '
        f'{status_pedido}'
    )

    return {
        'ok': True,
        'nf_id': nf_id,
        'pedido_id': pedido_id_antigo,
        'status_pedido': status_pedido,
    }


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
        # fallback_sentinela=True: NF entrada nao bloqueia por modelo
        # desconhecido. Cria pendencia + moto sentinela.
        from app.hora.models import PENDENTE_ORIGEM_NF_ENTRADA
        get_or_create_moto(
            numero_chassi=chassi_norm,
            modelo_nome=item.modelo_texto_original,
            cor=item.cor_texto_original or 'NAO_INFORMADA',
            numero_motor=numero_motor_texto_original if numero_motor_texto_original else None,
            criado_por=operador,
            origem_pendencia=PENDENTE_ORIGEM_NF_ENTRADA,
            origem_id=item.id,
            fallback_sentinela=True,
        )

    item.numero_chassi = chassi_norm
    if numero_motor_texto_original is not None:
        item.numero_motor_texto_original = numero_motor_texto_original or None

    db.session.flush()

    # Reprocessa recebimentos vinculados a NF ANTES da limpeza de motos
    # orfas — o reprocessamento pode deletar conferencias batch sinteticas
    # MOTO_FALTANDO + eventos associados, liberando o chassi_antigo para ser
    # eventualmente removido pelo `_limpar_motos_orfas`. Idempotente.
    if chassi_antigo and chassi_antigo != chassi_norm:
        from app.hora.services.recebimento_service import (
            reprocessar_recebimentos_para_nf,
        )
        reprocessar_recebimentos_para_nf(
            nf_id=nf.id,
            chassi_antigo=chassi_antigo,
            chassi_novo=chassi_norm,
            operador=operador,
        )

    # Se o chassi antigo ficou orfao, remove a hora_moto dele.
    # Reusa fonte unica de verdade `_limpar_motos_orfas` (cobre todas as FKs
    # incluindo HoraEmprestimoMoto.chassi_saida/chassi_entrada).
    if chassi_antigo and chassi_antigo != chassi_norm:
        _limpar_motos_orfas([chassi_antigo])

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


_APELIDO_LOJA_DEFAULT_MATRIZ = 'MOTOCHEFE MATRIZ SP'


def get_loja_default_matriz():
    """Retorna a HoraLoja "MOTOCHEFE MATRIZ SP" (default para upload em lote).

    Usa busca por apelido (case-insensitive) — robusto contra mudanca de id.
    Confirmado em 2026-05-05 que a loja apelido='MOTOCHEFE MATRIZ SP' (id=1
    em prod) e a matriz fiscal cujo CNPJ recebe todas as NFs HORA. Fluxo
    operacional: NF entra na matriz por defeito; loja fisica e ajustada
    apos o import.

    Returns:
        HoraLoja ou None (se cadastro foi removido/renomeado — caller
        decide como reagir).
    """
    from app.hora.models import HoraLoja
    return (
        HoraLoja.query
        .filter(db.func.upper(HoraLoja.apelido) == _APELIDO_LOJA_DEFAULT_MATRIZ)
        .filter(HoraLoja.ativa.is_(True))
        .first()
    )


def importar_danfe_pdfs_lote(
    arquivos: list,  # list[tuple[str, bytes]]  (filename, pdf_bytes)
    loja_destino_id: int,
    criado_por: Optional[str] = None,
) -> dict:
    """Importa N DANFEs em lote, sequencialmente.

    Cada arquivo e tratado em transacao independente (delegada a
    `importar_danfe_pdf` que ja faz commit). Falha em um nao aborta os
    demais. Cada NF herda a `loja_destino_id` informada — operador pode
    ajustar individualmente apos o import via rota `nfs_alterar_loja`.

    Args:
        arquivos: lista de tuplas (filename, pdf_bytes).
        loja_destino_id: loja default aplicada a todas as NFs.
        criado_por: rotulo do usuario responsavel.

    Returns:
        dict com:
          - total: int — total de arquivos processados
          - sucesso: list[dict] — NFs importadas com sucesso
          - duplicada: list[dict] — chave_44 ja existia (link para NF existente)
          - erro: list[dict] — falha de parser ou validacao

        Cada dict de sucesso traz `{filename, nf_id, numero_nf, chave_44,
        n_itens, loja_destino_id, loja_destino_label}`.
    """
    sucesso: list[dict] = []
    duplicada: list[dict] = []
    erro: list[dict] = []

    for filename, pdf_bytes in arquivos:
        try:
            nf = importar_danfe_pdf(
                pdf_bytes=pdf_bytes,
                nome_arquivo_origem=filename,
                pedido_id_sugerido=None,
                loja_destino_id=loja_destino_id,
                criado_por=criado_por,
            )
            sucesso.append({
                'filename': filename,
                'nf_id': nf.id,
                'numero_nf': nf.numero_nf,
                'chave_44': nf.chave_44,
                'n_itens': len(nf.itens),
                'loja_destino_id': nf.loja_destino_id,
                'loja_destino_label': (
                    nf.loja_destino.rotulo_display if nf.loja_destino else '—'
                ),
            })
        except NfEntradaJaImportada as exc:
            duplicada.append({
                'filename': filename,
                'chave_44': exc.chave_44,
                'nf_existente_id': exc.nf_existente_id,
                'mensagem': str(exc),
            })
        except Exception as exc:  # parser, validacao, qualquer outro
            erro.append({
                'filename': filename,
                'mensagem': str(exc),
            })

    current_app.logger.info(
        f'hora: upload em lote por {criado_por or "?"} → '
        f'{len(sucesso)} sucesso, {len(duplicada)} duplicada(s), '
        f'{len(erro)} erro(s) de {len(arquivos)} arquivo(s).'
    )

    return {
        'total': len(arquivos),
        'sucesso': sucesso,
        'duplicada': duplicada,
        'erro': erro,
    }


def _limpar_motos_orfas(chassis: list[str]) -> list[str]:
    """Remove HoraMoto cujo chassi nao e mais referenciado por nenhuma tabela.

    Fonte unica de verdade para limpeza de motos orfa apos remover/reapontar
    referencias em hora_nf_entrada_item. Usado por `remover_nf_entrada` e
    `editar_nf_item_manual`.

    IMPORTANTE: cada novo modelo com FK para `hora_moto.numero_chassi` precisa
    ser adicionado aqui, senao a remocao causa FK violation. Modelos cobertos
    (verificar grep `ForeignKey('hora_moto.numero_chassi')`):
      - HoraNfEntradaItem
      - HoraPedidoItem
      - HoraMotoEvento
      - HoraRecebimentoConferencia
      - HoraVendaItem
      - HoraAvaria
      - HoraTransferenciaItem
      - HoraPecaFaltando
      - HoraEmprestimoMoto (DOIS campos: chassi_saida, chassi_entrada)

    Retorna a lista de chassis que foram efetivamente removidos.
    """
    if not chassis:
        return []
    from sqlalchemy import or_
    from app.hora.models import (
        HoraMoto, HoraMotoEvento, HoraPedidoItem,
        HoraRecebimentoConferencia, HoraVendaItem, HoraAvaria,
        HoraTransferenciaItem, HoraPecaFaltando, HoraEmprestimoMoto,
    )

    def _ainda_referenciado(chassi: str) -> bool:
        # Modelos com 1 coluna FK para chassi
        modelos_simples = (
            HoraNfEntradaItem, HoraPedidoItem, HoraMotoEvento,
            HoraRecebimentoConferencia, HoraVendaItem, HoraAvaria,
            HoraTransferenciaItem, HoraPecaFaltando,
        )
        for modelo in modelos_simples:
            existe = db.session.query(
                db.exists().where(modelo.numero_chassi == chassi)
            ).scalar()
            if existe:
                return True
        # HoraEmprestimoMoto: 2 colunas FK (chassi_saida e chassi_entrada)
        existe_emp = db.session.query(
            db.exists().where(
                or_(
                    HoraEmprestimoMoto.chassi_saida == chassi,
                    HoraEmprestimoMoto.chassi_entrada == chassi,
                )
            )
        ).scalar()
        if existe_emp:
            return True
        return False

    removidos: list[str] = []
    for chassi in chassis:
        if not _ainda_referenciado(chassi):
            HoraMoto.query.filter_by(numero_chassi=chassi).delete(
                synchronize_session=False
            )
            removidos.append(chassi)
    return removidos


def remover_nf_entrada(nf_id: int, operador: Optional[str] = None) -> dict:
    """Remove uma NF de entrada e seus itens.

    Bloqueia se houver:
      - `HoraRecebimento` (recebimento fisico) vinculado
      - `HoraDevolucaoFornecedor` (devolucao a fornecedor) com nf_entrada_id

    Apos remover:
      - Itens (`HoraNfEntradaItem`) saem por cascade.
      - `HoraMoto` orfas (sem referencia em outras tabelas) sao apagadas
        — mesma logica do `editar_nf_item_manual`.
      - Status do pedido vinculado (se existir) e recalculado via
        `atualizar_status_pedido_por_faturamento` (pode descer de FATURADO
        para PARCIALMENTE_FATURADO/ABERTO).
      - PDF/XML no storage sao removidos em best-effort (warn se falhar).
    """
    # Lock pessimista na NF para evitar race com import/edicao concorrente.
    nf = HoraNfEntrada.query.with_for_update().get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')
    db.session.refresh(nf)  # garante que itens estao atualizados (evita identity-map stale)

    from app.hora.models import HoraRecebimento, HoraDevolucaoFornecedor

    rec_count = HoraRecebimento.query.filter_by(nf_id=nf.id).count()
    if rec_count > 0:
        raise NfEntradaTemDependencias(
            f'NF possui {rec_count} recebimento(s) fisico(s) registrado(s). '
            f'Cancele/exclua os recebimentos antes de remover a NF.'
        )

    dev_count = HoraDevolucaoFornecedor.query.filter_by(nf_entrada_id=nf.id).count()
    if dev_count > 0:
        raise NfEntradaTemDependencias(
            f'NF possui {dev_count} devolucao(oes) ao fornecedor vinculada(s). '
            f'Resolva-as antes de remover a NF.'
        )

    pedido_id = nf.pedido_id
    chassis_da_nf = [it.numero_chassi for it in nf.itens]
    s3_key_pdf = nf.arquivo_pdf_s3_key
    s3_key_xml = nf.arquivo_xml_s3_key
    numero_nf = nf.numero_nf
    chave_44 = nf.chave_44

    db.session.delete(nf)
    db.session.flush()

    motos_removidas = _limpar_motos_orfas(chassis_da_nf)

    db.session.commit()

    # NF ja foi removida (irreversivel). Falha no recalculo do pedido NAO deve
    # propagar como erro generico para o operador — registra warning e continua,
    # senao o usuario recebe "erro inesperado" achando que a remocao falhou
    # quando ela ja foi efetivada.
    if pedido_id:
        try:
            atualizar_status_pedido_por_faturamento(pedido_id)
        except Exception as exc:  # pragma: no cover
            current_app.logger.error(
                f'hora: ATENCAO — NF {numero_nf} (id={nf_id}) removida com '
                f'sucesso, mas falha ao revalidar status do pedido {pedido_id}: '
                f'{exc}. Status pode estar inconsistente — revalidar manualmente.'
            )

    storage = FileStorage()
    for s3_key in (s3_key_pdf, s3_key_xml):
        if not s3_key:
            continue
        try:
            storage.delete_file(s3_key)
        except Exception as exc:  # pragma: no cover
            current_app.logger.warning(
                f'hora: falha ao remover arquivo {s3_key} ao excluir NF '
                f'{numero_nf} (chave={chave_44}): {exc}'
            )

    current_app.logger.info(
        f'hora: NF {numero_nf} (id={nf_id}, chave={chave_44}) removida por '
        f'{operador or "?"} — {len(chassis_da_nf)} item(ns), '
        f'{len(motos_removidas)} moto(s) orfa(s) removida(s).'
    )

    return {
        'ok': True,
        'nf_id': nf_id,
        'numero_nf': numero_nf,
        'chassis_removidos': chassis_da_nf,
        'motos_orfas_removidas': motos_removidas,
        'pedido_revalidado': pedido_id,
    }


def alterar_loja_nf_entrada(
    nf_id: int,
    nova_loja_id: int,
    operador: Optional[str] = None,
) -> dict:
    """Altera a loja de destino de uma NF de entrada.

    Cobre os dois casos:
      - NF sem loja (`loja_destino_id is None`) → atribui loja inicial.
      - NF com loja → troca para outra loja.

    Bloqueia se:
      - Loja nao existe ou esta inativa.
      - NF tem recebimento fisico em loja diferente da nova
        (alterar a loja apos receber e contraditorio).
      - NF esta vinculada a pedido cuja loja e diferente da nova
        (mantem coerencia NF×Pedido).
    """
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')

    from app.hora.models import HoraLoja, HoraRecebimento

    loja = HoraLoja.query.get(nova_loja_id)
    if not loja:
        raise ValueError(f'Loja {nova_loja_id} nao encontrada')
    if not loja.ativa:
        raise ValueError(f'Loja {loja.rotulo_display} esta inativa')

    if nf.loja_destino_id == nova_loja_id:
        return {'ok': True, 'inalterado': True, 'nf_id': nf.id}

    rec = HoraRecebimento.query.filter_by(nf_id=nf.id).first()
    if rec and rec.loja_id != nova_loja_id:
        raise ValueError(
            f'NF ja possui recebimento fisico (id={rec.id}) em loja diferente. '
            f'Nao e possivel trocar a loja apos receber.'
        )

    if nf.pedido_id:
        pedido = HoraPedido.query.get(nf.pedido_id)
        if pedido and pedido.loja_destino_id and pedido.loja_destino_id != nova_loja_id:
            raise ValueError(
                f'Pedido vinculado ({pedido.numero_pedido}) e da loja '
                f'{pedido.loja_destino.rotulo_display if pedido.loja_destino else pedido.loja_destino_id}. '
                f'Desvincule o pedido ou escolha uma loja compativel.'
            )

    loja_anterior_id = nf.loja_destino_id
    nf.loja_destino_id = nova_loja_id
    db.session.commit()

    current_app.logger.info(
        f'hora: NF {nf.numero_nf} (id={nf.id}) — loja alterada de '
        f'{loja_anterior_id} para {nova_loja_id} por {operador or "?"}.'
    )

    return {
        'ok': True,
        'nf_id': nf.id,
        'loja_anterior_id': loja_anterior_id,
        'loja_nova_id': nova_loja_id,
    }


def exportar_nfs_excel(
    data_inicio=None,
    data_fim=None,
    lojas_ids=None,
    limit: int = 10000,
) -> bytes:
    """Exporta NFs de entrada com itens e vinculo de pedido por chassi para XLSX.

    Cada linha = 1 item da NF (chassi). Se NF tem pedido vinculado, mostra
    dados do pedido + tenta casar item-pedido pelo chassi para diferenca de preco.
    """
    import io
    import pandas as pd
    from app.hora.models import HoraPedidoItem

    query = HoraNfEntrada.query
    if data_inicio:
        query = query.filter(HoraNfEntrada.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(HoraNfEntrada.data_emissao <= data_fim)
    if lojas_ids is not None:
        if not lojas_ids:
            nfs = []
        else:
            query = query.filter(HoraNfEntrada.loja_destino_id.in_(lojas_ids))
            nfs = query.order_by(HoraNfEntrada.data_emissao.desc(), HoraNfEntrada.id.desc()).limit(limit).all()
    else:
        nfs = query.order_by(HoraNfEntrada.data_emissao.desc(), HoraNfEntrada.id.desc()).limit(limit).all()

    # Mapa (pedido_id, chassi) -> HoraPedidoItem para casar preco esperado.
    pedido_ids = {nf.pedido_id for nf in nfs if nf.pedido_id}
    itens_pedido_map: dict[tuple, HoraPedidoItem] = {}
    if pedido_ids:
        itens = (
            HoraPedidoItem.query
            .filter(HoraPedidoItem.pedido_id.in_(list(pedido_ids)))
            .filter(HoraPedidoItem.numero_chassi.isnot(None))
            .all()
        )
        for it in itens:
            itens_pedido_map[(it.pedido_id, it.numero_chassi)] = it

    linhas = []
    for nf in nfs:
        loja_nome = nf.loja_destino.rotulo_display if nf.loja_destino else ''
        pedido = nf.pedido
        for nfi in nf.itens:
            chassi = nfi.numero_chassi
            preco_real = float(nfi.preco_real) if nfi.preco_real is not None else None

            item_ped = itens_pedido_map.get((pedido.id, chassi)) if pedido else None
            preco_esp = (
                float(item_ped.preco_compra_esperado)
                if item_ped and item_ped.preco_compra_esperado is not None
                else None
            )
            diferenca = (preco_real - preco_esp) if (preco_real is not None and preco_esp is not None) else None

            if pedido and item_ped:
                vinculo_chassi = 'CASADO'
            elif pedido and not item_ped:
                vinculo_chassi = 'CHASSI_NAO_NO_PEDIDO'
            else:
                vinculo_chassi = 'NF_SEM_PEDIDO'

            linhas.append({
                'NF Número': nf.numero_nf,
                'Série': nf.serie_nf or '',
                'Chave 44': nf.chave_44,
                'Data Emissão': nf.data_emissao,
                'Emitente': nf.nome_emitente or '',
                'CNPJ Emitente': nf.cnpj_emitente,
                'Loja Destino': loja_nome,
                'Valor Total NF': float(nf.valor_total) if nf.valor_total is not None else None,
                'Pedido Vinculado': pedido.numero_pedido if pedido else '',
                'Data Pedido': pedido.data_pedido if pedido else None,
                'Status Pedido': pedido.status if pedido else '',
                'Chassi': chassi,
                'Modelo (NF)': nfi.modelo_texto_original or '',
                'Cor (NF)': nfi.cor_texto_original or '',
                'Preço Real (NF)': preco_real,
                'Preço Esperado (Pedido)': preco_esp,
                'Diferença Preço': diferenca,
                'Vínculo Chassi↔Pedido': vinculo_chassi,
            })

    df = pd.DataFrame(linhas, columns=[
        'NF Número', 'Série', 'Chave 44', 'Data Emissão',
        'Emitente', 'CNPJ Emitente', 'Loja Destino', 'Valor Total NF',
        'Pedido Vinculado', 'Data Pedido', 'Status Pedido',
        'Chassi', 'Modelo (NF)', 'Cor (NF)',
        'Preço Real (NF)', 'Preço Esperado (Pedido)', 'Diferença Preço',
        'Vínculo Chassi↔Pedido',
    ])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='NFs Compra HORA')
        ws = writer.sheets['NFs Compra HORA']
        for col_idx, col in enumerate(df.columns, start=1):
            max_len = max(
                [len(str(col))] + [len(str(v)) for v in df[col].head(200).astype(str)]
            )
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_len + 2, 40)

    output.seek(0)
    return output.read()


def listar_nfs_entrada(
    limit: int = 100,
    lojas_permitidas_ids=None,
    cnpjs_permitidos=None,
    *,
    numero_nf=None,
    emitente=None,
    loja_id=None,
    data_inicio=None,
    data_fim=None,
    vinculo_status=None,  # 'vinculada' | 'sem_pedido' | None
):
    """Lista NFs de entrada com filtros opcionais.

    Filtros:
    - numero_nf: substring no campo numero_nf (ilike)
    - emitente: substring em nome_emitente OU cnpj_emitente
    - loja_id: id especifico de loja_destino_id
    - data_inicio / data_fim: faixa em data_emissao
    - vinculo_status: 'vinculada' (pedido_id is not None) ou 'sem_pedido'

    Escopo:
    - lojas_permitidas_ids=None -> todas
    - lista vazia -> []
    """
    from sqlalchemy import or_
    from sqlalchemy.orm import selectinload

    # selectinload evita N+1 ao acessar nf.itens e nf.pedido no template
    # e em matching_service.resumo_vinculo_nf / comparativo_valores_nf.
    # Sentry PYTHON-FLASK-VJ (hora_nf_entrada_item) e PYTHON-FLASK-VK (hora_pedido).
    query = HoraNfEntrada.query.options(
        selectinload(HoraNfEntrada.itens),
        selectinload(HoraNfEntrada.pedido),
    ).order_by(
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

    if numero_nf:
        query = query.filter(HoraNfEntrada.numero_nf.ilike(f'%{numero_nf.strip()}%'))
    if emitente:
        e = emitente.strip()
        query = query.filter(or_(
            HoraNfEntrada.nome_emitente.ilike(f'%{e}%'),
            HoraNfEntrada.cnpj_emitente.ilike(f'%{e}%'),
        ))
    if loja_id:
        query = query.filter(HoraNfEntrada.loja_destino_id == loja_id)
    if data_inicio:
        query = query.filter(HoraNfEntrada.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(HoraNfEntrada.data_emissao <= data_fim)
    if vinculo_status == 'vinculada':
        query = query.filter(HoraNfEntrada.pedido_id.isnot(None))
    elif vinculo_status == 'sem_pedido':
        query = query.filter(HoraNfEntrada.pedido_id.is_(None))

    return query.limit(limit).all()


# ============================================================
# Itens de PECA em NF de entrada (XOR moto/peca aplicado em camada de UI)
# ============================================================

def adicionar_item_peca_nf(
    nf_id: int,
    peca_id: int,
    qtd_nf,
    preco_real,
    modelo_texto_original: Optional[str] = None,
) -> HoraNfEntradaItemPeca:
    """Adiciona linha de peca em NF de entrada (manual ou via parser).

    Nao emite movimento de estoque — isso so acontece em conferir_item_peca_nf.
    """
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')
    if not HoraPeca.query.get(peca_id):
        raise ValueError(f'Peca {peca_id} nao existe')
    qtd = Decimal(str(qtd_nf or 0))
    if qtd <= 0:
        raise ValueError('qtd_nf deve ser positiva')
    preco = Decimal(str(preco_real or 0))
    if preco < 0:
        raise ValueError('preco_real nao pode ser negativo')

    item = HoraNfEntradaItemPeca(
        nf_id=nf.id,
        peca_id=peca_id,
        qtd_nf=qtd,
        preco_real=preco,
        modelo_texto_original=(modelo_texto_original or '').strip() or None,
    )
    db.session.add(item)
    db.session.commit()
    return item


def remover_item_peca_nf(nf_item_id: int) -> None:
    """Remove item peca de NF. Bloqueia se ja conferida."""
    item = HoraNfEntradaItemPeca.query.get(nf_item_id)
    if not item:
        raise ValueError(f'Item peca {nf_item_id} nao encontrado')
    if item.qtd_conferida is not None:
        raise ValueError(
            f'Item ja foi conferido em {item.conferida_em} '
            f'(qtd_conferida={item.qtd_conferida}). Estorne primeiro.'
        )
    db.session.delete(item)
    db.session.commit()


def conferir_item_peca_nf(
    nf_item_id: int,
    qtd_conferida,
    divergencia_qtd: str = 'OK',
    foto_file=None,
    operador: Optional[str] = None,
) -> HoraNfEntradaItemPeca:
    """Confere item peca + emite ENTRADA_NF no estoque na loja destino.

    Idempotencia: se ja conferido, atualiza valores e ajusta movimento (delta).
    Para conferencia inicial, emite movimento ENTRADA_NF com qtd_conferida.
    """
    from app.hora.services import peca_estoque_service

    item = HoraNfEntradaItemPeca.query.get(nf_item_id)
    if not item:
        raise ValueError(f'Item peca {nf_item_id} nao encontrado')
    qtd_conf = Decimal(str(qtd_conferida or 0))
    if qtd_conf < 0:
        raise ValueError('qtd_conferida nao pode ser negativa')
    if divergencia_qtd not in PECA_DIVERGENCIA_VALIDAS:
        raise ValueError(
            f'divergencia_qtd invalida: {divergencia_qtd!r}. '
            f'Valores: {", ".join(PECA_DIVERGENCIA_VALIDAS)}'
        )

    nf = item.nf
    if not nf.loja_destino_id:
        raise ValueError('NF sem loja_destino_id — defina antes de conferir.')

    # Foto opcional.
    if foto_file and getattr(foto_file, 'filename', ''):
        storage = FileStorage()
        folder = f'hora/nf_entrada/{nf.id}/peca/{item.id}'
        s3_key = storage.save_file(
            file=foto_file, folder=folder, allowed_extensions=_PECA_FOTO_EXT,
        )
        if s3_key:
            item.foto_conferencia_s3_key = s3_key

    qtd_anterior = item.qtd_conferida
    item.qtd_conferida = qtd_conf
    item.divergencia_qtd = divergencia_qtd
    item.conferida_em = agora_utc_naive()
    item.conferida_por = operador

    # Movimento de estoque: delta entre qtd_anterior e qtd_atual.
    delta = qtd_conf - Decimal(str(qtd_anterior or 0))
    if delta != 0:
        peca_estoque_service.registrar_movimento(
            peca_id=item.peca_id,
            loja_id=nf.loja_destino_id,
            tipo=PECA_MOV_TIPO_ENTRADA_NF,
            qtd=delta,
            ref_tabela='hora_nf_entrada_item_peca',
            ref_id=item.id,
            motivo=f'Conferencia NF #{nf.id} ({divergencia_qtd})',
            operador=operador,
        )

    db.session.commit()
    return item
