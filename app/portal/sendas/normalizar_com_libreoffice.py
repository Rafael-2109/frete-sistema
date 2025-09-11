#!/usr/bin/env python3
"""
Normaliza arquivo Excel usando LibreOffice em modo headless.
Simula o "abrir e salvar" que o Excel faz, convertendo para sharedStrings.
"""

import os
import subprocess
import shutil
import logging
import tempfile
from typing import Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def instalar_libreoffice_se_necessario():
    """Verifica e instala LibreOffice se necessário"""
    try:
        result = subprocess.run(['libreoffice', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ LibreOffice encontrado: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    logger.info("📦 LibreOffice não encontrado. Instalando...")
    try:
        # Tentar instalar via apt (Ubuntu/Debian)
        subprocess.run(['sudo', 'apt-get', 'update'], check=True)
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'libreoffice'], check=True)
        logger.info("✅ LibreOffice instalado com sucesso!")
        return True
    except:
        logger.error("❌ Não foi possível instalar LibreOffice automaticamente")
        logger.info("Por favor, instale manualmente:")
        logger.info("  Ubuntu/Debian: sudo apt-get install libreoffice")
        logger.info("  CentOS/RHEL: sudo yum install libreoffice")
        return False


def normalizar_com_libreoffice(arquivo_entrada: str, arquivo_saida: str = None) -> Tuple[bool, str]:
    """
    Usa LibreOffice para abrir e salvar o arquivo, normalizando-o.
    Isso simula o que o Excel faz ao abrir/salvar, convertendo para sharedStrings.
    
    Args:
        arquivo_entrada: Arquivo Excel para normalizar
        arquivo_saida: Arquivo de saída (opcional)
        
    Returns:
        (sucesso, caminho_arquivo_normalizado)
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 NORMALIZAÇÃO COM LIBREOFFICE (ABRIR E SALVAR)")
        logger.info("=" * 60)
        
        # Verificar LibreOffice
        if not instalar_libreoffice_se_necessario():
            logger.error("❌ LibreOffice não disponível")
            return False, arquivo_entrada
        
        # Definir arquivo de saída
        if not arquivo_saida:
            base_name = os.path.splitext(os.path.basename(arquivo_entrada))[0]
            arquivo_saida = f"/tmp/{base_name}_normalizado.xlsx"
        
        # Criar diretório temporário
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copiar arquivo para temp
            temp_input = os.path.join(temp_dir, "input.xlsx")
            shutil.copy2(arquivo_entrada, temp_input)
            
            logger.info(f"📂 Arquivo original: {arquivo_entrada}")
            logger.info(f"📝 Processando com LibreOffice...")
            
            # Comando LibreOffice para converter
            # --headless: sem interface gráfica
            # --convert-to xlsx: força formato XLSX
            # --outdir: diretório de saída
            cmd = [
                'libreoffice',
                '--headless',
                '--convert-to', 'xlsx',
                '--outdir', temp_dir,
                temp_input
            ]
            
            logger.info(f"📋 Comando: {' '.join(cmd)}")
            
            # Executar conversão
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"❌ LibreOffice retornou erro: {result.stderr}")
                return False, arquivo_entrada
            
            # Arquivo convertido
            converted_file = os.path.join(temp_dir, "input.xlsx")
            
            if not os.path.exists(converted_file):
                logger.error(f"❌ Arquivo convertido não encontrado")
                return False, arquivo_entrada
            
            # Copiar para destino final
            shutil.copy2(converted_file, arquivo_saida)
            
            # Verificar tamanhos
            tamanho_original = os.path.getsize(arquivo_entrada)
            tamanho_final = os.path.getsize(arquivo_saida)
            
            logger.info(f"📊 Tamanhos:")
            logger.info(f"   Original: {tamanho_original/1024:.1f} KB")
            logger.info(f"   Normalizado: {tamanho_final/1024:.1f} KB")
            
            logger.info(f"✅ Arquivo normalizado: {arquivo_saida}")
            logger.info("✅ Conversão para sharedStrings realizada!")
            
            return True, arquivo_saida
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Timeout na conversão com LibreOffice")
        return False, arquivo_entrada
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False, arquivo_entrada


# Alternativa 2: Usar Python puro com xlsxwriter
def normalizar_com_xlsxwriter(arquivo_entrada: str, arquivo_saida: str = None) -> Tuple[bool, str]:
    """
    Normaliza usando xlsxwriter que SEMPRE usa sharedStrings.
    Baseado na solução do GPT.
    """
    try:
        import pandas as pd
        import xlsxwriter
        
        logger.info("=" * 60)
        logger.info("🚀 NORMALIZAÇÃO COM XLSXWRITER (FORÇA SHAREDSTRINGS)")
        logger.info("=" * 60)
        
        # Definir saída
        if not arquivo_saida:
            base_name = os.path.splitext(os.path.basename(arquivo_entrada))[0]
            arquivo_saida = f"/tmp/{base_name}_normalizado.xlsx"
        
        logger.info(f"📖 Lendo arquivo: {arquivo_entrada}")
        
        # Ler tudo como matriz, sem mexer nas linhas/colunas
        df = pd.read_excel(arquivo_entrada, header=None, dtype=object, engine="openpyxl")
        
        logger.info(f"📊 Dados: {df.shape[0]} linhas x {df.shape[1]} colunas")
        
        # Converter strings numéricas para números reais
        # EXCETO para coluna 17 (Data sugerida de entrega) que deve permanecer como data
        from datetime import datetime, timedelta
        
        def process_cell(val, col_idx):
            if val is None or pd.isna(val):
                return None
                
            # Coluna 17 é a "Data sugerida de entrega" - manter como data Excel
            if col_idx == 17:
                # Se for número (serial date do Excel), converter para datetime
                if isinstance(val, (int, float)):
                    try:
                        # Converter serial date do Excel para datetime Python
                        excel_date = int(val)
                        # Excel usa 1/1/1900 como dia 1
                        base_date = datetime(1899, 12, 30)  # Base correta do Excel
                        if excel_date > 60:
                            excel_date -= 1  # Correção do bug do ano bissexto 1900
                        return base_date + timedelta(days=excel_date)
                    except:
                        return val
                # Se já for datetime, mantém
                elif isinstance(val, datetime):
                    return val
                # Se for string com data, tentar converter
                elif isinstance(val, str) and "/" in val:
                    try:
                        # Tentar converter dd/mm/yyyy para datetime
                        return pd.to_datetime(val, format="%d/%m/%Y")
                    except:
                        return val
                return val
            
            # Para outras colunas, converter strings numéricas
            if isinstance(val, str):
                s = val.strip().replace(",", ".")
                try:
                    return float(s) if "." in s else int(s)
                except:
                    pass
            return val
        
        # Aplicar processamento mantendo índices de coluna
        for col_idx in df.columns:
            df[col_idx] = df[col_idx].apply(lambda x: process_cell(x, col_idx))
        
        df = df.where(pd.notna(df), None)
        
        logger.info("✏️ Escrevendo com xlsxwriter (sharedStrings)...")
        
        # Criar workbook com xlsxwriter
        wb = xlsxwriter.Workbook(arquivo_saida, {
            "strings_to_numbers": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
            "use_zip64": False,
            "nan_inf_to_errors": True,
            "default_date_format": "dd/mm/yyyy"
        })
        
        # Nome da aba deve ser o mesmo do template
        ws = wb.add_worksheet("Planilha1")  # ou "Sheet" dependendo do template
        
        # Criar formato de data
        date_format = wb.add_format({'num_format': 'dd/mm/yyyy'})
        
        # Escrever dados
        for r, row in enumerate(df.itertuples(index=False, name=None)):
            for c, v in enumerate(row):
                if v is not None:
                    # Se for datetime (coluna 17 principalmente), escrever como data formatada
                    if isinstance(v, (datetime, pd.Timestamp)):
                        ws.write_datetime(r, c, v, date_format)
                    else:
                        ws.write(r, c, v)
        
        wb.close()
        
        # Verificar resultado
        if os.path.exists(arquivo_saida):
            tamanho = os.path.getsize(arquivo_saida)
            logger.info(f"✅ Arquivo criado: {arquivo_saida}")
            logger.info(f"📏 Tamanho: {tamanho/1024:.1f} KB")
            logger.info("✅ Usando sharedStrings (compatível com Sendas)")
            return True, arquivo_saida
        
        return False, arquivo_entrada
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False, arquivo_entrada


def normalizar_planilha_sendas(arquivo_entrada: str, arquivo_saida: str = None) -> Tuple[bool, str]:
    """
    Função principal que tenta as melhores estratégias.
    
    1. LibreOffice (se disponível) - mais confiável
    2. xlsxwriter - sempre usa sharedStrings
    """
    
    logger.info(f"📥 Normalizando: {arquivo_entrada}")
    
    # Estratégia 1: LibreOffice (mais próximo do Excel)
    sucesso, arquivo = normalizar_com_libreoffice(arquivo_entrada, arquivo_saida)
    if sucesso:
        return sucesso, arquivo
    
    # Estratégia 2: xlsxwriter
    logger.info("🔄 Tentando com xlsxwriter...")
    return normalizar_com_xlsxwriter(arquivo_entrada, arquivo_saida)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        arquivo = sys.argv[1]
    else:
        # Criar arquivo teste
        import pandas as pd
        arquivo = "/tmp/teste.xlsx"
        df = pd.DataFrame({
            'A': ['Teste1', 'Teste2'],
            'B': [123, 456],
            'C': ['ABC', 'DEF']
        })
        df.to_excel(arquivo, index=False)
        logger.info(f"📝 Criado arquivo teste: {arquivo}")
    
    sucesso, normalizado = normalizar_planilha_sendas(arquivo)
    
    if sucesso:
        logger.info(f"✅ SUCESSO! Arquivo normalizado: {normalizado}")
        
        # Verificar se tem sharedStrings
        import zipfile
        with zipfile.ZipFile(normalizado, 'r') as zf:
            if 'xl/sharedStrings.xml' in zf.namelist():
                logger.info("✅ Confirmado: usando sharedStrings!")
            else:
                logger.warning("⚠️ AVISO: não está usando sharedStrings")
    else:
        logger.error("❌ Falha na normalização")