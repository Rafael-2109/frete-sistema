"""
Service para Importacao de Reversoes de NF de Venda do Odoo
============================================================

OBJETIVO:
    Buscar Notas de Credito (out_refund) que revertem NFs de venda
    e criar ocorrencias de devolucao para elas no sistema.

FILTRO ODOO:
    move_type = 'out_refund' (Nota de Credito de venda)
    state = 'posted' (Publicada)
    reversed_entry_id != False (Tem NF original vinculada)

FLUXO:
    1. Buscar Notas de Credito no Odoo
    2. Para cada Nota de Credito:
       a) Buscar NF de Venda Original via reversed_entry_id
       b) Verificar se ja existe NFDevolucao para esta NF
       c) Se nao existe, criar NFDevolucao com tipo='NF'
       d) Vincular ao monitoramento se existir entrega

MODELO ODOO: account.move (com move_type='out_refund' e reversed_entry_id)

AUTOR: Sistema de Fretes - Modulo Devolucoes
DATA: 11/01/2026
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from app import db
from app.devolucao.models import NFDevolucao, OcorrenciaDevolucao
from app.monitoramento.models import EntregaMonitorada
from app.faturamento.models import FaturamentoProduto
from app.estoque.models import MovimentacaoEstoque
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc, agora_utc_naive

logger = logging.getLogger(__name__)

# CNPJs a excluir da importacao (La Famiglia e Nacom Goya - empresas internas)
CNPJS_EXCLUIDOS = {'18467441', '61724241'}


class ReversaoService:
    """
    Service para importacao de NFs de venda revertidas/canceladas do Odoo

    Uma NF de venda e considerada revertida quando existe uma Nota de Credito
    (out_refund) com reversed_entry_id apontando para ela.

    Fluxo:
    1. Busca Notas de Credito (out_refund) postadas com reversed_entry_id
    2. Para cada NC, busca a NF de Venda original
    3. Cria NFDevolucao com tipo_documento='NF' e status_odoo='Revertida'
    4. Tenta vincular ao monitoramento para sincronizar status
    """

    def __init__(self):
        """Inicializa conexao com Odoo"""
        self.odoo = get_odoo_connection()

    # =========================================================================
    # IMPORTACAO DE REVERSOES DO ODOO
    # =========================================================================

    def importar_reversoes(
        self,
        dias: int = 30,
        limite: Optional[int] = None
    ) -> Dict:
        """
        Importa NFs de venda revertidas do Odoo

        Args:
            dias: Quantos dias para tras buscar (padrao: 30)
            limite: Limite de registros (None = todos)

        Returns:
            Dict com estatisticas da importacao
        """
        logger.info("=" * 80)
        logger.info("INICIANDO IMPORTACAO DE REVERSOES (NF de Venda Revertidas)")
        logger.info("=" * 80)

        resultado = {
            'sucesso': False,
            'reversoes_processadas': 0,
            'nfds_criadas': 0,
            'nfds_atualizadas': 0,
            'vinculadas_monitoramento': 0,
            'ocorrencias_criadas': 0,
            # Novas metricas de estoque/faturamento
            'faturamento_marcados': 0,
            'movimentacoes_criadas': 0,
            'erros': []
        }

        try:
            # 1. Calcular data de corte
            data_corte = (agora_utc() - timedelta(days=dias)).strftime('%Y-%m-%d')
            logger.info(f"Periodo: ultimos {dias} dias (desde {data_corte})")

            # 2. Buscar Notas de Credito no Odoo
            notas_credito = self._buscar_notas_credito(data_corte, limite)

            if not notas_credito:
                logger.warning("Nenhuma Nota de Credito encontrada no Odoo")
                resultado['sucesso'] = True
                return resultado

            logger.info(f"Total de Notas de Credito encontradas: {len(notas_credito)}")

            # 3. Processar cada Nota de Credito
            for nc in notas_credito:
                try:
                    nc_id = nc.get('id')
                    nc_name = nc.get('name', f'NC-{nc_id}')
                    logger.info(f"\nProcessando NC: {nc_name} (ID {nc_id})")

                    estatisticas = self._processar_nota_credito(nc)

                    resultado['reversoes_processadas'] += 1

                    if estatisticas.get('criada'):
                        resultado['nfds_criadas'] += 1
                    if estatisticas.get('atualizada'):
                        resultado['nfds_atualizadas'] += 1
                    if estatisticas.get('vinculada_monitoramento'):
                        resultado['vinculadas_monitoramento'] += 1
                    if estatisticas.get('ocorrencia_criada'):
                        resultado['ocorrencias_criadas'] += 1
                    # Novas metricas de estoque/faturamento
                    resultado['faturamento_marcados'] += estatisticas.get('faturamento_marcados', 0)
                    resultado['movimentacoes_criadas'] += estatisticas.get('movimentacoes_criadas', 0)

                    # Commit apos cada NC processada
                    db.session.commit()

                except Exception as e:
                    db.session.rollback()
                    erro_msg = f"Erro ao processar NC {nc.get('id')}: {str(e)}"
                    logger.error(f"{erro_msg}")
                    resultado['erros'].append(erro_msg)

            resultado['sucesso'] = True
            logger.info("=" * 80)
            logger.info("IMPORTACAO DE REVERSOES CONCLUIDA")
            logger.info(f"   Processadas: {resultado['reversoes_processadas']}")
            logger.info(f"   NFDs criadas: {resultado['nfds_criadas']}")
            logger.info(f"   NFDs atualizadas: {resultado['nfds_atualizadas']}")
            logger.info(f"   Vinculadas ao monitoramento: {resultado['vinculadas_monitoramento']}")
            logger.info(f"   Ocorrencias criadas: {resultado['ocorrencias_criadas']}")
            logger.info(f"   Faturamentos marcados: {resultado['faturamento_marcados']}")
            logger.info(f"   Movimentacoes estoque criadas: {resultado['movimentacoes_criadas']}")
            logger.info(f"   Erros: {len(resultado['erros'])}")
            logger.info("=" * 80)

            return resultado

        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro fatal na importacao de reversoes: {str(e)}"
            logger.error(f"{erro_msg}")
            resultado['erros'].append(erro_msg)
            resultado['sucesso'] = False
            return resultado

    def _buscar_notas_credito(
        self,
        data_corte: str,
        limite: Optional[int] = None
    ) -> List[Dict]:
        """
        Busca Notas de Credito (out_refund) no Odoo

        Args:
            data_corte: Data minima
            limite: Limite de registros

        Returns:
            Lista de Notas de Credito
        """
        try:
            # Filtro: out_refund + posted + tem reversed_entry_id
            # IMPORTANTE: Exclui devoluções de vasilhame (pallet) que são tratadas no módulo de pallet
            filtros = [
                ('move_type', '=', 'out_refund'),
                ('state', '=', 'posted'),
                ('reversed_entry_id', '!=', False),
                ('invoice_date', '>=', data_corte),
                ('l10n_br_tipo_pedido', '!=', 'vasilhame'),  # Exclui devoluções de pallet
            ]

            logger.info(f"   Filtro: move_type='out_refund' AND state='posted' AND reversed_entry_id != False AND l10n_br_tipo_pedido != 'vasilhame' AND invoice_date >= {data_corte}")

            campos = [
                'id',
                'name',
                'partner_id',
                'amount_total',
                'amount_untaxed',
                'reversed_entry_id',
                'l10n_br_numero_nota_fiscal',
                'l10n_br_chave_nf',
                'invoice_origin',
                'invoice_date',
                'state',
                'payment_state',
            ]

            params = {'fields': campos}
            if limite:
                params['limit'] = limite

            notas_credito = self.odoo.execute_kw(
                'account.move',
                'search_read',
                [filtros],
                params
            )

            return notas_credito or []

        except Exception as e:
            logger.error(f"Erro ao buscar Notas de Credito: {e}")
            return []

    def _processar_nota_credito(self, nc_data: Dict) -> Dict:
        """
        Processa uma Nota de Credito e cria/atualiza NFDevolucao

        Args:
            nc_data: Dados da Nota de Credito do Odoo

        Returns:
            Dict com estatisticas
        """
        estatisticas = {
            'criada': False,
            'atualizada': False,
            'vinculada_monitoramento': False,
            'ocorrencia_criada': False,
        }

        nc_id = nc_data.get('id')
        reversed_entry_id = nc_data.get('reversed_entry_id')

        if not reversed_entry_id:
            logger.warning(f"   NC {nc_id} nao tem reversed_entry_id, ignorando")
            return estatisticas

        # O reversed_entry_id vem como [id, name] quando e many2one
        nf_original_id = reversed_entry_id[0] if isinstance(reversed_entry_id, list) else reversed_entry_id

        # 1. Buscar NF de Venda Original
        nf_original = self._buscar_nf_original(nf_original_id)

        if not nf_original:
            logger.warning(f"   NF original ID {nf_original_id} nao encontrada")
            return estatisticas

        numero_nf = nf_original.get('l10n_br_numero_nota_fiscal')
        chave_nf = nf_original.get('l10n_br_chave_nf')
        cnpj_parceiro = self._extrair_cnpj_parceiro(nf_original.get('partner_id'))

        logger.info(f"   NF Original: {numero_nf} (ID {nf_original_id})")

        # Verificar se CNPJ deve ser excluido
        if cnpj_parceiro:
            cnpj_prefixo = cnpj_parceiro[:8]
            if cnpj_prefixo in CNPJS_EXCLUIDOS:
                logger.info(f"   NC ignorada - CNPJ excluido: {cnpj_parceiro}")
                return estatisticas

        # 2. Verificar se ja existe NFDevolucao para esta NF
        nfd_existente = NFDevolucao.query.filter_by(
            odoo_nf_venda_id=nf_original_id
        ).first()

        if not nfd_existente and numero_nf:
            # Tentar por numero da NF
            nfd_existente = NFDevolucao.query.filter(
                NFDevolucao.numero_nf_venda == str(numero_nf),
                NFDevolucao.tipo_documento == 'NF'
            ).first()

        # 3. Buscar EntregaMonitorada
        entrega = None
        if numero_nf:
            entrega = EntregaMonitorada.query.filter_by(
                numero_nf=str(numero_nf)
            ).first()

        if nfd_existente:
            # Atualizar existente
            self._atualizar_nfd_reversao(nfd_existente, nc_data, nf_original, entrega)
            estatisticas['atualizada'] = True
            logger.info(f"   NFD atualizada: ID {nfd_existente.id}")
        else:
            # Criar nova
            nfd_existente = self._criar_nfd_reversao(nc_data, nf_original, entrega)
            estatisticas['criada'] = True
            logger.info(f"   NFD criada: ID {nfd_existente.id}")

            # Criar OcorrenciaDevolucao
            ocorrencia = self._criar_ocorrencia_automatica(nfd_existente)
            if ocorrencia:
                estatisticas['ocorrencia_criada'] = True
                logger.info(f"   Ocorrencia criada: {ocorrencia.numero_ocorrencia}")

        # 4. Atualizar entrega se existir
        if entrega:
            estatisticas['vinculada_monitoramento'] = True
            if not entrega.teve_devolucao:
                entrega.teve_devolucao = True
                logger.info(f"   Entrega {entrega.numero_nf} marcada como teve_devolucao=True")
            # Apenas se NF revertida (reversed_entry_id) e sem status prévio do monitoramento
            if not entrega.status_finalizacao:
                entrega.status_finalizacao = 'Devolvida'
                logger.info(f"   Entrega {entrega.numero_nf} status_finalizacao='Devolvida'")

        # 5. Processar reversao de estoque e faturamento
        if numero_nf:
            nc_id = nc_data.get('id')
            nc_name = nc_data.get('name', f'NC-{nc_id}')
            resultado_estoque = self.processar_reversao_estoque(
                numero_nf=str(numero_nf),
                nota_credito_id=nc_id,
                nota_credito_name=nc_name
            )
            if resultado_estoque.get('sucesso'):
                estatisticas['faturamento_marcados'] = resultado_estoque.get('faturamento_marcados', 0)
                estatisticas['movimentacoes_criadas'] = resultado_estoque.get('movimentacoes_criadas', 0)

        return estatisticas

    def _buscar_nf_original(self, nf_id: int) -> Optional[Dict]:
        """
        Busca NF de Venda original no Odoo

        Args:
            nf_id: ID da NF original

        Returns:
            Dict com dados da NF ou None
        """
        try:
            campos = [
                'id',
                'name',
                'partner_id',
                'amount_total',
                'amount_untaxed',
                'l10n_br_numero_nota_fiscal',
                'l10n_br_chave_nf',
                'invoice_date',
                'state',
            ]

            nfs = self.odoo.execute_kw(
                'account.move',
                'search_read',
                [[('id', '=', nf_id)]],
                {'fields': campos, 'limit': 1}
            )

            return nfs[0] if nfs else None

        except Exception as e:
            logger.error(f"Erro ao buscar NF original {nf_id}: {e}")
            return None

    def _buscar_itens_nf_original(self, nf_id: int) -> List[Dict]:
        """
        Busca os itens (invoice_line_ids) da NF original no Odoo

        Args:
            nf_id: ID do account.move no Odoo

        Returns:
            Lista de dicts com dados dos itens
        """
        try:
            # Buscar linhas da NF no Odoo
            linhas = self.odoo.execute_kw(
                'account.move.line',
                'search_read',
                [[
                    ('move_id', '=', nf_id),
                    ('display_type', '=', 'product'),  # Apenas linhas de produto
                ]],
                {'fields': [
                    'product_id',
                    'name',
                    'quantity',
                    'price_unit',
                    'price_subtotal',
                    'product_uom_id',
                ]}
            )
            return linhas or []
        except Exception as e:
            logger.error(f"Erro ao buscar itens da NF {nf_id}: {e}")
            return []

    def _criar_linhas_reversao(self, nfd: NFDevolucao, itens: List[Dict]) -> int:
        """
        Cria NFDevolucaoLinha para cada item da NF revertida

        Args:
            nfd: Instância de NFDevolucao
            itens: Lista de itens do Odoo

        Returns:
            Quantidade de linhas criadas
        """
        from app.devolucao.models import NFDevolucaoLinha

        linhas_criadas = 0

        for item in itens:
            try:
                # Extrair dados do produto
                product_id = item.get('product_id')
                if product_id and isinstance(product_id, (list, tuple)):
                    cod_produto = str(product_id[0])
                    nome_produto = product_id[1] if len(product_id) > 1 else item.get('name', '')
                else:
                    cod_produto = str(product_id) if product_id else ''
                    nome_produto = item.get('name', '')

                quantidade = Decimal(str(item.get('quantity', 0)))
                valor_unitario = Decimal(str(item.get('price_unit', 0)))
                valor_total = Decimal(str(item.get('price_subtotal', 0)))

                # Extrair unidade de medida
                uom = item.get('product_uom_id')
                unidade = uom[1] if uom and isinstance(uom, (list, tuple)) and len(uom) > 1 else 'UN'

                # Criar linha - usando campos corretos do modelo
                linha = NFDevolucaoLinha(
                    nf_devolucao_id=nfd.id,
                    # Código do cliente (original) = código interno pois é nossa NF
                    codigo_produto_cliente=cod_produto,
                    descricao_produto_cliente=nome_produto,
                    # Código interno = mesmo código (já resolvido pois é nossa NF)
                    codigo_produto_interno=cod_produto,
                    descricao_produto_interno=nome_produto,
                    produto_resolvido=True,  # Já resolvido (é nossa NF)
                    metodo_resolucao='ODOO',  # Indica origem da resolução
                    # Quantidades
                    quantidade=quantidade,
                    unidade_medida=unidade,
                    valor_unitario=valor_unitario,
                    valor_total=valor_total,
                )
                db.session.add(linha)
                linhas_criadas += 1

            except Exception as e:
                logger.error(f"Erro ao criar linha para item {item}: {e}")
                continue

        return linhas_criadas

    def _criar_nf_referenciada(self, nfd: NFDevolucao, nf_original: Dict) -> bool:
        """
        Cria NFDevolucaoNFReferenciada para vincular a NF original

        Args:
            nfd: Instância de NFDevolucao
            nf_original: Dados da NF original do Odoo

        Returns:
            True se criou, False se já existia ou erro
        """
        from app.devolucao.models import NFDevolucaoNFReferenciada

        try:
            numero_nf = nf_original.get('l10n_br_numero_nota_fiscal')
            if not numero_nf:
                return False

            # Verificar se já existe
            existente = NFDevolucaoNFReferenciada.query.filter_by(
                nf_devolucao_id=nfd.id,
                numero_nf=str(numero_nf)
            ).first()

            if existente:
                return False

            # Buscar EntregaMonitorada se existir
            entrega_id = None
            entrega = EntregaMonitorada.query.filter_by(
                numero_nf=str(numero_nf)
            ).first()
            if entrega:
                entrega_id = entrega.id

            # Extrair data de emissão
            data_emissao = self._parse_date(nf_original.get('invoice_date'))

            # Criar vínculo - usando campos corretos do modelo
            ref = NFDevolucaoNFReferenciada(
                nf_devolucao_id=nfd.id,
                numero_nf=str(numero_nf),
                serie_nf='1',  # Série padrão
                chave_nf=nf_original.get('l10n_br_chave_nf'),
                data_emissao_nf=data_emissao,
                origem='ODOO_REVERSAO',  # Nova origem para identificar reversões
                entrega_monitorada_id=entrega_id,
            )
            db.session.add(ref)
            return True

        except Exception as e:
            logger.error(f"Erro ao criar NF referenciada: {e}")
            return False

    def _extrair_cnpj_parceiro(self, partner_id) -> Optional[str]:
        """
        Extrai CNPJ do parceiro

        Args:
            partner_id: ID ou [id, name] do parceiro

        Returns:
            CNPJ limpo ou None
        """
        if not partner_id:
            return None

        try:
            p_id = partner_id[0] if isinstance(partner_id, list) else partner_id

            parceiro = self.odoo.execute_kw(
                'res.partner',
                'search_read',
                [[('id', '=', p_id)]],
                {'fields': ['l10n_br_cnpj'], 'limit': 1}
            )

            if parceiro:
                cnpj = parceiro[0].get('l10n_br_cnpj')
                if cnpj:
                    return self._limpar_cnpj(cnpj)

            return None

        except Exception as e:
            logger.error(f"Erro ao extrair CNPJ do parceiro: {e}")
            return None

    def _atualizar_nfd_reversao(
        self,
        nfd: NFDevolucao,
        nc_data: Dict,
        nf_original: Dict,
        entrega: Optional[EntregaMonitorada]
    ):
        """
        Atualiza NFDevolucao existente com dados da reversao

        Args:
            nfd: NFDevolucao a atualizar
            nc_data: Dados da Nota de Credito
            nf_original: Dados da NF original
            entrega: EntregaMonitorada vinculada (opcional)
        """
        # Tipo e status
        nfd.tipo_documento = 'NF'
        nfd.status_odoo = 'Revertida'

        # IDs do Odoo
        nfd.odoo_nf_venda_id = nf_original.get('id')
        nfd.odoo_nota_credito_id = nc_data.get('id')

        # Numero e chave
        nfd.numero_nf_venda = nf_original.get('l10n_br_numero_nota_fiscal')
        nfd.chave_nfd = nf_original.get('l10n_br_chave_nf')

        # Valor
        valor = nc_data.get('amount_total')
        if valor:
            nfd.valor_total = Decimal(str(valor))

        # Vincular ao monitoramento
        if entrega:
            nfd.entrega_monitorada_id = entrega.id
            if entrega.status_finalizacao in ('Cancelada', 'Devolvida', 'Troca de NF'):
                nfd.status_monitoramento = entrega.status_finalizacao

        # Auditoria
        nfd.atualizado_em = agora_utc_naive()
        nfd.atualizado_por = 'Sistema Odoo - Reversao'

        # Se não tem linhas, tentar buscar e criar
        from app.devolucao.models import NFDevolucaoLinha
        linhas_existentes = NFDevolucaoLinha.query.filter_by(nf_devolucao_id=nfd.id).count()
        if linhas_existentes == 0:
            itens = self._buscar_itens_nf_original(nf_original.get('id'))
            if itens:
                linhas_criadas = self._criar_linhas_reversao(nfd, itens)
                logger.info(f"   Criadas {linhas_criadas} linhas para NFD existente {nfd.id}")

        # Garantir vínculo estrutural
        self._criar_nf_referenciada(nfd, nf_original)

    def _criar_nfd_reversao(
        self,
        nc_data: Dict,
        nf_original: Dict,
        entrega: Optional[EntregaMonitorada]
    ) -> NFDevolucao:
        """
        Cria nova NFDevolucao para NF revertida

        Args:
            nc_data: Dados da Nota de Credito
            nf_original: Dados da NF original
            entrega: EntregaMonitorada vinculada (opcional)

        Returns:
            NFDevolucao criada
        """
        valor = nc_data.get('amount_total')
        partner_id = nf_original.get('partner_id')
        nome_parceiro = partner_id[1] if isinstance(partner_id, list) else None
        cnpj_parceiro = self._extrair_cnpj_parceiro(partner_id)

        # Status do monitoramento
        status_monit = None
        if entrega and entrega.status_finalizacao in ('Cancelada', 'Devolvida', 'Troca de NF'):
            status_monit = entrega.status_finalizacao

        nfd = NFDevolucao(
            # Tipo e status
            tipo_documento='NF',
            status_odoo='Revertida',
            status_monitoramento=status_monit,

            # IDs do Odoo
            odoo_nf_venda_id=nf_original.get('id'),
            odoo_nota_credito_id=nc_data.get('id'),

            # Numero e chave
            numero_nfd=nf_original.get('l10n_br_numero_nota_fiscal') or 'SEM_NUMERO',
            numero_nf_venda=nf_original.get('l10n_br_numero_nota_fiscal'),
            chave_nfd=nf_original.get('l10n_br_chave_nf'),

            # Valor
            valor_total=Decimal(str(valor)) if valor else None,

            # Emitente (cliente)
            cnpj_emitente=cnpj_parceiro,
            nome_emitente=nome_parceiro,

            # Vinculacao ao monitoramento
            entrega_monitorada_id=entrega.id if entrega else None,

            # Data
            data_emissao=self._parse_date(nc_data.get('invoice_date')),

            # Controle
            origem_registro='ODOO',
            status='VINCULADA_DFE',
            sincronizado_odoo=True,
            data_sincronizacao=agora_utc(),

            # Motivo
            motivo='OUTROS',
            descricao_motivo='NF de venda revertida - Nota de Credito emitida no Odoo',

            # Auditoria
            criado_em=agora_utc_naive(),
            criado_por='Sistema Odoo - Reversao',
        )

        db.session.add(nfd)
        db.session.flush()

        # Buscar e criar itens da NF original
        itens = self._buscar_itens_nf_original(nf_original.get('id'))
        if itens:
            linhas_criadas = self._criar_linhas_reversao(nfd, itens)
            logger.info(f"   Criadas {linhas_criadas} linhas para NFD {nfd.id}")
        else:
            logger.warning(f"   Nenhum item encontrado para NF original {nf_original.get('id')}")

        # Criar vínculo estrutural com NF original
        self._criar_nf_referenciada(nfd, nf_original)

        return nfd

    def _criar_ocorrencia_automatica(self, nfd: NFDevolucao) -> Optional[OcorrenciaDevolucao]:
        """
        Cria OcorrenciaDevolucao automaticamente para NFDs de reversao

        Args:
            nfd: NFDevolucao

        Returns:
            OcorrenciaDevolucao criada ou None se ja existir
        """
        # Verificar se ja existe ocorrencia
        ocorrencia_existente = OcorrenciaDevolucao.query.filter_by(
            nf_devolucao_id=nfd.id
        ).first()

        if ocorrencia_existente:
            return None

        ocorrencia = OcorrenciaDevolucao(
            nf_devolucao_id=nfd.id,
            numero_ocorrencia=OcorrenciaDevolucao.gerar_numero_ocorrencia(),

            # Secao Logistica
            destino='INDEFINIDO',
            localizacao_atual='CLIENTE',

            # Secao Comercial
            status='ABERTA',
            responsavel='INDEFINIDO',
            origem='INDEFINIDO',

            # Auditoria
            criado_em=agora_utc_naive(),
            criado_por='Sistema Odoo - Reversao',
        )

        db.session.add(ocorrencia)
        db.session.flush()

        return ocorrencia

    # =========================================================================
    # PROCESSAMENTO DE ESTOQUE E FATURAMENTO
    # =========================================================================

    def processar_reversao_estoque(
        self,
        numero_nf: str,
        nota_credito_id: int,
        nota_credito_name: str
    ) -> Dict:
        """
        Processa reversao de NF no estoque e faturamento.

        NOVA LOGICA (nao desfaz, apenas adiciona):
        1. FaturamentoProduto -> marca revertida=True (MANTEM status_nf='Lancado')
        2. MovimentacaoEstoque -> CRIA entrada tipo REVERSAO (quantidade volta ao estoque)
        3. Separacao -> NAO ALTERA (mantem sincronizado_nf=True)
        4. EmbarqueItem -> NAO ALTERA (mantem numero_nf)

        Args:
            numero_nf: Numero da NF que foi revertida
            nota_credito_id: ID do out_refund no Odoo
            nota_credito_name: Nome/Numero da Nota de Credito

        Returns:
            Dict com estatisticas do processamento
        """
        resultado = {
            'sucesso': False,
            'faturamento_marcados': 0,
            'movimentacoes_criadas': 0,
            'erros': []
        }

        try:
            logger.info(f"   Processando reversao de estoque para NF {numero_nf}")

            # 1. Buscar itens de faturamento da NF
            itens_fat = FaturamentoProduto.query.filter_by(
                numero_nf=str(numero_nf)
            ).all()

            if not itens_fat:
                logger.warning(f"   Nenhum item de faturamento encontrado para NF {numero_nf}")
                resultado['sucesso'] = False
                resultado['erros'].append(f"Nenhum FaturamentoProduto encontrado para NF {numero_nf}")
                return resultado

            logger.info(f"   Encontrados {len(itens_fat)} itens de faturamento")

            # 2. Processar cada item
            for item in itens_fat:
                # Verificar se ja foi marcado como revertida
                if item.revertida:
                    logger.info(f"   Item {item.cod_produto} ja estava marcado como revertido")
                    continue

                # 2.1. Marcar FaturamentoProduto como revertida
                item.revertida = True
                item.nota_credito_id = nota_credito_id
                item.data_reversao = agora_utc_naive()
                # NAO altera status_nf - continua 'Lancado'
                resultado['faturamento_marcados'] += 1

                logger.info(f"   FaturamentoProduto {item.id} ({item.cod_produto}) marcado como revertida")

                # 2.2. Criar MovimentacaoEstoque de ENTRADA (reversao)
                # Verificar se ja existe movimentacao de reversao para este item
                mov_existente = MovimentacaoEstoque.query.filter_by(
                    numero_nf=str(numero_nf),
                    cod_produto=item.cod_produto,
                    local_movimentacao='REVERSAO',
                    ativo=True
                ).first()

                if mov_existente:
                    logger.info(f"   Movimentacao de reversao ja existe para {item.cod_produto}")
                    continue

                # Criar movimentacao de entrada (quantidade positiva = volta ao estoque)
                mov = MovimentacaoEstoque(
                    cod_produto=item.cod_produto,
                    nome_produto=item.nome_produto,
                    data_movimentacao=agora_utc_naive().date(),
                    tipo_movimentacao='ENTRADA',        # E uma entrada de estoque
                    local_movimentacao='REVERSAO',      # Origem: reversao de NF
                    qtd_movimentacao=item.qtd_produto_faturado,  # Positivo (volta ao estoque)
                    numero_nf=str(numero_nf),           # NF que foi revertida
                    status_nf='REVERTIDA',              # Status especifico
                    tipo_origem='ODOO',
                    observacao=f'Reversao NF {numero_nf} via NC {nota_credito_name}',
                    criado_em=agora_utc_naive(),
                    criado_por='Sistema Odoo - Reversao'
                )
                db.session.add(mov)
                resultado['movimentacoes_criadas'] += 1

                logger.info(f"   MovimentacaoEstoque criada: {item.cod_produto} +{item.qtd_produto_faturado}")

            resultado['sucesso'] = True
            logger.info(f"   Reversao de estoque concluida: {resultado['faturamento_marcados']} itens marcados, {resultado['movimentacoes_criadas']} movimentacoes criadas")

            return resultado

        except Exception as e:
            erro_msg = f"Erro ao processar reversao de estoque para NF {numero_nf}: {str(e)}"
            logger.error(erro_msg)
            resultado['erros'].append(erro_msg)
            resultado['sucesso'] = False
            return resultado

    # =========================================================================
    # UTILITARIOS
    # =========================================================================

    @staticmethod
    def _parse_date(date_str):
        """Converte string de data para date object"""
        if not date_str:
            return None
        try:
            if isinstance(date_str, str):
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            return date_str
        except Exception:
            return None

    @staticmethod
    def _limpar_cnpj(cnpj):
        """Remove formatacao de CNPJ"""
        if not cnpj:
            return None
        return cnpj.replace('.', '').replace('/', '').replace('-', '').strip()


# =============================================================================
# FUNCOES HELPER
# =============================================================================

def get_reversao_service() -> ReversaoService:
    """Retorna instancia do ReversaoService"""
    return ReversaoService()


def importar_reversoes_odoo(dias: int = 30, limite: int = None) -> Dict:
    """
    Funcao helper para importar reversoes do Odoo

    Args:
        dias: Quantos dias para tras buscar
        limite: Limite de registros

    Returns:
        Dict com estatisticas
    """
    service = get_reversao_service()
    return service.importar_reversoes(dias=dias, limite=limite)
