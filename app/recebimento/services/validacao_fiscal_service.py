"""
Service de Validacao Fiscal - FASE 1
====================================

Valida campos fiscais de NF-e comparando com baseline (PerfilFiscalProdutoFornecedor).

Fluxo de Validacao:
1. NF recebida no scheduler
2. Para cada linha:
   a) Busca perfil local (PerfilFiscalProdutoFornecedor)
   b) Se NAO existe perfil:
      - Busca historico Odoo (3 ultimas NFs do produto/fornecedor)
      - Se CONSISTENTE → Cria perfil automaticamente
      - Se INCONSISTENTE ou NAO ENCONTROU → Tela 1a compra
   c) Se existe perfil:
      - Compara campos fiscais
      - Divergencia → Bloqueia recebimento

Campos validados:
- NCM, CFOP (exato)
- % ICMS, % ICMS ST, % IPI (exato)
- BC ICMS, BC ICMS ST, Tributos (percentual)

Referencia: .claude/references/RECEBIMENTO_MATERIAIS.md
"""

import logging
import json
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import Counter

from app import db
from app.recebimento.models import (
    PerfilFiscalProdutoFornecedor,
    DivergenciaFiscal,
    CadastroPrimeiraCompra,
    ValidacaoFiscalDfe
)
from app.odoo.utils.connection import get_odoo_connection
from app.utils.cnpj_utils import normalizar_cnpj, obter_nome_empresa

logger = logging.getLogger(__name__)

# Numero de NFs para consultar historico
HISTORICO_NFS_LIMITE = 3


