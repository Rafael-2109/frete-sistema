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

from app.pallet.models.nf_remessa import PalletNFRemessa
from app.pallet.models.nf_solucao import PalletNFSolucao
from app.pallet.services.nf_service import NFService

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

    @property
    def odoo(self):
        """Lazy loading do cliente Odoo."""
        if self._odoo_client is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._odoo_client = get_odoo_connection()
        return self._odoo_client

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
                    'tipo_sugestao': str,  # 'DEVOLUCAO' ou 'RETORNO'
                    'nf_remessa_referenciada': str  # Se encontrada em info complementar
                }
        """
        from datetime import timedelta

        if not data_de:
            data_de = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not data_ate:
            data_ate = datetime.now().strftime('%Y-%m-%d')

        logger.info(
            f"🔍 Buscando NFs de devolução de pallet no DFe "
            f"(período: {data_de} a {data_ate})"
        )

        resultado = []

        try:
            # Buscar DFEs de entrada (finnfe=4) no período
            # Campos disponíveis no modelo l10n_br_fiscal.document do Odoo
            domain = [
                ('document_type_id.code', 'in', ['55']),  # NF-e
                ('state_edoc', '=', 'autorizada'),
                ('date', '>=', data_de),
                ('date', '<=', data_ate),
            ]

            campos = [
                'id', 'number', 'document_serie', 'document_key',
                'date', 'partner_id', 'partner_cnpj_cpf',
                'fiscal_additional_data', 'amount_total'
            ]

            # Buscar documentos fiscais
            documentos = self.odoo.search_read(
                'l10n_br_fiscal.document', domain, campos
            )

            logger.info(f"   📄 Encontrados {len(documentos)} documentos fiscais")

            # Para cada documento, verificar se tem linha de pallet
            for doc in documentos:
                try:
                    # Verificar se é NF de pallet pelas linhas
                    if not self._eh_nf_devolucao_pallet(doc['id']):
                        continue

                    # Limpar CNPJ
                    cnpj_emitente = self._limpar_cnpj(
                        doc.get('partner_cnpj_cpf', '')
                    )

                    # Ignorar intercompany
                    if self._eh_intercompany(cnpj_emitente):
                        continue

                    # Verificar se já processada
                    if apenas_nao_processadas:
                        if self._nf_ja_processada(doc.get('document_key', '')):
                            continue

                    # Extrair informações
                    info_complementar = doc.get('fiscal_additional_data', '') or ''
                    nf_remessa_ref = self._extrair_nf_referencia(info_complementar)
                    tipo_sugestao = 'RETORNO' if nf_remessa_ref else 'DEVOLUCAO'

                    # Obter quantidade de pallets das linhas
                    qtd_pallets = self._obter_quantidade_pallets_linhas(doc['id'])

                    nf_data = {
                        'odoo_dfe_id': doc['id'],
                        'numero_nf': str(doc.get('number', '')),
                        'serie': str(doc.get('document_serie', '')),
                        'chave_nfe': doc.get('document_key', ''),
                        'data_emissao': doc.get('date'),
                        'cnpj_emitente': cnpj_emitente,
                        'nome_emitente': (
                            doc.get('partner_id', [None, ''])[1]
                            if isinstance(doc.get('partner_id'), (list, tuple))
                            else ''
                        ),
                        'quantidade': qtd_pallets,
                        'valor_total': Decimal(str(doc.get('amount_total', 0))),
                        'info_complementar': info_complementar,
                        'tipo_sugestao': tipo_sugestao,
                        'nf_remessa_referenciada': nf_remessa_ref
                    }

                    resultado.append(nf_data)
                    logger.debug(
                        f"   ✓ NF {nf_data['numero_nf']} identificada como {tipo_sugestao}"
                    )

                except Exception as e:
                    logger.warning(
                        f"   ⚠️ Erro ao processar documento #{doc.get('id')}: {e}"
                    )
                    continue

            logger.info(
                f"   📦 Total de NFs de devolução de pallet encontradas: {len(resultado)}"
            )

            return resultado

        except Exception as e:
            logger.error(f"Erro ao buscar NFs de devolução de pallet: {e}")
            raise

    def _eh_nf_devolucao_pallet(self, document_id: int) -> bool:
        """
        Verifica se o documento fiscal é uma NF de devolução de pallet.

        Critérios:
        - Tem linha com CFOP de devolução de vasilhame (5920/6920/1920/2920)
        - OU tem linha com produto código 208000012

        Args:
            document_id: ID do documento fiscal no Odoo

        Returns:
            bool: True se é NF de devolução de pallet
        """
        try:
            # Buscar linhas do documento
            linhas = self.odoo.search_read(
                'l10n_br_fiscal.document.line',
                [('document_id', '=', document_id)],
                ['cfop_id', 'product_id', 'quantity']
            )

            for linha in linhas:
                # Verificar CFOP
                cfop_id = linha.get('cfop_id')
                if cfop_id:
                    cfop_code = self._obter_cfop_code(cfop_id[0] if isinstance(cfop_id, (list, tuple)) else cfop_id)
                    if cfop_code in CFOPS_DEVOLUCAO_PALLET:
                        return True

                # Verificar produto
                product_id = linha.get('product_id')
                if product_id:
                    prod_id = product_id[0] if isinstance(product_id, (list, tuple)) else product_id
                    if self._eh_produto_pallet(prod_id):
                        return True

            return False

        except Exception as e:
            logger.warning(f"Erro ao verificar se doc #{document_id} é pallet: {e}")
            return False

    def _obter_cfop_code(self, cfop_id: int) -> str:
        """Obtém o código do CFOP pelo ID."""
        try:
            cfop = self.odoo.search_read(
                'l10n_br_fiscal.cfop',
                [('id', '=', cfop_id)],
                ['code']
            )
            if cfop:
                return cfop[0].get('code', '')
            return ''
        except Exception:
            return ''

    def _eh_produto_pallet(self, product_id: int) -> bool:
        """Verifica se o produto é pallet pelo código."""
        try:
            produto = self.odoo.search_read(
                'product.product',
                [('id', '=', product_id)],
                ['default_code']
            )
            if produto:
                return produto[0].get('default_code', '') == COD_PRODUTO_PALLET
            return False
        except Exception:
            return False

    def _obter_quantidade_pallets_linhas(self, document_id: int) -> int:
        """Obtém a quantidade de pallets das linhas do documento."""
        try:
            linhas = self.odoo.search_read(
                'l10n_br_fiscal.document.line',
                [('document_id', '=', document_id)],
                ['cfop_id', 'product_id', 'quantity']
            )

            total = 0
            for linha in linhas:
                # Verificar se é linha de pallet (por CFOP ou produto)
                eh_pallet = False

                cfop_id = linha.get('cfop_id')
                if cfop_id:
                    cfop_code = self._obter_cfop_code(
                        cfop_id[0] if isinstance(cfop_id, (list, tuple)) else cfop_id
                    )
                    if cfop_code in CFOPS_DEVOLUCAO_PALLET:
                        eh_pallet = True

                if not eh_pallet:
                    product_id = linha.get('product_id')
                    if product_id:
                        prod_id = product_id[0] if isinstance(product_id, (list, tuple)) else product_id
                        if self._eh_produto_pallet(prod_id):
                            eh_pallet = True

                if eh_pallet:
                    total += int(linha.get('quantity', 0))

            return total

        except Exception as e:
            logger.warning(f"Erro ao obter quantidade de pallets: {e}")
            return 0

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

    def sugerir_vinculacao_retorno(
        self,
        nf_retorno: Dict,
        criar_sugestao: bool = True
    ) -> Optional[Dict]:
        """
        Sugere NF de remessa para vincular a uma NF de retorno (1:1).

        Para RETORNO, busca correspondência exata:
        1. Número da NF nas informações complementares
        2. Mesmo CNPJ destinatário
        3. Quantidade exata

        Args:
            nf_retorno: Dados da NF de retorno
            criar_sugestao: Se True, cria PalletNFSolucao com vinculacao='AUTOMATICO'
                           (retornos com match exato são confirmados automaticamente)

        Returns:
            Dict ou None: Candidata encontrada ou None
        """
        cnpj_emitente = nf_retorno.get('cnpj_emitente', '')
        quantidade = nf_retorno.get('quantidade', 0)
        nf_ref = nf_retorno.get('nf_remessa_referenciada')

        if not nf_ref:
            logger.info(
                f"   ℹ️ NF de retorno sem referência - tratando como devolução"
            )
            return None

        logger.info(
            f"🔍 Buscando NF de remessa {nf_ref} para retorno "
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

        # Criar sugestão automática (já confirmada para retorno com match exato)
        if criar_sugestao:
            try:
                # Para retorno com match exato, criar como AUTOMATICO (já confirmado)
                solucao = NFService.registrar_solucao_nf(
                    nf_remessa_id=nf_remessa.id,
                    tipo='RETORNO',
                    quantidade=min(quantidade, nf_remessa.qtd_pendente),
                    dados={
                        'numero_nf_solucao': nf_retorno.get('numero_nf', ''),
                        'serie_nf_solucao': nf_retorno.get('serie', ''),
                        'chave_nfe_solucao': nf_retorno.get('chave_nfe', ''),
                        'data_nf_solucao': nf_retorno.get('data_emissao'),
                        'cnpj_emitente': cnpj_emitente,
                        'nome_emitente': nf_retorno.get('nome_emitente', ''),
                        'info_complementar': nf_retorno.get('info_complementar', ''),
                        'vinculacao': 'AUTOMATICO',
                        'odoo_dfe_id': nf_retorno.get('odoo_dfe_id'),
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

    def vincular_devolucao_manual(
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
                solucao = NFService.registrar_solucao_nf(
                    nf_remessa_id=nf_remessa_id,
                    tipo='DEVOLUCAO',
                    quantidade=quantidade,
                    dados={
                        'numero_nf_solucao': nf_devolucao.get('numero_nf', ''),
                        'serie_nf_solucao': nf_devolucao.get('serie', ''),
                        'chave_nfe_solucao': nf_devolucao.get('chave_nfe', ''),
                        'data_nf_solucao': nf_devolucao.get('data_emissao'),
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

            except Exception as e:
                logger.error(
                    f"   ✗ Erro ao vincular NF remessa #{nf_remessa_id}: {e}"
                )
                raise

        return solucoes

    def vincular_retorno_manual(
        self,
        nf_remessa_id: int,
        nf_retorno: Dict,
        quantidade: int,
        usuario: str
    ) -> PalletNFSolucao:
        """
        Vincula manualmente uma NF de retorno a uma NF de remessa (1:1).

        Args:
            nf_remessa_id: ID da NF de remessa
            nf_retorno: Dados da NF de retorno
            quantidade: Quantidade a vincular
            usuario: Usuário que está vinculando

        Returns:
            PalletNFSolucao: Solução criada

        Raises:
            ValueError: Se NF não encontrada ou quantidade inválida
        """
        logger.info(
            f"🔗 Vinculando NF retorno {nf_retorno.get('numero_nf')} "
            f"a NF remessa #{nf_remessa_id} (usuario: {usuario})"
        )

        return NFService.registrar_solucao_nf(
            nf_remessa_id=nf_remessa_id,
            tipo='RETORNO',
            quantidade=quantidade,
            dados={
                'numero_nf_solucao': nf_retorno.get('numero_nf', ''),
                'serie_nf_solucao': nf_retorno.get('serie', ''),
                'chave_nfe_solucao': nf_retorno.get('chave_nfe', ''),
                'data_nf_solucao': nf_retorno.get('data_emissao'),
                'cnpj_emitente': nf_retorno.get('cnpj_emitente', ''),
                'nome_emitente': nf_retorno.get('nome_emitente', ''),
                'info_complementar': nf_retorno.get('info_complementar', ''),
                'vinculacao': 'MANUAL',
                'odoo_dfe_id': nf_retorno.get('odoo_dfe_id'),
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
                    if nf.get('tipo_sugestao') == 'RETORNO':
                        # Processar como retorno (1:1)
                        resumo['retornos'] += 1

                        resultado = self.sugerir_vinculacao_retorno(
                            nf_retorno=nf,
                            criar_sugestao=criar_sugestoes
                        )

                        if resultado and resultado.get('sugestao_id'):
                            resumo['retornos_automaticos'] += 1
                            resumo['detalhes'].append({
                                'tipo': 'RETORNO',
                                'nf': nf.get('numero_nf'),
                                'status': 'VINCULADO_AUTOMATICO',
                                'nf_remessa_id': resultado['nf_remessa_id']
                            })
                        elif resultado:
                            resumo['sem_match'] += 1
                            resumo['detalhes'].append({
                                'tipo': 'RETORNO',
                                'nf': nf.get('numero_nf'),
                                'status': 'SEM_MATCH',
                                'motivo': 'NF referenciada não encontrada'
                            })

                    else:
                        # Processar como devolução (1:N)
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
