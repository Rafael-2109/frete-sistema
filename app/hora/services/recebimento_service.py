"""Service de recebimento físico: conferência por chassi + emissão de eventos."""
from __future__ import annotations

from app.utils.timezone import agora_utc_naive
from typing import List, Optional

from app import db
from app.hora.models import (
    HoraLoja,
    HoraMoto,
    HoraNfEntrada,
    HoraNfEntradaItem,
    HoraPedidoItem,
    HoraRecebimento,
    HoraRecebimentoConferencia,
)
from app.hora.services.moto_service import registrar_evento


TIPOS_DIVERGENCIA = {
    'MODELO_DIFERENTE',
    'COR_DIFERENTE',
    'MOTO_FALTANDO',
    'CHASSI_EXTRA',
    'MOTOR_DIFERENTE',
    'AVARIA_FISICA',
}


def validar_chassi_contra_recebimento(
    recebimento_id: int,
    numero_chassi: str,
) -> dict:
    """Valida um chassi contra a NF (e pedido vinculado) do recebimento.

    Retorna dict com:
        na_nf: bool — chassi presente em algum item da NF do recebimento
        no_pedido: bool | None — chassi em item do pedido vinculado (None se pedido ausente)
        ja_conferido: bool — conferência já registrada para este chassi neste recebimento
        moto_existe: bool — registro HoraMoto existe
        modelo_esperado: str | None — da NF (texto original) ou do cadastro
        cor_esperada: str | None
        motor_esperado: str | None
        divergencia_sugerida: str | None — enum TIPOS_DIVERGENCIA ou None
        mensagem: str
    """
    chassi_norm = (numero_chassi or '').strip().upper()
    resultado = {
        'chassi': chassi_norm,
        'na_nf': False,
        'no_pedido': None,
        'ja_conferido': False,
        'moto_existe': False,
        'modelo_esperado': None,
        'cor_esperada': None,
        'motor_esperado': None,
        'divergencia_sugerida': None,
        'mensagem': '',
        # Sugestoes: listas agregadas da NF + pedido + cadastro
        'modelos_sugeridos': [],
        'cores_sugeridas': [],
    }

    if not chassi_norm:
        resultado['mensagem'] = 'Chassi vazio.'
        resultado['divergencia_sugerida'] = 'CHASSI_EXTRA'
        return resultado

    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        resultado['mensagem'] = f'Recebimento {recebimento_id} não encontrado.'
        return resultado

    # Item da NF com este chassi?
    item_nf = (
        HoraNfEntradaItem.query
        .filter_by(nf_id=rec.nf_id, numero_chassi=chassi_norm)
        .first()
    )
    resultado['na_nf'] = item_nf is not None

    if item_nf:
        resultado['modelo_esperado'] = item_nf.modelo_texto_original
        resultado['cor_esperada'] = item_nf.cor_texto_original
        resultado['motor_esperado'] = item_nf.numero_motor_texto_original

    # HoraMoto existe?
    moto = HoraMoto.query.get(chassi_norm)
    resultado['moto_existe'] = moto is not None
    if moto and not resultado['modelo_esperado']:
        resultado['modelo_esperado'] = moto.modelo.nome_modelo if moto.modelo else None
        resultado['cor_esperada'] = moto.cor

    # Pedido vinculado?
    if rec.nf and rec.nf.pedido_id:
        pedido_item = (
            HoraPedidoItem.query
            .filter_by(pedido_id=rec.nf.pedido_id, numero_chassi=chassi_norm)
            .first()
        )
        resultado['no_pedido'] = pedido_item is not None

    # Já conferido neste recebimento?
    existente = HoraRecebimentoConferencia.query.filter_by(
        recebimento_id=recebimento_id,
        numero_chassi=chassi_norm,
    ).first()
    resultado['ja_conferido'] = existente is not None

    # Sugestoes de modelo/cor para UI: agrega NF + pedido (contexto proximo).
    # NAO consulta o catalogo geral (hora_modelo) aqui — essa query e chamada
    # a cada keystroke no input de chassi. Se o operador precisar de um modelo
    # fora do contexto, usa o botao "criar novo" que faz uma chamada dedicada.
    modelos = set()
    cores = set()
    for item_nf_rec in rec.nf.itens:
        if item_nf_rec.modelo_texto_original:
            modelos.add(item_nf_rec.modelo_texto_original.strip())
        if item_nf_rec.cor_texto_original:
            cores.add(item_nf_rec.cor_texto_original.strip().upper())
    if rec.nf.pedido_id:
        for item_ped in rec.nf.pedido.itens:
            if item_ped.modelo and item_ped.modelo.nome_modelo:
                modelos.add(item_ped.modelo.nome_modelo.strip())
            if item_ped.cor:
                cores.add(item_ped.cor.strip().upper())

    resultado['modelos_sugeridos'] = sorted(m for m in modelos if m)
    resultado['cores_sugeridas'] = sorted(c for c in cores if c)

    # Divergência sugerida
    if not resultado['na_nf']:
        resultado['divergencia_sugerida'] = 'CHASSI_EXTRA'
        if resultado['no_pedido'] is True:
            resultado['mensagem'] = (
                'Chassi está no pedido mas NÃO na NF. Faturamento pode ter errado.'
            )
        else:
            resultado['mensagem'] = (
                'Chassi NÃO consta na NF deste recebimento. Marque como CHASSI_EXTRA '
                'ou cancele a leitura.'
            )
    elif resultado['ja_conferido']:
        resultado['mensagem'] = (
            'Chassi já foi conferido neste recebimento — registro existente será atualizado.'
        )
    else:
        resultado['mensagem'] = 'Chassi OK — está na NF.'
        if resultado['no_pedido'] is False:
            resultado['mensagem'] += ' (mas não consta no pedido — NF tem item extra)'

    return resultado


