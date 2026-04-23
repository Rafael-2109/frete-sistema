"""Service de recebimento físico: conferência CEGA por chassi + auditoria.

Fluxo:
  1. iniciar_recebimento(nf_id, loja_id) -> status=AGUARDANDO_QTD
  2. definir_qtd_declarada(id, qtd)      -> status=EM_CONFERENCIA, ordem=1..qtd
  3. registrar_conferencia_cega(id, ordem, chassi, modelo_id, cor, avaria, ...)
     - deriva divergencias 1-N em hora_conferencia_divergencia
     - grava auditoria
  4. finalizar_recebimento(id)          -> marca MOTO_FALTANDO em batch + status
  5. Reconferencia: reiniciar_conferencia_para_chassis(id, [chassis])
     - cria NOVAS linhas; antigas -> substituida=True (historico 3a)
"""
from __future__ import annotations

from typing import List, Optional

from app import db
from app.utils.timezone import agora_utc_naive
from app.hora.models import (
    HoraConferenciaDivergencia,
    HoraLoja,
    HoraMoto,
    HoraModelo,
    HoraNfEntrada,
    HoraNfEntradaItem,
    HoraPedidoItem,
    HoraRecebimento,
    HoraRecebimentoConferencia,
)
from app.hora.services.moto_service import registrar_evento
from app.hora.services import recebimento_audit


# MOTOR_DIFERENTE removido: nao existe base para conferir motor.
TIPOS_DIVERGENCIA = {
    'MODELO_DIFERENTE',
    'COR_DIFERENTE',
    'MOTO_FALTANDO',
    'CHASSI_EXTRA',
    'AVARIA_FISICA',
}


# ========================================================================
# Helpers
# ========================================================================

