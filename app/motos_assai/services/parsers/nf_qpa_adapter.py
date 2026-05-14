"""Adapter sobre `app.carvia.services.parsers.danfe_pdf_parser.DanfePDFParser`.

NÃO modifica módulo CarVia. Apenas chama, traduz e persiste em entidades assai_*.

Match BATEU/DIVERGENTE/NAO_RECONCILIADO:
- Para cada chassi da NF: busca AssaiSeparacaoItem ativo (separação não cancelada)
- BATEU = todos chassis bateram (loja + modelo + valor com tolerância 1%)
- DIVERGENTE = pelo menos 1 não bateu mas alguns sim
- NAO_RECONCILIADO = nenhum chassi da NF bate com separação
"""

from __future__ import annotations

import io
import re
from decimal import Decimal
from typing import Optional, Dict, Any, List

from app import db
from app.utils.file_storage import FileStorage
from app.utils.timezone import agora_brasil_naive
from app.motos_assai.models import (
    AssaiNfQpa, AssaiNfQpaItem, AssaiLoja,
    AssaiSeparacao, AssaiSeparacaoItem, AssaiMoto,
    SEPARACAO_STATUS_CANCELADA, SEPARACAO_STATUS_FATURADA,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO,
    NF_STATUS_CANCELADA,
    EVENTO_FATURADA, EVENTO_SEPARADA,
    DIVERGENCIA_TIPO_LOJA_DIVERGENTE,
    DIVERGENCIA_TIPO_VALOR_DIVERGENTE,
    DIVERGENCIA_TIPO_MODELO_DIVERGENTE,
    DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO,
    DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
    DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
)
from app.motos_assai.services.modelo_resolver import resolver_modelo
from app.motos_assai.services.moto_evento_service import emitir_evento


TOLERANCIA_VALOR_PCT = Decimal('0.01')


class NfQpaParseError(Exception):
    pass


class NfQpaJaImportadaError(Exception):
    pass


