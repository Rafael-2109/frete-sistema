"""
Service para Importação de NFDs (Nota Fiscal de Devolução) do Odoo
==================================================================

OBJETIVO:
    Buscar NFDs do Odoo (modelo l10n_br_ciel_it_account.dfe)
    e registrar em NFDevolucao com vinculação automática

FILTRO ODOO:
    nfe_infnfe_ide_finnfe = 4 (finalidade = devolução)

FLUXO:
    1. Buscar NFDs no Odoo (finnfe=4)
    2. Para cada NFD:
       a) Tentar vincular a NFDevolucao existente (por numero + CNPJ)
       b) Se não encontrar, criar nova NFDevolucao como órfã
       c) Criar OcorrenciaDevolucao automaticamente para órfãs
    3. Extrair NFs referenciadas do XML e popular NFDevolucaoNFReferenciada
    4. Salvar XML/PDF em S3

MODELO ODOO: l10n_br_ciel_it_account.dfe (com nfe_infnfe_ide_finnfe=4)

AUTOR: Sistema de Fretes - Módulo Devoluções
DATA: 30/12/2024
"""

import logging
import re
import base64
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from io import BytesIO

from app import db
from app.devolucao.models import (
    NFDevolucao,
    NFDevolucaoLinha,
    NFDevolucaoNFReferenciada,
    OcorrenciaDevolucao
)
from app.monitoramento.models import EntregaMonitorada
from app.odoo.utils.connection import get_odoo_connection
from app.devolucao.services.nfd_xml_parser import NFDXMLParser, extrair_nfs_referenciadas, extrair_itens_nfd
from app.utils.file_storage import get_file_storage
from app.utils.timezone import agora_utc, agora_utc_naive

logger = logging.getLogger(__name__)

# CNPJs a excluir da importação (La Famiglia e Nacom Goya - empresas internas)
CNPJS_EXCLUIDOS = {'18467441', '61724241'}

# CFOPs de devolução/remessa de vasilhame (pallet)
# Estas NFDs devem ser tratadas no módulo de pallet, não no módulo de devoluções de produto
# 1920/2920 = Entrada de vasilhame ou sacaria
# 5920/6920 = Remessa de vasilhame ou sacaria
CFOPS_PALLET = {'1920', '2920', '5920', '6920', '5917', '6917', '1917', '2917'}

# Código do produto PALLET no sistema
CODIGO_PRODUTO_PALLET = '208000012'


