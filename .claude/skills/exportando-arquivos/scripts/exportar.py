#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exportacao de Arquivos - Gera Excel, CSV e JSON para Download

Skill: exportando-arquivos
Formatos: Excel (.xlsx), CSV (.csv), JSON (.json)

Recebe dados via stdin (JSON) e gera arquivo no diretorio de downloads
do agente, retornando URL acessivel via HTTP para o usuario baixar.

Dependencias:
- pandas
- xlsxwriter (formatacao Excel)
"""
import sys
import os
import json
import argparse
import uuid
import tempfile
from datetime import datetime
from decimal import Decimal

# Adicionar path do projeto para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# Dominio de producao no Render
RENDER_DOMAIN = "https://sistema-fretes.onrender.com"


def decimal_default(obj):
    """Serializa Decimal e date para JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def get_upload_folder():
    """
    Retorna o diretorio de upload para arquivos do agente.
    Mesmo diretorio usado pelo routes.py do agente.
    """
    # Diretorio padrao: /tmp/agente_files
    base_folder = os.path.join(tempfile.gettempdir(), 'agente_files')

    # Usar 'default' como session_id quando nao especificado
    # Em producao, o agente deveria passar o session_id real
    session_folder = os.path.join(base_folder, 'default')

    os.makedirs(session_folder, exist_ok=True)
    return session_folder


def gerar_excel(dados, nome_arquivo, titulo=None, colunas=None):
    """
    Gera arquivo Excel com os dados.

    Args:
        dados: Lista de dicionarios com os dados
        nome_arquivo: Nome do arquivo (sem extensao)
        titulo: Titulo da planilha (opcional)
        colunas: Lista de colunas a incluir (opcional)

    Returns:
        Caminho do arquivo gerado
    """
    import pandas as pd

    # Criar DataFrame
    df = pd.DataFrame(dados)

    # Filtrar colunas se especificado
    if colunas:
        colunas_existentes = [c for c in colunas if c in df.columns]
        if colunas_existentes:
            df = df[colunas_existentes]

    # Gerar nome unico para evitar colisoes
    file_id = str(uuid.uuid4())[:8]
    filename = f"{file_id}_{nome_arquivo}.xlsx"
    filepath = os.path.join(get_upload_folder(), filename)

    # Criar Excel com formatacao
    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        sheet_name = titulo[:31] if titulo else 'Dados'  # Excel limita a 31 chars
        df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Formatacao
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # Formato de cabecalho
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })

        # Formato de moeda
        money_format = workbook.add_format({'num_format': 'R$ #,##0.00'})

        # Formato de data
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})

        # Aplicar formato ao cabecalho
        for col_num, value in enumerate(df.columns):
            worksheet.write(0, col_num, value, header_format)

        # Ajustar largura das colunas
        for i, col in enumerate(df.columns):
            max_len = max(
                df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                len(str(col))
            ) + 2
            worksheet.set_column(i, i, min(max_len, 50))

            # Aplicar formato de moeda para colunas de valor
            col_lower = col.lower()
            if any(term in col_lower for term in ['valor', 'preco', 'custo', 'total']):
                worksheet.set_column(i, i, 15, money_format)

    return filepath, filename


def gerar_csv(dados, nome_arquivo, colunas=None):
    """
    Gera arquivo CSV com os dados.

    Args:
        dados: Lista de dicionarios com os dados
        nome_arquivo: Nome do arquivo (sem extensao)
        colunas: Lista de colunas a incluir (opcional)

    Returns:
        Caminho do arquivo gerado
    """
    import pandas as pd

    # Criar DataFrame
    df = pd.DataFrame(dados)

    # Filtrar colunas se especificado
    if colunas:
        colunas_existentes = [c for c in colunas if c in df.columns]
        if colunas_existentes:
            df = df[colunas_existentes]

    # Gerar nome unico
    file_id = str(uuid.uuid4())[:8]
    filename = f"{file_id}_{nome_arquivo}.csv"
    filepath = os.path.join(get_upload_folder(), filename)

    # Salvar CSV (separador ponto-e-virgula para compatibilidade BR)
    df.to_csv(filepath, index=False, sep=';', encoding='utf-8-sig')

    return filepath, filename