def importar_nf_qpa(
    pdf_bytes: bytes, nome_arquivo: str, importada_por_id: int,
) -> AssaiNfQpa:
    """Parseia PDF, persiste e calcula match."""
    from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser

    if not pdf_bytes:
        raise NfQpaParseError('PDF vazio')

    parser = DanfePDFParser(pdf_bytes=pdf_bytes)
    resultado = parser.get_todas_informacoes()

    chave = resultado.get('chave_acesso_nf')
    if not chave or len(chave) != 44:
        raise NfQpaParseError(f'chave_acesso_nf inválida: {chave}')

    if AssaiNfQpa.query.filter_by(chave_44=chave).first():
        raise NfQpaJaImportadaError(f'NF {chave} já importada')

    # Loja: extrair de nome_destinatario via "LJ\d+"
    nome_dest = resultado.get('nome_destinatario') or ''
    loja_match = re.search(r'LJ\s*(\d+)', nome_dest)
    loja = None
    if loja_match:
        loja = AssaiLoja.query.filter_by(numero=loja_match.group(1)).first()

    # S3
    buf = io.BytesIO(pdf_bytes); buf.name = nome_arquivo
    s3_key = FileStorage().save_file(
        buf, folder='motos_assai/nfs_qpa', filename=nome_arquivo,
        allowed_extensions=['pdf'],
    )

    nf = AssaiNfQpa(
        chave_44=chave,
        numero=resultado.get('numero_nf'),
        serie=resultado.get('serie_nf'),
        emitente_cnpj=re.sub(r'\D', '', resultado.get('cnpj_emitente') or '')[:18] or None,
        destinatario_cnpj=re.sub(r'\D', '', resultado.get('cnpj_destinatario') or '')[:18] or None,
        destinatario_nome=nome_dest,
        loja_id=loja.id if loja else None,
        valor_total=Decimal(str(resultado.get('valor_total', 0))),
        data_emissao=resultado.get('data_emissao'),
        pdf_s3_key=s3_key,
        status_match=NF_STATUS_NAO_RECONCILIADO,
        importada_em=agora_brasil_naive(),
        importada_por_id=importada_por_id,
    )
    db.session.add(nf)
    db.session.flush()

    # Items
    veiculos = resultado.get('veiculos') or []
    n_veiculos = max(1, len(veiculos))
    for v in veiculos:
        chassi = (v.get('chassi') or '').strip().upper()
        if not chassi:
            continue
        modelo = resolver_modelo(v.get('modelo', ''), origem='NF_QPA')
        # Valor unitário: tentar campos do parser (valor_unitario, valor, vUnCom,
        # vlrUnitario) — DanfePDFParser atual não retorna valor por veículo,
        # apenas chassi/cor/modelo/numero_motor/ano_modelo/codigo.
        # TODO: quando DanfePDFParser expor valor_unitario por veículo, remover fallback.
        valor_unit_v = (
            v.get('valor_unitario')
            or v.get('valor')
            or v.get('vUnCom')
            or v.get('vlrUnitario')
        )
        if valor_unit_v:
            try:
                valor_extraido = Decimal(str(valor_unit_v))
            except Exception:
                valor_extraido = Decimal(str(nf.valor_total / n_veiculos))
        else:
            # Fallback: distribuir valor_total igualmente entre veículos
            valor_extraido = Decimal(str(nf.valor_total / n_veiculos))
        db.session.add(AssaiNfQpaItem(
            nf_id=nf.id,
            chassi=chassi,
            modelo_extraido=v.get('modelo'),
            valor_extraido=valor_extraido,
        ))
    db.session.flush()

    # Ajuste pos-NF (regra 2026-05-12): NF e fonte de verdade. Se todos os
    # chassis da NF existem em assai_moto e ha sep candidata na loja, ajusta
    # a separacao para refletir a NF (move chassis necessarios, remove os
    # que nao vieram). Apos ajuste, _calcular_match() detecta BATEU.
    # Se ajuste falhar (chassis desconhecidos / sem loja / sem sep candidata),
    # _calcular_match() segue fluxo normal (DIVERGENTE/NAO_RECONCILIADO).
    sep_alvo_id_ajustada = None
    try:
        from app.motos_assai.services.separacao_service import ajustar_separacao_pela_nf
        ajuste = ajustar_separacao_pela_nf(nf.id, importada_por_id)
        if ajuste['ok']:
            sep_alvo_id_ajustada = ajuste['sep_alvo_id']
            import logging
            logging.getLogger(__name__).info(
                'ajustar_separacao_pela_nf: NF %s -> sep %s. %s',
                nf.numero, sep_alvo_id_ajustada, ajuste['razao'],
            )

            # K5 (Plano 5): apos ajuste mexer em chassis, sincronizar espelho Nacom
            # (delta entre AssaiSeparacaoItem atual e linhas em `separacao` Nacom).
            # Sem isso, lista_pedidos.html mostra qtd defasada.
            # Roda APENAS se sep ja foi mirrorada (lote tem linhas). Para EM_SEPARACAO,
            # a primeira finalizacao via mirror_assai_to_separacao ja cria tudo correto.
            try:
                from app.motos_assai.services.separacao_mirror_service import (
                    sincronizar_espelho_com_separacao,
                )
                sync_result = sincronizar_espelho_com_separacao(sep_alvo_id_ajustada)
                if sync_result['criadas'] or sync_result['deletadas']:
                    logging.getLogger(__name__).info(
                        'sincronizar_espelho_com_separacao apos NF %s: '
                        'criadas=%d deletadas=%d bloqueadas=%d',
                        nf.numero, sync_result['criadas'],
                        sync_result['deletadas'], len(sync_result['bloqueadas']),
                    )
                if sync_result['bloqueadas']:
                    logging.getLogger(__name__).warning(
                        'sincronizar_espelho_com_separacao NF %s: chassis bloqueados '
                        '(tem NF preenchida) — espelho fica defasado: %s',
                        nf.numero, sync_result['bloqueadas'],
                    )
            except Exception as e:
                logging.getLogger(__name__).error(
                    'sincronizar_espelho_com_separacao FALHOU NF %s: %s',
                    nf.numero, e, exc_info=True,
                )
        else:
            import logging
            logging.getLogger(__name__).info(
                'ajustar_separacao_pela_nf NAO aplicado para NF %s: %s '
                '(seguindo match natural)',
                nf.numero, ajuste['razao'],
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            'ajustar_separacao_pela_nf FALHOU para NF %s: %s — '
            'seguindo match natural',
            nf.numero, e, exc_info=True,
        )

    # Match (apos eventual ajuste — se ajuste OK, todos chassis estao na sep alvo
    # e _calcular_match retorna BATEU. Senao, fluxo original).
    _calcular_match(nf, importada_por_id)

    # Match reverso CCe (2026-05-13): aplicar CCes que chegaram antes desta NF.
    # Se houver alteracao de chassis pelas CCes, _calcular_match re-roda dentro
    # de aplicar_correcao_cce para atualizar status_match.
    try:
        from app.motos_assai.services.cce_service import (
            aplicar_cce_pendentes_para_nf,
        )
        resultados_cce = aplicar_cce_pendentes_para_nf(nf, importada_por_id)
        if resultados_cce:
            import logging as _log
            _log.getLogger(__name__).info(
                'NF %s: %d CCe(s) pendentes aplicadas via match reverso: %s',
                nf.numero, len(resultados_cce),
                [(r['cce_id'], r['status_final']) for r in resultados_cce],
            )
    except Exception as e:
        import logging as _log
        _log.getLogger(__name__).exception(
            'aplicar_cce_pendentes_para_nf FALHOU para NF %s: %s — '
            'NF importada normalmente, CCes ficam PENDENTE para acao manual',
            nf.numero, e,
        )
        # Nao bloqueia importacao da NF — CCes seguem como PENDENTE.

    db.session.commit()

    # Sincronizar EntregaMonitorada APOS commit — garante que a NF ja esta
    # persistida com status_match=BATEU (lookup posterior nao depende de
    # identity map). Nao-bloqueante: se sync falhar, NF e match permanecem.
    if nf.status_match == NF_STATUS_BATEU and nf.numero:
        try:
            from app.utils.sincronizar_entregas_op_assai import (
                sincronizar_entrega_op_assai_por_nf,
            )
            sincronizar_entrega_op_assai_por_nf(str(nf.numero))
            db.session.commit()  # commit do EntregaMonitorada criada/atualizada
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                'sincronizar_entrega_op_assai_por_nf (pos-commit) NF %s: %s',
                nf.numero, e,
            )
            db.session.rollback()

    return nf


