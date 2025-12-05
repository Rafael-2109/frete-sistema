#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leitura de Arquivos - Processa Excel e CSV do Usuario

Skill: lendo-arquivos
Formatos: Excel (.xlsx, .xls), CSV (.csv)

Le arquivos enviados pelo usuario via upload e retorna conteudo
estruturado como JSON para o agente processar e analisar.

Dependencias:
- pandas
- openpyxl (Excel .xlsx)
- xlrd (Excel .xls legado)
"""
import sys
import os
import json
import argparse
import tempfile
from datetime import datetime, date
from decimal import Decimal

# Adicionar path do projeto para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def decimal_default(obj):
    """Serializa tipos especiais para JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    # Para NaN e Inf do pandas
    if obj != obj:  # NaN check
        return None
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def url_para_caminho(url):
    """
    Converte URL do agente para caminho local do arquivo.

    Tenta multiplos caminhos possiveis:
    1. /tmp/agente_files/{session_id}/{filename} (skills)
    2. /tmp/agente_files/{user_id}/{session_id}/{filename} (uploads do usuario)
    3. Caminho direto se for path absoluto

    Args:
        url: URL no formato /agente/api/files/{session_id}/{filename}

    Returns:
        Caminho absoluto do arquivo
    """
    # Se for caminho absoluto que existe, usa direto
    if url.startswith('/') and not url.startswith('/agente') and os.path.exists(url):
        return url

    # Extrai session_id e filename da URL
    # Formato esperado: /agente/api/files/{session_id}/{filename}
    parts = url.strip('/').split('/')

    if len(parts) >= 4 and parts[0] == 'agente' and parts[1] == 'api' and parts[2] == 'files':
        session_id = parts[3]
        filename = parts[4] if len(parts) > 4 else parts[3]

        # Diretorio base dos uploads
        base_folder = os.path.join(tempfile.gettempdir(), 'agente_files')

        # Tenta caminho direto (skills - sem user_id)
        filepath_direct = os.path.join(base_folder, session_id, filename)
        if os.path.exists(filepath_direct):
            return filepath_direct

        # Tenta caminhos com user_id (uploads do usuario)
        # Percorre subdiretorios para encontrar o arquivo
        if os.path.exists(base_folder):
            for user_dir in os.listdir(base_folder):
                user_path = os.path.join(base_folder, user_dir)
                if os.path.isdir(user_path):
                    # Tenta {user_id}/{session_id}/{filename}
                    filepath_user = os.path.join(user_path, session_id, filename)
                    if os.path.exists(filepath_user):
                        return filepath_user
                    # Tenta {user_id}/{filename} (se session_id == user_id)
                    filepath_direct_user = os.path.join(user_path, filename)
                    if os.path.exists(filepath_direct_user):
                        return filepath_direct_user

        # Retorna caminho padrao mesmo se nao existir (para mensagem de erro)
        return filepath_direct

    # Se nao for URL do agente, tenta usar como caminho direto
    return url