def gerar_json(dados, nome_arquivo):
    """
    Gera arquivo JSON com os dados.

    Args:
        dados: Lista de dicionarios com os dados
        nome_arquivo: Nome do arquivo (sem extensao)

    Returns:
        Caminho do arquivo gerado
    """
    # Gerar nome unico
    file_id = str(uuid.uuid4())[:8]
    filename = f"{file_id}_{nome_arquivo}.json"
    filepath = os.path.join(get_upload_folder(), filename)

    # Salvar JSON formatado
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2, default=decimal_default)

    return filepath, filename


def copiar_imagem(caminho_origem, nome_arquivo=None):
    """
    Copia uma imagem existente para a pasta de downloads.

    Args:
        caminho_origem: Caminho completo da imagem existente
        nome_arquivo: Nome para o arquivo (opcional, usa nome original)

    Returns:
        Caminho do arquivo copiado e nome do arquivo
    """
    import shutil

    if not os.path.exists(caminho_origem):
        raise FileNotFoundError(f"Imagem não encontrada: {caminho_origem}")

    # Extrair extensão
    ext = caminho_origem.rsplit('.', 1)[-1].lower() if '.' in caminho_origem else 'png'
    if ext not in ('png', 'jpg', 'jpeg', 'gif'):
        raise ValueError(f"Formato de imagem não suportado: {ext}")

    # Usar nome original se não especificado
    if not nome_arquivo:
        nome_arquivo = os.path.basename(caminho_origem).rsplit('.', 1)[0]

    # Gerar nome unico
    file_id = str(uuid.uuid4())[:8]
    filename = f"{file_id}_{nome_arquivo}.{ext}"
    filepath = os.path.join(get_upload_folder(), filename)

    # Copiar arquivo
    shutil.copy2(caminho_origem, filepath)

    return filepath, filename


