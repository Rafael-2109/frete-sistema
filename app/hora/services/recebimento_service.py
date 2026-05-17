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

from sqlalchemy import func as sa_func
from sqlalchemy.orm import selectinload

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
    from app.hora.services.modelo_resolver_service import resolver_modelo
    from app.hora.models import ALIAS_TIPO_NOME_NF

    chassi_norm = (numero_chassi or '').strip().upper()
    resultado = {
        'chassi': chassi_norm,
        'na_nf': False,
        'no_pedido': None,
        'ja_conferido': False,
        'conferencia_ativa_id': None,
        'moto_existe': False,
        'modelo_esperado': None,
        'modelo_id_esperado': None,
        'modelo_canonico_esperado': None,
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
        # `modelo_esperado` (texto bruto) preservado para retrocompat / auditoria.
        resultado['modelo_esperado'] = item_nf.modelo_texto_original
        resultado['cor_esperada'] = item_nf.cor_texto_original
        # Resolve canonico para que a UI selecione pelo id (nao por texto).
        # Prioridade: HoraMoto.modelo (FK ja segue _seguir_canonico apos
        # _aplicar_correcao_moto_se_divergir); fallback para resolver_modelo
        # do texto NF (alias NOME_NF, depois qualquer tipo).
        modelo_canonico = None
        moto_existente = HoraMoto.query.get(chassi_norm)
        if moto_existente and moto_existente.modelo:
            modelo_canonico = moto_existente.modelo
        elif item_nf.modelo_texto_original:
            modelo_canonico = (
                resolver_modelo(item_nf.modelo_texto_original, tipo=ALIAS_TIPO_NOME_NF)
                or resolver_modelo(item_nf.modelo_texto_original)
            )
        if modelo_canonico is not None:
            resultado['modelo_id_esperado'] = modelo_canonico.id
            resultado['modelo_canonico_esperado'] = modelo_canonico.nome_modelo

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

    # modelos_sugeridos: lista nomes CANONICOS para casar com o select do
    # wizard (que so contem canonicos). Resolve cada texto livre da NF e
    # cada modelo_id de pedido para o canonico correspondente.
    modelos_canonicos: dict[int, str] = {}
    cores: set[str] = set()
    for i in rec.nf.itens:
        if i.modelo_texto_original:
            mc = (
                resolver_modelo(i.modelo_texto_original, tipo=ALIAS_TIPO_NOME_NF)
                or resolver_modelo(i.modelo_texto_original)
            )
            if mc is not None:
                modelos_canonicos[mc.id] = mc.nome_modelo
        if i.cor_texto_original:
            cores.add(i.cor_texto_original.strip().upper())
    if rec.nf.pedido_id and rec.nf.pedido:
        for pi in rec.nf.pedido.itens:
            if pi.modelo and pi.modelo.nome_modelo:
                modelos_canonicos[pi.modelo.id] = pi.modelo.nome_modelo
            if pi.cor:
                cores.add(pi.cor.strip().upper())
    resultado['modelos_sugeridos'] = sorted(modelos_canonicos.values())
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

    # Recebimento e SOT (regra de negocio confirmada 2026-05-06): se a
    # conferencia divergir de cor/modelo da NF, atualiza hora_moto.cor e
    # hora_moto.modelo_id para os valores conferidos. Excecao controlada a
    # invariante 3 (insert-once) — mesmo precedente de retroatividade de
    # modelo sentinela em hora_29. Documentado em docs/hora/INVARIANTES.md.
    _aplicar_correcao_moto_se_divergir(conf)

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

    Descarta conferencias parciais (confirmado_em IS NULL) antes de calcular
    faltantes — decisao 2026-05-07 do dono do modulo: "abandonada pela metade
    -> descartar". Conferencia abandonada nao deve bloquear o chassi de virar
    MOTO_FALTANDO se ele estiver na NF.
    """
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        raise ValueError(f"Recebimento {recebimento_id} nao encontrado")

    # 1. Descartar conferencias parciais (operador abandonou wizard).
    parciais = [
        c for c in rec.conferencias
        if not c.substituida and c.confirmado_em is None
    ]
    for parcial in parciais:
        # Limpa substituida_por_id de antecessoras para nao violar FK ao
        # deletar a parcial. Antecessoras (substituida=true) preservam o
        # historico de reconferencias mas perdem o link para a parcial.
        HoraRecebimentoConferencia.query.filter_by(
            substituida_por_id=parcial.id
        ).update({'substituida_por_id': None}, synchronize_session=False)
        recebimento_audit.registrar(
            recebimento_id=rec.id,
            conferencia_id=None,  # parcial sera deletada — FK invalida
            acao='DESCARTOU_PARCIAL',
            usuario=operador,
            detalhe=(
                f'ordem={parcial.ordem} chassi={parcial.numero_chassi} '
                f'(abandonada — confirmado_em IS NULL)'
            ),
        )
        db.session.delete(parcial)
    if parciais:
        db.session.flush()
        db.session.expire(rec, ['conferencias'])

    chassis_nf = {i.numero_chassi for i in rec.nf.itens}
    chassis_conferidos_ativos = {
        c.numero_chassi for c in rec.conferencias if not c.substituida
    }
    faltantes = sorted(chassis_nf - chassis_conferidos_ativos)

    # Garantir que cada chassi faltante vire uma conferencia MOTO_FALTANDO.
    if faltantes:
        agora = agora_utc_naive()
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
                # Marca a conferencia como confirmada (decisao 2026-05-06)
                # para distinguir "MOTO_FALTANDO consolidado no fechamento"
                # de "conferencia pendente no wizard" (confirmado_em IS NULL).
                confirmado_em=agora,
            )
            db.session.add(conf)
            db.session.flush()
            # Divergencia 1-N
            db.session.add(HoraConferenciaDivergencia(
                conferencia_id=conf.id,
                tipo='MOTO_FALTANDO',
                detalhe='Faltante no fechamento',
            ))
            # Evento dedicado (categoria EVENTOS_FALTANDO_FISICAMENTE em
            # estoque_service). NAO usar 'CONFERIDA' — esse tipo esta em
            # EVENTOS_EM_ESTOQUE e fazia a moto ressuscitar no estoque.
            registrar_evento(
                numero_chassi=chassi,
                tipo='MOTO_FALTANDO',
                origem_tabela='hora_recebimento_conferencia',
                origem_id=conf.id,
                loja_id=rec.loja_id,
                operador=operador,
                detalhe='Faltante no fechamento (batch)',
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
# Reprocessamento pos-edicao de chassi em item de NF (2026-05-16)
# ========================================================================

def reprocessar_recebimentos_para_nf(
    nf_id: int,
    chassi_antigo: Optional[str],
    chassi_novo: str,
    operador: Optional[str] = None,
) -> dict:
    """Reavalia recebimentos vinculados a uma NF apos edicao do chassi de um
    item da NF (chassi_antigo -> chassi_novo).

    Use case: NF tinha chassi "1", operador conferiu fisicamente o chassi "2"
    (registrado como CHASSI_EXTRA). Apos finalizar, o sistema criou conferencia
    batch sintetica para "1" com MOTO_FALTANDO. Operador percebe o engano e
    corrige a NF (chassi "1" -> "2"). Esta funcao reflete a nova realidade
    nos recebimentos ja finalizados:

      - Conferencia ATIVA de `chassi_antigo`:
        * Se for batch sintetica MOTO_FALTANDO (criada por finalizar_recebimento
          sem nenhum dado real conferido pelo operador): DELETA conferencia,
          divergencias 1-N e evento hora_moto_evento(MOTO_FALTANDO) associado.
          O chassi nao esta mais na NF entao a marcacao "faltante" perde sentido.
        * Se for conferencia REAL (operador escaneou e completou wizard): mantem
          a linha e recalcula divergencias 1-N (chassi nao esta mais na NF =>
          vira CHASSI_EXTRA).

      - Conferencia ATIVA de `chassi_novo`:
        * Se existe: recalcula divergencias 1-N. Deixa de ser CHASSI_EXTRA porque
          agora esta na NF; pode passar a OK ou ter divergencia de MODELO/COR.
        * Se NAO existe E o recebimento ja foi finalizado: cria conferencia
          batch sintetica MOTO_FALTANDO para `chassi_novo` (mesmo padrao do
          finalizar_recebimento), pois agora ele esta declarado na NF mas nao
          foi conferido.

      - Recalcula `status` apenas para recebimentos finalizados
        (CONCLUIDO/COM_DIVERGENCIA). Recebimentos em AGUARDANDO_QTD ou
        EM_CONFERENCIA mantem status — operador ainda finalizara via wizard.

    Idempotente: chamar 2x produz o mesmo estado final.

    Args:
        nf_id: id de HoraNfEntrada.
        chassi_antigo: chassi anterior do item NF (pode ser None se nao
            houve troca real, p.ex. correcao so de motor — neste caso a
            funcao e no-op em relacao a divergencias por chassi).
        chassi_novo: chassi atual do item NF (obrigatorio, normalizado UPPER).
        operador: rotulo do operador para auditoria.

    Returns:
        dict com estatisticas:
          - recebimentos_processados, recebimentos_afetados
          - confs_batch_removidas, eventos_removidos
          - confs_batch_criadas
          - confs_reavaliadas
          - status_changes: [{recebimento_id, antes, depois}]
    """
    if chassi_antigo is not None:
        chassi_antigo = (chassi_antigo or '').strip().upper() or None
    chassi_novo = (chassi_novo or '').strip().upper()
    if not chassi_novo:
        raise ValueError('chassi_novo obrigatorio.')

    resultado = {
        'nf_id': nf_id,
        'chassi_antigo': chassi_antigo,
        'chassi_novo': chassi_novo,
        'recebimentos_processados': 0,
        'recebimentos_afetados': 0,
        'confs_batch_removidas': 0,
        'eventos_removidos': 0,
        'confs_batch_criadas': 0,
        'confs_reavaliadas': 0,
        'status_changes': [],
    }

    # Short-circuit: edicao sem troca real de chassi (so motor, p.ex.).
    if chassi_antigo is None or chassi_antigo == chassi_novo:
        return resultado

    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')

    recebimentos = HoraRecebimento.query.filter_by(nf_id=nf.id).all()
    if not recebimentos:
        return resultado

    chassis_nf_atual = {i.numero_chassi for i in nf.itens}

    for rec in recebimentos:
        resultado['recebimentos_processados'] += 1
        status_antes = rec.status
        afetou = False

        # ----------------------------------------------------------------
        # 1) Conferencia ATIVA do chassi ANTIGO
        # ----------------------------------------------------------------
        conf_antigo = (
            HoraRecebimentoConferencia.query
            .filter_by(
                recebimento_id=rec.id,
                numero_chassi=chassi_antigo,
                substituida=False,
            )
            .first()
        )
        if conf_antigo is not None:
            if _eh_conferencia_batch_faltante(conf_antigo):
                # Batch sintetica -> seguro deletar (chassi nao esta mais na NF).
                eventos_del = _deletar_conferencia_batch_faltante(conf_antigo)
                resultado['confs_batch_removidas'] += 1
                resultado['eventos_removidos'] += eventos_del
                afetou = True
                recebimento_audit.registrar(
                    recebimento_id=rec.id,
                    conferencia_id=None,
                    acao='REPROCESSOU_POS_EDICAO_NF',
                    usuario=operador,
                    detalhe=(
                        f'Removida conferencia batch MOTO_FALTANDO de chassi '
                        f'{chassi_antigo} (chassi nao consta mais na NF apos edicao '
                        f'{chassi_antigo} -> {chassi_novo}). Eventos removidos: '
                        f'{eventos_del}.'
                    ),
                )
            else:
                # Conferencia REAL: mantem, mas reavalia (X agora vira CHASSI_EXTRA).
                _redefinir_divergencias(conf_antigo, rec)
                resultado['confs_reavaliadas'] += 1
                afetou = True
                recebimento_audit.registrar(
                    recebimento_id=rec.id,
                    conferencia_id=conf_antigo.id,
                    acao='REPROCESSOU_POS_EDICAO_NF',
                    usuario=operador,
                    detalhe=(
                        f'Reavaliada conferencia REAL de chassi {chassi_antigo} '
                        f'apos edicao NF ({chassi_antigo} -> {chassi_novo}).'
                    ),
                )

        # ----------------------------------------------------------------
        # 2) Conferencia ATIVA do chassi NOVO
        # ----------------------------------------------------------------
        conf_novo = (
            HoraRecebimentoConferencia.query
            .filter_by(
                recebimento_id=rec.id,
                numero_chassi=chassi_novo,
                substituida=False,
            )
            .first()
        )
        if conf_novo is not None:
            # Reavalia (deixa de ser CHASSI_EXTRA porque agora esta na NF).
            _redefinir_divergencias(conf_novo, rec)
            resultado['confs_reavaliadas'] += 1
            afetou = True
            recebimento_audit.registrar(
                recebimento_id=rec.id,
                conferencia_id=conf_novo.id,
                acao='REPROCESSOU_POS_EDICAO_NF',
                usuario=operador,
                detalhe=(
                    f'Reavaliada conferencia de chassi {chassi_novo} apos edicao '
                    f'NF ({chassi_antigo} -> {chassi_novo}). Esperado: deixa de '
                    f'ser CHASSI_EXTRA.'
                ),
            )
        elif rec.status in ('CONCLUIDO', 'COM_DIVERGENCIA') and chassi_novo in chassis_nf_atual:
            # Recebimento finalizado + chassi novo agora na NF mas sem conferencia
            # = novo MOTO_FALTANDO sintetico (mesmo padrao de finalizar_recebimento).
            _criar_conferencia_batch_faltante(rec, chassi_novo, operador)
            resultado['confs_batch_criadas'] += 1
            afetou = True
            recebimento_audit.registrar(
                recebimento_id=rec.id,
                conferencia_id=None,
                acao='REPROCESSOU_POS_EDICAO_NF',
                usuario=operador,
                detalhe=(
                    f'Criada conferencia batch MOTO_FALTANDO para chassi {chassi_novo} '
                    f'(agora declarado na NF apos edicao {chassi_antigo} -> '
                    f'{chassi_novo}, sem conferencia fisica).'
                ),
            )

        # ----------------------------------------------------------------
        # 3) Recalcula status para recebimentos finalizados
        # ----------------------------------------------------------------
        if afetou and rec.status in ('CONCLUIDO', 'COM_DIVERGENCIA'):
            db.session.flush()
            # _recalcular_status_recebimento_finalizado faz expire(rec, ['conferencias'])
            # e expire(conf, ['divergencias']) internamente.
            _recalcular_status_recebimento_finalizado(rec)
            if rec.status != status_antes:
                resultado['status_changes'].append({
                    'recebimento_id': rec.id,
                    'antes': status_antes,
                    'depois': rec.status,
                })
                recebimento_audit.registrar(
                    recebimento_id=rec.id,
                    acao='REPROCESSOU_POS_EDICAO_NF',
                    usuario=operador,
                    detalhe=f'Status: {status_antes} -> {rec.status}',
                )

        if afetou:
            resultado['recebimentos_afetados'] += 1

    db.session.commit()
    return resultado


def _eh_conferencia_batch_faltante(conf: HoraRecebimentoConferencia) -> bool:
    """Detecta se uma conferencia foi criada como batch sintetica de
    MOTO_FALTANDO por `finalizar_recebimento`, sem nenhum dado real conferido.

    Sinais (TODOS verdadeiros):
      - tipo_divergencia == 'MOTO_FALTANDO' OU possui divergencia 1-N MOTO_FALTANDO
      - modelo_id_conferido IS NULL
      - cor_conferida IS NULL
      - foto_s3_key IS NULL
      - qr_code_lido == False
      - avaria_fisica == False

    Se algum campo "real" foi setado, a linha NAO eh batch sintetica — eh
    conferencia que o operador iniciou (possivelmente reconferida ou ajustada)
    e nao pode ser deletada sem perder evidencia.
    """
    tem_faltante = bool(
        conf.tipo_divergencia == 'MOTO_FALTANDO'
        or any(d.tipo == 'MOTO_FALTANDO' for d in conf.divergencias)
    )
    if not tem_faltante:
        return False
    return (
        conf.modelo_id_conferido is None
        and conf.cor_conferida is None
        and conf.foto_s3_key is None
        and not conf.qr_code_lido
        and not conf.avaria_fisica
    )


def _deletar_conferencia_batch_faltante(conf: HoraRecebimentoConferencia) -> int:
    """Deleta uma conferencia batch sintetica + divergencias 1-N (cascade) +
    evento hora_moto_evento(MOTO_FALTANDO) associado.

    Retorna a quantidade de eventos `MOTO_FALTANDO` deletados (esperado: 1).

    NAO toca em hora_moto (a moto pode estar referenciada em outras tabelas;
    a limpeza de orfas eh feita pelo caller via `_limpar_motos_orfas`).
    """
    from app.hora.models import HoraMotoEvento

    eventos_del = (
        HoraMotoEvento.query
        .filter(HoraMotoEvento.origem_tabela == 'hora_recebimento_conferencia')
        .filter(HoraMotoEvento.origem_id == conf.id)
        .filter(HoraMotoEvento.tipo == 'MOTO_FALTANDO')
        .delete(synchronize_session=False)
    )
    # Limpa substituida_por_id de antecessoras (FK seguro).
    HoraRecebimentoConferencia.query.filter_by(
        substituida_por_id=conf.id
    ).update({'substituida_por_id': None}, synchronize_session=False)
    db.session.delete(conf)
    db.session.flush()
    return eventos_del or 0


def _criar_conferencia_batch_faltante(
    rec: HoraRecebimento,
    chassi: str,
    operador: Optional[str],
) -> HoraRecebimentoConferencia:
    """Cria conferencia batch sintetica MOTO_FALTANDO para um chassi.

    Mesma logica do `finalizar_recebimento` (linhas 511-550):
      - HoraRecebimentoConferencia com tipo_divergencia=MOTO_FALTANDO,
        confirmado_em=now, sem dados reais.
      - HoraConferenciaDivergencia(tipo=MOTO_FALTANDO).
      - HoraMotoEvento(tipo=MOTO_FALTANDO).
    """
    _garantir_moto(chassi, None, operador)
    ordem = proxima_ordem(rec.id)
    agora = agora_utc_naive()
    conf = HoraRecebimentoConferencia(
        recebimento_id=rec.id,
        numero_chassi=chassi,
        ordem=ordem,
        qr_code_lido=False,
        avaria_fisica=False,
        tipo_divergencia='MOTO_FALTANDO',
        detalhe_divergencia='Faltante apos edicao NF',
        operador=operador,
        confirmado_em=agora,
    )
    db.session.add(conf)
    db.session.flush()
    db.session.add(HoraConferenciaDivergencia(
        conferencia_id=conf.id,
        tipo='MOTO_FALTANDO',
        detalhe='Faltante apos edicao NF',
    ))
    registrar_evento(
        numero_chassi=chassi,
        tipo='MOTO_FALTANDO',
        origem_tabela='hora_recebimento_conferencia',
        origem_id=conf.id,
        loja_id=rec.loja_id,
        operador=operador,
        detalhe='Faltante apos edicao NF (batch reprocessamento)',
    )
    return conf


def metricas_recebimento(rec: HoraRecebimento) -> dict:
    """Computa metricas amigaveis para exibicao do recebimento (UI).

    Substitui a leitura confusa "conferidas/NF" — onde "conferidas" somava
    MOTO_FALTANDO sintetico (chassis declarados na NF mas nao escaneados) com
    CHASSI_EXTRA (escaneados mas nao na NF) — por:

      - qtd_nf: chassis declarados na NF (motos; pecas ficam separadas).
      - qtd_recebidas: conferencias REAIS confirmadas (operador escaneou e
        confirmou no wizard). EXCLUI batch sintetico MOTO_FALTANDO criado pelo
        finalizar_recebimento. INCLUI CHASSI_EXTRA (foi recebido fisicamente,
        ainda que nao esteja na NF).
      - qtd_divergencias: chassis com qualquer divergencia ativa
        (MOTO_FALTANDO + CHASSI_EXTRA + MODELO_DIFERENTE + COR_DIFERENTE +
        AVARIA_FISICA).
      - qtd_faltando: subset — chassis declarados na NF mas nao recebidos
        (batch MOTO_FALTANDO).
      - qtd_extra: subset — chassis recebidos sem estar na NF (CHASSI_EXTRA).
      - qtd_ok: chassis recebidos e sem divergencias (qtd_recebidas - extras
        com divergencia - recebidos com modelo/cor/avaria divergente).

    Considera apenas conferencias ATIVAS (substituida=False).
    """
    confs_ativas = [c for c in rec.conferencias if not c.substituida]
    qtd_nf = sum(1 for _ in rec.nf.itens) if rec.nf else 0
    qtd_faltando = 0
    qtd_extra = 0
    qtd_recebidas = 0
    qtd_divergencias = 0
    qtd_ok = 0
    for c in confs_ativas:
        eh_batch = _eh_conferencia_batch_faltante(c)
        tem_divergencia = bool(c.divergencias) or bool(c.tipo_divergencia)
        # Recebidas: conferencia REAL (operador escaneou).
        if not eh_batch:
            qtd_recebidas += 1
        # Faltando vs Extra (categorias mutuamente exclusivas)
        if eh_batch:
            qtd_faltando += 1
        else:
            # Detecta CHASSI_EXTRA por divergencia 1-N OU snapshot
            tem_extra = (
                c.tipo_divergencia == 'CHASSI_EXTRA'
                or any(d.tipo == 'CHASSI_EXTRA' for d in c.divergencias)
            )
            if tem_extra:
                qtd_extra += 1
        if tem_divergencia:
            qtd_divergencias += 1
        elif not eh_batch:
            qtd_ok += 1
    return {
        'qtd_nf': qtd_nf,
        'qtd_recebidas': qtd_recebidas,
        'qtd_divergencias': qtd_divergencias,
        'qtd_faltando': qtd_faltando,
        'qtd_extra': qtd_extra,
        'qtd_ok': qtd_ok,
    }


def _recalcular_status_recebimento_finalizado(rec: HoraRecebimento) -> None:
    """Recalcula `status` de um recebimento ja finalizado (CONCLUIDO ou
    COM_DIVERGENCIA) apos modificacao nas conferencias.

    Mesma logica de `finalizar_recebimento` linhas 555-562. Usa apenas
    conferencias ATIVAS (nao substituidas) confirmadas.

    Expira o cache ORM de `conferencias` e `divergencias` para garantir leitura
    fresca do DB (sem isso, `_redefinir_divergencias` que deletou e recriou
    divergencias 1-N nao reflete via `c.divergencias` cached).
    """
    if rec.status not in ('CONCLUIDO', 'COM_DIVERGENCIA'):
        return
    db.session.expire(rec, ['conferencias'])
    confs_ativas = [c for c in rec.conferencias if not c.substituida]
    for c in confs_ativas:
        db.session.expire(c, ['divergencias'])
    houve_divergencia = any(
        c.divergencias or c.tipo_divergencia for c in confs_ativas
    )
    rec.status = 'COM_DIVERGENCIA' if houve_divergencia else 'CONCLUIDO'


# ========================================================================
# Comparativo lado-a-lado (tela T4)
# ========================================================================

def comparativo_recebimento_nf(
    recebimento_id: int,
    apenas_conferidas: bool = False,
) -> dict:
    """Produz dict para a tela de resumo lado-a-lado.

    {
      'linhas': [ {chassi, nf_item, conferencia, divergencias, status, avaria} ],
      'totais': {esperado, conferido, ok, com_divergencia, avarias, extras, faltantes}
    }

    Parametros:
      apenas_conferidas: se True, filtra as linhas e devolve somente chassis
        com conferencia ATIVA (substituida=False). Usado para o conferente
        "cego" enxergar o resumo do proprio trabalho SEM ver motos da NF que
        ele ainda nao conferiu (evita "colar" da NF).
    """
    rec = HoraRecebimento.query.get_or_404(recebimento_id)

    # Chassis conhecidos: da NF + da conferencia ativa
    chassis_nf = [i.numero_chassi for i in rec.nf.itens if i.numero_chassi]
    # Conferencia parcial (confirmado_em IS NULL) NAO conta como conferida:
    # operador abandonou o wizard sem completar (passos B, C, D). Decisao
    # 2026-05-07 do dono do modulo: "abandonada pela metade -> descartar".
    # Sem esse filtro, parciais caiam em status='OK' (badge "bate") por nao
    # terem divergencias derivadas (que so sao calculadas em
    # registrar_conferencia_cega -> _redefinir_divergencias).
    confs_ativas = [
        c for c in rec.conferencias
        if not c.substituida and c.confirmado_em is not None
    ]
    chassis_conf = [c.numero_chassi for c in confs_ativas]

    todos = []
    seen = set()
    if apenas_conferidas:
        # So as que passaram pela conferencia (nao vaza chassis so-NF)
        for c in chassis_conf:
            if c not in seen:
                todos.append(c)
                seen.add(c)
    else:
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

    # Em modo `apenas_conferidas` (conferente "cego"), o denominador publico
    # deve refletir APENAS o que o operador vai ver — senao vazamos a qtd
    # da NF via `esperado`, e `faltantes` ainda exporia motos pendentes.
    if apenas_conferidas:
        esperado_exposto = len(confs_ativas)
        faltantes_exposto = 0
    else:
        esperado_exposto = len(chassis_nf)
        faltantes_exposto = faltantes

    totais = {
        'esperado': esperado_exposto,
        'conferido': len(confs_ativas),
        'ok': ok,
        'com_divergencia': com_divergencia,
        'avarias': avarias,
        'extras': extras,
        'faltantes': faltantes_exposto,
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
    *,
    numero_nf: Optional[str] = None,
    data_inicio=None,
    data_fim=None,
) -> List[HoraRecebimento]:
    # selectinload em conferencias, divergencias e nf.itens: o template
    # `recebimentos_lista` chama `metricas_recebimento` para cada linha, que
    # itera `conferencias`, `conferencia.divergencias` e `nf.itens`. Sem
    # eager-load vira N+1 (centenas de queries extras).
    query = HoraRecebimento.query.options(
        selectinload(HoraRecebimento.conferencias)
            .selectinload(HoraRecebimentoConferencia.divergencias),
        selectinload(HoraRecebimento.nf).selectinload(HoraNfEntrada.itens),
    ).order_by(
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
    if numero_nf:
        query = (
            query.join(HoraRecebimento.nf)
            .filter(HoraNfEntrada.numero_nf.ilike(f'%{numero_nf.strip()}%'))
        )
    if data_inicio:
        query = query.filter(HoraRecebimento.data_recebimento >= data_inicio)
    if data_fim:
        query = query.filter(HoraRecebimento.data_recebimento <= data_fim)
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
# Recebimento automatico de NF inteira (Item 1 — 2026-05-16)
# ========================================================================

def listar_nfs_para_recebimento_automatico(
    lojas_permitidas_ids: Optional[List[int]] = None,
    *,
    limit: int = 100,
) -> List[dict]:
    """Lista NFs SEM recebimento + agregados para o modal admin.

    Filtros:
      - nf.loja_destino_id NOT NULL (sem loja nao da pra criar recebimento).
      - sem `hora_recebimento` para esta NF (LEFT JOIN com NULL).
      - se `lojas_permitidas_ids` passado: restringe a essas lojas.

    Retorna lista de dicts ordenada por data_emissao DESC com:
      {
        nf_id, numero_nf, data_emissao, cnpj_emitente, nome_emitente,
        loja_id, loja_nome,
        pedido_id, pedido_numero,
        qtd_motos_nf, qtd_motos_pedido_motos_only, qtd_motos_pedido_ja_faturadas,
        chassis: [{numero_chassi, modelo_canonico_nome, cor}, ...]
      }
    """
    from app.hora.models import HoraPedido, HoraPedidoItem
    from app.hora.services.modelo_resolver_service import resolver_modelo
    from app.hora.models import ALIAS_TIPO_NOME_NF

    q = (
        HoraNfEntrada.query
        .options(
            selectinload(HoraNfEntrada.itens),
            selectinload(HoraNfEntrada.loja_destino),
        )
        .filter(HoraNfEntrada.loja_destino_id.isnot(None))
        .filter(~HoraNfEntrada.recebimentos.any())
        .order_by(HoraNfEntrada.data_emissao.desc(), HoraNfEntrada.id.desc())
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraNfEntrada.loja_destino_id.in_(list(lojas_permitidas_ids)))

    nfs = q.limit(limit).all()
    if not nfs:
        return []

    # Pre-carrega pedidos e contagens
    pedido_ids = [nf.pedido_id for nf in nfs if nf.pedido_id]
    pedido_por_id = {}
    pedidos_qtd_motos = {}
    pedidos_chassis_faturados = {}
    if pedido_ids:
        for p in HoraPedido.query.filter(HoraPedido.id.in_(pedido_ids)).all():
            pedido_por_id[p.id] = p
        # Qtd de itens motos (peca_id IS NULL) por pedido
        rows_qtd = (
            db.session.query(
                HoraPedidoItem.pedido_id,
                sa_func.count(HoraPedidoItem.id),
            )
            .filter(HoraPedidoItem.pedido_id.in_(pedido_ids))
            .filter(HoraPedidoItem.peca_id.is_(None))
            .group_by(HoraPedidoItem.pedido_id)
            .all()
        )
        pedidos_qtd_motos = {pid: cnt for pid, cnt in rows_qtd}
        # Chassis ja faturados em qualquer NF do mesmo pedido
        rows_fat = (
            db.session.query(
                HoraNfEntrada.pedido_id,
                HoraNfEntradaItem.numero_chassi,
            )
            .join(HoraNfEntradaItem, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
            .filter(HoraNfEntrada.pedido_id.in_(pedido_ids))
            .all()
        )
        for pid, chassi in rows_fat:
            pedidos_chassis_faturados.setdefault(pid, set()).add(chassi)

    saida = []
    for nf in nfs:
        chassis = []
        for it in nf.itens:
            canonico_nome = None
            if it.modelo_texto_original:
                mc = (
                    resolver_modelo(it.modelo_texto_original, tipo=ALIAS_TIPO_NOME_NF)
                    or resolver_modelo(it.modelo_texto_original)
                )
                if mc:
                    canonico_nome = mc.nome_modelo
            chassis.append({
                'numero_chassi': it.numero_chassi,
                'modelo_canonico': canonico_nome,
                'modelo_texto_nf': it.modelo_texto_original,
                'cor': it.cor_texto_original,
            })
        pedido = pedido_por_id.get(nf.pedido_id) if nf.pedido_id else None
        qtd_motos_pedido = pedidos_qtd_motos.get(nf.pedido_id, 0) if nf.pedido_id else 0
        qtd_motos_pedido_ja_faturadas = len(
            pedidos_chassis_faturados.get(nf.pedido_id, set())
        ) if nf.pedido_id else 0
        saida.append({
            'nf_id': nf.id,
            'numero_nf': nf.numero_nf,
            'data_emissao': nf.data_emissao.isoformat() if nf.data_emissao else None,
            'cnpj_emitente': nf.cnpj_emitente,
            'nome_emitente': nf.nome_emitente,
            'loja_id': nf.loja_destino_id,
            'loja_nome': nf.loja_destino.nome.strip() if nf.loja_destino else None,
            'pedido_id': nf.pedido_id,
            'pedido_numero': pedido.numero_pedido if pedido else None,
            'qtd_motos_nf': len(nf.itens),
            'qtd_motos_pedido': qtd_motos_pedido,
            'qtd_motos_pedido_ja_faturadas': qtd_motos_pedido_ja_faturadas,
            'chassis': chassis,
        })
    return saida


def criar_recebimento_automatico_da_nf(
    nf_id: int,
    operador: Optional[str] = None,
) -> dict:
    """Cria recebimento + conferencias confirmadas com dados da NF.

    Equivale a um operador rodando o wizard de A-D para CADA chassi da NF
    confirmando o que esta declarado. Diferenca: ao inves de scan manual,
    usa dados da NF (chassi, modelo via resolver canonico, cor).

    Eh DESTINADO ao admin que recebe NF "no papel" sem conferencia fisica
    real (ex.: lojas que recebem motos antes de cadastrar no sistema).

    Fluxo:
      1. Valida NF: existe, loja_destino_id presente, sem recebimento aberto.
      2. iniciar_recebimento -> AGUARDANDO_QTD
      3. definir_qtd_declarada(qtd = len(nf.itens)) -> EM_CONFERENCIA
      4. Para cada item NF:
         a. resolve modelo canonico (None se nao resolver)
         b. registra conferencia confirmada via registrar_conferencia_cega
            (reusa toda a logica: _redefinir_divergencias, _aplicar_correcao_moto,
             registrar_evento RECEBIDA, auditoria CONFERIU_MOTO).
      5. finalizar_recebimento -> CONCLUIDO ou COM_DIVERGENCIA.
      6. Auditoria adicional RECEBIMENTO_AUTOMATICO no header.

    Retorna dict com totais.
    """
    from app.hora.services.modelo_resolver_service import resolver_modelo
    from app.hora.models import ALIAS_TIPO_NOME_NF

    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')
    if not nf.loja_destino_id:
        raise ValueError(
            f'NF {nf.numero_nf} (#{nf.id}) sem loja_destino_id. '
            f'Preencha a loja antes de criar recebimento automatico.'
        )
    if not nf.itens:
        raise ValueError(f'NF {nf.numero_nf} sem itens.')

    rec_existente = HoraRecebimento.query.filter_by(
        nf_id=nf.id, loja_id=nf.loja_destino_id,
    ).first()
    if rec_existente:
        raise ValueError(
            f'Ja existe recebimento #{rec_existente.id} para NF {nf.numero_nf} '
            f'(status={rec_existente.status}). Exclua o existente antes.'
        )

    # 1. Inicia (faz commit interno)
    rec = iniciar_recebimento(
        nf_id=nf.id, loja_id=nf.loja_destino_id, operador=operador,
    )

    # 2. Define qtd_declarada (faz commit interno)
    qtd_nf = len(nf.itens)
    definir_qtd_declarada(recebimento_id=rec.id, qtd=qtd_nf, usuario=operador)

    # 3. Registra cada conferencia (cada call faz commit interno)
    conf_ids: List[int] = []
    chassis_sem_modelo_canonico: List[str] = []
    for ordem, item in enumerate(nf.itens, start=1):
        modelo_canonico = None
        if item.modelo_texto_original:
            modelo_canonico = (
                resolver_modelo(item.modelo_texto_original, tipo=ALIAS_TIPO_NOME_NF)
                or resolver_modelo(item.modelo_texto_original)
            )
        if modelo_canonico is None:
            chassis_sem_modelo_canonico.append(item.numero_chassi)
        cor_norm = (item.cor_texto_original or '').strip().upper() or None
        conf = registrar_conferencia_cega(
            recebimento_id=rec.id,
            numero_chassi=item.numero_chassi,
            modelo_id_conferido=modelo_canonico.id if modelo_canonico else None,
            cor_conferida=cor_norm,
            avaria_fisica=False,
            qr_code_lido=False,
            ordem=ordem,
            operador=operador,
        )
        conf_ids.append(conf.id)

    # 4. Finaliza (faz commit interno; trata MOTO_FALTANDO se sobrarem)
    rec = finalizar_recebimento(recebimento_id=rec.id, operador=operador)

    # 5. Auditoria explicita marcando origem AUTOMATICA
    recebimento_audit.registrar(
        recebimento_id=rec.id,
        acao='RECEBIMENTO_AUTOMATICO',
        usuario=operador,
        detalhe=(
            f'NF {nf.numero_nf} processada automaticamente: '
            f'{qtd_nf} chassi(s), {len(chassis_sem_modelo_canonico)} sem modelo canonico. '
            f'Status final: {rec.status}.'
        ),
    )
    db.session.commit()

    return {
        'ok': True,
        'recebimento_id': rec.id,
        'nf_id': nf.id,
        'numero_nf': nf.numero_nf,
        'loja_id': rec.loja_id,
        'qtd_itens_nf': qtd_nf,
        'conferencias_criadas': len(conf_ids),
        'chassis_sem_modelo_canonico': chassis_sem_modelo_canonico,
        'status_final': rec.status,
    }


# ========================================================================
# Exclusao admin-only (Item 2 — 2026-05-16)
# ========================================================================

def verificar_bloqueios_exclusao(recebimento_id: int) -> dict:
    """Mapeia conexoes pos-recebimento que bloqueiam (ou nao) a exclusao.

    Retorna dict com:
      - existe: bool — recebimento existe
      - bloqueios: list[str] — motivos que IMPEDEM exclusao
      - efeitos_colaterais: list[str] — o que sera deletado (avisos)
      - resumo: {qtd_confs, qtd_eventos, qtd_auditorias, qtd_divergencias,
                  pecas_faltando_abertas, devolucoes_abertas}
    """
    from app.hora.models import (
        HoraPecaFaltando,
        HoraDevolucaoFornecedorItem,
        HoraDevolucaoFornecedor,
        HoraMotoEvento,
        HoraConferenciaAuditoria,
        HoraConferenciaDivergencia,
    )

    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        return {'existe': False, 'bloqueios': [], 'efeitos_colaterais': [], 'resumo': {}}

    conf_ids = [c.id for c in rec.conferencias]
    bloqueios: list[str] = []
    efeitos: list[str] = []

    # Peca faltando ABERTA originada por conferencia do recebimento — bloqueia
    pecas_abertas = []
    if conf_ids:
        pecas_abertas = (
            HoraPecaFaltando.query
            .filter(HoraPecaFaltando.recebimento_conferencia_id.in_(conf_ids))
            .filter(HoraPecaFaltando.status == 'ABERTA')
            .all()
        )
    if pecas_abertas:
        chassis_p = ', '.join(sorted({p.numero_chassi for p in pecas_abertas}))
        bloqueios.append(
            f'{len(pecas_abertas)} peca(s) faltando ABERTA(s) vinculada(s) a '
            f'conferencias deste recebimento (chassis: {chassis_p}). '
            f'Resolva ou cancele as pecas antes de excluir.'
        )

    # Devolucao ao fornecedor com item vinculado a conferencia — bloqueia
    # se devolucao estiver ABERTA/ENVIADA (nao confirmada). CONFIRMADA: bloqueia
    # tambem (e historico fiscal).
    devs = []
    if conf_ids:
        devs = (
            db.session.query(HoraDevolucaoFornecedor, HoraDevolucaoFornecedorItem)
            .join(
                HoraDevolucaoFornecedorItem,
                HoraDevolucaoFornecedorItem.devolucao_id == HoraDevolucaoFornecedor.id,
            )
            .filter(HoraDevolucaoFornecedorItem.recebimento_conferencia_id.in_(conf_ids))
            .all()
        )
    if devs:
        ids_dev = sorted({d.id for d, _ in devs})
        bloqueios.append(
            f'{len(devs)} item(ns) de devolucao ao fornecedor vinculado(s) a '
            f'conferencias deste recebimento (devolucoes #{ids_dev}). '
            f'Cancele/exclua a devolucao antes (ou desvincule recebimento_conferencia_id).'
        )

    # Efeitos colaterais (deletes em cascata):
    qtd_eventos = 0
    if conf_ids:
        qtd_eventos = (
            HoraMotoEvento.query
            .filter(HoraMotoEvento.origem_tabela == 'hora_recebimento_conferencia')
            .filter(HoraMotoEvento.origem_id.in_(conf_ids))
            .count()
        )
    qtd_auditorias = (
        HoraConferenciaAuditoria.query
        .filter_by(recebimento_id=rec.id)
        .count()
    )
    qtd_divergencias = 0
    if conf_ids:
        qtd_divergencias = (
            HoraConferenciaDivergencia.query
            .filter(HoraConferenciaDivergencia.conferencia_id.in_(conf_ids))
            .count()
        )

    if rec.conferencias:
        efeitos.append(f'{len(rec.conferencias)} conferencia(s) sera(o) deletada(s) (cascade).')
    if qtd_divergencias:
        efeitos.append(f'{qtd_divergencias} divergencia(s) sera(o) deletada(s) (cascade).')
    if qtd_auditorias:
        efeitos.append(f'{qtd_auditorias} linha(s) de auditoria sera(o) deletada(s) (cascade).')
    if qtd_eventos:
        efeitos.append(
            f'{qtd_eventos} evento(s) hora_moto_evento (RECEBIDA/CONFERIDA/MOTO_FALTANDO) '
            f'sera(o) deletado(s) manualmente.'
        )
    efeitos.append(
        'Atualizacoes em hora_moto (cor/modelo_id) feitas pela conferencia '
        'NAO sao revertidas — sem historico para restaurar valor anterior. '
        'Edicao manual em hora_moto se necessario.'
    )

    return {
        'existe': True,
        'bloqueios': bloqueios,
        'efeitos_colaterais': efeitos,
        'resumo': {
            'qtd_confs': len(rec.conferencias),
            'qtd_eventos': qtd_eventos,
            'qtd_auditorias': qtd_auditorias,
            'qtd_divergencias': qtd_divergencias,
            'pecas_faltando_abertas': len(pecas_abertas),
            'devolucoes_vinculadas': len(devs),
            'nf_numero': rec.nf.numero_nf if rec.nf else None,
            'loja_nome': rec.loja.nome if rec.loja else None,
            'status': rec.status,
        },
    }


def excluir_recebimento(
    recebimento_id: int,
    operador: Optional[str] = None,
) -> dict:
    """Exclui recebimento + conferencias + auditoria + divergencias + eventos.

    Pre-condicoes:
      - Sem peca faltando ABERTA vinculada a conferencias do recebimento.
      - Sem item de devolucao_fornecedor vinculado a conferencias.

    Cascades automaticos (cascade='all, delete-orphan' nos relationships):
      - hora_recebimento_conferencia
      - hora_conferencia_auditoria (preservada nao adianta — FK CASCADE)
      - hora_conferencia_divergencia (cascade via conferencia)

    Deletes manuais (sem FK declarada):
      - hora_moto_evento WHERE origem_tabela='hora_recebimento_conferencia'
        AND origem_id IN [confs.id]

    Nao reverte: hora_moto.cor / modelo_id (sem historico).

    Retorna dict com totais deletados.
    """
    from app.hora.models import HoraMotoEvento

    bloqueio_info = verificar_bloqueios_exclusao(recebimento_id)
    if not bloqueio_info['existe']:
        raise ValueError(f'Recebimento {recebimento_id} nao encontrado')
    if bloqueio_info['bloqueios']:
        raise ValueError(
            'Nao e possivel excluir: ' + ' | '.join(bloqueio_info['bloqueios'])
        )

    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    conf_ids = [c.id for c in rec.conferencias]

    eventos_deletados = 0
    if conf_ids:
        eventos_deletados = (
            HoraMotoEvento.query
            .filter(HoraMotoEvento.origem_tabela == 'hora_recebimento_conferencia')
            .filter(HoraMotoEvento.origem_id.in_(conf_ids))
            .delete(synchronize_session=False)
        )
        db.session.flush()

    # Snapshot do recebimento para log (apos delete, o objeto some)
    snap_nf = rec.nf.numero_nf if rec.nf else None
    snap_loja = rec.loja.nome if rec.loja else None
    snap_status = rec.status
    snap_qtd_confs = len(rec.conferencias)
    snap_qtd_divs = bloqueio_info['resumo']['qtd_divergencias']

    # Auditoria nao podera ser registrada via recebimento_audit.registrar
    # porque a FK aponta para hora_recebimento (que sera deletado em sequencia).
    # Em vez disso, log estruturado.
    import logging
    logging.getLogger(__name__).warning(
        'EXCLUIU_RECEBIMENTO id=%s nf=%s loja=%s status=%s '
        'confs=%s eventos=%s divs=%s operador=%s',
        rec.id, snap_nf, snap_loja, snap_status,
        snap_qtd_confs, eventos_deletados, snap_qtd_divs, operador,
    )

    db.session.delete(rec)
    db.session.commit()

    return {
        'ok': True,
        'recebimento_id': recebimento_id,
        'eventos_deletados': eventos_deletados,
        'confs_deletadas': snap_qtd_confs,
        'divs_deletadas': snap_qtd_divs,
        'nf_numero': snap_nf,
        'loja_nome': snap_loja,
        'status_antes': snap_status,
        'operador': operador,
    }


# ========================================================================
# Privados
# ========================================================================

def _garantir_moto(chassi: str, item_nf: Optional[HoraNfEntradaItem], operador: Optional[str]):
    """Cria HoraMoto minima se nao existe (FK para conferencia).

    Migration hora_29: fallback_sentinela=True garante que recebimento
    nunca bloqueia por modelo desconhecido. Cria pendencia em paralelo.
    """
    if HoraMoto.query.get(chassi):
        return
    from app.hora.services.moto_service import get_or_create_moto
    from app.hora.models import PENDENTE_ORIGEM_RECEBIMENTO
    if item_nf:
        get_or_create_moto(
            numero_chassi=chassi,
            modelo_nome=(item_nf.modelo_texto_original or 'DESCONHECIDO').strip() or 'DESCONHECIDO',
            cor=(item_nf.cor_texto_original or 'NAO_INFORMADA').strip().upper() or 'NAO_INFORMADA',
            criado_por=operador,
            origem_pendencia=PENDENTE_ORIGEM_RECEBIMENTO,
            origem_id=item_nf.id,
            fallback_sentinela=True,
        )
    else:
        get_or_create_moto(
            numero_chassi=chassi,
            modelo_nome='CHASSI_EXTRA_DESCONHECIDO',
            cor='NAO_INFORMADA',
            criado_por=operador,
            origem_pendencia=PENDENTE_ORIGEM_RECEBIMENTO,
            fallback_sentinela=True,
        )


def _aplicar_correcao_moto_se_divergir(conf: HoraRecebimentoConferencia) -> None:
    """Recebimento e SOT: se conferencia confirmou cor/modelo diferente da NF,
    UPDATE-eia hora_moto.cor e hora_moto.modelo_id para os valores conferidos.

    Excecao controlada a invariante 3 do modulo HORA (insert-once em
    hora_moto). Justificada porque (a) recebimento e fonte de verdade de
    cor/modelo apos o fato fisico — usuario confirmou regra em 2026-05-06,
    e (b) ja existe precedente em hora_29 (retroatividade de modelo
    sentinela DESCONHECIDO -> canonico).

    Atualiza apenas se:
      - Existe HoraMoto para o chassi.
      - A conferencia ja tem `cor_conferida` ou `modelo_id_conferido` setado.
      - O valor conferido difere do que esta em hora_moto.

    Nao toca em chassis CHASSI_EXTRA (moto criada com modelo sentinela
    DESCONHECIDO + cor 'NAO_INFORMADA' ou cor conferida — operador
    eventualmente cataloga).
    """
    moto = HoraMoto.query.get(conf.numero_chassi)
    if moto is None:
        return

    mudou = False
    if conf.cor_conferida and conf.cor_conferida != moto.cor:
        moto.cor = conf.cor_conferida
        mudou = True
    if conf.modelo_id_conferido and conf.modelo_id_conferido != moto.modelo_id:
        moto.modelo_id = conf.modelo_id_conferido
        mudou = True
    if mudou:
        db.session.flush()


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
        # Comparacao via modelo CANONICO. A NF JA RESOLVE o modelo canonico
        # no momento do import: `nf_entrada_service.criar_nf_com_itens` chama
        # `get_or_create_moto(fallback_sentinela=True)` que cria HoraMoto com
        # FK `modelo_id` apontando para o canonico (ou para sentinela
        # DESCONHECIDO se ainda nao resolveu — retroatividade corrige depois).
        # Logo, a fonte de verdade do canonico do item da NF e
        # `item_nf.moto.modelo`, NAO `item_nf.modelo_texto_original`.
        # Bug 2026-05-16 — antes comparavamos texto cru no fallback e
        # marcavamos MODELO_DIFERENTE quando, de fato, ambos os lados ja
        # apontavam para o mesmo canonico. Confirmado em PROD (confs 39, 40).
        # Decisao 2026-05-16 (usuario): NAO criar alias auto aqui. So compara.
        # Quando NF nao resolve, pendencia ja existe (criada pelo import) e
        # operador resolve via /hora/modelos/pendencias (item 12 CLAUDE.md).
        from app.hora.services.modelo_resolver_service import resolver_modelo, _seguir_canonico
        from app.hora.models import ALIAS_TIPO_NOME_NF

        modelo_conf = (
            HoraModelo.query.get(conf.modelo_id_conferido)
            if conf.modelo_id_conferido else None
        )
        # Segue cadeia merged_em_id ate canonico ativo (defesa contra modelos
        # absorvidos).
        modelo_conf_canonico = _seguir_canonico(modelo_conf) if modelo_conf else None

        # FONTE DE VERDADE: FK da NF -> HoraMoto -> HoraModelo. JA e canonico
        # (com seguir_canonico defensivo para cobrir merges pos-creation).
        modelo_nf_canonico = None
        if item_nf.moto and item_nf.moto.modelo:
            modelo_nf_canonico = _seguir_canonico(item_nf.moto.modelo)
            # Se a moto da NF aponta para sentinela DESCONHECIDO (modelo nao
            # resolveu no import), trata como "nao resolvido" para nao gerar
            # divergencia falsa.
            if modelo_nf_canonico and modelo_nf_canonico.nome_modelo == 'DESCONHECIDO':
                modelo_nf_canonico = None

        # Fallback: se a moto ainda nao tem FK canonica boa (edge case raro,
        # ex. moto criada antes de hora_29 sem retroatividade), tenta resolver
        # pelo texto NF via aliases.
        if modelo_nf_canonico is None and item_nf.modelo_texto_original:
            modelo_nf_canonico = (
                resolver_modelo(item_nf.modelo_texto_original, tipo=ALIAS_TIPO_NOME_NF)
                or resolver_modelo(item_nf.modelo_texto_original)
            )

        if modelo_conf_canonico and modelo_nf_canonico:
            # Ambos resolveram canonico — compara IDs.
            if modelo_conf_canonico.id != modelo_nf_canonico.id:
                db.session.add(HoraConferenciaDivergencia(
                    conferencia_id=conf.id,
                    tipo='MODELO_DIFERENTE',
                    valor_esperado=modelo_nf_canonico.nome_modelo,
                    valor_conferido=modelo_conf_canonico.nome_modelo,
                ))
                snapshot = snapshot or 'MODELO_DIFERENTE'
        # Casos restantes (sem divergencia marcada):
        #   - NF nao resolve canonico (operador resolve via /hora/modelos/pendencias)
        #   - operador nao conferiu modelo (modelo_conf_canonico is None)
        # Em qualquer um deles, sem evidencia confiavel para divergir.

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