def detectar_separador(filepath):
    """Detecta o separador do arquivo CSV."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        primeira_linha = f.readline()

    # Conta ocorrencias de separadores comuns
    separadores = {';': 0, ',': 0, '\t': 0, '|': 0}
    for sep in separadores:
        separadores[sep] = primeira_linha.count(sep)

    # Retorna o mais frequente
    return max(separadores, key=separadores.get)


def ler_excel(filepath, aba=None, cabecalho=0, limite=1000):
    """
    Le arquivo Excel e retorna dados.

    Args:
        filepath: Caminho do arquivo
        aba: Nome ou indice da aba (None = primeira)
        cabecalho: Linha do cabecalho
        limite: Maximo de linhas

    Returns:
        Dict com dados do arquivo
    """
    import pandas as pd

    # Ler todas as abas para listar
    xl = pd.ExcelFile(filepath)
    abas_disponiveis = xl.sheet_names

    # Determinar qual aba ler
    sheet_name = 0  # Default: primeira aba
    if aba is not None:
        if isinstance(aba, int) or aba.isdigit():
            sheet_name = int(aba)
        else:
            sheet_name = aba

    # Ler a aba especifica
    df = pd.read_excel(filepath, sheet_name=sheet_name, header=cabecalho)

    # Limitar linhas
    total_linhas = len(df)
    if limite and len(df) > limite:
        df = df.head(limite)

    # Limpar nomes de colunas
    df.columns = [str(col).strip() for col in df.columns]

    # Converter para lista de dicionarios
    # Trata NaN e tipos especiais
    dados = []
    for _, row in df.iterrows():
        linha = {}
        for col in df.columns:
            val = row[col]
            # Tratar NaN
            if pd.isna(val):
                linha[col] = None
            elif isinstance(val, (datetime, date)):
                linha[col] = val.isoformat()
            elif isinstance(val, Decimal):
                linha[col] = float(val)
            else:
                linha[col] = val
        dados.append(linha)

    return {
        'colunas': list(df.columns),
        'linhas': total_linhas,
        'linhas_retornadas': len(dados),
        'amostra': dados,
        'abas': abas_disponiveis,
        'aba_lida': sheet_name if isinstance(sheet_name, str) else abas_disponiveis[sheet_name]
    }


def ler_csv(filepath, cabecalho=0, limite=1000):
    """
    Le arquivo CSV e retorna dados.

    Args:
        filepath: Caminho do arquivo
        cabecalho: Linha do cabecalho
        limite: Maximo de linhas

    Returns:
        Dict com dados do arquivo
    """
    import pandas as pd

    # Detectar separador
    separador = detectar_separador(filepath)

    # Ler CSV
    df = pd.read_csv(
        filepath,
        sep=separador,
        header=cabecalho,
        encoding='utf-8-sig',
        low_memory=False
    )

    # Limitar linhas
    total_linhas = len(df)
    if limite and len(df) > limite:
        df = df.head(limite)

    # Limpar nomes de colunas
    df.columns = [str(col).strip() for col in df.columns]

    # Converter para lista de dicionarios
    dados = []
    for _, row in df.iterrows():
        linha = {}
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                linha[col] = None
            elif isinstance(val, (datetime, date)):
                linha[col] = val.isoformat()
            else:
                linha[col] = val
        dados.append(linha)

    return {
        'colunas': list(df.columns),
        'linhas': total_linhas,
        'linhas_retornadas': len(dados),
        'amostra': dados,
        'separador': separador
    }


def main():
    parser = argparse.ArgumentParser(
        description='Le arquivo Excel ou CSV e retorna conteudo como JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python ler.py --url "/agente/api/files/default/abc_teste.xlsx"
  python ler.py --url "/agente/api/files/default/abc_dados.csv" --limite 100
  python ler.py --url "/agente/api/files/default/abc_multi.xlsx" --aba "Vendas"
        """
    )

    parser.add_argument('--url', required=True,
                        help='URL do arquivo (formato /agente/api/files/...)')
    parser.add_argument('--limite', type=int, default=1000,
                        help='Limite de linhas a retornar (default: 1000)')
    parser.add_argument('--aba', default=None,
                        help='Nome ou indice da aba (Excel)')
    parser.add_argument('--cabecalho', type=int, default=0,
                        help='Linha do cabecalho (default: 0)')

    args = parser.parse_args()

    resultado = {
        'sucesso': False,
        'arquivo': None,
        'dados': None,
        'resumo': ''
    }

    try:
        # Converter URL para caminho local
        filepath = url_para_caminho(args.url)

        if not os.path.exists(filepath):
            resultado['erro'] = f'Arquivo nao encontrado: {filepath}'
            resultado['mensagem'] = 'Verifique se a URL do arquivo esta correta'
            resultado['url_recebida'] = args.url
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return

        # Obter informacoes do arquivo
        tamanho = os.path.getsize(filepath)
        filename = os.path.basename(filepath)
        extensao = filename.split('.')[-1].lower()

        # Determinar tipo e ler arquivo
        if extensao in ('xlsx', 'xls'):
            tipo = 'excel'
            dados = ler_excel(filepath, args.aba, args.cabecalho, args.limite)
        elif extensao == 'csv':
            tipo = 'csv'
            dados = ler_csv(filepath, args.cabecalho, args.limite)
        else:
            resultado['erro'] = f'Formato nao suportado: .{extensao}'
            resultado['mensagem'] = 'Formatos aceitos: xlsx, xls, csv'
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return

        # Montar resultado
        resultado['sucesso'] = True
        resultado['arquivo'] = {
            'nome': filename,
            'tipo': tipo,
            'tamanho': tamanho,
            'tamanho_formatado': f"{tamanho / 1024:.1f} KB" if tamanho < 1024*1024 else f"{tamanho / (1024*1024):.1f} MB"
        }

        # Adicionar abas se for Excel
        if tipo == 'excel' and 'abas' in dados:
            resultado['arquivo']['abas'] = dados['abas']
            resultado['arquivo']['aba_lida'] = dados.get('aba_lida')

        resultado['dados'] = {
            'colunas': dados['colunas'],
            'total_linhas': dados['linhas'],
            'linhas_retornadas': dados['linhas_retornadas'],
            'registros': dados['amostra']
        }

        # Resumo
        truncado = ' (limitado)' if dados['linhas'] > dados['linhas_retornadas'] else ''
        resultado['resumo'] = (
            f"Arquivo {tipo.upper()} com {dados['linhas']} linhas e {len(dados['colunas'])} colunas{truncado}. "
            f"Colunas: {', '.join(dados['colunas'][:10])}"
            f"{'...' if len(dados['colunas']) > 10 else ''}"
        )

    except ImportError as e:
        resultado['erro'] = f'Dependencia nao instalada: {str(e)}'
        resultado['mensagem'] = 'Execute: pip install pandas openpyxl xlrd'
    except Exception as e:
        resultado['erro'] = str(e)
        resultado['mensagem'] = 'Erro ao ler arquivo'

    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()
