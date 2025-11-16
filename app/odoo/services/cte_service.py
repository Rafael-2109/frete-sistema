"""
Service para Importação de CTes (Conhecimento de Transporte) do Odoo
====================================================================

OBJETIVO:
    Buscar CTes do Odoo (modelo l10n_br_ciel_it_account.dfe)
    e registrar em ConhecimentoTransporte

FILTRO ODOO:
    ["&", "|", ("active", "=", True), ("active", "=", False), ("is_cte", "=", True)]

MODELO ODOO: l10n_br_ciel_it_account.dfe (com is_cte=True)

CAMPOS MAPEADOS (baseado em dados reais do Odoo):
    - dfe_id: ID do registro no Odoo
    - protnfe_infnfe_chnfe: Chave de acesso (44 dígitos)
    - nfe_infnfe_ide_nnf: Número do CTe
    - nfe_infnfe_ide_serie: Série do CTe
    - nfe_infnfe_ide_dhemi: Data de emissão
    - l10n_br_status: Status (01-07)
    - nfe_infnfe_total_icmstot_vnf: Valor total
    - nfe_infnfe_total_icms_vfrete: Valor do frete
    - nfe_infnfe_total_icms_vicms: Valor do ICMS
    - nfe_infnfe_emit_cnpj: CNPJ emissor (transportadora)
    - nfe_infnfe_emit_xnome: Nome emissor
    - nfe_infnfe_dest_cnpj: CNPJ destinatário
    - nfe_infnfe_rem_cnpj: CNPJ remetente
    - l10n_br_pdf_dfe: PDF em base64
    - l10n_br_xml_dfe: XML em base64

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import base64
from io import BytesIO
import json

from app import db
from app.fretes.models import ConhecimentoTransporte, Frete
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.cte_xml_parser import extrair_info_complementar
from app.utils.file_storage import get_file_storage

logger = logging.getLogger(__name__)


class CteService:
    """
    Service para importação de CTes do Odoo
    """

    def __init__(self):
        """Inicializa conexão com Odoo"""
        self.odoo = get_odoo_connection()
        self.file_storage = get_file_storage()

    def importar_ctes(
        self,
        dias_retroativos: Optional[int] = None,
        limite: Optional[int] = None,
        minutos_janela: Optional[int] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None
    ) -> Dict:
        """
        Importa CTes do Odoo

        Args:
            dias_retroativos: Quantos dias para trás buscar (padrão: 30) - Usado se data_inicio=None
            limite: Limite de registros (None = todos)
            minutos_janela: Se especificado, busca CTes atualizados nos últimos X minutos (incremental)
            data_inicio: Data início do período (formato: YYYY-MM-DD) - Prioridade sobre dias_retroativos
            data_fim: Data fim do período (formato: YYYY-MM-DD) - Opcional

        Returns:
            Dict com estatísticas da importação
        """
        logger.info("=" * 80)
        logger.info("📄 INICIANDO IMPORTAÇÃO DE CTes")
        logger.info("=" * 80)

        resultado = {
            'sucesso': False,
            'ctes_processados': 0,
            'ctes_novos': 0,
            'ctes_atualizados': 0,
            'ctes_ignorados': 0,
            'erros': []
        }

        try:
            # 1. Buscar CTes do Odoo
            if minutos_janela:
                # ✅ SINCRONIZAÇÃO INCREMENTAL: Últimos X minutos
                data_calc = (datetime.now() - timedelta(minutes=minutos_janela)).strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"🔄 Sincronização Incremental: Últimos {minutos_janela} minutos")
                logger.info(f"📅 Buscando CTes atualizados desde {data_calc}")
                ctes = self._buscar_ctes_odoo(data_calc, limite, usar_write_date=True)
            elif data_inicio:
                # ✅ SINCRONIZAÇÃO POR PERÍODO PERSONALIZADO
                logger.info(f"📅 Sincronização por Período Personalizado")
                logger.info(f"   Data Início: {data_inicio}")
                if data_fim:
                    logger.info(f"   Data Fim: {data_fim}")
                    ctes = self._buscar_ctes_odoo_periodo(data_inicio, data_fim, limite)
                else:
                    # Se só tem data_inicio, buscar até hoje usando write_date
                    logger.info(f"   Data Fim: Hoje")
                    data_hoje = datetime.now().strftime('%Y-%m-%d')
                    ctes = self._buscar_ctes_odoo_periodo(data_inicio, data_hoje, limite)
            else:
                # 📅 SINCRONIZAÇÃO INICIAL: Últimos X dias (padrão: 30)
                dias = dias_retroativos if dias_retroativos else 30
                data_calc = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
                logger.info(f"📅 Sincronização Inicial: Últimos {dias} dias")
                logger.info(f"📅 Buscando CTes desde {data_calc}")
                ctes = self._buscar_ctes_odoo(data_calc, limite, usar_write_date=False)

            if not ctes:
                logger.warning("⚠️  Nenhum CTe encontrado no Odoo")
                resultado['sucesso'] = True
                return resultado

            logger.info(f"📦 Total de CTes encontrados: {len(ctes)}")

            # ✅ OTIMIZAÇÃO 1: Buscar TODAS as referências de NFs de uma vez (batch read)
            logger.info("🚀 Coletando todos os refs_ids para batch read...")
            todos_refs_ids = []
            for cte_data in ctes:
                refs_ids = cte_data.get('refs_ids')
                if refs_ids and isinstance(refs_ids, (list, tuple)):
                    todos_refs_ids.extend(refs_ids)

            # Remover duplicatas
            todos_refs_ids = list(set(todos_refs_ids))
            logger.info(f"   📊 Total de referências únicas: {len(todos_refs_ids)}")

            # Buscar todas as referências de uma vez
            mapa_refs = {}
            if todos_refs_ids:
                try:
                    logger.info(f"   📡 Buscando {len(todos_refs_ids)} referências do Odoo em batch...")
                    referencias_batch = self.odoo.read(
                        'l10n_br_ciel_it_account.dfe.referencia',
                        todos_refs_ids,
                        ['infdoc_infnfe_chave']
                    )

                    # Criar mapa {ref_id: numero_nf}
                    for ref in referencias_batch:
                        ref_id = ref.get('id')
                        chave_nf = ref.get('infdoc_infnfe_chave')

                        if chave_nf and len(chave_nf) == 44:
                            numero_nf = chave_nf[25:34]
                            numero_nf_limpo = str(int(numero_nf))
                            mapa_refs[ref_id] = numero_nf_limpo

                    logger.info(f"   ✅ Mapa de referências criado: {len(mapa_refs)} NFs")
                except Exception as e:
                    logger.error(f"   ❌ Erro ao buscar referências em batch: {e}")

            # 2. Processar cada CTe
            for cte_data in ctes:
                try:
                    dfe_id = str(cte_data.get('id'))
                    numero_cte = cte_data.get('nfe_infnfe_ide_nnf', '')
                    logger.info(f"\n📋 Processando CTe: {numero_cte} (DFe ID {dfe_id})")

                    estatisticas = self._processar_cte(cte_data, mapa_refs)

                    # Verificar se foi ignorado
                    if estatisticas.get('ignorado'):
                        resultado['ctes_ignorados'] += 1
                        continue

                    resultado['ctes_processados'] += 1
                    if estatisticas.get('novo'):
                        resultado['ctes_novos'] += 1
                    else:
                        resultado['ctes_atualizados'] += 1

                except Exception as e:
                    erro_msg = f"Erro ao processar CTe {cte_data.get('id')}: {str(e)}"
                    logger.error(f"❌ {erro_msg}")
                    resultado['erros'].append(erro_msg)

            # 3. Commit final
            db.session.commit()

            resultado['sucesso'] = True
            logger.info("=" * 80)
            logger.info("✅ IMPORTAÇÃO DE CTes CONCLUÍDA")
            logger.info(f"   📊 Processados: {resultado['ctes_processados']}")
            logger.info(f"   ✨ Novos: {resultado['ctes_novos']}")
            logger.info(f"   🔄 Atualizados: {resultado['ctes_atualizados']}")
            logger.info(f"   ⏭️  Ignorados (< R$ 1,00): {resultado['ctes_ignorados']}")
            logger.info(f"   ❌ Erros: {len(resultado['erros'])}")
            logger.info("=" * 80)

            return resultado

        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro fatal na importação de CTes: {str(e)}"
            logger.error(f"❌ {erro_msg}")
            resultado['erros'].append(erro_msg)
            resultado['sucesso'] = False
            return resultado

    def _buscar_ctes_odoo(
        self,
        data_inicio: str,
        limite: Optional[int] = None,
        usar_write_date: bool = False
    ) -> List[Dict]:
        """
        Busca CTes no Odoo

        Filtro: ["&", "|", ("active", "=", True), ("active", "=", False), ("is_cte", "=", True)]

        Args:
            data_inicio: Data mínima (YYYY-MM-DD HH:MM:SS para write_date, YYYY-MM-DD para emissão)
            limite: Limite de registros
            usar_write_date: Se True, usa write_date (data de atualização). Se False, usa data de emissão

        Returns:
            Lista de CTes
        """
        try:
            # Filtro base
            if usar_write_date:
                # ✅ SINCRONIZAÇÃO INCREMENTAL: Usar write_date (data de atualização)
                # ✅ CORREÇÃO: Buscar APENAS active=True para evitar duplicatas
                filtros = [
                    "&",
                    "&",
                    ("active", "=", True),  # ✅ APENAS ativos
                    ("is_cte", "=", True),
                    ("write_date", ">=", data_inicio)  # Filtro por atualização
                ]
                logger.info(f"   Filtro: is_cte=True AND active=True AND write_date >= {data_inicio}")
            else:
                # 📅 SINCRONIZAÇÃO INICIAL: Usar data de emissão
                # ✅ CORREÇÃO: Buscar APENAS active=True para evitar duplicatas
                filtros = [
                    "&",
                    "&",
                    ("active", "=", True),  # ✅ APENAS ativos
                    ("is_cte", "=", True),
                    ("nfe_infnfe_ide_dhemi", ">=", data_inicio)  # Filtro por emissão
                ]
                logger.info(f"   Filtro: is_cte=True AND active=True AND data_emissao >= {data_inicio}")

            campos = [
                'id',
                'name',
                'active',
                'l10n_br_status',
                'l10n_br_data_entrada',
                'l10n_br_tipo_pedido',

                # Chave e numeração
                'protnfe_infnfe_chnfe',  # Chave de acesso
                'nfe_infnfe_ide_nnf',     # Número do CTe
                'nfe_infnfe_ide_serie',   # Série

                # Data
                'nfe_infnfe_ide_dhemi',   # Data de emissão

                # Valores
                'nfe_infnfe_total_icmstot_vnf',  # Valor total
                'nfe_infnfe_total_icms_vfrete',  # Valor do frete
                'nfe_infnfe_total_icms_vicms',   # Valor do ICMS

                # Emissor (Transportadora)
                'nfe_infnfe_emit_cnpj',
                'nfe_infnfe_emit_xnome',
                'nfe_infnfe_emit_ie',

                # Destinatário
                'nfe_infnfe_dest_cnpj',

                # Remetente
                'nfe_infnfe_rem_cnpj',

                # Expedidor
                'nfe_infnfe_exped_cnpj',

                # Municípios CTe
                'cte_infcte_ide_cmunini',
                'cte_infcte_ide_cmunfim',

                # Tomador
                'cte_infcte_ide_toma3_toma',

                # Informações complementares
                'nfe_infnfe_infadic_infcpl',

                # Arquivos
                'l10n_br_pdf_dfe',
                'l10n_br_pdf_dfe_fname',
                'l10n_br_xml_dfe',
                'l10n_br_xml_dfe_fname',

                # Relacionamentos Odoo (para referência)
                'partner_id',
                'invoice_ids',
                'purchase_fiscal_id',

                # Referências de NFs contidas no CTe
                'refs_ids',
            ]

            params = {'fields': campos}
            if limite:
                params['limit'] = limite

            ctes = self.odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe',
                'search_read',
                [filtros],
                params
            )

            return ctes or []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar CTes do Odoo: {e}")
            return []

    def _buscar_ctes_odoo_periodo(
        self,
        data_inicio: str,
        data_fim: str,
        limite: Optional[int] = None
    ) -> List[Dict]:
        """
        Busca CTes no Odoo por período usando write_date (data de atualização)

        Args:
            data_inicio: Data inicial (YYYY-MM-DD)
            data_fim: Data final (YYYY-MM-DD)
            limite: Limite de registros

        Returns:
            Lista de CTes
        """
        try:
            # ✅ Filtro com período usando WRITE_DATE (data de atualização no Odoo)
            # ✅ CORREÇÃO: Buscar APENAS active=True para evitar duplicatas
            filtros = [
                "&",
                "&",
                "&",
                ("active", "=", True),  # ✅ APENAS ativos
                ("is_cte", "=", True),
                ("write_date", ">=", data_inicio),
                ("write_date", "<=", f"{data_fim} 23:59:59")  # Até o final do dia
            ]

            logger.info(f"   Filtro: is_cte=True AND active=True AND write_date ENTRE {data_inicio} 00:00:00 E {data_fim} 23:59:59")

            # Usar mesmos campos do método _buscar_ctes_odoo
            campos = [
                'id', 'name', 'active', 'l10n_br_status', 'l10n_br_data_entrada', 'l10n_br_tipo_pedido',
                'protnfe_infnfe_chnfe', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
                'nfe_infnfe_ide_dhemi', 'nfe_infnfe_total_icmstot_vnf', 'nfe_infnfe_total_icms_vfrete',
                'nfe_infnfe_total_icms_vicms', 'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
                'nfe_infnfe_emit_ie', 'nfe_infnfe_dest_cnpj', 'nfe_infnfe_rem_cnpj', 'nfe_infnfe_exped_cnpj',
                'cte_infcte_ide_cmunini', 'cte_infcte_ide_cmunfim', 'cte_infcte_ide_toma3_toma',
                'nfe_infnfe_infadic_infcpl', 'l10n_br_pdf_dfe', 'l10n_br_pdf_dfe_fname',
                'l10n_br_xml_dfe', 'l10n_br_xml_dfe_fname', 'partner_id', 'invoice_ids',
                'purchase_fiscal_id', 'refs_ids'
            ]

            logger.info(f"   📡 Chamando Odoo search_read...")
            ctes = self.odoo.search_read(
                'l10n_br_ciel_it_account.dfe',
                filtros,
                campos,
                limit=limite if limite else None
            )

            logger.info(f"   ✅ Retornados: {len(ctes) if ctes else 0} CTes")
            return ctes or []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar CTes por período do Odoo: {e}")
            return []

    def _processar_cte(self, cte_data: Dict, mapa_refs: Dict = None) -> Dict:
        """
        Processa um CTe e cria/atualiza ConhecimentoTransporte

        Args:
            cte_data: Dados do CTe do Odoo
            mapa_refs: Mapa {ref_id: numero_nf} para evitar N+1

        Returns:
            Dict com estatísticas
        """
        dfe_id = str(cte_data.get('id'))

        # Extrair chave de acesso PRIMEIRO (é a UNIQUE constraint)
        chave_acesso = cte_data.get('protnfe_infnfe_chnfe')

        # ✅ CORREÇÃO: Verificar PRIMEIRO por chave_acesso (UNIQUE constraint)
        # Isso evita erro de duplicate key quando Odoo tem múltiplos DFes com mesma chave
        cte_existente = None

        if chave_acesso:
            cte_existente = ConhecimentoTransporte.query.filter_by(
                chave_acesso=chave_acesso
            ).first()

            if cte_existente:
                logger.info(f"   ✅ CTe encontrado por chave_acesso: ID {cte_existente.id} (DFe {cte_existente.dfe_id})")

                # ⚠️ Se DFe ID diferente, Odoo tem múltiplos DFes com mesma chave
                if cte_existente.dfe_id != dfe_id:
                    logger.warning(f"   ⚠️ Mesma chave com DFe IDs diferentes!")
                    logger.warning(f"      - DFe no banco: {cte_existente.dfe_id}")
                    logger.warning(f"      - DFe do Odoo: {dfe_id}")
                    logger.warning(f"      - Atualizando com dados do novo DFe")

        # Se não encontrou por chave, buscar por dfe_id (fallback)
        if not cte_existente:
            cte_existente = ConhecimentoTransporte.query.filter_by(dfe_id=dfe_id).first()

            if cte_existente:
                logger.info(f"   ✅ CTe encontrado por dfe_id: ID {cte_existente.id}")
        numero_cte = cte_data.get('nfe_infnfe_ide_nnf')
        serie_cte = cte_data.get('nfe_infnfe_ide_serie')
        odoo_name = cte_data.get('name')

        # Status do Odoo
        status_codigo = cte_data.get('l10n_br_status')
        status_descricao = ConhecimentoTransporte.get_status_descricao(status_codigo) if status_codigo else None

        # Datas
        data_emissao_str = cte_data.get('nfe_infnfe_ide_dhemi')
        data_emissao = self._parse_date(data_emissao_str)

        data_entrada_str = cte_data.get('l10n_br_data_entrada')
        data_entrada = self._parse_date(data_entrada_str)

        # Valores
        valor_total = cte_data.get('nfe_infnfe_total_icmstot_vnf')
        valor_frete = cte_data.get('nfe_infnfe_total_icms_vfrete')
        valor_icms = cte_data.get('nfe_infnfe_total_icms_vicms')

        # 🔴 FILTRO: Ignorar CTes com valor total < R$ 1,00
        if valor_total is not None and valor_total < 1.00:
            logger.info(f"   ⏭️  CTe {numero_cte} ignorado - Valor total R$ {valor_total:.2f} < R$ 1,00")
            return {'novo': False, 'ignorado': True}

        # Limpar CNPJs (remover formatação)
        cnpj_emitente = self._limpar_cnpj(cte_data.get('nfe_infnfe_emit_cnpj'))
        nome_emitente = cte_data.get('nfe_infnfe_emit_xnome')
        ie_emitente = cte_data.get('nfe_infnfe_emit_ie')

        cnpj_destinatario = self._limpar_cnpj(cte_data.get('nfe_infnfe_dest_cnpj'))
        cnpj_remetente = self._limpar_cnpj(cte_data.get('nfe_infnfe_rem_cnpj'))
        cnpj_expedidor = self._limpar_cnpj(cte_data.get('nfe_infnfe_exped_cnpj'))

        # Municípios
        municipio_inicio = cte_data.get('cte_infcte_ide_cmunini')
        municipio_fim = cte_data.get('cte_infcte_ide_cmunfim')

        # Tomador
        tomador = cte_data.get('cte_infcte_ide_toma3_toma')

        # Informações complementares
        info_complementares = cte_data.get('nfe_infnfe_infadic_infcpl')

        # Tipo de pedido
        tipo_pedido = cte_data.get('l10n_br_tipo_pedido')

        # Relacionamentos Odoo
        partner_id = self._extract_relation_id(cte_data.get('partner_id'))
        invoice_ids = self._extract_relation_list(cte_data.get('invoice_ids'))
        purchase_fiscal_id = self._extract_relation_id(cte_data.get('purchase_fiscal_id'))

        # ✅ OTIMIZAÇÃO: Extrair números de NFs do mapa (batch) ao invés de chamar Odoo
        numeros_nfs = self._extrair_numeros_nfs_do_mapa(cte_data.get('refs_ids'), mapa_refs)

        # Baixar e salvar PDF/XML
        pdf_path, xml_path = self._salvar_arquivos_cte(cte_data)

        # Nomes dos arquivos
        pdf_nome = cte_data.get('l10n_br_pdf_dfe_fname')
        xml_nome = cte_data.get('l10n_br_xml_dfe_fname')

        # ================================================
        # 🆕 PROCESSAR CTe COMPLEMENTAR (extrair do XML)
        # ================================================
        tipo_cte = '0'  # Padrão: Normal
        cte_complementa_chave = None
        cte_complementa_id = None
        motivo_complemento = None

        # Tentar extrair informações de CTe complementar do XML
        xml_base64 = cte_data.get('l10n_br_xml_dfe')
        if xml_base64:
            try:
                # Decodificar base64
                xml_bytes = base64.b64decode(xml_base64)

                # Tentar UTF-8 primeiro, depois ISO-8859-1 (Latin-1)
                try:
                    xml_content = xml_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    xml_content = xml_bytes.decode('iso-8859-1')

                info_comp = extrair_info_complementar(xml_content)

                if info_comp:
                    tipo_cte = '1'  # CTe Complementar
                    cte_complementa_chave = info_comp.get('chave_cte_original')
                    motivo_complemento = info_comp.get('motivo')

                    # Tentar buscar o CTe original no banco pela chave
                    if cte_complementa_chave:
                        cte_original = ConhecimentoTransporte.query.filter_by(
                            chave_acesso=cte_complementa_chave
                        ).first()

                        if cte_original:
                            cte_complementa_id = cte_original.id
                            logger.info(f"   🔗 CTe Complementar vinculado ao CTe #{cte_original.id} ({cte_original.numero_cte})")
                        else:
                            logger.warning(f"   ⚠️  CTe original não encontrado: {cte_complementa_chave}")

            except Exception as e:
                logger.warning(f"   ⚠️  Erro ao processar XML para CTe complementar: {e}")

        if cte_existente:
            # Atualizar
            logger.info(f"   🔄 Atualizando CTe existente: {numero_cte}")

            cte_existente.odoo_ativo = cte_data.get('active', True)
            cte_existente.odoo_name = odoo_name
            cte_existente.odoo_status_codigo = status_codigo
            cte_existente.odoo_status_descricao = status_descricao
            cte_existente.chave_acesso = chave_acesso
            cte_existente.numero_cte = numero_cte
            cte_existente.serie_cte = serie_cte
            cte_existente.data_emissao = data_emissao
            cte_existente.data_entrada = data_entrada
            cte_existente.valor_total = Decimal(str(valor_total)) if valor_total else None
            cte_existente.valor_frete = Decimal(str(valor_frete)) if valor_frete else None
            cte_existente.valor_icms = Decimal(str(valor_icms)) if valor_icms else None
            cte_existente.cnpj_emitente = cnpj_emitente
            cte_existente.nome_emitente = nome_emitente
            cte_existente.ie_emitente = ie_emitente
            cte_existente.cnpj_destinatario = cnpj_destinatario
            cte_existente.cnpj_remetente = cnpj_remetente
            cte_existente.cnpj_expedidor = cnpj_expedidor
            cte_existente.municipio_inicio = str(municipio_inicio) if municipio_inicio else None
            cte_existente.municipio_fim = str(municipio_fim) if municipio_fim else None
            cte_existente.tomador = str(tomador) if tomador else None
            cte_existente.informacoes_complementares = info_complementares
            cte_existente.tipo_pedido = tipo_pedido
            cte_existente.cte_pdf_path = pdf_path
            cte_existente.cte_xml_path = xml_path
            cte_existente.cte_pdf_nome_arquivo = pdf_nome
            cte_existente.cte_xml_nome_arquivo = xml_nome
            cte_existente.odoo_partner_id = partner_id
            cte_existente.odoo_invoice_ids = invoice_ids
            cte_existente.odoo_purchase_fiscal_id = purchase_fiscal_id
            cte_existente.numeros_nfs = numeros_nfs

            # 🆕 Atualizar campos de CTe complementar
            cte_existente.tipo_cte = tipo_cte
            cte_existente.cte_complementa_chave = cte_complementa_chave
            cte_existente.cte_complementa_id = cte_complementa_id
            cte_existente.motivo_complemento = motivo_complemento

            cte_existente.atualizado_em = datetime.now()
            cte_existente.atualizado_por = 'Sistema Odoo'

            # ✅ Calcular e gravar flag tomador_e_empresa
            cte_existente.tomador_e_empresa = cte_existente.calcular_tomador_e_empresa()

            return {'novo': False}

        else:
            # Criar novo
            logger.info(f"   ✨ Criando novo CTe: {numero_cte}")

            cte = ConhecimentoTransporte(
                dfe_id=dfe_id,
                odoo_ativo=cte_data.get('active', True),
                odoo_name=odoo_name,
                odoo_status_codigo=status_codigo,
                odoo_status_descricao=status_descricao,
                chave_acesso=chave_acesso,
                numero_cte=numero_cte,
                serie_cte=serie_cte,
                data_emissao=data_emissao,
                data_entrada=data_entrada,
                valor_total=Decimal(str(valor_total)) if valor_total else None,
                valor_frete=Decimal(str(valor_frete)) if valor_frete else None,
                valor_icms=Decimal(str(valor_icms)) if valor_icms else None,
                cnpj_emitente=cnpj_emitente,
                nome_emitente=nome_emitente,
                ie_emitente=ie_emitente,
                cnpj_destinatario=cnpj_destinatario,
                cnpj_remetente=cnpj_remetente,
                cnpj_expedidor=cnpj_expedidor,
                municipio_inicio=str(municipio_inicio) if municipio_inicio else None,
                municipio_fim=str(municipio_fim) if municipio_fim else None,
                tomador=str(tomador) if tomador else None,
                informacoes_complementares=info_complementares,
                tipo_pedido=tipo_pedido,
                cte_pdf_path=pdf_path,
                cte_xml_path=xml_path,
                cte_pdf_nome_arquivo=pdf_nome,
                cte_xml_nome_arquivo=xml_nome,
                odoo_partner_id=partner_id,
                odoo_invoice_ids=invoice_ids,
                odoo_purchase_fiscal_id=purchase_fiscal_id,
                numeros_nfs=numeros_nfs,
                # 🆕 Campos de CTe complementar
                tipo_cte=tipo_cte,
                cte_complementa_chave=cte_complementa_chave,
                cte_complementa_id=cte_complementa_id,
                motivo_complemento=motivo_complemento,
                importado_por='Sistema Odoo'
            )

            # ✅ Calcular e gravar flag tomador_e_empresa
            cte.tomador_e_empresa = cte.calcular_tomador_e_empresa()

            db.session.add(cte)

            return {'novo': True}

    def _salvar_arquivos_cte(
        self,
        cte_data: Dict
    ) -> tuple:
        """
        Salva PDF e XML do CTe em S3/local

        Args:
            cte_data: Dados do CTe

        Returns:
            tuple: (pdf_path, xml_path)
        """
        pdf_path = None
        xml_path = None

        # Limpar CNPJ para pasta
        cnpj_emitente = cte_data.get('nfe_infnfe_emit_cnpj', '')
        cnpj_limpo = cnpj_emitente.replace('.', '').replace('/', '').replace('-', '') if cnpj_emitente else 'sem_cnpj'

        # Organizar em pastas por data
        data_hoje = datetime.now()
        pasta_base = f"ctes/{data_hoje.year}/{data_hoje.month:02d}/{cnpj_limpo}"

        # Chave de acesso para nome do arquivo
        chave_acesso = cte_data.get('protnfe_infnfe_chnfe', str(cte_data['id']))

        # Salvar PDF
        pdf_base64 = cte_data.get('l10n_br_pdf_dfe')
        if pdf_base64 and pdf_base64 != False:
            try:
                logger.info(f"   📄 Decodificando PDF base64...")
                pdf_bytes = base64.b64decode(pdf_base64)
                logger.info(f"   📄 PDF decodificado: {len(pdf_bytes)} bytes")

                # ✅ OTIMIZAÇÃO: Usar BytesIO ao invés de arquivo temporário em disco
                from werkzeug.datastructures import FileStorage as WerkzeugFileStorage

                pdf_stream = BytesIO(pdf_bytes)
                file_storage_obj = WerkzeugFileStorage(
                    stream=pdf_stream,
                    filename=f"{chave_acesso}.pdf",
                    content_type='application/pdf'
                )

                logger.info(f"   ☁️  Enviando para S3: pasta={pasta_base}, arquivo={chave_acesso}.pdf")
                pdf_path = self.file_storage.save_file(
                    file=file_storage_obj,
                    folder=pasta_base,
                    allowed_extensions=['pdf']
                )

                if pdf_path:
                    logger.info(f"   ✅ PDF salvo no S3: {pdf_path}")
                else:
                    logger.error(f"   ❌ save_file retornou None!")

            except Exception as e:
                logger.error(f"   ❌ Erro ao salvar PDF: {e}")
                logger.exception("   📋 Traceback completo:")
        else:
            logger.warning(f"   ⚠️  PDF não disponível no Odoo (campo vazio ou False)")

        # Salvar XML
        xml_base64 = cte_data.get('l10n_br_xml_dfe')
        if xml_base64 and xml_base64 != False:
            try:
                xml_bytes = base64.b64decode(xml_base64)

                # ✅ OTIMIZAÇÃO: Usar BytesIO ao invés de arquivo temporário em disco
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
                    logger.info(f"   ✅ XML salvo: {xml_path}")

            except Exception as e:
                logger.error(f"   ❌ Erro ao salvar XML: {e}")

        return pdf_path, xml_path

    def vincular_cte_com_frete(
        self,
        cte_id: int,
        frete_id: int,
        manual: bool = True,
        usuario: str = None
    ) -> bool:
        """
        Vincula um CTe com um Frete do sistema

        Args:
            cte_id: ID do ConhecimentoTransporte
            frete_id: ID do Frete
            manual: Se o vínculo foi manual ou automático
            usuario: Nome do usuário que fez o vínculo

        Returns:
            bool: True se vinculado com sucesso
        """
        try:
            cte = ConhecimentoTransporte.query.get(cte_id)
            frete = Frete.query.get(frete_id)

            if not cte or not frete:
                return False

            cte.frete_id = frete_id
            cte.vinculado_manualmente = manual
            cte.vinculado_em = datetime.now()
            cte.vinculado_por = usuario or 'Sistema'
            cte.atualizado_em = datetime.now()

            db.session.commit()

            logger.info(f"✅ CTe {cte.numero_cte} vinculado ao Frete {frete.id}")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao vincular CTe com Frete: {e}")
            return False

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
    def _extract_relation_id(relation_data):
        """Extrai ID de relação many2one do Odoo"""
        if isinstance(relation_data, (list, tuple)) and len(relation_data) >= 1:
            return relation_data[0]
        return None

    @staticmethod
    def _extract_relation_list(relation_data):
        """Extrai lista de IDs de relação one2many/many2many do Odoo"""
        if isinstance(relation_data, (list, tuple)) and relation_data:
            return json.dumps(relation_data)
        return None

    @staticmethod
    def _extrair_numeros_nfs_do_mapa(refs_ids, mapa_refs):
        """
        ✅ OTIMIZADO: Extrai números de NFs do mapa pré-carregado (sem chamada ao Odoo)

        Args:
            refs_ids: Lista de IDs de referências deste CTe
            mapa_refs: Dicionário {ref_id: numero_nf} pré-carregado

        Returns:
            str: String com números de NFs separados por vírgula (ex: "141768,141769,141770")
        """
        if not refs_ids or not isinstance(refs_ids, (list, tuple)) or len(refs_ids) == 0:
            return None

        if not mapa_refs:
            # Fallback: se mapa não foi criado, retornar None
            logger.warning("   ⚠️  Mapa de referências não disponível")
            return None

        numeros_nfs = []

        for ref_id in refs_ids:
            numero_nf = mapa_refs.get(ref_id)
            if numero_nf:
                numeros_nfs.append(numero_nf)

        if numeros_nfs:
            nfs_string = ",".join(numeros_nfs)
            logger.info(f"   📄 NFs extraídas do mapa: {nfs_string}")
            return nfs_string

        return None

    def _extrair_numeros_nfs(self, refs_ids):
        """
        ⚠️ DEPRECATED: Mantido para compatibilidade, mas não é mais usado
        Use _extrair_numeros_nfs_do_mapa() para melhor performance

        Busca as referências de NFs no Odoo e extrai os números das NFs

        Args:
            refs_ids: Lista de IDs de l10n_br_ciel_it_account.dfe.referencia

        Returns:
            str: String com números de NFs separados por vírgula (ex: "141768,141769,141770")
        """
        if not refs_ids or not isinstance(refs_ids, (list, tuple)) or len(refs_ids) == 0:
            return None

        try:
            # Buscar registros de referência no Odoo
            referencias = self.odoo.read(
                'l10n_br_ciel_it_account.dfe.referencia',
                refs_ids,
                ['infdoc_infnfe_chave']
            )

            if not referencias:
                return None

            numeros_nfs = []

            for ref in referencias:
                chave_nf = ref.get('infdoc_infnfe_chave')

                if chave_nf and len(chave_nf) == 44:
                    # Extrair número da NF (posições 25-34, índice Python 0-based)
                    numero_nf = chave_nf[25:34]  # 9 dígitos

                    # Remover zeros à esquerda
                    numero_nf_limpo = str(int(numero_nf))

                    numeros_nfs.append(numero_nf_limpo)

            if numeros_nfs:
                # Retornar string separada por vírgula
                nfs_string = ",".join(numeros_nfs)
                logger.info(f"   📄 NFs extraídas: {nfs_string}")
                return nfs_string

            return None

        except Exception as e:
            logger.error(f"   ⚠️  Erro ao extrair números de NFs: {e}")
            return None
