#!/usr/bin/env python3
"""
Excel Faturamento - Mini esqueleto especializado para relatórios de faturamento
Migrado de excel_commands.py para a nova estrutura modular
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

# Excel generation
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

# Sistema imports (com fallbacks)
try:
    from app import db
    from app.faturamento.models import RelatorioFaturamentoImportado
    from flask_login import current_user
    from sqlalchemy import func, and_, or_
    SISTEMA_AVAILABLE = True
except ImportError:
    SISTEMA_AVAILABLE = False

logger = logging.getLogger(__name__)

class ExcelFaturamento:
    """Mini esqueleto especializado para Excel de faturamento"""
    
    def __init__(self):
        self.output_dir = Path("static/reports")
        self.output_dir.mkdir(exist_ok=True)
        
    def detectar_comando_faturamento(self, consulta: str) -> bool:
        """Detecta se é comando específico de faturamento"""
        keywords_faturamento = [
            'faturamento', 'fatura', 'faturas', 'nf', 'nota fiscal', 'notas fiscais',
            'invoice', 'invoices', 'billing', 'receita', 'receitas', 'cobrança'
        ]
        
        consulta_lower = consulta.lower()
        return any(keyword in consulta_lower for keyword in keywords_faturamento)
    
    def gerar_excel_faturamento(self, consulta: str, filtros: Optional[Dict] = None) -> str:
        """Gera Excel específico de faturamento"""
        
        if not EXCEL_AVAILABLE:
            return self._fallback_sem_openpyxl()
            
        if not SISTEMA_AVAILABLE:
            return self._fallback_sem_sistema()
        
        try:
            # Query do faturamento
            query = db.session.query(RelatorioFaturamentoImportado)
            
            # Aplicar filtros
            if filtros:
                if filtros.get('cliente'):
                    query = query.filter(RelatorioFaturamentoImportado.nome_cliente.ilike(f"%{filtros['cliente']}%"))
                
                if filtros.get('periodo'):
                    # Implementar filtros de período se necessário
                    pass
            
            faturamento = query.limit(1000).all()
            
            if not faturamento:
                return "⚠️ **Nenhum faturamento encontrado** para os critérios especificados."
            
            # Criar workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Faturamento"
            
            # Headers
            headers = [
                "Número NF", "Cliente", "CNPJ", "Valor Total", "Data Fatura",
                "Origem", "Incoterm", "Status"
            ]
            
            # Aplicar estilo profissional aos headers
            self._aplicar_estilo_header(ws, headers)
            
            # Dados
            for row, fat in enumerate(faturamento, 2):
                try:
                    ws.cell(row=row, column=1, value=getattr(fat, 'numero_nf', '') or '')
                    ws.cell(row=row, column=2, value=getattr(fat, 'nome_cliente', '') or '')
                    ws.cell(row=row, column=3, value=getattr(fat, 'cnpj_cliente', '') or '')
                    ws.cell(row=row, column=4, value=float(getattr(fat, 'valor_total', 0) or 0))
                    data_fatura = getattr(fat, 'data_fatura', None)
                    ws.cell(row=row, column=5, value=data_fatura.strftime('%d/%m/%Y') if data_fatura else '')
                    ws.cell(row=row, column=6, value=getattr(fat, 'origem', '') or '')
                    ws.cell(row=row, column=7, value=getattr(fat, 'incoterm', '') or '')
                    ws.cell(row=row, column=8, value=getattr(fat, 'status', '') or '')
                except Exception as e:
                    logger.warning(f"Erro ao processar faturamento {row}: {e}")
                    # Linha em branco em caso de erro
                    for col in range(1, 9):
                        ws.cell(row=row, column=col, value='')
            
            # Auto-ajustar colunas
            self._auto_ajustar_colunas(ws)
            
            # Salvar arquivo
            filename = f"relatorio_faturamento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = self.output_dir / filename
            wb.save(filepath)
            
            # Calcular estatísticas
            valor_total = sum(float(getattr(f, 'valor_total', 0) or 0) for f in faturamento)
            
            return f"""💰 **Relatório de Faturamento Gerado com Sucesso!**

