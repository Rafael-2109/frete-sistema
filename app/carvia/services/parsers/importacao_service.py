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
   - CarviaCteComplementar (CTe Complementar, vinculado ao CTe original)
   - CarviaSubcontrato (CTe Subcontratado, vinculado via NFs compartilhadas)
   - CarviaFaturaCliente ou CarviaFaturaTransportadora (faturas PDF)
"""

import logging
import os
import re
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app import db
from sqlalchemy.exc import IntegrityError
from app.carvia.models import (
    CarviaNf, CarviaNfItem, CarviaNfVeiculo,
    CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato,
    CarviaFaturaCliente, CarviaFaturaClienteItem, CarviaFaturaTransportadora,
    CarviaCteComplementar
)
from app.carvia.services.parsers.nfe_xml_parser import NFeXMLParser
from app.carvia.services.parsers.cte_xml_parser_carvia import CTeXMLParserCarvia
from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser
from app.carvia.services.parsers.fatura_pdf_parser import FaturaPDFParser
from app.carvia.services.documentos.matching_service import MatchingService

# CNPJ da CarVia para classificacao de CTes
CARVIA_CNPJ = re.sub(r'\D', '', os.environ.get('CARVIA_CNPJ', ''))

# Mapeamento SEFAZ toma3/toma4 -> enum persistido em CarviaOperacao.cte_tomador
_TOMADOR_CODE_MAP = {
    '0': 'REMETENTE',
    '1': 'EXPEDIDOR',
    '2': 'RECEBEDOR',
    '3': 'DESTINATARIO',
    '4': 'TERCEIRO',
}

logger = logging.getLogger(__name__)

if not CARVIA_CNPJ:
    logger.warning(
        "CARVIA_CNPJ nao configurada — classificacao CTE_CARVIA/CTE_SUBCONTRATO desativada"
    )


class ImportacaoService:
    """Orquestrador do fluxo de importacao de NFs e CTes"""

    def __init__(self):
        self.matching = MatchingService()

    def _salvar_arquivo_storage(self, conteudo: bytes, nome: str,
                                 pasta: str) -> Optional[str]:
        """Salva arquivo no S3/local e retorna path. Best-effort: nao bloqueia import se falhar.

        Args:
            conteudo: Bytes do arquivo original
            nome: Nome original do arquivo (ex: 'nfe_12345.xml')
            pasta: Pasta de destino (ex: 'carvia/nfs_xml')

        Returns:
            Path (string) do arquivo salvo, ou None se falhar
        """
        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            buf = BytesIO(conteudo)
            buf.name = nome  # Necessario para deteccao de MIME type
            path = storage.save_file(file=buf, folder=pasta)
            if path:
                logger.info(f"Arquivo salvo no storage: {pasta}/{nome} -> {path}")
            return path
        except Exception as e:
            logger.warning(f"Falha ao salvar arquivo no storage (best-effort): {nome} -> {e}")
            return None

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

    def _is_dacte_pdf(self, conteudo: bytes) -> bool:
        """Verifica se um PDF e DACTE (CTe) e nao DANFE (NF-e).

        Usa DanfePDFParser apenas para extrair texto, depois verifica
        marcadores DACTE: texto "DACTE"/"Conhecimento de Transporte"
        ou modelo 57 na chave de 44 digitos.
        """
        danfe = DanfePDFParser(pdf_bytes=conteudo)
        if not danfe.is_valid():
            return False

        upper = danfe.texto_completo.upper()

        # Marcadores textuais DACTE
        if 'D A C T E' in upper or 'DACTE' in upper:
            return True
        if 'CONHECIMENTO DE TRANSPORTE' in upper:
            return True

        # Chave com modelo 57 (CTe)
        texto_limpo = re.sub(r'[.\-/\s]', '', danfe.texto_completo)
        chaves = re.findall(r'\d{44}', texto_limpo)
        for chave in chaves:
            if chave[20:22] == '57':
                return True

        return False

    def _classificar_pdf(self, conteudo: bytes) -> str:
        """Classifica PDF: DACTE (CTe) vs DANFE (NF-e) vs Fatura (fallback).

        Ordem de verificacao:
        1. DACTE: texto "DACTE"/"Conhecimento de Transporte" ou modelo 57 na chave
        2. DANFE: chave 44 digitos com modelo != 57
        3. DANFE (fallback): marcadores textuais "DANFE"/"NOTA FISCAL ELETRONICA"
           — protege contra falha na extracao de chave (ex: PDFs de 2+ paginas
           onde pdfplumber quebra a chave em linhas diferentes)
        4. Fatura: fallback final
        """
        # 1. DACTE primeiro — DACTEs tambem tem chaves de 44 digitos
        if self._is_dacte_pdf(conteudo):
            return 'PDF_DACTE'

        # 2. DANFE: chave 44 digitos (modelo 55)
        danfe = DanfePDFParser(pdf_bytes=conteudo)
        if danfe.is_valid():
            chave = danfe.get_chave_acesso()
            if chave and len(chave) == 44:
                return 'PDF_DANFE'

            # 3. DANFE (fallback textual): se chave nao foi extraida, verificar
            #    marcadores textuais que identificam inequivocamente um DANFE.
            #    Isso cobre PDFs multi-pagina onde pdfplumber fragmenta a chave.
            upper = danfe.texto_completo.upper()
            danfe_markers = (
                'DANFE' in upper
                and 'DOCUMENTO AUXILIAR' in upper
                and 'NOTA FISCAL' in upper
            )
            if danfe_markers:
                logger.info(
                    "PDF classificado como DANFE via marcadores textuais "
                    "(chave nao extraida)"
                )
                return 'PDF_DANFE'

        # 4. Fallback final: Fatura
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
                        dados['arquivo_xml_path'] = self._salvar_arquivo_storage(
                            conteudo, nome, 'carvia/nfs_xml'
                        )
                        nfs_parseadas.append(dados)
                    else:
                        erros.append(f'{nome}: Nao foi possivel extrair dados da NF-e XML')

                elif tipo == 'XML_CTE':
                    dados = self._parsear_cte_xml(conteudo, nome)
                    if dados:
                        dados['cte_xml_path'] = self._salvar_arquivo_storage(
                            conteudo, nome, 'carvia/ctes_xml'
                        )
                        ctes_parseados.append(dados)
                    else:
                        erros.append(f'{nome}: Nao foi possivel extrair dados do CTe XML')

                elif tipo == 'PDF_DACTE':
                    dados = self._parsear_dacte_pdf(conteudo, nome)
                    if dados:
                        pdf_path = self._salvar_arquivo_storage(
                            conteudo, nome, 'carvia/ctes_pdf'
                        )
                        dados['cte_pdf_path'] = pdf_path
                        ctes_parseados.append(dados)
                    else:
                        erros.append(f'{nome}: Nao foi possivel extrair dados do DACTE PDF')

                elif tipo == 'PDF_DANFE':
                    dados = self._parsear_danfe_pdf(conteudo, nome)
                    if dados:
                        dados['arquivo_pdf_path'] = self._salvar_arquivo_storage(
                            conteudo, nome, 'carvia/nfs_pdf'
                        )
                        nfs_parseadas.append(dados)
                    else:
                        erros.append(f'{nome}: Nao foi possivel extrair dados do DANFE PDF')

                elif tipo == 'PDF_FATURA':
                    dados_lista = self._parsear_fatura_pdf(conteudo, nome)
                    if dados_lista:
                        # PDF multi-pagina: salvar UMA vez, atribuir MESMO path a TODAS as faturas
                        pdf_path = self._salvar_arquivo_storage(
                            conteudo, nome, 'carvia/faturas_pdf'
                        )
                        for dados_fat in dados_lista:
                            dados_fat['arquivo_pdf_path'] = pdf_path
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
            if ctes_parseados:
                erros.append(
                    'AVISO: CARVIA_CNPJ nao configurada — todos os CTes foram '
                    'classificados como CTe CarVia. Configure a variavel de '
                    'ambiente CARVIA_CNPJ para separar CTes CarVia de Subcontratos.'
                )

        # Reclassificar CTes complementares (tpCTe=1) emitidos pela CarVia
        # CTe complementar NAO e uma operacao — e um acrescimo ao CTe original
        for cte in ctes_parseados:
            if (
                cte.get('tipo_cte') == '1'
                and cte.get('classificacao') == 'CTE_CARVIA'
            ):
                cte['classificacao'] = 'CTE_COMPLEMENTAR'
                logger.info(
                    "CTe %s reclassificado como COMPLEMENTAR (tpCTe=1)",
                    cte.get('cte_numero'),
                )

        # Pareamento DACTE PDF ↔ CTe Complementar XML pela chave de acesso
        # Quando o usuário sobe XML + DACTE do mesmo CTe Comp no mesmo upload,
        # o DACTE chega como entrada separada em ctes_parseados via _parsear_dacte_pdf.
        # Este loop transfere o cte_pdf_path do item DACTE para o item XML
        # complementar (mesma chave) e marca o DACTE para ser ignorado no salvar.
        for cte in ctes_parseados:
            if cte.get('classificacao') != 'CTE_COMPLEMENTAR':
                continue
            chave = cte.get('cte_chave_acesso')
            if not chave:
                continue
            # Procurar par DACTE pela mesma chave
            for outro in ctes_parseados:
                if outro is cte:
                    continue
                if outro.get('cte_chave_acesso') != chave:
                    continue
                if outro.get('cte_pdf_path') and not cte.get('cte_pdf_path'):
                    cte['cte_pdf_path'] = outro['cte_pdf_path']
                    cte['dacte_pareado'] = True
                    outro['_skip_save'] = True  # marca DACTE para pular no salvar
                    logger.info(
                        "DACTE pareado a CTe Comp %s pela chave %s",
                        cte.get('cte_numero'), chave[:20] + '...'
                    )
                    break

        # Calcular custos_entrega_candidatos para cada CTe Complementar
        # Permite que o preview (importar_resultado.html) mostre dropdown
        # com Custos Entrega disponíveis para vinculação manual.
        for cte in ctes_parseados:
            if cte.get('classificacao') != 'CTE_COMPLEMENTAR':
                continue
            info_comp = cte.get('info_complementar') or {}
            chave_pai = info_comp.get('chave_cte_original')
            if not chave_pai:
                cte['custos_entrega_candidatos'] = []
                continue
            try:
                op_pai = CarviaOperacao.query.filter_by(
                    cte_chave_acesso=chave_pai
                ).first()
                if not op_pai:
                    cte['custos_entrega_candidatos'] = []
                    cte['operacao_pai_nao_encontrada'] = True
                    continue
                cte['operacao_pai_id'] = op_pai.id
                cte['operacao_pai_ctrc_numero'] = op_pai.ctrc_numero
                from app.carvia.services.cte_complementar_persistencia import (
                    auto_match_custo_entrega,
                )
                candidatos = auto_match_custo_entrega(op_pai.id)
                cte['custos_entrega_candidatos'] = [
                    {
                        'id': c.id,
                        'numero_custo': c.numero_custo,
                        'tipo_custo': c.tipo_custo,
                        'valor': float(c.valor),
                        'status': c.status,
                    }
                    for c in candidatos
                ]
                # Auto-match: se houver UM ÚNICO candidato, pré-seleciona
                if len(candidatos) == 1:
                    cte['custo_entrega_id_selecionado'] = candidatos[0].id
            except Exception as e:
                logger.warning(
                    "Falha ao calcular custos_entrega_candidatos para CTe Comp "
                    "%s: %s", cte.get('cte_numero'), e
                )
                cte['custos_entrega_candidatos'] = []

        # Pre-check: verificar transportadoras para CTes subcontrato e faturas
        transportadoras_nao_encontradas = {}

        for cte in ctes_parseados:
            if cte.get('classificacao') != 'CTE_SUBCONTRATO':
                continue
            emit = cte.get('emitente', {})
            cnpj = re.sub(r'\D', '', emit.get('cnpj') or '')
            if not cnpj:
                continue
            if cnpj not in transportadoras_nao_encontradas:
                transp = self._encontrar_transportadora(cnpj)
                if transp:
                    cte['transportadora_encontrada'] = True
                    cte['transportadora_nome'] = transp.razao_social
                else:
                    cte['transportadora_encontrada'] = False
                    transportadoras_nao_encontradas[cnpj] = {
                        'cnpj': cnpj,
                        'nome': emit.get('nome', ''),
                        'uf': emit.get('uf', ''),
                        'cidade': emit.get('cidade', ''),
                        'fonte': 'CTE_SUBCONTRATO',
                    }
            else:
                cte['transportadora_encontrada'] = False

        # Pre-check: verificar transportadoras para faturas (beneficiario)
        for fat in faturas_parseadas:
            cnpj_emissor = fat.get('cnpj_emissor') or ''
            cnpj_digitos = re.sub(r'\D', '', cnpj_emissor)
            if len(cnpj_digitos) < 14:
                continue
            if cnpj_digitos == CARVIA_CNPJ:
                continue
            if cnpj_digitos in transportadoras_nao_encontradas:
                fat['transportadora_encontrada'] = False
            else:
                transp = self._encontrar_transportadora(cnpj_digitos)
                if transp:
                    fat['transportadora_encontrada'] = True
                    fat['transportadora_nome'] = transp.razao_social
                else:
                    fat['transportadora_encontrada'] = False
                    transportadoras_nao_encontradas[cnpj_digitos] = {
                        'cnpj': cnpj_digitos,
                        'nome': fat.get('nome_emissor', ''),
                        'uf': '',
                        'cidade': '',
                        'fonte': 'FATURA_BENEFICIARIO',
                    }

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
            'transportadoras_nao_encontradas': list(
                transportadoras_nao_encontradas.values()
            ),
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
        nfs_reutilizadas = []
        operacoes_criadas = []
        subcontratos_criados = []
        faturas_criadas = []
        erros = []

        try:
            # 1. Salvar NFs e seus itens (com deduplicacao)
            # W9: cada iteracao usa begin_nested() explicito envolvendo
            # TODO o trabalho (writes + side-effects). Exceptions nao
            # propagadas por try/except internos saem do `with` e o
            # SAVEPOINT e revertido automaticamente. As NFs anteriores
            # ja processadas com sucesso permanecem intactas na sessao.
            nf_map = {}  # chave/numero -> CarviaNf
            for nf_data in nfs_data:
                chave = nf_data.get('chave_acesso_nf')
                numero = nf_data.get('numero_nf')
                cnpj = nf_data.get('cnpj_emitente')

                # Tracking temporario — so e aplicado ao estado global
                # APOS o savepoint commitar com sucesso (ver pos-with abaixo).
                nf = None
                acao = None  # 'criada' | 'reutilizada'

                try:
                    with db.session.begin_nested():
                        # Verificar se NF ja existe no banco (evitar UNIQUE violation)
                        nf_existente = None
                        if chave:
                            nf_existente = CarviaNf.query.filter_by(
                                chave_acesso_nf=chave
                            ).first()

                        # Se nao encontrou por chave, buscar stub FATURA_REFERENCIA
                        # por numero+CNPJ (stub nao tem chave_acesso_nf)
                        if not nf_existente and numero and cnpj:
                            nf_existente = self._buscar_stub_fatura_referencia(
                                numero, cnpj
                            )

                        if nf_existente:
                            if nf_existente.status == 'CANCELADA':
                                # NF cancelada com mesma chave — reativar e
                                # atualizar com dados corretos do novo parse.
                                # Sem isso, NF cancelada com dados errados
                                # bloqueia re-importacao permanentemente.
                                self._atualizar_nf_existente(
                                    nf_existente, nf_data, criado_por
                                )
                                nf_existente.status = 'ATIVA'
                                nf_existente.cancelado_em = None
                                nf_existente.cancelado_por = None
                                nf_existente.motivo_cancelamento = None
                                nf = nf_existente
                                acao = 'criada'
                                logger.info(
                                    f"NF cancelada reativada e atualizada: "
                                    f"nf_id={nf.id} chave={chave}"
                                )
                            elif nf_existente.tipo_fonte == 'FATURA_REFERENCIA':
                                # MERGE: promover stub com dados reais da NF
                                nf = self._merge_nf_sobre_stub(
                                    nf_existente, nf_data, criado_por
                                )
                                acao = 'criada'

                                # Re-linking retroativo: o stub nao tinha
                                # chave_acesso_nf, agora a NF real tem — pode
                                # gerar novas junctions via nfs_referenciadas_json
                                try:
                                    from app.carvia.services.documentos.linking_service import LinkingService
                                    linker = LinkingService()
                                    junc_count = linker.vincular_nf_a_operacoes_orfas(nf)
                                    if junc_count > 0:
                                        logger.info(
                                            f"Re-linking (stub promovido) NF→CTe: "
                                            f"NF {nf.id} vinculada a {junc_count} "
                                            f"operacao(oes)"
                                        )
                                except Exception as e_link:
                                    logger.warning(
                                        f"Erro no re-linking do stub promovido "
                                        f"NF {nf.id}: {e_link}"
                                    )
                            else:
                                logger.info(
                                    f"NF ja importada (reutilizando): "
                                    f"nf_id={nf_existente.id} chave={chave}"
                                )
                                nf = nf_existente
                                acao = 'reutilizada'
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

                            # Gravar veiculos (chassi/modelo/cor) extraidos do DANFE/XML
                            veiculos_pendentes = getattr(nf, '_veiculos_pendentes', [])
                            veic_inseridos = 0
                            for v_data in veiculos_pendentes:
                                chassi_v = (v_data.get('chassi') or '').strip()
                                if not chassi_v:
                                    continue
                                # Dedup: chassi UNIQUE
                                existente = CarviaNfVeiculo.query.filter_by(
                                    chassi=chassi_v
                                ).first()
                                if existente:
                                    continue
                                db.session.add(CarviaNfVeiculo(
                                    nf_id=nf.id,
                                    chassi=chassi_v,
                                    modelo=v_data.get('modelo'),
                                    cor=v_data.get('cor'),
                                    numero_motor=v_data.get('numero_motor'),
                                    ano=v_data.get('ano_modelo'),
                                ))
                                veic_inseridos += 1
                            if veic_inseridos:
                                db.session.flush()
                                logger.info(
                                    "NF %s: %d veiculo(s) persistido(s)",
                                    nf.numero_nf, veic_inseridos,
                                )

                            # Detectar e persistir modelos de moto nos itens
                            try:
                                from app.carvia.services.pricing.moto_recognition_service import (
                                    MotoRecognitionService,
                                )
                                moto_count = MotoRecognitionService().detectar_e_persistir_nf(nf.id)
                                if moto_count > 0:
                                    logger.info(
                                        f"Auto-deteccao motos NF {nf.numero_nf}: "
                                        f"{moto_count} modelo(s) persistido(s)"
                                    )
                            except Exception as e_moto:
                                logger.warning(
                                    f"Erro auto-deteccao motos NF {nf.id}: {e_moto}"
                                )

                            acao = 'criada'

                            # Re-linking retroativo: resolver vinculos pendentes
                            # quando NF chega depois de CTe ou Fatura
                            try:
                                from app.carvia.services.documentos.linking_service import LinkingService
                                linker = LinkingService()

                                # CTe→NF: criar junction via nfs_referenciadas_json
                                junc_count = linker.vincular_nf_a_operacoes_orfas(nf)
                                if junc_count > 0:
                                    logger.info(
                                        f"Re-linking NF→CTe: NF {nf.id} vinculada "
                                        f"a {junc_count} operacao(oes) orfa(s)"
                                    )

                                # Fat→NF: atualizar nf_id em itens de fatura
                                fat_count = linker.vincular_nf_a_itens_fatura_orfaos(nf)
                                if fat_count > 0:
                                    logger.info(
                                        f"Re-linking NF→Fatura: NF {nf.id} vinculada "
                                        f"a {fat_count} item(ns) de fatura"
                                    )
                            except Exception as e_link:
                                logger.warning(
                                    f"Erro no re-linking retroativo da NF {nf.id}: {e_link}"
                                )

                    # SAVEPOINT commitou com sucesso. Atualiza tracking Python
                    # (fora do savepoint para evitar entries fantasma se o
                    # savepoint reverter apos mutacao da lista — listas Python
                    # nao sao controladas por rollback).
                    # Guarda defensiva: `nf is not None` evita poluir `nf_map`
                    # com None se algum caminho futuro esquecer de setar nf
                    # dentro do with (latent bug protection).
                    if nf is not None:
                        if acao == 'criada':
                            nfs_criadas.append(nf)
                        elif acao == 'reutilizada':
                            nfs_reutilizadas.append(nf)

                        if chave:
                            nf_map[chave] = nf
                        if numero and cnpj:
                            nf_map[(cnpj, numero)] = nf

                except IntegrityError as e:
                    # SAVEPOINT ja revertido automaticamente pelo `with`.
                    # NFs anteriores permanecem intactas.
                    logger.warning(
                        f"NF duplicada ignorada (IntegrityError): "
                        f"{nf_data.get('numero_nf')} chave={chave}"
                    )
                    erros.append(
                        f"NF {nf_data.get('numero_nf')} ignorada (duplicata)"
                    )
                except Exception as e:
                    # SAVEPOINT ja revertido automaticamente. NAO chamar
                    # db.session.rollback() aqui — isso reverteria a
                    # transacao toda, perdendo NFs anteriores.
                    logger.error(f"Erro ao salvar NF: {e}")
                    erros.append(f"Erro ao salvar NF {nf_data.get('numero_nf')}: {e}")

            # 2. Separar CTes por classificacao (filtro positivo: evitar
            #    CTes com classificacao None/invalida virarem operacao)
            # Filtro positivo + exclusao de itens marcados com _skip_save.
            # _skip_save e setado em processar_arquivos quando o item DACTE PDF
            # foi pareado com um XML CTe Complementar (mesma chave de acesso) —
            # o DACTE nao deve virar nenhum registro proprio.
            ctes_carvia = [c for c in ctes_data
                           if c.get('classificacao') == 'CTE_CARVIA'
                           and not c.get('_skip_save')]
            ctes_subcontrato = [c for c in ctes_data
                                if c.get('classificacao') == 'CTE_SUBCONTRATO'
                                and not c.get('_skip_save')]
            ctes_complementar = [c for c in ctes_data
                                 if c.get('classificacao') == 'CTE_COMPLEMENTAR'
                                 and not c.get('_skip_save')]

            # 3. Criar Operacoes a partir dos CTes CarVia
            # W9: cada iteracao envolvida em begin_nested() — se qualquer
            # write falhar, apenas o SAVEPOINT da operacao corrente e
            # revertido. Operacoes ja commitadas permanecem intactas.
            for cte_data in ctes_carvia:
                # Tracking temporario — so registra na lista apos o
                # savepoint commitar com sucesso (fora do with).
                operacao_registrada = None
                try:
                    with db.session.begin_nested():
                        # Verificar se CTe ja existe no banco (evitar duplicata)
                        cte_chave = cte_data.get('cte_chave_acesso')
                        op_ja_importada = None
                        if cte_chave:
                            op_ja_importada = CarviaOperacao.query.filter_by(
                                cte_chave_acesso=cte_chave
                            ).first()

                        # Buscar op AUTO_PORTARIA por NFs quando nao ha chave duplicada
                        nfs_ref = cte_data.get('nfs_referenciadas', [])
                        op_auto = None
                        if op_ja_importada is None:
                            op_auto = self._buscar_op_auto_por_nfs(nfs_ref, nf_map)

                        if op_ja_importada:
                            # Caminho 1: reimport — reutilizar operacao existente
                            logger.info(
                                f"CTe ja importado (reutilizando): "
                                f"op_id={op_ja_importada.id} cte={cte_chave}"
                            )
                            # Vincular NFs que ainda nao estejam vinculadas
                            self._vincular_nfs(op_ja_importada, nfs_ref, nf_map)

                            # Preencher JSON se ausente (backfill on re-import)
                            if op_ja_importada.nfs_referenciadas_json is None and nfs_ref:
                                op_ja_importada.nfs_referenciadas_json = nfs_ref
                                logger.info(
                                    f"Backfill JSON: op={op_ja_importada.id} "
                                    f"nfs_ref={len(nfs_ref)} refs"
                                )

                            # Re-linking: atualizar itens de fatura orfaos
                            try:
                                from app.carvia.services.documentos.linking_service import LinkingService
                                linker = LinkingService()
                                linker.vincular_operacao_a_itens_fatura_orfaos(op_ja_importada)
                            except Exception as e_link:
                                logger.warning(
                                    f"Erro re-linking CTe re-import: {e_link}"
                                )

                            operacao_registrada = op_ja_importada
                        elif op_auto:
                            # Caminho 2: enriquecer op auto-gerada pela portaria
                            op_auto.cte_chave_acesso = cte_data.get('cte_chave_acesso')
                            op_auto.ctrc_numero = cte_data.get('ctrc_numero')
                            op_auto.cte_xml_nome_arquivo = cte_data.get('arquivo_nome_original')
                            op_auto.cte_xml_path = cte_data.get('cte_xml_path')
                            op_auto.cte_pdf_path = cte_data.get('cte_pdf_path')
                            op_auto.cte_data_emissao = self._parsear_data_cte(
                                cte_data.get('cte_data_emissao')
                            )
                            if not op_auto.nfs_referenciadas_json and nfs_ref:
                                op_auto.nfs_referenciadas_json = nfs_ref
                            # Vincular NFs adicionais
                            self._vincular_nfs(op_auto, nfs_ref, nf_map)
                            logger.info(
                                "CTe CarVia enriqueceu op AUTO_PORTARIA existente: "
                                "op_id=%s, chave=%s",
                                op_auto.id, cte_data.get('cte_chave_acesso'),
                            )
                            operacao_registrada = op_auto
                        else:
                            # Caminho 3: criar operacao nova
                            operacao = self._criar_operacao_de_cte(
                                cte_data, nf_map, criado_por
                            )
                            db.session.add(operacao)
                            db.session.flush()

                            # Vincular NFs
                            self._vincular_nfs(operacao, nfs_ref, nf_map)

                            # Re-linking retroativo: atualizar itens de fatura
                            # que referenciam este CTe mas foram importados antes
                            try:
                                from app.carvia.services.documentos.linking_service import LinkingService
                                linker = LinkingService()
                                fat_count = linker.vincular_operacao_a_itens_fatura_orfaos(operacao)
                                if fat_count > 0:
                                    logger.info(
                                        f"Re-linking CTe→Fatura: op={operacao.id} "
                                        f"vinculada a {fat_count} item(ns) de fatura"
                                    )
                            except Exception as e_link:
                                logger.warning(
                                    f"Erro no re-linking CTe→Fatura op={operacao.id}: {e_link}"
                                )

                            # Auto-cubagem para motos (se empresa configurada)
                            try:
                                from app.carvia.services.pricing.moto_recognition_service import (
                                    MotoRecognitionService,
                                )
                                moto_svc = MotoRecognitionService()
                                cnpj_cliente = operacao.cnpj_cliente or ''
                                if cnpj_cliente and moto_svc.empresa_usa_cubagem(cnpj_cliente):
                                    resultado_cubagem = moto_svc.calcular_peso_cubado_operacao(
                                        operacao.id
                                    )
                                    if (
                                        resultado_cubagem
                                        and resultado_cubagem['peso_cubado_total'] > 0
                                    ):
                                        operacao.peso_cubado = resultado_cubagem[
                                            'peso_cubado_total'
                                        ]
                                        operacao.calcular_peso_utilizado()  # R3
                                        logger.info(
                                            f"Auto-cubagem op={operacao.id}: "
                                            f"peso_cubado={operacao.peso_cubado}"
                                        )
                            except Exception as e_cub:
                                logger.warning(
                                    f"Erro auto-cubagem op={operacao.id}: {e_cub}"
                                )

                            operacao_registrada = operacao

                    # SAVEPOINT commitou com sucesso — registrar operacao
                    # (lista Python atualizada apenas apos persist OK).
                    if operacao_registrada is not None:
                        operacoes_criadas.append(operacao_registrada)
                except IntegrityError as e:
                    # SAVEPOINT ja revertido automaticamente pelo `with`.
                    logger.warning(
                        f"CTe duplicado ignorado (IntegrityError): "
                        f"{cte_data.get('cte_numero')} — {e}"
                    )
                    erros.append(
                        f"CTe {cte_data.get('cte_numero')} ignorado (duplicata)"
                    )
                except Exception as e:
                    # SAVEPOINT ja revertido automaticamente. NAO chamar
                    # db.session.rollback() — isso reverteria operacoes
                    # anteriores commitadas na mesma transacao.
                    logger.error(f"Erro ao criar operacao: {e}")
                    erros.append(
                        f"Erro ao criar operacao CTe {cte_data.get('cte_numero')}: {e}"
                    )

            # 3.5 Criar CTe Complementar a partir de CTes tipo complementar
            #
            # Para fechar os 7 gaps com o worker SSW, este bloco usa o helper
            # `cte_complementar_persistencia.persistir_cte_complementar_completo`
            # que cuida de:
            #   - Parser XML (chave, numero, data, valor)
            #   - Detectar status EMITIDO via <protCTe>/cStat=100
            #   - Upload XML para folder S3 correto (carvia/ctes_complementares_xml)
            #   - Upload DACTE para folder S3 correto (carvia/ctes_complementares_dacte)
            #   - Vincular CarviaCustoEntrega.cte_complementar_id
            #   - Criar CarviaEmissaoCteComplementar com resultado_json
            from app.carvia.services.cte_complementar_persistencia import (
                persistir_cte_complementar_completo,
            )
            from app.utils.file_storage import get_file_storage
            from app.carvia.models import (
                CarviaCustoEntrega, CarviaFrete,
            )

            storage = get_file_storage()
            ctes_comp_criados = []
            # Jobs de verificacao SSW sao enfileirados APOS o commit final
            # para evitar race: se o commit falhar por qualquer razao, os
            # cte_comp ids nao existirao e o job falharia silenciosamente.
            cte_comps_para_verificar_ssw = []

            # W9: cada iteracao usa begin_nested(). Pre-checks sem writes
            # (falta de chave, op original ausente, comp ja existente)
            # sao feitos ANTES do savepoint para evitar criar savepoints
            # vazios. O trabalho real (INSERT do cte_comp + helper de
            # persistencia) fica dentro do savepoint.
            #
            # CUIDADO: o helper `persistir_cte_complementar_completo` faz
            # I/O no S3 (upload XML/DACTE). Uploads S3 NAO sao
            # transacionais — se o savepoint reverter, os arquivos ja
            # carregados ficam orfaos no bucket. Isso ja era assim antes
            # desta refatoracao, portanto comportamento preservado.
            for cte_data in ctes_complementar:
                info_comp = cte_data.get('info_complementar') or {}
                chave_original = info_comp.get('chave_cte_original')

                if not chave_original:
                    erros.append(
                        f"CTe Comp {cte_data.get('cte_numero')}: "
                        f"sem chave do CTe original no XML"
                    )
                    continue

                # Buscar operacao original pela chave do CTe complementado
                operacao_original = CarviaOperacao.query.filter_by(
                    cte_chave_acesso=chave_original
                ).first()

                if not operacao_original:
                    erros.append(
                        f"CTe Comp {cte_data.get('cte_numero')}: "
                        f"CTe original nao encontrado "
                        f"(chave: {chave_original[:20]}...)"
                    )
                    continue

                # Dedup por chave de acesso — sem writes
                cte_chave = cte_data.get('cte_chave_acesso')
                if cte_chave:
                    comp_existente = CarviaCteComplementar.query.filter_by(
                        cte_chave_acesso=cte_chave
                    ).first()
                    if comp_existente:
                        logger.info(
                            "CTe Comp ja importado: chave=%s", cte_chave
                        )
                        ctes_comp_criados.append(comp_existente)
                        continue

                # Tracking temporario — commitado apos o savepoint.
                cte_comp_persistido = None
                cte_comp_id_para_ssw = None
                try:
                    with db.session.begin_nested():
                        numero_comp = CarviaCteComplementar.gerar_numero_comp()

                        # Status inicial:
                        # - XML disponivel: SEMPRE comeca RASCUNHO. O helper
                        #   persistir_cte_complementar_completo parseia o XML
                        #   e e a fonte de verdade — promove para EMITIDO se
                        #   <protCTe>/cStat=100. Pre-promover do PDF aqui criaria
                        #   inconsistencia se o XML tivesse cStat != 100 (helper
                        #   so promove RASCUNHO->EMITIDO, nunca demota).
                        # - PDF only: pre-promove se DACTE PDF tem protocolo
                        #   SEFAZ (DACTE so e impresso quando autorizado). Sem
                        #   XML, o helper nao tem como avaliar o status.
                        xml_disponivel = bool(cte_data.get('cte_xml_path'))
                        protocolo_data = cte_data.get('protocolo_autorizacao') or {}
                        status_inicial = (
                            'EMITIDO'
                            if (
                                not xml_disponivel
                                and protocolo_data.get('codigo_status') == '100'
                            )
                            else 'RASCUNHO'
                        )

                        cte_comp = CarviaCteComplementar(
                            numero_comp=numero_comp,
                            operacao_id=operacao_original.id,
                            cte_valor=float(cte_data.get('cte_valor') or 0),
                            cte_numero=str(cte_data.get('cte_numero') or '') or None,
                            cte_chave_acesso=cte_chave,
                            ctrc_numero=cte_data.get('ctrc_numero'),
                            cte_data_emissao=self._parsear_data_cte(
                                cte_data.get('cte_data_emissao')
                            ),
                            cnpj_cliente=operacao_original.cnpj_cliente,
                            nome_cliente=operacao_original.nome_cliente,
                            status=status_inicial,
                            observacoes=info_comp.get('motivo'),
                            criado_por=criado_por,
                        )

                        db.session.add(cte_comp)
                        db.session.flush()  # gerar cte_comp.id antes do helper

                        # Vincular ao CarviaFrete pela operacao
                        frete = CarviaFrete.query.filter_by(
                            operacao_id=operacao_original.id
                        ).first()
                        if frete:
                            cte_comp.frete_id = frete.id

                        # Resolver Custo Entrega (selecionado pelo usuario no
                        # preview ou auto-match na ausencia de selecao)
                        custo_entrega = None
                        custo_id_selecionado = cte_data.get(
                            'custo_entrega_id_selecionado'
                        )
                        if custo_id_selecionado:
                            custo_entrega = db.session.get(
                                CarviaCustoEntrega, int(custo_id_selecionado)
                            )
                            if custo_entrega and custo_entrega.cte_complementar_id:
                                logger.warning(
                                    "Custo Entrega %s ja vinculado a CTe Comp %s — "
                                    "ignorando selecao manual",
                                    custo_entrega.numero_custo,
                                    custo_entrega.cte_complementar_id,
                                )
                                custo_entrega = None

                        # Baixar bytes do XML e DACTE do S3 (paths salvos no upload)
                        xml_bytes = None
                        xml_path = cte_data.get('cte_xml_path')
                        if xml_path:
                            try:
                                xml_bytes = storage.download_file(xml_path)
                            except Exception as e_dl:
                                logger.warning(
                                    "Falha ao baixar XML CTe Comp %s do S3: %s",
                                    xml_path, e_dl
                                )

                        dacte_bytes = None
                        dacte_path = cte_data.get('cte_pdf_path')
                        if dacte_path:
                            try:
                                dacte_bytes = storage.download_file(dacte_path)
                            except Exception as e_dl:
                                logger.warning(
                                    "Falha ao baixar DACTE CTe Comp %s do S3: %s",
                                    dacte_path, e_dl
                                )

                        # Persistir tudo via helper (parser, S3 folder correto,
                        # CarviaEmissaoCteComplementar, vínculo de Custo Entrega)
                        resultado_persist = persistir_cte_complementar_completo(
                            cte_comp=cte_comp,
                            xml_bytes=xml_bytes,
                            xml_nome=None,  # helper gera baseado na chave
                            dacte_bytes=dacte_bytes,
                            dacte_nome=None,
                            custo_entrega=custo_entrega,
                            motivo_ssw='C',  # Complementar geral (manual import)
                            filial_ssw='CAR',
                            icms_pai=None,  # helper extrai do CTe pai
                            valor_calculado=None,  # helper usa cte_valor do XML
                            criado_por=criado_por,
                            origem='IMPORTACAO_MANUAL',
                        )

                        if resultado_persist.get('erros'):
                            for err in resultado_persist['erros']:
                                erros.append(
                                    f"CTe Comp {cte_data.get('cte_numero')}: {err}"
                                )

                        cte_comp_persistido = cte_comp
                        if cte_data.get('verificar_ctrc_ssw'):
                            cte_comp_id_para_ssw = cte_comp.id

                        logger.info(
                            "CTe Complementar criado: %s → op=%s "
                            "(CTe original: %s, custo_vinculado=%s, "
                            "emissao_id=%s, status=%s)",
                            numero_comp, operacao_original.id,
                            operacao_original.cte_numero,
                            custo_entrega.numero_custo if custo_entrega else 'NENHUM',
                            resultado_persist.get('emissao_id'),
                            cte_comp.status,
                        )

                    # SAVEPOINT commitou — atualizar tracking Python
                    if cte_comp_persistido is not None:
                        ctes_comp_criados.append(cte_comp_persistido)
                        if cte_comp_id_para_ssw is not None:
                            cte_comps_para_verificar_ssw.append(cte_comp_id_para_ssw)

                except IntegrityError as e:
                    # SAVEPOINT ja revertido automaticamente. NAO chamar
                    # db.session.rollback() — isso reverteria CTes Comp
                    # anteriores commitados na mesma transacao.
                    logger.warning(
                        "CTe Comp duplicado (IntegrityError): %s", e
                    )
                    erros.append(
                        f"CTe Comp {cte_data.get('cte_numero')} "
                        f"ignorado (duplicata)"
                    )
                except Exception as e:
                    # SAVEPOINT ja revertido automaticamente.
                    logger.error("Erro ao criar CTe Complementar: %s", e)
                    erros.append(
                        f"Erro CTe Comp {cte_data.get('cte_numero')}: {e}"
                    )

            # 4. Criar Subcontratos a partir dos CTes de transportadoras
            # W9: cada iteracao envolvida em begin_nested(). O helper
            # `_processar_cte_subcontrato` faz db.session.flush() internamente
            # — isso e seguro dentro do savepoint (flush escreve mas nao
            # commita). Se qualquer write falhar, apenas o SAVEPOINT deste
            # sub e revertido.
            for cte_data in ctes_subcontrato:
                sub_persistido = None
                try:
                    with db.session.begin_nested():
                        sub = self._processar_cte_subcontrato(
                            cte_data, nf_map, operacoes_criadas, criado_por
                        )
                        sub_persistido = sub

                    # SAVEPOINT commitou — atualizar tracking Python
                    if sub_persistido:
                        subcontratos_criados.append(sub_persistido)
                except IntegrityError as e:
                    # SAVEPOINT ja revertido automaticamente. NAO chamar
                    # db.session.rollback() — isso reverteria subs
                    # anteriores commitados na mesma transacao.
                    logger.warning(
                        f"CTe Subcontrato duplicado (IntegrityError): {e}"
                    )
                    erros.append(
                        f"CTe Sub {cte_data.get('cte_numero')} ignorado (duplicata)"
                    )
                except Exception as e:
                    # SAVEPOINT ja revertido automaticamente.
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
                        with db.session.begin_nested():
                            db.session.add(fatura)
                            db.session.flush()  # Obter ID

                            # Gravar itens de detalhe CTe (apenas para CarviaFaturaCliente)
                            if isinstance(fatura, CarviaFaturaCliente):
                                from app.carvia.services.documentos.linking_service import LinkingService
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
                                        else:
                                            # Fallback: CTe pode ser Complementar
                                            cte_comp = linker.resolver_cte_complementar_por_cte(cte_num)
                                            if cte_comp and cte_comp.operacao_id:
                                                operacao_id = cte_comp.operacao_id
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

                                # Flush para que os itens recem-adicionados estejam
                                # visiveis na query do vincular_itens_fatura_cliente
                                db.session.flush()

                                # Fallback: resolver NFs pendentes com auto-criacao
                                # Itens criados acima podem ter nf_id=NULL se NF nunca
                                # foi importada. vincular_itens_fatura_cliente com
                                # auto_criar_nf=True cria CarviaNf stub (FATURA_REFERENCIA).
                                #
                                # NOTA (W9): esses stubs NF sao criados DENTRO do
                                # savepoint da fatura — se o savepoint reverter por
                                # qualquer motivo (ex: IntegrityError no restante do
                                # processamento), os stubs tambem sao revertidos.
                                # Logs do linker dirao "NF referencia criada" mesmo
                                # em casos de rollback — confuso em post-mortem,
                                # mas consistente com o estado final do DB.
                                link_stats = linker.vincular_itens_fatura_cliente(
                                    fatura.id, auto_criar_nf=True
                                )
                                if link_stats.get('nfs_criadas_referencia', 0) > 0:
                                    logger.info(
                                        f"Fatura {fatura.id}: {link_stats['nfs_criadas_referencia']} "
                                        f"NFs referencia criadas automaticamente"
                                    )

                                # Expandir: criar itens para NFs do CTe não presentes no PDF
                                # PDF SSW mostra 1 NF por linha, mas CTe pode ter N NFs
                                expand_stats = linker.expandir_itens_com_nfs_do_cte(
                                    fatura.id
                                )
                                if expand_stats.get('itens_criados', 0) > 0:
                                    logger.info(
                                        f"Fatura {fatura.id}: {expand_stats['itens_criados']} "
                                        f"itens suplementares criados (NFs do CTe)"
                                    )

                                # Backward binding: setar fatura_cliente_id e status
                                # nas operacoes que ja foram resolvidas nos itens.
                                # Fatura PDF e evidencia de faturamento consumado.
                                bind_stats = linker.vincular_operacoes_da_fatura(
                                    fatura.id
                                )
                                if bind_stats['operacoes_vinculadas'] > 0:
                                    logger.info(
                                        f"Fatura {fatura.id}: "
                                        f"{bind_stats['operacoes_vinculadas']} operacao(oes) "
                                        f"vinculada(s) com status FATURADO"
                                    )

                                # Binding CTe Complementares: vincular CTe Comps
                                # referenciados nos itens e recalcular valor_total.
                                comp_stats = linker.vincular_ctes_complementares_da_fatura(
                                    fatura.id
                                )
                                if comp_stats['cte_comp_vinculados'] > 0:
                                    logger.info(
                                        f"Fatura {fatura.id}: "
                                        f"{comp_stats['cte_comp_vinculados']} CTe Comp(s) "
                                        f"vinculado(s). Valor: R$ {comp_stats['valor_total_anterior']:.2f} "
                                        f"-> R$ {comp_stats['valor_total_novo']:.2f}"
                                    )

                        faturas_criadas.append(fatura)
                except IntegrityError as e:
                    logger.warning(
                        f"Fatura duplicada ignorada (IntegrityError): "
                        f"{fat_data.get('numero_fatura', '?')} — {e}"
                    )
                    erros.append(
                        f"Fatura {fat_data.get('numero_fatura', '?')} ignorada (duplicata)"
                    )
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

            # Hook Monitoramento CarVia: sincroniza NFs recem-importadas com
            # EntregaMonitorada (origem='CARVIA'). Usa status_inicial para
            # marcar como 'Aguardando Embarque' e nao poluir filtro sem_previsao.
            # Nao-bloqueante: erro aqui nao reverte a importacao.
            if nfs_criadas:
                try:
                    from app.utils.sincronizar_entregas_carvia import (
                        sincronizar_entrega_carvia_por_nf,
                    )
                    for nf_criada in nfs_criadas:
                        try:
                            sincronizar_entrega_carvia_por_nf(
                                nf_criada.numero_nf,
                                status_inicial='Aguardando Embarque',
                            )
                        except Exception as e_item:
                            logger.warning(
                                "Sync monitoramento NF import %s falhou: %s",
                                nf_criada.numero_nf, e_item,
                            )
                except Exception as e_sync:
                    logger.warning(
                        "Hook monitoramento (importacao CarVia) falhou: %s",
                        e_sync,
                    )

            # Enfileirar jobs de verificacao SSW APOS commit bem-sucedido.
            # Fazer antes do commit causa race: se o commit falhar, o cte_comp
            # nao existe mas o job ja esta na fila (retorna SKIPPED silencioso).
            if cte_comps_para_verificar_ssw:
                try:
                    from app.portal.workers import enqueue_job
                    from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                        verificar_ctrc_cte_comp_job,
                    )
                    for _cte_comp_id in cte_comps_para_verificar_ssw:
                        try:
                            enqueue_job(
                                verificar_ctrc_cte_comp_job,
                                _cte_comp_id,
                                queue_name='default',
                                timeout='10m',
                            )
                            logger.info(
                                "CTe Comp id=%s: job verificar_ctrc_ssw "
                                "enfileirado (pos-commit)",
                                _cte_comp_id,
                            )
                        except Exception as e_job:
                            logger.warning(
                                "Falha ao enfileirar job verificar_ctrc_ssw "
                                "para CTe Comp id=%s: %s",
                                _cte_comp_id, e_job,
                            )
                except ImportError as e_imp:
                    logger.warning(
                        "Falha ao importar worker verificar_ctrc_ssw_jobs: %s",
                        e_imp,
                    )

            return {
                'sucesso': True,
                'nfs_criadas': len(nfs_criadas),
                'nfs_reutilizadas': len(nfs_reutilizadas),
                'operacoes_criadas': len(operacoes_criadas),
                'subcontratos_criados': len(subcontratos_criados),
                'ctes_comp_criados': len(ctes_comp_criados),
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
                'nfs_reutilizadas': 0,
                'operacoes_criadas': 0,
                'subcontratos_criados': 0,
                'ctes_comp_criados': 0,
                'faturas_criadas': 0,
                'nfs_sem_cte': 0,
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

    def _parsear_dacte_pdf(self, conteudo: bytes, nome: str) -> Dict:
        """Parseia DACTE PDF (CTe em formato PDF).

        Retorna dict no mesmo formato de _parsear_cte_xml() para que o
        fluxo de classificacao CNPJ e criacao de operacao/subcontrato
        funcione sem alteracao.
        """
        from app.carvia.services.parsers.dacte_pdf_parser import DactePDFParser

        parser = DactePDFParser(pdf_bytes=conteudo)
        if not parser.is_valid():
            return {}
        dados = parser.get_todas_informacoes()
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

        # Verificar se fatura ja existe no banco (evitar duplicata cross-upload)
        # Precisa verificar em AMBAS as tabelas (cliente e transportadora)
        fatura_existente = CarviaFaturaCliente.query.filter_by(
            numero_fatura=numero,
            cnpj_cliente=cnpj_pagador or 'DESCONHECIDO',
        ).first()

        if not fatura_existente:
            fatura_existente = CarviaFaturaTransportadora.query.filter_by(
                numero_fatura=numero,
                data_emissao=data_emissao,
            ).first()

        if fatura_existente:
            tipo = 'cliente' if isinstance(fatura_existente, CarviaFaturaCliente) else 'transportadora'
            logger.info(
                f"Fatura {tipo} ja existe (ignorando): "
                f"num={numero} id={fatura_existente.id}"
            )
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
                arquivo_pdf_path=fat_data.get('arquivo_pdf_path'),
                status_conferencia='PENDENTE',
                criado_por=criado_por,
            )
            logger.info(
                f"Fatura transportadora criada: {numero} transp={transportadora.razao_social}"
            )
            return fatura

        # Warning: beneficiario nao cadastrado como transportadora
        if cnpj_emissor:
            cnpj_digitos = re.sub(r'\D', '', cnpj_emissor)
            # Se tem CNPJ de empresa (14 digitos) e nao e o CNPJ CarVia,
            # pode ser fatura de subcontrato com transportadora nao cadastrada
            if len(cnpj_digitos) >= 14 and cnpj_digitos != CARVIA_CNPJ:
                nome_emissor = fat_data.get('nome_emissor', '')
                logger.warning(
                    f"Fatura {numero}: beneficiario CNPJ {cnpj_emissor} "
                    f"({nome_emissor}) nao encontrado como transportadora. "
                    f"Classificando como fatura cliente. Se for fatura de "
                    f"subcontrato, cadastre a transportadora."
                )

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
            arquivo_pdf_path=fat_data.get('arquivo_pdf_path'),
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

    def _buscar_stub_fatura_referencia(self, numero: str, cnpj: str) -> Optional[CarviaNf]:
        """Busca CarviaNf stub (tipo_fonte=FATURA_REFERENCIA) por numero+CNPJ.

        Stubs sao criados pelo LinkingService quando uma fatura referencia
        uma NF que ainda nao foi importada. Quando a NF real chega,
        precisamos encontrar o stub para fazer merge.

        Normaliza zeros a esquerda e CNPJ (apenas digitos).

        Returns:
            CarviaNf stub ou None
        """
        from sqlalchemy import func as sa_func

        nf_norm = numero.lstrip('0') or '0'
        cnpj_digits = re.sub(r'\D', '', cnpj)

        if not cnpj_digits:
            return None

        stub = CarviaNf.query.filter(
            CarviaNf.tipo_fonte == 'FATURA_REFERENCIA',
            sa_func.ltrim(CarviaNf.numero_nf, '0') == nf_norm,
            sa_func.regexp_replace(
                CarviaNf.cnpj_emitente, '[^0-9]', '', 'g'
            ) == cnpj_digits,
        ).first()

        if stub:
            logger.info(
                f"Stub FATURA_REFERENCIA encontrado: nf_id={stub.id} "
                f"numero={numero} cnpj={cnpj}"
            )

        return stub

    def _merge_nf_sobre_stub(self, stub: CarviaNf, nf_data: Dict,
                              criado_por: str) -> CarviaNf:
        """Promove stub FATURA_REFERENCIA com dados reais da NF.

        Atualiza TODOS os campos do stub com dados da NF real,
        preservando id, criado_em e todas as FK existentes (fatura items,
        junctions carvia_operacao_nfs).

        Args:
            stub: CarviaNf com tipo_fonte='FATURA_REFERENCIA'
            nf_data: Dict com dados parseados da NF real
            criado_por: Email do usuario

        Returns:
            O mesmo stub (atualizado in-place)
        """
        data_emissao = nf_data.get('data_emissao')
        if data_emissao and hasattr(data_emissao, 'date'):
            data_emissao = data_emissao.date()

        # Atualizar campos com dados reais
        stub.numero_nf = nf_data.get('numero_nf') or stub.numero_nf
        stub.serie_nf = nf_data.get('serie_nf')
        stub.chave_acesso_nf = nf_data.get('chave_acesso_nf')
        stub.data_emissao = data_emissao

        stub.cnpj_emitente = nf_data.get('cnpj_emitente') or stub.cnpj_emitente
        stub.nome_emitente = nf_data.get('nome_emitente')
        stub.uf_emitente = nf_data.get('uf_emitente')
        stub.cidade_emitente = nf_data.get('cidade_emitente')

        stub.cnpj_destinatario = nf_data.get('cnpj_destinatario')
        stub.nome_destinatario = nf_data.get('nome_destinatario')
        stub.uf_destinatario = nf_data.get('uf_destinatario')
        stub.cidade_destinatario = nf_data.get('cidade_destinatario')

        stub.valor_total = nf_data.get('valor_total')
        stub.peso_bruto = nf_data.get('peso_bruto')
        stub.peso_liquido = nf_data.get('peso_liquido')
        stub.quantidade_volumes = nf_data.get('quantidade_volumes')

        stub.arquivo_nome_original = nf_data.get('arquivo_nome_original')
        stub.arquivo_xml_path = nf_data.get('arquivo_xml_path')
        stub.arquivo_pdf_path = nf_data.get('arquivo_pdf_path')

        novo_tipo = nf_data.get('tipo_fonte', 'MANUAL')
        stub.tipo_fonte = novo_tipo

        db.session.flush()

        # Gravar itens de produto (que o stub nao tinha)
        itens_data = nf_data.get('itens', [])
        for item_data in itens_data:
            item = CarviaNfItem(
                nf_id=stub.id,
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

        # Detectar e persistir modelos de moto nos itens
        try:
            from app.carvia.services.pricing.moto_recognition_service import (
                MotoRecognitionService,
            )
            MotoRecognitionService().detectar_e_persistir_nf(stub.id)
        except Exception as e_moto:
            logger.warning(
                f"Erro auto-deteccao motos stub NF {stub.id}: {e_moto}"
            )

        logger.info(
            f"NF stub FATURA_REFERENCIA promovida para {novo_tipo}: "
            f"nf_id={stub.id} numero={stub.numero_nf} "
            f"chave={stub.chave_acesso_nf} "
            f"itens={len(itens_data)}"
        )

        return stub

    def _atualizar_nf_existente(self, nf: 'CarviaNf', data: Dict,
                               criado_por: str) -> None:
        """Atualiza campos de uma NF existente com dados de novo parse.

        Usado quando NF cancelada e reimportada — os dados do parse anterior
        podem estar incorretos (ex: parser antigo extraiu campos errados).
        """
        data_emissao = data.get('data_emissao')
        if data_emissao and hasattr(data_emissao, 'date'):
            data_emissao = data_emissao.date()

        nf.numero_nf = data.get('numero_nf') or nf.numero_nf
        nf.serie_nf = data.get('serie_nf') or nf.serie_nf
        nf.data_emissao = data_emissao or nf.data_emissao
        nf.cnpj_emitente = data.get('cnpj_emitente') or nf.cnpj_emitente
        nf.nome_emitente = data.get('nome_emitente') or nf.nome_emitente
        nf.uf_emitente = data.get('uf_emitente') or nf.uf_emitente
        nf.cidade_emitente = data.get('cidade_emitente') or nf.cidade_emitente
        nf.cnpj_destinatario = data.get('cnpj_destinatario') or nf.cnpj_destinatario
        nf.nome_destinatario = data.get('nome_destinatario') or nf.nome_destinatario
        nf.uf_destinatario = data.get('uf_destinatario') or nf.uf_destinatario
        nf.cidade_destinatario = data.get('cidade_destinatario') or nf.cidade_destinatario
        nf.valor_total = data.get('valor_total') or nf.valor_total
        nf.peso_bruto = data.get('peso_bruto') or nf.peso_bruto
        nf.peso_liquido = data.get('peso_liquido') or nf.peso_liquido
        nf.quantidade_volumes = data.get('quantidade_volumes') or nf.quantidade_volumes
        nf.arquivo_nome_original = data.get('arquivo_nome_original') or nf.arquivo_nome_original
        nf.arquivo_pdf_path = data.get('arquivo_pdf_path') or nf.arquivo_pdf_path
        nf.arquivo_xml_path = data.get('arquivo_xml_path') or nf.arquivo_xml_path
        nf.tipo_fonte = data.get('tipo_fonte') or nf.tipo_fonte
        nf.criado_por = criado_por

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
            arquivo_xml_path=data.get('arquivo_xml_path'),
            arquivo_pdf_path=data.get('arquivo_pdf_path'),
            tipo_fonte=data.get('tipo_fonte', 'MANUAL'),
            criado_por=criado_por,
        )

        # Itens de produto e veiculos (armazenar para gravar apos flush da NF)
        nf._itens_pendentes = data.get('itens', [])
        nf._veiculos_pendentes = data.get('veiculos', [])
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

        # Persistir referencias de NF do CTe XML para re-linking retroativo
        nfs_ref_json = nfs_ref if nfs_ref else None

        # Tomador do CTe extraido via get_tomador() do parser (<ide>/<toma3> ou <toma4>)
        tomador_info = cte_data.get('tomador') or {}
        cte_tomador_persist = _TOMADOR_CODE_MAP.get(tomador_info.get('codigo'))

        return CarviaOperacao(
            cte_numero=cte_data.get('cte_numero'),
            cte_chave_acesso=cte_data.get('cte_chave_acesso'),
            ctrc_numero=cte_data.get('ctrc_numero'),
            cte_valor=cte_data.get('cte_valor'),
            cte_xml_nome_arquivo=cte_data.get('arquivo_nome_original'),
            cte_xml_path=cte_data.get('cte_xml_path'),
            cte_pdf_path=cte_data.get('cte_pdf_path'),
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
            nfs_referenciadas_json=nfs_ref_json,
            tipo_entrada='IMPORTADO',
            status='RASCUNHO',
            criado_por=criado_por,
            icms_aliquota=cte_data.get('impostos', {}).get('aliquota_icms'),
            cte_tomador=cte_tomador_persist,
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

    def _buscar_op_auto_por_nfs(self, nfs_ref: list, nf_map: dict):
        """Busca CarviaOperacao AUTO_PORTARIA que referencia as mesmas NFs.

        Usado como guardrail: se CarviaFreteService ja criou op auto na portaria,
        o import de CTe deve ENRIQUECER (nao duplicar).
        """
        if not nfs_ref:
            return None

        # Resolver NF IDs a partir das referencias
        nf_ids = []
        for nf_ref in nfs_ref:
            chave = nf_ref.get('chave')
            nf = nf_map.get(chave) if chave else None
            if nf is None and nf_ref.get('cnpj_emitente') and nf_ref.get('numero_nf'):
                nf = nf_map.get((nf_ref['cnpj_emitente'], nf_ref['numero_nf']))
            if nf is None:
                nf = self._buscar_nf_no_banco(nf_ref)
            if nf and isinstance(nf, CarviaNf):
                nf_ids.append(nf.id)

        if not nf_ids:
            return None

        # Buscar op auto-gerada que tem junction com essas NFs
        from app.carvia.models import CarviaOperacaoNf
        op_auto = CarviaOperacao.query.filter(
            CarviaOperacao.tipo_entrada == 'AUTO_PORTARIA',
            CarviaOperacao.cte_chave_acesso.is_(None),  # ainda sem CTe real
            CarviaOperacao.id.in_(
                db.session.query(CarviaOperacaoNf.operacao_id).filter(
                    CarviaOperacaoNf.nf_id.in_(nf_ids)
                )
            ),
        ).first()

        return op_auto

    def _buscar_sub_auto_por_operacao(self, operacao_id: int, transportadora_id: int):
        """Busca CarviaSubcontrato auto-gerado pela mesma operacao + transportadora."""
        from app.carvia.models import CarviaSubcontrato
        return CarviaSubcontrato.query.filter(
            CarviaSubcontrato.operacao_id == operacao_id,
            CarviaSubcontrato.transportadora_id == transportadora_id,
            CarviaSubcontrato.observacoes.ilike('%auto:embarque=%'),
            CarviaSubcontrato.cte_chave_acesso.is_(None),  # ainda sem CTe real
            CarviaSubcontrato.status != 'CANCELADO',
        ).first()

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

        # 3. Verificar se subcontrato ja existe (dedup)
        cte_chave = cte_data.get('cte_chave_acesso')
        if cte_chave:
            sub_existente = CarviaSubcontrato.query.filter_by(
                cte_chave_acesso=cte_chave
            ).first()
            if sub_existente:
                logger.info(
                    f"CTe Subcontrato ja importado (reutilizando): "
                    f"sub_id={sub_existente.id} cte={cte_chave}"
                )
                return sub_existente

        # 4. Guardrail: buscar sub AUTO_PORTARIA existente → enriquecer
        sub_auto = self._buscar_sub_auto_por_operacao(
            operacao.id, transportadora.id
        )
        if sub_auto:
            sub_auto.cte_chave_acesso = cte_data.get('cte_chave_acesso')
            sub_auto.cte_xml_nome_arquivo = cte_data.get('arquivo_nome_original')
            sub_auto.cte_xml_path = cte_data.get('cte_xml_path')
            sub_auto.cte_pdf_path = cte_data.get('cte_pdf_path')
            sub_auto.cte_data_emissao = self._parsear_data_cte(
                cte_data.get('cte_data_emissao')
            )
            # Valor REAL cobrado pela transportadora (atualiza custo)
            if cte_data.get('cte_valor'):
                sub_auto.cte_valor = cte_data['cte_valor']
            logger.info(
                "CTe Subcontrato enriqueceu sub AUTO_PORTARIA existente: "
                "sub_id=%s, chave=%s",
                sub_auto.id, cte_data.get('cte_chave_acesso'),
            )
            return sub_auto

        # 5. Gerar numero sequencial por transportadora
        max_seq = db.session.query(
            db.func.max(CarviaSubcontrato.numero_sequencial_transportadora)
        ).filter(
            CarviaSubcontrato.transportadora_id == transportadora.id,
        ).scalar() or 0

        # 6. Criar subcontrato
        sub = CarviaSubcontrato(
            operacao_id=operacao.id,
            transportadora_id=transportadora.id,
            numero_sequencial_transportadora=max_seq + 1,
            cte_numero=cte_data.get('cte_numero'),
            cte_chave_acesso=cte_data.get('cte_chave_acesso'),
            cte_valor=cte_data.get('cte_valor'),
            cte_xml_nome_arquivo=cte_data.get('arquivo_nome_original'),
            cte_xml_path=cte_data.get('cte_xml_path'),
            cte_pdf_path=cte_data.get('cte_pdf_path'),
            cte_data_emissao=self._parsear_data_cte(
                cte_data.get('cte_data_emissao')
            ),
            valor_cotado=None,
            status='PENDENTE',
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
        """Busca operacao existente no banco por NFs referenciadas (chave de acesso ou CNPJ+numero)."""
        nfs_ref = cte_data.get('nfs_referenciadas', [])
        for nf_ref in nfs_ref:
            nf_existente = self._buscar_nf_no_banco(nf_ref)
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
