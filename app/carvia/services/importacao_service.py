"""
Importacao Service — Orquestrador do fluxo de importacao
=========================================================

Fluxo:
1. Recebe arquivos (PDFs + XMLs)
2. Classifica cada arquivo (NF-e XML, CTe XML, DANFE PDF, Fatura PDF)
3. Parseia todos os arquivos
4. Classifica CTes por CNPJ emitente (CarVia vs Subcontratado)
5. Executa matching CTe CarVia <-> NF
6. Cria registros no banco:
   - CarviaNf + CarviaNfItem (NFs de mercadoria)
   - CarviaOperacao + junction (CTe CarVia)
   - CarviaSubcontrato (CTe Subcontratado, vinculado via NFs compartilhadas)
   - CarviaFaturaCliente ou CarviaFaturaTransportadora (faturas PDF)
"""

import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app import db
from app.carvia.models import (
    CarviaNf, CarviaNfItem, CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato,
    CarviaFaturaCliente, CarviaFaturaClienteItem, CarviaFaturaTransportadora
)
from app.carvia.services.nfe_xml_parser import NFeXMLParser
from app.carvia.services.cte_xml_parser_carvia import CTeXMLParserCarvia
from app.carvia.services.danfe_pdf_parser import DanfePDFParser
from app.carvia.services.fatura_pdf_parser import FaturaPDFParser
from app.carvia.services.matching_service import MatchingService

# CNPJ da CarVia para classificacao de CTes
CARVIA_CNPJ = re.sub(r'\D', '', os.environ.get('CARVIA_CNPJ', ''))

logger = logging.getLogger(__name__)