def iniciar_recebimento(
    nf_id: int,
    loja_id: int,
    operador: Optional[str] = None,
) -> HoraRecebimento:
    """Cria um recebimento em status EM_CONFERENCIA para uma NF + loja.

    Idempotente: se já existe um recebimento (UNIQUE nf_id+loja_id), retorna ele.
    """
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f"NF {nf_id} não encontrada")
    loja = HoraLoja.query.get(loja_id)
    if not loja:
        raise ValueError(f"Loja {loja_id} não encontrada")

    existente = HoraRecebimento.query.filter_by(nf_id=nf_id, loja_id=loja_id).first()
    if existente:
        return existente

    rec = HoraRecebimento(
        nf_id=nf_id,
        loja_id=loja_id,
        data_recebimento=agora_utc_naive().date(),
        operador=operador,
        status='EM_CONFERENCIA',
    )
    db.session.add(rec)
    db.session.commit()
    return rec


def registrar_conferencia(
    recebimento_id: int,
    numero_chassi: str,
    qr_code_lido: bool,
    foto_s3_key: Optional[str] = None,
    tipo_divergencia: Optional[str] = None,
    detalhe_divergencia: Optional[str] = None,
    operador: Optional[str] = None,
) -> HoraRecebimentoConferencia:
    """Registra conferência de um chassi + emite evento RECEBIDA ou CONFERIDA.

    Se há divergência, evento é CONFERIDA com detalhe (indicando problema).
    Se está OK, evento é RECEBIDA.
    """
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        raise ValueError(f"Recebimento {recebimento_id} não encontrado")
    if rec.status != 'EM_CONFERENCIA':
        raise ValueError(
            f"Recebimento {recebimento_id} não está EM_CONFERENCIA (status={rec.status})"
        )

    chassi_norm = numero_chassi.strip().upper()

    if tipo_divergencia and tipo_divergencia not in TIPOS_DIVERGENCIA:
        raise ValueError(
            f"tipo_divergencia inválido: {tipo_divergencia}. "
            f"Aceitos: {TIPOS_DIVERGENCIA}"
        )

    # Validação AUTOMÁTICA: detecta CHASSI_EXTRA mesmo sem operador marcar.
    validacao = validar_chassi_contra_recebimento(recebimento_id, chassi_norm)

    if not validacao['na_nf']:
        # Chassi desconhecido neste recebimento → força CHASSI_EXTRA.
        if not tipo_divergencia:
            tipo_divergencia = 'CHASSI_EXTRA'
        # Cria HoraMoto mínima para não violar FK (moto "fantasma" com origem
        # desconhecida — operador pode complementar depois).
        if not validacao['moto_existe']:
            from app.hora.services.moto_service import get_or_create_moto
            get_or_create_moto(
                numero_chassi=chassi_norm,
                modelo_nome='CHASSI_EXTRA_DESCONHECIDO',
                cor='NAO_INFORMADA',
                criado_por=operador,
            )
    else:
        moto = HoraMoto.query.get(chassi_norm)
        if not moto:
            raise ValueError(
                f"Chassi {chassi_norm} está na NF mas não existe em hora_moto. "
                f"Reimporte a NF."
            )

    # Idempotência: se já tem conferência deste chassi neste recebimento, atualizar.
    existente = HoraRecebimentoConferencia.query.filter_by(
        recebimento_id=recebimento_id,
        numero_chassi=chassi_norm,
    ).first()

    if existente:
        # Update-in-place permitido aqui (é registro transacional, não HoraMoto).
        existente.qr_code_lido = qr_code_lido
        existente.foto_s3_key = foto_s3_key or existente.foto_s3_key
        existente.tipo_divergencia = tipo_divergencia
        existente.detalhe_divergencia = detalhe_divergencia
        existente.operador = operador
        conferencia = existente
    else:
        conferencia = HoraRecebimentoConferencia(
            recebimento_id=recebimento_id,
            numero_chassi=chassi_norm,
            qr_code_lido=qr_code_lido,
            foto_s3_key=foto_s3_key,
            tipo_divergencia=tipo_divergencia,
            detalhe_divergencia=detalhe_divergencia,
            operador=operador,
        )
        db.session.add(conferencia)
        db.session.flush()

    # Emitir evento correspondente
    tipo_evento = 'CONFERIDA' if tipo_divergencia else 'RECEBIDA'
    detalhe = None
    if tipo_divergencia:
        detalhe = f'Divergencia: {tipo_divergencia}'
        if detalhe_divergencia:
            detalhe += f' — {detalhe_divergencia}'
    registrar_evento(
        numero_chassi=chassi_norm,
        tipo=tipo_evento,
        origem_tabela='hora_recebimento_conferencia',
        origem_id=conferencia.id,
        loja_id=rec.loja_id,
        operador=operador,
        detalhe=detalhe,
    )

    db.session.commit()
    return conferencia