def _normalizar_cor(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    return v.strip().upper() or None


def _normalizar_modelo_nome(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    return v.strip().upper() or None


# ========================================================================
# Validacao pre-conferencia (usado pelo wizard ao scanear chassi)
# ========================================================================

def validar_chassi_contra_recebimento(
    recebimento_id: int,
    numero_chassi: str,
) -> dict:
    """Chamada no passo A do wizard, logo apos scan do chassi.

    Retorna dict com contexto para o wizard: item da NF (se existir),
    sugestoes de modelo/cor, ja_conferido.
    """
    chassi_norm = (numero_chassi or '').strip().upper()
    resultado = {
        'chassi': chassi_norm,
        'na_nf': False,
        'no_pedido': None,
        'ja_conferido': False,
        'conferencia_ativa_id': None,
        'moto_existe': False,
        'modelo_esperado': None,
        'cor_esperada': None,
        'mensagem': '',
        'modelos_sugeridos': [],
        'cores_sugeridas': [],
    }
    if not chassi_norm:
        resultado['mensagem'] = 'Chassi vazio.'
        return resultado

    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        resultado['mensagem'] = f'Recebimento {recebimento_id} nao encontrado.'
        return resultado

    item_nf = (
        HoraNfEntradaItem.query
        .filter_by(nf_id=rec.nf_id, numero_chassi=chassi_norm)
        .first()
    )
    resultado['na_nf'] = item_nf is not None
    if item_nf:
        resultado['modelo_esperado'] = item_nf.modelo_texto_original
        resultado['cor_esperada'] = item_nf.cor_texto_original

    moto = HoraMoto.query.get(chassi_norm)
    resultado['moto_existe'] = moto is not None

    if rec.nf and rec.nf.pedido_id and rec.nf.pedido:
        ped_item = (
            HoraPedidoItem.query
            .filter_by(pedido_id=rec.nf.pedido_id, numero_chassi=chassi_norm)
            .first()
        )
        resultado['no_pedido'] = ped_item is not None

    existente = (
        HoraRecebimentoConferencia.query
        .filter_by(recebimento_id=recebimento_id, numero_chassi=chassi_norm,
                   substituida=False)
        .first()
    )
    if existente:
        resultado['ja_conferido'] = True
        resultado['conferencia_ativa_id'] = existente.id

    modelos, cores = set(), set()
    for i in rec.nf.itens:
        if i.modelo_texto_original:
            modelos.add(i.modelo_texto_original.strip())
        if i.cor_texto_original:
            cores.add(i.cor_texto_original.strip().upper())
    if rec.nf.pedido_id and rec.nf.pedido:
        for pi in rec.nf.pedido.itens:
            if pi.modelo and pi.modelo.nome_modelo:
                modelos.add(pi.modelo.nome_modelo.strip())
            if pi.cor:
                cores.add(pi.cor.strip().upper())
    resultado['modelos_sugeridos'] = sorted(m for m in modelos if m)
    resultado['cores_sugeridas'] = sorted(c for c in cores if c)

    if not resultado['na_nf']:
        resultado['mensagem'] = (
            'Chassi NAO consta na NF deste recebimento. Sera registrado como CHASSI_EXTRA.'
        )
    elif resultado['ja_conferido']:
        resultado['mensagem'] = 'Chassi ja conferido nesta sessao (ativo).'
    else:
        resultado['mensagem'] = 'Chassi OK — esta na NF.'
    return resultado


# ========================================================================
# Fluxo principal
# ========================================================================

def iniciar_recebimento(
    nf_id: int,
    loja_id: int,
    operador: Optional[str] = None,
) -> HoraRecebimento:
    """Cria (ou retorna existente) recebimento em AGUARDANDO_QTD."""
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f"NF {nf_id} nao encontrada")
    loja = HoraLoja.query.get(loja_id)
    if not loja:
        raise ValueError(f"Loja {loja_id} nao encontrada")

    existente = HoraRecebimento.query.filter_by(nf_id=nf_id, loja_id=loja_id).first()
    if existente:
        return existente

    rec = HoraRecebimento(
        nf_id=nf_id,
        loja_id=loja_id,
        data_recebimento=agora_utc_naive().date(),
        operador=operador,
        status='AGUARDANDO_QTD',
    )
    db.session.add(rec)
    db.session.flush()
    recebimento_audit.registrar(
        recebimento_id=rec.id,
        acao='INICIOU_RECEBIMENTO',
        usuario=operador,
        detalhe=f'NF {nf.numero_nf} -> loja {loja.rotulo_display}',
    )
    db.session.commit()
    return rec


def definir_qtd_declarada(
    recebimento_id: int,
    qtd: int,
    usuario: Optional[str] = None,
) -> HoraRecebimento:
    """Etapa 2: conferência cega macro.

    Valor baixo NAO bloqueia (auditoria mostra se operador burlar).
    """
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if qtd is None or qtd < 1:
        raise ValueError("Qtd deve ser >= 1")
    if rec.status not in ('AGUARDANDO_QTD', 'EM_CONFERENCIA'):
        raise ValueError(f"Recebimento em status {rec.status} nao aceita alterar qtd")

    valor_antes = rec.qtd_declarada
    acao = 'ALTEROU_QTD' if valor_antes is not None else 'DEFINIU_QTD'

    rec.qtd_declarada = qtd
    if rec.status == 'AGUARDANDO_QTD':
        rec.status = 'EM_CONFERENCIA'

    recebimento_audit.registrar(
        recebimento_id=rec.id,
        acao=acao,
        usuario=usuario,
        campo_alterado='qtd_declarada',
        valor_antes=valor_antes,
        valor_depois=qtd,
    )
    db.session.commit()
    return rec


def proxima_ordem(recebimento_id: int) -> int:
    """Menor inteiro >= 1 sem conferência ATIVA (substituida=false) no recebimento."""
    usados = {
        row[0]
        for row in (
            db.session.query(HoraRecebimentoConferencia.ordem)
            .filter(HoraRecebimentoConferencia.recebimento_id == recebimento_id,
                    HoraRecebimentoConferencia.substituida.is_(False))
            .all()
        )
    }
    i = 1
    while i in usados:
        i += 1
    return i


def registrar_conferencia_cega(
    recebimento_id: int,
    numero_chassi: str,
    modelo_id_conferido: Optional[int],
    cor_conferida: Optional[str],
    avaria_fisica: bool,
    qr_code_lido: bool = False,
    foto_s3_key: Optional[str] = None,
    ordem: Optional[int] = None,
    operador: Optional[str] = None,
) -> HoraRecebimentoConferencia:
    """Registra conferencia cega: chassi + modelo + cor + avaria.

    Backend compara com NF e deriva divergencias 1-N em
    hora_conferencia_divergencia.
    """
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        raise ValueError(f"Recebimento {recebimento_id} nao encontrado")
    if rec.status != 'EM_CONFERENCIA':
        raise ValueError(
            f"Recebimento {recebimento_id} em status {rec.status} nao aceita conferencia"
        )

    chassi_norm = (numero_chassi or '').strip().upper()
    if not chassi_norm:
        raise ValueError("numero_chassi obrigatorio")
    cor_norm = _normalizar_cor(cor_conferida)

    # Se ja existe conferencia ATIVA para este chassi, reusar (update-in-place)
    conf = (
        HoraRecebimentoConferencia.query
        .filter_by(recebimento_id=recebimento_id, numero_chassi=chassi_norm,
                   substituida=False)
        .first()
    )

    is_new = conf is None
    if is_new:
        ordem_final = ordem if (ordem and ordem >= 1) else proxima_ordem(recebimento_id)
        # Garantir HoraMoto existe (FK)
        item_nf = HoraNfEntradaItem.query.filter_by(
            nf_id=rec.nf_id, numero_chassi=chassi_norm,
        ).first()
        _garantir_moto(chassi_norm, item_nf, operador)
        conf = HoraRecebimentoConferencia(
            recebimento_id=recebimento_id,
            numero_chassi=chassi_norm,
            ordem=ordem_final,
            qr_code_lido=qr_code_lido,
            foto_s3_key=foto_s3_key,
            modelo_id_conferido=modelo_id_conferido,
            cor_conferida=cor_norm,
            avaria_fisica=bool(avaria_fisica),
            confirmado_em=agora_utc_naive(),
            operador=operador,
        )
        db.session.add(conf)
        db.session.flush()
    else:
        # Update-in-place + auditoria campo a campo.
        _audita_update(conf, {
            'modelo_id_conferido': modelo_id_conferido,
            'cor_conferida': cor_norm,
            'avaria_fisica': bool(avaria_fisica),
            'qr_code_lido': qr_code_lido or conf.qr_code_lido,
            'foto_s3_key': foto_s3_key or conf.foto_s3_key,
        }, usuario=operador, recebimento_id=recebimento_id)
        conf.confirmado_em = agora_utc_naive()
        conf.operador = operador

    # Deriva divergencias 1-N
    _redefinir_divergencias(conf, rec)

    # Evento de moto
    item_nf = HoraNfEntradaItem.query.filter_by(
        nf_id=rec.nf_id, numero_chassi=chassi_norm,
    ).first()
    tipo_evento = 'RECEBIDA' if (item_nf and not conf.divergencias) else 'CONFERIDA'
    detalhe_evento = None
    if conf.divergencias:
        tipos = ', '.join(sorted({d.tipo for d in conf.divergencias}))
        detalhe_evento = f'Divergencias: {tipos}'
    registrar_evento(
        numero_chassi=chassi_norm,
        tipo=tipo_evento,
        origem_tabela='hora_recebimento_conferencia',
        origem_id=conf.id,
        loja_id=rec.loja_id,
        operador=operador,
        detalhe=detalhe_evento,
    )

    # Auditoria header
    recebimento_audit.registrar(
        recebimento_id=rec.id,
        conferencia_id=conf.id,
        acao='CONFERIU_MOTO' if is_new else 'AJUSTOU_CAMPO',
        usuario=operador,
        detalhe=(
            f'ordem={conf.ordem} chassi={chassi_norm} '
            f'modelo_id={modelo_id_conferido} cor={cor_norm} avaria={bool(avaria_fisica)}'
        ),
    )
    if avaria_fisica:
        recebimento_audit.registrar(
            recebimento_id=rec.id,
            conferencia_id=conf.id,
            acao='MARCOU_AVARIA',
            usuario=operador,
        )

    db.session.commit()
    return conf


def reiniciar_conferencia_para_chassis(
    recebimento_id: int,
    conferencia_ids: List[int],
    operador: Optional[str] = None,
) -> List[HoraRecebimentoConferencia]:
    """Reconferencia 3a): marca as linhas escolhidas como `substituida=True`
    e cria NOVAS linhas pendentes (confirmado_em=NULL) com os mesmos
    chassi/ordem para serem refeitas no wizard.

    Retorna as NOVAS conferencias pendentes (enfileiradas).
    """
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if rec.status not in ('EM_CONFERENCIA', 'CONCLUIDO', 'COM_DIVERGENCIA'):
        raise ValueError(f"Recebimento em status {rec.status} nao permite reconferencia")

    # Se ja finalizado, volta a EM_CONFERENCIA para permitir reconferencia.
    if rec.status in ('CONCLUIDO', 'COM_DIVERGENCIA'):
        rec.status = 'EM_CONFERENCIA'
        rec.finalizado_em = None

    novas = []
    for conf_id in conferencia_ids:
        conf = HoraRecebimentoConferencia.query.get(conf_id)
        if not conf or conf.recebimento_id != recebimento_id:
            continue
        if conf.substituida:
            continue
        # Marca antiga substituida
        conf.substituida = True
        # Garante que UNIQUE parcial nao conflite: ordem ficara livre ate commit
        # da nova linha — flush intermediario.
        db.session.flush()
        # Nova linha pendente (confirmado_em=NULL) com mesmos chassi/ordem.
        nova = HoraRecebimentoConferencia(
            recebimento_id=recebimento_id,
            numero_chassi=conf.numero_chassi,
            ordem=conf.ordem,
            qr_code_lido=False,
            modelo_id_conferido=conf.modelo_id_conferido,
            cor_conferida=conf.cor_conferida,
            avaria_fisica=conf.avaria_fisica,
            confirmado_em=None,
            operador=operador,
        )
        db.session.add(nova)
        db.session.flush()
        conf.substituida_por_id = nova.id
        novas.append(nova)

        recebimento_audit.registrar(
            recebimento_id=recebimento_id,
            conferencia_id=conf.id,
            acao='SUBSTITUIU_CONFERENCIA',
            usuario=operador,
            detalhe=f'substituida_por={nova.id} ordem={conf.ordem} chassi={conf.numero_chassi}',
        )
        recebimento_audit.registrar(
            recebimento_id=recebimento_id,
            conferencia_id=nova.id,
            acao='RECONFEREU_MOTO',
            usuario=operador,
            detalhe=f'pendente ordem={nova.ordem} chassi={nova.numero_chassi}',
        )
    db.session.commit()
    return novas


def finalizar_recebimento(
    recebimento_id: int,
    operador: Optional[str] = None,
) -> HoraRecebimento:
    """Marca MOTO_FALTANDO em batch para chassis da NF sem conferencia ativa,
    e seta status CONCLUIDO ou COM_DIVERGENCIA.
    """
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        raise ValueError(f"Recebimento {recebimento_id} nao encontrado")

    chassis_nf = {i.numero_chassi for i in rec.nf.itens}
    chassis_conferidos_ativos = {
        c.numero_chassi for c in rec.conferencias if not c.substituida
    }
    faltantes = sorted(chassis_nf - chassis_conferidos_ativos)

    # Garantir que cada chassi faltante vire uma conferencia MOTO_FALTANDO.
    if faltantes:
        for chassi in faltantes:
            ordem = proxima_ordem(recebimento_id)
            _garantir_moto(chassi, None, operador)
            conf = HoraRecebimentoConferencia(
                recebimento_id=recebimento_id,
                numero_chassi=chassi,
                ordem=ordem,
                qr_code_lido=False,
                avaria_fisica=False,
                tipo_divergencia='MOTO_FALTANDO',
                detalhe_divergencia='Faltante no fechamento',
                operador=operador,
            )
            db.session.add(conf)
            db.session.flush()
            # Divergencia 1-N
            db.session.add(HoraConferenciaDivergencia(
                conferencia_id=conf.id,
                tipo='MOTO_FALTANDO',
                detalhe='Faltante no fechamento',
            ))
            registrar_evento(
                numero_chassi=chassi,
                tipo='CONFERIDA',
                origem_tabela='hora_recebimento_conferencia',
                origem_id=conf.id,
                loja_id=rec.loja_id,
                operador=operador,
                detalhe='Divergencia: MOTO_FALTANDO (batch)',
            )

    # Recarrega conferencias (expira cache ORM apos batch insert de faltantes)
    if faltantes:
        db.session.expire(rec, ['conferencias'])
    confs_ativas = [c for c in rec.conferencias if not c.substituida]
    # Faltantes recem-criadas ja sao divergencia — cobertura explicita caso
    # ORM cache nao refresque a tempo.
    houve_divergencia = (
        bool(faltantes)
        or any(c.divergencias or c.tipo_divergencia for c in confs_ativas)
    )
    rec.status = 'COM_DIVERGENCIA' if houve_divergencia else 'CONCLUIDO'
    rec.finalizado_em = agora_utc_naive()

    recebimento_audit.registrar(
        recebimento_id=rec.id,
        acao='FINALIZOU',
        usuario=operador,
        detalhe=f'status={rec.status} faltantes={len(faltantes)}',
    )
    db.session.commit()
    return rec


# ========================================================================
# Comparativo lado-a-lado (tela T4)
# ========================================================================

def comparativo_recebimento_nf(recebimento_id: int) -> dict:
    """Produz dict para a tela de resumo lado-a-lado.

    {
      'linhas': [ {chassi, nf_item, conferencia, divergencias, status, avaria} ],
      'totais': {esperado, conferido, ok, com_divergencia, avarias, extras, faltantes}
    }
    """
    rec = HoraRecebimento.query.get_or_404(recebimento_id)

    # Chassis conhecidos: da NF + da conferencia ativa
    chassis_nf = [i.numero_chassi for i in rec.nf.itens if i.numero_chassi]
    confs_ativas = [c for c in rec.conferencias if not c.substituida]
    chassis_conf = [c.numero_chassi for c in confs_ativas]

    todos = []
    seen = set()
    # Preserva ordem NF primeiro, depois extras na ordem de conferencia
    for c in chassis_nf:
        if c not in seen:
            todos.append(c)
            seen.add(c)
    for c in chassis_conf:
        if c not in seen:
            todos.append(c)
            seen.add(c)

    nf_por_chassi = {i.numero_chassi: i for i in rec.nf.itens if i.numero_chassi}
    conf_por_chassi = {c.numero_chassi: c for c in confs_ativas}

    linhas = []
    ok = com_divergencia = avarias = extras = faltantes = 0
    for chassi in todos:
        nf_item = nf_por_chassi.get(chassi)
        conf = conf_por_chassi.get(chassi)
        divergencias = []
        if conf:
            divergencias = list(conf.divergencias)
            if conf.tipo_divergencia and not divergencias:
                # Legado (MOTO_FALTANDO em batch)
                divergencias = [_divergencia_legado(conf)]
        if not conf:
            status = 'FALTANDO'
            faltantes += 1
        elif not nf_item:
            status = 'EXTRA'
            extras += 1
            if conf.avaria_fisica:
                avarias += 1
            com_divergencia += 1
        elif divergencias:
            status = 'DIVERGENTE'
            com_divergencia += 1
            if conf.avaria_fisica:
                avarias += 1
        else:
            status = 'OK'
            ok += 1
        linhas.append({
            'chassi': chassi,
            'nf_item': nf_item,
            'conferencia': conf,
            'divergencias': divergencias,
            'status': status,
        })

    totais = {
        'esperado': len(chassis_nf),
        'conferido': len(confs_ativas),
        'ok': ok,
        'com_divergencia': com_divergencia,
        'avarias': avarias,
        'extras': extras,
        'faltantes': faltantes,
        'qtd_declarada': rec.qtd_declarada or 0,
    }
    return {'linhas': linhas, 'totais': totais}


# ========================================================================
# Listagem (mantida)
# ========================================================================

def listar_recebimentos(
    loja_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    lojas_permitidas_ids=None,
) -> List[HoraRecebimento]:
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


def chassis_esperados_mas_nao_conferidos(recebimento_id: int) -> List[str]:
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        return []
    chassis_nf = {i.numero_chassi for i in rec.nf.itens}
    chassis_conf = {c.numero_chassi for c in rec.conferencias if not c.substituida}
    return sorted(chassis_nf - chassis_conf)


def chassis_conferidos_nao_na_nf(recebimento_id: int) -> List[str]:
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        return []
    chassis_nf = {i.numero_chassi for i in rec.nf.itens}
    chassis_conf = {c.numero_chassi for c in rec.conferencias if not c.substituida}
    return sorted(chassis_conf - chassis_nf)


# ========================================================================
# Privados
# ========================================================================

def _garantir_moto(chassi: str, item_nf: Optional[HoraNfEntradaItem], operador: Optional[str]):
    """Cria HoraMoto minima se nao existe (FK para conferencia)."""
    if HoraMoto.query.get(chassi):
        return
    from app.hora.services.moto_service import get_or_create_moto
    if item_nf:
        get_or_create_moto(
            numero_chassi=chassi,
            modelo_nome=(item_nf.modelo_texto_original or 'DESCONHECIDO').strip() or 'DESCONHECIDO',
            cor=(item_nf.cor_texto_original or 'NAO_INFORMADA').strip().upper() or 'NAO_INFORMADA',
            criado_por=operador,
        )
    else:
        get_or_create_moto(
            numero_chassi=chassi,
            modelo_nome='CHASSI_EXTRA_DESCONHECIDO',
            cor='NAO_INFORMADA',
            criado_por=operador,
        )


def _redefinir_divergencias(conf: HoraRecebimentoConferencia, rec: HoraRecebimento):
    """Recalcula 1-N divergencias da conferencia vs NF."""
    # Remove divergencias existentes (recria tudo a partir do estado atual)
    for d in list(conf.divergencias):
        db.session.delete(d)
    db.session.flush()

    item_nf = HoraNfEntradaItem.query.filter_by(
        nf_id=rec.nf_id, numero_chassi=conf.numero_chassi,
    ).first()

    # Mantem o snapshot tipo_divergencia (compat) = prioridade: CHASSI_EXTRA > modelo/cor > avaria
    snapshot = None

    if not item_nf:
        db.session.add(HoraConferenciaDivergencia(
            conferencia_id=conf.id,
            tipo='CHASSI_EXTRA',
            detalhe='Chassi nao esta na NF',
        ))
        snapshot = 'CHASSI_EXTRA'
    else:
        modelo_nf = _normalizar_modelo_nome(item_nf.modelo_texto_original)
        modelo_conf_nome = None
        if conf.modelo_id_conferido:
            m = HoraModelo.query.get(conf.modelo_id_conferido)
            if m:
                modelo_conf_nome = _normalizar_modelo_nome(m.nome_modelo)
        if modelo_nf and modelo_conf_nome and modelo_nf != modelo_conf_nome:
            db.session.add(HoraConferenciaDivergencia(
                conferencia_id=conf.id,
                tipo='MODELO_DIFERENTE',
                valor_esperado=item_nf.modelo_texto_original,
                valor_conferido=modelo_conf_nome,
            ))
            snapshot = snapshot or 'MODELO_DIFERENTE'

        cor_nf = _normalizar_cor(item_nf.cor_texto_original)
        cor_conf = _normalizar_cor(conf.cor_conferida)
        if cor_nf and cor_conf and cor_nf != cor_conf:
            db.session.add(HoraConferenciaDivergencia(
                conferencia_id=conf.id,
                tipo='COR_DIFERENTE',
                valor_esperado=item_nf.cor_texto_original,
                valor_conferido=cor_conf,
            ))
            snapshot = snapshot or 'COR_DIFERENTE'

    if conf.avaria_fisica:
        db.session.add(HoraConferenciaDivergencia(
            conferencia_id=conf.id,
            tipo='AVARIA_FISICA',
            detalhe='Marcado pelo operador no wizard',
        ))
        snapshot = snapshot or 'AVARIA_FISICA'

    conf.tipo_divergencia = snapshot
    conf.detalhe_divergencia = None
    db.session.flush()


def _divergencia_legado(conf: HoraRecebimentoConferencia):
    """Adapta conferencias legado (sem divergencias 1-N) para exibicao uniforme."""
    return type('LegadoDiv', (), {
        'tipo': conf.tipo_divergencia,
        'detalhe': conf.detalhe_divergencia,
        'valor_esperado': None,
        'valor_conferido': None,
    })()


def _audita_update(conf: HoraRecebimentoConferencia, novos: dict, usuario, recebimento_id):
    """Compara valores atuais vs novos e grava auditoria por campo alterado."""
    for campo, novo in novos.items():
        antes = getattr(conf, campo)
        if antes != novo:
            recebimento_audit.registrar(
                recebimento_id=recebimento_id,
                conferencia_id=conf.id,
                acao='AJUSTOU_CAMPO',
                usuario=usuario,
                campo_alterado=campo,
                valor_antes=antes,
                valor_depois=novo,
                flush=False,
            )
            setattr(conf, campo, novo)
    db.session.flush()