def _calcular_match(nf: AssaiNfQpa, operador_id: int) -> None:
    """Tenta amarrar cada item da NF a uma AssaiSeparacaoItem ativo (v2).

    Plano 3 Tasks 3-5:
    - D5: ignora seps FATURADAS no JOIN (evita dupla vinculacao G7)
    - S8=a: grava divergencias em assai_divergencia centralizada (NAO em tipo_divergencia do item)
    - A8: valida modelo (cria MODELO_DIVERGENTE)
    - A14: idempotente — early return se NF CANCELADA
    - N-M6: distingue CHASSI_NAO_CADASTRADO vs CHASSI_SEM_SEPARACAO
    - M3: emite evento FATURADA por chassi quando BATEU (preserva comportamento legado)

    Atualiza:
        - nf.status_match (BATEU / DIVERGENTE / NAO_RECONCILIADO)
        - cria divergencias em assai_divergencia
        - vincula sep_item ao item da NF (separacao_item_id)

    NAO commita.
    """
    # A14: NF cancelada nao bate mais nada
    if nf.status_match == NF_STATUS_CANCELADA:
        return

    from app.motos_assai.services.divergencia_service import criar_divergencia

    items_nf = AssaiNfQpaItem.query.filter_by(nf_id=nf.id).all()
    matches_ok = 0
    matches_falha = 0

    separacoes_atualizar = set()

    for it in items_nf:
        # D5: ignora FATURADA + CANCELADA no JOIN (evita dupla vinculacao)
        sep_item = (
            db.session.query(AssaiSeparacaoItem)
            .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
            .filter(
                AssaiSeparacaoItem.chassi == it.chassi,
                AssaiSeparacao.status.notin_([
                    SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_CANCELADA,
                ]),
            )
            .first()
        )

        if not sep_item:
            # N-M6 fix: distinguir CHASSI_NAO_CADASTRADO (moto inexistente em assai_moto)
            # de CHASSI_SEM_SEPARACAO (moto existe mas sem sep candidata)
            moto_check = AssaiMoto.query.filter_by(chassi=it.chassi).first()
            tipo_div = (
                DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO if not moto_check
                else DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO
            )
            criar_divergencia(
                tipo=tipo_div,
                chassi=it.chassi, nf_id=nf.id,
                detalhes={'modelo_extraido': it.modelo_extraido},
            )
            # S8=a: legado tipo_divergencia mantido para retrocompat (ate UI migrar)
            it.tipo_divergencia = tipo_div
            matches_falha += 1
            continue

        sep = AssaiSeparacao.query.get(sep_item.separacao_id)

        # 1. Loja (S8=a)
        loja_ok = (not nf.loja_id) or (sep.loja_id == nf.loja_id)
        if not loja_ok:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_LOJA_DIVERGENTE,
                chassi=it.chassi, sep_id=sep.id, nf_id=nf.id,
                detalhes={'loja_sep': sep.loja_id, 'loja_nf': nf.loja_id},
            )
            it.tipo_divergencia = 'LOJA_DIVERGENTE'
            matches_falha += 1
            continue

        # 2. Valor com tolerância 1% (S8=a)
        v_sep = sep_item.valor_unitario_qpa
        v_nf = it.valor_extraido or Decimal('0')
        if v_sep > 0:
            diff_pct = abs(v_sep - v_nf) / v_sep
            if diff_pct > TOLERANCIA_VALOR_PCT:
                criar_divergencia(
                    tipo=DIVERGENCIA_TIPO_VALOR_DIVERGENTE,
                    chassi=it.chassi, sep_id=sep.id, nf_id=nf.id,
                    detalhes={
                        'valor_sep': float(v_sep),
                        'valor_nf': float(v_nf),
                        'pct': float(diff_pct),
                    },
                )
                it.tipo_divergencia = 'VALOR_DIVERGENTE'
                matches_falha += 1
                continue

        # 3. A8 — Modelo (chassi cadastrado em assai_moto X modelo extraido da NF)
        moto = AssaiMoto.query.filter_by(chassi=it.chassi).first()
        if moto and it.modelo_extraido:
            modelo_resolvido = resolver_modelo(it.modelo_extraido, origem='NF_QPA')
            if modelo_resolvido and moto.modelo_id != modelo_resolvido.id:
                criar_divergencia(
                    tipo=DIVERGENCIA_TIPO_MODELO_DIVERGENTE,
                    chassi=it.chassi, sep_id=sep.id, nf_id=nf.id,
                    detalhes={
                        'modelo_assai_moto_id': moto.modelo_id,
                        'modelo_extraido_nf': it.modelo_extraido,
                        'modelo_resolvido_id': modelo_resolvido.id,
                    },
                )
                it.tipo_divergencia = 'MODELO_DIVERGENTE'
                matches_falha += 1
                continue

        # OK
        it.separacao_item_id = sep_item.id
        matches_ok += 1
        separacoes_atualizar.add(sep_item.separacao_id)

    if matches_ok == 0:
        nf.status_match = NF_STATUS_NAO_RECONCILIADO
    elif matches_falha > 0:
        nf.status_match = NF_STATUS_DIVERGENTE
    else:
        nf.status_match = NF_STATUS_BATEU
        # Se BATEU, atribui separacao_id principal (a primeira que apareceu)
        if separacoes_atualizar:
            nf.separacao_id = next(iter(separacoes_atualizar))

        # Atualiza separações para FATURADA + emite eventos FATURADA (M3)
        pedidos_para_recalcular = set()
        for sep_id in separacoes_atualizar:
            sep = AssaiSeparacao.query.get(sep_id)
            if sep:
                sep.status = SEPARACAO_STATUS_FATURADA
                pedidos_para_recalcular.add(sep.pedido_id)

        # M3 fix: emite evento FATURADA por chassi (preserva comportamento legado)
        for it_ok in items_nf:
            if it_ok.separacao_item_id:
                emitir_evento(
                    it_ok.chassi, EVENTO_FATURADA,
                    operador_id=operador_id,
                    dados_extras={'nf_id': nf.id, 'chave_44': nf.chave_44},
                )

        # Code review fix C6 / S10 (2026-05-13): recalcular_status_pedido apos
        # BATEU. Spec §14.2: "_calcular_match BATEU eh o UNICO caminho que pode
        # SUBIR para FATURADO". Sem este callsite, pedido fica defasado em
        # PARCIALMENTE_FATURADO ate algum outro evento acionar a funcao.
        try:
            from app.motos_assai.services.pedido_status_service import (
                recalcular_status_pedido,
            )
            for pedido_id in pedidos_para_recalcular:
                recalcular_status_pedido(pedido_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                '_calcular_match BATEU: falha em recalcular_status_pedido '
                'pedidos=%s nf=%s: %s — segue (nao bloqueia BATEU)',
                pedidos_para_recalcular, nf.id, e, exc_info=True,
            )

        # Propagar numero_nf para o espelho em separacao Nacom — listener
        # `atualizar_status_automatico` recalcula status -> FATURADO.
        # Tambem propaga para EmbarqueItem.nota_fiscal (busca por
        # separacao_lote_id) se houver embarque ativo. Decisao do usuario
        # (2026-05-11): NFs Q.P.A. permitem sincronizado_nf=True (NF
        # Q.P.A. e propria da operacao, fora do fluxo Odoo Nacom).
        if nf.numero:
            try:
                from app.motos_assai.services.separacao_mirror_service import (
                    atualizar_nf_no_espelho, lote_id_de,
                )
                from app.embarques.models import EmbarqueItem
                for sep_id in separacoes_atualizar:
                    atualizar_nf_no_espelho(sep_id, str(nf.numero))
                    # Propagar para EmbarqueItem ativo do lote (se houver)
                    lote = lote_id_de(sep_id)
                    items_emb = EmbarqueItem.query.filter_by(
                        separacao_lote_id=lote, status='ativo',
                    ).all()
                    for ei in items_emb:
                        if not ei.nota_fiscal:
                            ei.nota_fiscal = str(nf.numero)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    'Falha ao propagar NF %s (assai_nf_qpa=%s) para espelho '
                    'em separacao Nacom: %s',
                    nf.numero, nf.id, e, exc_info=True,
                )

            # Sincronizacao EntregaMonitorada (origem='OP_ASSAI') foi movida
            # para APOS o commit em `importar_nf_qpa` (code review 2026-05-11):
            # `sincronizar_entrega_op_assai_por_nf` requery AssaiNfQpa por
            # status_match=BATEU, mas dentro de `_calcular_match` o status
            # so esta setado em memoria (ainda nao commitado). Identity map
            # do SQLAlchemy mascarava o problema em request-context mas
            # falharia silenciosamente em workers/background jobs.


