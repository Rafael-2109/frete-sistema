"""
Extrator específico para PDFs de Proposta de Compra do Atacadão
"""

import re
from typing import Dict, List, Any
from .base import PDFExtractor


class AtacadaoExtractor(PDFExtractor):
    """Extrator para formato de Proposta de Compra do Atacadão"""
    
    def __init__(self):
        super().__init__()
        self.formato = "ATACADAO_PROPOSTA"
        self.depara_cache = {}  # Cache para conversões de código
        
    def extract(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extrai dados do PDF do Atacadão
        Retorna lista de dicionários com os dados extraídos
        """
        # Tenta primeiro com pdfplumber (melhor para tabelas)
        text = self.extract_text_with_pdfplumber(pdf_path)
        
        if not text:
            # Fallback para pypdf
            text = self.extract_text_with_pypdf2(pdf_path)
        
        if not text:
            self.errors.append("Não foi possível extrair texto do PDF")
            return []
        
        # Divide o texto por páginas/filiais
        filiais = self._split_por_filial(text)
        
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
        Busca dados do cliente na tabela RelatorioFaturamentoImportado
        """
        try:
            from app.faturamento.models import RelatorioFaturamentoImportado
            from app import db
            
            # Busca o cliente com o CNPJ formatado
            cliente = db.session.query(RelatorioFaturamentoImportado).filter(
                RelatorioFaturamentoImportado.cnpj_cliente == cnpj,
                RelatorioFaturamentoImportado.ativo == True
            ).order_by(RelatorioFaturamentoImportado.criado_em.desc()).first()
            
            if cliente:
                return {
                    'nome_cliente': cliente.nome_cliente,
                    'municipio': cliente.municipio,
                    'estado': cliente.estado,
                    'codigo_ibge': cliente.codigo_ibge
                }
            else:
                return {
                    'nome_cliente': None,
                    'municipio': None,
                    'estado': None,
                    'codigo_ibge': None
                }
                
        except Exception as e:
            self.warnings.append(f"Erro ao buscar dados do cliente {cnpj}: {e}")
            return {
                'nome_cliente': None,
                'municipio': None,
                'estado': None,
                'codigo_ibge': None
            }
    
    def _get_nosso_codigo(self, codigo_atacadao: str) -> Dict[str, Any]:
        """
        Busca nosso código interno baseado no código do Atacadão
        Usa cache para evitar múltiplas consultas ao banco
        """
        # Verifica cache primeiro
        if codigo_atacadao in self.depara_cache:
            return self.depara_cache[codigo_atacadao]
        
        try:
            # Importa aqui para evitar dependência circular
            from app.portal.atacadao.models import ProdutoDeParaAtacadao
            from app import db
            
            # Busca no banco
            depara = db.session.query(ProdutoDeParaAtacadao).filter(
                ProdutoDeParaAtacadao.codigo_atacadao == codigo_atacadao,
                ProdutoDeParaAtacadao.ativo == True
            ).first()
            
            if depara:
                result = {
                    'nosso_codigo': depara.codigo_nosso,
                    'nossa_descricao': depara.descricao_nosso,
                    'fator_conversao': float(depara.fator_conversao) if depara.fator_conversao else 1.0
                }
            else:
                result = {
                    'nosso_codigo': None,
                    'nossa_descricao': None,
                    'fator_conversao': 1.0
                }
            
            # Adiciona ao cache
            self.depara_cache[codigo_atacadao] = result
            return result
            
        except Exception as e:
            self.warnings.append(f"Erro ao buscar De-Para para código {codigo_atacadao}: {e}")
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