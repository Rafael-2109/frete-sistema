"""Service de refresh do snapshot de NF inter-company (transferencia entre filiais).

Busca account.move out_invoice inter-company nos ultimos N dias (default 90),
faz cross-ref com DFe destino via chave NF-e, picking destino e invoice destino,
consolida status e grava em NfTransferenciaSnapshot + NfTransferenciaProdutoSnapshot.

Usado por:
- Tela /operacional/compras/relatorios/nf-transferencia (botao Atualizar)
- SnapshotOdooService.refresh (chamado ANTES, alimenta em_transito_*)
"""
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict
from typing import Dict, List, Any, Tuple

from sqlalchemy import delete, func as sa_func

from app import db
from app.recebimento.models import (
    NfTransferenciaSnapshot, NfTransferenciaProdutoSnapshot,
    NfTransferenciaDesconsiderada, CFOPS_RETORNO_INSUMO_INDUSTRIALIZACAO,
)
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.constants.operacoes_fiscais import (
    COMPANY_PARTNER_ID, ACAO_PARA_DIRECAO,
)
from app.utils.timezone import agora_utc_naive

import logging
logger = logging.getLogger(__name__)


COMPANY_NAME: Dict[int, str] = {1: 'FB', 4: 'CD', 5: 'LF'}
# Reverse de COMPANY_PARTNER_ID: partner_id (cliente) -> company_id (destino)
PARTNER_TO_COMPANY: Dict[int, int] = {v: k for k, v in COMPANY_PARTNER_ID.items()}

# Reverse de ACAO_PARA_DIRECAO: (company_origem, company_destino, tipo_pedido) -> acao
DIRECAO_PARA_ACAO: Dict[Tuple[int, int, str], str] = {}
for _acao, (_tipo_op, _co, _cd) in ACAO_PARA_DIRECAO.items():
    DIRECAO_PARA_ACAO[(_co, _cd, _tipo_op)] = _acao

ODOO_BATCH = 200

STATUS_PENDENTES = ('PENDENTE_DFE', 'PENDENTE_PICKING', 'PENDENTE_INVOICE')
STATUS_TODOS = (
    'PENDENTE_DFE', 'PENDENTE_PICKING', 'PENDENTE_INVOICE',
    'CONCLUIDO', 'CANCELADA',
)


def _m2o_id(v):
    return v[0] if isinstance(v, (list, tuple)) and v else None


def _m2o_name(v):
    return v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ''


def _norm_str(v, maxlen=None):
    if v is None or v is False:
        return None
    s = str(v).strip()
    if not s:
        return None
    if maxlen and len(s) > maxlen:
        s = s[:maxlen]
    return s


def _parse_odoo_dt(v):
    """Converte timestamp Odoo (UTC naive ISO string) para datetime naive.

    Odoo XML-RPC retorna `False` (ausente) ou string ISO
    'YYYY-MM-DD HH:MM:SS'. Mantemos naive (sem tzinfo) — convencao do
    sistema (.claude/references/REGRAS_TIMEZONE.md).

    Falha de parse (string malformada) NAO levanta — retorna None e loga
    em DEBUG para nao silenciar erros sistematicos do Odoo.
    """
    from datetime import datetime as _dt
    if v is None or v is False or v == '':
        return None
    try:
        # Odoo: '2026-05-28 13:42:39' (UTC). datetime.fromisoformat aceita.
        return _dt.fromisoformat(str(v).replace('T', ' ').split('.')[0])
    except (ValueError, TypeError):
        logger.debug('_parse_odoo_dt: nao parseou valor=%r', v)
        return None


