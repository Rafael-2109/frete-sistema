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
    AssaiSeparacao, AssaiSeparacaoItem,
    SEPARACAO_STATUS_CANCELADA, SEPARACAO_STATUS_FATURADA,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO,
    EVENTO_FATURADA,
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
    """Tenta amarrar cada item da NF a uma AssaiSeparacaoItem ativo.

    Critérios de BATEU:
    - chassi existe em AssaiSeparacaoItem ativa
    - separacao.loja_id == nf.loja_id (se NF tem loja)
    - separacao_item.modelo_id resolvido bate com modelo extraído
    - valor com tolerância de 1%
    """
    items_nf = AssaiNfQpaItem.query.filter_by(nf_id=nf.id).all()
    matches_ok = 0
    matches_falha = 0

    separacoes_atualizar = set()

    for it in items_nf:
        sep_item = (
            db.session.query(AssaiSeparacaoItem)
            .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
            .filter(
                AssaiSeparacaoItem.chassi == it.chassi,
                AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
            )
            .first()
        )

        if not sep_item:
            it.tipo_divergencia = 'CHASSI_SEM_SEPARACAO'
            matches_falha += 1
            continue

        sep = AssaiSeparacao.query.get(sep_item.separacao_id)

        # Loja
        loja_ok = (not nf.loja_id) or (sep.loja_id == nf.loja_id)
        if not loja_ok:
            it.tipo_divergencia = 'LOJA_DIVERGENTE'
            matches_falha += 1
            continue

        # Valor com tolerância 1%
        v_sep = sep_item.valor_unitario_qpa
        v_nf = it.valor_extraido or Decimal('0')
        if v_sep > 0:
            diff_pct = abs(v_sep - v_nf) / v_sep
            if diff_pct > TOLERANCIA_VALOR_PCT:
                it.tipo_divergencia = 'VALOR_DIVERGENTE'
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

        # Atualiza separações para FATURADA + emite eventos FATURADA
        for sep_id in separacoes_atualizar:
            sep = AssaiSeparacao.query.get(sep_id)
            sep.status = SEPARACAO_STATUS_FATURADA

        for it_ok in items_nf:
            if it_ok.separacao_item_id:
                emitir_evento(
                    it_ok.chassi, EVENTO_FATURADA,
                    operador_id=operador_id,
                    dados_extras={'nf_id': nf.id, 'chave_44': nf.chave_44},
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
            # Ver `importar_nf_qpa` no final do arquivo.
