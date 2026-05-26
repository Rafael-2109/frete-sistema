"""_invoice_helpers.py — Helpers POS-invoice CIEL IT por PERFIL (Skill 8 v16).

CR-C10.1 v16 (CRITICAL Rafael 2026-05-25): capina os 3 helpers F5d.5/.6/.7 do
service legado `inventario_pipeline_service.py:165-506` para arquivo separado
com PARAMETRO `perfil`. Cada helper aceita `perfil='inventario-inter-company'`
(V1); outros perfis raise `NotImplementedError` ate' a logica especifica estar
implementada.

ARQUITETURA (decisao Rafael v16):
  Inline na classe orchestrator contaminaria logica generica com regras
  especificas de inventario inter-company (ex: `price_unit=0` em
  venda-cliente NAO eh corrigido para `standard_price` — eh erro de
  cadastro real). Arquivo separado com perfis garante:
  - V1: cobre 'inventario-inter-company' (default Skill 8 v16+)
  - Futuro: perfis 'venda-cliente', 'compras-importacao', etc.
    adicionados sem refatorar Skill 8

ANALOGO arquitetural: sub-skill C5 `auditando-cadastro-fiscal-odoo` cobre
PRE-bulk; estes helpers cobrem POS-invoice (account.move criada pelo CIEL IT).
Timing distinto = arquivos distintos.

3 helpers (V1 perfil 'inventario-inter-company'):
  - garantir_payment_provider (G029): set payment_provider_id=38 (SEM PAGAMENTO).
    Sem isso, SEFAZ rejeita 'Meio de pagamento nao configurado'.
  - garantir_fiscal_setup (G034 DEV_*): reset_to_draft + write fiscal_position
    + l10n_br_tipo_pedido + post para acoes DEV (devolucao retrabalho).
    Robo CIEL IT usa defaults do picking_type errado para devolucao.
  - corrigir_price_zero_em_invoice (G007): fallback standard_price ou 0.01.
    Robo as vezes nao popula price_unit → vUnCom=0 viola schema NFe.

Auditoria via OperacaoOdooAuditoria.registrar (lazy import + try/except —
falha de auditoria NAO derruba pipeline real, pattern do service legado).

Spec: app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md §4.6 / §6.2 / §7.2.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, FrozenSet, Optional

from app.odoo.constants.ids_diversos import PAYMENT_PROVIDER_SEM_PAGAMENTO

logger = logging.getLogger(__name__)

# ============================================================
# Perfis suportados (V1 = inventario-inter-company)
# ============================================================

PERFIL_INVENTARIO_INTER_COMPANY = 'inventario-inter-company'

PERFIS_SUPORTADOS: FrozenSet[str] = frozenset({
    PERFIL_INVENTARIO_INTER_COMPANY,
})

# Futuros perfis declarados aqui (mas raise NotImplementedError nos helpers):
PERFIL_VENDA_CLIENTE = 'venda-cliente'                # logica G007 diferente
PERFIL_COMPRAS_IMPORTACAO = 'compras-importacao'      # hipotetico

# Lista de perfis EXISTENTES mas NAO implementados — informativo, raise.
PERFIS_PLANEJADOS_NAO_IMPLEMENTADOS: FrozenSet[str] = frozenset({
    PERFIL_VENDA_CLIENTE,
    PERFIL_COMPRAS_IMPORTACAO,
})


# ============================================================
# FISCAL_SETUP_POR_ACAO (G034 — DEV_* perfil inventario-inter-company)
# ============================================================

# Copia do service legado L143-159. Mantida aqui para fonte unica do
# perfil 'inventario-inter-company'. Quando service legado for capinado
# (v17+), service legado importa daqui (DEPRECATE inline).
#
# NF de referencia validada para DEV_CD_LF: 590839 RRET/2026/00008.
# LIMITACAO: journal_id NAO pode ser alterado apos primeira postagem.
FISCAL_SETUP_POR_ACAO_INVENTARIO: Dict[str, Dict[str, Any]] = {
    'DEV_LF_FB': {
        'fiscal_position_id': 89,    # SAIDA - RETRABALHO (LF, company=5)
        'l10n_br_tipo_pedido': 'dev-industrializacao',
    },
    'DEV_LF_CD': {
        'fiscal_position_id': 89,    # SAIDA - RETRABALHO (LF)
        'l10n_br_tipo_pedido': 'dev-industrializacao',
    },
    'DEV_CD_LF': {
        'fiscal_position_id': 74,    # SAIDA - REMESSA P/ RETRABALHO (CD, company=4)
        'l10n_br_tipo_pedido': 'dev-industrializacao',
    },
    # DEV_FB_LF: P011 — sem precedente historico. FP 74 esta em CD (company=4),
    # nao em FB (company=1). Precisa cadastro contadora antes de habilitar.
}


# ============================================================
# Helper de auditoria (compartilhado entre os 3 helpers)
# ============================================================

def _registrar_auditoria(
    *,
    ciclo: str,
    ajuste_id: int,
    fase: str,
    acao: str,
    status: str,
    modelo_odoo: str,
    odoo_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    resposta: Optional[Dict[str, Any]] = None,
    erro_msg: Optional[str] = None,
    tempo_ms: Optional[int] = None,
    executado_por: str = 'sistema',
) -> None:
    """Registra operacao em operacao_odoo_auditoria (POS-invoice CIEL IT).

    Lazy import OperacaoOdooAuditoria — evita circular em testes.
    Falha de auditoria NAO deve quebrar pipeline real (pattern service legado L569).
    """
    try:
        from app.odoo.models import OperacaoOdooAuditoria  # lazy
        external_id = (
            f'INV-{ciclo}-A{ajuste_id:06d}-{fase}-{uuid.uuid4().hex[:8]}'
        )
        OperacaoOdooAuditoria.registrar(
            external_id=external_id,
            tabela_origem='ajuste_estoque_inventario',
            registro_id=ajuste_id,
            acao=acao,
            modelo_odoo=modelo_odoo,
            etapa=fase,
            etapa_descricao=f'{fase} {acao}',
            status=status,
            payload_json=payload,
            resposta_json=resposta,
            erro_msg=erro_msg,
            tempo_execucao_ms=tempo_ms,
            pipeline_etapa=fase,
            contexto_origem='faturamento_pipeline_v16',
            contexto_ref=ciclo,
            executado_por=executado_por,
            odoo_id=odoo_id,
        )
    except Exception as e:
        logger.error(
            f'_registrar_auditoria fase={fase} falhou: {e}', exc_info=True,
        )


def _validar_perfil(perfil: str) -> None:
    """Valida perfil + raise NotImplementedError se nao suportado.

    Args:
        perfil: identificador do perfil (default 'inventario-inter-company').

    Raises:
        NotImplementedError: se perfil declarado mas nao implementado
            (ex: 'venda-cliente' V1).
        ValueError: se perfil totalmente desconhecido.
    """
    if perfil in PERFIS_SUPORTADOS:
        return
    if perfil in PERFIS_PLANEJADOS_NAO_IMPLEMENTADOS:
        raise NotImplementedError(
            f'Perfil {perfil!r} planejado mas NAO implementado. '
            f'V1 cobre apenas {sorted(PERFIS_SUPORTADOS)}. '
            f'Para venda-cliente: `price_unit=0` NAO eh corrigido por '
            f'standard_price (eh erro de cadastro real), DEV_* nao se '
            f'aplica, payment_provider depende do meio de pagamento '
            f'configurado no cliente. Refatorar quando demanda surgir.'
        )
    raise ValueError(
        f'Perfil {perfil!r} desconhecido. Validos: '
        f'{sorted(PERFIS_SUPORTADOS | PERFIS_PLANEJADOS_NAO_IMPLEMENTADOS)}'
    )


# ============================================================
# F5d.5 — garantir_payment_provider (G029)
# ============================================================

def garantir_payment_provider(
    odoo,
    invoice_id: int,
    ajuste,
    *,
    perfil: str = PERFIL_INVENTARIO_INTER_COMPANY,
    executado_por: str = 'sistema',
) -> bool:
    """G029 F5d.5: garante payment_provider_id setado em invoice (idempotente).

    Setado para PAYMENT_PROVIDER_SEM_PAGAMENTO=38 ('SEM PAGAMENTO') — valor
    compativel com NFs de transferencia/perda inter-company (sem cobranca
    financeira). Necessario para SEFAZ Playwright.

    Idempotente: se ja' setado, skip. Em falha de write em posted, fallback
    via reset_to_draft + write + action_post.

    Args:
        odoo: conexao XML-RPC.
        invoice_id: account.move.id criada pelo robo CIEL IT.
        ajuste: AjusteEstoqueInventario (para auditoria — precisa `.id`,
            `.ciclo`, `.acao_decidida`).
        perfil: V1 = 'inventario-inter-company'. Outros raise.
        executado_por: usuario para auditoria.

    Returns:
        True se setou (ou ja estava setado), False se falhou.

    Raises:
        NotImplementedError: se perfil != V1.
    """
    _validar_perfil(perfil)

    # CR-FIX R2F1 v16 (CRITICAL 92): ler situacao_nf JUNTO com
    # payment_provider_id na consulta inicial. Necessario para o guard
    # do fallback (button_draft em NF autorizada invalida chave SEFAZ).
    # Inclui 'enviado' (R2F2 88) — estado mid-SEFAZ.
    situacao_nf_inicial: Optional[str] = None
    try:
        current = odoo.read(
            'account.move', [invoice_id],
            ['payment_provider_id', 'l10n_br_situacao_nf'],
        )
        if current:
            situacao_nf_inicial = current[0].get('l10n_br_situacao_nf')
            if current[0].get('payment_provider_id'):
                logger.info(
                    f'payment_provider_id ja setado em invoice {invoice_id}: '
                    f'{current[0]["payment_provider_id"]} — skip.'
                )
                return True
    except Exception as e:
        logger.warning(f'check payment_provider_id falhou: {e}')

    # Setar via write direto (mesmo em state=posted — testado no piloto)
    try:
        odoo.write(
            'account.move', [invoice_id],
            {'payment_provider_id': PAYMENT_PROVIDER_SEM_PAGAMENTO},
        )
        logger.info(
            f'payment_provider_id={PAYMENT_PROVIDER_SEM_PAGAMENTO} '
            f'setado em invoice {invoice_id}'
        )
        _registrar_auditoria(
            ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.5',
            acao='set_payment_provider', modelo_odoo='account.move',
            status='SUCESSO', executado_por=executado_por,
            odoo_id=invoice_id,
            payload={'payment_provider_id': PAYMENT_PROVIDER_SEM_PAGAMENTO},
        )
        return True
    except Exception as e:
        logger.error(
            f'write payment_provider_id em posted falhou: {e}. '
            'Tentando reset_to_draft + write + post...'
        )
        # CR-FIX R2F1 v16 (CRITICAL 92): GUARD CRITICO — NAO chamar
        # button_draft se NF ja SEFAZ-autorizada ou enviada. Invalidaria
        # chave fiscal irreversivelmente.
        if situacao_nf_inicial in (
            'autorizado', 'excecao_autorizado', 'enviado',
        ):
            logger.error(
                f'F5d.5 GUARD R2F1: invoice {invoice_id} situacao_nf='
                f'{situacao_nf_inicial!r} — NAO chamar button_draft '
                f'(invalidaria chave SEFAZ). Operador deve cancelar NF '
                f'manualmente OU recriar invoice.'
            )
            _registrar_auditoria(
                ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.5',
                acao='set_payment_provider',
                modelo_odoo='account.move',
                status='SKIP_GUARD_SITUACAO_NF',
                executado_por=executado_por,
                odoo_id=invoice_id, erro_msg=str(e)[:200],
                payload={
                    'situacao_nf': situacao_nf_inicial,
                    'motivo': 'guard SEFAZ — button_draft invalidaria chave',
                },
            )
            return False
        try:
            odoo.execute_kw(
                'account.move', 'button_draft', [[invoice_id]],
            )
            odoo.write(
                'account.move', [invoice_id],
                {'payment_provider_id': PAYMENT_PROVIDER_SEM_PAGAMENTO},
            )
            odoo.execute_kw(
                'account.move', 'action_post', [[invoice_id]],
            )
            logger.info(
                f'payment_provider_id setado via reset_to_draft+post '
                f'em invoice {invoice_id}'
            )
            _registrar_auditoria(
                ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.5',
                acao='set_payment_provider', modelo_odoo='account.move',
                status='SUCESSO', executado_por=executado_por,
                odoo_id=invoice_id,
                payload={
                    'payment_provider_id': PAYMENT_PROVIDER_SEM_PAGAMENTO,
                    'metodo': 'reset_to_draft+write+post',
                },
            )
            return True
        except Exception as e2:
            _registrar_auditoria(
                ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.5',
                acao='set_payment_provider', modelo_odoo='account.move',
                status='FALHA', executado_por=executado_por,
                odoo_id=invoice_id, erro_msg=str(e2),
            )
            return False


# ============================================================
# F5d.7 — garantir_fiscal_setup (G034 DEV_*)
# ============================================================

def garantir_fiscal_setup(
    odoo,
    invoice_id: int,
    ajuste,
    *,
    perfil: str = PERFIL_INVENTARIO_INTER_COMPANY,
    executado_por: str = 'sistema',
) -> bool:
    """G034 F5d.7: garante FP/journal/tipo_pedido corretos para acoes DEV_*.

    Robo CIEL IT usa defaults do picking_type, que para PT 66 LF (Expedicao
    Industrializacao) sao venda-industrializacao (FP 111, journal VND, CFOP
    5124). ERRADO para devolucao de retrabalho — deveria ser CFOP 5949
    (FP 89/74 + tipo dev-industrializacao).

    Aplica reset_to_draft + write + action_post para corrigir. Idempotente:
    se ja' esta com setup correto, skip. Guard: se ja SEFAZ-autorizado
    ('autorizado' ou 'excecao_autorizado'), NAO mexer (pode quebrar chave).

    Args:
        odoo: conexao XML-RPC.
        invoice_id: account.move criada pelo robo.
        ajuste: AjusteEstoqueInventario (para resolver acao_decidida).
        perfil: V1 = 'inventario-inter-company'. Outros raise.
        executado_por: usuario para auditoria.

    Returns:
        True se setou (ou ja' OK ou acao sem fix), False se falhou.

    Raises:
        NotImplementedError: se perfil != V1.
    """
    _validar_perfil(perfil)

    setup = FISCAL_SETUP_POR_ACAO_INVENTARIO.get(ajuste.acao_decidida)
    if not setup:
        # CR-FIX R2F5 v16 (HIGH 83): se acao DEV_* nao mapeada (ex DEV_FB_LF
        # sem precedente historico), registrar SKIP_NAO_MAPEADO em auditoria
        # para nao silenciar problema. Caller (orchestrator) ainda recebe True
        # mas a auditoria revela que NAO houve fix fiscal aplicado.
        if (ajuste.acao_decidida or '').startswith('DEV_'):
            logger.warning(
                f'G034 acao={ajuste.acao_decidida!r} sem mapeamento em '
                f'FISCAL_SETUP_POR_ACAO_INVENTARIO. NAO aplicar fix fiscal — '
                f'cadastro contadora necessario antes de habilitar.'
            )
            _registrar_auditoria(
                ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.7',
                acao='fix_fiscal_setup', modelo_odoo='account.move',
                status='SKIP_NAO_MAPEADO', executado_por=executado_por,
                odoo_id=invoice_id,
                payload={'acao_decidida': ajuste.acao_decidida},
                erro_msg=(
                    'FISCAL_SETUP_POR_ACAO_INVENTARIO sem entrada — '
                    'cadastro contadora pendente'
                ),
            )
        # Acao nao precisa de fix (PERDA, INDUSTRIALIZACAO, TRANSFERIR, etc.)
        return True

    # Idempotencia: ler estado atual
    try:
        current = odoo.read(
            'account.move', [invoice_id],
            ['fiscal_position_id', 'journal_id', 'l10n_br_tipo_pedido',
             'state', 'l10n_br_situacao_nf'],
        )
        if not current:
            logger.warning(f'G034 invoice {invoice_id} sumiu, skip')
            return False
        inv = current[0]

        # CR-FIX R2F2+R2F4 v16: GUARD SEFAZ + retornar True (orchestrator
        # distingue OK real vs SKIP_GUARD via auditoria, NAO via bool).
        # Inclui 'enviado' (mid-SEFAZ) — chamar button_draft com lote SEFAZ
        # em transito abandona o polling do CIEL IT.
        if inv.get('l10n_br_situacao_nf') in (
            'autorizado', 'excecao_autorizado', 'enviado',
        ):
            logger.warning(
                f'G034 invoice {invoice_id} situacao_nf='
                f'{inv["l10n_br_situacao_nf"]!r} — guard SEFAZ '
                f'(button_draft invalidaria/abandonaria lote). '
                f'Operador deve cancelar NF manualmente se FP errada.'
            )
            _registrar_auditoria(
                ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.7',
                acao='fix_fiscal_setup', modelo_odoo='account.move',
                status='SKIP_GUARD_SITUACAO_NF',
                executado_por=executado_por,
                odoo_id=invoice_id,
                payload={
                    'situacao_nf': inv['l10n_br_situacao_nf'],
                    'motivo': 'guard SEFAZ — button_draft invalidaria chave',
                },
            )
            # CR-FIX R2F4: retornar True para nao inflar contador de falha.
            # Operador ve via auditoria SKIP_GUARD_SITUACAO_NF que NAO houve fix.
            return True

        fp_atual = (
            inv['fiscal_position_id'][0] if inv['fiscal_position_id'] else None
        )
        tipo_atual = inv.get('l10n_br_tipo_pedido')

        if (
            fp_atual == setup['fiscal_position_id']
            and tipo_atual == setup['l10n_br_tipo_pedido']
        ):
            logger.info(
                f'G034 invoice {invoice_id} fiscal setup ja correto — skip.'
            )
            return True

        logger.warning(
            f'G034 invoice {invoice_id} setup divergente: '
            f'fp={fp_atual}->{setup["fiscal_position_id"]}, '
            f'tipo={tipo_atual}->{setup["l10n_br_tipo_pedido"]}. '
            f'Aplicando reset_to_draft + write + post '
            f'(journal_id NAO alteravel apos post inicial).'
        )
    except Exception as e:
        logger.warning(f'G034 ler invoice {invoice_id} falhou: {e}')
        return False

    # Reset to draft + write + post
    # journal_id removido do write — Odoo bloqueia troca apos primeira post
    try:
        odoo.execute_kw(
            'account.move', 'button_draft', [[invoice_id]],
        )
        odoo.write(
            'account.move', [invoice_id],
            {
                'fiscal_position_id': setup['fiscal_position_id'],
                'l10n_br_tipo_pedido': setup['l10n_br_tipo_pedido'],
            },
        )
        odoo.execute_kw(
            'account.move', 'action_post', [[invoice_id]],
        )
        logger.info(
            f'G034 invoice {invoice_id} fiscal setup corrigido '
            f'(FP={setup["fiscal_position_id"]}, '
            f'tipo={setup["l10n_br_tipo_pedido"]}; '
            f'journal mantido — Odoo proibe troca)'
        )
        _registrar_auditoria(
            ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.7',
            acao='fix_fiscal_setup', modelo_odoo='account.move',
            status='SUCESSO', executado_por=executado_por,
            odoo_id=invoice_id,
            payload=setup,
        )
        return True
    except Exception as e:
        logger.error(f'G034 reset+write+post falhou: {e}')
        _registrar_auditoria(
            ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.7',
            acao='fix_fiscal_setup', modelo_odoo='account.move',
            status='FALHA', executado_por=executado_por,
            odoo_id=invoice_id, erro_msg=str(e),
            payload=setup,
        )
        return False


# ============================================================
# F5d.6 — corrigir_price_zero_em_invoice (G007)
# ============================================================

def corrigir_price_zero_em_invoice(
    odoo,
    invoice_id: int,
    ajuste,
    *,
    perfil: str = PERFIL_INVENTARIO_INTER_COMPANY,
    executado_por: str = 'sistema',
) -> int:
    """G007 F5d.6: corrige linhas com price_unit=0 buscando standard_price.

    Robo CIEL IT as vezes nao popula price_unit (gera zero). Se transmitir
    SEFAZ assim, vUnCom=0 viola schema NFe e SEFAZ rejeita com 'Falha no
    Schema XML do lote de NFe'.

    PERFIL 'inventario-inter-company' V1: fallback standard_price ou 0.01.
    Em venda-cliente futuro, esta estrategia eh ERRADA — preco zero seria
    erro de cadastro real do cliente, nao default do robo.

    Estrategia:
      1. Ler invoice_line_ids e identificar linhas com price_unit<=0
      2. Para cada linha zerada: buscar product.standard_price
      3. Reset invoice to draft, write price_unit=abs(std_price) ou 0.01
      4. Re-post invoice

    Idempotente: se nao ha linhas zeradas, no-op.

    Args:
        odoo: conexao XML-RPC.
        invoice_id: account.move.
        ajuste: AjusteEstoqueInventario (auditoria).
        perfil: V1 = 'inventario-inter-company'. Outros raise.
        executado_por: usuario.

    Returns:
        int: numero de linhas corrigidas (0 se nada feito).

    Raises:
        NotImplementedError: se perfil != V1.
        Excecao: se reset/write/post falhar (caller decide).
    """
    _validar_perfil(perfil)

    try:
        # CR-FIX R2F3 v16 (HIGH 85): ler situacao_nf JUNTO com state +
        # invoice_line_ids. button_draft em NF autorizada/enviada invalida
        # chave SEFAZ — guard critico.
        inv = odoo.read(
            'account.move', [invoice_id],
            ['invoice_line_ids', 'state', 'l10n_br_situacao_nf'],
        )
        if not inv:
            logger.warning(f'F5d.6 invoice {invoice_id} sumiu, skip')
            return 0
        situacao_nf = inv[0].get('l10n_br_situacao_nf')
        line_ids = inv[0].get('invoice_line_ids') or []
        if not line_ids:
            return 0
        lines = odoo.read(
            'account.move.line', line_ids,
            ['id', 'product_id', 'price_unit'],
        )
        lines_zero = [
            l for l in lines
            if l.get('product_id') and (l.get('price_unit') or 0) <= 0
        ]
        if not lines_zero:
            return 0

        # CR-FIX R2F3 v16 (HIGH 85): GUARD SEFAZ — F5d.6 roda ANTES de F5d.7,
        # antes de SEFAZ. Mas em re-execucao (resume), invoice pode ja' estar
        # autorizada/enviada. button_draft invalidaria chave fiscal.
        if situacao_nf in ('autorizado', 'excecao_autorizado', 'enviado'):
            logger.warning(
                f'F5d.6 invoice {invoice_id}: {len(lines_zero)} linhas '
                f'price_unit<=0 detectadas MAS situacao_nf={situacao_nf!r}. '
                f'GUARD SEFAZ — NAO chamar button_draft (invalidaria chave). '
                f'Operador deve cancelar NF e recriar.'
            )
            _registrar_auditoria(
                ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.6',
                acao='corrigir_price_zero', modelo_odoo='account.move',
                status='SKIP_GUARD_SITUACAO_NF',
                executado_por=executado_por,
                odoo_id=invoice_id,
                payload={
                    'situacao_nf': situacao_nf,
                    'linhas_zero': len(lines_zero),
                    'motivo': 'guard SEFAZ — button_draft invalidaria chave',
                },
            )
            return 0

        logger.warning(
            f'F5d.6 invoice {invoice_id}: {len(lines_zero)} linhas '
            f'price_unit<=0. Corrigindo via standard_price (G007).'
        )

        # Buscar standard_price dos produtos
        prod_ids = list({l['product_id'][0] for l in lines_zero})
        prods = odoo.read(
            'product.product', prod_ids,
            ['default_code', 'standard_price'],
        )
        std_cache = {
            p['id']: abs(float(p.get('standard_price') or 0)) or 0.01
            for p in prods
        }

        # Reset to draft
        odoo.execute_kw(
            'account.move', 'button_draft', [[invoice_id]],
        )

        # Atualizar cada linha
        corrigidas = []
        for l in lines_zero:
            pid = l['product_id'][0]
            novo_preco = std_cache.get(pid, 0.01)
            odoo.write(
                'account.move.line', [l['id']],
                {'price_unit': novo_preco},
            )
            corrigidas.append({
                'line_id': l['id'],
                'product_id': pid,
                'price_novo': novo_preco,
            })

        # Re-post
        odoo.execute_kw(
            'account.move', 'action_post', [[invoice_id]],
        )

        _registrar_auditoria(
            ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.6',
            acao='corrigir_price_zero',
            modelo_odoo='account.move',
            status='SUCESSO', executado_por=executado_por,
            odoo_id=invoice_id,
            payload={'linhas_corrigidas': len(corrigidas)},
            resposta={'corrigidas': corrigidas},
        )
        logger.info(
            f'F5d.6 invoice {invoice_id}: {len(corrigidas)} linhas '
            f'price_unit corrigidas via standard_price.'
        )
        return len(corrigidas)
    except Exception as e:
        _registrar_auditoria(
            ciclo=ajuste.ciclo, ajuste_id=ajuste.id, fase='F5d.6',
            acao='corrigir_price_zero',
            modelo_odoo='account.move',
            status='FALHA', executado_por=executado_por,
            odoo_id=invoice_id, erro_msg=str(e),
        )
        raise