class ImportacaoService:
    """Orquestrador do fluxo de importacao de NFs e CTes"""

    def __init__(self):
        self.matching = MatchingService()

    def classificar_arquivo(self, nome_arquivo: str, conteudo: bytes) -> str:
        """
        Classifica o tipo de arquivo.

        Returns:
            'XML_NFE', 'XML_CTE', 'PDF_DANFE', 'PDF_FATURA', 'DESCONHECIDO'
        """
        ext = os.path.splitext(nome_arquivo)[1].lower()

        if ext == '.pdf':
            return self._classificar_pdf(conteudo)

        if ext == '.xml':
            return self._classificar_xml(conteudo)

        return 'DESCONHECIDO'

    def _classificar_pdf(self, conteudo: bytes) -> str:
        """Classifica PDF: DANFE (chave 44 digitos) vs Fatura (fallback).

        DANFE sempre tem chave de acesso de 44 digitos. Se nao encontrar,
        assume que e uma fatura (cliente ou transportadora).
        """
        danfe = DanfePDFParser(pdf_bytes=conteudo)
        if danfe.is_valid():
            chave = danfe.get_chave_acesso()
            if chave and len(chave) == 44:
                return 'PDF_DANFE'
        return 'PDF_FATURA'

    def _classificar_xml(self, conteudo: bytes) -> str:
        """Classifica XML como NF-e ou CTe.

        IMPORTANTE: CTe ANTES de NF-e — CTe XML contem <infNFe> internamente
        (secao <infDoc> referenciando NFs). Truncamento removido para evitar
        falso positivo quando marcadores CTe estao alem dos primeiros bytes.
        """
        try:
            texto_lower = conteudo.decode('utf-8', errors='replace').lower()

            # CTe ANTES de NF-e: CTe contem <infNFe> internamente
            if 'cteproc' in texto_lower or 'infcte' in texto_lower:
                return 'XML_CTE'
            elif 'nfeproc' in texto_lower or 'infnfe' in texto_lower:
                return 'XML_NFE'
            else:
                return 'DESCONHECIDO'
        except Exception:
            return 'DESCONHECIDO'

    def processar_arquivos(self, arquivos: List[Tuple[str, bytes]],
                           criado_por: str) -> Dict:
        """
        Processa lista de arquivos (nome, conteudo bytes).

        Args:
            arquivos: Lista de tuplas (nome_arquivo, conteudo_bytes)
            criado_por: Email do usuario

        Returns:
            Dict com resultado do processamento:
            - nfs_parseadas: lista de dados NF
            - ctes_parseados: lista de dados CTe
            - faturas_parseadas: lista de dados de faturas PDF
            - matches: resultado do matching
            - erros: lista de erros
        """
        nfs_parseadas = []
        ctes_parseados = []
        faturas_parseadas = []
        erros = []

        for nome, conteudo in arquivos:
            tipo = self.classificar_arquivo(nome, conteudo)

            try:
                if tipo == 'XML_NFE':
                    dados = self._parsear_nfe_xml(conteudo, nome)
                    if dados:
                        nfs_parseadas.append(dados)
                    else:
                        erros.append(f'{nome}: Nao foi possivel extrair dados da NF-e XML')

                elif tipo == 'XML_CTE':
                    dados = self._parsear_cte_xml(conteudo, nome)
                    if dados:
                        ctes_parseados.append(dados)
                    else:
                        erros.append(f'{nome}: Nao foi possivel extrair dados do CTe XML')

                elif tipo == 'PDF_DANFE':
                    dados = self._parsear_danfe_pdf(conteudo, nome)
                    if dados:
                        nfs_parseadas.append(dados)
                    else:
                        erros.append(f'{nome}: Nao foi possivel extrair dados do DANFE PDF')

                elif tipo == 'PDF_FATURA':
                    dados_lista = self._parsear_fatura_pdf(conteudo, nome)
                    if dados_lista:
                        faturas_parseadas.extend(dados_lista)
                    else:
                        erros.append(f'{nome}: Nao foi possivel extrair dados da fatura PDF')

                else:
                    erros.append(f'{nome}: Tipo de arquivo nao reconhecido')

            except Exception as e:
                logger.error(f"Erro ao processar {nome}: {e}")
                erros.append(f'{nome}: Erro ao processar - {str(e)}')

        # Classificar CTes por CNPJ emitente (CarVia vs Subcontratado)
        if CARVIA_CNPJ:
            for cte in ctes_parseados:
                cnpj_emit = re.sub(
                    r'\D', '', (cte.get('emitente') or {}).get('cnpj') or ''
                )
                if cnpj_emit == CARVIA_CNPJ:
                    cte['classificacao'] = 'CTE_CARVIA'
                else:
                    cte['classificacao'] = 'CTE_SUBCONTRATO'
        else:
            # Sem CARVIA_CNPJ configurado — todos sao CTe CarVia (compatibilidade)
            for cte in ctes_parseados:
                cte['classificacao'] = 'CTE_CARVIA'

        # Matching (apenas CTes CarVia participam do match com NFs)
        ctes_carvia = [c for c in ctes_parseados if c['classificacao'] == 'CTE_CARVIA']
        matches = {}
        if ctes_carvia and nfs_parseadas:
            matches = self.matching.match_multiplos_ctes(ctes_carvia, nfs_parseadas)

        return {
            'nfs_parseadas': nfs_parseadas,
            'ctes_parseados': ctes_parseados,
            'faturas_parseadas': faturas_parseadas,
            'matches': {k: [m.to_dict() for m in v] for k, v in matches.items()},
            'erros': erros,
        }

    def salvar_importacao(self, nfs_data: List[Dict], ctes_data: List[Dict],
                          matches: Dict, criado_por: str,
                          faturas_data: Optional[List[Dict]] = None) -> Dict:
        """
        Salva os dados processados no banco de dados.

        Args:
            nfs_data: Lista de dicts com dados das NFs
            ctes_data: Lista de dicts com dados dos CTes
            matches: Resultado do matching (cte_key -> lista de match results)
            criado_por: Email do usuario
            faturas_data: Lista de dicts com dados de faturas PDF (opcional)

        Returns:
            Dict com ids criados e estatisticas
        """
        nfs_criadas = []
        operacoes_criadas = []
        subcontratos_criados = []
        faturas_criadas = []
        erros = []

        try:
            # 1. Salvar NFs e seus itens (com deduplicacao)
            nf_map = {}  # chave/numero -> CarviaNf
            for nf_data in nfs_data:
                try:
                    chave = nf_data.get('chave_acesso_nf')
                    numero = nf_data.get('numero_nf')
                    cnpj = nf_data.get('cnpj_emitente')

                    # Verificar se NF ja existe no banco (evitar UNIQUE violation)
                    nf_existente = None
                    if chave:
                        nf_existente = CarviaNf.query.filter_by(
                            chave_acesso_nf=chave
                        ).first()

                    if nf_existente:
                        logger.info(
                            f"NF ja importada (reutilizando): "
                            f"nf_id={nf_existente.id} chave={chave}"
                        )
                        nf = nf_existente
                    else:
                        nf = self._criar_nf(nf_data, criado_por)
                        db.session.add(nf)
                        db.session.flush()  # Obter ID

                        # Gravar itens de produto
                        itens_pendentes = getattr(nf, '_itens_pendentes', [])
                        for item_data in itens_pendentes:
                            item = CarviaNfItem(
                                nf_id=nf.id,
                                codigo_produto=item_data.get('codigo_produto'),
                                descricao=item_data.get('descricao'),
                                ncm=item_data.get('ncm'),
                                cfop=item_data.get('cfop'),
                                unidade=item_data.get('unidade'),
                                quantidade=item_data.get('quantidade'),
                                valor_unitario=item_data.get('valor_unitario'),
                                valor_total_item=item_data.get('valor_total_item'),
                            )
                            db.session.add(item)

                        nfs_criadas.append(nf)

                    if chave:
                        nf_map[chave] = nf
                    if numero and cnpj:
                        nf_map[(cnpj, numero)] = nf

                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Erro ao salvar NF: {e}")
                    erros.append(f"Erro ao salvar NF {nf_data.get('numero_nf')}: {e}")

            # 2. Separar CTes por classificacao (filtro positivo: evitar
            #    CTes com classificacao None/invalida virarem operacao)
            ctes_carvia = [c for c in ctes_data
                           if c.get('classificacao') == 'CTE_CARVIA']
            ctes_subcontrato = [c for c in ctes_data
                                if c.get('classificacao') == 'CTE_SUBCONTRATO']

            # 3. Criar Operacoes a partir dos CTes CarVia
            for cte_data in ctes_carvia:
                try:
                    # Verificar se CTe ja existe no banco (evitar duplicata)
                    cte_chave = cte_data.get('cte_chave_acesso')
                    if cte_chave:
                        op_existente = CarviaOperacao.query.filter_by(
                            cte_chave_acesso=cte_chave
                        ).first()
                        if op_existente:
                            logger.info(
                                f"CTe ja importado (reutilizando): "
                                f"op_id={op_existente.id} cte={cte_chave}"
                            )
                            # Vincular NFs que ainda nao estejam vinculadas
                            nfs_ref = cte_data.get('nfs_referenciadas', [])
                            self._vincular_nfs(op_existente, nfs_ref, nf_map)
                            operacoes_criadas.append(op_existente)
                            continue

                    operacao = self._criar_operacao_de_cte(cte_data, nf_map, criado_por)
                    db.session.add(operacao)
                    db.session.flush()

                    # Vincular NFs
                    nfs_ref = cte_data.get('nfs_referenciadas', [])
                    self._vincular_nfs(operacao, nfs_ref, nf_map)

                    operacoes_criadas.append(operacao)
                except Exception as e:
                    logger.error(f"Erro ao criar operacao: {e}")
                    erros.append(
                        f"Erro ao criar operacao CTe {cte_data.get('cte_numero')}: {e}"
                    )

            # 4. Criar Subcontratos a partir dos CTes de transportadoras
            for cte_data in ctes_subcontrato:
                try:
                    sub = self._processar_cte_subcontrato(
                        cte_data, nf_map, operacoes_criadas, criado_por
                    )
                    if sub:
                        subcontratos_criados.append(sub)
                except Exception as e:
                    logger.warning(f"CTe Subcontrato ignorado: {e}")
                    erros.append(
                        f"CTe Subcontrato {cte_data.get('cte_numero')}: {e}"
                    )

            # 5. Criar Faturas a partir de PDFs parseados
            # Dedup: PDFs SSW podem ter paginas duplicadas (ex: fatura cancelada
            # + reimpressao com mesmo numero). Manter apenas 1 por numero_fatura,
            # preferindo a versao cancelada (tem mais info) ou a com maior valor.
            faturas_dedup = {}
            for fat_data in (faturas_data or []):
                num = fat_data.get('numero_fatura')
                if num and num in faturas_dedup:
                    existente = faturas_dedup[num]
                    # Preferir cancelada (tem contexto), ou maior valor
                    if fat_data.get('cancelada') and not existente.get('cancelada'):
                        faturas_dedup[num] = fat_data
                    elif (fat_data.get('valor_total') or 0) > (existente.get('valor_total') or 0):
                        if not existente.get('cancelada'):
                            faturas_dedup[num] = fat_data
                    logger.info(
                        f"Fatura duplicada detectada: {num} (mantendo "
                        f"{'cancelada' if faturas_dedup[num].get('cancelada') else 'maior valor'})"
                    )
                else:
                    faturas_dedup[num or f'_sem_num_{id(fat_data)}'] = fat_data

            for fat_data in faturas_dedup.values():
                try:
                    fatura = self._criar_fatura_de_pdf(fat_data, criado_por)
                    if fatura:
                        db.session.add(fatura)
                        db.session.flush()  # Obter ID

                        # Gravar itens de detalhe CTe (apenas para CarviaFaturaCliente)
                        if isinstance(fatura, CarviaFaturaCliente):
                            from app.carvia.services.linking_service import LinkingService
                            linker = LinkingService()

                            itens_detalhe = fat_data.get('itens_detalhe', [])
                            for item_data in itens_detalhe:
                                # Resolver FKs via linking
                                operacao_id = None
                                nf_id = None
                                cte_num = item_data.get('cte_numero')
                                nf_num = item_data.get('nf_numero')
                                cnpj_contraparte = item_data.get('contraparte_cnpj')

                                if cte_num:
                                    op = linker.resolver_operacao_por_cte(cte_num)
                                    if op:
                                        operacao_id = op.id
                                if nf_num:
                                    nf_obj = linker.resolver_nf_por_numero(
                                        nf_num, cnpj_contraparte
                                    )
                                    if nf_obj:
                                        nf_id = nf_obj.id

                                item = CarviaFaturaClienteItem(
                                    fatura_cliente_id=fatura.id,
                                    cte_numero=cte_num,
                                    cte_data_emissao=self._parsear_data_fatura(
                                        item_data.get('cte_data_emissao')
                                    ),
                                    contraparte_cnpj=cnpj_contraparte,
                                    contraparte_nome=item_data.get('contraparte_nome'),
                                    nf_numero=nf_num,
                                    operacao_id=operacao_id,
                                    nf_id=nf_id,
                                    valor_mercadoria=item_data.get('valor_mercadoria'),
                                    peso_kg=item_data.get('peso_kg'),
                                    base_calculo=item_data.get('base_calculo'),
                                    icms=item_data.get('icms'),
                                    iss=item_data.get('iss'),
                                    st=item_data.get('st'),
                                    frete=item_data.get('frete'),
                                )
                                db.session.add(item)

                        faturas_criadas.append(fatura)
                except Exception as e:
                    logger.error(f"Erro ao salvar fatura: {e}")
                    erros.append(
                        f"Erro ao salvar fatura "
                        f"{fat_data.get('numero_fatura', '?')}: {e}"
                    )

            # 6. Contar NFs sem CTe vinculado (para mensagem de feedback)
            nf_ids_vinculados = set()
            if nfs_criadas:
                for row in db.session.query(CarviaOperacaoNf.nf_id).filter(
                    CarviaOperacaoNf.nf_id.in_([nf.id for nf in nfs_criadas])
                ).all():
                    nf_ids_vinculados.add(row[0])
            nfs_sem_cte_count = len(nfs_criadas) - len(nf_ids_vinculados)

            db.session.commit()

            return {
                'sucesso': True,
                'nfs_criadas': len(nfs_criadas),
                'operacoes_criadas': len(operacoes_criadas),
                'subcontratos_criados': len(subcontratos_criados),
                'faturas_criadas': len(faturas_criadas),
                'nfs_sem_cte': nfs_sem_cte_count,
                'erros': erros,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro fatal na importacao: {e}")
            return {
                'sucesso': False,
                'nfs_criadas': 0,
                'operacoes_criadas': 0,
                'subcontratos_criados': 0,
                'faturas_criadas': 0,
                'erros': [f'Erro fatal: {e}'] + erros,
            }

    def _parsear_nfe_xml(self, conteudo: bytes, nome: str) -> Dict:
        """Parseia XML NF-e.

        Defesa em profundidade: alem de is_valid(), verifica is_nfe() (mod==55)
        para rejeitar CTe XML que possa ter sido classificado como NF-e.
        """
        parser = NFeXMLParser(conteudo)
        if not parser.is_valid():
            return {}
        if not parser.is_nfe():
            logger.warning(f"{nome}: XML valido mas nao e NF-e (modelo 55) — rejeitado")
            return {}
        dados = parser.get_todas_informacoes()
        dados['arquivo_nome_original'] = nome
        return dados

    def _parsear_cte_xml(self, conteudo: bytes, nome: str) -> Dict:
        """Parseia XML CTe"""
        parser = CTeXMLParserCarvia(conteudo)
        if parser.root is None:
            return {}
        dados = parser.get_todas_informacoes_carvia()
        dados['arquivo_nome_original'] = nome
        return dados

    def _parsear_danfe_pdf(self, conteudo: bytes, nome: str) -> Dict:
        """Parseia DANFE PDF"""
        parser = DanfePDFParser(pdf_bytes=conteudo)
        if not parser.is_valid():
            return {}
        dados = parser.get_todas_informacoes()
        dados['arquivo_nome_original'] = nome
        return dados

    def _parsear_fatura_pdf(self, conteudo: bytes, nome: str) -> List[Dict]:
        """Parseia fatura PDF (cliente ou transportadora).

        Usa FaturaPDFParser com 3 camadas: regex -> Haiku -> Sonnet.
        Suporte multi-pagina: formato SSW tem 1 fatura por pagina.

        Returns:
            List[Dict] — cada dict e uma fatura parseada. Lista vazia se invalido.
        """
        parser = FaturaPDFParser(pdf_bytes=conteudo)
        if not parser.is_valid():
            return []
        resultados = parser.parse_multi()
        if not resultados:
            return []
        for dados in resultados:
            dados['arquivo_nome_original'] = nome
        return resultados

    def _criar_fatura_de_pdf(self, fat_data: Dict, criado_por: str):
        """Cria CarviaFaturaCliente ou CarviaFaturaTransportadora a partir de dados parseados.

        Classificacao:
        - Se cnpj_emissor (beneficiario) bate com transportadora cadastrada
          -> CarviaFaturaTransportadora.
        - Caso contrario -> CarviaFaturaCliente (usa cnpj_pagador como cnpj_cliente).
        """
        numero = fat_data.get('numero_fatura')
        cnpj_emissor = fat_data.get('cnpj_emissor')
        cnpj_pagador = fat_data.get('cnpj_pagador')
        valor_str = fat_data.get('valor_total')
        data_emissao_str = fat_data.get('data_emissao')

        if not numero or not data_emissao_str:
            logger.warning(
                f"Fatura sem numero ou data — ignorada: {fat_data.get('arquivo_nome_original')}"
            )
            return None

        # Parsear data de emissao
        data_emissao = self._parsear_data_fatura(data_emissao_str)
        if not data_emissao:
            logger.warning(f"Fatura com data invalida '{data_emissao_str}' — ignorada")
            return None

        # Parsear valor total
        valor_total = 0.0
        if valor_str is not None:
            try:
                valor_total = float(valor_str)
            except (ValueError, TypeError):
                valor_total = 0.0

        # Parsear vencimento (opcional)
        vencimento = None
        venc_str = fat_data.get('vencimento')
        if venc_str:
            vencimento = self._parsear_data_fatura(venc_str)

        # Parsear vencimento original (opcional)
        vencimento_original = None
        venc_orig_str = fat_data.get('vencimento_original')
        if venc_orig_str:
            vencimento_original = self._parsear_data_fatura(venc_orig_str)

        # Classificar: transportadora ou cliente?
        # Usar cnpj_emissor (beneficiario) para classificacao
        transportadora = None
        if cnpj_emissor:
            cnpj_digitos = re.sub(r'\D', '', cnpj_emissor)
            if len(cnpj_digitos) >= 14:
                transportadora = self._encontrar_transportadora(cnpj_digitos)

        if transportadora:
            # Fatura de transportadora (subcontratado -> CarVia)
            fatura = CarviaFaturaTransportadora(
                transportadora_id=transportadora.id,
                numero_fatura=numero,
                data_emissao=data_emissao,
                valor_total=valor_total,
                vencimento=vencimento,
                arquivo_nome_original=fat_data.get('arquivo_nome_original'),
                status_conferencia='PENDENTE',
                criado_por=criado_por,
            )
            logger.info(
                f"Fatura transportadora criada: {numero} transp={transportadora.razao_social}"
            )
            return fatura

        # Fatura cliente (CarVia -> cliente)
        # FIX CRITICO: usar cnpj_pagador (cliente) — NAO cnpj_emissor (CarVia)
        cancelada = fat_data.get('cancelada', False)
        status = 'CANCELADA' if cancelada else 'PENDENTE'

        # Helper para truncar strings aos limites do DB
        def _trunc(val, max_len):
            if val and isinstance(val, str) and len(val) > max_len:
                return val[:max_len]
            return val

        fatura = CarviaFaturaCliente(
            cnpj_cliente=cnpj_pagador or 'DESCONHECIDO',
            nome_cliente=_trunc(
                fat_data.get('nome_pagador') or fat_data.get('nome_emissor'), 255
            ),
            numero_fatura=numero,
            data_emissao=data_emissao,
            valor_total=valor_total,
            vencimento=vencimento,
            arquivo_nome_original=fat_data.get('arquivo_nome_original'),
            # Campos SSW adicionais
            tipo_frete=fat_data.get('tipo_frete'),
            quantidade_documentos=fat_data.get('quantidade_documentos'),
            valor_mercadoria=fat_data.get('valor_mercadoria'),
            valor_icms=fat_data.get('valor_icms'),
            aliquota_icms=fat_data.get('aliquota_icms'),
            valor_pedagio=fat_data.get('valor_pedagio'),
            vencimento_original=vencimento_original,
            cancelada=cancelada,
            pagador_endereco=_trunc(fat_data.get('pagador_endereco'), 500),
            pagador_cep=_trunc(fat_data.get('pagador_cep'), 10),
            pagador_cidade=_trunc(fat_data.get('pagador_cidade'), 100),
            pagador_uf=_trunc(fat_data.get('pagador_uf'), 2),
            pagador_ie=_trunc(fat_data.get('pagador_ie'), 20),
            pagador_telefone=_trunc(fat_data.get('pagador_telefone'), 30),
            status=status,
            criado_por=criado_por,
        )
        logger.info(
            f"Fatura cliente criada: {numero} cnpj_pagador={cnpj_pagador} "
            f"cancelada={cancelada} tipo_frete={fat_data.get('tipo_frete')}"
        )
        return fatura

    def _parsear_data_fatura(self, data_str):
        """Parseia data de fatura (DD/MM/YYYY ou date object)"""
        if not data_str:
            return None
        if hasattr(data_str, 'date'):
            return data_str.date()
        if hasattr(data_str, 'year'):
            return data_str
        try:
            clean = str(data_str).replace('-', '/').replace('.', '/')
            return datetime.strptime(clean, '%d/%m/%Y').date()
        except (ValueError, TypeError):
            logger.warning(f"Erro ao parsear data fatura '{data_str}'")
            return None

    def _criar_nf(self, data: Dict, criado_por: str) -> CarviaNf:
        """Cria registro CarviaNf a partir de dados parseados"""
        data_emissao = data.get('data_emissao')
        if data_emissao and hasattr(data_emissao, 'date'):
            data_emissao = data_emissao.date()

        nf = CarviaNf(
            numero_nf=data.get('numero_nf') or '0',
            serie_nf=data.get('serie_nf'),
            chave_acesso_nf=data.get('chave_acesso_nf'),
            data_emissao=data_emissao,
            cnpj_emitente=data.get('cnpj_emitente') or 'DESCONHECIDO',
            nome_emitente=data.get('nome_emitente'),
            uf_emitente=data.get('uf_emitente'),
            cidade_emitente=data.get('cidade_emitente'),
            cnpj_destinatario=data.get('cnpj_destinatario'),
            nome_destinatario=data.get('nome_destinatario'),
            uf_destinatario=data.get('uf_destinatario'),
            cidade_destinatario=data.get('cidade_destinatario'),
            valor_total=data.get('valor_total'),
            peso_bruto=data.get('peso_bruto'),
            peso_liquido=data.get('peso_liquido'),
            quantidade_volumes=data.get('quantidade_volumes'),
            arquivo_nome_original=data.get('arquivo_nome_original'),
            tipo_fonte=data.get('tipo_fonte', 'MANUAL'),
            criado_por=criado_por,
        )

        # Itens de produto (armazenar para gravar apos flush da NF)
        nf._itens_pendentes = data.get('itens', [])
        return nf

    def _criar_operacao_de_cte(self, cte_data: Dict, nf_map: Dict,
                                criado_por: str) -> CarviaOperacao:
        """Cria CarviaOperacao a partir de dados de CTe"""
        # Calcular peso e valor das NFs referenciadas
        peso_total = 0.0
        valor_total = 0.0
        nfs_ref = cte_data.get('nfs_referenciadas', [])
        for nf_ref in nfs_ref:
            chave = nf_ref.get('chave')
            nf = nf_map.get(chave) if chave else None
            if nf is None and nf_ref.get('cnpj_emitente') and nf_ref.get('numero_nf'):
                nf = nf_map.get((nf_ref['cnpj_emitente'], nf_ref['numero_nf']))
            # Fallback: buscar no banco
            if nf is None:
                nf = self._buscar_nf_no_banco(nf_ref)
                if nf and chave:
                    nf_map[chave] = nf
            if nf and isinstance(nf, CarviaNf):
                peso_total += float(nf.peso_bruto or 0)
                valor_total += float(nf.valor_total or 0)

        # Usar dados do CTe para peso/valor se NFs nao resolveram
        if peso_total == 0:
            peso_total = float(cte_data.get('peso_bruto') or 0)
        if valor_total == 0:
            valor_total = float(cte_data.get('valor_mercadoria') or 0)

        rem = cte_data.get('remetente', {})

        return CarviaOperacao(
            cte_numero=cte_data.get('cte_numero'),
            cte_chave_acesso=cte_data.get('cte_chave_acesso'),
            cte_valor=cte_data.get('cte_valor'),
            cte_xml_nome_arquivo=cte_data.get('arquivo_nome_original'),
            cte_data_emissao=self._parsear_data_cte(cte_data.get('cte_data_emissao')),
            cnpj_cliente=rem.get('cnpj') or 'DESCONHECIDO',
            nome_cliente=rem.get('nome'),
            uf_origem=cte_data.get('uf_origem'),
            cidade_origem=cte_data.get('cidade_origem'),
            uf_destino=cte_data.get('uf_destino') or 'XX',
            cidade_destino=cte_data.get('cidade_destino') or 'DESCONHECIDO',
            peso_bruto=peso_total if peso_total > 0 else None,
            peso_utilizado=peso_total if peso_total > 0 else None,
            valor_mercadoria=valor_total if valor_total > 0 else None,
            tipo_entrada='IMPORTADO',
            status='RASCUNHO',
            criado_por=criado_por,
        )

    def _vincular_nfs(self, operacao: CarviaOperacao, nfs_ref: List[Dict],
                      nf_map: Dict):
        """Vincula NFs a uma operacao via junction table.

        Busca NFs primeiro no nf_map (batch atual), depois no banco de dados
        (NFs importadas em batches anteriores).
        """
        for nf_ref in nfs_ref:
            chave = nf_ref.get('chave')
            nf = nf_map.get(chave) if chave else None
            if nf is None and nf_ref.get('cnpj_emitente') and nf_ref.get('numero_nf'):
                nf = nf_map.get((nf_ref['cnpj_emitente'], nf_ref['numero_nf']))

            # Fallback: buscar NF existente no banco (importada em batch anterior)
            if nf is None:
                nf = self._buscar_nf_no_banco(nf_ref)
                if nf:
                    # Adicionar ao nf_map para evitar lookups repetidos
                    if chave:
                        nf_map[chave] = nf
                    logger.info(
                        f"NF encontrada no banco (batch anterior): "
                        f"nf_id={nf.id} chave={chave}"
                    )

            if nf and isinstance(nf, CarviaNf):
                # Verificar se junction ja existe (evitar duplicata)
                existing = db.session.query(CarviaOperacaoNf).filter_by(
                    operacao_id=operacao.id,
                    nf_id=nf.id,
                ).first()
                if not existing:
                    junction = CarviaOperacaoNf(
                        operacao_id=operacao.id,
                        nf_id=nf.id,
                    )
                    db.session.add(junction)
                    logger.info(
                        f"NF vinculada: op={operacao.id} nf={nf.id} "
                        f"chave={chave}"
                    )
            else:
                logger.warning(
                    f"NF referenciada nao encontrada: "
                    f"chave={chave} cnpj={nf_ref.get('cnpj_emitente')} "
                    f"numero={nf_ref.get('numero_nf')}"
                )

    def _buscar_nf_no_banco(self, nf_ref: Dict):
        """Busca NF existente no banco por chave de acesso ou CNPJ+numero.

        Usado como fallback quando a NF nao esta no nf_map (batch atual),
        mas pode ter sido importada em um batch anterior.
        """
        # 1. Busca por chave de acesso (mais confiavel)
        chave = nf_ref.get('chave')
        if chave:
            nf = CarviaNf.query.filter_by(chave_acesso_nf=chave).first()
            if nf:
                return nf

        # 2. Fallback: CNPJ + numero
        cnpj = nf_ref.get('cnpj_emitente')
        numero = nf_ref.get('numero_nf')
        if cnpj and numero:
            nf = CarviaNf.query.filter_by(
                cnpj_emitente=cnpj,
                numero_nf=numero,
            ).first()
            if nf:
                return nf

        return None

    # ------------------------------------------------------------------
    # CTe Subcontrato — metodos auxiliares
    # ------------------------------------------------------------------

    def _parsear_data_cte(self, dt_str):
        """Parseia string datetime ISO do CTe para date object.

        Input: '2025-10-22T16:49:56-04:00' (ISO com timezone)
        Output: date(2025, 10, 22)
        """
        if not dt_str:
            return None
        try:
            clean = dt_str
            # Remover timezone offset (+03:00 ou -04:00)
            if '+' in clean:
                clean = clean.split('+')[0]
            elif clean.count('-') > 2:
                parts = clean.rsplit('-', 1)
                if ':' in parts[-1]:
                    clean = parts[0]
            return datetime.fromisoformat(clean).date()
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao parsear data CTe '{dt_str}': {e}")
            return None

    def _processar_cte_subcontrato(self, cte_data: Dict, nf_map: Dict,
                                    operacoes_criadas: List,
                                    criado_por: str):
        """Cria CarviaSubcontrato a partir de CTe de transportadora subcontratada.

        Vincula ao CTe CarVia (CarviaOperacao) que referencia as mesmas NFs.
        """
        # 1. Encontrar operacao pai via NFs compartilhadas
        operacao = self._encontrar_operacao_por_nfs(
            cte_data, nf_map, operacoes_criadas
        )
        if not operacao:
            # Tentar buscar operacao existente no banco
            operacao = self._buscar_operacao_existente_por_nfs(cte_data)

        if not operacao:
            raise ValueError(
                f"CTe Subcontrato {cte_data.get('cte_numero', '?')} — "
                f"nao encontrou CTe CarVia correspondente. "
                f"Importe primeiro o CTe CarVia que referencia as mesmas NFs, "
                f"ou crie o CTe Subcontrato manualmente."
            )

        # 2. Encontrar transportadora por CNPJ emitente
        emit = cte_data.get('emitente', {})
        cnpj_emit = re.sub(r'\D', '', emit.get('cnpj') or '')
        transportadora = self._encontrar_transportadora(cnpj_emit)

        if not transportadora:
            raise ValueError(
                f"transportadora CNPJ {cnpj_emit} nao cadastrada"
            )

        # 3. Gerar numero sequencial por transportadora
        max_seq = db.session.query(
            db.func.max(CarviaSubcontrato.numero_sequencial_transportadora)
        ).filter(
            CarviaSubcontrato.transportadora_id == transportadora.id,
        ).scalar() or 0

        # 4. Criar subcontrato
        sub = CarviaSubcontrato(
            operacao_id=operacao.id,
            transportadora_id=transportadora.id,
            numero_sequencial_transportadora=max_seq + 1,
            cte_numero=cte_data.get('cte_numero'),
            cte_chave_acesso=cte_data.get('cte_chave_acesso'),
            cte_valor=cte_data.get('cte_valor'),
            cte_xml_nome_arquivo=cte_data.get('arquivo_nome_original'),
            cte_data_emissao=self._parsear_data_cte(
                cte_data.get('cte_data_emissao')
            ),
            valor_cotado=cte_data.get('cte_valor'),
            status='COTADO',
            criado_por=criado_por,
        )
        db.session.add(sub)
        db.session.flush()

        logger.info(
            f"CTe Subcontrato criado: sub={sub.id} op={operacao.id} "
            f"transp={transportadora.razao_social} cte={cte_data.get('cte_numero')}"
        )
        return sub

    def _encontrar_operacao_por_nfs(self, cte_data: Dict, nf_map: Dict,
                                     operacoes_criadas: List):
        """Encontra operacao recem-criada que compartilha NFs referenciadas."""
        nfs_ref = cte_data.get('nfs_referenciadas', [])
        if not nfs_ref:
            return None

        # Coletar IDs das NFs referenciadas pelo CTe Subcontrato
        nf_ids = set()
        for nf_ref in nfs_ref:
            chave = nf_ref.get('chave')
            nf = nf_map.get(chave) if chave else None
            if nf is None and nf_ref.get('cnpj_emitente') and nf_ref.get('numero_nf'):
                nf = nf_map.get((nf_ref['cnpj_emitente'], nf_ref['numero_nf']))
            # Fallback: buscar no banco
            if nf is None:
                nf = self._buscar_nf_no_banco(nf_ref)
                if nf and chave:
                    nf_map[chave] = nf
            if nf and isinstance(nf, CarviaNf):
                nf_ids.add(nf.id)

        if not nf_ids:
            return None

        # Comparar com NFs de cada operacao recem-criada
        for op in operacoes_criadas:
            junctions = db.session.query(CarviaOperacaoNf).filter(
                CarviaOperacaoNf.operacao_id == op.id
            ).all()
            op_nf_ids = {j.nf_id for j in junctions}
            if nf_ids & op_nf_ids:  # Intersecao nao-vazia
                return op

        return None

    def _buscar_operacao_existente_por_nfs(self, cte_data: Dict):
        """Busca operacao existente no banco por NFs referenciadas (chave de acesso)."""
        nfs_ref = cte_data.get('nfs_referenciadas', [])
        for nf_ref in nfs_ref:
            chave = nf_ref.get('chave')
            if chave:
                nf_existente = CarviaNf.query.filter_by(
                    chave_acesso_nf=chave
                ).first()
                if nf_existente:
                    junction = CarviaOperacaoNf.query.filter_by(
                        nf_id=nf_existente.id
                    ).first()
                    if junction:
                        return CarviaOperacao.query.get(junction.operacao_id)
        return None

    def _encontrar_transportadora(self, cnpj_digits: str):
        """Encontra transportadora cadastrada por CNPJ (apenas digitos)."""
        if not cnpj_digits or len(cnpj_digits) < 14:
            return None

        from app.transportadoras.models import Transportadora

        # Buscar comparando apenas digitos do CNPJ armazenado
        return Transportadora.query.filter(
            db.func.regexp_replace(
                Transportadora.cnpj, '[^0-9]', '', 'g'
            ) == cnpj_digits
        ).first()