# =====================================================================
# Vincular NF manualmente (Plano 4 Task 6 — 2026-05-13)
# =====================================================================
#
# Spec: §15.6 (ferramenta excepcional apos backfill Migration 23)
# Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase5-auxiliares.md Task 6
#
# Atalho de ajustar_separacao_pela_nf v2 que aceita pedido_id e loja_id explicitos.
# Usado quando NF NAO_RECONCILIADO precisa ser vinculada manualmente —
# casos onde Migration 23 backfill nao cobriu (ex: chassi nao existe em
# assai_moto + operador escolhe pedido+loja diretamente).


class VincularNfError(Exception):
    """Erro ao vincular NF manualmente."""


def vincular_nf_manualmente(
    nf_id: int,
    pedido_id: int,
    operador_id: int,
):
    """Vincula NF NAO_RECONCILIADO manualmente a um pedido.

    Regra de negocio (2026-05-14): o match e por **CNPJ destinatario** da NF.
    A NF nao traz o numero da loja explicitamente — apenas o CNPJ. O CNPJ e
    deterministico e e a chave usada para amarrar NF <-> Pedido:

        NF.destinatario_cnpj  ==  AssaiLoja.cnpj  ==  loja do pedido

    O pedido deve ter cabecalho (`AssaiPedidoVendaLoja`) cuja loja tenha o
    mesmo CNPJ do destinatario da NF.

    `loja_id` na NF e apenas uma derivacao do CNPJ — preenchemos se ainda
    estiver vazio (operacoes posteriores podem usar para evitar re-lookup).

    NAO commita — caller commita.

    Args:
        nf_id: ID da AssaiNfQpa NAO_RECONCILIADO.
        pedido_id: pedido alvo (deve ter AssaiPedidoVendaLoja em loja com mesmo CNPJ).
        operador_id: usuario que solicitou.

    Returns:
        Resultado de ajustar_separacao_pela_nf.

    Raises:
        VincularNfError: NF nao encontrada / NF nao NAO_RECONCILIADO /
            NF sem CNPJ destinatario / nenhuma loja com esse CNPJ /
            pedido nao tem cabecalho com esse CNPJ.
    """
    import re as _re
    from app.motos_assai.models import (
        AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiLoja,
    )
    from app.motos_assai.services.separacao_service import ajustar_separacao_pela_nf

    # Lock pessimista (code review #2): impede 2 operadores vinculando a mesma
    # NF em paralelo. Segue o padrao "Lock pessimista e invariantes de
    # concorrencia" ja estabelecido no modulo (CLAUDE.md Plano 3).
    nf = (
        db.session.query(AssaiNfQpa)
        .filter(AssaiNfQpa.id == nf_id)
        .with_for_update()
        .first()
    )
    if not nf:
        raise VincularNfError(f'NF {nf_id} nao encontrada')
    if nf.status_match != NF_STATUS_NAO_RECONCILIADO:
        raise VincularNfError(
            f'NF {nf_id} esta {nf.status_match} — apenas NAO_RECONCILIADO permite '
            'vincular manualmente. Para BATEU/DIVERGENTE/CANCELADA, use cancelar_nf_qpa '
            'antes se precisar re-vincular.'
        )

    # === Match por CNPJ destinatario (chave deterministica) ===
    cnpj_destinatario = _re.sub(r'\D', '', nf.destinatario_cnpj or '')
    if not cnpj_destinatario:
        raise VincularNfError(
            f'NF {nf_id} sem CNPJ destinatario — nao da pra vincular automaticamente. '
            'Reimporte a NF apos garantir que o PDF traz o CNPJ.'
        )

    # Buscar AssaiLoja com mesmo CNPJ (normalizado).
    # AssaiLoja.cnpj pode estar com mascara ('12.345.678/0001-90') ou sem.
    # Como a tabela de lojas e pequena (cadastro Sendas/Assai), normaliza
    # in-memory — evita SQL com regexp_replace que e dependente de dialeto.
    todas_lojas = AssaiLoja.query.all()
    lojas_match = [
        ll for ll in todas_lojas
        if _re.sub(r'\D', '', ll.cnpj or '') == cnpj_destinatario
    ]
    # Code review #3: AssaiLoja.cnpj nao tem UNIQUE no schema. Se houver
    # duplicacao no cadastro, levantar erro explicito em vez de pegar a
    # primeira loja silenciosamente (que dependeria do plano do Postgres).
    if len(lojas_match) > 1:
        raise VincularNfError(
            f'CNPJ {nf.destinatario_cnpj} ambiguo: {len(lojas_match)} lojas '
            f'cadastradas com esse CNPJ (ids: {[ll.id for ll in lojas_match]}). '
            'Corrija o cadastro em /motos-assai/lojas antes de vincular.'
        )
    loja = lojas_match[0] if lojas_match else None
    if not loja:
        raise VincularNfError(
            f'Nenhuma loja cadastrada com CNPJ {nf.destinatario_cnpj}. '
            'Cadastre a loja em /motos-assai/lojas antes de vincular esta NF.'
        )

    # Validar pedido existe
    if not AssaiPedidoVenda.query.get(pedido_id):
        raise VincularNfError(f'Pedido {pedido_id} nao encontrado')

    # Regra: o pedido deve ter cabecalho (AssaiPedidoVendaLoja) na loja resolvida via CNPJ
    pvl = AssaiPedidoVendaLoja.query.filter_by(
        pedido_id=pedido_id, loja_id=loja.id,
    ).first()
    if not pvl:
        raise VincularNfError(
            f'Pedido {pedido_id} nao possui cabecalho para CNPJ {nf.destinatario_cnpj} '
            f'(loja {loja.numero} {loja.nome}). '
            'Escolha um pedido que inclua esse CNPJ.'
        )

    # Sincroniza nf.loja_id (derivado do CNPJ) — preenche se ainda NULL
    # ou corrige se ficou divergente (cenario: regex LJ\d+ pegou loja errada).
    if nf.loja_id != loja.id:
        if nf.loja_id is not None:
            import logging
            logging.getLogger(__name__).warning(
                'vincular_nf_manualmente: NF %s tinha loja_id=%s mas CNPJ %s '
                'aponta para loja_id=%s — corrigindo via operador %s',
                nf_id, nf.loja_id, nf.destinatario_cnpj, loja.id, operador_id,
            )
        nf.loja_id = loja.id
        db.session.flush()

    # Reusa logica completa de ajustar_separacao_pela_nf v2:
    # - S1=b cria sep em FATURADA se nao ha sep candidata
    # - A11 gera Excel versao 1
    # - Match natural detecta BATEU apos ajuste
    resultado = ajustar_separacao_pela_nf(nf.id, operador_id)

    # Se ajuste OK, re-roda _calcular_match para fechar status=BATEU
    if resultado.get('ok'):
        _calcular_match(nf, operador_id)
        db.session.flush()

    import logging
    logging.getLogger(__name__).info(
        'vincular_nf_manualmente: nf=%s pedido=%s cnpj=%s loja=%s ok=%s sep=%s '
        'operador=%s',
        nf_id, pedido_id, cnpj_destinatario, loja.id, resultado.get('ok'),
        resultado.get('sep_alvo_id'), operador_id,
    )

    return resultado
