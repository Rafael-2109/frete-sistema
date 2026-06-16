"""
Service de Match de NFs de Devolução/Retorno de Pallet - Domínio B

Este service gerencia a identificação e vinculação de NFs de devolução/retorno
de pallet com as respectivas NFs de remessa:
- Buscar NFs de devolução de pallet no DFe (CFOP 5920/6920/1920/2920)
- Sugerir vinculação automática baseada em CNPJ e quantidade
- Confirmar ou rejeitar sugestões
- Criar soluções documentais vinculadas

Regras de Negócio:
- REGRA 004: Devolução 1:N - 1 NF devolução pode fechar N NFs remessa
- REGRA 004: Retorno 1:1 - 1 NF retorno fecha apenas 1 NF remessa
- Sistema SUGERE mas EXIGE confirmação do usuário (vinculacao='SUGESTAO')

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app import db
from app.pallet.models.nf_remessa import PalletNFRemessa
from app.pallet.models.nf_solucao import PalletNFSolucao
from app.pallet.services.nf_service import NFService
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# CFOPs de devolução/remessa de vasilhame/pallet
# 5920/6920 = Remessa para devolução de vasilhame (saída do cliente para nós)
# 1920/2920 = Entrada de vasilhame devolvido (entrada para nós)
CFOPS_DEVOLUCAO_PALLET = ['5920', '6920', '1920', '2920']

# Código do produto pallet
COD_PRODUTO_PALLET = '208000012'

# CNPJs Nacom/La Famiglia (intercompany - ignorar)
CNPJS_INTERCOMPANY_PREFIXOS = [
    '61724241',  # Nacom Goya (matriz e filiais)
    '18467441',  # La Famiglia
]

# Partner IDs internos no Odoo (Nacom/La Famiglia) - devoluções internas não são controladas
PARTNER_IDS_INTERNOS = [35, 1, 34, 33]


class MatchService:
    """
    Service para identificação e match de NFs de devolução de pallet (Domínio B).

    Responsabilidades:
    - Buscar NFs de devolução de pallet no DFe do Odoo
    - Identificar NFs de remessa candidatas para vinculação
    - Criar sugestões de vinculação para confirmação do usuário
    - Executar vinculação manual ou automática
    """

    def __init__(self, odoo_client=None):
        """
        Inicializa o service com cliente Odoo opcional.

        Args:
            odoo_client: Cliente XML-RPC do Odoo configurado (opcional).
                         Se não informado, cria conexão automaticamente quando necessário.
        """
        self._odoo_client = odoo_client
        self._produto_pallet_id = None  # Cache do ID do produto PALLET

    @property
    def odoo(self):
        """Lazy loading do cliente Odoo."""
        if self._odoo_client is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._odoo_client = get_odoo_connection()
        return self._odoo_client

    def _get_produto_pallet_id(self) -> int:
        """Retorna o ID do produto PALLET (208000012) com cache."""
        if self._produto_pallet_id is None:
            produtos = self.odoo.search_read(
                'product.product',
                [('default_code', '=', COD_PRODUTO_PALLET)],
                ['id']
            )
            if produtos:
                self._produto_pallet_id = produtos[0]['id']
            else:
                self._produto_pallet_id = 0  # Não encontrado
        return self._produto_pallet_id

    # =========================================================================
    # IDENTIFICAÇÃO DE NFS DE DEVOLUÇÃO DE PALLET
    # =========================================================================

    def buscar_nfs_devolucao_pallet_dfe(
        self,
        data_de: str = None,
        data_ate: str = None,
        apenas_nao_processadas: bool = True
    ) -> List[Dict]:
        """
        Busca NFs de devolução de pallet no DFe do Odoo.

        Critérios:
        - finnfe = 4 (NF de entrada)
        - CFOP in (5920, 6920, 1920, 2920) ou
        - Produto com código 208000012 (PALLET)

        Args:
            data_de: Data inicial (formato YYYY-MM-DD). Default: últimos 30 dias
            data_ate: Data final (formato YYYY-MM-DD). Default: hoje
            apenas_nao_processadas: Se True, exclui NFs já vinculadas

        Returns:
            List[Dict]: Lista de NFs encontradas com dados para match
                {
                    'odoo_dfe_id': int,
                    'numero_nf': str,
                    'serie': str,
                    'chave_nfe': str,
                    'data_emissao': datetime,
                    'cnpj_emitente': str,
                    'nome_emitente': str,
                    'quantidade': int,
                    'valor_total': Decimal,
                    'info_complementar': str,
                    'tipo_sugestao': str,  # 'DEVOLUCAO'
                    'nf_remessa_referenciada': str  # Se encontrada em info complementar
                }
        """
        from datetime import timedelta

        if not data_de:
            data_de = (agora_utc_naive() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not data_ate:
            data_ate = agora_utc_naive().strftime('%Y-%m-%d')

        logger.info(
            f"🔍 Buscando NFs de devolução de pallet no DFe "
            f"(período: {data_de} a {data_ate})"
        )

        resultado = []

        try:
            # PASSO 1: Identificar DFE IDs que têm linha de pallet (otimizado)
            pallet_id = self._get_produto_pallet_id()
            cfops_pallet = CFOPS_DEVOLUCAO_PALLET + ['5921', '6921']

            # Buscar linhas com produto pallet
            dfe_ids_com_pallet = set()
            quantidades_por_dfe = {}  # Cache de quantidades

            # Buscar por produto pallet (mais preciso)
            if pallet_id:
                linhas_produto = self.odoo.search_read(
                    'l10n_br_ciel_it_account.dfe.line',
                    [('product_id', '=', pallet_id)],
                    ['dfe_id', 'det_prod_qcom']
                )
                for linha in linhas_produto:
                    dfe = linha.get('dfe_id')
                    if dfe:
                        dfe_id = dfe[0] if isinstance(dfe, (list, tuple)) else dfe
                        dfe_ids_com_pallet.add(dfe_id)
                        quantidades_por_dfe[dfe_id] = quantidades_por_dfe.get(dfe_id, 0) + int(linha.get('det_prod_qcom', 0))

            # Buscar também por CFOPs de vasilhame
            linhas_cfop = self.odoo.search_read(
                'l10n_br_ciel_it_account.dfe.line',
                [('det_prod_cfop', 'in', cfops_pallet)],
                ['dfe_id', 'det_prod_qcom', 'product_id']
            )
            for linha in linhas_cfop:
                dfe = linha.get('dfe_id')
                if dfe:
                    dfe_id = dfe[0] if isinstance(dfe, (list, tuple)) else dfe
                    dfe_ids_com_pallet.add(dfe_id)
                    # Adicionar quantidade se não for do produto pallet (evitar duplicação)
                    prod = linha.get('product_id')
                    prod_id = prod[0] if isinstance(prod, (list, tuple)) else prod
                    if prod_id != pallet_id:
                        quantidades_por_dfe[dfe_id] = quantidades_por_dfe.get(dfe_id, 0) + int(linha.get('det_prod_qcom', 0))

            if not dfe_ids_com_pallet:
                logger.info("   📦 Nenhuma linha de pallet encontrada no período")
                return []

            logger.info(f"   📦 Encontrados {len(dfe_ids_com_pallet)} DFEs com linhas de pallet")

            # PASSO 2: Buscar detalhes dos DFEs de DEVOLUÇÃO que têm pallet
            domain = [
                ('id', 'in', list(dfe_ids_com_pallet)),
                ('nfe_infnfe_ide_finnfe', '=', '4'),  # Finalidade 4 = Devolução/Retorno
                ('partner_id', 'not in', PARTNER_IDS_INTERNOS),  # Excluir Nacom/La Famiglia
                ('l10n_br_status', 'in', ['03', '04', '05', '06']),  # Ciencia, PO, Rateio, Concluido
                ('nfe_infnfe_ide_dhemi', '>=', data_de),
                ('nfe_infnfe_ide_dhemi', '<=', data_ate),
            ]

            campos = [
                'id', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie', 'protnfe_infnfe_chnfe',
                'nfe_infnfe_ide_dhemi', 'partner_id', 'nfe_infnfe_emit_cnpj',
                'nfe_infnfe_infadic_infcpl', 'nfe_infnfe_total_icmstot_vnf'
            ]

            documentos = self.odoo.search_read(
                'l10n_br_ciel_it_account.dfe', domain, campos
            )

            logger.info(f"   📄 Encontrados {len(documentos)} DFEs de devolução de pallet (finnfe=4)")

            # PASSO 3: Processar documentos (já sabemos que têm pallet)
            for doc in documentos:
                try:
                    dfe_id = doc['id']

                    # Limpar CNPJ
                    cnpj_emitente = self._limpar_cnpj(doc.get('nfe_infnfe_emit_cnpj', ''))

                    # Ignorar intercompany
                    if self._eh_intercompany(cnpj_emitente):
                        continue

                    # Verificar se já processada
                    if apenas_nao_processadas:
                        if self._nf_ja_processada(doc.get('protnfe_infnfe_chnfe', '')):
                            continue

                    # Extrair informações
                    info_complementar = doc.get('nfe_infnfe_infadic_infcpl', '') or ''
                    nf_remessa_ref = self._extrair_nf_referencia(info_complementar)
                    tipo_sugestao = 'DEVOLUCAO'  # Sempre DEVOLUCAO agora

                    # Usar quantidade do cache
                    qtd_pallets = quantidades_por_dfe.get(dfe_id, 1)

                    nf_data = {
                        'odoo_dfe_id': dfe_id,
                        'numero_nf': str(doc.get('nfe_infnfe_ide_nnf', '')),
                        'serie': str(doc.get('nfe_infnfe_ide_serie', '')),
                        'chave_nfe': doc.get('protnfe_infnfe_chnfe', ''),
                        'data_emissao': doc.get('nfe_infnfe_ide_dhemi'),
                        'cnpj_emitente': cnpj_emitente,
                        'nome_emitente': (
                            doc.get('partner_id', [None, ''])[1]
                            if isinstance(doc.get('partner_id'), (list, tuple))
                            else ''
                        ),
                        'quantidade': qtd_pallets,
                        'valor_total': Decimal(str(doc.get('nfe_infnfe_total_icmstot_vnf', 0))),
                        'info_complementar': info_complementar,
                        'tipo_sugestao': tipo_sugestao,
                        'nf_remessa_referenciada': nf_remessa_ref
                    }

                    resultado.append(nf_data)
                    logger.debug(f"   ✓ NF {nf_data['numero_nf']} - {qtd_pallets} pallets")

                except Exception as e:
                    logger.warning(f"   ⚠️ Erro ao processar documento #{doc.get('id')}: {e}")
                    continue

            logger.info(f"   📦 Total de NFs de devolução de pallet encontradas: {len(resultado)}")

            return resultado

        except Exception as e:
            logger.error(f"Erro ao buscar NFs de devolução de pallet: {e}")
            raise

    def buscar_nfs_pallet_canceladas(
        self,
        data_de: str = None,
        data_ate: str = None,
        apenas_nao_processadas: bool = True
    ) -> List[Dict]:
        """
        Busca NFs de pallet CANCELADAS do Odoo.

        NFs canceladas são NFs de remessa de vasilhame com state='cancel'.
        Essas NFs podem ser direcionadas para solucionar pendências.

        Args:
            data_de: Data inicial (formato YYYY-MM-DD). Default: últimos 90 dias
            data_ate: Data final (formato YYYY-MM-DD). Default: hoje
            apenas_nao_processadas: Se True, exclui NFs já vinculadas

        Returns:
            List[Dict]: Lista de NFs canceladas encontradas
                {
                    'odoo_account_move_id': int,
                    'numero_nf': str,
                    'chave_nfe': str,
                    'data_emissao': datetime,
                    'cnpj_destinatario': str,
                    'nome_destinatario': str,
                    'quantidade': int,
                    'valor_total': Decimal,
                    'tipo_sugestao': 'CANCELAMENTO'
                }
        """
        from datetime import timedelta

        if not data_de:
            data_de = (agora_utc_naive() - timedelta(days=90)).strftime('%Y-%m-%d')
        if not data_ate:
            data_ate = agora_utc_naive().strftime('%Y-%m-%d')

        logger.info(
            f"🔍 Buscando NFs de pallet CANCELADAS no Odoo "
            f"(período: {data_de} a {data_ate})"
        )

        resultado = []

        try:
            # Buscar NFs de vasilhame canceladas (state=cancel)
            domain = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),  # NFs de saída
                ('state', '=', 'cancel'),  # CANCELADAS
                ('l10n_br_tipo_pedido', '=', 'vasilhame'),  # Tipo vasilhame/pallet
                ('invoice_date', '>=', data_de),
                ('invoice_date', '<=', data_ate),
            ]

            campos = [
                'id', 'name', 'l10n_br_numero_nota_fiscal', 'l10n_br_chave_nf',
                'invoice_date', 'partner_id', 'amount_total',
                'invoice_line_ids', 'company_id'
            ]

            nfs_canceladas = self.odoo.search_read('account.move', domain, campos)

            logger.info(f"   📄 Encontradas {len(nfs_canceladas)} NFs de pallet canceladas")

            for nf in nfs_canceladas:
                try:
                    numero_nf = nf.get('l10n_br_numero_nota_fiscal')
                    # Ignorar NFs sem número (rascunhos cancelados)
                    if not numero_nf or numero_nf == 'False':
                        continue
                    numero_nf = str(numero_nf)

                    # Verificar se já processada
                    if apenas_nao_processadas:
                        chave = nf.get('l10n_br_chave_nf', '')
                        if chave and self._nf_ja_processada(chave):
                            continue

                    # Dados do parceiro (destinatário original)
                    partner = nf.get('partner_id', [])
                    partner_nome = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''
                    partner_id = partner[0] if isinstance(partner, (list, tuple)) else partner

                    # Buscar CNPJ do parceiro
                    cnpj = ''
                    if partner_id:
                        partner_data = self.odoo.search_read(
                            'res.partner',
                            [('id', '=', partner_id)],
                            ['l10n_br_cnpj']
                        )
                        if partner_data:
                            cnpj = self._limpar_cnpj(partner_data[0].get('l10n_br_cnpj', ''))

                    # Ignorar intercompany
                    if self._eh_intercompany(cnpj):
                        continue

                    # Buscar quantidade das linhas
                    linha_ids = nf.get('invoice_line_ids', [])
                    quantidade = 0
                    if linha_ids:
                        linhas = self.odoo.search_read(
                            'account.move.line',
                            [('id', 'in', linha_ids), ('product_id', '!=', False)],
                            ['quantity']
                        )
                        for linha in linhas:
                            quantidade += abs(int(linha.get('quantity', 0)))
                    if quantidade == 0:
                        quantidade = 1

                    # Data da NF
                    data_nf = nf.get('invoice_date')

                    nf_data = {
                        'odoo_account_move_id': nf['id'],
                        'numero_nf': numero_nf,
                        'chave_nfe': nf.get('l10n_br_chave_nf', ''),
                        'data_emissao': data_nf,
                        'cnpj_destinatario': cnpj,
                        'nome_destinatario': partner_nome,
                        'quantidade': quantidade,
                        'valor_total': Decimal(str(nf.get('amount_total', 0))),
                        'tipo_sugestao': 'CANCELAMENTO'
                    }

                    resultado.append(nf_data)
                    logger.debug(f"   ✓ NF cancelada {numero_nf} - {partner_nome}")

                except Exception as e:
                    logger.warning(f"   ⚠️ Erro ao processar NC #{nf.get('id')}: {e}")
                    continue

            logger.info(f"   📦 Total de NFs de pallet canceladas: {len(resultado)}")

            return resultado

        except Exception as e:
            logger.error(f"Erro ao buscar NFs de pallet canceladas: {e}")
            raise

    def buscar_notas_credito_pallet(
        self,
        data_de: str = None,
        data_ate: str = None,
        apenas_nao_processadas: bool = True
    ) -> List[Dict]:
        """
        Busca Notas de Crédito de pallet do Odoo.

        NCs são NFs de estorno (out_refund) com linhas de produto pallet.
        IMPORTANTE: O campo l10n_br_tipo_pedido NÃO é confiável para NCs,
        pois frequentemente está como False. A identificação é feita pelo
        produto pallet nas linhas (account.move.line).

        Args:
            data_de: Data inicial (formato YYYY-MM-DD). Default: últimos 90 dias
            data_ate: Data final (formato YYYY-MM-DD). Default: hoje
            apenas_nao_processadas: Se True, exclui NCs já vinculadas

        Returns:
            List[Dict]: Lista de NCs encontradas
                {
                    'odoo_account_move_id': int,
                    'numero_nf': str,
                    'chave_nfe': str,
                    'data_emissao': date,
                    'cnpj_destinatario': str,
                    'nome_destinatario': str,
                    'quantidade': int,
                    'valor_total': Decimal,
                    'tipo_sugestao': 'NOTA_CREDITO',
                    'nf_remessa_original_id': int ou None  # ID da NF revertida (vinculação automática)
                }
        """
        from datetime import timedelta

        if not data_de:
            data_de = (agora_utc_naive() - timedelta(days=90)).strftime('%Y-%m-%d')
        if not data_ate:
            data_ate = agora_utc_naive().strftime('%Y-%m-%d')

        logger.info(
            f"🔍 Buscando Notas de Crédito de pallet no Odoo "
            f"(período: {data_de} a {data_ate})"
        )

        resultado = []

        try:
            # PASSO 1: Buscar linhas com produto pallet em account.move.line
            pallet_id = self._get_produto_pallet_id()
            if not pallet_id:
                logger.warning("   ⚠️ Produto PALLET (208000012) não encontrado no Odoo")
                return []

            logger.info(f"   📦 Buscando linhas com produto pallet (ID: {pallet_id})...")

            linhas_pallet = self.odoo.search_read(
                'account.move.line',
                [('product_id', '=', pallet_id)],
                ['move_id', 'quantity']
            )

            # Extrair IDs únicos dos moves e somar quantidades
            move_ids = set()
            qtd_por_move = {}
            for linha in linhas_pallet:
                move = linha.get('move_id')
                if move:
                    move_id = move[0] if isinstance(move, (list, tuple)) else move
                    move_ids.add(move_id)
                    qtd_por_move[move_id] = qtd_por_move.get(move_id, 0) + abs(int(linha.get('quantity', 0)))

            if not move_ids:
                logger.info("   📦 Nenhuma linha de pallet encontrada")
                return []

            logger.info(f"   📦 Encontradas {len(linhas_pallet)} linhas de pallet em {len(move_ids)} account.move")

            # PASSO 2: Filtrar apenas NCs (out_refund) postadas no período
            domain = [
                ('id', 'in', list(move_ids)),
                ('move_type', '=', 'out_refund'),  # Nota de Crédito de saída
                ('state', '=', 'posted'),  # Apenas postadas
                ('invoice_date', '>=', data_de),
                ('invoice_date', '<=', data_ate),
            ]

            campos = [
                'id', 'name', 'l10n_br_numero_nota_fiscal', 'l10n_br_chave_nf',
                'invoice_date', 'partner_id', 'amount_total',
                'reversed_entry_id'  # ID da NF original que foi revertida
            ]

            ncs = self.odoo.search_read('account.move', domain, campos)

            logger.info(f"   📄 Encontradas {len(ncs)} NCs de pallet (out_refund + posted)")

            # PASSO 3: Processar cada NC
            for nc in ncs:
                try:
                    numero_nf = nc.get('l10n_br_numero_nota_fiscal')
                    # Ignorar NCs sem número
                    if not numero_nf or numero_nf == 'False':
                        continue
                    numero_nf = str(numero_nf)

                    # Verificar se já processada
                    if apenas_nao_processadas:
                        chave = nc.get('l10n_br_chave_nf', '')
                        if chave and self._nf_ja_processada(chave):
                            continue

                    # Dados do parceiro (destinatário)
                    partner = nc.get('partner_id', [])
                    partner_nome = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''
                    partner_id = partner[0] if isinstance(partner, (list, tuple)) else partner

                    # Buscar CNPJ do parceiro
                    cnpj = ''
                    if partner_id:
                        partner_data = self.odoo.search_read(
                            'res.partner',
                            [('id', '=', partner_id)],
                            ['l10n_br_cnpj']
                        )
                        if partner_data:
                            cnpj = self._limpar_cnpj(partner_data[0].get('l10n_br_cnpj', ''))

                    # Ignorar intercompany
                    if self._eh_intercompany(cnpj):
                        continue

                    # Usar quantidade do cache
                    move_id = nc['id']
                    quantidade = qtd_por_move.get(move_id, 1)

                    # Data da NC
                    data_nc = nc.get('invoice_date')

                    # Extrair ID da NF de remessa original (reversed_entry_id)
                    reversed_entry = nc.get('reversed_entry_id')
                    nf_remessa_original_id = None
                    if reversed_entry:
                        nf_remessa_original_id = (
                            reversed_entry[0] if isinstance(reversed_entry, (list, tuple))
                            else reversed_entry
                        )

                    nc_data = {
                        'odoo_account_move_id': move_id,
                        'numero_nf': numero_nf,
                        'chave_nfe': nc.get('l10n_br_chave_nf', ''),
                        'data_emissao': data_nc,
                        'cnpj_destinatario': cnpj,
                        'nome_destinatario': partner_nome,
                        'quantidade': quantidade,
                        'valor_total': Decimal(str(nc.get('amount_total', 0))),
                        'tipo_sugestao': 'NOTA_CREDITO',
                        'nf_remessa_original_id': nf_remessa_original_id  # ID da NF de remessa revertida
                    }

                    resultado.append(nc_data)
                    logger.debug(f"   ✓ NC {numero_nf} - {partner_nome} - Qtd: {quantidade}")

                except Exception as e:
                    logger.warning(f"   ⚠️ Erro ao processar NC #{nc.get('id')}: {e}")
                    continue

            logger.info(f"   📦 Total de NCs de pallet encontradas: {len(resultado)}")

            return resultado

        except Exception as e:
            logger.error(f"Erro ao buscar NCs de pallet: {e}")
            raise

    def _eh_nf_devolucao_pallet(self, dfe_id: int) -> bool:
        """
        Verifica se o documento fiscal é uma NF de devolução de pallet.

        Critérios:
        - Tem linha com CFOP de devolução de vasilhame (5920/6920/1920/2920/5921/6921)
        - OU tem linha com produto código 208000012

        Args:
            dfe_id: ID do DFE no Odoo (l10n_br_ciel_it_account.dfe)

        Returns:
            bool: True se é NF de devolução de pallet
        """
        try:
            pallet_id = self._get_produto_pallet_id()

            # Busca otimizada: verificar se existe linha com produto pallet OU CFOP de devolução
            # Primeiro tenta pelo produto (mais preciso)
            if pallet_id:
                linhas_pallet = self.odoo.search_read(
                    'l10n_br_ciel_it_account.dfe.line',
                    [('dfe_id', '=', dfe_id), ('product_id', '=', pallet_id)],
                    ['id'],
                    limit=1
                )
                if linhas_pallet:
                    return True

            # Se não encontrou por produto, verificar por CFOP de vasilhame
            # Incluir também 5921/6921 (devolução de vasilhame/pallet)
            cfops_pallet = CFOPS_DEVOLUCAO_PALLET + ['5921', '6921']
            for cfop in cfops_pallet:
                linhas_cfop = self.odoo.search_read(
                    'l10n_br_ciel_it_account.dfe.line',
                    [('dfe_id', '=', dfe_id), ('det_prod_cfop', '=', cfop)],
                    ['id'],
                    limit=1
                )
                if linhas_cfop:
                    return True

            return False

        except Exception as e:
            logger.warning(f"Erro ao verificar se DFE #{dfe_id} é pallet: {e}")
            return False

    def _eh_produto_pallet(self, product_id: int) -> bool:
        """Verifica se o produto é pallet usando cache do ID."""
        pallet_id = self._get_produto_pallet_id()
        return product_id == pallet_id if pallet_id else False

    def _obter_quantidade_pallets_linhas(self, dfe_id: int) -> int:
        """Obtém a quantidade de pallets das linhas do DFE (otimizado)."""
        try:
            total = 0
            pallet_id = self._get_produto_pallet_id()

            # Buscar linhas com produto pallet diretamente
            if pallet_id:
                linhas_prod = self.odoo.search_read(
                    'l10n_br_ciel_it_account.dfe.line',
                    [('dfe_id', '=', dfe_id), ('product_id', '=', pallet_id)],
                    ['det_prod_qcom']
                )
                for linha in linhas_prod:
                    total += int(linha.get('det_prod_qcom', 0))

            # Buscar também por CFOPs de vasilhame (incluindo 5921/6921)
            cfops_pallet = CFOPS_DEVOLUCAO_PALLET + ['5921', '6921']
            linhas_cfop = self.odoo.search_read(
                'l10n_br_ciel_it_account.dfe.line',
                [('dfe_id', '=', dfe_id), ('det_prod_cfop', 'in', cfops_pallet)],
                ['det_prod_qcom', 'product_id']
            )
            for linha in linhas_cfop:
                # Evitar contar duplicado se já contou pelo produto
                prod = linha.get('product_id')
                prod_id = prod[0] if isinstance(prod, (list, tuple)) else prod
                if prod_id != pallet_id:
                    total += int(linha.get('det_prod_qcom', 0))

            return total if total > 0 else 1  # Fallback para 1 se não encontrou quantidade

        except Exception as e:
            logger.warning(f"Erro ao obter quantidade de pallets: {e}")
            return 1

    def _limpar_cnpj(self, cnpj: str) -> str:
        """Remove formatação do CNPJ (apenas números)."""
        if not cnpj:
            return ''
        return re.sub(r'[^0-9]', '', str(cnpj))

    def _eh_intercompany(self, cnpj: str) -> bool:
        """Verifica se o CNPJ é intercompany (Nacom ou La Famiglia)."""
        if not cnpj:
            return False
        prefixo = cnpj[:8]
        return prefixo in CNPJS_INTERCOMPANY_PREFIXOS

    def _nf_ja_processada(self, chave_nfe: str) -> bool:
        """Verifica se a NF já foi processada (vinculada a alguma solução)."""
        if not chave_nfe:
            return False

        existente = PalletNFSolucao.buscar_por_chave_nfe(chave_nfe)
        return existente is not None

    def _extrair_nf_referencia(self, info_complementar: str) -> Optional[str]:
        """
        Extrai número de NF referenciada das informações complementares.

        Busca por padrões como:
        - "Ref. NF 12345"
        - "Referente a NF 12345"
        - "NF Remessa: 12345"
        - "NF de origem: 12345"

        Args:
            info_complementar: Texto das informações complementares

        Returns:
            str ou None: Número da NF referenciada ou None
        """
        if not info_complementar:
            return None

        # Padrões para buscar NF referenciada (case-insensitive para cada grupo)
        padroes = [
            r'[Rr][Ee][Ff]\.?\s*[Nn][Ff]\s*[:n°]?\s*(\d+)',  # Ref. NF, REF NF, ref nf
            r'[Rr][Ee][Ff][Ee][Rr][Ee][Nn][Tt][Ee]\s+[aàAÀ]\s*[Nn][Ff]\s*[:n°]?\s*(\d+)',  # Referente a NF
            r'[Nn][Ff]\s+[Rr][Ee][Mm][Ee][Ss][Ss][Aa]\s*[:n°]?\s*(\d+)',  # NF Remessa
            r'[Nn][Ff]\s+[Dd][Ee]\s+[Oo][Rr][Ii][Gg][Ee][Mm]\s*[:n°]?\s*(\d+)',  # NF de origem
            r'[Nn][Oo][Tt][Aa]\s+[Ff][Ii][Ss][Cc][Aa][Ll]\s*[:n°]?\s*(\d+)',  # Nota Fiscal
        ]

        for padrao in padroes:
            match = re.search(padrao, info_complementar)
            if match:
                return match.group(1)

        return None

    # =========================================================================
    # SUGESTÃO DE VINCULAÇÃO
    # =========================================================================

    def sugerir_vinculacao_devolucao(
        self,
        nf_devolucao: Dict,
        criar_sugestao: bool = True
    ) -> List[Dict]:
        """
        Sugere NFs de remessa para vincular a uma NF de devolução.

        Critérios de match:
        1. Mesmo CNPJ destinatário (cliente/transportadora que recebeu)
        2. NF de remessa com status ATIVA
        3. Quantidade pendente >= quantidade devolvida

        Args:
            nf_devolucao: Dados da NF de devolução (retorno de buscar_nfs_devolucao_pallet_dfe)
            criar_sugestao: Se True, cria PalletNFSolucao com vinculacao='SUGESTAO'

        Returns:
            List[Dict]: Lista de candidatas com score de match
                {
                    'nf_remessa_id': int,
                    'numero_nf': str,
                    'data_emissao': datetime,
                    'quantidade': int,
                    'qtd_pendente': int,
                    'tipo_destinatario': str,
                    'nome_destinatario': str,
                    'score': int,  # 0-100, maior = melhor match
                    'motivo_score': str,
                    'sugestao_id': int  # ID da sugestão criada (se criar_sugestao=True)
                }
        """
        cnpj_emitente = nf_devolucao.get('cnpj_emitente', '')
        quantidade = nf_devolucao.get('quantidade', 0)
        nf_ref = nf_devolucao.get('nf_remessa_referenciada')

        logger.info(
            f"🔍 Buscando NFs de remessa para vincular "
            f"(CNPJ: {cnpj_emitente}, Qtd: {quantidade})"
        )

        candidatas = []

        # Buscar NFs de remessa ativas para o mesmo CNPJ
        nfs_remessa = PalletNFRemessa.query.filter(
            PalletNFRemessa.cnpj_destinatario == cnpj_emitente,
            PalletNFRemessa.status == 'ATIVA',
            PalletNFRemessa.cancelada == False,
            PalletNFRemessa.ativo == True
        ).order_by(
            PalletNFRemessa.data_emissao.asc()  # FIFO - mais antigas primeiro
        ).all()

        for nf in nfs_remessa:
            if nf.qtd_pendente <= 0:
                continue

            # Calcular score de match
            score, motivo = self._calcular_score_match(
                nf, nf_devolucao, nf_ref
            )

            candidata = {
                'nf_remessa_id': nf.id,
                'numero_nf': nf.numero_nf,
                'data_emissao': nf.data_emissao,
                'quantidade': nf.quantidade,
                'qtd_pendente': nf.qtd_pendente,
                'tipo_destinatario': nf.tipo_destinatario,
                'nome_destinatario': nf.nome_destinatario,
                'score': score,
                'motivo_score': motivo,
                'sugestao_id': None
            }

            # Criar sugestão se solicitado
            if criar_sugestao and score >= 50:
                try:
                    sugestao = self._criar_sugestao_vinculacao(
                        nf_remessa=nf,
                        nf_devolucao=nf_devolucao,
                        quantidade_sugerida=min(quantidade, nf.qtd_pendente)
                    )
                    candidata['sugestao_id'] = sugestao.id
                except Exception as e:
                    logger.warning(
                        f"Erro ao criar sugestão para NF #{nf.id}: {e}"
                    )

            candidatas.append(candidata)

        # Ordenar por score (maior primeiro)
        candidatas.sort(key=lambda x: x['score'], reverse=True)

        logger.info(
            f"   📋 Encontradas {len(candidatas)} NFs de remessa candidatas"
        )

        return candidatas

    def sugerir_vinculacao_devolucao_com_referencia(
        self,
        nf_devolucao: Dict,
        criar_sugestao: bool = True
    ) -> Optional[Dict]:
        """
        Sugere NF de remessa para vincular a uma NF de devolução com referência (match exato).

        Quando a NF de devolução tem referência à NF original nas informações complementares,
        busca correspondência exata:
        1. Número da NF nas informações complementares
        2. Mesmo CNPJ destinatário

        Args:
            nf_devolucao: Dados da NF de devolução
            criar_sugestao: Se True, cria PalletNFSolucao com vinculacao='AUTOMATICO'
                           (devoluções com match exato são confirmadas automaticamente)

        Returns:
            Dict ou None: Candidata encontrada ou None
        """
        cnpj_emitente = nf_devolucao.get('cnpj_emitente', '')
        quantidade = nf_devolucao.get('quantidade', 0)
        nf_ref = nf_devolucao.get('nf_remessa_referenciada')

        if not nf_ref:
            logger.info(
                f"   ℹ️ NF de devolução sem referência - usar sugestão por CNPJ"
            )
            return None

        logger.info(
            f"🔍 Buscando NF de remessa {nf_ref} para devolução "
            f"(CNPJ: {cnpj_emitente})"
        )

        # Buscar NF de remessa específica
        nf_remessa = PalletNFRemessa.query.filter(
            PalletNFRemessa.numero_nf == nf_ref,
            PalletNFRemessa.cnpj_destinatario == cnpj_emitente,
            PalletNFRemessa.status == 'ATIVA',
            PalletNFRemessa.cancelada == False,
            PalletNFRemessa.ativo == True
        ).first()

        if not nf_remessa:
            logger.info(
                f"   ⚠️ NF de remessa {nf_ref} não encontrada para CNPJ {cnpj_emitente}"
            )
            return None

        if nf_remessa.qtd_pendente <= 0:
            logger.info(
                f"   ⚠️ NF de remessa {nf_ref} já está totalmente resolvida"
            )
            return None

        resultado = {
            'nf_remessa_id': nf_remessa.id,
            'numero_nf': nf_remessa.numero_nf,
            'data_emissao': nf_remessa.data_emissao,
            'quantidade': nf_remessa.quantidade,
            'qtd_pendente': nf_remessa.qtd_pendente,
            'tipo_destinatario': nf_remessa.tipo_destinatario,
            'nome_destinatario': nf_remessa.nome_destinatario,
            'score': 100,  # Match exato por número
            'motivo_score': 'Match exato por número de NF nas informações complementares',
            'sugestao_id': None
        }

        # Criar sugestão automática (já confirmada para devolução com match exato)
        if criar_sugestao:
            try:
                # Para devolução com match exato, criar como AUTOMATICO (já confirmado)
                solucao = NFService.registrar_solucao_nf(
                    nf_remessa_id=nf_remessa.id,
                    tipo='DEVOLUCAO',
                    quantidade=min(quantidade, nf_remessa.qtd_pendente),
                    dados={
                        'numero_nf_solucao': nf_devolucao.get('numero_nf', ''),
                        'serie_nf_solucao': nf_devolucao.get('serie', ''),
                        'chave_nfe_solucao': nf_devolucao.get('chave_nfe', ''),
                        'data_nf_solucao': nf_devolucao.get('data_emissao'),
                        'cnpj_emitente': cnpj_emitente,
                        'nome_emitente': nf_devolucao.get('nome_emitente', ''),
                        'info_complementar': nf_devolucao.get('info_complementar', ''),
                        'vinculacao': 'AUTOMATICO',
                        'odoo_dfe_id': nf_devolucao.get('odoo_dfe_id'),
                        'observacao': f'Match automático: NF {nf_ref} referenciada nas info complementares'
                    },
                    usuario='SISTEMA'
                )
                resultado['sugestao_id'] = solucao.id

                logger.info(
                    f"   ✓ Vinculação automática criada: "
                    f"NF retorno → NF remessa #{nf_remessa.id}"
                )

            except Exception as e:
                logger.error(f"Erro ao criar vinculação automática: {e}")

        return resultado

    def _calcular_score_match(
        self,
        nf_remessa: PalletNFRemessa,
        nf_devolucao: Dict,
        nf_referenciada: str = None
    ) -> Tuple[int, str]:
        """
        Calcula score de match entre NF remessa e NF devolução.

        Critérios de pontuação:
        - Match por número de NF referenciada: +50 pontos
        - CNPJ corresponde exatamente: +30 pontos
        - Quantidade compatível: +20 pontos

        Args:
            nf_remessa: NF de remessa candidata
            nf_devolucao: Dados da NF de devolução
            nf_referenciada: Número de NF referenciada (se encontrado)

        Returns:
            Tuple[int, str]: (score 0-100, motivo do score)
        """
        score = 0
        motivos = []

        # Match por número de NF referenciada (+50)
        if nf_referenciada and nf_remessa.numero_nf == nf_referenciada:
            score += 50
            motivos.append("NF referenciada nas info complementares")

        # CNPJ corresponde (+30)
        # Já filtrado na query, mas confirma
        if nf_remessa.cnpj_destinatario == nf_devolucao.get('cnpj_emitente', ''):
            score += 30
            motivos.append("CNPJ correspondente")

        # Quantidade compatível (+20)
        qtd_devolvida = nf_devolucao.get('quantidade', 0)
        if nf_remessa.qtd_pendente >= qtd_devolvida:
            score += 20
            motivos.append("Quantidade compatível")
        elif nf_remessa.qtd_pendente > 0:
            # Quantidade parcial, reduz pontuação
            score += 10
            motivos.append("Quantidade parcialmente compatível")

        motivo_final = "; ".join(motivos) if motivos else "Sem critérios de match"

        return score, motivo_final

    def _criar_sugestao_vinculacao(
        self,
        nf_remessa: PalletNFRemessa,
        nf_devolucao: Dict,
        quantidade_sugerida: int
    ) -> PalletNFSolucao:
        """
        Cria uma sugestão de vinculação para confirmação do usuário.

        Args:
            nf_remessa: NF de remessa
            nf_devolucao: Dados da NF de devolução
            quantidade_sugerida: Quantidade a vincular

        Returns:
            PalletNFSolucao: Sugestão criada
        """
        return NFService.registrar_solucao_nf(
            nf_remessa_id=nf_remessa.id,
            tipo='DEVOLUCAO',
            quantidade=quantidade_sugerida,
            dados={
                'numero_nf_solucao': nf_devolucao.get('numero_nf', ''),
                'serie_nf_solucao': nf_devolucao.get('serie', ''),
                'chave_nfe_solucao': nf_devolucao.get('chave_nfe', ''),
                'data_nf_solucao': nf_devolucao.get('data_emissao'),
                'cnpj_emitente': nf_devolucao.get('cnpj_emitente', ''),
                'nome_emitente': nf_devolucao.get('nome_emitente', ''),
                'info_complementar': nf_devolucao.get('info_complementar', ''),
                'vinculacao': 'SUGESTAO',
                'odoo_dfe_id': nf_devolucao.get('odoo_dfe_id'),
                'observacao': 'Sugestão automática - aguardando confirmação'
            },
            usuario='SISTEMA'
        )

    # =========================================================================
    # CONFIRMAÇÃO E REJEIÇÃO DE VINCULAÇÃO
    # =========================================================================

    def confirmar_vinculacao(
        self,
        nf_solucao_id: int,
        usuario: str
    ) -> PalletNFSolucao:
        """
        Confirma uma sugestão de vinculação.

        Delegate para NFService.confirmar_sugestao().

        Args:
            nf_solucao_id: ID da solução (sugestão)
            usuario: Usuário que está confirmando

        Returns:
            PalletNFSolucao: Solução confirmada
        """
        return NFService.confirmar_sugestao(nf_solucao_id, usuario)

    def rejeitar_sugestao(
        self,
        nf_solucao_id: int,
        motivo: str,
        usuario: str
    ) -> PalletNFSolucao:
        """
        Rejeita uma sugestão de vinculação.

        Delegate para NFService.rejeitar_sugestao().

        Args:
            nf_solucao_id: ID da solução (sugestão)
            motivo: Motivo da rejeição
            usuario: Usuário que está rejeitando

        Returns:
            PalletNFSolucao: Solução rejeitada
        """
        return NFService.rejeitar_sugestao(nf_solucao_id, motivo, usuario)

    # =========================================================================
    # VINCULAÇÃO MANUAL
    # =========================================================================

    def vincular_devolucao_manual_multiplas(
        self,
        nf_remessa_ids: List[int],
        nf_devolucao: Dict,
        quantidades: Dict[int, int],
        usuario: str
    ) -> List[PalletNFSolucao]:
        """
        Vincula manualmente uma NF de devolução a múltiplas NFs de remessa (1:N).

        Args:
            nf_remessa_ids: Lista de IDs das NFs de remessa
            nf_devolucao: Dados da NF de devolução
            quantidades: Dict {nf_remessa_id: quantidade} para cada NF
            usuario: Usuário que está vinculando

        Returns:
            List[PalletNFSolucao]: Lista de soluções criadas

        Raises:
            ValueError: Se quantidade total não bate ou NF não encontrada
        """
        qtd_total_devolucao = nf_devolucao.get('quantidade', 0)
        qtd_total_vinculada = sum(quantidades.values())

        if qtd_total_vinculada > qtd_total_devolucao:
            raise ValueError(
                f"Quantidade vinculada ({qtd_total_vinculada}) maior que "
                f"quantidade devolvida ({qtd_total_devolucao})"
            )

        logger.info(
            f"🔗 Vinculando NF devolução {nf_devolucao.get('numero_nf')} "
            f"a {len(nf_remessa_ids)} NFs de remessa (usuario: {usuario})"
        )

        solucoes = []

        for nf_remessa_id in nf_remessa_ids:
            quantidade = quantidades.get(nf_remessa_id, 0)
            if quantidade <= 0:
                continue

            try:
                # Aceita campos com nomes novos (numero_nf_solucao) ou antigos (numero_nf) para compatibilidade
                solucao = NFService.registrar_solucao_nf(
                    nf_remessa_id=nf_remessa_id,
                    tipo='DEVOLUCAO',
                    quantidade=quantidade,
                    dados={
                        'numero_nf_solucao': nf_devolucao.get('numero_nf_solucao') or nf_devolucao.get('numero_nf', ''),
                        'serie_nf_solucao': nf_devolucao.get('serie_nf_solucao') or nf_devolucao.get('serie', ''),
                        'chave_nfe_solucao': nf_devolucao.get('chave_nfe_solucao') or nf_devolucao.get('chave_nfe', ''),
                        'data_nf_solucao': nf_devolucao.get('data_nf_solucao') or nf_devolucao.get('data_emissao'),
                        'cnpj_emitente': nf_devolucao.get('cnpj_emitente', ''),
                        'nome_emitente': nf_devolucao.get('nome_emitente', ''),
                        'info_complementar': nf_devolucao.get('info_complementar', ''),
                        'vinculacao': 'MANUAL',
                        'odoo_dfe_id': nf_devolucao.get('odoo_dfe_id'),
                        'observacao': f'Vinculação manual por {usuario}'
                    },
                    usuario=usuario
                )
                solucoes.append(solucao)

                logger.info(
                    f"   ✓ NF remessa #{nf_remessa_id} vinculada ({quantidade} pallets)"
                )

            except ValueError as e:
                # Validação de negócio (ex.: quantidade > pendente) — não é bug,
                # é tentativa inválida do usuário. WARNING evita ruído no Sentry
                # (PYTHON-FLASK-2A); o route trata o raise e responde ao usuário.
                logger.warning(
                    f"   ✗ Vínculo rejeitado NF remessa #{nf_remessa_id}: {e}"
                )
                raise
            except Exception as e:
                logger.error(
                    f"   ✗ Erro ao vincular NF remessa #{nf_remessa_id}: {e}"
                )
                raise

        return solucoes

    def vincular_devolucao_manual(
        self,
        nf_remessa_id: int,
        nf_devolucao: Dict,
        quantidade: int,
        usuario: str
    ) -> PalletNFSolucao:
        """
        Vincula manualmente uma NF de devolução a uma NF de remessa.

        Args:
            nf_remessa_id: ID da NF de remessa
            nf_devolucao: Dados da NF de devolução
            quantidade: Quantidade a vincular
            usuario: Usuário que está vinculando

        Returns:
            PalletNFSolucao: Solução criada

        Raises:
            ValueError: Se NF não encontrada ou quantidade inválida
        """
        logger.info(
            f"🔗 Vinculando NF devolução {nf_devolucao.get('numero_nf')} "
            f"a NF remessa #{nf_remessa_id} (usuario: {usuario})"
        )

        # Aceita campos com nomes novos (numero_nf_solucao) ou antigos (numero_nf) para compatibilidade
        return NFService.registrar_solucao_nf(
            nf_remessa_id=nf_remessa_id,
            tipo='DEVOLUCAO',
            quantidade=quantidade,
            dados={
                'numero_nf_solucao': nf_devolucao.get('numero_nf_solucao') or nf_devolucao.get('numero_nf', ''),
                'serie_nf_solucao': nf_devolucao.get('serie_nf_solucao') or nf_devolucao.get('serie', ''),
                'chave_nfe_solucao': nf_devolucao.get('chave_nfe_solucao') or nf_devolucao.get('chave_nfe', ''),
                'data_nf_solucao': nf_devolucao.get('data_nf_solucao') or nf_devolucao.get('data_emissao'),
                'cnpj_emitente': nf_devolucao.get('cnpj_emitente', ''),
                'nome_emitente': nf_devolucao.get('nome_emitente', ''),
                'info_complementar': nf_devolucao.get('info_complementar', ''),
                'vinculacao': 'MANUAL',
                'odoo_dfe_id': nf_devolucao.get('odoo_dfe_id'),
                'observacao': f'Vinculação manual por {usuario}'
            },
            usuario=usuario
        )

    # =========================================================================
    # PROCESSAMENTO EM LOTE
    # =========================================================================

    def processar_devolucoes_pendentes(
        self,
        data_de: str = None,
        data_ate: str = None,
        criar_sugestoes: bool = True
    ) -> Dict:
        """
        Processa todas as NFs de devolução de pallet pendentes.

        Busca NFs no DFe, identifica tipo (devolução/retorno) e cria sugestões.

        Args:
            data_de: Data inicial
            data_ate: Data final
            criar_sugestoes: Se True, cria sugestões de vinculação

        Returns:
            Dict: Resumo do processamento
                {
                    'processadas': int,
                    'devolucoes': int,
                    'retornos': int,
                    'retornos_automaticos': int,
                    'sugestoes_criadas': int,
                    'sem_match': int,
                    'erros': int,
                    'detalhes': [...]
                }
        """
        logger.info("🔄 Iniciando processamento de devoluções de pallet pendentes")

        resumo = {
            'processadas': 0,
            'devolucoes': 0,
            'retornos': 0,
            'retornos_automaticos': 0,
            'sugestoes_criadas': 0,
            'sem_match': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar NFs de devolução
            nfs_devolucao = self.buscar_nfs_devolucao_pallet_dfe(
                data_de=data_de,
                data_ate=data_ate,
                apenas_nao_processadas=True
            )

            for nf in nfs_devolucao:
                resumo['processadas'] += 1

                try:
                    # Se tem referência à NF original, tenta match automático
                    nf_ref = nf.get('nf_remessa_referenciada')
                    if nf_ref:
                        resultado = self.sugerir_vinculacao_devolucao_com_referencia(
                            nf_devolucao=nf,
                            criar_sugestao=criar_sugestoes
                        )

                        if resultado and resultado.get('sugestao_id'):
                            resumo['devolucoes'] += 1
                            resumo['sugestoes_criadas'] += 1
                            resumo['detalhes'].append({
                                'tipo': 'DEVOLUCAO',
                                'nf': nf.get('numero_nf'),
                                'status': 'VINCULADO_AUTOMATICO',
                                'nf_remessa_id': resultado['nf_remessa_id']
                            })
                            continue  # Já processou, vai para próxima NF

                    # Processar como devolução padrão (sugestão por CNPJ)
                    resumo['devolucoes'] += 1

                    candidatas = self.sugerir_vinculacao_devolucao(
                        nf_devolucao=nf,
                        criar_sugestao=criar_sugestoes
                    )

                    sugestoes_nf = [c for c in candidatas if c.get('sugestao_id')]

                    if sugestoes_nf:
                        resumo['sugestoes_criadas'] += len(sugestoes_nf)
                        resumo['detalhes'].append({
                            'tipo': 'DEVOLUCAO',
                            'nf': nf.get('numero_nf'),
                            'status': 'SUGESTOES_CRIADAS',
                            'quantidade_sugestoes': len(sugestoes_nf)
                        })
                    else:
                        resumo['sem_match'] += 1
                        resumo['detalhes'].append({
                            'tipo': 'DEVOLUCAO',
                            'nf': nf.get('numero_nf'),
                            'status': 'SEM_MATCH',
                            'motivo': 'Nenhuma NF de remessa candidata'
                        })

                except Exception as e:
                    resumo['erros'] += 1
                    resumo['detalhes'].append({
                        'tipo': nf.get('tipo_sugestao', 'DESCONHECIDO'),
                        'nf': nf.get('numero_nf'),
                        'status': 'ERRO',
                        'motivo': str(e)
                    })
                    logger.error(
                        f"Erro ao processar NF {nf.get('numero_nf')}: {e}"
                    )

            logger.info(
                f"✅ Processamento concluído: "
                f"{resumo['processadas']} NFs processadas, "
                f"{resumo['sugestoes_criadas']} sugestões criadas, "
                f"{resumo['retornos_automaticos']} retornos automáticos"
            )

            return resumo

        except Exception as e:
            logger.error(f"Erro ao processar devoluções pendentes: {e}")
            raise

    # =========================================================================
    # PROCESSAMENTO DE NOTAS DE CRÉDITO E CANCELADAS (SCHEDULER)
    # =========================================================================

    def processar_ncs_pallet(
        self,
        data_de: str = None,
        data_ate: str = None
    ) -> Dict:
        """
        Processa NCs de pallet e vincula às NFs de remessa via reversed_entry_id.

        Este método é chamado pelo scheduler para:
        1. Buscar NCs de pallet do Odoo
        2. Identificar a NF de remessa original via reversed_entry_id
        3. Criar PalletNFSolucao tipo=NOTA_CREDITO com vinculação automática

        Args:
            data_de: Data inicial (YYYY-MM-DD). Default: últimos 90 dias
            data_ate: Data final (YYYY-MM-DD). Default: hoje

        Returns:
            Dict: Resumo do processamento
                {
                    'ncs_encontradas': int,
                    'ncs_vinculadas': int,
                    'ncs_sem_remessa': int,
                    'erros': int,
                    'detalhes': [...]
                }
        """
        logger.info("🔄 Iniciando processamento de NCs de pallet")

        resumo = {
            'ncs_encontradas': 0,
            'ncs_vinculadas': 0,
            'ncs_sem_remessa': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar NCs de pallet
            ncs = self.buscar_notas_credito_pallet(
                data_de=data_de,
                data_ate=data_ate,
                apenas_nao_processadas=True
            )

            resumo['ncs_encontradas'] = len(ncs)
            logger.info(f"   📄 Encontradas {len(ncs)} NCs de pallet para processar")

            for nc in ncs:
                try:
                    nf_remessa_original_id = nc.get('nf_remessa_original_id')

                    if not nf_remessa_original_id:
                        resumo['ncs_sem_remessa'] += 1
                        resumo['detalhes'].append({
                            'nc': nc.get('numero_nf'),
                            'status': 'SEM_VINCULO',
                            'motivo': 'NC sem reversed_entry_id'
                        })
                        continue

                    # Buscar NF de remessa local pelo odoo_account_move_id
                    nf_remessa = PalletNFRemessa.query.filter(
                        PalletNFRemessa.odoo_account_move_id == nf_remessa_original_id,
                        PalletNFRemessa.ativo == True
                    ).first()

                    if not nf_remessa:
                        # NF de remessa não existe localmente - pode ser de outro tipo
                        resumo['ncs_sem_remessa'] += 1
                        resumo['detalhes'].append({
                            'nc': nc.get('numero_nf'),
                            'status': 'REMESSA_NAO_ENCONTRADA',
                            'motivo': f'NF remessa Odoo ID {nf_remessa_original_id} não encontrada localmente'
                        })
                        continue

                    # Verificar se já existe solução para esta NC
                    solucao_existente = PalletNFSolucao.query.filter(
                        PalletNFSolucao.odoo_account_move_id == nc.get('odoo_account_move_id'),
                        PalletNFSolucao.ativo == True
                    ).first()

                    if solucao_existente:
                        logger.debug(f"   ℹ️ NC {nc.get('numero_nf')} já processada")
                        continue

                    # Criar PalletNFSolucao com vinculação automática
                    solucao = PalletNFSolucao(
                        nf_remessa_id=nf_remessa.id,
                        tipo='NOTA_CREDITO',
                        quantidade=nc.get('quantidade', 1),
                        numero_nf_solucao=nc.get('numero_nf'),
                        chave_nfe_solucao=nc.get('chave_nfe'),
                        data_nf_solucao=nc.get('data_emissao'),
                        odoo_account_move_id=nc.get('odoo_account_move_id'),
                        cnpj_emitente=nc.get('cnpj_destinatario'),  # Destinatário da NC = Emitente original
                        nome_emitente=nc.get('nome_destinatario'),
                        vinculacao='AUTOMATICO',
                        confirmado=True,  # Vinculação automática é confirmada
                        criado_por='SCHEDULER',
                        observacao=f'NC vinculada automaticamente à NF remessa #{nf_remessa.numero_nf}'
                    )

                    db.session.add(solucao)

                    # Atualizar quantidade resolvida na NF de remessa
                    nf_remessa.qtd_resolvida = (nf_remessa.qtd_resolvida or 0) + nc.get('quantidade', 1)
                    if nf_remessa.qtd_resolvida >= nf_remessa.quantidade:
                        nf_remessa.status = 'RESOLVIDA'

                    resumo['ncs_vinculadas'] += 1
                    resumo['detalhes'].append({
                        'nc': nc.get('numero_nf'),
                        'nf_remessa': nf_remessa.numero_nf,
                        'status': 'VINCULADA',
                        'quantidade': nc.get('quantidade', 1)
                    })

                    logger.debug(
                        f"   ✓ NC {nc.get('numero_nf')} vinculada à NF remessa {nf_remessa.numero_nf}"
                    )

                except Exception as e:
                    resumo['erros'] += 1
                    resumo['detalhes'].append({
                        'nc': nc.get('numero_nf'),
                        'status': 'ERRO',
                        'motivo': str(e)
                    })
                    logger.error(f"Erro ao processar NC {nc.get('numero_nf')}: {e}")

            db.session.commit()

            logger.info(
                f"✅ Processamento de NCs concluído: "
                f"{resumo['ncs_vinculadas']} vinculadas, "
                f"{resumo['ncs_sem_remessa']} sem remessa, "
                f"{resumo['erros']} erros"
            )

            return resumo

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao processar NCs de pallet: {e}")
            raise

    def processar_canceladas_pallet(
        self,
        data_de: str = None,
        data_ate: str = None
    ) -> Dict:
        """
        Processa NFs de pallet canceladas do Odoo.

        Este método é chamado pelo scheduler para:
        1. Buscar NFs canceladas do Odoo (state='cancel')
        2. Criar PalletNFSolucao tipo=CANCELAMENTO para auditoria

        Args:
            data_de: Data inicial (YYYY-MM-DD). Default: últimos 90 dias
            data_ate: Data final (YYYY-MM-DD). Default: hoje

        Returns:
            Dict: Resumo do processamento
        """
        logger.info("🔄 Iniciando processamento de NFs canceladas de pallet")

        resumo = {
            'canceladas_encontradas': 0,
            'canceladas_registradas': 0,
            'ja_existentes': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar NFs canceladas
            canceladas = self.buscar_nfs_pallet_canceladas(
                data_de=data_de,
                data_ate=data_ate,
                apenas_nao_processadas=True
            )

            resumo['canceladas_encontradas'] = len(canceladas)
            logger.info(f"   📄 Encontradas {len(canceladas)} NFs canceladas para processar")

            for nf in canceladas:
                try:
                    # Verificar se já existe registro
                    existente = PalletNFSolucao.query.filter(
                        PalletNFSolucao.odoo_account_move_id == nf.get('odoo_account_move_id'),
                        PalletNFSolucao.ativo == True
                    ).first()

                    if existente:
                        resumo['ja_existentes'] += 1
                        continue

                    # Buscar NF de remessa correspondente (se existir)
                    nf_remessa = PalletNFRemessa.query.filter(
                        PalletNFRemessa.odoo_account_move_id == nf.get('odoo_account_move_id'),
                        PalletNFRemessa.ativo == True
                    ).first()

                    nf_remessa_id = nf_remessa.id if nf_remessa else None

                    # Criar registro de cancelamento
                    # Se não tem nf_remessa_id, criar registro para auditoria
                    if nf_remessa_id:
                        solucao = PalletNFSolucao(
                            nf_remessa_id=nf_remessa_id,
                            tipo='CANCELAMENTO',
                            quantidade=nf.get('quantidade', 1),
                            numero_nf_solucao=nf.get('numero_nf'),
                            chave_nfe_solucao=nf.get('chave_nfe'),
                            data_nf_solucao=nf.get('data_emissao'),
                            odoo_account_move_id=nf.get('odoo_account_move_id'),
                            cnpj_emitente=nf.get('cnpj_destinatario'),
                            nome_emitente=nf.get('nome_destinatario'),
                            vinculacao='AUTOMATICO',
                            confirmado=True,
                            criado_por='SCHEDULER',
                            observacao='NF cancelada no Odoo - importada automaticamente'
                        )

                        db.session.add(solucao)

                        # Marcar NF de remessa como cancelada
                        nf_remessa.cancelada = True
                        nf_remessa.status = 'CANCELADA'

                        resumo['canceladas_registradas'] += 1
                        resumo['detalhes'].append({
                            'nf': nf.get('numero_nf'),
                            'status': 'REGISTRADA',
                            'nf_remessa': nf_remessa.numero_nf
                        })
                    else:
                        # NF cancelada sem remessa local - apenas log
                        resumo['detalhes'].append({
                            'nf': nf.get('numero_nf'),
                            'status': 'SEM_REMESSA_LOCAL',
                            'motivo': 'NF cancelada não tem remessa correspondente'
                        })

                except Exception as e:
                    resumo['erros'] += 1
                    resumo['detalhes'].append({
                        'nf': nf.get('numero_nf'),
                        'status': 'ERRO',
                        'motivo': str(e)
                    })
                    logger.error(f"Erro ao processar NF cancelada {nf.get('numero_nf')}: {e}")

            db.session.commit()

            logger.info(
                f"✅ Processamento de canceladas concluído: "
                f"{resumo['canceladas_registradas']} registradas, "
                f"{resumo['ja_existentes']} já existentes"
            )

            return resumo

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao processar NFs canceladas: {e}")
            raise
