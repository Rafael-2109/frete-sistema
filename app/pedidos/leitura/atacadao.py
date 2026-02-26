"""
Extrator específico para PDFs de Proposta de Compra do Atacadão
"""

import re
from typing import Dict, List, Any
from .base import PDFExtractor
from app import db


class AtacadaoExtractor(PDFExtractor):
    """Extrator para formato de Proposta de Compra do Atacadão"""
    
    def __init__(self):
        super().__init__()
        self.formato = "ATACADAO_PROPOSTA"
        self.depara_cache = {}  # Cache para conversões de código
        self._clientes_cache = {}  # Cache batch de dados de clientes
        self._odoo_client = None  # Conexão Odoo reutilizada entre filiais
        
    def extract(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extrai dados do PDF do Atacadão
        Retorna lista de dicionários com os dados extraídos

        Args:
            pdf_path: Caminho do arquivo PDF
        """
        text = self.extract_text_with_pdfplumber(pdf_path)

        if not text:
            # Fallback para pypdf
            text = self.extract_text_with_pypdf2(pdf_path)

        if not text:
            self.errors.append("Não foi possível extrair texto do PDF")
            return []

        # Divide o texto por páginas/filiais
        filiais = self._split_por_filial(text)

        # Batch preload: coleta identificadores e carrega tudo em ~3 queries
        # em vez de ~1700 queries individuais (N+1)
        cnpjs, codigos = self._coletar_identificadores(filiais)
        self._preload_clientes(cnpjs)
        self._preload_depara(codigos)

        # Batch Odoo para CNPJs não encontrados localmente
        # NOTA: NÃO fechar db.session aqui — os batch preloads completam em <1s,
        # bem abaixo do idle_in_transaction_session_timeout=30s.
        # db.session.close() causa DetachedInstanceError em objetos carregados.
        cnpjs_faltantes = [c for c in cnpjs if c not in self._clientes_cache]
        if cnpjs_faltantes:
            self._preload_clientes_odoo(cnpjs_faltantes)

        # Processa filiais usando caches em memória (sem mais queries DB)
        all_data = []
        for filial_text in filiais:
            filial_data = self._extract_filial_data(filial_text)
            if filial_data:
                all_data.extend(filial_data)

        return all_data
    
    def _split_por_filial(self, text: str) -> List[str]:
        """Divide o texto em seções por filial"""
        # Padrão para identificar início de cada filial
        # Procura por CNPJ no formato XX.XXX.XXX/XXXX-XX
        pattern = r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})'
        
        # Encontra todas as posições de CNPJ
        matches = list(re.finditer(pattern, text))
        
        if not matches:
            return [text]  # Retorna texto completo se não encontrar CNPJs
        
        sections = []
        for i, match in enumerate(matches):
            start = match.start()
            # Pega até o próximo CNPJ ou fim do texto
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections.append(text[start:end])
        
        return sections

    def _coletar_identificadores(self, filiais: List[str]):
        """
        Primeira passada leve: extrai CNPJs e códigos de produto de todas
        as filiais sem tocar no banco de dados.
        Retorna (cnpjs, codigos) para batch preload.
        """
        cnpjs = set()
        codigos = set()

        for filial_text in filiais:
            # CNPJ: formato XX.XXX.XXX/XXXX-XX (já formatado no PDF de Proposta)
            cnpj_match = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', filial_text)
            if cnpj_match:
                cnpjs.add(cnpj_match.group(1))

            # Códigos de produto: formato NNNNN-NNN seguido de descrição
            for m in re.finditer(r'\b(\d{4,6})-\d+\s+[A-Z]', filial_text):
                codigos.add(m.group(1))

        return list(cnpjs), list(codigos)

    def _preload_clientes(self, cnpjs: List[str]):
        """
        Carrega todos os clientes de uma vez em UMA query batch.
        Popula self._clientes_cache[cnpj] = {nome_cliente, municipio, estado, codigo_ibge}
        """
        if not cnpjs:
            return

        try:
            from app.faturamento.models import RelatorioFaturamentoImportado

            resultados = db.session.query(RelatorioFaturamentoImportado).filter(
                RelatorioFaturamentoImportado.cnpj_cliente.in_(cnpjs),
                RelatorioFaturamentoImportado.ativo == True
            ).order_by(
                RelatorioFaturamentoImportado.criado_em.desc()
            ).all()

            # Dedupe: primeiro registro por CNPJ (mais recente)
            for r in resultados:
                if r.cnpj_cliente not in self._clientes_cache:
                    self._clientes_cache[r.cnpj_cliente] = {
                        'nome_cliente': r.nome_cliente,
                        'municipio': r.municipio,
                        'estado': r.estado,
                        'codigo_ibge': r.codigo_ibge
                    }
        except Exception as e:
            db.session.rollback()
            self.warnings.append(f"Erro ao precarregar clientes: {e}")

    def _preload_depara(self, codigos: List[str]):
        """
        Carrega todos os De-Para de produto em UMA query batch.
        Popula self.depara_cache[codigo] = {nosso_codigo, nossa_descricao, fator_conversao}
        """
        if not codigos:
            return

        try:
            from app.portal.atacadao.models import ProdutoDeParaAtacadao

            # Inclui versão normalizada (sem zeros à esquerda)
            codigos_norm = [c.lstrip('0') for c in codigos if c]
            todos = list(set(codigos + codigos_norm))

            # ORDER BY id ASC: registros mais recentes (IDs maiores) sobrescrevem
            # os mais antigos no loop, priorizando dados corrigidos
            resultados = ProdutoDeParaAtacadao.query.filter(
                ProdutoDeParaAtacadao.codigo_atacadao.in_(todos),
                ProdutoDeParaAtacadao.ativo == True
            ).order_by(ProdutoDeParaAtacadao.id.asc()).all()

            for r in resultados:
                codigo_nosso = r.codigo_nosso or ''
                # Defesa: se codigo_nosso tem >10 chars ou contém espaço,
                # provavelmente é descrição invertida — não sobrescrever registro válido
                parece_invalido = len(codigo_nosso) > 10 or ' ' in codigo_nosso
                if parece_invalido and r.codigo_atacadao in self.depara_cache:
                    continue  # Já temos registro válido, não sobrescrever

                result = {
                    'nosso_codigo': r.codigo_nosso,
                    'nossa_descricao': r.descricao_nosso,
                    'fator_conversao': float(r.fator_conversao) if r.fator_conversao else 1.0
                }
                self.depara_cache[r.codigo_atacadao] = result
        except Exception as e:
            db.session.rollback()
            self.warnings.append(f"Erro ao precarregar De-Para: {e}")

    def _preload_clientes_odoo(self, cnpjs_faltantes: List[str]):
        """
        Busca em batch no Odoo os CNPJs não encontrados localmente.
        UMA busca search_read com IN() em vez de N buscas individuais.
        """
        if not cnpjs_faltantes:
            return

        try:
            from app.odoo.utils.connection import get_odoo_connection

            if self._odoo_client is None:
                self._odoo_client = get_odoo_connection()
            client = self._odoo_client

            # Formata CNPJs para padrão Odoo (XX.XXX.XXX/XXXX-XX)
            cnpjs_formatados = []
            cnpj_map = {}  # cnpj_formatado_odoo → cnpj_original
            for cnpj in cnpjs_faltantes:
                cnpj_limpo = re.sub(r'\D', '', cnpj)
                if len(cnpj_limpo) == 14:
                    cnpj_fmt = (
                        f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}"
                        f"/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"
                    )
                else:
                    cnpj_fmt = cnpj
                cnpjs_formatados.append(cnpj_fmt)
                cnpj_map[cnpj_fmt] = cnpj

            # UMA busca batch no Odoo
            partners = client.search_read(
                'res.partner',
                domain=[('l10n_br_cnpj', 'in', cnpjs_formatados)],
                fields=['name', 'state_id', 'l10n_br_municipio_id', 'l10n_br_cnpj'],
                limit=0
            )

            # Coleta state_ids para busca batch de UFs
            state_ids_to_fetch = set()
            for partner in partners:
                if partner.get('state_id'):
                    sid = partner['state_id']
                    if isinstance(sid, (list, tuple)) and len(sid) > 1:
                        state_ids_to_fetch.add(sid[0])

            # UMA busca batch de estados
            state_codes = {}
            if state_ids_to_fetch:
                states = client.search_read(
                    'res.country.state',
                    domain=[('id', 'in', list(state_ids_to_fetch))],
                    fields=['id', 'code'],
                    limit=0
                )
                for s in states:
                    state_codes[s['id']] = s.get('code')

            # Processa resultados e popula cache
            for partner in partners:
                cnpj_odoo = partner.get('l10n_br_cnpj', '')
                cnpj_original = cnpj_map.get(cnpj_odoo, cnpj_odoo)

                resultado = {
                    'nome_cliente': partner.get('name'),
                    'municipio': None,
                    'estado': None,
                    'codigo_ibge': None
                }

                # Municipio
                if partner.get('l10n_br_municipio_id'):
                    mun = partner['l10n_br_municipio_id']
                    if isinstance(mun, (list, tuple)) and len(mun) > 1:
                        nome = mun[1]
                        resultado['municipio'] = nome.split('(')[0].strip() if '(' in nome else nome

                # Estado (UF)
                if partner.get('state_id'):
                    sid = partner['state_id']
                    if isinstance(sid, (list, tuple)) and len(sid) > 1:
                        resultado['estado'] = state_codes.get(sid[0])

                self._clientes_cache[cnpj_original] = resultado

        except Exception as e:
            self.warnings.append(f"Erro ao buscar clientes no Odoo em batch: {e}")

    def _extract_filial_data(self, text: str) -> List[Dict[str, Any]]:
        """Extrai dados de uma filial específica"""
        data = []
        
        # Extrai informações do cabeçalho
        header_info = self._extract_header(text)
        if not header_info:
            return data
        
        # Busca dados do cliente se tiver CNPJ
        if 'cnpj_filial' in header_info:
            # Passa o CNPJ com formatação original
            dados_cliente = self._get_dados_cliente(header_info['cnpj_filial'])
            header_info.update(dados_cliente)

            # Atualiza local_entrega com dados do cliente (Odoo) se disponíveis
            if dados_cliente.get('municipio') or dados_cliente.get('estado'):
                cidade = dados_cliente.get('municipio') or header_info.get('cidade', '')
                uf = dados_cliente.get('estado') or header_info.get('uf', '')
                header_info['local_entrega'] = f"{cidade} - {uf}".strip(' -')

        # Extrai linhas de produtos
        produtos = self._extract_produtos(text)
        
        # Combina header com cada produto
        for produto in produtos:
            item = {**header_info, **produto}
            if self.validate(item):
                data.append(item)
            else:
                self.warnings.append(f"Item inválido: {produto.get('codigo', 'sem código')}")
        
        return data
    
    def _extract_header(self, text: str) -> Dict[str, Any]:
        """Extrai informações do cabeçalho da filial"""
        header = {}
        
        # CNPJ da filial (Local de Entrega) - Mantém formatação original
        cnpj_pattern = r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})'
        cnpj_match = re.search(cnpj_pattern, text)
        if cnpj_match:
            header['cnpj_filial'] = cnpj_match.group(1)  # Mantém formatação original
        
        # Local de Entrega (nome da filial)
        local_pattern = r'Local de Entrega:\s*([^\n]+)'
        local_match = re.search(local_pattern, text)
        if local_match:
            # Pega a linha seguinte que tem o endereço
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'Local de Entrega:' in line:
                    # Nome da filial está na próxima linha útil
                    if i + 1 < len(lines):
                        header['local_entrega'] = lines[i + 1].strip()
                    break
        
        # Cidade e Estado
        # Padrão: CIDADE - UF
        cidade_pattern = r'([A-Z\s]+)\s*-\s*([A-Z]{2})'
        if 'local_entrega' in header:
            cidade_match = re.search(cidade_pattern, header['local_entrega'])
            if cidade_match:
                header['cidade'] = cidade_match.group(1).strip()
                header['uf'] = cidade_match.group(2).strip()
        
        # Número da Proposta
        proposta_pattern = r'Proposta:\s*(\d+)'
        proposta_match = re.search(proposta_pattern, text)
        if proposta_match:
            header['proposta'] = proposta_match.group(1)
        
        # Data de Elaboração
        data_pattern = r'Dt Elab:\s*(\d{2}/\d{2}/\d{4})'
        data_match = re.search(data_pattern, text)
        if data_match:
            header['data_proposta'] = data_match.group(1)
        
        # Fornecedor (NACOM)
        fornecedor_pattern = r'Fornecedor:\s*([^\n]+)'
        fornecedor_match = re.search(fornecedor_pattern, text)
        if fornecedor_match:
            header['fornecedor'] = fornecedor_match.group(1).strip()
        
        # Prazo de Pagamento
        prazo_pattern = r'Prazos de Pgto:\s*(\d+)'
        prazo_match = re.search(prazo_pattern, text)
        if prazo_match:
            header['prazo_pagamento'] = int(prazo_match.group(1))
        
        # Frete
        frete_pattern = r'Frete:\s*(\w+)'
        frete_match = re.search(frete_pattern, text)
        if frete_match:
            header['tipo_frete'] = frete_match.group(1)
        
        return header
    
    def _extract_produtos(self, text: str) -> List[Dict[str, Any]]:
        """Extrai linhas de produtos da tabela"""
        produtos = []
        
        # Padrão para linhas de produto
        # Seq Código-XXX Descrição Embalagem Pr. F Dt Entr Qtde Vlr. Unit ...
        # Ex: 1 35642-114 AZEITONA VERDE CAMPO BELO BALDE CXA 1 X 6 2KG N 15/07/25 770 199,48 0,00 0,00 0,00
        
        # Regex para capturar linhas de produtos
        produto_pattern = r'(\d+)\s+(\d+)-(\d+)\s+([A-Z\s\./\-]+?)\s+(CXA\s+\d+\s+X\s+[\d,]+\s*\w+)\s+([N|S])\s+(\d{2}/\d{2}/\d{2})\s+([\d\.]+)\s+([\d,\.]+)'
        
        matches = re.finditer(produto_pattern, text)
        
        for match in matches:
            produto = {
                'seq': int(match.group(1)),
                'codigo': self.sanitize_codigo(match.group(2)),  # Pega apenas parte antes do hífen
                'codigo_completo': f"{match.group(2)}-{match.group(3)}",  # Código completo para referência
                'descricao': match.group(4).strip(),
                'embalagem': match.group(5).strip(),
                'prazo_fixo': match.group(6) == 'S',
                'data_entrega': f"{match.group(7)}",  # Será convertida depois
                'quantidade': self.sanitize_quantity(match.group(8)),
                'valor_unitario': self.sanitize_decimal(match.group(9))
            }
            
            # Calcula valor total
            produto['valor_total'] = produto['quantidade'] * produto['valor_unitario']
            
            # Busca nosso código via De-Para
            depara = self._get_nosso_codigo(produto['codigo'])
            produto['nosso_codigo'] = depara['nosso_codigo']
            produto['nossa_descricao'] = depara['nossa_descricao']
            produto['fator_conversao'] = depara['fator_conversao']
            
            # Se não encontrou De-Para, adiciona aviso
            if not produto['nosso_codigo']:
                self.warnings.append(f"Código Atacadão {produto['codigo']} não tem De-Para configurado")
            
            produtos.append(produto)
        
        # Se não encontrou com o padrão completo, tenta padrão mais simples
        if not produtos:
            # Padrão alternativo mais flexível
            simple_pattern = r'(\d+)-\d+\s+([A-Z][A-Z\s\./\-]+?)\s+CXA[^\n]+\s+(\d+)\s+([\d,\.]+)\s+[\d,\.]+\s+[\d,\.]+'
            
            matches = re.finditer(simple_pattern, text)
            for match in matches:
                produto = {
                    'codigo': self.sanitize_codigo(match.group(1)),
                    'descricao': match.group(2).strip(),
                    'quantidade': self.sanitize_quantity(match.group(3)),
                    'valor_unitario': self.sanitize_decimal(match.group(4))
                }
                produto['valor_total'] = produto['quantidade'] * produto['valor_unitario']
                produtos.append(produto)
        
        return produtos
    
    def _get_dados_cliente(self, cnpj: str) -> Dict[str, Any]:
        """
        Busca dados do cliente no cache (precarregado em batch por
        _preload_clientes e _preload_clientes_odoo).
        Não faz queries ao banco — todo acesso a DB foi feito no preload.
        """
        if cnpj in self._clientes_cache:
            return self._clientes_cache[cnpj]

        # Fallback: CNPJ não encontrado nem local nem no Odoo
        resultado = {
            'nome_cliente': f"CLIENTE {cnpj}",
            'municipio': None,
            'estado': None,
            'codigo_ibge': None
        }
        self.warnings.append(f"Cliente {cnpj} não encontrado - usando nome padrão")
        return resultado
    
    def _get_nosso_codigo(self, codigo_atacadao: str) -> Dict[str, Any]:
        """
        Busca nosso código no cache (precarregado em batch por _preload_depara).
        Não faz queries ao banco — todo acesso a DB foi feito no preload.

        Normaliza códigos removendo zeros à esquerda para garantir
        compatibilidade entre formatos (ex: '082545' vs '82545').
        """
        # Verifica código original no cache
        if codigo_atacadao in self.depara_cache:
            return self.depara_cache[codigo_atacadao]

        # Tenta versão normalizada (sem zeros à esquerda)
        codigo_normalizado = codigo_atacadao.lstrip('0') if codigo_atacadao else ''
        if codigo_normalizado in self.depara_cache:
            result = self.depara_cache[codigo_normalizado]
            self.depara_cache[codigo_atacadao] = result  # Cache para lookups futuros
            return result

        # Não encontrado no De-Para
        return {
            'nosso_codigo': None,
            'nossa_descricao': None,
            'fator_conversao': 1.0
        }
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Valida os dados extraídos"""
        # Validações obrigatórias
        required = ['codigo', 'quantidade', 'valor_unitario']
        
        for field in required:
            if field not in data or not data[field]:
                return False
        
        # Valida se quantidade é positiva
        if data.get('quantidade', 0) <= 0:
            return False
        
        # Valida se valor é positivo
        if data.get('valor_unitario', 0) <= 0:
            return False
        
        return True
    
    def to_dataframe(self, data: List[Dict[str, Any]]):
        """Converte dados para DataFrame do pandas"""
        import pandas as pd
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Ordena colunas
        column_order = [
            'cnpj_filial', 'local_entrega', 'cidade', 'uf',
            'codigo', 'descricao', 'quantidade', 'valor_unitario', 'valor_total',
            'data_entrega', 'proposta', 'data_proposta'
        ]
        
        # Reordena apenas colunas que existem
        existing_cols = [col for col in column_order if col in df.columns]
        other_cols = [col for col in df.columns if col not in column_order]
        
        df = df[existing_cols + other_cols]
        
        return df