class NFDService:
    """
    Service para importação e gestão de NFDs do Odoo

    Fluxo de vinculação:
    1. NFD registrada no monitoramento (origem_registro=MONITORAMENTO)
    2. NFD importada do Odoo tenta vincular por numero_nfd + cnpj_emitente
    3. Se encontrar match: atualiza NFDevolucao existente com dados fiscais
    4. Se não encontrar: cria nova NFDevolucao como órfã (origem_registro=ODOO)
    5. Órfãs ganham OcorrenciaDevolucao automaticamente
    """

    def __init__(self):
        """Inicializa conexão com Odoo"""
        self.odoo = get_odoo_connection()
        self._file_storage = None  # Lazy loading

    @property
    def file_storage(self):
        """Lazy loading do file storage (precisa de app context)"""
        if self._file_storage is None:
            self._file_storage = get_file_storage()
        return self._file_storage

    # =========================================================================
    # IMPORTAÇÃO DE NFDs DO ODOO
    # =========================================================================

    def importar_nfds(
        self,
        dias_retroativos: Optional[int] = None,
        limite: Optional[int] = None,
        minutos_janela: Optional[int] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None
    ) -> Dict:
        """
        Importa NFDs do Odoo (finalidade=4 = devolução)

        Args:
            dias_retroativos: Quantos dias para trás buscar (padrão: 30)
            limite: Limite de registros (None = todos)
            minutos_janela: Busca incremental nos últimos X minutos
            data_inicio: Data início do período (YYYY-MM-DD)
            data_fim: Data fim do período (YYYY-MM-DD)

        Returns:
            Dict com estatísticas da importação
        """
        logger.info("=" * 80)
        logger.info("📄 INICIANDO IMPORTAÇÃO DE NFDs (Devoluções)")
        logger.info("=" * 80)

        resultado = {
            'sucesso': False,
            'nfds_processadas': 0,
            'nfds_novas': 0,
            'nfds_atualizadas': 0,
            'nfds_vinculadas': 0,  # Vinculadas a registro do monitoramento
            'nfds_orfas': 0,  # Sem match no monitoramento
            'ocorrencias_criadas': 0,
            'nfs_referenciadas': 0,
            'linhas_criadas': 0,
            'erros': []
        }

        try:
            # 1. Determinar período de busca
            if minutos_janela:
                momento_atual = agora_utc()
                data_calc = (momento_atual - timedelta(minutes=minutos_janela)).strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"🔄 Sincronização Incremental: Últimos {minutos_janela} minutos")
                nfds = self._buscar_nfds_odoo(data_calc, limite, usar_write_date=True)
            elif data_inicio:
                logger.info(f"📅 Sincronização por Período: {data_inicio} a {data_fim or 'hoje'}")
                if data_fim:
                    nfds = self._buscar_nfds_odoo_periodo(data_inicio, data_fim, limite)
                else:
                    data_hoje = agora_utc().strftime('%Y-%m-%d')
                    nfds = self._buscar_nfds_odoo_periodo(data_inicio, data_hoje, limite)
            else:
                dias = dias_retroativos if dias_retroativos else 30
                data_calc = (agora_utc() - timedelta(days=dias)).strftime('%Y-%m-%d')
                logger.info(f"📅 Sincronização Inicial: Últimos {dias} dias")
                nfds = self._buscar_nfds_odoo(data_calc, limite, usar_write_date=False)

            if not nfds:
                logger.warning("⚠️  Nenhuma NFD encontrada no Odoo")
                resultado['sucesso'] = True
                return resultado

            logger.info(f"📦 Total de NFDs encontradas: {len(nfds)}")

            # 2. Processar cada NFD
            for nfd_data in nfds:
                try:
                    dfe_id = str(nfd_data.get('id'))
                    numero_nfd = nfd_data.get('nfe_infnfe_ide_nnf', '')
                    logger.info(f"\n📋 Processando NFD: {numero_nfd} (DFe ID {dfe_id})")

                    estatisticas = self._processar_nfd(nfd_data)

                    resultado['nfds_processadas'] += 1

                    if estatisticas.get('nova'):
                        resultado['nfds_novas'] += 1
                    else:
                        resultado['nfds_atualizadas'] += 1

                    if estatisticas.get('vinculada'):
                        resultado['nfds_vinculadas'] += 1
                    if estatisticas.get('orfa'):
                        resultado['nfds_orfas'] += 1
                    if estatisticas.get('ocorrencia_criada'):
                        resultado['ocorrencias_criadas'] += 1

                    resultado['nfs_referenciadas'] += estatisticas.get('nfs_referenciadas', 0)
                    resultado['linhas_criadas'] += estatisticas.get('linhas_criadas', 0)

                    # Commit após cada NFD processada com sucesso
                    # Isso evita perder processamentos anteriores em caso de erro posterior
                    db.session.commit()

                except Exception as e:
                    # CRÍTICO: Fazer rollback para limpar estado da sessão
                    # Isso permite continuar processando outras NFDs após um erro
                    db.session.rollback()
                    erro_msg = f"Erro ao processar NFD {nfd_data.get('id')}: {str(e)}"
                    logger.error(f"❌ {erro_msg}")
                    resultado['erros'].append(erro_msg)

            # Commit final removido - cada NFD já é commitada individualmente
            resultado['sucesso'] = True
            logger.info("=" * 80)
            logger.info("✅ IMPORTAÇÃO DE NFDs CONCLUÍDA")
            logger.info(f"   📊 Processadas: {resultado['nfds_processadas']}")
            logger.info(f"   ✨ Novas: {resultado['nfds_novas']}")
            logger.info(f"   🔄 Atualizadas: {resultado['nfds_atualizadas']}")
            logger.info(f"   🔗 Vinculadas: {resultado['nfds_vinculadas']}")
            logger.info(f"   👻 Órfãs: {resultado['nfds_orfas']}")
            logger.info(f"   📝 Ocorrências criadas: {resultado['ocorrencias_criadas']}")
            logger.info(f"   📄 NFs referenciadas: {resultado['nfs_referenciadas']}")
            logger.info(f"   📦 Linhas criadas: {resultado['linhas_criadas']}")
            logger.info(f"   ❌ Erros: {len(resultado['erros'])}")
            logger.info("=" * 80)

            return resultado

        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro fatal na importação de NFDs: {str(e)}"
            logger.error(f"❌ {erro_msg}")
            resultado['erros'].append(erro_msg)
            resultado['sucesso'] = False
            return resultado

    def _buscar_nfds_odoo(
        self,
        data_inicio: str,
        limite: Optional[int] = None,
        usar_write_date: bool = False
    ) -> List[Dict]:
        """
        Busca NFDs no Odoo (finalidade=4)

        Args:
            data_inicio: Data mínima
            limite: Limite de registros
            usar_write_date: Se True, usa write_date. Se False, usa data de emissão

        Returns:
            Lista de NFDs
        """
        try:
            # Filtro: finnfe=4 (devolução) + active=True
            if usar_write_date:
                filtros = [
                    "&",
                    "&",
                    "&",
                    ("active", "=", True),
                    ("nfe_infnfe_ide_finnfe", "=", "4"),
                    ("is_cte", "=", False),  # Não é CTe
                    ("write_date", ">=", data_inicio)
                ]
                logger.info(f"   Filtro: finnfe=4 AND active=True AND write_date >= {data_inicio}")
            else:
                filtros = [
                    "&",
                    "&",
                    "&",
                    ("active", "=", True),
                    ("nfe_infnfe_ide_finnfe", "=", "4"),
                    ("is_cte", "=", False),
                    ("nfe_infnfe_ide_dhemi", ">=", data_inicio)
                ]
                logger.info(f"   Filtro: finnfe=4 AND active=True AND data_emissao >= {data_inicio}")

            campos = self._get_campos_nfd()

            params = {'fields': campos}
            if limite:
                params['limit'] = limite

            nfds = self.odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe',
                'search_read',
                [filtros],
                params
            )

            return nfds or []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar NFDs do Odoo: {e}")
            return []

    def _buscar_nfds_odoo_periodo(
        self,
        data_inicio: str,
        data_fim: str,
        limite: Optional[int] = None
    ) -> List[Dict]:
        """Busca NFDs por período"""
        try:
            filtros = [
                "&",
                "&",
                "&",
                "&",
                ("active", "=", True),
                ("nfe_infnfe_ide_finnfe", "=", "4"),
                ("is_cte", "=", False),
                ("write_date", ">=", data_inicio),
                ("write_date", "<=", f"{data_fim} 23:59:59")
            ]

            logger.info(f"   Filtro: finnfe=4 AND write_date ENTRE {data_inicio} E {data_fim}")

            campos = self._get_campos_nfd()

            nfds = self.odoo.search_read(
                'l10n_br_ciel_it_account.dfe',
                filtros,
                campos,
                limit=limite if limite else None
            )

            return nfds or []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar NFDs por período: {e}")
            return []

    def _get_campos_nfd(self) -> List[str]:
        """Retorna lista de campos a buscar no Odoo"""
        return [
            'id',
            'name',
            'active',
            'l10n_br_status',
            'l10n_br_data_entrada',

            # Chave e numeração
            'protnfe_infnfe_chnfe',  # Chave de acesso
            'nfe_infnfe_ide_nnf',     # Número
            'nfe_infnfe_ide_serie',   # Série
            'nfe_infnfe_ide_finnfe',  # Finalidade (4=devolução)

            # Data
            'nfe_infnfe_ide_dhemi',   # Data de emissão

            # Valores
            'nfe_infnfe_total_icmstot_vnf',  # Valor total
            'nfe_infnfe_total_icmstot_vprod',  # Valor produtos

            # Emitente (cliente que devolveu)
            'nfe_infnfe_emit_cnpj',
            'nfe_infnfe_emit_xnome',
            'nfe_infnfe_emit_ie',

            # Destinatário (nós - Nacom)
            'nfe_infnfe_dest_cnpj',
            # Nota: nfe_infnfe_dest_xnome não existe no Odoo

            # Arquivos
            'l10n_br_pdf_dfe',
            'l10n_br_pdf_dfe_fname',
            'l10n_br_xml_dfe',
            'l10n_br_xml_dfe_fname',

            # Linhas de produto
            'lines_ids',
        ]

    def _processar_nfd(self, nfd_data: Dict) -> Dict:
        """
        Processa uma NFD e cria/atualiza NFDevolucao

        Fluxo:
        1. Verificar se já existe por chave de acesso (UNIQUE)
        2. Se não existe, tentar vincular por numero + CNPJ
        3. Se não encontrar match, criar como órfã
        4. Extrair NFs referenciadas do XML
        5. Criar OcorrenciaDevolucao para órfãs

        Args:
            nfd_data: Dados da NFD do Odoo

        Returns:
            Dict com estatísticas
        """
        estatisticas = {
            'nova': False,
            'vinculada': False,
            'orfa': False,
            'ocorrencia_criada': False,
            'nfs_referenciadas': 0,
            'linhas_criadas': 0,
        }

        dfe_id = str(nfd_data.get('id'))
        chave_acesso = nfd_data.get('protnfe_infnfe_chnfe')
        numero_nfd = nfd_data.get('nfe_infnfe_ide_nnf')
        cnpj_emitente = self._limpar_cnpj(nfd_data.get('nfe_infnfe_emit_cnpj'))

        # Verificar se CNPJ deve ser excluído (empresas internas)
        cnpj_prefixo = cnpj_emitente[:8] if cnpj_emitente else None
        if cnpj_prefixo in CNPJS_EXCLUIDOS:
            logger.info(f"   ⚠️ NFD ignorada - CNPJ excluído: {cnpj_emitente} ({cnpj_prefixo})")
            estatisticas['ignorada_cnpj'] = True
            return estatisticas

        # 1. Verificar se já existe por chave de acesso ou dfe_id
        nfd_existente = None

        if chave_acesso:
            nfd_existente = NFDevolucao.query.filter_by(
                chave_nfd=chave_acesso
            ).first()

            if nfd_existente:
                logger.info(f"   ✅ NFD encontrada por chave_acesso: ID {nfd_existente.id}")

        if not nfd_existente:
            nfd_existente = NFDevolucao.query.filter_by(
                odoo_dfe_id=int(dfe_id)
            ).first()

            if nfd_existente:
                logger.info(f"   ✅ NFD encontrada por dfe_id: ID {nfd_existente.id}")

        # 2. Se não existe, tentar vincular por numero + CNPJ (late binding)
        if not nfd_existente and numero_nfd and cnpj_emitente:
            nfd_existente = self._tentar_vincular_por_numero_cnpj(numero_nfd, cnpj_emitente)

            if nfd_existente:
                estatisticas['vinculada'] = True
                logger.info(f"   🔗 NFD vinculada a registro do monitoramento: ID {nfd_existente.id}")

        # 3. Se ainda não existe, criar nova (órfã)
        if nfd_existente:
            # Atualizar existente
            self._atualizar_nfd_existente(nfd_existente, nfd_data)
            logger.info(f"   🔄 NFD atualizada: {numero_nfd}")
        else:
            # Criar nova como órfã
            nfd_existente = self._criar_nfd_orfa(nfd_data)
            estatisticas['nova'] = True
            estatisticas['orfa'] = True
            logger.info(f"   ✨ NFD órfã criada: {numero_nfd}")

            # Criar OcorrenciaDevolucao automaticamente para órfãs
            ocorrencia = self._criar_ocorrencia_automatica(nfd_existente)
            if ocorrencia:
                estatisticas['ocorrencia_criada'] = True
                logger.info(f"   📝 Ocorrência criada: {ocorrencia.numero_ocorrencia}")

        # 4. Extrair e salvar NFs referenciadas do XML
        xml_base64 = nfd_data.get('l10n_br_xml_dfe')
        if xml_base64 and xml_base64 != False:
            nfs_criadas = self._processar_nfs_referenciadas(nfd_existente.id, xml_base64)
            estatisticas['nfs_referenciadas'] = nfs_criadas

            # Extrair e salvar linhas de produto (com auto-resolucao via De-Para)
            prefixo_cnpj = nfd_existente.prefixo_cnpj_emitente
            linhas_criadas = self._processar_linhas_produto(nfd_existente.id, xml_base64, prefixo_cnpj=prefixo_cnpj)
            estatisticas['linhas_criadas'] = linhas_criadas

            # Detectar se é NFD de pallet/vasilhame (após processar linhas)
            e_pallet = self._detectar_nfd_pallet(nfd_existente.id)
            if e_pallet:
                nfd_existente.e_pallet_devolucao = True
                estatisticas['e_pallet_devolucao'] = True
                logger.info(f"   📦 NFD classificada como PALLET (CFOPs de vasilhame detectados)")

            # Extrair informações complementares (infCpl) - motivo da devolução
            self._extrair_info_complementar(nfd_existente, xml_base64)

            # Extrair endereço do emitente (UF, cidade, CEP)
            self._extrair_endereco_emitente(nfd_existente, xml_base64)

        # 5. Salvar arquivos no S3
        self._salvar_arquivos_nfd(nfd_existente, nfd_data)

        return estatisticas

    def _tentar_vincular_por_numero_cnpj(
        self,
        numero_nfd: str,
        cnpj_emitente: str
    ) -> Optional[NFDevolucao]:
        """
        Tenta encontrar NFDevolucao existente por numero + CNPJ

        Args:
            numero_nfd: Número da NFD
            cnpj_emitente: CNPJ do emitente (cliente)

        Returns:
            NFDevolucao se encontrar match, None caso contrário
        """
        # Buscar por numero_nfd que ainda não tem odoo_dfe_id (não importada)
        # E que tem o mesmo CNPJ do emitente
        # Prioriza registros do monitoramento (origem_registro=MONITORAMENTO)

        candidatos = NFDevolucao.query.filter(
            NFDevolucao.numero_nfd == str(numero_nfd),
            NFDevolucao.odoo_dfe_id.is_(None),  # Ainda não vinculada ao Odoo
            NFDevolucao.ativo == True
        ).all()

        if not candidatos:
            logger.info(f"   ⚠️ Nenhum candidato encontrado para vinculação: NFD {numero_nfd}")
            return None

        # Filtrar por CNPJ (pode estar em entrega_monitorada ou em cnpj_emitente)
        for candidato in candidatos:
            # Verificar CNPJ do emitente
            if candidato.cnpj_emitente:
                cnpj_candidato = self._limpar_cnpj(candidato.cnpj_emitente)
                if cnpj_candidato == cnpj_emitente:
                    return candidato

            # Verificar CNPJ via entrega monitorada
            if candidato.entrega_monitorada:
                # Comparar prefixo CNPJ (8 dígitos - grupo econômico)
                prefixo_odoo = cnpj_emitente[:8] if len(cnpj_emitente) >= 8 else cnpj_emitente

                # Tentar obter CNPJ da entrega (depende da estrutura)
                cnpj_entrega = getattr(candidato.entrega_monitorada, 'cnpj_cliente', None)
                if cnpj_entrega:
                    cnpj_entrega_limpo = self._limpar_cnpj(cnpj_entrega)
                    prefixo_entrega = cnpj_entrega_limpo[:8] if len(cnpj_entrega_limpo) >= 8 else cnpj_entrega_limpo # type: ignore

                    if prefixo_odoo == prefixo_entrega:
                        return candidato

        logger.info(f"   ⚠️ Candidatos encontrados mas CNPJ não corresponde: NFD {numero_nfd}")
        return None

    def _atualizar_nfd_existente(self, nfd: NFDevolucao, nfd_data: Dict):
        """
        Atualiza NFDevolucao existente com dados fiscais do Odoo

        Regra: Dados fiscais do Odoo sobrescrevem
        """
        # Dados do Odoo
        nfd.odoo_dfe_id = int(nfd_data.get('id'))
        nfd.odoo_ativo = nfd_data.get('active', True)
        nfd.odoo_name = nfd_data.get('name')
        nfd.odoo_status_codigo = nfd_data.get('l10n_br_status')
        nfd.odoo_status_descricao = self._get_status_descricao(nfd_data.get('l10n_br_status'))

        # NOVOS CAMPOS: tipo_documento e status_odoo
        # NFD (finnfe=4) sempre é "Devolução"
        nfd.tipo_documento = 'NFD'
        nfd.status_odoo = 'Devolução'

        # Sincronizar status_monitoramento se houver entrega vinculada
        if nfd.entrega_monitorada:
            status_monit = nfd.entrega_monitorada.status_finalizacao
            if status_monit in ('Cancelada', 'Devolvida', 'Troca de NF'):
                nfd.status_monitoramento = status_monit

        # Dados fiscais (Odoo sobrescreve)
        nfd.chave_nfd = nfd_data.get('protnfe_infnfe_chnfe')
        nfd.numero_nfd = nfd_data.get('nfe_infnfe_ide_nnf') or nfd.numero_nfd
        nfd.serie_nfd = nfd_data.get('nfe_infnfe_ide_serie')
        nfd.data_emissao = self._parse_date(nfd_data.get('nfe_infnfe_ide_dhemi'))
        nfd.data_entrada = self._parse_date(nfd_data.get('l10n_br_data_entrada'))

        # Valores
        valor_total = nfd_data.get('nfe_infnfe_total_icmstot_vnf')
        valor_produtos = nfd_data.get('nfe_infnfe_total_icmstot_vprod')
        nfd.valor_total = Decimal(str(valor_total)) if valor_total else None
        nfd.valor_produtos = Decimal(str(valor_produtos)) if valor_produtos else None

        # Emitente (cliente)
        nfd.cnpj_emitente = self._limpar_cnpj(nfd_data.get('nfe_infnfe_emit_cnpj'))
        nfd.nome_emitente = nfd_data.get('nfe_infnfe_emit_xnome')
        nfd.ie_emitente = nfd_data.get('nfe_infnfe_emit_ie')

        # Destinatário (nós)
        nfd.cnpj_destinatario = self._limpar_cnpj(nfd_data.get('nfe_infnfe_dest_cnpj'))
        # nome_destinatario não disponível no modelo Odoo (campo nfe_infnfe_dest_xnome não existe)

        # Controle
        nfd.sincronizado_odoo = True
        nfd.data_sincronizacao = agora_utc()

        nfd.atualizado_em = agora_utc_naive()
        nfd.atualizado_por = 'Sistema Odoo'

        # Recalcular status da ocorrencia vinculada (auto-computado)
        if nfd.ocorrencia:
            novo_status = nfd.ocorrencia.calcular_status()
            if nfd.ocorrencia.status != novo_status:
                status_anterior = nfd.ocorrencia.status
                nfd.ocorrencia.status = novo_status
                # Transicao para RESOLVIDO: marcar data_resolucao
                if novo_status == 'RESOLVIDO' and status_anterior != 'RESOLVIDO':
                    if nfd.data_entrada:
                        from datetime import date as date_type, datetime as dt_type
                        if isinstance(nfd.data_entrada, date_type) and not isinstance(nfd.data_entrada, dt_type):
                            nfd.ocorrencia.data_resolucao = dt_type.combine(nfd.data_entrada, dt_type.min.time())
                        else:
                            nfd.ocorrencia.data_resolucao = nfd.data_entrada
                    else:
                        nfd.ocorrencia.data_resolucao = agora_utc_naive()
                    nfd.ocorrencia.resolvido_por = 'Sistema Odoo'

    def _criar_nfd_orfa(self, nfd_data: Dict) -> NFDevolucao:
        """
        Cria nova NFDevolucao como órfã (sem match no monitoramento)

        Args:
            nfd_data: Dados do Odoo

        Returns:
            NFDevolucao criada
        """
        valor_total = nfd_data.get('nfe_infnfe_total_icmstot_vnf')
        valor_produtos = nfd_data.get('nfe_infnfe_total_icmstot_vprod')

        nfd = NFDevolucao(
            # Dados do Odoo
            odoo_dfe_id=int(nfd_data.get('id')),
            odoo_ativo=nfd_data.get('active', True),
            odoo_name=nfd_data.get('name'),
            odoo_status_codigo=nfd_data.get('l10n_br_status'),
            odoo_status_descricao=self._get_status_descricao(nfd_data.get('l10n_br_status')),

            # NOVOS CAMPOS: tipo_documento e status
            # NFD (finnfe=4) sempre é tipo 'NFD' com status_odoo='Devolução'
            tipo_documento='NFD',
            status_odoo='Devolução',
            status_monitoramento=None,  # Órfã não tem vinculação com monitoramento

            # Dados fiscais
            chave_nfd=nfd_data.get('protnfe_infnfe_chnfe'),
            numero_nfd=nfd_data.get('nfe_infnfe_ide_nnf') or 'SEM_NUMERO',
            serie_nfd=nfd_data.get('nfe_infnfe_ide_serie'),
            data_emissao=self._parse_date(nfd_data.get('nfe_infnfe_ide_dhemi')),
            data_entrada=self._parse_date(nfd_data.get('l10n_br_data_entrada')),

            # Valores
            valor_total=Decimal(str(valor_total)) if valor_total else None,
            valor_produtos=Decimal(str(valor_produtos)) if valor_produtos else None,

            # Emitente (cliente)
            cnpj_emitente=self._limpar_cnpj(nfd_data.get('nfe_infnfe_emit_cnpj')),
            nome_emitente=nfd_data.get('nfe_infnfe_emit_xnome'),
            ie_emitente=nfd_data.get('nfe_infnfe_emit_ie'),

            # Destinatário (nós)
            cnpj_destinatario=self._limpar_cnpj(nfd_data.get('nfe_infnfe_dest_cnpj')),
            # nome_destinatario não disponível (campo não existe no Odoo)

            # Controle
            origem_registro='ODOO',
            status='VINCULADA_DFE',
            sincronizado_odoo=True,
            data_sincronizacao=agora_utc(),

            # Motivo genérico para órfãs
            motivo='OUTROS',
            descricao_motivo='NFD importada do Odoo sem registro no monitoramento',

            # Auditoria
            criado_em=agora_utc_naive(),
            criado_por='Sistema Odoo',
        )

        db.session.add(nfd)
        db.session.flush()  # Para obter o ID

        return nfd

    def _criar_ocorrencia_automatica(self, nfd: NFDevolucao) -> Optional[OcorrenciaDevolucao]:
        """
        Cria OcorrenciaDevolucao automaticamente para NFDs órfãs

        Args:
            nfd: NFDevolucao órfã

        Returns:
            OcorrenciaDevolucao criada ou None se já existir
        """
        # Verificar se já existe ocorrência
        ocorrencia_existente = OcorrenciaDevolucao.query.filter_by(
            nf_devolucao_id=nfd.id
        ).first()

        if ocorrencia_existente:
            return None

        ocorrencia = OcorrenciaDevolucao(
            nf_devolucao_id=nfd.id,
            numero_ocorrencia=OcorrenciaDevolucao.gerar_numero_ocorrencia(),

            # Seção Logística
            destino='INDEFINIDO',
            localizacao_atual='CLIENTE',

            # Seção Comercial
            status='PENDENTE',
            responsavel='INDEFINIDO',
            origem='INDEFINIDO',

            # Auditoria
            criado_em=agora_utc_naive(),
            criado_por='Sistema Odoo',
        )

        db.session.add(ocorrencia)
        db.session.flush()

        return ocorrencia

    def _processar_nfs_referenciadas(self, nfd_id: int, xml_base64: str) -> int:
        """
        Extrai NFs referenciadas do XML e cria NFDevolucaoNFReferenciada

        IMPORTANTE: Também vincula automaticamente à EntregaMonitorada
        e marca teve_devolucao = True

        Args:
            nfd_id: ID da NFDevolucao
            xml_base64: XML em base64

        Returns:
            Quantidade de NFs referenciadas criadas
        """
        try:
            # Decodificar XML
            xml_bytes = base64.b64decode(xml_base64)
            try:
                xml_content = xml_bytes.decode('utf-8')
            except UnicodeDecodeError:
                xml_content = xml_bytes.decode('iso-8859-1')

            # Extrair NFs referenciadas
            nfs_ref = extrair_nfs_referenciadas(xml_content)

            # Obter a NFD para atualizar numero_nf_venda
            from app import db
            nfd = db.session.get(NFDevolucao,nfd_id) if nfd_id else None

            count = 0
            for nf_ref in nfs_ref:
                numero_nf = nf_ref.get('numero')

                # Verificar se já existe
                existe = NFDevolucaoNFReferenciada.query.filter_by(
                    nf_devolucao_id=nfd_id,
                    numero_nf=numero_nf,
                    serie_nf=nf_ref.get('serie')
                ).first()

                if existe:
                    continue

                # Buscar EntregaMonitorada pelo numero da NF
                entrega = None
                entrega_id = None
                if numero_nf:
                    entrega = EntregaMonitorada.query.filter_by(
                        numero_nf=numero_nf
                    ).first()

                    if entrega:
                        entrega_id = entrega.id
                        # MARCAR teve_devolucao = True
                        if not entrega.teve_devolucao:
                            entrega.teve_devolucao = True
                            logger.info(f"   ✅ Entrega {entrega.numero_nf} marcada como teve_devolucao=True")

                # Criar novo registro
                ref = NFDevolucaoNFReferenciada(
                    nf_devolucao_id=nfd_id,
                    numero_nf=numero_nf or 'N/A',
                    serie_nf=nf_ref.get('serie'),
                    chave_nf=nf_ref.get('chave'),
                    entrega_monitorada_id=entrega_id,  # Vincular à entrega
                    origem='XML',
                    criado_em=agora_utc_naive(),
                    criado_por='Sistema Odoo',
                )

                db.session.add(ref)
                count += 1

                # Atualizar numero_nf_venda na NFD (primeira NF encontrada)
                if nfd and not nfd.numero_nf_venda and numero_nf:
                    nfd.numero_nf_venda = numero_nf
                    logger.info(f"   📝 NFD atualizada: numero_nf_venda = {numero_nf}")

                    # Se NFD não tem entrega_monitorada_id, vincular à primeira entrega encontrada
                    if not nfd.entrega_monitorada_id and entrega_id:
                        nfd.entrega_monitorada_id = entrega_id
                        logger.info(f"   🔗 NFD vinculada à entrega ID {entrega_id}")

                        # Sincronizar status_monitoramento com a entrega
                        if entrega and entrega.status_finalizacao in ('Cancelada', 'Devolvida', 'Troca de NF'):
                            nfd.status_monitoramento = entrega.status_finalizacao
                            logger.info(f"   📊 status_monitoramento sincronizado: {entrega.status_finalizacao}")

            logger.info(f"   📄 {count} NFs referenciadas criadas")
            return count

        except Exception as e:
            logger.error(f"   ❌ Erro ao processar NFs referenciadas: {e}")
            return 0

    def _processar_linhas_produto(self, nfd_id: int, xml_base64: str, prefixo_cnpj: str = None) -> int:
        """
        Extrai linhas de produto do XML e cria NFDevolucaoLinha.
        Se prefixo_cnpj for fornecido, tenta aplicar De-Para automaticamente.

        Args:
            nfd_id: ID da NFDevolucao
            xml_base64: XML em base64
            prefixo_cnpj: Prefixo CNPJ (8 digitos) para busca De-Para

        Returns:
            Quantidade de linhas criadas
        """
        try:
            # Decodificar XML
            xml_bytes = base64.b64decode(xml_base64)
            try:
                xml_content = xml_bytes.decode('utf-8')
            except UnicodeDecodeError:
                xml_content = xml_bytes.decode('iso-8859-1')

            # Extrair itens
            itens = extrair_itens_nfd(xml_content)

            # =========================================================
            # Buscar De-Para em lote para todos os codigos de produto
            # =========================================================
            depara_map = {}
            if prefixo_cnpj and itens:
                try:
                    from app.devolucao.services import get_ai_resolver
                    ai_service = get_ai_resolver()
                    codigos_clientes = [
                        str(item.get('codigo_produto', '')).strip()
                        for item in itens
                        if item.get('codigo_produto')
                    ]
                    if codigos_clientes:
                        depara_map = ai_service._buscar_depara_lote(codigos_clientes, prefixo_cnpj)
                except Exception as e:
                    logger.warning(f"   ⚠️ Erro ao buscar De-Para em lote: {e}")

            count = 0
            auto_resolvidas = 0
            cache_precos = {}  # {cod_produto: {mediana_caixa, qtd_por_caixa, total_vendas} ou None}

            # Batch: carregar numeros_item existentes em 1 query (evita N+1)
            numeros_existentes = set()
            if nfd_id:
                rows = db.session.query(NFDevolucaoLinha.numero_item).filter(
                    NFDevolucaoLinha.nf_devolucao_id == nfd_id,
                    NFDevolucaoLinha.numero_item != None  # noqa: E711
                ).all()
                numeros_existentes = {r[0] for r in rows}

            for item in itens:
                # Verificar se já existe linha com mesmo numero_item
                numero_item = item.get('numero_item')
                if numero_item and numero_item in numeros_existentes:
                    continue

                # Criar linha
                linha = NFDevolucaoLinha(
                    nf_devolucao_id=nfd_id,
                    numero_item=numero_item,
                    codigo_produto_cliente=item.get('codigo_produto'),
                    descricao_produto_cliente=item.get('descricao'),
                    quantidade=Decimal(str(item.get('quantidade'))) if item.get('quantidade') else None,
                    unidade_medida=item.get('unidade_medida'),
                    valor_unitario=Decimal(str(item.get('valor_unitario'))) if item.get('valor_unitario') else None,
                    valor_total=Decimal(str(item.get('valor_total'))) if item.get('valor_total') else None,
                    cfop=item.get('cfop'),
                    ncm=item.get('ncm'),
                    peso_bruto=Decimal(str(item.get('peso_bruto'))) if item.get('peso_bruto') else None,
                    peso_liquido=Decimal(str(item.get('peso_liquido'))) if item.get('peso_liquido') else None,
                    criado_em=agora_utc_naive(),
                )

                # =========================================================
                # Tentar auto-resolver via De-Para
                # =========================================================
                codigo_cliente = str(item.get('codigo_produto', '')).strip()
                depara = depara_map.get(codigo_cliente)

                if depara and depara.get('nosso_codigo'):
                    unidade_str = (item.get('unidade_medida') or '').strip().upper()
                    tipo_unidade = self._classificar_unidade(unidade_str)

                    # Validar tipo_unidade contra preço histórico de faturamento
                    _preco_override = False
                    tipo_validado = self._validar_tipo_por_preco(
                        cod_produto=depara['nosso_codigo'],
                        valor_unitario=float(item.get('valor_unitario', 0)),
                        tipo_deterministico=tipo_unidade,
                        cache_precos=cache_precos,
                    )
                    if tipo_validado and tipo_validado != tipo_unidade:
                        logger.warning(
                            f"[NFD_SERVICE] Override tipo_unidade: {tipo_unidade} -> {tipo_validado} "
                            f"para cod_produto={depara['nosso_codigo']} "
                            f"(preço NFD={item.get('valor_unitario')} vs faturamento)"
                        )
                        tipo_unidade = tipo_validado
                        _preco_override = True

                    # Proteção: só aplicar conversão automática se tipo é reconhecido
                    if tipo_unidade != 'OUTRO':
                        linha.codigo_produto_interno = depara['nosso_codigo']
                        linha.descricao_produto_interno = depara.get('descricao_nosso', '')
                        linha.produto_resolvido = True
                        metodo = depara.get('metodo', 'DEPARA')
                        if _preco_override:
                            metodo += '+PRECO'
                        linha.metodo_resolucao = metodo

                        # Calcular conversão baseada no tipo de unidade
                        fator = float(depara.get('fator_conversao', 1.0))
                        quantidade = float(item.get('quantidade', 0)) if item.get('quantidade') else None

                        # =====================================================
                        # ISSUE 2: Derivar fator do XML via preco quando possivel
                        # O XML nao carrega fator_conversao, mas podemos inferir
                        # comparando valor_unitario do XML com mediana do faturamento
                        # =====================================================
                        if tipo_unidade == 'UNIDADE' and item.get('valor_unitario'):
                            valor_un_xml = float(item.get('valor_unitario', 0))
                            dados_preco = cache_precos.get(depara['nosso_codigo'])
                            if dados_preco and valor_un_xml > 0:
                                mediana_cx = dados_preco['mediana_caixa']
                                fator_inferido = round(mediana_cx / valor_un_xml)
                                # Validar: fator faz sentido? (entre 2 e 100, ratio proximo de 1)
                                if 2 <= fator_inferido <= 100:
                                    ratio_check = mediana_cx / (valor_un_xml * fator_inferido)
                                    if 0.8 <= ratio_check <= 1.2:
                                        if fator_inferido != int(fator):
                                            logger.info(
                                                f"[NFD_SERVICE] Fator XML derivado: {fator_inferido} "
                                                f"(De-Para: {fator}) para {depara['nosso_codigo']} "
                                                f"(valor_un_xml={valor_un_xml}, mediana_cx={mediana_cx})"
                                            )
                                        fator = float(fator_inferido)
                            elif _preco_override and dados_preco and dados_preco.get('qtd_por_caixa', 0) > 1:
                                # Fallback: usar qtd_por_caixa do cache_precos (fonte: cadastro NxM)
                                fator = float(dados_preco['qtd_por_caixa'])

                        if tipo_unidade == 'CAIXA' and quantidade:
                            # Já é caixa: 1:1
                            linha.qtd_por_caixa = 1
                            linha.quantidade_convertida = quantidade
                        elif tipo_unidade == 'UNIDADE' and fator > 0 and quantidade:
                            linha.qtd_por_caixa = int(fator)
                            linha.quantidade_convertida = round(quantidade / fator, 3)

                        # Buscar CadastroPalletizacao UMA vez (PESO + peso calculado)
                        try:
                            from app.producao.models import CadastroPalletizacao
                            produto_cad = CadastroPalletizacao.query.filter_by(
                                cod_produto=depara['nosso_codigo']
                            ).first()
                            if produto_cad:
                                # PESO: converter kg -> caixas
                                if tipo_unidade == 'PESO' and produto_cad.peso_bruto and float(produto_cad.peso_bruto) > 0 and quantidade:
                                    peso_caixa = float(produto_cad.peso_bruto)
                                    linha.quantidade_convertida = round(quantidade / peso_caixa, 3)
                                # Peso calculado (todas as UM)
                                if produto_cad.peso_bruto:
                                    qtd_para_peso = float(linha.quantidade_convertida) if linha.quantidade_convertida else float(quantidade or 0)
                                    linha.peso_bruto = Decimal(str(round(qtd_para_peso * float(produto_cad.peso_bruto), 2)))
                        except Exception:
                            pass

                        auto_resolvidas += 1

                db.session.add(linha)
                count += 1

            if auto_resolvidas > 0:
                logger.info(f"   ✅ {auto_resolvidas}/{count} linhas auto-resolvidas via De-Para")
            logger.info(f"   📦 {count} linhas de produto criadas")
            return count

        except Exception as e:
            logger.error(f"   ❌ Erro ao processar linhas de produto: {e}")
            return 0

    @staticmethod
    def _classificar_unidade(unidade_str: str) -> str:
        """
        Classifica unidade de medida em CAIXA, UNIDADE, PESO ou OUTRO.
        Usa regras deterministicas baseadas na analise de 1892 linhas de NFD.

        Args:
            unidade_str: Unidade em uppercase (ja stripped)

        Returns:
            'CAIXA', 'UNIDADE', 'PESO' ou 'OUTRO'
        """
        if not unidade_str:
            return 'OUTRO'

        # CAIXA (verificar primeiro - mais especifico)
        if any(u in unidade_str for u in ['CX', 'CAIXA', 'BOX', 'FD', 'FARDO', 'PCT', 'PACOTE', 'TAMBOR']):
            return 'CAIXA'

        # UNIDADE
        if any(u in unidade_str for u in ['UN', 'UNI', 'PC', 'PECA', 'PÇ', 'BD', 'BALDE', 'BLD',
                                            'SC', 'SACO', 'PT', 'POTE', 'BL', 'BA', 'SH', 'SACHE']):
            return 'UNIDADE'

        # PESO
        if any(u in unidade_str for u in ['KG', 'GR', 'GRAM', 'QUILO', 'TON']):
            return 'PESO'

        # Casos especiais
        if unidade_str == 'U':
            return 'UNIDADE'
        if unidade_str == 'G':
            return 'PESO'

        return 'OUTRO'

    @staticmethod
    def _validar_tipo_por_preco(
        cod_produto: str,
        valor_unitario: float,
        tipo_deterministico: str,
        cache_precos: dict,
    ) -> Optional[str]:
        """
        Valida tipo_unidade cruzando preço da NFD com mediana do faturamento.
        Retorna tipo corrigido ou None se não conseguir validar.

        Lógica:
            preco_caixa_mediano  = mediana(faturamento_produto.preco_produto_faturado)
            preco_unidade_estimado = preco_caixa_mediano / qtd_por_caixa (do padrão NxM)

            ratio_como_unidade = valor_unitario / preco_unidade_estimado
            ratio_como_caixa   = preco_caixa_mediano / valor_unitario

            O ratio mais próximo de 1 vence.

        Regras de skip (retorna None):
        - valor_unitario <= 0
        - tipo_deterministico não é CAIXA nem UNIDADE
        - Produto sem faturamento (< 5 vendas)
        - qtd_por_caixa <= 1 (CAIXA = UNIDADE, indistinguível)
        - Ratio ambíguo (vencedor >= 1.5 ou perdedor <= 2.5)

        Args:
            cod_produto: Código interno do produto
            valor_unitario: Preço unitário da NFD
            tipo_deterministico: Tipo classificado por _classificar_unidade()
            cache_precos: Cache local {cod_produto: dados ou None}

        Returns:
            Tipo corrigido ('CAIXA' ou 'UNIDADE') ou None se não pode validar
        """
        from sqlalchemy import text as sa_text

        # Skip se valor_unitario inválido
        if not valor_unitario or valor_unitario <= 0:
            return None

        # Validação só faz sentido para CAIXA vs UNIDADE
        if tipo_deterministico not in ('CAIXA', 'UNIDADE'):
            return None

        # Consultar cache ou buscar dados
        if cod_produto not in cache_precos:
            try:
                # 1. Mediana do preço de faturamento (preço por CAIXA)
                resultado_fat = db.session.execute(sa_text("""
                    SELECT
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY preco_produto_faturado) AS mediana,
                        COUNT(*) AS total
                    FROM faturamento_produto
                    WHERE cod_produto = :cod_produto
                      AND preco_produto_faturado > 0
                      AND status_nf = 'Lançado'
                      AND revertida = false
                """), {'cod_produto': cod_produto}).fetchone()

                if not resultado_fat or not resultado_fat.total or resultado_fat.total < 5:
                    cache_precos[cod_produto] = None
                else:
                    mediana_caixa = float(resultado_fat.mediana)
                    total_vendas = int(resultado_fat.total)

                    # 2. Buscar nome_produto do cadastro para extrair qtd_por_caixa (NxM)
                    from app.producao.models import CadastroPalletizacao
                    produto = CadastroPalletizacao.query.filter_by(
                        cod_produto=cod_produto
                    ).first()

                    qtd_por_caixa = None
                    if produto and produto.nome_produto:
                        match = re.search(r'(\d+)\s*[Xx]\s*\d+', produto.nome_produto)
                        if match:
                            qtd_por_caixa = int(match.group(1))

                    if not qtd_por_caixa or qtd_por_caixa <= 1:
                        cache_precos[cod_produto] = None
                    else:
                        cache_precos[cod_produto] = {
                            'mediana_caixa': mediana_caixa,
                            'qtd_por_caixa': qtd_por_caixa,
                            'total_vendas': total_vendas,
                        }
            except Exception as e:
                logger.warning(f"[NFD_SERVICE] Erro ao consultar preço para validação: {e}")
                cache_precos[cod_produto] = None

        # Verificar resultado do cache
        dados = cache_precos.get(cod_produto)
        if not dados:
            return None

        mediana_caixa = dados['mediana_caixa']
        qtd_por_caixa = dados['qtd_por_caixa']

        # Calcular preço unitário estimado (dividir preço da caixa por N)
        preco_unidade_estimado = mediana_caixa / qtd_por_caixa

        # Calcular ratios
        # ratio_como_unidade: se o preço da NFD fosse de UNIDADE, quão perto de 1 está?
        ratio_como_unidade = valor_unitario / preco_unidade_estimado if preco_unidade_estimado > 0 else 999.0
        # ratio_como_caixa: se o preço da NFD fosse de CAIXA, quão perto de 1 está?
        ratio_como_caixa = mediana_caixa / valor_unitario if valor_unitario > 0 else 999.0

        dist_unidade = abs(ratio_como_unidade - 1)
        dist_caixa = abs(ratio_como_caixa - 1)

        # Determinar vencedor (ratio mais próximo de 1)
        if dist_caixa < dist_unidade:
            tipo_sugerido = 'CAIXA'
            winner_ratio = ratio_como_caixa
            loser_ratio = ratio_como_unidade
        else:
            tipo_sugerido = 'UNIDADE'
            winner_ratio = ratio_como_unidade
            loser_ratio = ratio_como_caixa

        # Critérios conservadores para override:
        # - O ratio vencedor deve ser < 1.5 (próximo de 1)
        # - O ratio perdedor deve ser > 2.5 (claramente longe de 1)
        # Se ambos forem ambíguos → manter determinístico (None)
        if winner_ratio < 1.5 and loser_ratio > 2.5:
            return tipo_sugerido

        return None

    def _detectar_nfd_pallet(self, nfd_id: int) -> bool:
        """
        Detecta se uma NFD é de devolução de pallet/vasilhame.

        Critérios de detecção:
        1. CFOP nas linhas de produto está em CFOPS_PALLET (1920, 2920, 5920, 6920, etc.)
        2. Código do produto contém CODIGO_PRODUTO_PALLET (208000012)

        Args:
            nfd_id: ID da NFDevolucao

        Returns:
            True se for NFD de pallet, False caso contrário
        """
        try:
            # Buscar linhas de produto desta NFD
            linhas = NFDevolucaoLinha.query.filter_by(nf_devolucao_id=nfd_id).all()

            if not linhas:
                return False

            # Verificar se ALGUMA linha tem CFOP de pallet ou código de produto pallet
            for linha in linhas:
                # Verificar CFOP
                if linha.cfop and linha.cfop in CFOPS_PALLET:
                    logger.info(f"   🎯 CFOP {linha.cfop} identificado como pallet")
                    return True

                # Verificar código do produto
                if linha.codigo_produto_cliente:
                    # Remover caracteres não numéricos para comparação
                    codigo_limpo = ''.join(c for c in linha.codigo_produto_cliente if c.isdigit())
                    if CODIGO_PRODUTO_PALLET in codigo_limpo:
                        logger.info(f"   🎯 Código {linha.codigo_produto_cliente} identificado como pallet")
                        return True

            return False

        except Exception as e:
            logger.error(f"   ❌ Erro ao detectar NFD pallet: {e}")
            return False

    def _extrair_info_complementar(self, nfd: NFDevolucao, xml_base64: str) -> bool:
        """
        Extrai informações complementares (infCpl) do XML da NFD

        O campo infCpl contém texto livre do cliente, que pode incluir:
        - Motivo da devolução
        - Referência à NF de venda original
        - Observações gerais

        Args:
            nfd: NFDevolucao a atualizar
            xml_base64: XML em base64

        Returns:
            True se extraiu, False caso contrário
        """
        try:
            # Decodificar XML
            xml_bytes = base64.b64decode(xml_base64)
            try:
                xml_content = xml_bytes.decode('utf-8')
            except UnicodeDecodeError:
                xml_content = xml_bytes.decode('iso-8859-1')

            # Usar o parser para extrair infCpl
            parser = NFDXMLParser(xml_content)
            info_complementar = parser.get_info_complementar()

            if info_complementar:
                nfd.info_complementar = info_complementar
                logger.info(f"   📝 Info complementar extraída: {info_complementar[:100]}...")

            # Extrair data de emissão do XML (mais confiável que Odoo)
            data_emissao_xml = parser.get_data_emissao()
            if data_emissao_xml:
                nfd.data_emissao = data_emissao_xml.date() if hasattr(data_emissao_xml, 'date') else data_emissao_xml
                logger.info(f"   📅 Data emissão extraída do XML: {nfd.data_emissao}")

            return info_complementar is not None or data_emissao_xml is not None

        except Exception as e:
            logger.error(f"   ❌ Erro ao extrair info complementar: {e}")
            return False

    def _extrair_endereco_emitente(self, nfd: NFDevolucao, xml_base64: str) -> bool:
        """
        Extrai endereço do emitente (UF, município, CEP) do XML da NFD

        O emitente é o cliente que emitiu a nota de devolução.
        Esses dados são usados como origem do frete de retorno.

        Args:
            nfd: NFDevolucao a atualizar
            xml_base64: XML em base64

        Returns:
            True se extraiu, False caso contrário
        """
        try:
            # Decodificar XML
            xml_bytes = base64.b64decode(xml_base64)
            try:
                xml_content = xml_bytes.decode('utf-8')
            except UnicodeDecodeError:
                xml_content = xml_bytes.decode('iso-8859-1')

            # Usar o parser para extrair dados do emitente
            parser = NFDXMLParser(xml_content)
            dados_emitente = parser.get_dados_emitente()

            if dados_emitente:
                # Atualizar campos de endereço do emitente
                uf = dados_emitente.get('uf')
                municipio = dados_emitente.get('municipio')

                if uf:
                    nfd.uf_emitente = uf
                if municipio:
                    nfd.municipio_emitente = municipio

                # CEP e endereço podem ser extraídos de tags adicionais se necessário
                # Por ora, extraímos apenas UF e município que são os mais importantes

                if uf or municipio:
                    logger.info(f"   📍 Endereço emitente extraído: {uf}/{municipio}")
                    return True
                else:
                    logger.info("   ℹ️ Endereço do emitente não encontrado no XML")
                    return False
            else:
                logger.info("   ℹ️ Dados do emitente não encontrados no XML")
                return False

        except Exception as e:
            logger.error(f"   ❌ Erro ao extrair endereço do emitente: {e}")
            return False

    def _salvar_arquivos_nfd(self, nfd: NFDevolucao, nfd_data: Dict):
        """
        Salva PDF e XML da NFD no S3

        Args:
            nfd: NFDevolucao
            nfd_data: Dados do Odoo
        """
        # Organizar em pastas por data e CNPJ
        cnpj_limpo = nfd.cnpj_emitente.replace('.', '').replace('/', '').replace('-', '') if nfd.cnpj_emitente else 'sem_cnpj'
        data_hoje = agora_utc()
        pasta_base = f"devolucoes/nfd/{data_hoje.year}/{data_hoje.month:02d}/{cnpj_limpo}"

        # Usar chave de acesso para nome do arquivo
        chave_acesso = nfd.chave_nfd or str(nfd.id)

        # Salvar PDF
        pdf_base64 = nfd_data.get('l10n_br_pdf_dfe')
        if pdf_base64 and pdf_base64 != False:
            try:
                pdf_bytes = base64.b64decode(pdf_base64)
                from werkzeug.datastructures import FileStorage as WerkzeugFileStorage

                pdf_stream = BytesIO(pdf_bytes)
                file_storage_obj = WerkzeugFileStorage(
                    stream=pdf_stream,
                    filename=f"{chave_acesso}.pdf",
                    content_type='application/pdf'
                )

                pdf_path = self.file_storage.save_file(
                    file=file_storage_obj,
                    folder=pasta_base,
                    allowed_extensions=['pdf']
                )

                if pdf_path:
                    nfd.nfd_pdf_path = pdf_path
                    nfd.nfd_pdf_nome_arquivo = nfd_data.get('l10n_br_pdf_dfe_fname')
                    logger.info(f"   ✅ PDF salvo: {pdf_path}")

            except Exception as e:
                logger.error(f"   ❌ Erro ao salvar PDF: {e}")

        # Salvar XML
        xml_base64 = nfd_data.get('l10n_br_xml_dfe')
        if xml_base64 and xml_base64 != False:
            try:
                xml_bytes = base64.b64decode(xml_base64)
                from werkzeug.datastructures import FileStorage as WerkzeugFileStorage

                xml_stream = BytesIO(xml_bytes)
                file_storage_obj = WerkzeugFileStorage(
                    stream=xml_stream,
                    filename=f"{chave_acesso}.xml",
                    content_type='application/xml'
                )

                xml_path = self.file_storage.save_file(
                    file=file_storage_obj,
                    folder=pasta_base,
                    allowed_extensions=['xml']
                )

                if xml_path:
                    nfd.nfd_xml_path = xml_path
                    nfd.nfd_xml_nome_arquivo = nfd_data.get('l10n_br_xml_dfe_fname')
                    logger.info(f"   ✅ XML salvo: {xml_path}")

            except Exception as e:
                logger.error(f"   ❌ Erro ao salvar XML: {e}")

    # =========================================================================
    # MÉTODOS DE VINCULAÇÃO MANUAL
    # =========================================================================

    def vincular_nfd_manual(
        self,
        nfd_id: int,
        entrega_monitorada_id: int,
        usuario: str
    ) -> Dict:
        """
        Vincula manualmente uma NFD órfã a uma entrega monitorada

        IMPORTANTE: Também marca teve_devolucao = True na entrega

        Args:
            nfd_id: ID da NFDevolucao
            entrega_monitorada_id: ID da EntregaMonitorada
            usuario: Nome do usuário

        Returns:
            Dict com resultado
        """
        try:
            from app import db
            nfd = db.session.get(NFDevolucao,nfd_id) if nfd_id else None
            if not nfd:
                return {'sucesso': False, 'erro': 'NFD não encontrada'}

            entrega = db.session.get(EntregaMonitorada,entrega_monitorada_id) if entrega_monitorada_id else None
            if not entrega:
                return {'sucesso': False, 'erro': 'Entrega não encontrada'}

            # Vincular NFD à entrega
            nfd.entrega_monitorada_id = entrega_monitorada_id
            nfd.numero_nf_venda = entrega.numero_nf  # Atualizar numero_nf_venda
            nfd.atualizado_em = agora_utc_naive()
            nfd.atualizado_por = usuario

            # Sincronizar status_monitoramento com a entrega
            if entrega.status_finalizacao in ('Cancelada', 'Devolvida', 'Troca de NF'):
                nfd.status_monitoramento = entrega.status_finalizacao
                logger.info(f"📊 status_monitoramento sincronizado: {entrega.status_finalizacao}")

            # MARCAR teve_devolucao = True na entrega
            if not entrega.teve_devolucao:
                entrega.teve_devolucao = True
                logger.info(f"✅ Entrega {entrega.numero_nf} marcada como teve_devolucao=True")

            db.session.commit()

            logger.info(f"✅ NFD {nfd.numero_nfd} vinculada à entrega {entrega_monitorada_id} por {usuario}")

            return {
                'sucesso': True,
                'nfd_id': nfd_id,
                'entrega_monitorada_id': entrega_monitorada_id
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao vincular NFD: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def listar_nfds_orfas(
        self,
        cnpj_prefixo: Optional[str] = None,
        incluir_pallets: bool = False
    ) -> List[Dict]:
        """
        Lista NFDs órfãs (sem entrega_monitorada)

        IMPORTANTE: Por padrão, exclui NFDs de pallet/vasilhame que devem
        ser tratadas no módulo de pallet, não no módulo de devoluções.

        Args:
            cnpj_prefixo: Filtrar por prefixo CNPJ (8 dígitos)
            incluir_pallets: Se True, inclui NFDs de pallet (default: False)

        Returns:
            Lista de NFDs órfãs (excluindo pallets por padrão)
        """
        query = NFDevolucao.query.filter(
            NFDevolucao.entrega_monitorada_id.is_(None),
            NFDevolucao.origem_registro == 'ODOO',
            NFDevolucao.ativo == True
        )

        # Excluir NFDs de pallet por padrão
        if not incluir_pallets:
            query = query.filter(
                NFDevolucao.e_pallet_devolucao == False
            )

        if cnpj_prefixo:
            # Filtrar por prefixo CNPJ
            query = query.filter(
                NFDevolucao.cnpj_emitente.like(f'{cnpj_prefixo}%')
            )

        nfds = query.order_by(NFDevolucao.data_emissao.desc()).all()

        return [nfd.to_dict() for nfd in nfds]

    def listar_candidatos_vinculacao(
        self,
        nfd_id: int
    ) -> List[Dict]:
        """
        Lista possíveis candidatos para vinculação de uma NFD órfã

        Busca entregas monitoradas do mesmo CNPJ (prefixo) que ainda
        não têm NFD vinculada

        Args:
            nfd_id: ID da NFDevolucao órfã

        Returns:
            Lista de candidatos
        """
        from app import db
        nfd = db.session.get(NFDevolucao,nfd_id) if nfd_id else None
        if not nfd:
            return []

        # Obter prefixo CNPJ
        prefixo = nfd.prefixo_cnpj_emitente
        if not prefixo:
            return []

        # Buscar NFDs do monitoramento com mesmo prefixo CNPJ
        # que ainda não foram vinculadas ao Odoo
        from app.monitoramento.models import EntregaMonitorada # noqa: E402

        # Buscar entregas que têm devolução registrada mas sem DFe vinculado
        candidatos = db.session.query(NFDevolucao).filter(
            NFDevolucao.odoo_dfe_id.is_(None),
            NFDevolucao.origem_registro == 'MONITORAMENTO',
            NFDevolucao.ativo == True
        ).all()

        # Filtrar por prefixo CNPJ
        resultado = []
        for candidato in candidatos:
            # Verificar CNPJ via entrega monitorada
            if candidato.entrega_monitorada:
                cnpj_entrega = getattr(candidato.entrega_monitorada, 'cnpj_cliente', None)
                if cnpj_entrega:
                    cnpj_limpo = self._limpar_cnpj(cnpj_entrega)
                    if cnpj_limpo and cnpj_limpo.startswith(prefixo):
                        resultado.append({
                            'nfd_id': candidato.id,
                            'numero_nfd': candidato.numero_nfd,
                            'motivo': candidato.motivo,
                            'data_registro': candidato.data_registro.isoformat() if candidato.data_registro else None,
                            'entrega_id': candidato.entrega_monitorada_id,
                        })

        return resultado

    # =========================================================================
    # UTILITÁRIOS
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
        """Remove formatação de CNPJ"""
        if not cnpj:
            return None
        return cnpj.replace('.', '').replace('/', '').replace('-', '').strip()

    @staticmethod
    def _get_status_descricao(status_codigo):
        """Retorna descrição do status do DFE no Odoo

        Status do fluxo de entrada de NFD:
        - 01: Rascunho - NFD recebida, não processada
        - 02: Sincronizado - NFD sincronizada
        - 03: Ciência/Confirmado - NFD manifestada
        - 04: PO - Pedido de Compra criado, PENDENTE entrada física
        - 05: Rateio - Rateio de custos
        - 06: Concluído - ENTRADA FÍSICA REALIZADA
        - 07: Rejeitado - NFD rejeitada
        """
        STATUS_MAP = {
            '01': 'Rascunho',
            '02': 'Sincronizado',
            '03': 'Ciência/Confirmado',
            '04': 'PO',
            '05': 'Rateio',
            '06': 'Concluído',
            '07': 'Rejeitado',
        }
        return STATUS_MAP.get(status_codigo, f'Status {status_codigo}')


# =============================================================================
# FUNÇÕES HELPER
# =============================================================================

def get_nfd_service() -> NFDService:
    """Retorna instância do NFDService"""
    return NFDService()


def importar_nfds_odoo(dias_retroativos: int = 30, limite: int = None) -> Dict:
    """
    Função helper para importar NFDs do Odoo

    Args:
        dias_retroativos: Quantos dias para trás buscar
        limite: Limite de registros

    Returns:
        Dict com estatísticas
    """
    service = get_nfd_service()
    return service.importar_nfds(dias_retroativos=dias_retroativos, limite=limite)
