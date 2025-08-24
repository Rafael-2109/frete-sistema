"""
Processador principal para pedidos em PDF
Coordena extração, validação e inserção no banco
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from decimal import Decimal

from .atacadao import AtacadaoExtractor


class PedidoProcessor:
    """Processador principal de pedidos"""
    
    # Mapeamento de formatos para extratores
    EXTRACTORS = {
        'atacadao': AtacadaoExtractor,
        'atacadão': AtacadaoExtractor,
        # Adicionar outros formatos aqui no futuro
        # 'sendas': SendasExtractor,
        # 'assai': AssaiExtractor,
    }
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.processed_count = 0
        self.failed_count = 0
        
    def process_file(self, 
                    file_path: str, 
                    formato: str = 'auto',
                    validate: bool = True,
                    save_to_db: bool = False) -> Dict[str, Any]:
        """
        Processa um arquivo PDF
        
        Args:
            file_path: Caminho do arquivo PDF
            formato: Formato do PDF ('atacadao', 'sendas', etc) ou 'auto' para detectar
            validate: Se deve validar os dados
            save_to_db: Se deve salvar no banco de dados
            
        Returns:
            Dict com resultado do processamento
        """
        result = {
            'success': False,
            'data': [],
            'errors': [],
            'warnings': [],
            'summary': {}
        }
        
        try:
            # Detecta formato se necessário
            if formato == 'auto':
                formato = self._detect_format(file_path)
                if not formato:
                    result['errors'].append("Não foi possível detectar o formato do PDF")
                    return result
            
            # Obtém extrator apropriado
            extractor_class = self.EXTRACTORS.get(formato.lower())
            if not extractor_class:
                result['errors'].append(f"Formato '{formato}' não suportado")
                return result
            
            # Extrai dados
            extractor = extractor_class()
            data = extractor.extract(file_path)
            
            if not data:
                result['errors'].append("Nenhum dado foi extraído do PDF")
                result['errors'].extend(extractor.errors)
                return result
            
            # Valida dados se necessário
            if validate:
                data = self._validate_data(data)
            
            # Salva no banco se necessário
            if save_to_db:
                saved = self._save_to_database(data)
                result['saved_count'] = saved
            
            # Prepara resultado
            result['success'] = True
            result['data'] = data
            result['errors'] = extractor.errors
            result['warnings'] = extractor.warnings
            result['summary'] = self._generate_summary(data)
            
        except Exception as e:
            result['errors'].append(f"Erro ao processar arquivo: {str(e)}")
        
        return result
    
    def _detect_format(self, file_path: str) -> Optional[str]:
        """
        Detecta o formato do PDF baseado no conteúdo
        """
        try:
            # Extrai texto para análise
            import pdfplumber
            text = ""
            
            with pdfplumber.open(file_path) as pdf:
                # Lê apenas primeira página para detecção
                if pdf.pages:
                    text = pdf.pages[0].extract_text() or ""
            
            # Padrões para identificar cada formato
            patterns = {
                'atacadao': [
                    r'Proposta de Compra',
                    r'75\.315\.333',  # CNPJ Atacadão
                    r'CCPMERM01'
                ],
                # Adicionar outros padrões aqui
            }
            
            # Verifica padrões
            for formato, pattern_list in patterns.items():
                for pattern in pattern_list:
                    import re
                    if re.search(pattern, text, re.IGNORECASE):
                        return formato
            
        except Exception as e:
            self.errors.append(f"Erro ao detectar formato: {e}")
        
        return None
    
    def _validate_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Valida e limpa os dados extraídos
        """
        validated = []
        
        for item in data:
            # Remove valores None
            item = {k: v for k, v in item.items() if v is not None}
            
            # Validações básicas
            if not item.get('codigo'):
                self.warnings.append(f"Item sem código: {item.get('descricao', 'sem descrição')}")
                continue
            
            if item.get('quantidade', 0) <= 0:
                self.warnings.append(f"Quantidade inválida para {item['codigo']}")
                continue
            
            if item.get('valor_unitario', 0) <= 0:
                self.warnings.append(f"Valor inválido para {item['codigo']}")
                continue
            
            validated.append(item)
        
        return validated
    
    def _save_to_database(self, data: List[Dict[str, Any]]) -> int:
        """
        Salva dados no banco de dados
        TODO: Implementar quando modelos estiverem definidos
        """
        saved_count = 0
        
        # Por enquanto, apenas retorna contagem
        # No futuro, salvar em tabelas apropriadas
        
        return len(data)
    
    def _generate_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Gera resumo dos dados processados agrupados por CNPJ
        """
        try:
            if not data:
                return {}
            
            df = pd.DataFrame(data)
            
            summary = {
                'total_itens': len(data),
                'total_filiais': df['cnpj_filial'].nunique() if 'cnpj_filial' in df else 0,
                'total_produtos': df['codigo'].nunique() if 'codigo' in df else 0,
                'quantidade_total': int(df['quantidade'].sum()) if 'quantidade' in df else 0,
                'valor_total': float(df['valor_total'].sum()) if 'valor_total' in df else 0.0
            }
            
            # Resumo por filial com dados completos do cliente
            if 'cnpj_filial' in df:
                summary['por_filial'] = []
                for cnpj in df['cnpj_filial'].unique():
                    filial_df = df[df['cnpj_filial'] == cnpj]
                    
                    # Pega os dados do primeiro item (todos têm os mesmos dados de cliente)
                    if not filial_df.empty:
                        primeiro_item = filial_df.iloc[0].to_dict()
                    else:
                        primeiro_item = {}
                    
                    # Converte produtos para garantir que Decimals sejam float
                    produtos_list = []
                    for produto in filial_df.to_dict('records'):
                        produto_clean = {}
                        for k, v in produto.items():
                            if hasattr(v, 'quantize'):  # É Decimal
                                produto_clean[k] = float(v)
                            elif pd.isna(v):  # É NaN/None
                                produto_clean[k] = None
                            else:
                                produto_clean[k] = v
                        produtos_list.append(produto_clean)
                    
                    filial_info = {
                        'cnpj': cnpj,
                        'nome_cliente': primeiro_item.get('nome_cliente', ''),
                        'local': primeiro_item.get('local_entrega', ''),
                        'municipio': primeiro_item.get('municipio', ''),
                        'estado': primeiro_item.get('estado', ''),
                        'itens': len(filial_df),
                        'quantidade': int(filial_df['quantidade'].sum()) if 'quantidade' in filial_df else 0,
                        'valor': float(filial_df['valor_total'].sum()) if 'valor_total' in filial_df else 0.0,
                        'produtos': produtos_list  # Lista com Decimals convertidos
                    }
                    summary['por_filial'].append(filial_info)
            
            return summary
        except Exception as e:
            # Em caso de erro, retorna um summary básico
            print(f"Erro ao gerar summary: {e}")
            return {
                'total_itens': len(data) if data else 0,
                'total_filiais': 0,
                'total_produtos': 0,
                'quantidade_total': 0,
                'valor_total': 0.0,
                'por_filial': [],
                'error': str(e)
            }
    
    def export_to_excel(self, data: List[Dict[str, Any]], output_path: str):
        """
        Exporta dados para Excel
        """
        if not data:
            raise ValueError("Sem dados para exportar")
        
        df = pd.DataFrame(data)
        
        # Formata colunas monetárias
        if 'valor_unitario' in df.columns:
            df['valor_unitario'] = df['valor_unitario'].apply(lambda x: f"R$ {x:,.2f}")
        if 'valor_total' in df.columns:
            df['valor_total'] = df['valor_total'].apply(lambda x: f"R$ {x:,.2f}")
        
        # Salva Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Pedidos', index=False)
            
            # Ajusta largura das colunas
            worksheet = writer.sheets['Pedidos']
            from openpyxl.utils import get_column_letter
            
            for idx, column in enumerate(df.columns, 1):
                column_length = max(df[column].astype(str).map(len).max(), len(column))
                column_letter = get_column_letter(idx)
                worksheet.column_dimensions[column_letter].width = min(column_length + 2, 50)
        
        return output_path
    
    def export_to_csv(self, data: List[Dict[str, Any]], output_path: str):
        """
        Exporta dados para CSV
        """
        if not data:
            raise ValueError("Sem dados para exportar")
        
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        return output_path