class ValidacaoFiscalService:
    """
    Service para validacao fiscal de NF-e.
    Compara dados fiscais com baseline (PerfilFiscalProdutoFornecedor).
    """

    # Mapeamento de campos DFE Line -> validacao
    CAMPOS_VALIDACAO = {
        'ncm': {
            'label': 'NCM',
            'tipo': 'exato',
            'field_dfe': 'det_prod_ncm',
            'field_perfil': 'ncm_esperado'
        },
        'cfop': {
            'label': 'CFOP',
            'tipo': 'lista',  # Pode ter varios CFOPs validos
            'field_dfe': 'det_prod_cfop',
            'field_perfil': 'cfop_esperados'
        },
        'aliq_icms': {
            'label': '% ICMS',
            'tipo': 'exato',
            'field_dfe': 'det_imposto_icms_picms',
            'field_perfil': 'aliquota_icms_esperada'
        },
        'reducao_bc_icms': {
            'label': 'Red. BC ICMS',
            'tipo': 'exato',
            'field_dfe': 'det_imposto_icms_predbc',
            'field_perfil': 'reducao_bc_icms_esperada'
        },
        # NOTA: det_imposto_icms_picmsst nao existe no Odoo
        # ICMS ST sera calculado a partir de vicmsst/vbcst quando necessario
        'aliq_icms_st': {
            'label': '% ICMS ST',
            'tipo': 'exato',
            'field_dfe': '_calc_aliq_icms_st',  # Campo calculado
            'field_perfil': 'aliquota_icms_st_esperada'
        },
        'aliq_ipi': {
            'label': '% IPI',
            'tipo': 'exato',
            'field_dfe': 'det_imposto_ipi_pipi',
            'field_perfil': 'aliquota_ipi_esperada'
        },
        'bc_icms': {
            'label': 'BC ICMS',
            'tipo': 'percentual',
            'field_dfe': 'det_imposto_icms_vbc',
            'tolerancia_field': 'tolerancia_bc_icms_pct'
        },
        'bc_icms_st': {
            'label': 'BC ICMS ST',
            'tipo': 'percentual',
            'field_dfe': 'det_imposto_icms_vbcst',
            'tolerancia_field': 'tolerancia_bc_icms_st_pct'
        },
        # PIS
        'cst_pis': {
            'label': 'CST PIS',
            'tipo': 'exato',
            'field_dfe': 'det_imposto_pis_cst',
            'field_perfil': 'cst_pis_esperado'
        },
        'aliq_pis': {
            'label': '% PIS',
            'tipo': 'exato',
            'field_dfe': 'det_imposto_pis_ppis',
            'field_perfil': 'aliquota_pis_esperada'
        },
        # COFINS
        'cst_cofins': {
            'label': 'CST COFINS',
            'tipo': 'exato',
            'field_dfe': 'det_imposto_cofins_cst',
            'field_perfil': 'cst_cofins_esperado'
        },
        'aliq_cofins': {
            'label': '% COFINS',
            'tipo': 'exato',
            'field_dfe': 'det_imposto_cofins_pcofins',
            'field_perfil': 'aliquota_cofins_esperada'
        },
    }

    def __init__(self):
        self.odoo = None

    def _get_odoo(self):
        """Obtem conexao Odoo lazy"""
        if self.odoo is None:
            self.odoo = get_odoo_connection()
            if not self.odoo.authenticate():
                raise Exception("Falha na autenticacao com Odoo")
        return self.odoo

    def validar_nf(self, odoo_dfe_id: int) -> Dict[str, Any]:
        """
        Valida TODAS as linhas de uma NF.
        Retorna resultado consolidado.

        Args:
            odoo_dfe_id: ID do DFE no Odoo

        Returns:
            {
                'dfe_id': int,
                'status': 'aprovado' | 'bloqueado' | 'primeira_compra',
                'linhas_validadas': int,
                'divergencias': List[Dict],
                'primeira_compra': List[Dict],
                'erro': str | None
            }
        """
        resultado = {
            'dfe_id': odoo_dfe_id,
            'status': 'aprovado',
            'linhas_validadas': 0,
            'divergencias': [],
            'primeira_compra': [],
            'erro': None
        }

        try:
            # 0. Obter conexao Odoo
            odoo = self._get_odoo()

            # 1. Buscar DFE no Odoo
            dfe = self._buscar_dfe(odoo_dfe_id)
            if not dfe:
                resultado['status'] = 'erro'
                resultado['erro'] = f'DFE {odoo_dfe_id} nao encontrado no Odoo'
                return resultado

            # 2. Buscar linhas do DFE
            linhas = self._buscar_linhas_dfe(odoo_dfe_id)
            if not linhas:
                resultado['status'] = 'erro'
                resultado['erro'] = f'DFE {odoo_dfe_id} sem linhas de produto'
                return resultado

            # 3. Extrair CNPJ do fornecedor
            cnpj = self._extrair_cnpj(dfe)
            razao = dfe.get('nfe_infnfe_emit_xnome', '')

            # 3.0.1. Extrair empresa compradora (destinatario da NF)
            cnpj_empresa_compradora = normalizar_cnpj(dfe.get('nfe_infnfe_dest_cnpj', ''))
            razao_empresa_compradora = dfe.get('nfe_infnfe_dest_xnome', '')

            # 3.1. Extrair dados da NF
            crt = dfe.get('nfe_infnfe_emit_crt')
            dados_nf = {
                'numero_nf': dfe.get('nfe_infnfe_ide_nnf'),
                'serie_nf': dfe.get('nfe_infnfe_ide_serie'),
                'chave_nfe': dfe.get('protnfe_infnfe_chnfe'),
                'uf_fornecedor': dfe.get('nfe_infnfe_emit_uf'),
                'cidade_fornecedor': None,  # Sera buscado do partner
                'regime_tributario': str(crt) if crt and crt is not False else None,
                'cnpj_empresa_compradora': cnpj_empresa_compradora,
                'razao_empresa_compradora': razao_empresa_compradora
            }

            # 3.2. Buscar cidade do fornecedor (do partner_id)
            partner_id = dfe.get('partner_id')
            if partner_id and isinstance(partner_id, (list, tuple)) and len(partner_id) > 0:
                partner_dados = odoo.search_read(
                    'res.partner',
                    [['id', '=', partner_id[0]]],
                    fields=['l10n_br_municipio_id', 'state_id'],
                    limit=1
                )
                if partner_dados:
                    # l10n_br_municipio_id retorna [id, "Nome (UF)"] - Ex: [5570, "Brasília (DF)"]
                    municipio = partner_dados[0].get('l10n_br_municipio_id')
                    if municipio and isinstance(municipio, (list, tuple)) and len(municipio) > 1:
                        nome_cidade = municipio[1].split('(')[0].strip() if '(' in municipio[1] else municipio[1]
                        dados_nf['cidade_fornecedor'] = nome_cidade
                    # state_id retorna [id, nome_estado]
                    state = partner_dados[0].get('state_id')
                    if state and isinstance(state, (list, tuple)) and not dados_nf['uf_fornecedor']:
                        # Se nao veio do DFE, pega do partner
                        dados_nf['uf_fornecedor'] = state[1][:2] if len(state) > 1 else None

            # 3.3. Resolver default_code de todos os product_ids em bulk
            product_ids_unicos = set()
            for linha in linhas:
                pid = linha.get('product_id', [None, ''])[0] if linha.get('product_id') else None
                if pid:
                    product_ids_unicos.add(int(pid))

            # Mapeamento: product_id -> {default_code, name}
            mapa_produtos = {}
            if product_ids_unicos:
                produtos_odoo = odoo.search_read(
                    'product.product',
                    [['id', 'in', list(product_ids_unicos)]],
                    fields=['id', 'default_code', 'name']
                )
                for p in produtos_odoo:
                    mapa_produtos[p['id']] = {
                        'default_code': str(p.get('default_code', '')).strip() if p.get('default_code') else None,
                        'name': p.get('name', '')
                    }

            # 3.4. Resolver nome da empresa compradora (usa mapeamento centralizado)
            nome_empresa = obter_nome_empresa(cnpj_empresa_compradora) or razao_empresa_compradora

            # 4. Validar cada linha
            for linha in linhas:
                product_id_odoo = linha.get('product_id', [None, ''])[0] if linha.get('product_id') else None

                if not product_id_odoo:
                    logger.warning(f"Linha {linha.get('id')} sem product_id, pulando...")
                    continue

                # Resolver default_code (codigo interno) a partir do product_id
                produto_info = mapa_produtos.get(int(product_id_odoo), {})
                if produto_info.get('default_code'):
                    cod_produto = produto_info['default_code']
                    nome_produto_interno = produto_info.get('name', '')
                else:
                    # Fallback: usar product_id se nao tiver default_code
                    cod_produto = str(product_id_odoo)
                    nome_produto_interno = linha.get('det_prod_xprod', '')
                    logger.warning(
                        f"Produto ID {product_id_odoo} sem default_code no Odoo, "
                        f"usando product_id como cod_produto"
                    )

                nome_produto = linha.get('det_prod_xprod', '')

                # Buscar perfil fiscal (baseline) - chave: empresa + fornecedor + produto
                perfil = PerfilFiscalProdutoFornecedor.query.filter_by(
                    cnpj_empresa_compradora=cnpj_empresa_compradora,
                    cnpj_fornecedor=cnpj,
                    cod_produto=cod_produto,
                    ativo=True
                ).first()

                if not perfil:
                    # Sem perfil local → Buscar historico no Odoo
                    historico_resultado = self._processar_sem_perfil(
                        odoo_dfe_id=odoo_dfe_id,
                        linha=linha,
                        cod_produto=cod_produto,
                        nome_produto=nome_produto,
                        cnpj=cnpj,
                        razao=razao,
                        dados_nf=dados_nf,
                        nome_produto_interno=nome_produto_interno,
                        nome_empresa=nome_empresa
                    )

                    if historico_resultado['acao'] == 'perfil_criado':
                        # Perfil criado automaticamente → continua validacao normal
                        perfil = historico_resultado['perfil']
                        logger.info(
                            f"Perfil criado automaticamente: produto={cod_produto}, "
                            f"fornecedor={cnpj}, perfil_id={perfil.id}"
                        )
                        # Nao precisa comparar, pois acabou de criar do mesmo historico
                    else:
                        # 1a compra ou historico inconsistente
                        resultado['primeira_compra'].append(historico_resultado['registro'])
                        resultado['status'] = 'primeira_compra'
                else:
                    # Com perfil = comparar
                    divergencias = self._comparar_com_baseline(
                        linha=linha,
                        perfil=perfil,
                        odoo_dfe_id=odoo_dfe_id,
                        razao=razao,
                        dados_nf=dados_nf
                    )
                    if divergencias:
                        resultado['divergencias'].extend(divergencias)
                        resultado['status'] = 'bloqueado'

                resultado['linhas_validadas'] += 1

            logger.info(
                f"Validacao DFE {odoo_dfe_id}: status={resultado['status']}, "
                f"linhas={resultado['linhas_validadas']}, "
                f"divergencias={len(resultado['divergencias'])}, "
                f"primeira_compra={len(resultado['primeira_compra'])}"
            )

        except Exception as e:
            logger.error(f"Erro ao validar NF {odoo_dfe_id}: {e}")
            resultado['status'] = 'erro'
            resultado['erro'] = str(e)

        return resultado

    def _buscar_dfe(self, odoo_dfe_id: int) -> Optional[Dict]:
        """Busca DFE no Odoo"""
        odoo = self._get_odoo()

        campos = [
            'id', 'name', 'partner_id',
            'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
            'nfe_infnfe_infadic_infcpl',
            'nfe_infnfe_ide_finnfe',
            # Dados da NF para identificacao
            'nfe_infnfe_ide_nnf',       # Numero da NF
            'nfe_infnfe_ide_serie',     # Serie da NF
            'protnfe_infnfe_chnfe',     # Chave de acesso NF-e
            # Localizacao do emitente
            'nfe_infnfe_emit_uf',       # UF do emitente
            # Regime tributario do emitente (CRT)
            'nfe_infnfe_emit_crt'       # 1=Simples, 2=Simples excesso, 3=Normal
        ]

        registros = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            [['id', '=', odoo_dfe_id]],
            fields=campos,
            limit=1
        )

        return registros[0] if registros else None

    def _buscar_linhas_dfe(self, odoo_dfe_id: int) -> List[Dict]:
        """Busca linhas do DFE no Odoo"""
        odoo = self._get_odoo()

        campos = [
            'id', 'dfe_id', 'product_id',
            'det_prod_xprod', 'det_prod_ncm', 'det_prod_cfop', 'det_prod_cprod',
            # Quantidade e valores do produto
            'det_prod_qcom', 'det_prod_ucom', 'det_prod_vuncom', 'det_prod_vprod',
            # ICMS
            'det_imposto_icms_picms', 'det_imposto_icms_vbc', 'det_imposto_icms_vicms',
            'det_imposto_icms_vbcst', 'det_imposto_icms_vicmsst',  # Para calcular aliq ST
            # IPI
            'det_imposto_ipi_pipi', 'det_imposto_ipi_vipi',
            # PIS
            'det_imposto_pis_cst', 'det_imposto_pis_ppis', 'det_imposto_pis_vbc', 'det_imposto_pis_vpis',
            # COFINS
            'det_imposto_cofins_cst', 'det_imposto_cofins_pcofins', 'det_imposto_cofins_vbc', 'det_imposto_cofins_vcofins'
        ]

        return odoo.search_read(
            'l10n_br_ciel_it_account.dfe.line',
            [['dfe_id', '=', odoo_dfe_id]],
            fields=campos
        )

    def _extrair_cnpj(self, dfe: Dict) -> str:
        """Extrai CNPJ do fornecedor do DFE"""
        cnpj = dfe.get('nfe_infnfe_emit_cnpj', '')
        # Limpar formatacao usando funcao centralizada
        return normalizar_cnpj(cnpj)

    # =========================================================================
    # BUSCA HISTORICA NO ODOO
    # =========================================================================

    def _processar_sem_perfil(
        self,
        odoo_dfe_id: int,
        linha: Dict,
        cod_produto: str,
        nome_produto: str,
        cnpj: str,
        razao: str,
        dados_nf: Dict = None,
        nome_produto_interno: str = None,
        nome_empresa: str = None
    ) -> Dict:
        """
        Processa linha sem perfil local.
        Busca historico no Odoo e decide: criar perfil ou 1a compra.

        Returns:
            {
                'acao': 'perfil_criado' | 'primeira_compra',
                'perfil': PerfilFiscalProdutoFornecedor | None,
                'registro': Dict | None,
                'motivo': str
            }
        """
        # 1. Buscar historico no Odoo (3 ultimas NFs do produto/fornecedor)
        historico = self._buscar_historico_odoo(
            cod_produto=cod_produto,
            cnpj_fornecedor=cnpj,
            excluir_dfe_id=odoo_dfe_id  # Excluir a NF atual
        )

        if not historico:
            # Sem historico → 1a compra real
            logger.info(
                f"Sem historico Odoo: produto={cod_produto}, fornecedor={cnpj} → 1a compra"
            )
            registro = self._criar_registro_primeira_compra(
                odoo_dfe_id=odoo_dfe_id,
                linha=linha,
                cnpj=cnpj,
                razao=razao,
                dados_nf=dados_nf
            )
            return {
                'acao': 'primeira_compra',
                'perfil': None,
                'registro': registro,
                'motivo': 'sem_historico_odoo'
            }

        # 2. Verificar consistencia do historico
        consistente, dados_consistentes = self._verificar_consistencia_historico(historico)

        if consistente:
            # Historico consistente → Criar perfil automaticamente
            logger.info(
                f"Historico consistente ({len(historico)} NFs): "
                f"produto={cod_produto}, fornecedor={cnpj} → Criando perfil"
            )
            perfil = self._criar_perfil_automatico(
                cod_produto=cod_produto,
                cnpj_fornecedor=cnpj,
                cnpj_empresa_compradora=dados_nf.get('cnpj_empresa_compradora') if dados_nf else None,
                dados=dados_consistentes,
                dfe_ids=[h['dfe_id'] for h in historico],
                nome_produto=nome_produto_interno,
                razao_fornecedor=razao,
                nome_empresa=nome_empresa
            )
            return {
                'acao': 'perfil_criado',
                'perfil': perfil,
                'registro': None,
                'motivo': 'historico_consistente'
            }
        else:
            # Historico inconsistente → 1a compra para validacao manual
            logger.warning(
                f"Historico INCONSISTENTE ({len(historico)} NFs): "
                f"produto={cod_produto}, fornecedor={cnpj} → 1a compra"
            )
            registro = self._criar_registro_primeira_compra(
                odoo_dfe_id=odoo_dfe_id,
                linha=linha,
                cnpj=cnpj,
                razao=razao,
                dados_nf=dados_nf
            )
            return {
                'acao': 'primeira_compra',
                'perfil': None,
                'registro': registro,
                'motivo': 'historico_inconsistente'
            }

    def _buscar_historico_odoo(
        self,
        cod_produto: str,
        cnpj_fornecedor: str,
        excluir_dfe_id: int = None
    ) -> List[Dict]:
        """
        Busca historico de NFs do produto/fornecedor no Odoo.

        Args:
            cod_produto: Codigo interno do produto (default_code)
            cnpj_fornecedor: CNPJ do fornecedor (apenas digitos)
            excluir_dfe_id: ID do DFE a excluir da busca

        Retorna lista de dicts com dados fiscais das ultimas N NFs.
        """
        odoo = self._get_odoo()

        # Resolver product_id a partir do default_code
        # Se cod_produto e numerico puro, pode ser um product_id legado
        try:
            product_id_int = int(cod_produto)
            # Verificar se e um product_id valido
            produto = odoo.search_read(
                'product.product',
                [['id', '=', product_id_int]],
                fields=['id', 'default_code'],
                limit=1
            )
            if produto:
                product_id = product_id_int
            else:
                # Nao existe como ID, tentar como default_code
                produto = odoo.search_read(
                    'product.product',
                    [['default_code', '=', cod_produto]],
                    fields=['id'],
                    limit=1
                )
                if not produto:
                    logger.warning(f"Produto nao encontrado no Odoo: {cod_produto}")
                    return []
                product_id = produto[0]['id']
        except (ValueError, TypeError):
            # Nao e numerico, buscar por default_code
            produto = odoo.search_read(
                'product.product',
                [['default_code', '=', cod_produto]],
                fields=['id'],
                limit=1
            )
            if not produto:
                logger.warning(f"Produto nao encontrado no Odoo por default_code: {cod_produto}")
                return []
            product_id = produto[0]['id']

        # Buscar DFEs do fornecedor (tipo compra)
        # l10n_br_status = '04' significa processado/concluido
        # Excluir devolucoes (finnfe = 4)
        filtro_dfe = [
            ['nfe_infnfe_emit_cnpj', 'ilike', cnpj_fornecedor],
            ['l10n_br_tipo_pedido', '=', 'compra'],
            ['l10n_br_status', '=', '04'],  # Apenas NFs processadas
            ['nfe_infnfe_ide_finnfe', '!=', '4']  # Excluir devolucoes
        ]

        if excluir_dfe_id:
            filtro_dfe.append(['id', '!=', excluir_dfe_id])

        # Buscar DFEs
        dfes = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            filtro_dfe,
            fields=['id', 'name', 'nfe_infnfe_ide_dhemi'],
            limit=50  # Buscar mais para filtrar por produto depois
        )

        if not dfes:
            return []

        # Ordenar por data de emissao decrescente (localmente, API nao suporta order)
        dfes.sort(key=lambda x: x.get('nfe_infnfe_ide_dhemi', ''), reverse=True)

        # Para cada DFE, buscar linhas do produto especifico
        historico = []
        for dfe in dfes:
            if len(historico) >= HISTORICO_NFS_LIMITE:
                break

            linhas = odoo.search_read(
                'l10n_br_ciel_it_account.dfe.line',
                [
                    ['dfe_id', '=', dfe['id']],
                    ['product_id', '=', product_id]
                ],
                fields=[
                    'id', 'det_prod_ncm', 'det_prod_cfop',
                    'det_imposto_icms_picms', 'det_imposto_icms_vbcst',
                    'det_imposto_icms_vicmsst',  # Para calcular aliq ST
                    'det_imposto_icms_predbc',  # Reducao BC ICMS
                    'det_imposto_ipi_pipi', 'det_imposto_ipi_vipi',
                    'det_imposto_icms_cst',
                    # PIS
                    'det_imposto_pis_cst', 'det_imposto_pis_ppis',
                    'det_imposto_pis_vpis',
                    # COFINS
                    'det_imposto_cofins_cst', 'det_imposto_cofins_pcofins',
                    'det_imposto_cofins_vcofins'
                ],
                limit=1
            )

            if linhas:
                linha = linhas[0]
                # Calcular aliquota ICMS ST = vicmsst / vbcst * 100
                aliq_icms_st = self._calcular_aliq_icms_st(linha)

                # IPI: se nao tem valor de IPI, aliquota e None (nao se aplica)
                aliq_ipi = self._to_decimal(linha.get('det_imposto_ipi_pipi'))
                vipi = self._to_decimal(linha.get('det_imposto_ipi_vipi'))
                if vipi is None or vipi == 0:
                    aliq_ipi = None

                # PIS: se nao tem valor de PIS, aliquota e None
                aliq_pis = self._to_decimal(linha.get('det_imposto_pis_ppis'))
                vpis = self._to_decimal(linha.get('det_imposto_pis_vpis'))
                if vpis is None or vpis == 0:
                    aliq_pis = None

                # COFINS: se nao tem valor de COFINS, aliquota e None
                aliq_cofins = self._to_decimal(linha.get('det_imposto_cofins_pcofins'))
                vcofins = self._to_decimal(linha.get('det_imposto_cofins_vcofins'))
                if vcofins is None or vcofins == 0:
                    aliq_cofins = None

                historico.append({
                    'dfe_id': dfe['id'],
                    'dfe_name': dfe['name'],
                    'data': dfe.get('nfe_infnfe_ide_dhemi'),
                    'ncm': linha.get('det_prod_ncm'),
                    'cfop': linha.get('det_prod_cfop'),
                    'cst_icms': linha.get('det_imposto_icms_cst'),
                    'aliq_icms': self._to_decimal(linha.get('det_imposto_icms_picms')),
                    'reducao_bc_icms': self._to_decimal(linha.get('det_imposto_icms_predbc')),
                    'aliq_icms_st': aliq_icms_st,
                    'aliq_ipi': aliq_ipi,
                    # PIS
                    'cst_pis': linha.get('det_imposto_pis_cst'),
                    'aliq_pis': aliq_pis,
                    # COFINS
                    'cst_cofins': linha.get('det_imposto_cofins_cst'),
                    'aliq_cofins': aliq_cofins
                })

        logger.debug(
            f"Historico Odoo: produto={cod_produto} (product_id={product_id}), "
            f"fornecedor={cnpj_fornecedor}, encontrados={len(historico)} registros"
        )

        return historico

    def _verificar_consistencia_historico(
        self,
        historico: List[Dict]
    ) -> Tuple[bool, Dict]:
        """
        Verifica se o historico e consistente (mesmos valores fiscais).

        Campos verificados para consistencia:
        - NCM (deve ser identico)
        - % ICMS (deve ser identico)
        - % ICMS ST (deve ser identico)
        - % IPI (deve ser identico)
        - CST PIS (deve ser identico)
        - % PIS (deve ser identico)
        - CST COFINS (deve ser identico)
        - % COFINS (deve ser identico)

        CFOP pode variar (operacoes diferentes), entao coleta todos os unicos.

        Returns:
            (consistente: bool, dados: Dict com valores consistentes)
        """
        if not historico:
            return False, {}

        # Extrair valores de cada campo
        ncms = [h['ncm'] for h in historico if h['ncm']]
        cfops = [h['cfop'] for h in historico if h['cfop']]
        aliqs_icms = [h['aliq_icms'] for h in historico if h['aliq_icms'] is not None]
        reducoes_bc_icms = [h.get('reducao_bc_icms') for h in historico if h.get('reducao_bc_icms') is not None]
        aliqs_icms_st = [h['aliq_icms_st'] for h in historico if h['aliq_icms_st'] is not None]
        aliqs_ipi = [h['aliq_ipi'] for h in historico if h['aliq_ipi'] is not None]
        csts = [h['cst_icms'] for h in historico if h['cst_icms']]
        # PIS
        csts_pis = [h.get('cst_pis') for h in historico if h.get('cst_pis')]
        aliqs_pis = [h.get('aliq_pis') for h in historico if h.get('aliq_pis') is not None]
        # COFINS
        csts_cofins = [h.get('cst_cofins') for h in historico if h.get('cst_cofins')]
        aliqs_cofins = [h.get('aliq_cofins') for h in historico if h.get('aliq_cofins') is not None]

        # Verificar consistencia de cada campo
        consistente = True
        motivos_inconsistencia = []

        # NCM - deve ser unico
        if len(set(ncms)) > 1:
            consistente = False
            motivos_inconsistencia.append(f"NCM: {set(ncms)}")

        # % ICMS - deve ser unico
        if len(set(aliqs_icms)) > 1:
            consistente = False
            motivos_inconsistencia.append(f"ICMS: {set(aliqs_icms)}")

        # % Reducao BC ICMS - deve ser unico
        if len(set(reducoes_bc_icms)) > 1:
            consistente = False
            motivos_inconsistencia.append(f"Red. BC ICMS: {set(reducoes_bc_icms)}")

        # % ICMS ST - deve ser unico
        if len(set(aliqs_icms_st)) > 1:
            consistente = False
            motivos_inconsistencia.append(f"ICMS ST: {set(aliqs_icms_st)}")

        # % IPI - deve ser unico
        if len(set(aliqs_ipi)) > 1:
            consistente = False
            motivos_inconsistencia.append(f"IPI: {set(aliqs_ipi)}")

        # CST PIS - deve ser unico
        if len(set(csts_pis)) > 1:
            consistente = False
            motivos_inconsistencia.append(f"CST PIS: {set(csts_pis)}")

        # % PIS - deve ser unico
        if len(set(aliqs_pis)) > 1:
            consistente = False
            motivos_inconsistencia.append(f"PIS: {set(aliqs_pis)}")

        # CST COFINS - deve ser unico
        if len(set(csts_cofins)) > 1:
            consistente = False
            motivos_inconsistencia.append(f"CST COFINS: {set(csts_cofins)}")

        # % COFINS - deve ser unico
        if len(set(aliqs_cofins)) > 1:
            consistente = False
            motivos_inconsistencia.append(f"COFINS: {set(aliqs_cofins)}")

        if not consistente:
            logger.warning(f"Historico inconsistente: {', '.join(motivos_inconsistencia)}")

        # Montar dados consistentes (pega o mais frequente ou primeiro)
        dados = {
            'ncm': ncms[0] if ncms else None,
            'cfops': list(set(cfops)),  # CFOP pode ter varios
            'cst_icms': csts[0] if csts else None,
            'aliq_icms': aliqs_icms[0] if aliqs_icms else None,
            'reducao_bc_icms': reducoes_bc_icms[0] if reducoes_bc_icms else None,
            'aliq_icms_st': aliqs_icms_st[0] if aliqs_icms_st else None,
            'aliq_ipi': aliqs_ipi[0] if aliqs_ipi else None,
            # PIS
            'cst_pis': csts_pis[0] if csts_pis else None,
            'aliq_pis': aliqs_pis[0] if aliqs_pis else None,
            # COFINS
            'cst_cofins': csts_cofins[0] if csts_cofins else None,
            'aliq_cofins': aliqs_cofins[0] if aliqs_cofins else None
        }

        return consistente, dados

    def _criar_perfil_automatico(
        self,
        cod_produto: str,
        cnpj_fornecedor: str,
        cnpj_empresa_compradora: str,
        dados: Dict,
        dfe_ids: List[int],
        nome_produto: str = None,
        razao_fornecedor: str = None,
        nome_empresa: str = None
    ) -> PerfilFiscalProdutoFornecedor:
        """
        Cria perfil fiscal automaticamente a partir de historico consistente.

        Args:
            cod_produto: Codigo interno do produto (default_code)
            cnpj_fornecedor: CNPJ do fornecedor
            cnpj_empresa_compradora: CNPJ da empresa compradora (destinatario)
            dados: Dados fiscais consistentes do historico
            dfe_ids: IDs dos DFEs usados para criar o perfil
            nome_produto: Nome interno do produto (para exibicao)
            razao_fornecedor: Razao social do fornecedor (para exibicao)
            nome_empresa: Nome da empresa compradora (para exibicao)

        Returns:
            PerfilFiscalProdutoFornecedor criado
        """
        # Garantir que nome_empresa seja preenchido pelo mapeamento se não vier
        if not nome_empresa and cnpj_empresa_compradora:
            nome_empresa = obter_nome_empresa(cnpj_empresa_compradora)

        perfil = PerfilFiscalProdutoFornecedor(
            cnpj_empresa_compradora=cnpj_empresa_compradora,
            cod_produto=cod_produto,
            cnpj_fornecedor=cnpj_fornecedor,
            # Nomes para exibicao
            nome_empresa_compradora=nome_empresa,
            razao_fornecedor=razao_fornecedor,
            nome_produto=nome_produto,
            # Dados fiscais
            ncm_esperado=dados.get('ncm'),
            cfop_esperados=json.dumps(dados.get('cfops', [])),
            cst_icms_esperado=dados.get('cst_icms'),
            aliquota_icms_esperada=dados.get('aliq_icms') or Decimal('0'),
            reducao_bc_icms_esperada=dados.get('reducao_bc_icms') or Decimal('0'),
            aliquota_icms_st_esperada=dados.get('aliq_icms_st') or Decimal('0'),
            aliquota_ipi_esperada=dados.get('aliq_ipi') or Decimal('0'),
            # PIS
            cst_pis_esperado=dados.get('cst_pis'),
            aliquota_pis_esperada=dados.get('aliq_pis') or Decimal('0'),
            # COFINS
            cst_cofins_esperado=dados.get('cst_cofins'),
            aliquota_cofins_esperada=dados.get('aliq_cofins') or Decimal('0'),
            ultimas_nfs_ids=json.dumps(dfe_ids),
            criado_por='SISTEMA_AUTO_HISTORICO',
            ativo=True
        )

        db.session.add(perfil)
        db.session.commit()

        logger.info(
            f"Perfil fiscal criado automaticamente: id={perfil.id}, "
            f"produto={cod_produto}, fornecedor={cnpj_fornecedor}, "
            f"baseado em {len(dfe_ids)} NFs"
        )

        return perfil

    def _criar_registro_primeira_compra(
        self,
        odoo_dfe_id: int,
        linha: Dict,
        cnpj: str,
        razao: str,
        dados_nf: Dict = None
    ) -> Dict:
        """Cria registro de 1a compra para validacao manual"""

        cod_produto = str(linha.get('product_id', [None, ''])[0])
        nome_produto = linha.get('det_prod_xprod', '')
        dados_nf = dados_nf or {}

        # Verificar se ja existe registro pendente
        existente = CadastroPrimeiraCompra.query.filter_by(
            odoo_dfe_id=str(odoo_dfe_id),
            cod_produto=cod_produto,
            cnpj_fornecedor=cnpj,
            status='pendente'
        ).first()

        if existente:
            return {
                'id': existente.id,
                'cod_produto': cod_produto,
                'nome_produto': nome_produto,
                'status': 'ja_registrado'
            }

        # Criar novo registro
        registro = CadastroPrimeiraCompra(
            odoo_dfe_id=str(odoo_dfe_id),
            odoo_dfe_line_id=str(linha.get('id')),
            # Dados da NF
            numero_nf=dados_nf.get('numero_nf'),
            serie_nf=dados_nf.get('serie_nf'),
            chave_nfe=dados_nf.get('chave_nfe'),
            # Produto e fornecedor
            cod_produto=cod_produto,
            nome_produto=nome_produto,
            cnpj_fornecedor=cnpj,
            razao_fornecedor=razao,
            # Empresa compradora (destinatario da NF)
            cnpj_empresa_compradora=dados_nf.get('cnpj_empresa_compradora'),
            razao_empresa_compradora=dados_nf.get('razao_empresa_compradora'),
            # Localizacao do fornecedor
            uf_fornecedor=dados_nf.get('uf_fornecedor'),
            cidade_fornecedor=dados_nf.get('cidade_fornecedor'),
            # Regime tributario
            regime_tributario=dados_nf.get('regime_tributario'),
            # Quantidade e valores do produto
            quantidade=self._to_decimal(linha.get('det_prod_qcom')),
            unidade_medida=linha.get('det_prod_ucom'),
            valor_unitario=self._to_decimal(linha.get('det_prod_vuncom')),
            valor_total=self._to_decimal(linha.get('det_prod_vprod')),
            # Dados fiscais
            ncm=linha.get('det_prod_ncm'),
            cfop=linha.get('det_prod_cfop'),
            # ICMS
            aliquota_icms=self._to_decimal(linha.get('det_imposto_icms_picms')),
            reducao_bc_icms=self._to_decimal(linha.get('det_imposto_icms_predbc')),
            valor_icms=self._to_decimal(linha.get('det_imposto_icms_vicms')),
            bc_icms=self._to_decimal(linha.get('det_imposto_icms_vbc')),
            # ICMS ST
            aliquota_icms_st=self._calcular_aliq_icms_st(linha),
            valor_icms_st=self._to_decimal(linha.get('det_imposto_icms_vicmsst')),
            bc_icms_st=self._to_decimal(linha.get('det_imposto_icms_vbcst')),
            # IPI
            aliquota_ipi=self._to_decimal(linha.get('det_imposto_ipi_pipi')),
            valor_ipi=self._to_decimal(linha.get('det_imposto_ipi_vipi')),
            valor_tributos_aprox=None,  # Campo nao disponivel no Odoo
            # PIS
            cst_pis=linha.get('det_imposto_pis_cst'),
            aliquota_pis=self._to_decimal(linha.get('det_imposto_pis_ppis')),
            bc_pis=self._to_decimal(linha.get('det_imposto_pis_vbc')),
            valor_pis=self._to_decimal(linha.get('det_imposto_pis_vpis')),
            # COFINS
            cst_cofins=linha.get('det_imposto_cofins_cst'),
            aliquota_cofins=self._to_decimal(linha.get('det_imposto_cofins_pcofins')),
            bc_cofins=self._to_decimal(linha.get('det_imposto_cofins_vbc')),
            valor_cofins=self._to_decimal(linha.get('det_imposto_cofins_vcofins')),
            status='pendente'
        )

        db.session.add(registro)
        db.session.commit()

        logger.info(f"1a compra registrada: DFE={odoo_dfe_id}, produto={cod_produto}, fornecedor={cnpj}")

        return {
            'id': registro.id,
            'cod_produto': cod_produto,
            'nome_produto': nome_produto,
            'status': 'criado'
        }

    def _comparar_com_baseline(
        self,
        linha: Dict,
        perfil: PerfilFiscalProdutoFornecedor,
        odoo_dfe_id: int,
        razao: str,
        dados_nf: Dict = None
    ) -> List[Dict]:
        """Compara linha da NF com baseline do perfil fiscal"""
        divergencias = []
        dados_nf = dados_nf or {}

        cod_produto = str(linha.get('product_id', [None, ''])[0])
        nome_produto = linha.get('det_prod_xprod', '')

        # NCM
        ncm_nf = linha.get('det_prod_ncm', '')
        if ncm_nf and perfil.ncm_esperado and ncm_nf != perfil.ncm_esperado:
            div = self._criar_divergencia(
                odoo_dfe_id=odoo_dfe_id,
                linha=linha,
                perfil=perfil,
                campo='ncm',
                valor_esperado=perfil.ncm_esperado,
                valor_encontrado=ncm_nf,
                razao=razao
            )
            divergencias.append(div)

        # CFOP (pode ser lista)
        cfop_nf = linha.get('det_prod_cfop', '')
        if cfop_nf and perfil.cfop_esperados:
            cfops_validos = json.loads(perfil.cfop_esperados) if perfil.cfop_esperados else []
            if cfop_nf not in cfops_validos:
                div = self._criar_divergencia(
                    odoo_dfe_id=odoo_dfe_id,
                    linha=linha,
                    perfil=perfil,
                    campo='cfop',
                    valor_esperado=', '.join(cfops_validos),
                    valor_encontrado=cfop_nf,
                    razao=razao,
                    dados_nf=dados_nf
                )
                divergencias.append(div)

        # % ICMS
        aliq_icms_nf = self._to_decimal(linha.get('det_imposto_icms_picms'))
        if aliq_icms_nf is not None and perfil.aliquota_icms_esperada is not None:
            if aliq_icms_nf != perfil.aliquota_icms_esperada:
                div = self._criar_divergencia(
                    odoo_dfe_id=odoo_dfe_id,
                    linha=linha,
                    perfil=perfil,
                    campo='aliq_icms',
                    valor_esperado=str(perfil.aliquota_icms_esperada),
                    valor_encontrado=str(aliq_icms_nf),
                    razao=razao,
                    dados_nf=dados_nf
                )
                divergencias.append(div)

        # % Reducao BC ICMS
        reducao_bc_icms_nf = self._to_decimal(linha.get('det_imposto_icms_predbc'))
        if reducao_bc_icms_nf is not None and perfil.reducao_bc_icms_esperada is not None:
            if reducao_bc_icms_nf != perfil.reducao_bc_icms_esperada:
                div = self._criar_divergencia(
                    odoo_dfe_id=odoo_dfe_id,
                    linha=linha,
                    perfil=perfil,
                    campo='reducao_bc_icms',
                    valor_esperado=str(perfil.reducao_bc_icms_esperada),
                    valor_encontrado=str(reducao_bc_icms_nf),
                    razao=razao,
                    dados_nf=dados_nf
                )
                divergencias.append(div)

        # % ICMS ST (calculado a partir de vicmsst/vbcst)
        aliq_icms_st_nf = self._calcular_aliq_icms_st(linha)
        if aliq_icms_st_nf is not None and perfil.aliquota_icms_st_esperada is not None:
            if aliq_icms_st_nf != perfil.aliquota_icms_st_esperada:
                div = self._criar_divergencia(
                    odoo_dfe_id=odoo_dfe_id,
                    linha=linha,
                    perfil=perfil,
                    campo='aliq_icms_st',
                    valor_esperado=str(perfil.aliquota_icms_st_esperada),
                    valor_encontrado=str(aliq_icms_st_nf),
                    razao=razao,
                    dados_nf=dados_nf
                )
                divergencias.append(div)

        # % IPI
        aliq_ipi_nf = self._to_decimal(linha.get('det_imposto_ipi_pipi'))
        if aliq_ipi_nf is not None and perfil.aliquota_ipi_esperada is not None:
            if aliq_ipi_nf != perfil.aliquota_ipi_esperada:
                div = self._criar_divergencia(
                    odoo_dfe_id=odoo_dfe_id,
                    linha=linha,
                    perfil=perfil,
                    campo='aliq_ipi',
                    valor_esperado=str(perfil.aliquota_ipi_esperada),
                    valor_encontrado=str(aliq_ipi_nf),
                    razao=razao,
                    dados_nf=dados_nf
                )
                divergencias.append(div)

        # CST PIS
        cst_pis_nf = linha.get('det_imposto_pis_cst')
        if cst_pis_nf and perfil.cst_pis_esperado:
            if cst_pis_nf != perfil.cst_pis_esperado:
                div = self._criar_divergencia(
                    odoo_dfe_id=odoo_dfe_id,
                    linha=linha,
                    perfil=perfil,
                    campo='cst_pis',
                    valor_esperado=str(perfil.cst_pis_esperado),
                    valor_encontrado=str(cst_pis_nf),
                    razao=razao,
                    dados_nf=dados_nf
                )
                divergencias.append(div)

        # % PIS
        aliq_pis_nf = self._to_decimal(linha.get('det_imposto_pis_ppis'))
        if aliq_pis_nf is not None and perfil.aliquota_pis_esperada is not None:
            if aliq_pis_nf != perfil.aliquota_pis_esperada:
                div = self._criar_divergencia(
                    odoo_dfe_id=odoo_dfe_id,
                    linha=linha,
                    perfil=perfil,
                    campo='aliq_pis',
                    valor_esperado=str(perfil.aliquota_pis_esperada),
                    valor_encontrado=str(aliq_pis_nf),
                    razao=razao,
                    dados_nf=dados_nf
                )
                divergencias.append(div)

        # CST COFINS
        cst_cofins_nf = linha.get('det_imposto_cofins_cst')
        if cst_cofins_nf and perfil.cst_cofins_esperado:
            if cst_cofins_nf != perfil.cst_cofins_esperado:
                div = self._criar_divergencia(
                    odoo_dfe_id=odoo_dfe_id,
                    linha=linha,
                    perfil=perfil,
                    campo='cst_cofins',
                    valor_esperado=str(perfil.cst_cofins_esperado),
                    valor_encontrado=str(cst_cofins_nf),
                    razao=razao,
                    dados_nf=dados_nf
                )
                divergencias.append(div)

        # % COFINS
        aliq_cofins_nf = self._to_decimal(linha.get('det_imposto_cofins_pcofins'))
        if aliq_cofins_nf is not None and perfil.aliquota_cofins_esperada is not None:
            if aliq_cofins_nf != perfil.aliquota_cofins_esperada:
                div = self._criar_divergencia(
                    odoo_dfe_id=odoo_dfe_id,
                    linha=linha,
                    perfil=perfil,
                    campo='aliq_cofins',
                    valor_esperado=str(perfil.aliquota_cofins_esperada),
                    valor_encontrado=str(aliq_cofins_nf),
                    razao=razao,
                    dados_nf=dados_nf
                )
                divergencias.append(div)

        return divergencias

    def _criar_divergencia(
        self,
        odoo_dfe_id: int,
        linha: Dict,
        perfil: PerfilFiscalProdutoFornecedor,
        campo: str,
        valor_esperado: str,
        valor_encontrado: str,
        razao: str,
        dados_nf: Dict = None
    ) -> Dict:
        """Cria registro de divergencia fiscal"""
        dados_nf = dados_nf or {}

        config = self.CAMPOS_VALIDACAO.get(campo, {})
        label = config.get('label', campo)

        cod_produto = str(linha.get('product_id', [None, ''])[0])
        nome_produto = linha.get('det_prod_xprod', '')

        # Calcular diferenca percentual (se numerico)
        diferenca_pct = None
        try:
            esp = Decimal(str(valor_esperado))
            enc = Decimal(str(valor_encontrado))
            if esp != 0:
                diferenca_pct = ((enc - esp) / esp * 100).quantize(Decimal('0.01'))
        except (ValueError, TypeError, InvalidOperation):
            pass

        # Criar registro
        divergencia = DivergenciaFiscal(
            odoo_dfe_id=str(odoo_dfe_id),
            odoo_dfe_line_id=str(linha.get('id')),
            # Dados da NF
            numero_nf=dados_nf.get('numero_nf'),
            serie_nf=dados_nf.get('serie_nf'),
            chave_nfe=dados_nf.get('chave_nfe'),
            # Perfil e produto
            perfil_fiscal_id=perfil.id,
            cod_produto=cod_produto,
            nome_produto=nome_produto,
            cnpj_fornecedor=perfil.cnpj_fornecedor,
            razao_fornecedor=razao,
            # Empresa compradora (destinatario da NF)
            cnpj_empresa_compradora=dados_nf.get('cnpj_empresa_compradora'),
            razao_empresa_compradora=dados_nf.get('razao_empresa_compradora'),
            # Localizacao do fornecedor
            uf_fornecedor=dados_nf.get('uf_fornecedor'),
            cidade_fornecedor=dados_nf.get('cidade_fornecedor'),
            # Regime tributario
            regime_tributario=dados_nf.get('regime_tributario'),
            campo=campo,
            campo_label=label,
            valor_esperado=valor_esperado,
            valor_encontrado=valor_encontrado,
            diferenca_percentual=diferenca_pct,
            status='pendente'
        )

        db.session.add(divergencia)
        db.session.commit()

        logger.warning(
            f"Divergencia fiscal: DFE={odoo_dfe_id}, produto={cod_produto}, "
            f"campo={campo}, esperado={valor_esperado}, encontrado={valor_encontrado}"
        )

        return {
            'id': divergencia.id,
            'campo': campo,
            'label': label,
            'esperado': valor_esperado,
            'encontrado': valor_encontrado,
            'diferenca_pct': str(diferenca_pct) if diferenca_pct else None
        }

    def _to_decimal(self, valor) -> Optional[Decimal]:
        """Converte valor para Decimal"""
        if valor is None or valor == '':
            return None
        try:
            return Decimal(str(valor))
        except Exception:
            return None

    def _calcular_aliq_icms_st(self, linha: Dict) -> Optional[Decimal]:
        """
        Calcula aliquota de ICMS ST a partir dos valores.

        Formula: aliq_st = (vicmsst / vbcst) * 100

        O campo det_imposto_icms_picmsst nao existe no Odoo,
        entao calculamos a partir dos valores.

        Retorna None quando ICMS ST nao se aplica (sem base ou sem valor).
        """
        vicmsst = self._to_decimal(linha.get('det_imposto_icms_vicmsst'))
        vbcst = self._to_decimal(linha.get('det_imposto_icms_vbcst'))

        if vicmsst is None or vbcst is None or vbcst == 0:
            return None  # ICMS ST nao se aplica

        try:
            aliq = (vicmsst / vbcst) * 100
            return aliq.quantize(Decimal('0.01'))
        except Exception:
            return None

    # =========================================================================
    # METODOS PARA RESOLUCAO DE DIVERGENCIAS
    # =========================================================================

    def aprovar_divergencia(
        self,
        divergencia_id: int,
        atualizar_baseline: bool,
        justificativa: str,
        usuario: str
    ) -> Dict:
        """
        Aprova uma divergencia fiscal.

        Args:
            divergencia_id: ID da divergencia
            atualizar_baseline: Se True, atualiza o perfil fiscal
            justificativa: Motivo da aprovacao
            usuario: Nome do usuario

        Returns:
            {'sucesso': bool, 'mensagem': str}
        """
        divergencia = db.session.get(DivergenciaFiscal,divergencia_id) if divergencia_id else None
        if not divergencia:
            return {'sucesso': False, 'mensagem': 'Divergencia nao encontrada'}

        if divergencia.status != 'pendente':
            return {'sucesso': False, 'mensagem': f'Divergencia ja resolvida: {divergencia.status}'}

        # Atualizar divergencia
        divergencia.status = 'aprovada'
        divergencia.resolucao = 'aprovar_atualizar' if atualizar_baseline else 'aprovar_manter'
        divergencia.atualizar_baseline = atualizar_baseline
        divergencia.justificativa = justificativa
        divergencia.resolvido_por = usuario
        divergencia.resolvido_em = datetime.utcnow()

        # Se atualizar baseline
        if atualizar_baseline and divergencia.perfil_fiscal_id:
            perfil = db.session.get(PerfilFiscalProdutoFornecedor,divergencia.perfil_fiscal_id) if divergencia.perfil_fiscal_id else None
            if perfil:
                self._atualizar_perfil_campo(
                    perfil=perfil,
                    campo=divergencia.campo,
                    novo_valor=divergencia.valor_encontrado,
                    usuario=usuario
                )

        db.session.commit()

        logger.info(f"Divergencia {divergencia_id} aprovada por {usuario}, atualizar_baseline={atualizar_baseline}")

        return {'sucesso': True, 'mensagem': 'Divergencia aprovada com sucesso'}

    def rejeitar_divergencia(
        self,
        divergencia_id: int,
        justificativa: str,
        usuario: str
    ) -> Dict:
        """Rejeita uma divergencia fiscal (NF sera rejeitada)"""
        divergencia = db.session.get(DivergenciaFiscal,divergencia_id) if divergencia_id else None
        if not divergencia:
            return {'sucesso': False, 'mensagem': 'Divergencia nao encontrada'}

        if divergencia.status != 'pendente':
            return {'sucesso': False, 'mensagem': f'Divergencia ja resolvida: {divergencia.status}'}

        divergencia.status = 'rejeitada'
        divergencia.resolucao = 'rejeitar'
        divergencia.justificativa = justificativa
        divergencia.resolvido_por = usuario
        divergencia.resolvido_em = datetime.utcnow()

        db.session.commit()

        logger.info(f"Divergencia {divergencia_id} rejeitada por {usuario}")

        return {'sucesso': True, 'mensagem': 'Divergencia rejeitada'}

    def _atualizar_perfil_campo(
        self,
        perfil: PerfilFiscalProdutoFornecedor,
        campo: str,
        novo_valor: str,
        usuario: str
    ):
        """Atualiza campo especifico do perfil fiscal"""
        if campo == 'ncm':
            perfil.ncm_esperado = novo_valor
        elif campo == 'cfop':
            # Adicionar ao lista de CFOPs
            cfops = json.loads(perfil.cfop_esperados) if perfil.cfop_esperados else []
            if novo_valor not in cfops:
                cfops.append(novo_valor)
                perfil.cfop_esperados = json.dumps(cfops)
        elif campo == 'aliq_icms':
            perfil.aliquota_icms_esperada = Decimal(novo_valor)
        elif campo == 'aliq_icms_st':
            perfil.aliquota_icms_st_esperada = Decimal(novo_valor)
        elif campo == 'aliq_ipi':
            perfil.aliquota_ipi_esperada = Decimal(novo_valor)

        perfil.atualizado_por = usuario
        perfil.atualizado_em = datetime.utcnow()

        logger.info(f"Perfil {perfil.id} atualizado: {campo}={novo_valor}")

    # =========================================================================
    # METODOS PARA VALIDACAO DE 1a COMPRA
    # =========================================================================

    def validar_primeira_compra(
        self,
        cadastro_id: int,
        usuario: str,
        observacao: Optional[str] = None
    ) -> Dict:
        """
        Valida registro de 1a compra e cria perfil fiscal.

        Args:
            cadastro_id: ID do cadastro de 1a compra
            usuario: Nome do usuario
            observacao: Observacao opcional

        Returns:
            {'sucesso': bool, 'mensagem': str, 'perfil_id': int}
        """
        cadastro = db.session.get(CadastroPrimeiraCompra,cadastro_id) if cadastro_id else None
        if not cadastro:
            return {'sucesso': False, 'mensagem': 'Cadastro nao encontrado'}

        if cadastro.status != 'pendente':
            return {'sucesso': False, 'mensagem': f'Cadastro ja processado: {cadastro.status}'}

        # Criar perfil fiscal com TODOS os campos disponíveis
        # Garantir que nome_empresa seja preenchido pelo mapeamento se não vier
        nome_empresa = cadastro.razao_empresa_compradora
        if not nome_empresa and cadastro.cnpj_empresa_compradora:
            nome_empresa = obter_nome_empresa(cadastro.cnpj_empresa_compradora)

        perfil = PerfilFiscalProdutoFornecedor(
            cod_produto=cadastro.cod_produto,
            cnpj_fornecedor=cadastro.cnpj_fornecedor,
            cnpj_empresa_compradora=cadastro.cnpj_empresa_compradora,
            # Nomes para exibição
            nome_empresa_compradora=nome_empresa,
            razao_fornecedor=cadastro.razao_fornecedor,
            nome_produto=cadastro.nome_produto,
            # Dados fiscais completos
            ncm_esperado=cadastro.ncm,
            cfop_esperados=json.dumps([cadastro.cfop]) if cadastro.cfop else None,
            cst_icms_esperado=cadastro.cst_icms,
            aliquota_icms_esperada=cadastro.aliquota_icms or Decimal('0'),
            reducao_bc_icms_esperada=cadastro.reducao_bc_icms or Decimal('0'),
            aliquota_icms_st_esperada=cadastro.aliquota_icms_st or Decimal('0'),
            aliquota_ipi_esperada=cadastro.aliquota_ipi or Decimal('0'),
            # PIS
            cst_pis_esperado=cadastro.cst_pis,
            aliquota_pis_esperada=cadastro.aliquota_pis or Decimal('0'),
            # COFINS
            cst_cofins_esperado=cadastro.cst_cofins,
            aliquota_cofins_esperada=cadastro.aliquota_cofins or Decimal('0'),
            ultimas_nfs_ids=json.dumps([cadastro.odoo_dfe_id]),
            criado_por=usuario,
            ativo=True
        )

        db.session.add(perfil)

        # Atualizar cadastro
        cadastro.status = 'validado'
        cadastro.validado_por = usuario
        cadastro.validado_em = datetime.utcnow()
        cadastro.observacao = observacao

        db.session.commit()

        logger.info(
            f"1a compra validada: cadastro={cadastro_id}, "
            f"perfil={perfil.id}, produto={cadastro.cod_produto}"
        )

        return {
            'sucesso': True,
            'mensagem': 'Perfil fiscal criado com sucesso',
            'perfil_id': perfil.id
        }

    def rejeitar_primeira_compra(
        self,
        cadastro_id: int,
        usuario: str,
        observacao: str
    ) -> Dict:
        """Rejeita registro de 1a compra (NF sera rejeitada)"""
        cadastro = db.session.get(CadastroPrimeiraCompra,cadastro_id) if cadastro_id else None
        if not cadastro:
            return {'sucesso': False, 'mensagem': 'Cadastro nao encontrado'}

        if cadastro.status != 'pendente':
            return {'sucesso': False, 'mensagem': f'Cadastro ja processado: {cadastro.status}'}

        cadastro.status = 'rejeitado'
        cadastro.validado_por = usuario
        cadastro.validado_em = datetime.utcnow()
        cadastro.observacao = observacao

        db.session.commit()

        logger.info(f"1a compra rejeitada: cadastro={cadastro_id}")

        return {'sucesso': True, 'mensagem': 'Cadastro rejeitado'}

    # =========================================================================
    # VALIDACAO IBS/CBS (Reforma Tributaria 2026)
    # =========================================================================

    def validar_ibscbs_nfe(
        self,
        odoo_dfe_id: int,
        linhas: List[Dict] = None
    ) -> Dict:
        """
        Valida IBS/CBS nas linhas de uma NF-e.

        Regra:
        - Se emitente for Regime Normal (CRT=3)
        - E o NCM (4 primeiros digitos) estiver na tabela de NCMs validados
        - Entao DEVE destacar IBS/CBS

        Args:
            odoo_dfe_id: ID do DFE no Odoo
            linhas: Linhas ja carregadas (opcional, busca se nao fornecido)

        Returns:
            {
                'validado': bool,
                'pendencias_criadas': int,
                'ncm_nao_cadastrados': List[str],
                'detalhes': str
            }
        """
        from app.recebimento.models import NcmIbsCbsValidado, PendenciaFiscalIbsCbs
        from app.recebimento.services.validacao_ibscbs_service import validacao_ibscbs_service

        resultado = {
            'validado': True,
            'pendencias_criadas': 0,
            'ncm_nao_cadastrados': [],
            'detalhes': ''
        }

        try:
            odoo = self._get_odoo()

            # Buscar DFE
            dfe = self._buscar_dfe(odoo_dfe_id)
            if not dfe:
                resultado['detalhes'] = f'DFE {odoo_dfe_id} nao encontrado'
                return resultado

            # Verificar regime tributario
            crt = dfe.get('nfe_infnfe_emit_crt')
            regime = str(crt) if crt and crt is not False else None

            # Se nao for Regime Normal, nao valida
            if regime not in ['3']:  # Apenas Regime Normal
                resultado['detalhes'] = f'Regime tributario {regime} - IBS/CBS nao obrigatorio'
                return resultado

            # Extrair dados do emitente
            cnpj = self._extrair_cnpj(dfe)
            razao = dfe.get('nfe_infnfe_emit_xnome', '')
            chave_nfe = dfe.get('protnfe_infnfe_chnfe')
            numero_nf = dfe.get('nfe_infnfe_ide_nnf')
            serie_nf = dfe.get('nfe_infnfe_ide_serie')
            data_emissao_str = dfe.get('nfe_infnfe_ide_dhemi')

            # Buscar linhas se nao fornecidas
            if linhas is None:
                linhas = self._buscar_linhas_dfe_ibscbs(odoo_dfe_id)

            if not linhas:
                resultado['detalhes'] = 'Sem linhas de produto'
                return resultado

            # Para cada linha, validar IBS/CBS com validacao COMPLETA de campos
            for linha in linhas:
                ncm = linha.get('det_prod_ncm', '')
                ncm_prefixo = ncm[:4] if ncm and len(ncm) >= 4 else None

                if not ncm_prefixo:
                    continue

                # Verificar se NCM esta na tabela de validados
                ncm_validado = db.session.query(NcmIbsCbsValidado).filter_by(
                    ncm_prefixo=ncm_prefixo,
                    ativo=True
                ).first()

                if not ncm_validado:
                    # NCM nao cadastrado - sugerir para cadastro
                    if ncm_prefixo not in resultado['ncm_nao_cadastrados']:
                        resultado['ncm_nao_cadastrados'].append(ncm_prefixo)
                    continue

                # NCM esta na tabela - montar estrutura com TODOS os campos para validacao
                ibscbs_valores = {
                    # CST e ClassTrib
                    'cst': linha.get('det_imposto_ibscbs_cst'),
                    'class_trib': linha.get('det_imposto_ibscbs_classtrib'),
                    # Base de Calculo
                    'base_calculo': self._to_decimal(linha.get('det_imposto_ibscbs_vbc')),
                    # IBS UF com reducao e aliquota efetiva
                    'ibs_uf_aliquota': self._to_decimal(linha.get('det_imposto_ibscbs_ibs_uf_aliq')),
                    'ibs_uf_reducao': self._to_decimal(linha.get('det_imposto_ibscbs_ibs_uf_redaliq')),
                    'ibs_uf_aliq_efetiva': self._to_decimal(linha.get('det_imposto_ibscbs_ibs_uf_aliqefet')),
                    'ibs_uf_valor': self._to_decimal(linha.get('det_imposto_ibscbs_ibs_uf_valor')),
                    # IBS Municipio com reducao e aliquota efetiva
                    'ibs_mun_aliquota': self._to_decimal(linha.get('det_imposto_ibscbs_ibs_mun_aliq')),
                    'ibs_mun_reducao': self._to_decimal(linha.get('det_imposto_ibscbs_ibs_mun_redaliq')),
                    'ibs_mun_aliq_efetiva': self._to_decimal(linha.get('det_imposto_ibscbs_ibs_mun_aliqefet')),
                    'ibs_mun_valor': self._to_decimal(linha.get('det_imposto_ibscbs_ibs_mun_valor')),
                    # IBS Total
                    'ibs_total': self._to_decimal(linha.get('det_imposto_ibscbs_ibs_valor')),
                    # CBS com reducao e aliquota efetiva
                    'cbs_aliquota': self._to_decimal(linha.get('det_imposto_ibscbs_cbs_aliq')),
                    'cbs_reducao': self._to_decimal(linha.get('det_imposto_ibscbs_cbs_redaliq')),
                    'cbs_aliq_efetiva': self._to_decimal(linha.get('det_imposto_ibscbs_cbs_aliqefet')),
                    'cbs_valor': self._to_decimal(linha.get('det_imposto_ibscbs_cbs_valor'))
                }

                valor_produto = self._to_decimal(linha.get('det_prod_vprod')) or 0
                dados_documento = {
                    'chave_acesso': chave_nfe,
                    'numero_documento': numero_nf,
                    'serie': serie_nf,
                    'data_emissao': data_emissao_str
                }

                # Usar validacao completa de campos do service
                ok, motivo, divergencias = validacao_ibscbs_service.validar_nfe_linha(
                    ncm=ncm,
                    ibscbs_valores=ibscbs_valores,
                    valor_produto=valor_produto,
                    cnpj_fornecedor=cnpj,
                    dados_documento=dados_documento
                )

                if not ok:
                    resultado['validado'] = False

                    # Verificar se ja existe pendencia para esta chave
                    pendencia_existente = db.session.query(PendenciaFiscalIbsCbs).filter_by(
                        chave_acesso=chave_nfe
                    ).first()

                    if not pendencia_existente:
                        detalhes = "; ".join(divergencias) if divergencias else 'IBS/CBS com valores divergentes'

                        pendencia = PendenciaFiscalIbsCbs(
                            tipo_documento='NF-e',
                            chave_acesso=chave_nfe,
                            numero_documento=numero_nf,
                            serie=serie_nf,
                            data_emissao=self._parse_date(data_emissao_str) if data_emissao_str else None,
                            odoo_dfe_id=odoo_dfe_id,
                            cnpj_fornecedor=cnpj,
                            razao_fornecedor=razao,
                            regime_tributario=regime,
                            regime_tributario_descricao=PendenciaFiscalIbsCbs.get_regime_descricao(regime),
                            ncm=ncm,
                            ncm_prefixo=ncm_prefixo,
                            valor_total=valor_produto,
                            valor_base_calculo=ibscbs_valores.get('base_calculo'),
                            # Valores IBS/CBS encontrados
                            ibscbs_cst=ibscbs_valores.get('cst'),
                            ibscbs_class_trib=ibscbs_valores.get('class_trib'),
                            ibscbs_base=ibscbs_valores.get('base_calculo'),
                            ibs_uf_aliq=ibscbs_valores.get('ibs_uf_aliquota'),
                            ibs_uf_valor=ibscbs_valores.get('ibs_uf_valor'),
                            ibs_mun_aliq=ibscbs_valores.get('ibs_mun_aliquota'),
                            ibs_mun_valor=ibscbs_valores.get('ibs_mun_valor'),
                            ibs_total=ibscbs_valores.get('ibs_total'),
                            cbs_aliq=ibscbs_valores.get('cbs_aliquota'),
                            cbs_valor=ibscbs_valores.get('cbs_valor'),
                            motivo_pendencia=motivo or 'aliquota_divergente',
                            detalhes_pendencia=detalhes,
                            status='pendente',
                            criado_por='SISTEMA'
                        )

                        db.session.add(pendencia)
                        db.session.commit()
                        resultado['pendencias_criadas'] += 1

                        logger.warning(
                            f"Pendencia IBS/CBS criada: NF-e {numero_nf}, NCM {ncm}, fornecedor {cnpj}"
                        )
                        logger.warning(f"   Divergencias: {detalhes}")

            if resultado['ncm_nao_cadastrados']:
                resultado['detalhes'] = f"NCMs nao cadastrados para validacao: {', '.join(resultado['ncm_nao_cadastrados'])}"

        except Exception as e:
            logger.error(f"Erro ao validar IBS/CBS da NF-e {odoo_dfe_id}: {e}")
            resultado['detalhes'] = f'Erro: {str(e)}'

        return resultado

    def _buscar_linhas_dfe_ibscbs(self, odoo_dfe_id: int) -> List[Dict]:
        """Busca linhas do DFE com campos IBS/CBS completos (incluindo reducao e aliquota efetiva)"""
        odoo = self._get_odoo()

        campos = [
            'id', 'dfe_id', 'product_id',
            'det_prod_xprod', 'det_prod_ncm', 'det_prod_cfop',
            'det_prod_vprod',
            # Campos IBS/CBS (dependem do localizador brasileiro suportar)
            'det_imposto_ibscbs_cst',
            'det_imposto_ibscbs_classtrib',
            'det_imposto_ibscbs_vbc',
            # IBS UF
            'det_imposto_ibscbs_ibs_uf_aliq',
            'det_imposto_ibscbs_ibs_uf_redaliq',
            'det_imposto_ibscbs_ibs_uf_aliqefet',
            'det_imposto_ibscbs_ibs_uf_valor',
            # IBS Municipio
            'det_imposto_ibscbs_ibs_mun_aliq',
            'det_imposto_ibscbs_ibs_mun_redaliq',
            'det_imposto_ibscbs_ibs_mun_aliqefet',
            'det_imposto_ibscbs_ibs_mun_valor',
            # IBS Total
            'det_imposto_ibscbs_ibs_valor',
            # CBS
            'det_imposto_ibscbs_cbs_aliq',
            'det_imposto_ibscbs_cbs_redaliq',
            'det_imposto_ibscbs_cbs_aliqefet',
            'det_imposto_ibscbs_cbs_valor'
        ]

        try:
            return odoo.search_read(
                'l10n_br_ciel_it_account.dfe.line',
                [['dfe_id', '=', odoo_dfe_id]],
                fields=campos
            )
        except Exception as e:
            # Se campos IBS/CBS nao existirem no Odoo, usar campos basicos
            logger.debug(f"Campos IBS/CBS nao disponiveis no Odoo: {e}")
            return self._buscar_linhas_dfe(odoo_dfe_id)

    def _parse_date(self, date_str):
        """Converte string de data para date object"""
        if not date_str:
            return None
        try:
            if isinstance(date_str, str):
                return datetime.strptime(date_str.split()[0], '%Y-%m-%d').date()
            return date_str
        except Exception:
            return None