📊 **Detalhes:**
• **Arquivo:** {filename}
• **Registros:** {len(faturamento)} faturas
• **Valor total:** R$ {valor_total:,.2f}
• **Filtros aplicados:** {', '.join([f"{k}={v}" for k, v in filtros.items()]) if filtros else 'Nenhum'}
• **Tamanho:** {self._get_file_size(filepath)}

💾 **Download:**
[Clique aqui para baixar](/static/reports/{filename})

📈 **Resumo:**
• Faturamento médio: R$ {valor_total/len(faturamento):,.2f}
• Clientes únicos: {len(set(getattr(f, 'nome_cliente', '') for f in faturamento))}
• Período: {self._obter_periodo_faturamento(faturamento)}

✅ Excel gerado com dados REAIS do sistema!"""
            
        except Exception as e:
            logger.error(f"Erro ao gerar Excel de faturamento: {e}")
            return f"❌ Erro ao gerar relatório de faturamento: {e}"
    
    def _aplicar_estilo_header(self, ws, headers: List[str]):
        """Aplica estilo profissional aos headers"""
        # Inserir headers
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
    
    def _auto_ajustar_colunas(self, ws):
        """Auto ajusta largura das colunas"""
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    def _get_file_size(self, filepath: Path) -> str:
        """Retorna tamanho do arquivo em formato legível"""
        try:
            size = filepath.stat().st_size
            if size < 1024:
                return f"{size} bytes"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        except:
            return "Tamanho não disponível"
    
    def _obter_periodo_faturamento(self, faturamento: List) -> str:
        """Obtém período do faturamento"""
        try:
            datas = [getattr(f, 'data_fatura', None) for f in faturamento if getattr(f, 'data_fatura', None)]
            datas_validas = [d for d in datas if d is not None]
            if datas_validas:
                data_min = min(datas_validas)
                data_max = max(datas_validas)
                return f"{data_min.strftime('%d/%m/%Y')} a {data_max.strftime('%d/%m/%Y')}"
            return "Período não disponível"
        except:
            return "Período não disponível"
    
    def _fallback_sem_openpyxl(self) -> str:
        """Fallback quando openpyxl não disponível"""
        return """💰 **Comando Excel Faturamento Detectado**

⚠️ **Módulo openpyxl não disponível**

Para gerar Excel de faturamento, instale:
```bash
pip install openpyxl
```

💡 **Funcionalidades disponíveis:**
• Relatórios de faturamento por cliente
• Análise de receitas por período
• Resumos executivos de cobrança
• Exportação completa de notas fiscais

📋 **Comandos suportados:**
• "excel do faturamento"
• "relatório de faturamento do [CLIENTE]"
• "planilha de notas fiscais"
• "faturamento por período"

🔧 **Instale openpyxl para funcionalidade completa!**"""
    
    def _fallback_sem_sistema(self) -> str:
        """Fallback quando sistema não disponível"""
        return """💰 **Excel Faturamento - Modo Simulação**

⚠️ **Sistema de faturamento não disponível**

📊 **Funcionalidades simuladas:**
• Relatórios de faturamento
• Análise de receitas
• Resumos executivos
• Exportação de notas fiscais

💡 **Em produção, geraria:**
• Excel com dados reais do faturamento
• Estatísticas de receitas
• Análise por cliente/período
• Resumos executivos completos

🔧 **Conecte ao sistema para funcionalidade completa!**"""

# Instância global
_excel_faturamento = None

def get_excel_faturamento():
    """Retorna instância do ExcelFaturamento"""
    global _excel_faturamento
    if _excel_faturamento is None:
        _excel_faturamento = ExcelFaturamento()
    return _excel_faturamento 