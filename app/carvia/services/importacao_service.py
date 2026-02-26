"""
Importacao Service — Orquestrador do fluxo de importacao
=========================================================

Fluxo:
1. Recebe arquivos (PDFs + XMLs)
2. Classifica cada arquivo (NF-e XML, CTe XML, DANFE PDF)
3. Parseia todos os arquivos
4. Executa matching CTe <-> NF
5. Cria registros no banco (CarviaNf + CarviaOperacao + junction)
"""

import logging
import os
from typing import Dict, List, Tuple

from app import db
from app.carvia.models import CarviaNf, CarviaOperacao, CarviaOperacaoNf
from app.carvia.services.nfe_xml_parser import NFeXMLParser
from app.carvia.services.cte_xml_parser_carvia import CTeXMLParserCarvia
from app.carvia.services.danfe_pdf_parser import DanfePDFParser
from app.carvia.services.matching_service import MatchingService
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class ImportacaoService:
    """Orquestrador do fluxo de importacao de NFs e CTes"""

    def __init__(self):
        self.matching = MatchingService()

    def classificar_arquivo(self, nome_arquivo: str, conteudo: bytes) -> str:
        """
        Classifica o tipo de arquivo.

        Returns:
            'XML_NFE', 'XML_CTE', 'PDF_DANFE', 'DESCONHECIDO'
        """
        ext = os.path.splitext(nome_arquivo)[1].lower()

        if ext == '.pdf':
            return 'PDF_DANFE'

        if ext == '.xml':
            return self._classificar_xml(conteudo)

        return 'DESCONHECIDO'

    def _classificar_xml(self, conteudo: bytes) -> str:
        """Classifica XML como NF-e ou CTe"""
        try:
            texto = conteudo.decode('utf-8', errors='replace')[:2000]
            texto_lower = texto.lower()

            if 'cteproc' in texto_lower or '<cte' in texto_lower or 'infcte' in texto_lower:
                return 'XML_CTE'
            elif 'nfeproc' in texto_lower or '<nfe' in texto_lower or 'infnfe' in texto_lower:
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
            - matches: resultado do matching
            - erros: lista de erros
        """
        nfs_parseadas = []
        ctes_parseados = []
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

                else:
                    erros.append(f'{nome}: Tipo de arquivo nao reconhecido')

            except Exception as e:
                logger.error(f"Erro ao processar {nome}: {e}")
                erros.append(f'{nome}: Erro ao processar - {str(e)}')

        # Matching
        matches = {}
        if ctes_parseados and nfs_parseadas:
            matches = self.matching.match_multiplos_ctes(ctes_parseados, nfs_parseadas)

        return {
            'nfs_parseadas': nfs_parseadas,
            'ctes_parseados': ctes_parseados,
            'matches': {k: [m.to_dict() for m in v] for k, v in matches.items()},
            'erros': erros,
        }

    def salvar_importacao(self, nfs_data: List[Dict], ctes_data: List[Dict],
                          matches: Dict, criado_por: str) -> Dict:
        """
        Salva os dados processados no banco de dados.

        Args:
            nfs_data: Lista de dicts com dados das NFs
            ctes_data: Lista de dicts com dados dos CTes
            matches: Resultado do matching (cte_key -> lista de match results)
            criado_por: Email do usuario

        Returns:
            Dict com ids criados e estatisticas
        """
        nfs_criadas = []
        operacoes_criadas = []
        erros = []

        try:
            # 1. Salvar NFs
            nf_map = {}  # chave/numero -> CarviaNf
            for nf_data in nfs_data:
                try:
                    nf = self._criar_nf(nf_data, criado_por)
                    db.session.add(nf)
                    db.session.flush()  # Obter ID

                    chave = nf_data.get('chave_acesso_nf')
                    numero = nf_data.get('numero_nf')
                    cnpj = nf_data.get('cnpj_emitente')

                    if chave:
                        nf_map[chave] = nf
                    if numero and cnpj:
                        nf_map[(cnpj, numero)] = nf

                    nfs_criadas.append(nf)
                except Exception as e:
                    logger.error(f"Erro ao salvar NF: {e}")
                    erros.append(f"Erro ao salvar NF {nf_data.get('numero_nf')}: {e}")

            # 2. Criar Operacoes a partir dos CTes
            for cte_data in ctes_data:
                try:
                    operacao = self._criar_operacao_de_cte(cte_data, nf_map, criado_por)
                    db.session.add(operacao)
                    db.session.flush()

                    # Vincular NFs
                    nfs_ref = cte_data.get('nfs_referenciadas', [])
                    self._vincular_nfs(operacao, nfs_ref, nf_map)

                    operacoes_criadas.append(operacao)
                except Exception as e:
                    logger.error(f"Erro ao criar operacao: {e}")
                    erros.append(f"Erro ao criar operacao CTe {cte_data.get('cte_numero')}: {e}")

            # 3. NFs sem CTe -> operacoes avulsas (1 por NF)
            nfs_sem_cte = self._encontrar_nfs_sem_operacao(nfs_criadas, operacoes_criadas)
            for nf in nfs_sem_cte:
                try:
                    operacao = self._criar_operacao_de_nf(nf, criado_por)
                    db.session.add(operacao)
                    db.session.flush()

                    junction = CarviaOperacaoNf(
                        operacao_id=operacao.id,
                        nf_id=nf.id,
                    )
                    db.session.add(junction)
                    operacoes_criadas.append(operacao)
                except Exception as e:
                    logger.error(f"Erro ao criar operacao avulsa: {e}")
                    erros.append(f"Erro ao criar operacao para NF {nf.numero_nf}: {e}")

            db.session.commit()

            return {
                'sucesso': True,
                'nfs_criadas': len(nfs_criadas),
                'operacoes_criadas': len(operacoes_criadas),
                'erros': erros,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro fatal na importacao: {e}")
            return {
                'sucesso': False,
                'nfs_criadas': 0,
                'operacoes_criadas': 0,
                'erros': [f'Erro fatal: {e}'] + erros,
            }

    def _parsear_nfe_xml(self, conteudo: bytes, nome: str) -> Dict:
        """Parseia XML NF-e"""
        parser = NFeXMLParser(conteudo)
        if not parser.is_valid():
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

    def _criar_nf(self, data: Dict, criado_por: str) -> CarviaNf:
        """Cria registro CarviaNf a partir de dados parseados"""
        data_emissao = data.get('data_emissao')
        if data_emissao and hasattr(data_emissao, 'date'):
            data_emissao = data_emissao.date()

        return CarviaNf(
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

    def _criar_operacao_de_cte(self, cte_data: Dict, nf_map: Dict,
                                criado_por: str) -> CarviaOperacao:
        """Cria CarviaOperacao a partir de dados de CTe"""
        # Calcular peso e valor das NFs referenciadas
        peso_total = 0.0
        valor_total = 0.0
        nfs_ref = cte_data.get('nfs_referenciadas', [])
        for nf_ref in nfs_ref:
            nf = nf_map.get(nf_ref.get('chave'))
            if nf is None and nf_ref.get('cnpj_emitente') and nf_ref.get('numero_nf'):
                nf = nf_map.get((nf_ref['cnpj_emitente'], nf_ref['numero_nf']))
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
            cte_data_emissao=None,  # Requer parsing de datetime string
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

    def _criar_operacao_de_nf(self, nf: CarviaNf, criado_por: str) -> CarviaOperacao:
        """Cria operacao avulsa para NF sem CTe"""
        return CarviaOperacao(
            cnpj_cliente=nf.cnpj_emitente,
            nome_cliente=nf.nome_emitente,
            uf_origem=nf.uf_emitente,
            cidade_origem=nf.cidade_emitente,
            uf_destino=nf.uf_destinatario or 'XX',
            cidade_destino=nf.cidade_destinatario or 'DESCONHECIDO',
            peso_bruto=nf.peso_bruto,
            peso_utilizado=nf.peso_bruto,
            valor_mercadoria=nf.valor_total,
            tipo_entrada='IMPORTADO',
            status='RASCUNHO',
            criado_por=criado_por,
        )

    def _vincular_nfs(self, operacao: CarviaOperacao, nfs_ref: List[Dict],
                      nf_map: Dict):
        """Vincula NFs a uma operacao via junction table"""
        for nf_ref in nfs_ref:
            nf = nf_map.get(nf_ref.get('chave'))
            if nf is None and nf_ref.get('cnpj_emitente') and nf_ref.get('numero_nf'):
                nf = nf_map.get((nf_ref['cnpj_emitente'], nf_ref['numero_nf']))

            if nf and isinstance(nf, CarviaNf):
                junction = CarviaOperacaoNf(
                    operacao_id=operacao.id,
                    nf_id=nf.id,
                )
                db.session.add(junction)

    def _encontrar_nfs_sem_operacao(self, nfs_criadas: List[CarviaNf],
                                     operacoes_criadas: List[CarviaOperacao]) -> List[CarviaNf]:
        """Encontra NFs que nao foram vinculadas a nenhuma operacao"""
        # IDs de NFs ja vinculadas
        nf_ids_vinculados = set()
        for op in operacoes_criadas:
            junctions = db.session.query(CarviaOperacaoNf).filter(
                CarviaOperacaoNf.operacao_id == op.id
            ).all()
            for j in junctions:
                nf_ids_vinculados.add(j.nf_id)

        return [nf for nf in nfs_criadas if nf.id not in nf_ids_vinculados]
