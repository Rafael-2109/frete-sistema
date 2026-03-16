"""
Classe base para extração de dados de PDFs
"""

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import pypdf  # Mudado de PyPDF2 para pypdf
import pdfplumber
from decimal import Decimal


class PDFExtractor(ABC):
    """Classe base abstrata para extratores de PDF"""
    
    def __init__(self):
        self.data = []
        self.errors = []
        self.warnings = []
        
    @abstractmethod
    def extract(self, pdf_path: str, texto_pre_extraido: str = None) -> List[Dict[str, Any]]:
        """
        Extrai dados do PDF.

        Args:
            pdf_path: Caminho do arquivo PDF
            texto_pre_extraido: Texto ja extraido pelo identificador (evita duplo-open)
        """
        pass
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """Valida os dados extraídos"""
        pass
    
    def sanitize_cnpj(self, cnpj: str) -> str:
        """Remove formatação do CNPJ"""
        if not cnpj:
            return ""
        # Remove tudo que não é número
        return re.sub(r'\D', '', cnpj)
    
    def sanitize_codigo(self, codigo: str) -> str:
        """Remove parte após o hífen do código"""
        if not codigo:
            return ""
        # Pega apenas a parte antes do hífen
        if '-' in str(codigo):
            return str(codigo).split('-')[0].strip()
        return str(codigo).strip()
    
    def sanitize_decimal(self, value: str) -> Decimal:
        """Converte string para Decimal"""
        if not value:
            return Decimal('0')
        
        # Remove espaços
        value = str(value).strip()
        
        # Substitui vírgula por ponto
        value = value.replace(',', '.')
        
        # Remove pontos de milhares (1.234.567,89 -> 1234567.89)
        parts = value.split('.')
        if len(parts) > 2:
            # Tem pontos de milhares
            value = ''.join(parts[:-1]) + '.' + parts[-1]
        
        try:
            return Decimal(value)
        except Exception as e:
            print(f"Erro ao converter para Decimal: {e}")
            return Decimal('0')
    
    def sanitize_quantity(self, qty: str) -> int:
        """Converte quantidade para inteiro"""
        if not qty:
            return 0
        
        # Remove pontos de milhares e espaços
        qty = str(qty).replace('.', '').replace(',', '').strip()
        
        try:
            return int(qty)
        except Exception as e:
            print(f"Erro ao converter para inteiro: {e}")
            return 0
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Converte string para datetime"""
        if not date_str:
            return None
        
        # Formatos comuns
        formats = [
            '%d/%m/%Y',
            '%d/%m/%y',
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%d.%m.%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except Exception as e:
                print(f"Erro ao converter para datetime: {e}")
                continue
        
        return None
    
    def extract_text_with_pdfplumber(self, pdf_path: str, texto_pre_extraido: str = None) -> str:
        """Extrai texto usando pdfplumber (melhor para tabelas)

        Se texto_pre_extraido for fornecido (ja extraido pelo identificador),
        retorna diretamente sem reabrir o PDF — elimina duplo-open.

        Processa página a página com flush_cache() para liberar memória
        de cada página após extração, evitando pico de RAM em PDFs grandes.
        """
        if texto_pre_extraido:
            return texto_pre_extraido

        chunks = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        chunks.append(page_text)
                    page.flush_cache()
                    # GC periódico a cada 20 páginas para PDFs grandes
                    if i > 0 and i % 20 == 0:
                        import gc
                        gc.collect()
        except Exception as e:
            self.errors.append(f"Erro ao extrair com pdfplumber: {e}")
        return "\n".join(chunks)
    
    def extract_text_with_pypdf2(self, pdf_path: str) -> str:
        """Extrai texto usando pypdf (backup)"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            self.errors.append(f"Erro ao extrair com pypdf: {e}")
        return text