class NfTransferenciaService:
    """Refresh do snapshot de NF inter-company."""

    @staticmethod
    def refresh(usuario: str = 'Sistema', dias: int = 90, job=None) -> Dict[str, Any]:
        """
        Busca NFs inter-company no Odoo + cross-ref destino + grava snapshot.

        Args:
            usuario: nome do usuario para auditoria
            dias: dias retroativos a buscar (default 90)
            job: rq.job para progress (opcional)

        Returns:
            {total, pendentes, concluidos, canceladas, por_status, refresh_em}
        """
        def _progress(p, msg):
            if job is not None:
                try:
                    job.meta['progress'] = p
                    job.meta['msg'] = msg
                    job.save_meta()
                except Exception:
                    pass

        _progress(5, 'Conectando ao Odoo')
        odoo = get_odoo_connection()

        data_corte = (date.today() - timedelta(days=dias)).isoformat()
        partners_grupo = list(COMPANY_PARTNER_ID.values())  # [1, 34, 35]

        _progress(15, 'Buscando NFs inter-company')
        moves = NfTransferenciaService._buscar_nfs_origem(
            odoo, data_corte, partners_grupo,
        )

        if not moves:
            # I2 (code review 2026-05-28): zero NFs encontradas pode ser
            # genuinamente "sem inter-company no periodo" OU erro transitorio
            # do Odoo (timeout retornando []). Log WARNING para auditoria —
            # operador pode comparar com refresh anterior e detectar regressao
            # silenciosa de em_transito_*.
            logger.warning(
                'NfTransferenciaService.refresh: ZERO NFs inter-company '
                'encontradas (dias=%s, partners=%s). Snapshot sera ZERADO. '
                'Validar se eh genuino ou erro Odoo transitorio.',
                dias, partners_grupo,
            )
            NfTransferenciaService._wipe_snapshot()
            _progress(100, 'Concluido (sem NFs)')
            return {
                'total': 0, 'pendentes': 0, 'concluidos': 0, 'canceladas': 0,
                'por_status': {s: 0 for s in STATUS_TODOS},
                'refresh_em': agora_utc_naive().isoformat(),
                'aviso': 'Zero NFs encontradas — verificar se eh genuino',
            }

        _progress(35, f'Cross-ref DFe destino ({len(moves)} NFs)')
        # NF origem usa `l10n_br_chave_nf` (account.move). DFe destino usa
        # `protnfe_infnfe_chnfe` (l10n_br_ciel_it_account.dfe). Mesma chave
        # NFe (44 digitos) mas campos com nomes diferentes em cada model.
        chaves = [m.get('l10n_br_chave_nf') for m in moves
                  if m.get('l10n_br_chave_nf')]
        dfes = NfTransferenciaService._buscar_dfes_destino(odoo, chaves)
        dfe_by_chave: Dict[str, Dict] = {}
        for d in dfes:
            ch = d.get('protnfe_infnfe_chnfe')
            if ch:
                dfe_by_chave[ch] = d

        po_ids = set()
        for d in dfes:
            for f in ('purchase_id', 'purchase_fiscal_id'):
                pid = _m2o_id(d.get(f))
                if pid:
                    po_ids.add(pid)

        _progress(55, f'Buscando POs destino ({len(po_ids)})')
        po_data = NfTransferenciaService._buscar_pos(odoo, list(po_ids))

        all_picking_ids: List[int] = []
        all_invoice_ids: List[int] = []
        for po in po_data.values():
            all_picking_ids.extend(po.get('picking_ids') or [])
            all_invoice_ids.extend(po.get('invoice_ids') or [])

        _progress(65, 'Buscando pickings + invoices destino')
        pickings = (NfTransferenciaService._buscar_pickings(odoo, all_picking_ids)
                    if all_picking_ids else {})
        invoices_dest = (NfTransferenciaService._buscar_invoices_destino(
            odoo, all_invoice_ids) if all_invoice_ids else {})

        _progress(80, 'Buscando linhas das NFs')
        all_line_ids: List[int] = []
        for m in moves:
            all_line_ids.extend(m.get('invoice_line_ids') or [])
        linhas_por_move = NfTransferenciaService._buscar_linhas(odoo, all_line_ids)

        _progress(90, 'Gravando snapshot local')
        NfTransferenciaService._wipe_snapshot()
        agora = agora_utc_naive()

        contadores = {s: 0 for s in STATUS_TODOS}

        for move in moves:
            registro = NfTransferenciaService._montar_registro(
                move, dfe_by_chave, po_data, pickings, invoices_dest,
                linhas_por_move, agora, usuario,
            )
            db.session.add(registro)
            db.session.flush()  # garante id para FK dos produtos

            for linha in linhas_por_move.get(move['id'], []):
                if not linha.get('cod_produto'):
                    continue  # ignora linhas sem produto (impostos)
                produto = NfTransferenciaProdutoSnapshot(
                    nf_snapshot_id=registro.id,
                    cod_produto=_norm_str(linha.get('cod_produto'), 50) or '',
                    nome_produto=_norm_str(linha.get('nome_produto'), 200),
                    quantidade=Decimal(str(linha.get('quantidade') or 0)),
                    valor_unit=(Decimal(str(linha.get('valor_unit')))
                                if linha.get('valor_unit') is not None else None),
                    valor_total=Decimal(str(linha.get('valor_total') or 0)),
                    cfop=_norm_str(linha.get('cfop'), 5),
                    lote_nome=_norm_str(linha.get('lote_nome'), 100),
                )
                db.session.add(produto)

            contadores[registro.status_consolidado] = (
                contadores.get(registro.status_consolidado, 0) + 1
            )

        db.session.flush()  # commit fica para o caller (route/worker)
        _progress(100, 'Concluido')

        return {
            'total': sum(contadores.values()),
            'pendentes': sum(contadores[s] for s in STATUS_PENDENTES),
            'concluidos': contadores['CONCLUIDO'],
            'canceladas': contadores['CANCELADA'],
            'por_status': contadores,
            'refresh_em': agora.isoformat(),
        }

    # =====================================================================
    # WIPE
    # =====================================================================

    @staticmethod
    def _wipe_snapshot():
        """Limpa snapshot existente (DELETE+INSERT — CASCADE remove produtos)."""
        db.session.execute(delete(NfTransferenciaSnapshot))
        db.session.flush()

    # =====================================================================
    # ODOO FETCHES
    # =====================================================================

    @staticmethod
    def _buscar_nfs_origem(odoo, data_corte: str,
                            partners_grupo: List[int]) -> List[Dict]:
        """Busca account.move out_invoice inter-company (posted+cancel).

        Campos validados contra Odoo CIEL IT (2026-05-28):
        - `l10n_br_chave_nf`        — chave NFe 44 digitos (fonte: reversao_service.py:207).
        - `l10n_br_numero_nota_fiscal` — numero formatado (fonte: faturamento_service.py:102).
        - Serie NAO tem equivalente direto em account.move (campo no DFe = nfe_infnfe_ide_serie).
        """
        domain = [
            ['move_type', '=', 'out_invoice'],
            ['state', 'in', ['posted', 'cancel']],
            ['partner_id', 'in', partners_grupo],
            ['invoice_date', '>=', data_corte],
        ]
        ids = odoo.search('account.move', domain)
        if not ids:
            return []
        fields = [
            'id', 'name', 'state', 'invoice_date', 'amount_total',
            'l10n_br_chave_nf', 'l10n_br_numero_nota_fiscal',
            'company_id', 'partner_id',
            'l10n_br_tipo_pedido', 'fiscal_position_id', 'invoice_line_ids',
            # `create_date` = timestamp da criacao do account.move
            # (proxy seguro para "horario de emissao"; UTC naive).
            'create_date',
        ]
        moves: List[Dict] = []
        for i in range(0, len(ids), ODOO_BATCH):
            moves.extend(odoo.read('account.move', ids[i:i + ODOO_BATCH], fields))
        return moves

    @staticmethod
    def _buscar_dfes_destino(odoo, chaves: List[str]) -> List[Dict]:
        if not chaves:
            return []
        chaves_unicas = list({c for c in chaves if c})
        ids = odoo.search(
            'l10n_br_ciel_it_account.dfe',
            [['protnfe_infnfe_chnfe', 'in', chaves_unicas]],
        )
        if not ids:
            return []
        fields = [
            'id', 'name', 'l10n_br_status', 'l10n_br_situacao_dfe',
            'protnfe_infnfe_chnfe', 'purchase_id', 'purchase_fiscal_id',
            'company_id',
        ]
        dfes: List[Dict] = []
        for i in range(0, len(ids), ODOO_BATCH):
            dfes.extend(odoo.read(
                'l10n_br_ciel_it_account.dfe', ids[i:i + ODOO_BATCH], fields,
            ))
        return dfes

    @staticmethod
    def _buscar_pos(odoo, po_ids: List[int]) -> Dict[int, Dict]:
        if not po_ids:
            return {}
        unique = list(set(po_ids))
        out: Dict[int, Dict] = {}
        fields = ['id', 'name', 'state', 'picking_ids', 'invoice_ids']
        for i in range(0, len(unique), ODOO_BATCH):
            for po in odoo.read('purchase.order', unique[i:i + ODOO_BATCH], fields):
                out[po['id']] = {
                    'name': po.get('name'),
                    'state': po.get('state'),
                    'picking_ids': po.get('picking_ids') or [],
                    'invoice_ids': po.get('invoice_ids') or [],
                }
        return out

    @staticmethod
    def _buscar_pickings(odoo, picking_ids: List[int]) -> Dict[int, Dict]:
        if not picking_ids:
            return {}
        unique = list(set(picking_ids))
        out: Dict[int, Dict] = {}
        for i in range(0, len(unique), ODOO_BATCH):
            # `date_done` = timestamp da validacao do picking (UTC naive
            # quando state='done'; None se ainda em assigned/draft).
            for p in odoo.read('stock.picking', unique[i:i + ODOO_BATCH],
                                ['id', 'name', 'state', 'date_done']):
                out[p['id']] = p
        return out

    @staticmethod
    def _buscar_invoices_destino(odoo, invoice_ids: List[int]) -> Dict[int, Dict]:
        if not invoice_ids:
            return {}
        unique = list(set(invoice_ids))
        out: Dict[int, Dict] = {}
        for i in range(0, len(unique), ODOO_BATCH):
            # `create_date` = timestamp da criacao do invoice destino (UTC
            # naive). Proxy para "data+hora de escrituracao" do in_invoice.
            for inv in odoo.read('account.move', unique[i:i + ODOO_BATCH],
                                  ['id', 'name', 'state', 'move_type',
                                   'create_date']):
                if inv.get('move_type') in ('in_invoice', 'in_refund'):
                    out[inv['id']] = inv
        return out

    @staticmethod
    def _buscar_linhas(odoo, line_ids: List[int]) -> Dict[int, List[Dict]]:
        """Busca account.move.line + product.product (cod_produto) em batch.

        NOTA (C1 do code review 2026-05-28): lote NAO eh extraido aqui. NF de
        saida no Odoo CIEL IT nao expoe lote diretamente em `account.move.line`.
        Para puxar lote precisaria cruzar com stock.move.line do picking de
        SAIDA (account.move.invoice_origin -> stock.picking -> stock.move.line
        -> lot_id) — chain custosa. Por enquanto o campo `lote_nome` no
        snapshot fica NULL e a coluna foi REMOVIDA do template; campo
        permanece no schema para futura implementacao se necessario.
        """
        if not line_ids:
            return {}
        unique = list(set(line_ids))
        out: Dict[int, List[Dict]] = defaultdict(list)
        # `l10n_br_cfop_id` em account.move.line eh many2one (retorna [id, name]).
        # Precedente: pedidos/workers/impostos_jobs.py:311 (`l10n_br_cfop_id` em
        # purchase.order) — mesmo campo herdado pelas linhas Brazil.
        fields = [
            'id', 'move_id', 'product_id', 'quantity',
            'price_unit', 'price_subtotal', 'l10n_br_cfop_id',
        ]
        for i in range(0, len(unique), ODOO_BATCH):
            for ln in odoo.read('account.move.line', unique[i:i + ODOO_BATCH], fields):
                move_id = _m2o_id(ln.get('move_id'))
                pid = _m2o_id(ln.get('product_id'))
                if not move_id or not pid:
                    continue
                out[move_id].append({
                    'product_id': pid,
                    'product_name': _m2o_name(ln.get('product_id')),
                    'quantidade': ln.get('quantity'),
                    'valor_unit': ln.get('price_unit'),
                    'valor_total': ln.get('price_subtotal'),
                    'cfop': _m2o_name(ln.get('l10n_br_cfop_id')) or None,
                })

        # Buscar cod_produto via product.product em batch
        all_pids = list({l['product_id'] for ls in out.values() for l in ls})
        cod_by_pid: Dict[int, Dict[str, str]] = {}
        if all_pids:
            for i in range(0, len(all_pids), ODOO_BATCH):
                for p in odoo.read('product.product', all_pids[i:i + ODOO_BATCH],
                                    ['id', 'default_code', 'name']):
                    cod_by_pid[p['id']] = {
                        'cod': str(p.get('default_code') or '').strip(),
                        'nome': p.get('name') or '',
                    }
        for ls in out.values():
            for l in ls:
                info = cod_by_pid.get(l['product_id'], {})
                l['cod_produto'] = info.get('cod') or None
                l['nome_produto'] = info.get('nome') or l.get('product_name')
        return dict(out)

    # =====================================================================
    # MONTAGEM DE REGISTRO
    # =====================================================================

    @staticmethod
    def _montar_registro(move, dfe_by_chave, po_data, pickings, invoices_dest,
                          linhas_por_move, agora, usuario) -> NfTransferenciaSnapshot:
        chave = move.get('l10n_br_chave_nf') or ''
        company_origem_id = _m2o_id(move.get('company_id'))
        partner_id = _m2o_id(move.get('partner_id'))

        company_origem = COMPANY_NAME.get(company_origem_id, '?')
        company_destino_id = PARTNER_TO_COMPANY.get(partner_id)
        company_destino = COMPANY_NAME.get(company_destino_id, '?')

        tipo_pedido = move.get('l10n_br_tipo_pedido') or ''
        acao = DIRECAO_PARA_ACAO.get(
            (company_origem_id, company_destino_id, tipo_pedido), ''
        )

        # CFOP saida: primeira linha com cod_produto (linhas de imposto nao contam)
        cfop_saida = None
        for ln in linhas_por_move.get(move['id'], []):
            if ln.get('cod_produto') and ln.get('cfop'):
                cfop_saida = ln.get('cfop')
                break

        state_nf = move.get('state') or ''

        # DFe destino
        dfe = dfe_by_chave.get(chave) if chave else None
        dfe_id = dfe.get('id') if dfe else None
        dfe_name = dfe.get('name') if dfe else None
        dfe_status = dfe.get('l10n_br_status') if dfe else None  # 01-07
        dfe_situacao = dfe.get('l10n_br_situacao_dfe') if dfe else None
        if dfe_situacao is False:
            dfe_situacao = None

        # Picking + Invoice destino — pega o primeiro disponivel
        picking_id = picking_name = picking_state = None
        picking_data_hora = None
        invoice_destino_id = invoice_destino_name = invoice_destino_state = None
        invoice_destino_data_hora = None

        if dfe:
            for f in ('purchase_fiscal_id', 'purchase_id'):
                po_id = _m2o_id(dfe.get(f))
                if not po_id:
                    continue
                po = po_data.get(po_id)
                if not po:
                    continue
                if picking_id is None:
                    for pid in po.get('picking_ids') or []:
                        if pid in pickings:
                            p = pickings[pid]
                            picking_id = p['id']
                            picking_name = p.get('name')
                            picking_state = p.get('state')
                            picking_data_hora = _parse_odoo_dt(p.get('date_done'))
                            break
                if invoice_destino_id is None:
                    for iid in po.get('invoice_ids') or []:
                        if iid in invoices_dest:
                            inv = invoices_dest[iid]
                            invoice_destino_id = inv['id']
                            invoice_destino_name = inv.get('name')
                            invoice_destino_state = inv.get('state')
                            invoice_destino_data_hora = _parse_odoo_dt(
                                inv.get('create_date')
                            )
                            break
                if picking_id and invoice_destino_id:
                    break

        status = NfTransferenciaService._consolidar_status(
            state_nf, dfe, picking_state, invoice_destino_state,
        )

        return NfTransferenciaSnapshot(
            refresh_em=agora,
            refreshed_por=usuario,
            chave_nfe=_norm_str(chave, 50),
            numero_nf=_norm_str(move.get('l10n_br_numero_nota_fiscal'), 20),
            # serie_nf: account.move CIEL IT nao expoe campo equivalente direto.
            # Permanece NULL — coluna mantida no schema para uso futuro se Odoo
            # adicionar campo (workaround: extrair via DFe.nfe_infnfe_ide_serie
            # se necessario para auditoria fiscal).
            serie_nf=None,
            account_move_id_origem=move['id'],
            account_move_name_origem=_norm_str(move.get('name'), 50),
            company_origem=company_origem[:5],
            company_destino=company_destino[:5],
            partner_origem_id=None,
            partner_destino_id=partner_id,
            data_emissao=move.get('invoice_date') or None,
            data_emissao_hora=_parse_odoo_dt(move.get('create_date')),
            valor_total=Decimal(str(move.get('amount_total') or 0)),
            acao=_norm_str(acao, 30),
            cfop_saida=_norm_str(cfop_saida, 5),
            state_nf_origem=_norm_str(state_nf, 20),
            dfe_id=dfe_id,
            dfe_name=_norm_str(dfe_name, 50),
            dfe_state=_norm_str(dfe_status, 30),
            dfe_situacao=_norm_str(dfe_situacao, 50),
            picking_id=picking_id,
            picking_name=_norm_str(picking_name, 50),
            picking_state=_norm_str(picking_state, 30),
            picking_data_hora=picking_data_hora,
            invoice_destino_id=invoice_destino_id,
            invoice_destino_name=_norm_str(invoice_destino_name, 50),
            invoice_destino_state=_norm_str(invoice_destino_state, 30),
            invoice_destino_data_hora=invoice_destino_data_hora,
            status_consolidado=status,
        )

    @staticmethod
    def _consolidar_status(state_nf, dfe, picking_state, invoice_destino_state) -> str:
        if state_nf == 'cancel':
            return 'CANCELADA'
        if not dfe:
            return 'PENDENTE_DFE'
        if picking_state != 'done':
            return 'PENDENTE_PICKING'
        if invoice_destino_state != 'posted':
            return 'PENDENTE_INVOICE'
        return 'CONCLUIDO'

    # =====================================================================
    # AGREGACAO PARA INVENTARIO (em_transito_*)
    # =====================================================================

    @staticmethod
    def agregar_em_transito_por_destino() -> Dict[str, Dict[str, Any]]:
        """
        Agrega produtos de NFs PENDENTES (nao CONCLUIDO/CANCELADA) por
        (cod_produto, company_destino). Usado pelo SnapshotOdooService
        para gravar em em_transito_fb/cd/lf no inventario_snapshot_odoo.

        Returns:
            {cod_produto: {'fb': Decimal, 'cd': Decimal, 'lf': Decimal, 'nome': str}}
        """
        # EXCLUSOES do calculo em_transito_*:
        # 1. NFs flagadas como "ja ajustadas no estoque" (Desconsiderada)
        #    -> LEFT JOIN + filter desconsiderada.id IS NULL
        # 2. Linhas de RETORNO DE INSUMO em industrializacao (CFOPs 5902/
        #    5903/6902/6903) -> insumos foram consumidos, so o produto
        #    acabado existe no destino. Filtra por TRIM(cfop) pois snapshot
        #    grava CFOP com espaco extra ('5902 ' vs '5902').
        rows = (
            db.session.query(
                NfTransferenciaProdutoSnapshot.cod_produto,
                sa_func.max(NfTransferenciaProdutoSnapshot.nome_produto),
                NfTransferenciaSnapshot.company_destino,
                sa_func.sum(NfTransferenciaProdutoSnapshot.quantidade),
            )
            .join(NfTransferenciaSnapshot,
                  NfTransferenciaSnapshot.id ==
                  NfTransferenciaProdutoSnapshot.nf_snapshot_id)
            .outerjoin(
                NfTransferenciaDesconsiderada,
                NfTransferenciaDesconsiderada.account_move_id_origem ==
                NfTransferenciaSnapshot.account_move_id_origem,
            )
            .filter(NfTransferenciaSnapshot.status_consolidado.in_(STATUS_PENDENTES))
            .filter(NfTransferenciaDesconsiderada.id.is_(None))  # exclui flagadas
            .filter(
                sa_func.coalesce(
                    sa_func.trim(NfTransferenciaProdutoSnapshot.cfop), ''
                ).notin_(CFOPS_RETORNO_INSUMO_INDUSTRIALIZACAO)
            )
            .group_by(
                NfTransferenciaProdutoSnapshot.cod_produto,
                NfTransferenciaSnapshot.company_destino,
            )
            .all()
        )

        out: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'fb': Decimal('0'), 'cd': Decimal('0'),
                     'lf': Decimal('0'), 'nome': ''}
        )
        for cod, nome, dest, qtd in rows:
            if not cod:
                continue
            key = (dest or '').lower()
            if key in ('fb', 'cd', 'lf'):
                out[cod][key] = (out[cod][key] or Decimal('0')) + Decimal(str(qtd or 0))
            if nome and not out[cod]['nome']:
                out[cod]['nome'] = nome
        return dict(out)
