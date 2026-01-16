"""
Job de Validacao IBS/CBS - CTes e NF-es
=======================================

Processa documentos fiscais para validar destaque de IBS/CBS.

Regras:
- CTes: Aliquotas FIXAS (CST=000, pIBSUF=0.10%, pCBS=0.90%)
- NF-es: Aliquotas por NCM (4 primeiros digitos)
- Apenas fornecedores Regime Normal (CRT=3) devem destacar

Autor: Sistema de Fretes
Data: 2026-01-16
"""

import logging
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app import db
from app.recebimento.models import PendenciaFiscalIbsCbs
from app.recebimento.services.validacao_ibscbs_service import validacao_ibscbs_service
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

# CNPJs do grupo a serem ignorados (Nacom, Goya)
CNPJS_IGNORAR = ['61724241', '18467441']


class ValidacaoIbsCbsJob:
    """
    Job para validacao IBS/CBS de CTes e NF-es.

    Integra com scheduler existente.
    """

    def __init__(self):
        self.odoo = None

    def _get_odoo(self):
        """Obtem conexao com Odoo (lazy loading)"""
        if self.odoo is None:
            self.odoo = get_odoo_connection()
            if not self.odoo.authenticate():
                raise Exception("Falha na autenticacao com Odoo")
        return self.odoo

    def executar(self, minutos_janela: int = 120) -> Dict[str, Any]:
        """
        Executa validacao IBS/CBS para CTes e NF-es.

        Args:
            minutos_janela: Janela de tempo em minutos para buscar documentos

        Returns:
            Dict com estatisticas do processamento
        """
        resultado = {
            'sucesso': True,
            'ctes_processados': 0,
            'ctes_pendencias': 0,
            'nfes_processadas': 0,
            'nfes_pendencias': 0,
            'erros': 0,
            'erro': None
        }

        try:
            logger.info(f"Iniciando validacao IBS/CBS (janela: {minutos_janela} minutos)...")

            # 1. Processar CTes (usa metodo existente do service com janela de tempo)
            logger.info("Processando CTes...")
            try:
                res_ctes = validacao_ibscbs_service.processar_ctes_pendentes(minutos_janela=minutos_janela)
                resultado['ctes_processados'] = res_ctes.get('processados', 0)
                resultado['ctes_pendencias'] = res_ctes.get('pendencias_criadas', 0)
                logger.info(f"CTes processados: {resultado['ctes_processados']}, pendencias: {resultado['ctes_pendencias']}")
            except Exception as e:
                logger.error(f"Erro ao processar CTes: {e}")
                resultado['erros'] += 1

            # 2. Processar NF-es de compra
            logger.info("Processando NF-es...")
            try:
                res_nfes = self._processar_nfes(minutos_janela)
                resultado['nfes_processadas'] = res_nfes.get('processadas', 0)
                resultado['nfes_pendencias'] = res_nfes.get('pendencias', 0)
                resultado['erros'] += res_nfes.get('erros', 0)
                logger.info(f"NF-es processadas: {resultado['nfes_processadas']}, pendencias: {resultado['nfes_pendencias']}")
            except Exception as e:
                logger.error(f"Erro ao processar NF-es: {e}")
                resultado['erros'] += 1

            logger.info(
                f"Validacao IBS/CBS concluida: "
                f"CTes={resultado['ctes_processados']} ({resultado['ctes_pendencias']} pendencias), "
                f"NF-es={resultado['nfes_processadas']} ({resultado['nfes_pendencias']} pendencias), "
                f"erros={resultado['erros']}"
            )

        except Exception as e:
            logger.error(f"Erro no job de validacao IBS/CBS: {e}")
            resultado['sucesso'] = False
            resultado['erro'] = str(e)

        return resultado

    def _processar_nfes(self, minutos_janela: int) -> Dict:
        """
        Processa NF-es de compra para validacao IBS/CBS.

        Args:
            minutos_janela: Janela de tempo em minutos

        Returns:
            Dict com estatisticas: {processadas, pendencias, erros}
        """
        resultado = {'processadas': 0, 'pendencias': 0, 'erros': 0}

        try:
            odoo = self._get_odoo()
            data_limite = datetime.utcnow() - timedelta(minutes=minutos_janela)

            # Buscar NF-es de compra processadas
            # l10n_br_status = '04' significa processado/concluido
            # is_cte = False exclui CTe
            # nfe_infnfe_ide_finnfe != '4' exclui devolucoes
            dfes = odoo.search_read(
                'l10n_br_ciel_it_account.dfe',
                [
                    ['l10n_br_tipo_pedido', '=', 'compra'],
                    ['l10n_br_status', '=', '04'],
                    ['is_cte', '=', False],
                    ['nfe_infnfe_ide_finnfe', '!=', '4'],
                    ['write_date', '>=', data_limite.strftime('%Y-%m-%d %H:%M:%S')]
                ],
                fields=[
                    'id', 'protnfe_infnfe_chnfe', 'nfe_infnfe_ide_nnf',
                    'nfe_infnfe_ide_serie', 'nfe_infnfe_ide_dhemi',
                    'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
                    'nfe_infnfe_emit_uf',
                    'nfe_infnfe_total_icmstot_vnf'
                ],
                limit=50
            )

            if not dfes:
                logger.info("Nenhuma NF-e encontrada para validar")
                return resultado

            logger.info(f"Encontradas {len(dfes)} NF-es para validar")

            for dfe in dfes:
                try:
                    chave = dfe.get('protnfe_infnfe_chnfe')
                    if not chave:
                        continue

                    # Verificar se ja existe pendencia para esta chave
                    if PendenciaFiscalIbsCbs.query.filter_by(chave_acesso=chave).first():
                        continue

                    cnpj = ''.join(c for c in (dfe.get('nfe_infnfe_emit_cnpj') or '') if c.isdigit())

                    # Ignorar CNPJs do grupo (Nacom, Goya)
                    if any(cnpj.startswith(p) for p in CNPJS_IGNORAR):
                        continue

                    # Verificar regime tributario do fornecedor
                    regime_info = validacao_ibscbs_service.buscar_regime_tributario_odoo(cnpj)

                    if not regime_info:
                        logger.debug(f"Regime tributario nao encontrado para CNPJ {cnpj}")
                        continue

                    if regime_info.get('regime_tributario') != '3':
                        # Nao e Regime Normal - nao precisa destacar IBS/CBS
                        continue

                    # Validar NF-e para IBS/CBS
                    pendencia_criada = self._validar_nfe_ibscbs(dfe, regime_info)

                    resultado['processadas'] += 1
                    if pendencia_criada:
                        resultado['pendencias'] += 1

                except Exception as e:
                    logger.error(f"Erro ao processar NF-e {dfe.get('id')}: {e}")
                    resultado['erros'] += 1

        except Exception as e:
            logger.error(f"Erro ao buscar NF-es: {e}")
            resultado['erros'] += 1

        return resultado

    def _validar_nfe_ibscbs(self, dfe: Dict, regime_info: Dict) -> bool:
        """
        Valida uma NF-e para IBS/CBS e cria pendencia se necessario.

        Args:
            dfe: Dados do DFE do Odoo
            regime_info: Informacoes do regime tributario

        Returns:
            True se pendencia foi criada, False caso contrario
        """
        dfe_id = dfe.get('id')

        try:
            odoo = self._get_odoo()

            # Buscar XML da NF-e
            dfe_completo = odoo.search_read(
                'l10n_br_ciel_it_account.dfe',
                [['id', '=', dfe_id]],
                ['l10n_br_xml_dfe']
            )

            if not dfe_completo or not dfe_completo[0].get('l10n_br_xml_dfe'):
                logger.debug(f"XML nao disponivel para NF-e DFE {dfe_id}")
                return False

            # Decodificar XML
            try:
                xml_content = base64.b64decode(dfe_completo[0]['l10n_br_xml_dfe']).decode('utf-8')
            except UnicodeDecodeError:
                xml_content = base64.b64decode(dfe_completo[0]['l10n_br_xml_dfe']).decode('iso-8859-1')

            # Verificar se tem tag <IBSCBS> no XML
            # Tags esperadas: <IBSCBS>, <IBSCBSTot>, <gIBSCBS>
            tem_ibscbs = (
                '<IBSCBS>' in xml_content or
                '<IBSCBSTot>' in xml_content or
                '<gIBSCBS>' in xml_content
            )

            if tem_ibscbs:
                # Tem IBS/CBS destacado - nao criar pendencia
                # Futuramente: validar valores contra cadastro de NCM
                logger.debug(f"NF-e DFE {dfe_id} possui IBS/CBS destacado")
                return False

            # Nao tem IBS/CBS destacado - criar pendencia
            logger.info(f"NF-e DFE {dfe_id} sem IBS/CBS - criando pendencia")

            # Extrair data de emissao
            data_emissao_str = dfe.get('nfe_infnfe_ide_dhemi', '')
            data_emissao = None
            if data_emissao_str:
                try:
                    # Formato pode ser: 2026-01-15T10:30:00-03:00 ou 2026-01-15
                    data_str = data_emissao_str.split('T')[0]
                    data_emissao = datetime.strptime(data_str, '%Y-%m-%d').date()
                except:
                    pass

            pendencia = PendenciaFiscalIbsCbs(
                tipo_documento='NF-e',
                chave_acesso=dfe.get('protnfe_infnfe_chnfe'),
                numero_documento=str(dfe.get('nfe_infnfe_ide_nnf', '')),
                serie=str(dfe.get('nfe_infnfe_ide_serie', '')),
                data_emissao=data_emissao,
                odoo_dfe_id=dfe_id,
                cnpj_fornecedor=''.join(c for c in (dfe.get('nfe_infnfe_emit_cnpj') or '') if c.isdigit()),
                razao_fornecedor=dfe.get('nfe_infnfe_emit_xnome'),
                uf_fornecedor=dfe.get('nfe_infnfe_emit_uf'),
                regime_tributario=regime_info.get('regime_tributario'),
                regime_tributario_descricao=regime_info.get('regime_descricao'),
                valor_total=dfe.get('nfe_infnfe_total_icmstot_vnf'),
                motivo_pendencia='nao_destacou',
                detalhes_pendencia='Tag <IBSCBS> nao encontrada no XML da NF-e',
                status='pendente',
                criado_por='SISTEMA'
            )

            db.session.add(pendencia)
            db.session.commit()

            logger.info(f"Pendencia IBS/CBS criada para NF-e {dfe.get('nfe_infnfe_ide_nnf')}: ID={pendencia.id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao validar NF-e DFE {dfe_id}: {e}")
            db.session.rollback()
            return False


def executar_validacao_ibscbs(minutos_janela: int = 120) -> Dict[str, Any]:
    """
    Funcao de conveniencia para uso no scheduler.

    Args:
        minutos_janela: Janela de tempo em minutos

    Returns:
        Resultado da execucao
    """
    job = ValidacaoIbsCbsJob()
    return job.executar(minutos_janela)
