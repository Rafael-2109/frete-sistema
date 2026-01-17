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

            # Usar no_autoflush para evitar erro de Query-invoked autoflush
            # quando queries sao executadas durante o loop de processamento
            with db.session.no_autoflush:
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

                        # Validar NF-e para IBS/CBS (retorna numero de pendencias criadas)
                        pendencias_criadas = self._validar_nfe_ibscbs(dfe, regime_info)

                        resultado['processadas'] += 1
                        resultado['pendencias'] += pendencias_criadas

                    except Exception as e:
                        logger.error(f"Erro ao processar NF-e {dfe.get('id')}: {e}")
                        resultado['erros'] += 1

        except Exception as e:
            logger.error(f"Erro ao buscar NF-es: {e}")
            resultado['erros'] += 1

        return resultado

    def _validar_nfe_ibscbs(self, dfe: Dict, regime_info: Dict) -> int:
        """
        Valida uma NF-e para IBS/CBS e cria pendencias por NCM distinto.

        Logica:
        1. Buscar XML da NF-e
        2. Parsear cada <det> (linha do item)
        3. Extrair NCM e verificar se tem <IBSCBS> na linha
        4. Agrupar por prefixo NCM (4 digitos)
        5. Para cada prefixo SEM IBS/CBS destacado:
           - Se NCM cadastrado: motivo = 'nao_destacou' (divergencia)
           - Se NCM NAO cadastrado: motivo = 'falta_cadastro'
        6. Criar uma pendencia por prefixo NCM distinto

        Args:
            dfe: Dados do DFE do Odoo
            regime_info: Informacoes do regime tributario

        Returns:
            Numero de pendencias criadas (pode ser > 1 se houver multiplos NCMs)
        """
        from app.recebimento.models import NcmIbsCbsValidado
        import xml.etree.ElementTree as ET
        import re

        dfe_id = dfe.get('id')
        pendencias_criadas = 0

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
                return 0

            # Decodificar XML
            try:
                xml_content = base64.b64decode(dfe_completo[0]['l10n_br_xml_dfe']).decode('utf-8')
            except UnicodeDecodeError:
                xml_content = base64.b64decode(dfe_completo[0]['l10n_br_xml_dfe']).decode('iso-8859-1')

            # Remover namespaces para facilitar parsing
            xml_content_clean = re.sub(r'\sxmlns[^"]*"[^"]*"', '', xml_content)

            try:
                root = ET.fromstring(xml_content_clean)
            except ET.ParseError as e:
                logger.error(f"Erro ao parsear XML da NF-e DFE {dfe_id}: {e}")
                return 0

            # Encontrar todos os itens <det>
            det_elements = root.findall('.//det')

            if not det_elements:
                logger.debug(f"Nenhum item <det> encontrado na NF-e DFE {dfe_id}")
                return 0

            # Estrutura para agrupar por prefixo NCM
            # {prefixo: {'ncm_completo': str, 'itens_sem_ibscbs': list, 'itens_com_ibscbs': list}}
            ncm_analise = {}

            for det in det_elements:
                n_item = det.get('nItem', '?')

                # Buscar NCM dentro de <prod>
                prod = det.find('prod')
                if prod is None:
                    continue

                ncm_elem = prod.find('NCM')
                if ncm_elem is None or not ncm_elem.text:
                    logger.debug(f"Item {n_item} sem NCM na NF-e DFE {dfe_id}")
                    continue

                ncm_completo = ncm_elem.text.strip()
                if not ncm_completo or len(ncm_completo) < 4:
                    logger.debug(f"NCM invalido '{ncm_completo}' no item {n_item} da NF-e DFE {dfe_id}")
                    continue

                ncm_prefixo = ncm_completo[:4]

                # Verificar se tem <IBSCBS> no <imposto> deste item
                imposto = det.find('imposto')
                tem_ibscbs_item = False

                if imposto is not None:
                    ibscbs = imposto.find('IBSCBS')
                    if ibscbs is not None:
                        # Verificar se tem conteudo (CST ou gIBSCBS)
                        cst = ibscbs.find('CST')
                        gibscbs = ibscbs.find('gIBSCBS')
                        if cst is not None or gibscbs is not None:
                            tem_ibscbs_item = True

                # Inicializar entrada do prefixo se nao existir
                if ncm_prefixo not in ncm_analise:
                    ncm_analise[ncm_prefixo] = {
                        'ncm_completo': ncm_completo,
                        'itens_sem_ibscbs': [],
                        'itens_com_ibscbs': []
                    }

                if tem_ibscbs_item:
                    ncm_analise[ncm_prefixo]['itens_com_ibscbs'].append(n_item)
                else:
                    ncm_analise[ncm_prefixo]['itens_sem_ibscbs'].append(n_item)

            # Extrair data de emissao (para todas as pendencias)
            data_emissao_str = dfe.get('nfe_infnfe_ide_dhemi', '')
            data_emissao = None
            if data_emissao_str:
                try:
                    data_str = data_emissao_str.split('T')[0]
                    data_emissao = datetime.strptime(data_str, '%Y-%m-%d').date()
                except Exception as e:
                    logger.error(f"Erro ao extrair data de emissao: {e}")
                    pass

            chave_acesso = dfe.get('protnfe_infnfe_chnfe')
            numero_nf = str(dfe.get('nfe_infnfe_ide_nnf', ''))
            serie = str(dfe.get('nfe_infnfe_ide_serie', ''))
            cnpj = ''.join(c for c in (dfe.get('nfe_infnfe_emit_cnpj') or '') if c.isdigit())
            razao = dfe.get('nfe_infnfe_emit_xnome')
            uf = dfe.get('nfe_infnfe_emit_uf')
            valor_total = dfe.get('nfe_infnfe_total_icmstot_vnf')

            # Processar cada prefixo NCM
            # Usar no_autoflush para evitar erro de Query-invoked autoflush
            # quando queries sao executadas enquanto ha objetos pendentes na sessao
            with db.session.no_autoflush:
                for ncm_prefixo, dados in ncm_analise.items():
                    # Se NAO tem itens sem IBS/CBS, este prefixo esta OK
                    if not dados['itens_sem_ibscbs']:
                        logger.debug(f"Prefixo {ncm_prefixo} OK - todos itens com IBS/CBS na NF-e {numero_nf}")
                        continue

                    # Verificar se ja existe pendencia para esta chave + prefixo
                    pendencia_existente = PendenciaFiscalIbsCbs.query.filter_by(
                        chave_acesso=chave_acesso,
                        ncm_prefixo=ncm_prefixo
                    ).first()

                    if pendencia_existente:
                        logger.debug(f"Pendencia ja existe para NF-e {numero_nf} + NCM {ncm_prefixo}")
                        continue

                    # Verificar se NCM esta cadastrado no sistema
                    ncm_cadastrado = NcmIbsCbsValidado.query.filter_by(
                        ncm_prefixo=ncm_prefixo,
                        ativo=True
                    ).first()

                    # Definir motivo e detalhes
                    itens_str = ', '.join(dados['itens_sem_ibscbs'])

                    if ncm_cadastrado:
                        motivo = 'nao_destacou'
                        detalhes = (
                            f'NCM {ncm_prefixo} (completo: {dados["ncm_completo"]}) esta cadastrado com IBS/CBS obrigatorio, '
                            f'mas o fornecedor nao destacou nos itens: {itens_str}. '
                            f'Aliquotas esperadas: IBS UF={ncm_cadastrado.aliquota_ibs_uf}%, '
                            f'IBS Mun={ncm_cadastrado.aliquota_ibs_mun}%, CBS={ncm_cadastrado.aliquota_cbs}%'
                        )
                    else:
                        motivo = 'falta_cadastro'
                        detalhes = (
                            f'NCM {ncm_prefixo} (completo: {dados["ncm_completo"]}) nao esta cadastrado no sistema. '
                            f'Itens sem IBS/CBS: {itens_str}. '
                            f'Cadastre o NCM para habilitar a validacao.'
                        )

                    # Criar pendencia para este prefixo
                    pendencia = PendenciaFiscalIbsCbs(
                        tipo_documento='NF-e',
                        chave_acesso=chave_acesso,
                        numero_documento=numero_nf,
                        serie=serie,
                        data_emissao=data_emissao,
                        odoo_dfe_id=dfe_id,
                        cnpj_fornecedor=cnpj,
                        razao_fornecedor=razao,
                        uf_fornecedor=uf,
                        regime_tributario=regime_info.get('regime_tributario'),
                        regime_tributario_descricao=regime_info.get('regime_descricao'),
                        ncm=dados['ncm_completo'],
                        ncm_prefixo=ncm_prefixo,
                        valor_total=valor_total,
                        motivo_pendencia=motivo,
                        detalhes_pendencia=detalhes,
                        status='pendente',
                        criado_por='SISTEMA'
                    )

                    db.session.add(pendencia)
                    pendencias_criadas += 1

                    logger.info(
                        f"Pendencia IBS/CBS criada para NF-e {numero_nf}, NCM {ncm_prefixo}: "
                        f"motivo={motivo}, itens={itens_str}"
                    )

            if pendencias_criadas > 0:
                db.session.commit()

            return pendencias_criadas

        except Exception as e:
            logger.error(f"Erro ao validar NF-e DFE {dfe_id}: {e}")
            db.session.rollback()
            return 0


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
