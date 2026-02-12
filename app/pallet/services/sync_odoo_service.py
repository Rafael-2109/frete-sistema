"""
Servico de sincronizacao de movimentacoes de pallet com Odoo

Este servico importa:
1. NFs de remessa de pallet (l10n_br_tipo_pedido = 'vasilhame') -> tipo_movimentacao = 'REMESSA'
2. NFs de venda de pallet (cod_produto = '208000012') -> tipo_movimentacao = 'SAIDA'
3. NFs de retorno/entrada de pallet -> tipo_movimentacao = 'ENTRADA'

INTEGRAÇÃO COM NOVOS MODELS (v2):
- Ao criar MovimentacaoEstoque de REMESSA, também cria:
  - PalletNFRemessa (via NFService.importar_nf_remessa_odoo)
  - PalletCredito (criado automaticamente pelo NFService)

OTIMIZACOES (v2.1):
- Batch fetch de partners: 1 chamada XML-RPC em vez de N
- Batch fetch de move.lines: 1-2 chamadas em vez de N
- Cache de buscar_tipo_destinatario: dict O(1) em vez de queries por NF
- Batch commit: commit a cada BATCH_SIZE em vez de 1 por NF
- Set de NFs existentes: 1 query local em vez de N

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
import logging
import time
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.utils.timezone import agora_utc_naive
from app.estoque.models import MovimentacaoEstoque
from app.pallet.services.nf_service import NFService
from app.pallet.services.match_service import MatchService

logger = logging.getLogger(__name__)

# Tamanho do batch para commits
BATCH_SIZE = 50

# Constantes
COD_PRODUTO_PALLET = '208000012'
NOME_PRODUTO_PALLET = 'PALLET'
# Prazo de cobranca agora e calculado dinamicamente em app/pallet/utils.py
# SP/RED = 7 dias, outros = 30 dias

# CNPJs intercompany (Nacom e La Famiglia) - NFs para esses destinos nao sao controladas
# Usa prefixo (raiz do CNPJ - 8 primeiros digitos) para pegar todas as filiais
CNPJS_INTERCOMPANY_PREFIXOS = [
    '61724241',  # Nacom Goya (matriz e filiais)
    '18467441',  # La Famiglia
]

# Mapeamento de company_id do Odoo para codigo de empresa
COMPANY_ID_TO_EMPRESA = {
    4: 'CD',  # NACOM GOYA - CD
    1: 'FB',  # NACOM GOYA - FB
    3: 'SC',  # NACOM GOYA - SC
}


class PalletSyncService:
    """Servico para sincronizar movimentacoes de pallet do Odoo"""

    def __init__(self, odoo_client=None):
        """
        Inicializa o servico com cliente Odoo

        Args:
            odoo_client: Cliente XML-RPC do Odoo configurado (opcional)
                         Se nao informado, cria conexao automaticamente
        """
        if odoo_client:
            self.odoo = odoo_client
        else:
            from app.odoo.utils.connection import get_odoo_connection
            self.odoo = get_odoo_connection()

    def sincronizar_remessas(self, dias_retroativos=30, data_de=None, data_ate=None):
        """
        Importa NFs de remessa de pallet (l10n_br_tipo_pedido = 'vasilhame')

        OTIMIZADO v2.1: batch fetch de partners, lines, cache destinatario, batch commit.

        Args:
            dias_retroativos: Quantos dias para tras buscar (ignorado se data_de informado)
            data_de: Data inicial absoluta (formato YYYY-MM-DD)
            data_ate: Data final absoluta (formato YYYY-MM-DD)

        Returns:
            dict: Resumo da sincronizacao
        """
        if data_de:
            data_corte = data_de
            logger.info(f"🔄 Iniciando sincronizacao de remessas de pallet (periodo: {data_de} a {data_ate or 'hoje'})")
        else:
            data_corte = (agora_utc_naive() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')
            logger.info(f"🔄 Iniciando sincronizacao de remessas de pallet (ultimos {dias_retroativos} dias)")

        t_inicio = time.time()
        resumo = {
            'processados': 0,
            'novos': 0,
            'ja_existentes': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar NFs de vasilhame no Odoo
            domain = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('l10n_br_tipo_pedido', '=', 'vasilhame'),
                ('invoice_date', '>=', data_corte)
            ]
            if data_ate:
                domain.append(('invoice_date', '<=', data_ate))

            campos = [
                'id', 'name', 'invoice_date', 'partner_id',
                'l10n_br_numero_nota_fiscal', 'l10n_br_tipo_pedido',
                'amount_total', 'invoice_line_ids', 'company_id',
                'l10n_br_chave_nf'
            ]

            nfs = self.odoo.search_read('account.move', domain, campos)
            logger.info(f"   📦 Encontradas {len(nfs)} NFs de vasilhame")

            if not nfs:
                return resumo

            # ============================================================
            # BATCH PRE-FETCH: Partners (1 chamada em vez de N)
            # ============================================================
            all_partner_ids = set()
            for nf in nfs:
                p = nf.get('partner_id', [])
                pid = p[0] if isinstance(p, (list, tuple)) else p
                if pid:
                    all_partner_ids.add(pid)

            partners_cache = {}
            if all_partner_ids:
                partners_data = self.odoo.search_read(
                    'res.partner',
                    [('id', 'in', list(all_partner_ids))],
                    ['id', 'l10n_br_cnpj', 'name', 'company_type']
                )
                for p in partners_data:
                    partners_cache[p['id']] = p
            logger.info(f"   👥 {len(partners_cache)} partners carregados em batch")

            # ============================================================
            # BATCH PRE-FETCH: Move Lines (chunks de 200 em vez de N)
            # ============================================================
            all_line_ids = []
            for nf in nfs:
                all_line_ids.extend(nf.get('invoice_line_ids', []))

            lines_cache = {}  # {move_id: [linhas]}
            if all_line_ids:
                for i in range(0, len(all_line_ids), 200):
                    chunk = all_line_ids[i:i + 200]
                    linhas = self.odoo.search_read(
                        'account.move.line',
                        [('id', 'in', chunk), ('product_id', '!=', False)],
                        ['id', 'quantity', 'product_id', 'move_id']
                    )
                    for l in linhas:
                        move = l.get('move_id')
                        move_id = move[0] if isinstance(move, (list, tuple)) else move
                        lines_cache.setdefault(move_id, []).append(l)
            logger.info(f"   📋 {len(all_line_ids)} linhas carregadas em batch ({len(lines_cache)} moves)")

            # ============================================================
            # SET DE NFs EXISTENTES (1 query local em vez de N)
            # ============================================================
            nfs_existentes = set(
                r.numero_nf for r in
                MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.local_movimentacao == 'PALLET',
                    MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
                    MovimentacaoEstoque.ativo == True
                ).with_entities(MovimentacaoEstoque.numero_nf).all()
            )
            logger.info(f"   🗃️ {len(nfs_existentes)} NFs existentes pre-carregadas")

            # ============================================================
            # CACHE DE TIPO DESTINATARIO
            # ============================================================
            from app.pallet.utils import buscar_tipo_destinatario_batch

            # ============================================================
            # PROCESSAR NFs
            # ============================================================
            batch_count = 0
            for nf in nfs:
                try:
                    resumo['processados'] += 1
                    numero_nf = str(nf.get('l10n_br_numero_nota_fiscal', ''))

                    if not numero_nf:
                        logger.warning(f"   ⚠️ NF sem numero: {nf.get('name')}")
                        continue

                    # Skip rapido via set (em vez de query individual)
                    if numero_nf in nfs_existentes:
                        resumo['ja_existentes'] += 1
                        continue

                    # Quantidade via cache de lines
                    linhas_nf = lines_cache.get(nf.get('id'), [])
                    quantidade_total = sum(l.get('quantity', 0) for l in linhas_nf)
                    if quantidade_total == 0:
                        quantidade_total = 1  # Fallback

                    # Dados do parceiro via cache
                    partner = nf.get('partner_id', [])
                    partner_id = partner[0] if isinstance(partner, (list, tuple)) else partner
                    partner_nome = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''

                    cnpj_destinatario = ''
                    if partner_id and partner_id in partners_cache:
                        p_data = partners_cache[partner_id]
                        cnpj_destinatario = (p_data.get('l10n_br_cnpj', '') or '').replace('.', '').replace('-', '').replace('/', '')

                    # Tipo destinatario via cache batch
                    tipo_destinatario, _, _ = buscar_tipo_destinatario_batch(cnpj_destinatario)

                    # Pular NFs intercompany
                    prefixo_cnpj = cnpj_destinatario[:8] if cnpj_destinatario else ''
                    if prefixo_cnpj in CNPJS_INTERCOMPANY_PREFIXOS:
                        logger.debug(f"   ⏭️ NF {numero_nf} ignorada (intercompany: {partner_nome})")
                        continue

                    # Data da NF
                    data_nf = nf.get('invoice_date')
                    if isinstance(data_nf, str):
                        data_nf = datetime.strptime(data_nf, '%Y-%m-%d').date()
                    elif not data_nf:
                        data_nf = date.today()

                    # Empresa pelo company_id
                    company_data = nf.get('company_id', [])
                    company_id = company_data[0] if isinstance(company_data, (list, tuple)) else company_data
                    empresa = COMPANY_ID_TO_EMPRESA.get(company_id, 'CD')

                    chave_nfe = nf.get('l10n_br_chave_nf', '') or ''

                    # Criar movimentacao (sistema legado)
                    movimento = MovimentacaoEstoque(
                        cod_produto=COD_PRODUTO_PALLET,
                        nome_produto=NOME_PRODUTO_PALLET,
                        data_movimentacao=data_nf,
                        tipo_movimentacao='REMESSA',
                        local_movimentacao='PALLET',
                        qtd_movimentacao=int(quantidade_total),
                        numero_nf=numero_nf,
                        tipo_origem='ODOO',
                        status_nf='FATURADO',
                        tipo_destinatario=tipo_destinatario,
                        cnpj_destinatario=cnpj_destinatario,
                        nome_destinatario=partner_nome,
                        baixado=False,
                        observacao=f'Remessa de pallet - NF {numero_nf}',
                        criado_por='SYNC_ODOO'
                    )

                    db.session.add(movimento)
                    db.session.flush()

                    # Integracao com novos models v2
                    try:
                        odoo_move_id = nf.get('id')
                        dados_nf_remessa = {
                            'numero_nf': numero_nf,
                            'chave_nfe': chave_nfe if chave_nfe else None,
                            'data_emissao': datetime.combine(data_nf, datetime.min.time()) if isinstance(data_nf, date) else data_nf,
                            'quantidade': int(quantidade_total),
                            'empresa': empresa,
                            'tipo_destinatario': tipo_destinatario,
                            'cnpj_destinatario': cnpj_destinatario,
                            'nome_destinatario': partner_nome,
                            'valor_unitario': Decimal('35.00'),
                            'odoo_account_move_id': odoo_move_id,
                            'movimentacao_estoque_id': movimento.id,
                            'observacao': f'Importado automaticamente do Odoo (account.move #{odoo_move_id})'
                        }
                        nf_remessa = NFService.importar_nf_remessa_odoo(
                            dados_odoo=dados_nf_remessa,
                            usuario='SYNC_ODOO'
                        )
                        logger.debug(f"      ↳ PalletNFRemessa #{nf_remessa.id} criada")
                    except Exception as e_v2:
                        logger.warning(
                            f"      ⚠️ Erro ao criar PalletNFRemessa para NF {numero_nf}: {e_v2}. "
                            "MovimentacaoEstoque criada normalmente."
                        )

                    # Batch commit
                    batch_count += 1
                    if batch_count % BATCH_SIZE == 0:
                        db.session.commit()
                        logger.info(f"   💾 Commit batch ({batch_count} processados)")

                    # Registrar no set para evitar duplicatas no mesmo batch
                    nfs_existentes.add(numero_nf)

                    resumo['novos'] += 1
                    resumo['detalhes'].append({
                        'nf': numero_nf,
                        'destinatario': partner_nome,
                        'quantidade': int(quantidade_total),
                        'tipo': tipo_destinatario,
                        'empresa': empresa
                    })

                    logger.info(f"   ✅ NF {numero_nf}: {int(quantidade_total)} pallets -> {partner_nome} ({empresa})")

                except Exception as e:
                    resumo['erros'] += 1
                    logger.error(f"   ❌ Erro ao processar NF: {e}")
                    db.session.rollback()
                    continue

            # Commit final dos restantes
            if batch_count % BATCH_SIZE != 0:
                db.session.commit()

            elapsed = time.time() - t_inicio
            logger.info(f"✅ Sincronizacao concluida em {elapsed:.1f}s: {resumo['novos']} novos, {resumo['ja_existentes']} existentes, {resumo['erros']} erros")

        except Exception as e:
            logger.error(f"❌ Erro na sincronizacao de remessas: {e}")
            resumo['erro_geral'] = str(e)

        return resumo

    def sincronizar_vendas_pallet(self, dias_retroativos=30, data_de=None, data_ate=None):
        """
        Importa NFs de venda de pallet (cod_produto = '208000012')

        OTIMIZADO v2.1: batch fetch de moves e partners.

        Args:
            dias_retroativos: Quantos dias para tras buscar (ignorado se data_de informado)
            data_de: Data inicial absoluta (formato YYYY-MM-DD)
            data_ate: Data final absoluta (formato YYYY-MM-DD)

        Returns:
            dict: Resumo da sincronizacao
        """
        if data_de:
            data_corte = data_de
            logger.info(f"🔄 Iniciando sincronizacao de vendas de pallet (periodo: {data_de} a {data_ate or 'hoje'})")
        else:
            data_corte = (agora_utc_naive() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')
            logger.info(f"🔄 Iniciando sincronizacao de vendas de pallet (ultimos {dias_retroativos} dias)")

        t_inicio = time.time()
        resumo = {
            'processados': 0,
            'novos': 0,
            'ja_existentes': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar produto PALLET no Odoo
            produtos = self.odoo.search_read(
                'product.product',
                [('default_code', '=', COD_PRODUTO_PALLET)],
                ['id', 'name']
            )

            if not produtos:
                logger.warning(f"   ⚠️ Produto {COD_PRODUTO_PALLET} nao encontrado no Odoo")
                return resumo

            produto_id = produtos[0]['id']
            logger.info(f"   📦 Produto PALLET encontrado: ID {produto_id}")

            # Buscar linhas de NF com esse produto
            domain = [
                ('product_id', '=', produto_id),
                ('move_id.move_type', 'in', ['out_invoice']),
                ('move_id.state', '=', 'posted'),
                ('move_id.invoice_date', '>=', data_corte)
            ]
            if data_ate:
                domain.append(('move_id.invoice_date', '<=', data_ate))

            campos = [
                'id', 'move_id', 'product_id', 'quantity', 'price_total', 'partner_id'
            ]

            linhas = self.odoo.search_read('account.move.line', domain, campos)
            logger.info(f"   📦 Encontradas {len(linhas)} linhas de venda de pallet")

            if not linhas:
                return resumo

            # ============================================================
            # BATCH PRE-FETCH: Moves pais (1 chamada em vez de N)
            # ============================================================
            all_move_ids = set()
            for linha in linhas:
                m = linha.get('move_id', [])
                mid = m[0] if isinstance(m, (list, tuple)) else m
                if mid:
                    all_move_ids.add(mid)

            moves_cache = {}
            if all_move_ids:
                moves_data = self.odoo.search_read(
                    'account.move',
                    [('id', 'in', list(all_move_ids))],
                    ['id', 'l10n_br_numero_nota_fiscal', 'invoice_date', 'partner_id', 'l10n_br_tipo_pedido']
                )
                for m in moves_data:
                    moves_cache[m['id']] = m
            logger.info(f"   📄 {len(moves_cache)} moves carregados em batch")

            # BATCH PRE-FETCH: Partners
            all_partner_ids = set()
            for m in moves_cache.values():
                p = m.get('partner_id', [])
                pid = p[0] if isinstance(p, (list, tuple)) else p
                if pid:
                    all_partner_ids.add(pid)

            partners_cache = {}
            if all_partner_ids:
                partners_data = self.odoo.search_read(
                    'res.partner',
                    [('id', 'in', list(all_partner_ids))],
                    ['id', 'l10n_br_cnpj']
                )
                for p in partners_data:
                    partners_cache[p['id']] = p

            # SET de NFs existentes
            nfs_existentes = set(
                r.numero_nf for r in
                MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.local_movimentacao == 'PALLET',
                    MovimentacaoEstoque.tipo_movimentacao == 'SAIDA',
                    MovimentacaoEstoque.ativo == True
                ).with_entities(MovimentacaoEstoque.numero_nf).all()
            )

            # ============================================================
            # PROCESSAR
            # ============================================================
            batch_count = 0
            for linha in linhas:
                try:
                    resumo['processados'] += 1

                    move_data = linha.get('move_id', [])
                    move_id = move_data[0] if isinstance(move_data, (list, tuple)) else move_data

                    nf_data = moves_cache.get(move_id)
                    if not nf_data:
                        continue

                    # Pular NFs de vasilhame (ja importadas como REMESSA)
                    if nf_data.get('l10n_br_tipo_pedido') == 'vasilhame':
                        continue

                    numero_nf = str(nf_data.get('l10n_br_numero_nota_fiscal', ''))
                    if not numero_nf:
                        continue

                    if numero_nf in nfs_existentes:
                        resumo['ja_existentes'] += 1
                        continue

                    # Dados do parceiro via cache
                    partner = nf_data.get('partner_id', [])
                    partner_id = partner[0] if isinstance(partner, (list, tuple)) else partner
                    partner_nome = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''

                    cnpj = ''
                    if partner_id and partner_id in partners_cache:
                        cnpj = (partners_cache[partner_id].get('l10n_br_cnpj', '') or '').replace('.', '').replace('-', '').replace('/', '')

                    # Pular NFs intercompany
                    prefixo_cnpj = cnpj[:8] if cnpj else ''
                    if prefixo_cnpj in CNPJS_INTERCOMPANY_PREFIXOS:
                        logger.debug(f"   ⏭️ Venda NF {numero_nf} ignorada (intercompany: {partner_nome})")
                        continue

                    data_nf = nf_data.get('invoice_date')
                    if isinstance(data_nf, str):
                        data_nf = datetime.strptime(data_nf, '%Y-%m-%d').date()
                    elif not data_nf:
                        data_nf = date.today()

                    quantidade = int(linha.get('quantity', 0))
                    valor = float(linha.get('price_total', 0))

                    movimento = MovimentacaoEstoque(
                        cod_produto=COD_PRODUTO_PALLET,
                        nome_produto=NOME_PRODUTO_PALLET,
                        data_movimentacao=data_nf,
                        tipo_movimentacao='SAIDA',
                        local_movimentacao='PALLET',
                        qtd_movimentacao=quantidade,
                        numero_nf=numero_nf,
                        tipo_origem='ODOO',
                        status_nf='FATURADO',
                        tipo_destinatario='CLIENTE',
                        cnpj_destinatario=cnpj,
                        nome_destinatario=partner_nome,
                        baixado=False,
                        observacao=f'Venda de pallet - NF {numero_nf} - R$ {valor:.2f}',
                        criado_por='SYNC_ODOO'
                    )

                    db.session.add(movimento)
                    nfs_existentes.add(numero_nf)

                    batch_count += 1
                    if batch_count % BATCH_SIZE == 0:
                        db.session.commit()

                    resumo['novos'] += 1
                    resumo['detalhes'].append({
                        'nf': numero_nf,
                        'comprador': partner_nome,
                        'quantidade': quantidade,
                        'valor': valor
                    })

                    logger.info(f"   ✅ Venda NF {numero_nf}: {quantidade} pallets -> {partner_nome} (R$ {valor:.2f})")

                except Exception as e:
                    resumo['erros'] += 1
                    logger.error(f"   ❌ Erro ao processar linha: {e}")
                    db.session.rollback()
                    continue

            if batch_count % BATCH_SIZE != 0:
                db.session.commit()

            elapsed = time.time() - t_inicio
            logger.info(f"✅ Sincronizacao de vendas concluida em {elapsed:.1f}s: {resumo['novos']} novos, {resumo['ja_existentes']} existentes")

        except Exception as e:
            logger.error(f"❌ Erro na sincronizacao de vendas: {e}")
            resumo['erro_geral'] = str(e)

        return resumo

    def sincronizar_devolucoes(self, dias_retroativos=30, data_de=None, data_ate=None):
        """
        Importa NFs de devolucao de pallet (NFs de entrada que referenciam remessas de pallet)

        OTIMIZADO v2.1: batch fetch de partners, lines, reversed entries, batch commit.

        Devolucoes ocorrem quando:
        - Cliente emite NF de devolucao referenciando NF de remessa
        - NF de entrada do tipo refund que referencia NF de vasilhame

        Args:
            dias_retroativos: Quantos dias para tras buscar (ignorado se data_de informado)
            data_de: Data inicial absoluta (formato YYYY-MM-DD)
            data_ate: Data final absoluta (formato YYYY-MM-DD)

        Returns:
            dict: Resumo da sincronizacao
        """
        if data_de:
            data_corte = data_de
            logger.info(f"🔄 Iniciando sincronizacao de devolucoes de pallet (periodo: {data_de} a {data_ate or 'hoje'})")
        else:
            data_corte = (agora_utc_naive() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')
            logger.info(f"🔄 Iniciando sincronizacao de devolucoes de pallet (ultimos {dias_retroativos} dias)")

        t_inicio = time.time()
        resumo = {
            'processados': 0,
            'novos': 0,
            'ja_existentes': 0,
            'baixas_realizadas': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar NFs de devolucao/reembolso (entrada) no Odoo
            # Devolucoes de cliente sao out_refund (NF de saida negativa)
            domain = [
                ('move_type', '=', 'out_refund'),
                ('state', '=', 'posted'),
                ('l10n_br_tipo_pedido', '=', 'vasilhame'),
                ('invoice_date', '>=', data_corte)
            ]
            if data_ate:
                domain.append(('invoice_date', '<=', data_ate))

            campos = [
                'id', 'name', 'invoice_date', 'partner_id',
                'l10n_br_numero_nota_fiscal', 'l10n_br_tipo_pedido',
                'amount_total', 'invoice_line_ids', 'reversed_entry_id'
            ]

            nfs = self.odoo.search_read('account.move', domain, campos)
            logger.info(f"   📦 Encontradas {len(nfs)} NFs de devolucao de vasilhame")

            if not nfs:
                return resumo

            # ============================================================
            # BATCH PRE-FETCH: Partners (1 chamada em vez de N)
            # ============================================================
            all_partner_ids = set()
            for nf in nfs:
                p = nf.get('partner_id', [])
                pid = p[0] if isinstance(p, (list, tuple)) else p
                if pid:
                    all_partner_ids.add(pid)

            partners_cache = {}
            if all_partner_ids:
                partners_data = self.odoo.search_read(
                    'res.partner',
                    [('id', 'in', list(all_partner_ids))],
                    ['id', 'l10n_br_cnpj', 'name']
                )
                for p in partners_data:
                    partners_cache[p['id']] = p
            logger.info(f"   👥 {len(partners_cache)} partners carregados em batch")

            # ============================================================
            # BATCH PRE-FETCH: Move Lines (chunks de 200)
            # ============================================================
            all_line_ids = []
            for nf in nfs:
                all_line_ids.extend(nf.get('invoice_line_ids', []))

            lines_cache = {}  # {move_id: [linhas]}
            if all_line_ids:
                for i in range(0, len(all_line_ids), 200):
                    chunk = all_line_ids[i:i + 200]
                    linhas = self.odoo.search_read(
                        'account.move.line',
                        [('id', 'in', chunk), ('product_id', '!=', False)],
                        ['id', 'quantity', 'product_id', 'move_id']
                    )
                    for l in linhas:
                        move = l.get('move_id')
                        move_id = move[0] if isinstance(move, (list, tuple)) else move
                        lines_cache.setdefault(move_id, []).append(l)
            logger.info(f"   📋 {len(all_line_ids)} linhas carregadas em batch")

            # ============================================================
            # BATCH PRE-FETCH: Reversed entries (NFs originais)
            # ============================================================
            all_reversed_ids = set()
            for nf in nfs:
                rev = nf.get('reversed_entry_id', [])
                rev_id = rev[0] if isinstance(rev, (list, tuple)) else rev
                if rev_id:
                    all_reversed_ids.add(rev_id)

            reversed_cache = {}  # {move_id: numero_nf}
            if all_reversed_ids:
                reversed_data = self.odoo.search_read(
                    'account.move',
                    [('id', 'in', list(all_reversed_ids))],
                    ['id', 'l10n_br_numero_nota_fiscal']
                )
                for r in reversed_data:
                    num = str(r.get('l10n_br_numero_nota_fiscal', ''))
                    if num:
                        reversed_cache[r['id']] = num
            logger.info(f"   🔗 {len(reversed_cache)} reversed entries carregadas em batch")

            # ============================================================
            # SET DE NFs EXISTENTES (1 query local em vez de N)
            # ============================================================
            nfs_existentes = set(
                r.numero_nf for r in
                MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.local_movimentacao == 'PALLET',
                    MovimentacaoEstoque.tipo_movimentacao == 'DEVOLUCAO',
                    MovimentacaoEstoque.ativo == True
                ).with_entities(MovimentacaoEstoque.numero_nf).all()
            )
            logger.info(f"   🗃️ {len(nfs_existentes)} devolucoes existentes pre-carregadas")

            # ============================================================
            # PROCESSAR NFs
            # ============================================================
            batch_count = 0
            for nf in nfs:
                try:
                    resumo['processados'] += 1
                    numero_nf = str(nf.get('l10n_br_numero_nota_fiscal', ''))

                    if not numero_nf:
                        logger.warning(f"   ⚠️ NF de devolucao sem numero: {nf.get('name')}")
                        continue

                    # Skip rapido via set
                    if numero_nf in nfs_existentes:
                        resumo['ja_existentes'] += 1
                        continue

                    # Quantidade via cache de lines
                    linhas_nf = lines_cache.get(nf.get('id'), [])
                    quantidade_total = sum(abs(l.get('quantity', 0)) for l in linhas_nf)
                    if quantidade_total == 0:
                        quantidade_total = 1  # Fallback

                    # Dados do parceiro via cache
                    partner = nf.get('partner_id', [])
                    partner_id = partner[0] if isinstance(partner, (list, tuple)) else partner
                    partner_nome = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''

                    cnpj_destinatario = ''
                    if partner_id and partner_id in partners_cache:
                        cnpj_destinatario = (partners_cache[partner_id].get('l10n_br_cnpj', '') or '').replace('.', '').replace('-', '').replace('/', '')

                    # NF de remessa original via cache de reversed entries
                    nf_remessa_origem = None
                    reversed_entry = nf.get('reversed_entry_id', [])
                    if reversed_entry:
                        reversed_id = reversed_entry[0] if isinstance(reversed_entry, (list, tuple)) else reversed_entry
                        nf_remessa_origem = reversed_cache.get(reversed_id)

                    # Data da NF
                    data_nf = nf.get('invoice_date')
                    if isinstance(data_nf, str):
                        data_nf = datetime.strptime(data_nf, '%Y-%m-%d').date()
                    elif not data_nf:
                        data_nf = date.today()

                    # Criar movimentacao de DEVOLUCAO
                    movimento = MovimentacaoEstoque(
                        cod_produto=COD_PRODUTO_PALLET,
                        nome_produto=NOME_PRODUTO_PALLET,
                        data_movimentacao=data_nf,
                        tipo_movimentacao='DEVOLUCAO',
                        local_movimentacao='PALLET',
                        qtd_movimentacao=int(quantidade_total),
                        numero_nf=numero_nf,
                        tipo_origem='ODOO',
                        status_nf='FATURADO',
                        tipo_destinatario='CLIENTE',
                        cnpj_destinatario=cnpj_destinatario,
                        nome_destinatario=partner_nome,
                        nf_remessa_origem=nf_remessa_origem,
                        baixado=True,  # Devolucao ja esta baixada por natureza
                        observacao=f'Devolucao de pallet - NF {numero_nf}' + (f' (ref: {nf_remessa_origem})' if nf_remessa_origem else ''),
                        criado_por='SYNC_ODOO'
                    )

                    db.session.add(movimento)
                    db.session.flush()

                    # Tentar baixar a remessa original se encontrada
                    if nf_remessa_origem:
                        remessa = MovimentacaoEstoque.query.filter(
                            MovimentacaoEstoque.numero_nf == nf_remessa_origem,
                            MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
                            MovimentacaoEstoque.local_movimentacao == 'PALLET',
                            MovimentacaoEstoque.baixado == False,
                            MovimentacaoEstoque.ativo == True
                        ).first()
                        if remessa:
                            remessa.baixado = True
                            remessa.baixado_em = agora_utc_naive()
                            remessa.baixado_por = 'SYNC_ODOO'
                            remessa.movimento_baixado_id = movimento.id
                            remessa.observacao = (remessa.observacao or '') + f'\n[BAIXA] Devolucao NF {numero_nf}'
                            resumo['baixas_realizadas'] += 1

                    # Batch commit
                    batch_count += 1
                    if batch_count % BATCH_SIZE == 0:
                        db.session.commit()
                        logger.info(f"   💾 Commit batch ({batch_count} processados)")

                    nfs_existentes.add(numero_nf)

                    resumo['novos'] += 1
                    resumo['detalhes'].append({
                        'nf': numero_nf,
                        'origem': partner_nome,
                        'quantidade': int(quantidade_total),
                        'nf_remessa_origem': nf_remessa_origem
                    })

                    logger.info(f"   ✅ Devolucao NF {numero_nf}: {int(quantidade_total)} pallets <- {partner_nome}")

                except Exception as e:
                    resumo['erros'] += 1
                    logger.error(f"   ❌ Erro ao processar devolucao: {e}")
                    db.session.rollback()
                    continue

            # Commit final dos restantes
            if batch_count % BATCH_SIZE != 0:
                db.session.commit()

            elapsed = time.time() - t_inicio
            logger.info(f"✅ Sincronizacao de devolucoes concluida em {elapsed:.1f}s: {resumo['novos']} novas, {resumo['baixas_realizadas']} baixas")

        except Exception as e:
            logger.error(f"❌ Erro na sincronizacao de devolucoes: {e}")
            resumo['erro_geral'] = str(e)

        return resumo

    def sincronizar_recusas(self, dias_retroativos=30, data_de=None, data_ate=None):
        """
        Importa NFs de remessa de pallet que foram recusadas/canceladas

        OTIMIZADO v2.1: batch fetch de lines, sets locais, batch commit.

        Recusas ocorrem quando:
        - NF foi emitida mas cliente recusou (evento SEFAZ)
        - NF foi cancelada dentro do prazo de 24h

        Args:
            dias_retroativos: Quantos dias para tras buscar (ignorado se data_de informado)
            data_de: Data inicial absoluta (formato YYYY-MM-DD)
            data_ate: Data final absoluta (formato YYYY-MM-DD)

        Returns:
            dict: Resumo da sincronizacao
        """
        if data_de:
            data_corte = data_de
            logger.info(f"🔄 Iniciando sincronizacao de recusas de pallet (periodo: {data_de} a {data_ate or 'hoje'})")
        else:
            data_corte = (agora_utc_naive() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')
            logger.info(f"🔄 Iniciando sincronizacao de recusas de pallet (ultimos {dias_retroativos} dias)")

        t_inicio = time.time()
        resumo = {
            'processados': 0,
            'novos': 0,
            'ja_atualizados': 0,
            'baixas_realizadas': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar NFs de vasilhame canceladas no Odoo
            domain = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'cancel'),
                ('l10n_br_tipo_pedido', '=', 'vasilhame'),
                ('invoice_date', '>=', data_corte)
            ]
            if data_ate:
                domain.append(('invoice_date', '<=', data_ate))

            campos = [
                'id', 'name', 'invoice_date', 'partner_id',
                'l10n_br_numero_nota_fiscal', 'l10n_br_tipo_pedido',
                'invoice_line_ids'
            ]

            nfs = self.odoo.search_read('account.move', domain, campos)
            logger.info(f"   📦 Encontradas {len(nfs)} NFs de vasilhame canceladas")

            if not nfs:
                return resumo

            # ============================================================
            # BATCH PRE-FETCH: Move Lines (chunks de 200)
            # ============================================================
            all_line_ids = []
            for nf in nfs:
                all_line_ids.extend(nf.get('invoice_line_ids', []))

            lines_cache = {}  # {move_id: [linhas]}
            if all_line_ids:
                for i in range(0, len(all_line_ids), 200):
                    chunk = all_line_ids[i:i + 200]
                    linhas = self.odoo.search_read(
                        'account.move.line',
                        [('id', 'in', chunk), ('product_id', '!=', False)],
                        ['id', 'quantity', 'move_id']
                    )
                    for l in linhas:
                        move = l.get('move_id')
                        move_id = move[0] if isinstance(move, (list, tuple)) else move
                        lines_cache.setdefault(move_id, []).append(l)
            logger.info(f"   📋 {len(all_line_ids)} linhas carregadas em batch")

            # ============================================================
            # SETS LOCAIS: remessas e recusas existentes (1 query cada)
            # ============================================================
            # Remessas existentes: {numero_nf: (status_nf, baixado, id)}
            remessas_existentes = {}
            for r in MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.local_movimentacao == 'PALLET',
                MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
                MovimentacaoEstoque.ativo == True
            ).with_entities(
                MovimentacaoEstoque.numero_nf,
                MovimentacaoEstoque.status_nf,
                MovimentacaoEstoque.baixado,
                MovimentacaoEstoque.id
            ).all():
                remessas_existentes[r.numero_nf] = {
                    'status_nf': r.status_nf,
                    'baixado': r.baixado,
                    'id': r.id
                }

            recusas_existentes = set(
                r.numero_nf for r in
                MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.local_movimentacao == 'PALLET',
                    MovimentacaoEstoque.tipo_movimentacao == 'RECUSA',
                    MovimentacaoEstoque.ativo == True
                ).with_entities(MovimentacaoEstoque.numero_nf).all()
            )
            logger.info(f"   🗃️ {len(remessas_existentes)} remessas + {len(recusas_existentes)} recusas pre-carregadas")

            # ============================================================
            # PROCESSAR NFs
            # ============================================================
            batch_count = 0
            for nf in nfs:
                try:
                    resumo['processados'] += 1
                    numero_nf = str(nf.get('l10n_br_numero_nota_fiscal', ''))

                    if not numero_nf:
                        continue

                    # Verificar se existe como REMESSA e atualizar status
                    remessa_info = remessas_existentes.get(numero_nf)

                    if remessa_info:
                        if remessa_info['status_nf'] == 'CANCELADO' and remessa_info['baixado']:
                            resumo['ja_atualizados'] += 1
                            continue

                        # Buscar o registro real para atualizar (precisa do ORM)
                        remessa = MovimentacaoEstoque.query.get(remessa_info['id'])
                        if remessa:
                            remessa.status_nf = 'CANCELADO'
                            remessa.baixado = True
                            remessa.baixado_em = agora_utc_naive()
                            remessa.baixado_por = 'SYNC_ODOO'
                            remessa.observacao = (remessa.observacao or '') + '\n[CANCELAMENTO] NF cancelada no Odoo'

                            # Atualizar cache local
                            remessas_existentes[numero_nf] = {
                                'status_nf': 'CANCELADO',
                                'baixado': True,
                                'id': remessa_info['id']
                            }

                            batch_count += 1
                            if batch_count % BATCH_SIZE == 0:
                                db.session.commit()
                                logger.info(f"   💾 Commit batch ({batch_count} processados)")

                            resumo['novos'] += 1
                            resumo['baixas_realizadas'] += 1
                            resumo['detalhes'].append({
                                'nf': numero_nf,
                                'acao': 'CANCELAMENTO',
                                'quantidade': int(remessa.qtd_movimentacao)
                            })

                            logger.info(f"   ✅ NF {numero_nf} marcada como CANCELADA e baixada")
                    else:
                        # NF cancelada nao existe como REMESSA - criar registro de RECUSA
                        if numero_nf in recusas_existentes:
                            resumo['ja_atualizados'] += 1
                            continue

                        # Quantidade via cache de lines
                        linhas_nf = lines_cache.get(nf.get('id'), [])
                        quantidade_total = sum(l.get('quantity', 0) for l in linhas_nf)
                        if quantidade_total == 0:
                            quantidade_total = 1

                        # Dados do parceiro
                        partner = nf.get('partner_id', [])
                        partner_nome = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''

                        # Data da NF
                        data_nf = nf.get('invoice_date')
                        if isinstance(data_nf, str):
                            data_nf = datetime.strptime(data_nf, '%Y-%m-%d').date()
                        elif not data_nf:
                            data_nf = date.today()

                        # Criar registro de RECUSA (para historico)
                        movimento = MovimentacaoEstoque(
                            cod_produto=COD_PRODUTO_PALLET,
                            nome_produto=NOME_PRODUTO_PALLET,
                            data_movimentacao=data_nf,
                            tipo_movimentacao='RECUSA',
                            local_movimentacao='PALLET',
                            qtd_movimentacao=int(quantidade_total),
                            numero_nf=numero_nf,
                            tipo_origem='ODOO',
                            status_nf='CANCELADO',
                            nome_destinatario=partner_nome,
                            baixado=True,  # Recusa ja esta baixada por natureza
                            observacao=f'NF de pallet recusada/cancelada - {numero_nf}',
                            criado_por='SYNC_ODOO'
                        )

                        db.session.add(movimento)
                        recusas_existentes.add(numero_nf)

                        batch_count += 1
                        if batch_count % BATCH_SIZE == 0:
                            db.session.commit()
                            logger.info(f"   💾 Commit batch ({batch_count} processados)")

                        resumo['novos'] += 1
                        resumo['detalhes'].append({
                            'nf': numero_nf,
                            'acao': 'RECUSA_REGISTRADA',
                            'quantidade': int(quantidade_total)
                        })

                        logger.info(f"   ✅ Recusa NF {numero_nf} registrada")

                except Exception as e:
                    resumo['erros'] += 1
                    logger.error(f"   ❌ Erro ao processar recusa: {e}")
                    db.session.rollback()
                    continue

            # Commit final dos restantes
            if batch_count % BATCH_SIZE != 0:
                db.session.commit()

            elapsed = time.time() - t_inicio
            logger.info(f"✅ Sincronizacao de recusas concluida em {elapsed:.1f}s: {resumo['novos']} novos, {resumo['baixas_realizadas']} baixas")

        except Exception as e:
            logger.error(f"❌ Erro na sincronizacao de recusas: {e}")
            resumo['erro_geral'] = str(e)

        return resumo

    def sincronizar_tudo(self, dias_retroativos=30, data_de=None, data_ate=None):
        """
        Sincroniza remessas, vendas, devolucoes e recusas de pallet

        Args:
            dias_retroativos: Quantos dias para tras buscar (ignorado se data_de informado)
            data_de: Data inicial absoluta (formato YYYY-MM-DD)
            data_ate: Data final absoluta (formato YYYY-MM-DD)

        Returns:
            dict: Resumo consolidado
        """
        t_inicio_total = time.time()
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO SINCRONIZACAO COMPLETA DE PALLET")
        if data_de:
            logger.info(f"   Periodo: {data_de} a {data_ate or 'hoje'}")
        else:
            logger.info(f"   Ultimos {dias_retroativos} dias")
        logger.info("=" * 60)

        resumo_remessas = self.sincronizar_remessas(dias_retroativos, data_de=data_de, data_ate=data_ate)
        resumo_vendas = self.sincronizar_vendas_pallet(dias_retroativos, data_de=data_de, data_ate=data_ate)
        resumo_devolucoes = self.sincronizar_devolucoes(dias_retroativos, data_de=data_de, data_ate=data_ate)
        resumo_recusas = self.sincronizar_recusas(dias_retroativos, data_de=data_de, data_ate=data_ate)

        # Limpar cache de destinatario usado nos batches
        from app.pallet.utils import limpar_cache_destinatario
        limpar_cache_destinatario()

        # DOMÍNIO B: Processar NCs e Canceladas (vinculação automática)
        resumo_ncs = {'ncs_vinculadas': 0, 'ncs_sem_remessa': 0, 'erros': 0}
        resumo_canceladas = {'canceladas_registradas': 0, 'ja_existentes': 0, 'erros': 0}
        try:
            match_service = MatchService(odoo_client=self.odoo)
            logger.info("📄 Processando NCs de pallet...")
            resumo_ncs = match_service.processar_ncs_pallet(
                data_de=data_de,
                data_ate=data_ate
            )
            logger.info(f"   NCs vinculadas: {resumo_ncs.get('ncs_vinculadas', 0)}")

            logger.info("📄 Processando NFs canceladas de pallet...")
            resumo_canceladas = match_service.processar_canceladas_pallet(
                data_de=data_de,
                data_ate=data_ate
            )
            logger.info(f"   Canceladas registradas: {resumo_canceladas.get('canceladas_registradas', 0)}")
        except Exception as e:
            logger.error(f"Erro ao processar NCs/Canceladas: {e}")

        elapsed_total = time.time() - t_inicio_total
        logger.info(f"🏁 SINCRONIZACAO COMPLETA FINALIZADA em {elapsed_total:.1f}s")

        return {
            'remessas': resumo_remessas,
            'vendas': resumo_vendas,
            'devolucoes': resumo_devolucoes,
            'recusas': resumo_recusas,
            'ncs': resumo_ncs,
            'canceladas': resumo_canceladas,
            'tempo_total_segundos': round(elapsed_total, 1),
            'total_novos': (
                resumo_remessas.get('novos', 0) +
                resumo_vendas.get('novos', 0) +
                resumo_devolucoes.get('novos', 0) +
                resumo_recusas.get('novos', 0) +
                resumo_ncs.get('ncs_vinculadas', 0) +
                resumo_canceladas.get('canceladas_registradas', 0)
            ),
            'total_baixas': (
                resumo_devolucoes.get('baixas_realizadas', 0) +
                resumo_recusas.get('baixas_realizadas', 0)
            )
        }