def finalizar_recebimento(recebimento_id: int) -> HoraRecebimento:
    """Conclui o recebimento. Status = CONCLUIDO (sem divergência) ou COM_DIVERGENCIA."""
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        raise ValueError(f"Recebimento {recebimento_id} não encontrado")

    houve_divergencia = any(c.tipo_divergencia for c in rec.conferencias)
    rec.status = 'COM_DIVERGENCIA' if houve_divergencia else 'CONCLUIDO'
    db.session.commit()
    return rec


def chassis_esperados_mas_nao_conferidos(recebimento_id: int) -> List[str]:
    """Retorna chassis que estão na NF mas ainda não foram conferidos (MOTO_FALTANDO candidata)."""
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        return []

    chassis_nf = {item.numero_chassi for item in rec.nf.itens}
    chassis_conferidos = {c.numero_chassi for c in rec.conferencias}
    return sorted(chassis_nf - chassis_conferidos)


def chassis_conferidos_nao_na_nf(recebimento_id: int) -> List[str]:
    """Retorna chassis conferidos que NÃO estão na NF (CHASSI_EXTRA candidatos)."""
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        return []

    chassis_nf = {item.numero_chassi for item in rec.nf.itens}
    chassis_conferidos = {c.numero_chassi for c in rec.conferencias}
    return sorted(chassis_conferidos - chassis_nf)


def marcar_faltantes_em_batch(
    recebimento_id: int,
    operador: Optional[str] = None,
    detalhe: Optional[str] = None,
) -> int:
    """Cria 1 conferencia MOTO_FALTANDO para cada chassi da NF que ainda
    nao foi conferido. Retorna quantidade criada. Idempotente.
    """
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        raise ValueError(f'recebimento {recebimento_id} nao encontrado')
    if rec.status != 'EM_CONFERENCIA':
        raise ValueError(f'recebimento nao esta EM_CONFERENCIA (status={rec.status})')

    faltantes = chassis_esperados_mas_nao_conferidos(recebimento_id)
    total = 0
    for chassi in faltantes:
        conferencia = HoraRecebimentoConferencia(
            recebimento_id=recebimento_id,
            numero_chassi=chassi,
            qr_code_lido=False,
            tipo_divergencia='MOTO_FALTANDO',
            detalhe_divergencia=detalhe or 'Marcado em batch no finalizar',
            operador=operador,
        )
        db.session.add(conferencia)
        db.session.flush()
        registrar_evento(
            numero_chassi=chassi,
            tipo='CONFERIDA',
            origem_tabela='hora_recebimento_conferencia',
            origem_id=conferencia.id,
            loja_id=rec.loja_id,
            operador=operador,
            detalhe='Divergencia: MOTO_FALTANDO (batch)',
        )
        total += 1
    db.session.commit()
    return total


def finalizar_com_faltantes_em_batch(
    recebimento_id: int,
    operador: Optional[str] = None,
) -> HoraRecebimento:
    """Marca faltantes em batch E finaliza em uma chamada."""
    marcar_faltantes_em_batch(recebimento_id, operador=operador)
    return finalizar_recebimento(recebimento_id)


def listar_recebimentos(
    loja_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    lojas_permitidas_ids=None,
) -> List[HoraRecebimento]:
    """Lista recebimentos. lojas_permitidas_ids=None → todas; filtra por loja_id."""
    query = HoraRecebimento.query.order_by(
        HoraRecebimento.data_recebimento.desc(),
        HoraRecebimento.id.desc(),
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        query = query.filter(HoraRecebimento.loja_id.in_(list(lojas_permitidas_ids)))
    if loja_id:
        query = query.filter_by(loja_id=loja_id)
    if status:
        query = query.filter_by(status=status)
    return query.limit(limit).all()
