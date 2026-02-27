"""
Importacao Service — Orquestrador do fluxo de importacao
=========================================================

Fluxo:
1. Recebe arquivos (PDFs + XMLs)
2. Classifica cada arquivo (NF-e XML, CTe XML, DANFE PDF)
3. Parseia todos os arquivos
4. Classifica CTes por CNPJ emitente (CarVia vs Subcontratado)
5. Executa matching CTe CarVia <-> NF
6. Cria registros no banco:
   - CarviaNf + CarviaNfItem (NFs de mercadoria)
   - CarviaOperacao + junction (CTe CarVia)
   - CarviaSubcontrato (CTe Subcontratado, vinculado via NFs compartilhadas)
"""

import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple

from app import db
from app.carvia.models import (
    CarviaNf, CarviaNfItem, CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato
)
from app.carvia.services.nfe_xml_parser import NFeXMLParser
from app.carvia.services.cte_xml_parser_carvia import CTeXMLParserCarvia
from app.carvia.services.danfe_pdf_parser import DanfePDFParser
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
        subcontratos_criados = []
        erros = []

        try:
            # 1. Salvar NFs e seus itens
            nf_map = {}  # chave/numero -> CarviaNf
            for nf_data in nfs_data:
                try:
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

            # 2. Separar CTes por classificacao
            ctes_carvia = [c for c in ctes_data
                           if c.get('classificacao') != 'CTE_SUBCONTRATO']
            ctes_subcontrato = [c for c in ctes_data
                                if c.get('classificacao') == 'CTE_SUBCONTRATO']

            # 3. Criar Operacoes a partir dos CTes CarVia
            for cte_data in ctes_carvia:
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

            # 5. NFs sem CTe -> operacoes avulsas (1 por NF)
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
                'subcontratos_criados': len(subcontratos_criados),
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
                f"nao encontrou CTe CarVia vinculado via NFs referenciadas"
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
            nf = nf_map.get(nf_ref.get('chave'))
            if nf is None and nf_ref.get('cnpj_emitente') and nf_ref.get('numero_nf'):
                nf = nf_map.get((nf_ref['cnpj_emitente'], nf_ref['numero_nf']))
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
