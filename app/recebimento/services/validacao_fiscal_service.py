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

            # 3.1. Extrair dados da NF
            crt = dfe.get('nfe_infnfe_emit_crt')
            dados_nf = {
                'numero_nf': dfe.get('nfe_infnfe_ide_nnf'),
                'serie_nf': dfe.get('nfe_infnfe_ide_serie'),
                'chave_nfe': dfe.get('protnfe_infnfe_chnfe'),
                'uf_fornecedor': dfe.get('nfe_infnfe_emit_uf'),
                'cidade_fornecedor': None,  # Sera buscado do partner
                'regime_tributario': str(crt) if crt and crt is not False else None
            }

            # 3.2. Buscar cidade do fornecedor (do partner_id)
            partner_id = dfe.get('partner_id')
            if partner_id and isinstance(partner_id, (list, tuple)) and len(partner_id) > 0:
                partner_dados = odoo.search_read(
                    'res.partner',
                    [['id', '=', partner_id[0]]],
                    fields=['city', 'state_id'],
                    limit=1
                )
                if partner_dados:
                    dados_nf['cidade_fornecedor'] = partner_dados[0].get('city')
                    # state_id retorna [id, nome_estado]
                    state = partner_dados[0].get('state_id')
                    if state and isinstance(state, (list, tuple)) and not dados_nf['uf_fornecedor']:
                        # Se nao veio do DFE, pega do partner
                        dados_nf['uf_fornecedor'] = state[1][:2] if len(state) > 1 else None

            # 4. Validar cada linha
            for linha in linhas:
                cod_produto = str(linha.get('product_id', [None, ''])[0]) if linha.get('product_id') else None
                nome_produto = linha.get('det_prod_xprod', '')

                if not cod_produto:
                    logger.warning(f"Linha {linha.get('id')} sem product_id, pulando...")
                    continue

                # Buscar perfil fiscal (baseline)
                perfil = PerfilFiscalProdutoFornecedor.query.filter_by(
                    cod_produto=cod_produto,
                    cnpj_fornecedor=cnpj,
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
                        dados_nf=dados_nf
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
        # Limpar formatacao
        return ''.join(c for c in cnpj if c.isdigit())

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
        dados_nf: Dict = None
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
                dados=dados_consistentes,
                dfe_ids=[h['dfe_id'] for h in historico]
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

        Retorna lista de dicts com dados fiscais das ultimas N NFs.
        """
        odoo = self._get_odoo()

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
                    ['product_id', '=', int(cod_produto)]
                ],
                fields=[
                    'id', 'det_prod_ncm', 'det_prod_cfop',
                    'det_imposto_icms_picms', 'det_imposto_icms_vbcst',
                    'det_imposto_icms_vicmsst',  # Para calcular aliq ST
                    'det_imposto_ipi_pipi', 'det_imposto_icms_cst',
                    # PIS
                    'det_imposto_pis_cst', 'det_imposto_pis_ppis',
                    # COFINS
                    'det_imposto_cofins_cst', 'det_imposto_cofins_pcofins'
                ],
                limit=1
            )

            if linhas:
                linha = linhas[0]
                # Calcular aliquota ICMS ST = vicmsst / vbcst * 100
                aliq_icms_st = self._calcular_aliq_icms_st(linha)
                historico.append({
                    'dfe_id': dfe['id'],
                    'dfe_name': dfe['name'],
                    'data': dfe.get('nfe_infnfe_ide_dhemi'),
                    'ncm': linha.get('det_prod_ncm'),
                    'cfop': linha.get('det_prod_cfop'),
                    'cst_icms': linha.get('det_imposto_icms_cst'),
                    'aliq_icms': self._to_decimal(linha.get('det_imposto_icms_picms')),
                    'aliq_icms_st': aliq_icms_st,
                    'aliq_ipi': self._to_decimal(linha.get('det_imposto_ipi_pipi')),
                    # PIS
                    'cst_pis': linha.get('det_imposto_pis_cst'),
                    'aliq_pis': self._to_decimal(linha.get('det_imposto_pis_ppis')),
                    # COFINS
                    'cst_cofins': linha.get('det_imposto_cofins_cst'),
                    'aliq_cofins': self._to_decimal(linha.get('det_imposto_cofins_pcofins'))
                })

        logger.debug(
            f"Historico Odoo: produto={cod_produto}, fornecedor={cnpj_fornecedor}, "
            f"encontrados={len(historico)} registros"
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
        dados: Dict,
        dfe_ids: List[int]
    ) -> PerfilFiscalProdutoFornecedor:
        """
        Cria perfil fiscal automaticamente a partir de historico consistente.

        Args:
            cod_produto: Codigo do produto
            cnpj_fornecedor: CNPJ do fornecedor
            dados: Dados fiscais consistentes do historico
            dfe_ids: IDs dos DFEs usados para criar o perfil

        Returns:
            PerfilFiscalProdutoFornecedor criado
        """
        perfil = PerfilFiscalProdutoFornecedor(
            cod_produto=cod_produto,
            cnpj_fornecedor=cnpj_fornecedor,
            ncm_esperado=dados.get('ncm'),
            cfop_esperados=json.dumps(dados.get('cfops', [])),
            cst_icms_esperado=dados.get('cst_icms'),
            aliquota_icms_esperada=dados.get('aliq_icms'),
            aliquota_icms_st_esperada=dados.get('aliq_icms_st'),
            aliquota_ipi_esperada=dados.get('aliq_ipi'),
            # PIS
            cst_pis_esperado=dados.get('cst_pis'),
            aliquota_pis_esperada=dados.get('aliq_pis'),
            # COFINS
            cst_cofins_esperado=dados.get('cst_cofins'),
            aliquota_cofins_esperada=dados.get('aliq_cofins'),
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
        """
        vicmsst = self._to_decimal(linha.get('det_imposto_icms_vicmsst'))
        vbcst = self._to_decimal(linha.get('det_imposto_icms_vbcst'))

        if vicmsst is None or vbcst is None or vbcst == 0:
            return Decimal('0')

        try:
            aliq = (vicmsst / vbcst) * 100
            return aliq.quantize(Decimal('0.01'))
        except Exception:
            return Decimal('0')

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
        divergencia = DivergenciaFiscal.query.get(divergencia_id)
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
            perfil = PerfilFiscalProdutoFornecedor.query.get(divergencia.perfil_fiscal_id)
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
        divergencia = DivergenciaFiscal.query.get(divergencia_id)
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
        cadastro = CadastroPrimeiraCompra.query.get(cadastro_id)
        if not cadastro:
            return {'sucesso': False, 'mensagem': 'Cadastro nao encontrado'}

        if cadastro.status != 'pendente':
            return {'sucesso': False, 'mensagem': f'Cadastro ja processado: {cadastro.status}'}

        # Criar perfil fiscal
        perfil = PerfilFiscalProdutoFornecedor(
            cod_produto=cadastro.cod_produto,
            cnpj_fornecedor=cadastro.cnpj_fornecedor,
            ncm_esperado=cadastro.ncm,
            cfop_esperados=json.dumps([cadastro.cfop]) if cadastro.cfop else None,
            aliquota_icms_esperada=cadastro.aliquota_icms,
            aliquota_icms_st_esperada=cadastro.aliquota_icms_st,
            aliquota_ipi_esperada=cadastro.aliquota_ipi,
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
        cadastro = CadastroPrimeiraCompra.query.get(cadastro_id)
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
