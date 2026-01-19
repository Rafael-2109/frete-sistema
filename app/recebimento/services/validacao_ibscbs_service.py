"""
Servico de Validacao IBS/CBS (Reforma Tributaria 2026)
======================================================

Valida se fornecedores nao optantes do Simples Nacional
estao destacando corretamente IBS/CBS nos documentos fiscais.

REGRA FUNDAMENTAL DA BASE DE CALCULO IBS/CBS:
=============================================
A base de calculo do IBS/CBS e o valor do documento MENOS os impostos
que estao sendo substituidos (ICMS, PIS, COFINS).

Formula: Base IBS/CBS = Valor Total - ICMS - PIS - COFINS

Os valores de ICMS, PIS e COFINS sao extraidos do proprio XML do documento.

REGRAS DE VALIDACAO:

CTe (Aliquotas FIXAS):
- CST: 000
- cClassTrib: 000001
- vBC: valor_total - ICMS - PIS - COFINS
- pIBSUF: 0.10%
- pIBSMun: 0.00%
- pCBS: 0.90%
- SEM reducao de aliquota

NF-e (Aliquotas por NCM - 4 primeiros digitos):
- CST: cadastrado por NCM
- cClassTrib: cadastrado por NCM
- vBC: valor_produto - ICMS - PIS - COFINS (da linha)
- pIBSUF: cadastrado por NCM
- pIBSMun: cadastrado por NCM
- pCBS: cadastrado por NCM
- pRedAliq: reducao cadastrada por NCM (aplicada sobre base ja reduzida)
- pAliqEfet: calculada (aliq * (1 - reducao%))

Regime Tributario (CRT):
- 1 = Simples Nacional (NAO destaca IBS/CBS)
- 2 = Simples Nacional - Excesso Sublimite (verifica caso a caso)
- 3 = Regime Normal (DEVE destacar IBS/CBS)

Autor: Sistema de Fretes
Data: 2026-01-14 (atualizado 2026-01-19 - correcao base IBS/CBS)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from decimal import Decimal, ROUND_HALF_UP

from app import db
from app.recebimento.models import PendenciaFiscalIbsCbs, NcmIbsCbsValidado
from app.fretes.models import ConhecimentoTransporte
from app.odoo.utils.cte_xml_parser import CTeXMLParser
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES DE ALIQUOTAS PADRAO PARA CTe
# =============================================================================

class AliquotasCTe:
    """Aliquotas padrao para CTe (FIXAS - sem reducao)"""
    CST = '000'
    CLASS_TRIB = '000001'
    ALIQ_IBS_UF = Decimal('0.10')      # 0.10%
    ALIQ_IBS_MUN = Decimal('0.00')     # 0.00%
    ALIQ_CBS = Decimal('0.90')         # 0.90%

    # CTe nao tem reducao
    REDUCAO = Decimal('0.00')


# Tolerancia para comparacao de valores calculados (centavos)
TOLERANCIA_VALOR = Decimal('0.02')

# Tolerancia para comparacao de aliquotas (%)
TOLERANCIA_ALIQUOTA = Decimal('0.01')


class ValidacaoIbsCbsService:
    """
    Service para validacao de IBS/CBS em CTe e NF-e
    """

    # Regimes que DEVEM destacar IBS/CBS
    REGIMES_OBRIGADOS = ['3']  # Regime Normal

    # Regimes que podem ou nao destacar (analise caso a caso)
    REGIMES_ANALISE = ['2']  # Simples excesso sublimite

    # Regimes isentos
    REGIMES_ISENTOS = ['1']  # Simples Nacional

    def __init__(self):
        self.odoo = None

    def _get_odoo(self):
        """Obtem conexao com Odoo (lazy loading)"""
        if self.odoo is None:
            self.odoo = get_odoo_connection()
            if not self.odoo.authenticate():
                logger.error("Falha na autenticacao com Odoo")
                self.odoo = None
        return self.odoo

    def buscar_regime_tributario_odoo(self, cnpj: str) -> Optional[Dict]:
        """
        Busca o regime tributario do fornecedor no Odoo.

        Args:
            cnpj: CNPJ do fornecedor (com ou sem formatacao)

        Returns:
            Dict com regime_tributario e descricao ou None
        """
        odoo = self._get_odoo()
        if not odoo:
            logger.warning(f"Nao foi possivel conectar ao Odoo para buscar regime de {cnpj}")
            return None

        # Limpar CNPJ
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj or ''))
        if len(cnpj_limpo) != 14:
            logger.warning(f"CNPJ invalido: {cnpj}")
            return None

        # Formatar CNPJ para busca (XX.XXX.XXX/XXXX-XX)
        cnpj_formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"

        try:
            # Buscar no res.partner
            partners = odoo.search_read(
                'res.partner',
                [['l10n_br_cnpj', '=', cnpj_formatado]],
                ['id', 'name', 'l10n_br_cnpj', 'l10n_br_regime_tributario']
            )

            if not partners:
                # Tentar buscar sem formatacao
                partners = odoo.search_read(
                    'res.partner',
                    [['l10n_br_cnpj', 'ilike', cnpj_limpo]],
                    ['id', 'name', 'l10n_br_cnpj', 'l10n_br_regime_tributario']
                )

            if partners:
                partner = partners[0]
                regime = partner.get('l10n_br_regime_tributario')

                # O campo pode ser uma tupla (id, name) ou string
                if isinstance(regime, (list, tuple)):
                    regime_codigo = str(regime[0]) if regime else None
                else:
                    regime_codigo = str(regime) if regime else None

                return {
                    'cnpj': cnpj_formatado,
                    'nome': partner.get('name'),
                    'regime_tributario': regime_codigo,
                    'regime_descricao': PendenciaFiscalIbsCbs.get_regime_descricao(regime_codigo)
                }

            logger.warning(f"Fornecedor nao encontrado no Odoo: {cnpj_formatado}")
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar regime tributario no Odoo: {e}")
            return None

    # =========================================================================
    # VALIDACAO DE CTe
    # =========================================================================

    def validar_cte(
        self,
        cte: ConhecimentoTransporte,
        xml_content: Optional[str] = None
    ) -> Tuple[bool, Optional[PendenciaFiscalIbsCbs], str]:
        """
        Valida IBS/CBS de um CTe com aliquotas FIXAS.

        Campos validados:
        - CST: deve ser 000
        - cClassTrib: deve ser 000001
        - vBC: deve ser igual ao valor total do CTe
        - pIBSUF: deve ser 0.10%
        - vIBSUF: deve ser vBC * 0.10%
        - pIBSMun: deve ser 0.00%
        - vIBSMun: deve ser vBC * 0.00%
        - vIBS: deve ser vIBSUF + vIBSMun
        - pCBS: deve ser 0.90%
        - vCBS: deve ser vBC * 0.90%

        Args:
            cte: Objeto ConhecimentoTransporte
            xml_content: Conteudo XML (opcional, busca do S3 se nao fornecido)

        Returns:
            Tuple[bool, Optional[PendenciaFiscalIbsCbs], str]:
                - bool: True se validacao OK, False se gerou pendencia
                - PendenciaFiscalIbsCbs: Pendencia criada (se houver)
                - str: Mensagem descritiva
        """
        logger.info(f"Validando IBS/CBS do CTe {cte.numero_cte}")

        # Verificar se ja existe pendencia para este CTe
        pendencia_existente = PendenciaFiscalIbsCbs.query.filter_by(
            chave_acesso=cte.chave_acesso
        ).first()

        if pendencia_existente:
            logger.info(f"Pendencia ja existe para CTe {cte.numero_cte}: {pendencia_existente.status}")
            return pendencia_existente.status == 'aprovado', pendencia_existente, "Pendencia ja registrada"

        # Buscar regime tributario do emitente (transportadora) no Odoo
        regime_info = self.buscar_regime_tributario_odoo(cte.cnpj_emitente)

        if not regime_info:
            logger.warning(f"Nao foi possivel obter regime tributario de {cte.cnpj_emitente}")
            return True, None, "Regime tributario nao encontrado - ignorando validacao"

        regime = regime_info.get('regime_tributario')
        logger.info(f"Regime tributario do emitente {cte.cnpj_emitente}: {regime} ({regime_info.get('regime_descricao')})")

        # Se for Simples Nacional, nao precisa validar IBS/CBS
        if regime in self.REGIMES_ISENTOS:
            logger.info(f"Emitente {cte.cnpj_emitente} e Simples Nacional - IBS/CBS nao obrigatorio")
            return True, None, "Simples Nacional - IBS/CBS nao obrigatorio"

        # Se for Regime Normal ou excesso sublimite, DEVE destacar IBS/CBS
        if regime in self.REGIMES_OBRIGADOS or regime in self.REGIMES_ANALISE:
            # Obter XML para extrair IBS/CBS
            if not xml_content:
                xml_content = self._obter_xml_cte(cte)

            if not xml_content:
                logger.warning(f"XML nao disponivel para CTe {cte.numero_cte}")
                return True, None, "XML nao disponivel - ignorando validacao"

            # Extrair IBS/CBS do XML
            parser = CTeXMLParser(xml_content)
            ibscbs = parser.get_ibscbs()

            # ====== CORREÇÃO: Extrair também impostos (ICMS, PIS, COFINS) do XML ======
            # A base de cálculo do IBS/CBS deve ser: Valor - ICMS - PIS - COFINS
            impostos = parser.get_impostos()

            # Validar TODOS os campos (passando os impostos extraidos)
            divergencias = self._validar_campos_cte(ibscbs, cte, impostos)

            if not divergencias:
                logger.info(f"CTe {cte.numero_cte} possui IBS/CBS destacado corretamente")
                return True, None, "IBS/CBS validado com sucesso"

            # Tem divergencias - criar pendencia
            logger.warning(f"CTe {cte.numero_cte} com divergencias IBS/CBS: {divergencias}")
            pendencia = self._criar_pendencia_cte(cte, regime_info, ibscbs, divergencias)
            return False, pendencia, f"Divergencias encontradas: {', '.join(divergencias)}"

        # Regime desconhecido
        logger.info(f"Regime tributario {regime} nao mapeado - ignorando validacao")
        return True, None, f"Regime tributario {regime} nao requer validacao"

    def _validar_campos_cte(
        self,
        ibscbs: Optional[Dict],
        cte: ConhecimentoTransporte,
        impostos: Optional[Dict] = None
    ) -> List[str]:
        """
        Valida TODOS os campos IBS/CBS do CTe contra valores esperados.

        REGRA IMPORTANTE (Reforma Tributária 2026):
        A base de cálculo do IBS/CBS é o valor do documento MENOS os impostos
        que estão sendo substituídos (ICMS, PIS, COFINS).

        Fórmula: Base IBS/CBS = Valor Total - ICMS - PIS - COFINS

        Args:
            ibscbs: Dados IBS/CBS extraidos do XML
            cte: ConhecimentoTransporte
            impostos: Dados de impostos (ICMS, PIS, COFINS) extraidos do XML

        Returns:
            Lista de divergencias encontradas (vazia se OK)
        """
        divergencias = []

        # Se nao tem IBS/CBS no XML
        if not ibscbs or not ibscbs.get('encontrado'):
            divergencias.append("Tag <IBSCBS> nao encontrada no XML")
            return divergencias

        valor_cte = Decimal(str(cte.valor_total)) if cte.valor_total else Decimal('0')

        # ====== CALCULAR BASE DE CALCULO ESPERADA DO IBS/CBS ======
        # Base IBS/CBS = Valor Total - ICMS - PIS - COFINS
        # Os valores vem do proprio XML do documento

        valor_icms = Decimal('0')
        valor_pis = Decimal('0')
        valor_cofins = Decimal('0')

        if impostos:
            if impostos.get('valor_icms'):
                valor_icms = Decimal(str(impostos['valor_icms']))
            if impostos.get('valor_pis'):
                valor_pis = Decimal(str(impostos['valor_pis']))
            if impostos.get('valor_cofins'):
                valor_cofins = Decimal(str(impostos['valor_cofins']))
        else:
            # Fallback: usar valor_icms do modelo se impostos nao foram passados
            if cte.valor_icms:
                valor_icms = Decimal(str(cte.valor_icms))

        # Base esperada = Valor Total - ICMS - PIS - COFINS
        base_ibscbs_esperada = (valor_cte - valor_icms - valor_pis - valor_cofins).quantize(Decimal('0.01'), ROUND_HALF_UP)

        logger.info(f"Calculo base IBS/CBS: Valor={valor_cte}, ICMS={valor_icms}, PIS={valor_pis}, COFINS={valor_cofins} => Base esperada={base_ibscbs_esperada}")

        # ====== VALIDAR CST ======
        cst_xml = ibscbs.get('cst')
        if cst_xml != AliquotasCTe.CST:
            divergencias.append(f"CST incorreto: esperado={AliquotasCTe.CST}, encontrado={cst_xml}")

        # ====== VALIDAR cClassTrib ======
        class_trib_xml = ibscbs.get('class_trib')
        if class_trib_xml != AliquotasCTe.CLASS_TRIB:
            divergencias.append(f"cClassTrib incorreto: esperado={AliquotasCTe.CLASS_TRIB}, encontrado={class_trib_xml}")

        # ====== VALIDAR vBC (Base de Calculo IBS/CBS) ======
        # CORRECAO: A base deve ser o valor SEM ICMS/PIS/COFINS
        vbc_xml = Decimal(str(ibscbs.get('base_calculo') or 0))
        if abs(vbc_xml - base_ibscbs_esperada) > TOLERANCIA_VALOR:
            divergencias.append(f"vBC incorreto: esperado={base_ibscbs_esperada} (valor-ICMS-PIS-COFINS), encontrado={vbc_xml}")

        # ====== VALIDAR pIBSUF ======
        aliq_ibs_uf_xml = Decimal(str(ibscbs.get('ibs_uf_aliquota') or 0))
        if abs(aliq_ibs_uf_xml - AliquotasCTe.ALIQ_IBS_UF) > TOLERANCIA_ALIQUOTA:
            divergencias.append(f"pIBSUF incorreto: esperado={AliquotasCTe.ALIQ_IBS_UF}, encontrado={aliq_ibs_uf_xml}")

        # ====== VALIDAR vIBSUF (calculado sobre a base correta) ======
        valor_ibs_uf_xml = Decimal(str(ibscbs.get('ibs_uf_valor') or 0))
        valor_ibs_uf_esperado = (vbc_xml * AliquotasCTe.ALIQ_IBS_UF / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
        if abs(valor_ibs_uf_xml - valor_ibs_uf_esperado) > TOLERANCIA_VALOR:
            divergencias.append(f"vIBSUF incorreto: esperado={valor_ibs_uf_esperado}, encontrado={valor_ibs_uf_xml}")

        # ====== VALIDAR pIBSMun ======
        aliq_ibs_mun_xml = Decimal(str(ibscbs.get('ibs_mun_aliquota') or 0))
        if abs(aliq_ibs_mun_xml - AliquotasCTe.ALIQ_IBS_MUN) > TOLERANCIA_ALIQUOTA:
            divergencias.append(f"pIBSMun incorreto: esperado={AliquotasCTe.ALIQ_IBS_MUN}, encontrado={aliq_ibs_mun_xml}")

        # ====== VALIDAR vIBSMun (calculado sobre a base correta) ======
        valor_ibs_mun_xml = Decimal(str(ibscbs.get('ibs_mun_valor') or 0))
        valor_ibs_mun_esperado = (vbc_xml * AliquotasCTe.ALIQ_IBS_MUN / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
        if abs(valor_ibs_mun_xml - valor_ibs_mun_esperado) > TOLERANCIA_VALOR:
            divergencias.append(f"vIBSMun incorreto: esperado={valor_ibs_mun_esperado}, encontrado={valor_ibs_mun_xml}")

        # ====== VALIDAR vIBS (calculado = vIBSUF + vIBSMun) ======
        valor_ibs_total_xml = Decimal(str(ibscbs.get('ibs_total') or 0))
        valor_ibs_total_esperado = valor_ibs_uf_esperado + valor_ibs_mun_esperado
        if abs(valor_ibs_total_xml - valor_ibs_total_esperado) > TOLERANCIA_VALOR:
            divergencias.append(f"vIBS incorreto: esperado={valor_ibs_total_esperado}, encontrado={valor_ibs_total_xml}")

        # ====== VALIDAR pCBS ======
        aliq_cbs_xml = Decimal(str(ibscbs.get('cbs_aliquota') or 0))
        if abs(aliq_cbs_xml - AliquotasCTe.ALIQ_CBS) > TOLERANCIA_ALIQUOTA:
            divergencias.append(f"pCBS incorreto: esperado={AliquotasCTe.ALIQ_CBS}, encontrado={aliq_cbs_xml}")

        # ====== VALIDAR vCBS (calculado sobre a base correta) ======
        valor_cbs_xml = Decimal(str(ibscbs.get('cbs_valor') or 0))
        valor_cbs_esperado = (vbc_xml * AliquotasCTe.ALIQ_CBS / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
        if abs(valor_cbs_xml - valor_cbs_esperado) > TOLERANCIA_VALOR:
            divergencias.append(f"vCBS incorreto: esperado={valor_cbs_esperado}, encontrado={valor_cbs_xml}")

        return divergencias

    def _obter_xml_cte(self, cte: ConhecimentoTransporte) -> Optional[str]:
        """
        Obtem conteudo XML do CTe.

        Prioridade:
        1. Buscar do S3 se cte_xml_path estiver preenchido
        2. Buscar do Odoo se tiver dfe_id (fallback)

        Args:
            cte: ConhecimentoTransporte

        Returns:
            Conteudo XML como string ou None
        """
        # PRIORIDADE 1: Buscar do S3
        if cte.cte_xml_path:
            try:
                from flask import current_app
                import boto3
                import os

                use_s3 = current_app.config.get('USE_S3', False)

                if use_s3 and not cte.cte_xml_path.startswith('uploads/'):
                    # Arquivo no S3
                    s3 = boto3.client(
                        's3',
                        aws_access_key_id=current_app.config.get('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=current_app.config.get('AWS_SECRET_ACCESS_KEY'),
                        region_name=current_app.config.get('AWS_REGION', 'us-east-1')
                    )
                    bucket = current_app.config.get('S3_BUCKET_NAME')

                    response = s3.get_object(Bucket=bucket, Key=cte.cte_xml_path)
                    xml_bytes = response['Body'].read()

                    # Decodificar com fallback
                    try:
                        return xml_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        return xml_bytes.decode('iso-8859-1')
                else:
                    # Arquivo local (desenvolvimento)
                    file_path = os.path.join(current_app.root_path, 'static', cte.cte_xml_path)
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            xml_bytes = f.read()
                            try:
                                return xml_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                return xml_bytes.decode('iso-8859-1')

            except Exception as e:
                logger.warning(f"Erro ao buscar XML do S3/local: {e}")

        # PRIORIDADE 2: Fallback - Buscar do Odoo
        if cte.dfe_id:
            try:
                odoo = self._get_odoo()
                if odoo:
                    dfe = odoo.search_read(
                        'l10n_br_ciel_it_account.dfe',
                        [['id', '=', int(cte.dfe_id)]],
                        ['l10n_br_xml_dfe']
                    )
                    if dfe and dfe[0].get('l10n_br_xml_dfe'):
                        import base64
                        xml_b64 = dfe[0]['l10n_br_xml_dfe']
                        return base64.b64decode(xml_b64).decode('utf-8')
            except Exception as e:
                logger.warning(f"Erro ao buscar XML do Odoo: {e}")

        return None

    def _criar_pendencia_cte(
        self,
        cte: ConhecimentoTransporte,
        regime_info: Dict,
        ibscbs: Optional[Dict],
        divergencias: List[str]
    ) -> PendenciaFiscalIbsCbs:
        """
        Cria pendencia fiscal para CTe com divergencias IBS/CBS.

        Args:
            cte: ConhecimentoTransporte
            regime_info: Informacoes do regime tributario
            ibscbs: Dados IBS/CBS extraidos do XML
            divergencias: Lista de divergencias encontradas

        Returns:
            PendenciaFiscalIbsCbs criada
        """
        # Determinar motivo principal
        if not ibscbs or not ibscbs.get('encontrado'):
            motivo = 'nao_destacou'
        elif 'CST incorreto' in str(divergencias) or 'cClassTrib incorreto' in str(divergencias):
            motivo = 'cst_incorreto'
        elif 'incorreto' in str(divergencias):
            motivo = 'aliquota_divergente'
        else:
            motivo = 'valor_zerado'

        detalhes = "; ".join(divergencias) if divergencias else "IBS/CBS nao destacado"

        pendencia = PendenciaFiscalIbsCbs(
            tipo_documento='CTe',
            chave_acesso=cte.chave_acesso,
            numero_documento=cte.numero_cte,
            serie=cte.serie_cte,
            data_emissao=cte.data_emissao,
            odoo_dfe_id=int(cte.dfe_id) if cte.dfe_id else None,
            cte_id=cte.id,
            cnpj_fornecedor=cte.cnpj_emitente,
            razao_fornecedor=cte.nome_emitente or regime_info.get('nome'),
            regime_tributario=regime_info.get('regime_tributario'),
            regime_tributario_descricao=regime_info.get('regime_descricao'),
            valor_total=float(cte.valor_total) if cte.valor_total else None,
            motivo_pendencia=motivo,
            detalhes_pendencia=detalhes,
            status='pendente',
            criado_por='SISTEMA'
        )

        # Preencher valores IBS/CBS encontrados no XML
        if ibscbs:
            pendencia.ibscbs_cst = ibscbs.get('cst')
            pendencia.ibscbs_class_trib = ibscbs.get('class_trib')
            pendencia.ibscbs_base = ibscbs.get('base_calculo')
            pendencia.ibs_uf_aliq = ibscbs.get('ibs_uf_aliquota')
            pendencia.ibs_uf_valor = ibscbs.get('ibs_uf_valor')
            pendencia.ibs_mun_aliq = ibscbs.get('ibs_mun_aliquota')
            pendencia.ibs_mun_valor = ibscbs.get('ibs_mun_valor')
            pendencia.ibs_total = ibscbs.get('ibs_total')
            pendencia.cbs_aliq = ibscbs.get('cbs_aliquota')
            pendencia.cbs_valor = ibscbs.get('cbs_valor')

        db.session.add(pendencia)
        db.session.commit()

        logger.info(f"Pendencia fiscal IBS/CBS criada para CTe {cte.numero_cte}: ID={pendencia.id}")

        return pendencia

    # =========================================================================
    # VALIDACAO DE NF-e (por NCM)
    # =========================================================================

    def validar_nfe_linha(
        self,
        ncm: str,
        ibscbs_valores: Dict,
        valor_produto: Decimal,
        cnpj_fornecedor: str,
        dados_documento: Dict,
        impostos_linha: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Valida IBS/CBS de uma linha de NF-e com aliquotas por NCM.

        REGRA IMPORTANTE (Reforma Tributária 2026):
        A base de cálculo do IBS/CBS é o valor do produto MENOS os impostos
        que estão sendo substituídos (ICMS, PIS, COFINS).

        Fórmula: Base IBS/CBS = Valor Produto - ICMS - PIS - COFINS

        Campos validados (todos cadastrados por NCM):
        - CST
        - cClassTrib
        - vBC (= valor do produto - ICMS - PIS - COFINS)
        - pIBSUF
        - pRedAliq (reducao IBS UF)
        - pAliqEfet (calculada: pIBSUF * (1 - pRedAliq/100))
        - vIBSUF (= vBC * pAliqEfet/100)
        - pIBSMun
        - pRedAliq (reducao IBS Mun)
        - pAliqEfet
        - vIBSMun
        - vIBS (= vIBSUF + vIBSMun)
        - pCBS
        - pRedAliq (reducao CBS)
        - pAliqEfet
        - vCBS

        Args:
            ncm: Codigo NCM completo
            ibscbs_valores: Valores IBS/CBS extraidos da linha
            valor_produto: Valor do produto
            cnpj_fornecedor: CNPJ do fornecedor
            dados_documento: Dados do documento (chave, numero, etc)
            impostos_linha: Dict com valor_icms, valor_pis, valor_cofins da linha (opcional)

        Returns:
            Tuple[bool, str, List[str]]:
                - bool: True se OK
                - str: Motivo principal (se reprovado)
                - List[str]: Lista de divergencias
        """
        # Extrair 4 primeiros digitos do NCM
        ncm_prefixo = ncm[:4] if ncm and len(ncm) >= 4 else None

        if not ncm_prefixo:
            return True, None, []

        # Buscar regime tributario
        regime_info = self.buscar_regime_tributario_odoo(cnpj_fornecedor)

        if not regime_info:
            return True, None, []

        regime = regime_info.get('regime_tributario')

        # Se for Simples Nacional, nao valida
        if regime in self.REGIMES_ISENTOS:
            return True, None, []

        # Se nao for Regime Normal, nao valida
        if regime not in self.REGIMES_OBRIGADOS:
            return True, None, []

        # Buscar NCM na tabela de validados
        ncm_cadastro = NcmIbsCbsValidado.query.filter_by(
            ncm_prefixo=ncm_prefixo,
            ativo=True
        ).first()

        if not ncm_cadastro:
            # NCM nao esta na tabela - nao valida mas registra sugestao
            logger.info(f"NCM {ncm_prefixo} nao cadastrado para validacao IBS/CBS")
            return True, "ncm_nao_cadastrado", [f"NCM {ncm_prefixo} nao cadastrado"]

        # Validar TODOS os campos contra o cadastro (passando os impostos da linha)
        divergencias = self._validar_campos_nfe(ibscbs_valores, ncm_cadastro, valor_produto, impostos_linha)

        if not divergencias:
            return True, None, []

        # Determinar motivo principal
        if 'CST incorreto' in str(divergencias):
            motivo = 'cst_incorreto'
        elif 'nao encontrada' in str(divergencias):
            motivo = 'nao_destacou'
        else:
            motivo = 'aliquota_divergente'

        return False, motivo, divergencias

    def _validar_campos_nfe(
        self,
        ibscbs: Dict,
        ncm_cadastro: NcmIbsCbsValidado,
        valor_produto: Decimal,
        impostos_linha: Optional[Dict] = None
    ) -> List[str]:
        """
        Valida TODOS os campos IBS/CBS da NF-e contra cadastro do NCM.

        REGRA IMPORTANTE (Reforma Tributária 2026):
        A base de cálculo do IBS/CBS é o valor do produto MENOS os impostos
        que estão sendo substituídos (ICMS, PIS, COFINS).

        Fórmula: Base IBS/CBS = Valor Produto - ICMS - PIS - COFINS

        Args:
            ibscbs: Dados IBS/CBS extraidos do XML
            ncm_cadastro: Cadastro do NCM com aliquotas esperadas
            valor_produto: Valor do produto
            impostos_linha: Dict com valor_icms, valor_pis, valor_cofins da linha

        Returns:
            Lista de divergencias encontradas
        """
        divergencias = []

        # Se nao tem IBS/CBS
        if not ibscbs:
            divergencias.append("Tag <IBSCBS> nao encontrada")
            return divergencias

        valor_prod = Decimal(str(valor_produto)) if valor_produto else Decimal('0')

        # ====== CALCULAR BASE DE CALCULO ESPERADA DO IBS/CBS ======
        # Base IBS/CBS = Valor Produto - ICMS - PIS - COFINS
        # Os valores vem do proprio XML do documento

        valor_icms = Decimal('0')
        valor_pis = Decimal('0')
        valor_cofins = Decimal('0')

        if impostos_linha:
            if impostos_linha.get('valor_icms'):
                valor_icms = Decimal(str(impostos_linha['valor_icms']))
            if impostos_linha.get('valor_pis'):
                valor_pis = Decimal(str(impostos_linha['valor_pis']))
            if impostos_linha.get('valor_cofins'):
                valor_cofins = Decimal(str(impostos_linha['valor_cofins']))

        # Base esperada = Valor Produto - ICMS - PIS - COFINS
        base_ibscbs_esperada = (valor_prod - valor_icms - valor_pis - valor_cofins).quantize(Decimal('0.01'), ROUND_HALF_UP)

        logger.info(f"Calculo base IBS/CBS NF-e: Valor={valor_prod}, ICMS={valor_icms}, PIS={valor_pis}, COFINS={valor_cofins} => Base esperada={base_ibscbs_esperada}")

        # ====== VALIDAR CST ======
        if ncm_cadastro.cst_esperado:
            cst_xml = ibscbs.get('cst')
            if cst_xml != ncm_cadastro.cst_esperado:
                divergencias.append(f"CST incorreto: esperado={ncm_cadastro.cst_esperado}, encontrado={cst_xml}")

        # ====== VALIDAR cClassTrib ======
        if ncm_cadastro.class_trib_codigo:
            class_trib_xml = ibscbs.get('class_trib')
            if class_trib_xml != ncm_cadastro.class_trib_codigo:
                divergencias.append(f"cClassTrib incorreto: esperado={ncm_cadastro.class_trib_codigo}, encontrado={class_trib_xml}")

        # ====== VALIDAR vBC (Base de Calculo IBS/CBS) ======
        # CORRECAO: A base deve ser o valor SEM ICMS/PIS/COFINS
        vbc_xml = Decimal(str(ibscbs.get('base_calculo') or 0))
        if abs(vbc_xml - base_ibscbs_esperada) > TOLERANCIA_VALOR:
            divergencias.append(f"vBC incorreto: esperado={base_ibscbs_esperada} (valor-ICMS-PIS-COFINS), encontrado={vbc_xml}")

        # Obter reducao cadastrada (ou zero se nao houver)
        reducao = Decimal(str(ncm_cadastro.reducao_aliquota or 0))

        # ====== VALIDAR IBS UF ======
        if ncm_cadastro.aliquota_ibs_uf is not None:
            aliq_esperada = Decimal(str(ncm_cadastro.aliquota_ibs_uf))
            aliq_xml = Decimal(str(ibscbs.get('ibs_uf_aliquota') or 0))

            if abs(aliq_xml - aliq_esperada) > TOLERANCIA_ALIQUOTA:
                divergencias.append(f"pIBSUF incorreto: esperado={aliq_esperada}, encontrado={aliq_xml}")

            # Validar reducao e aliquota efetiva
            if reducao > 0:
                aliq_efetiva_esperada = (aliq_esperada * (100 - reducao) / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
                aliq_efetiva_xml = Decimal(str(ibscbs.get('ibs_uf_aliq_efetiva') or 0))

                if abs(aliq_efetiva_xml - aliq_efetiva_esperada) > TOLERANCIA_ALIQUOTA:
                    divergencias.append(f"pAliqEfet IBS UF incorreto: esperado={aliq_efetiva_esperada}, encontrado={aliq_efetiva_xml}")

                reducao_xml = Decimal(str(ibscbs.get('ibs_uf_reducao') or 0))
                if abs(reducao_xml - reducao) > TOLERANCIA_ALIQUOTA:
                    divergencias.append(f"pRedAliq IBS UF incorreto: esperado={reducao}, encontrado={reducao_xml}")

                # Valor calculado com aliquota efetiva
                valor_esperado = (vbc_xml * aliq_efetiva_esperada / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
            else:
                valor_esperado = (vbc_xml * aliq_esperada / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)

            valor_xml = Decimal(str(ibscbs.get('ibs_uf_valor') or 0))
            if abs(valor_xml - valor_esperado) > TOLERANCIA_VALOR:
                divergencias.append(f"vIBSUF incorreto: esperado={valor_esperado}, encontrado={valor_xml}")

        # ====== VALIDAR IBS MUN ======
        if ncm_cadastro.aliquota_ibs_mun is not None:
            aliq_esperada = Decimal(str(ncm_cadastro.aliquota_ibs_mun))
            aliq_xml = Decimal(str(ibscbs.get('ibs_mun_aliquota') or 0))

            if abs(aliq_xml - aliq_esperada) > TOLERANCIA_ALIQUOTA:
                divergencias.append(f"pIBSMun incorreto: esperado={aliq_esperada}, encontrado={aliq_xml}")

            # Validar reducao e aliquota efetiva
            if reducao > 0:
                aliq_efetiva_esperada = (aliq_esperada * (100 - reducao) / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
                aliq_efetiva_xml = Decimal(str(ibscbs.get('ibs_mun_aliq_efetiva') or 0))

                if abs(aliq_efetiva_xml - aliq_efetiva_esperada) > TOLERANCIA_ALIQUOTA:
                    divergencias.append(f"pAliqEfet IBS Mun incorreto: esperado={aliq_efetiva_esperada}, encontrado={aliq_efetiva_xml}")

                valor_esperado = (vbc_xml * aliq_efetiva_esperada / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
            else:
                valor_esperado = (vbc_xml * aliq_esperada / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)

            valor_xml = Decimal(str(ibscbs.get('ibs_mun_valor') or 0))
            if abs(valor_xml - valor_esperado) > TOLERANCIA_VALOR:
                divergencias.append(f"vIBSMun incorreto: esperado={valor_esperado}, encontrado={valor_xml}")

        # ====== VALIDAR CBS ======
        if ncm_cadastro.aliquota_cbs is not None:
            aliq_esperada = Decimal(str(ncm_cadastro.aliquota_cbs))
            aliq_xml = Decimal(str(ibscbs.get('cbs_aliquota') or 0))

            if abs(aliq_xml - aliq_esperada) > TOLERANCIA_ALIQUOTA:
                divergencias.append(f"pCBS incorreto: esperado={aliq_esperada}, encontrado={aliq_xml}")

            # Validar reducao e aliquota efetiva
            if reducao > 0:
                aliq_efetiva_esperada = (aliq_esperada * (100 - reducao) / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
                aliq_efetiva_xml = Decimal(str(ibscbs.get('cbs_aliq_efetiva') or 0))

                if abs(aliq_efetiva_xml - aliq_efetiva_esperada) > TOLERANCIA_ALIQUOTA:
                    divergencias.append(f"pAliqEfet CBS incorreto: esperado={aliq_efetiva_esperada}, encontrado={aliq_efetiva_xml}")

                reducao_xml = Decimal(str(ibscbs.get('cbs_reducao') or 0))
                if abs(reducao_xml - reducao) > TOLERANCIA_ALIQUOTA:
                    divergencias.append(f"pRedAliq CBS incorreto: esperado={reducao}, encontrado={reducao_xml}")

                valor_esperado = (vbc_xml * aliq_efetiva_esperada / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
            else:
                valor_esperado = (vbc_xml * aliq_esperada / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)

            valor_xml = Decimal(str(ibscbs.get('cbs_valor') or 0))
            if abs(valor_xml - valor_esperado) > TOLERANCIA_VALOR:
                divergencias.append(f"vCBS incorreto: esperado={valor_esperado}, encontrado={valor_xml}")

        return divergencias

    # =========================================================================
    # PROCESSAMENTO EM LOTE
    # =========================================================================

    def processar_ctes_pendentes(self, minutos_janela: int = 120) -> Dict:
        """
        Processa CTes que ainda nao foram validados para IBS/CBS.

        Args:
            minutos_janela: Janela de tempo em minutos para buscar CTes

        Returns:
            Dict com estatisticas do processamento
        """
        logger.info(f"Iniciando processamento de CTes pendentes de validacao IBS/CBS (janela={minutos_janela} minutos)")

        resultado = {
            'processados': 0,
            'aprovados': 0,
            'pendencias_criadas': 0,
            'erros': 0,
            'ignorados': 0
        }

        from sqlalchemy import and_

        # Calcular data limite baseada na janela de tempo
        data_limite = datetime.utcnow() - timedelta(minutes=minutos_janela)

        # Subquery para CTes que ja tem pendencia
        subquery = db.session.query(PendenciaFiscalIbsCbs.chave_acesso).filter(
            PendenciaFiscalIbsCbs.tipo_documento == 'CTe'
        )

        ctes = ConhecimentoTransporte.query.filter(
            and_(
                ConhecimentoTransporte.ativo == True,
                ConhecimentoTransporte.tipo_cte == '0',  # Normal
                ConhecimentoTransporte.chave_acesso.isnot(None),
                ConhecimentoTransporte.data_emissao >= data_limite.date(),  # Filtro por data de emissao
                ~ConhecimentoTransporte.chave_acesso.in_(subquery)
            )
        ).all()

        logger.info(f"Encontrados {len(ctes)} CTes para processar (emissao >= {data_limite.date()})")

        for cte in ctes:
            try:
                resultado['processados'] += 1

                ok, pendencia, msg = self.validar_cte(cte)

                if ok:
                    resultado['aprovados'] += 1
                elif pendencia:
                    resultado['pendencias_criadas'] += 1
                else:
                    resultado['ignorados'] += 1

                logger.debug(f"CTe {cte.numero_cte}: {msg}")

            except Exception as e:
                resultado['erros'] += 1
                logger.error(f"Erro ao processar CTe {cte.numero_cte}: {e}")

        logger.info(f"Processamento concluido: {resultado}")
        return resultado

    # =========================================================================
    # CADASTRO DE NCM
    # =========================================================================

    def cadastrar_ncm_validado(
        self,
        ncm_prefixo: str,
        cst: str,
        class_trib: str,
        aliquota_ibs_uf: float,
        aliquota_ibs_mun: float,
        aliquota_cbs: float,
        reducao_aliquota: float = 0,
        descricao: str = None,
        usuario: str = None
    ) -> NcmIbsCbsValidado:
        """
        Cadastra um NCM com aliquotas para validacao IBS/CBS de NF-e.

        Args:
            ncm_prefixo: 4 primeiros digitos do NCM
            cst: CST esperado (ex: '200')
            class_trib: Codigo classificacao tributaria (ex: '200034')
            aliquota_ibs_uf: Aliquota IBS UF (ex: 0.10)
            aliquota_ibs_mun: Aliquota IBS Municipio (ex: 0.00)
            aliquota_cbs: Aliquota CBS (ex: 0.90)
            reducao_aliquota: Percentual de reducao (ex: 60.00)
            descricao: Descricao do NCM
            usuario: Usuario que cadastrou

        Returns:
            NcmIbsCbsValidado criado ou existente
        """
        if len(ncm_prefixo) != 4:
            raise ValueError("NCM prefixo deve ter exatamente 4 digitos")

        # Verificar se ja existe
        existente = NcmIbsCbsValidado.query.filter_by(ncm_prefixo=ncm_prefixo).first()
        if existente:
            # Atualizar existente
            existente.cst_esperado = cst
            existente.class_trib_codigo = class_trib
            existente.aliquota_ibs_uf = Decimal(str(aliquota_ibs_uf))
            existente.aliquota_ibs_mun = Decimal(str(aliquota_ibs_mun))
            existente.aliquota_cbs = Decimal(str(aliquota_cbs))
            existente.reducao_aliquota = Decimal(str(reducao_aliquota)) if reducao_aliquota else None
            existente.descricao_ncm = descricao or existente.descricao_ncm
            existente.validado_por = usuario
            existente.validado_em = datetime.utcnow()
            existente.ativo = True
            db.session.commit()
            logger.info(f"NCM {ncm_prefixo} atualizado")
            return existente

        ncm = NcmIbsCbsValidado(
            ncm_prefixo=ncm_prefixo,
            descricao_ncm=descricao,
            cst_esperado=cst,
            class_trib_codigo=class_trib,
            aliquota_ibs_uf=Decimal(str(aliquota_ibs_uf)),
            aliquota_ibs_mun=Decimal(str(aliquota_ibs_mun)),
            aliquota_cbs=Decimal(str(aliquota_cbs)),
            reducao_aliquota=Decimal(str(reducao_aliquota)) if reducao_aliquota else None,
            ativo=True,
            validado_por=usuario,
            validado_em=datetime.utcnow()
        )

        db.session.add(ncm)
        db.session.commit()

        logger.info(f"NCM {ncm_prefixo} cadastrado para validacao IBS/CBS")
        return ncm

    # =========================================================================
    # CONSULTAS
    # =========================================================================

    def listar_pendencias(
        self,
        tipo_documento: str = None,
        status: str = 'pendente',
        limite: int = 100
    ) -> List[PendenciaFiscalIbsCbs]:
        """Lista pendencias fiscais de IBS/CBS."""
        query = db.session.query(PendenciaFiscalIbsCbs)

        if tipo_documento:
            query = query.filter_by(tipo_documento=tipo_documento)

        if status:
            query = query.filter_by(status=status)

        return query.order_by(PendenciaFiscalIbsCbs.criado_em.desc()).limit(limite).all()

    def resolver_pendencia(
        self,
        pendencia_id: int,
        resolucao: str,
        justificativa: str,
        usuario: str
    ) -> PendenciaFiscalIbsCbs:
        """Resolve uma pendencia fiscal."""
        pendencia = db.session.get(PendenciaFiscalIbsCbs,pendencia_id) if pendencia_id else None
        if not pendencia:
            raise ValueError(f"Pendencia {pendencia_id} nao encontrada")

        if resolucao in ['fornecedor_isento', 'ncm_nao_tributa', 'erro_sistema']:
            pendencia.status = 'aprovado'
        elif resolucao == 'devolvido_fornecedor':
            pendencia.status = 'rejeitado'
        else:
            pendencia.status = 'aprovado'

        pendencia.resolucao = resolucao
        pendencia.justificativa = justificativa
        pendencia.resolvido_por = usuario
        pendencia.resolvido_em = datetime.utcnow()

        db.session.commit()

        logger.info(f"Pendencia {pendencia_id} resolvida: {resolucao} por {usuario}")
        return pendencia

    def listar_ncms_cadastrados(self, apenas_ativos: bool = True) -> List[NcmIbsCbsValidado]:
        """Lista NCMs cadastrados para validacao."""
        query = db.session.query(NcmIbsCbsValidado)

        if apenas_ativos:
            query = query.filter_by(ativo=True)

        return query.order_by(NcmIbsCbsValidado.ncm_prefixo).all()


# Instancia global do service
validacao_ibscbs_service = ValidacaoIbsCbsService()