def main():
    parser = argparse.ArgumentParser(
        description='Gera arquivo para download (Excel, CSV, JSON ou Imagem)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  echo '{"dados": [{"col1": "val1"}]}' | python exportar.py --formato excel --nome teste
  echo '{"dados": [{"col1": "val1"}]}' | python exportar.py --formato csv --nome teste
  python exportar.py --formato imagem --imagem /caminho/para/imagem.png --nome screenshot
        """
    )

    parser.add_argument('--formato', required=True, choices=['excel', 'csv', 'json', 'imagem'],
                        help='Formato do arquivo (excel, csv, json, imagem)')
    parser.add_argument('--nome', required=True,
                        help='Nome do arquivo (sem extensao)')
    parser.add_argument('--titulo', default=None,
                        help='Titulo da planilha (apenas Excel)')
    parser.add_argument('--colunas', default=None,
                        help='Colunas a incluir (JSON array)')
    parser.add_argument('--imagem', default=None,
                        help='Caminho da imagem a exportar (apenas formato imagem)')

    args = parser.parse_args()

    resultado = {
        'sucesso': False,
        'arquivo': None,
        'mensagem': ''
    }

    try:
        # Tratamento especial para imagens (não precisa de stdin)
        if args.formato == 'imagem':
            if not args.imagem:
                resultado['erro'] = 'Parametro --imagem obrigatorio para formato imagem'
                resultado['mensagem'] = 'Use: python exportar.py --formato imagem --imagem /caminho/imagem.png --nome teste'
                print(json.dumps(resultado, ensure_ascii=False, indent=2))
                return

            filepath, filename = copiar_imagem(args.imagem, args.nome)
            extensao = filepath.rsplit('.', 1)[-1].lower()
            tamanho = os.path.getsize(filepath)

            url_relativa = f"/agente/api/files/default/{filename}"
            url_completa = f"{RENDER_DOMAIN}{url_relativa}"

            resultado['sucesso'] = True
            resultado['arquivo'] = {
                'nome': filename,
                'nome_original': f"{args.nome}.{extensao}",
                'url': url_relativa,
                'url_completa': url_completa,
                'tamanho': tamanho,
                'tamanho_formatado': f"{tamanho / 1024:.1f} KB" if tamanho < 1024*1024 else f"{tamanho / (1024*1024):.1f} MB",
                'formato': 'imagem',
                'tipo_imagem': extensao,
                'caminho_local': filepath
            }
            resultado['mensagem'] = f"Imagem {extensao.upper()} exportada com sucesso!"

            # Instrucao para o agente - imagens podem ser exibidas inline
            resultado['instrucao_agente'] = (
                f"Informe ao usuario que a imagem esta disponivel.\n"
                f"Para EXIBIR a imagem inline:\n"
                f"![{args.nome}]({url_completa})\n\n"
                f"Para link de DOWNLOAD:\n"
                f"📥 **[Clique aqui para baixar]({url_completa}?download=1)**"
            )

            print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))
            return

        # Ler dados do stdin (para excel, csv, json)
        input_data = sys.stdin.read().strip()

        if not input_data:
            resultado['erro'] = 'Nenhum dado recebido via stdin'
            resultado['mensagem'] = 'Use: echo \'{"dados": [...]}\' | python exportar.py ...'
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return

        # Parsear JSON de entrada
        try:
            entrada = json.loads(input_data)
        except json.JSONDecodeError as e:
            resultado['erro'] = f'JSON invalido: {str(e)}'
            resultado['mensagem'] = 'Verifique o formato do JSON de entrada'
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return

        # Extrair dados
        dados = entrada.get('dados', [])

        if not dados:
            resultado['erro'] = 'Campo "dados" vazio ou ausente'
            resultado['mensagem'] = 'O JSON deve conter: {"dados": [...]}'
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return

        # Parsear colunas se fornecido
        colunas = None
        if args.colunas:
            try:
                colunas = json.loads(args.colunas)
            except (json.JSONDecodeError, TypeError):
                pass

        # Gerar arquivo conforme formato
        if args.formato == 'excel':
            filepath, filename = gerar_excel(dados, args.nome, args.titulo, colunas)
            extensao = 'xlsx'
        elif args.formato == 'csv':
            filepath, filename = gerar_csv(dados, args.nome, colunas)
            extensao = 'csv'
        else:  # json
            filepath, filename = gerar_json(dados, args.nome)
            extensao = 'json'

        # Obter tamanho do arquivo
        tamanho = os.path.getsize(filepath)

        # Gerar URL de download
        # Formato: /agente/api/files/{session_id}/{filename}
        url_relativa = f"/agente/api/files/default/{filename}"

        # URL completa com dominio (para uso no Render/producao)
        url_completa = f"{RENDER_DOMAIN}{url_relativa}"

        resultado['sucesso'] = True
        resultado['arquivo'] = {
            'nome': filename,
            'nome_original': f"{args.nome}.{extensao}",
            'url': url_relativa,
            'url_completa': url_completa,
            'tamanho': tamanho,
            'tamanho_formatado': f"{tamanho / 1024:.1f} KB" if tamanho < 1024*1024 else f"{tamanho / (1024*1024):.1f} MB",
            'registros': len(dados),
            'formato': args.formato,
            'caminho_local': filepath  # Para debug
        }
        resultado['mensagem'] = f"Arquivo {args.formato.upper()} criado com {len(dados)} registros!"

        # Instrucao para o agente - SEMPRE usar URL completa
        resultado['instrucao_agente'] = (
            f"Informe ao usuario que o arquivo esta disponivel para download.\n"
            f"IMPORTANTE: Use a URL COMPLETA na resposta (com dominio):\n"
            f"📥 **[Clique aqui para baixar]({url_completa})**\n"
            f"Arquivo: {args.nome}.{extensao} | {len(dados)} registros"
        )

    except ImportError as e:
        resultado['erro'] = f'Dependencia nao instalada: {str(e)}'
        resultado['mensagem'] = 'Execute: pip install pandas xlsxwriter'
    except Exception as e:
        resultado['erro'] = str(e)
        resultado['mensagem'] = 'Erro ao gerar arquivo'

    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()
