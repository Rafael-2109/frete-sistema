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
    def extract(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extrai dados do PDF"""
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
        except:
            return Decimal('0')
    
    def sanitize_quantity(self, qty: str) -> int:
        """Converte quantidade para inteiro"""
        if not qty:
            return 0
        
        # Remove pontos de milhares e espaços
        qty = str(qty).replace('.', '').replace(',', '').strip()
        
        try:
            return int(qty)
        except:
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
            except:
                continue
        
        return None
    
    def extract_text_with_pdfplumber(self, pdf_path: str) -> str:
        """Extrai texto usando pdfplumber (melhor para tabelas)"""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            self.errors.append(f"Erro ao extrair com pdfplumber: {e}")
        return text
    
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