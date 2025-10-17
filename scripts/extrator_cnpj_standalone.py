#!/usr/bin/env python3
"""
Extrator de CNPJ - Versão Standalone (sem dependências do Flask)
Data: 14/10/2025

USO DIRETO:
    python3 scripts/extrator_cnpj_standalone.py ~/temp_motos/PEDIDOS --output cnpjs.xlsx
"""

import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Optional
import argparse


class ExtratorCNPJ:
    """Classe para extrair CNPJ de planilhas Excel usando múltiplos padrões"""

    REGEX_CNPJ_MASCARA = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'
    REGEX_CNPJ_SEM_MASCARA = r'\b\d{14}\b'
    PALAVRAS_CHAVE_CNPJ = [
        'cnpj', 'cnpj:', 'c.n.p.j', 'c.n.p.j.', 'c.n.p.j:',
        'cadastro nacional', 'cadastro de pessoa jurídica'
    ]
    PALAVRAS_CHAVE_CLIENTE = ['cliente', 'cliente:', 'razão social', 'razao social']

    def __init__(self):
        self.debug = False

    def ativar_debug(self):
        self.debug = True

    def _log(self, mensagem: str):
        if self.debug:
            print(f"[DEBUG] {mensagem}")

    def limpar_cnpj(self, cnpj: str) -> str:
        if not cnpj:
            return ""
        return re.sub(r'[^\d]', '', str(cnpj))

    def validar_cnpj(self, cnpj: str) -> bool:
        cnpj_limpo = self.limpar_cnpj(cnpj)
        return len(cnpj_limpo) == 14

    def formatar_cnpj(self, cnpj: str) -> str:
        cnpj_limpo = self.limpar_cnpj(cnpj)
        if len(cnpj_limpo) != 14:
            return cnpj
        return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"

    def _get_column_letter(self, col_idx: int) -> str:
        result = ""
        col_idx += 1
        while col_idx > 0:
            col_idx -= 1
            result = chr(col_idx % 26 + 65) + result
            col_idx //= 26
        return result

    def buscar_padrao1_celula_ao_lado(self, df: pd.DataFrame, nome_aba: str) -> Optional[Dict]:
        self._log(f"[Padrão 1] Buscando em aba '{nome_aba}'...")

        for i, row in df.iterrows():
            for j, valor in enumerate(row):
                if pd.isna(valor):
                    continue

                valor_str = str(valor).strip().lower()

                if any(palavra in valor_str for palavra in self.PALAVRAS_CHAVE_CNPJ):
                    self._log(f"  Palavra-chave encontrada em ({i}, {j}): '{valor}'")

                    # Buscar à direita
                    if j + 1 < len(row):
                        cnpj_candidato = str(row.iloc[j + 1]).strip()
                        if self.validar_cnpj(cnpj_candidato):
                            return {
                                'cnpj': self.limpar_cnpj(cnpj_candidato),
                                'cnpj_formatado': self.formatar_cnpj(cnpj_candidato),
                                'padrao': 'Padrão 1: Célula ao lado de "CNPJ"',
                                'aba': nome_aba,
                                'celula': f'{self._get_column_letter(j+1)}{i+2}',
                                'valor_original': cnpj_candidato
                            }

                    # Buscar abaixo
                    if i + 1 < len(df):
                        cnpj_candidato = str(df.iloc[i + 1, j]).strip()
                        if self.validar_cnpj(cnpj_candidato):
                            return {
                                'cnpj': self.limpar_cnpj(cnpj_candidato),
                                'cnpj_formatado': self.formatar_cnpj(cnpj_candidato),
                                'padrao': 'Padrão 1: Célula abaixo de "CNPJ"',
                                'aba': nome_aba,
                                'celula': f'{self._get_column_letter(j)}{i+3}',
                                'valor_original': cnpj_candidato
                            }
        return None

    def buscar_padrao2_cnpj_colado(self, df: pd.DataFrame, nome_aba: str) -> Optional[Dict]:
        self._log(f"[Padrão 2] Buscando em aba '{nome_aba}'...")

        for i, row in df.iterrows():
            for j, valor in enumerate(row):
                if pd.isna(valor):
                    continue

                valor_str = str(valor).strip()
                valor_lower = valor_str.lower()

                if any(palavra in valor_lower for palavra in self.PALAVRAS_CHAVE_CNPJ):
                    for palavra in self.PALAVRAS_CHAVE_CNPJ:
                        if palavra in valor_lower:
                            idx = valor_lower.index(palavra) + len(palavra)
                            resto = valor_str[idx:].strip()
                            cnpj_candidato = self.limpar_cnpj(resto[:20])

                            if self.validar_cnpj(cnpj_candidato):
                                return {
                                    'cnpj': cnpj_candidato,
                                    'cnpj_formatado': self.formatar_cnpj(cnpj_candidato),
                                    'padrao': 'Padrão 2: CNPJ colado',
                                    'aba': nome_aba,
                                    'celula': f'{self._get_column_letter(j)}{i+2}',
                                    'valor_original': valor_str
                                }
        return None

    def buscar_padrao3_regex_mascara(self, df: pd.DataFrame, nome_aba: str) -> Optional[Dict]:
        self._log(f"[Padrão 3] Buscando em aba '{nome_aba}'...")

        for i, row in df.iterrows():
            for j, valor in enumerate(row):
                if pd.isna(valor):
                    continue

                valor_str = str(valor).strip()
                match = re.search(self.REGEX_CNPJ_MASCARA, valor_str)

                if match:
                    cnpj_encontrado = match.group(0)
                    if self.validar_cnpj(cnpj_encontrado):
                        return {
                            'cnpj': self.limpar_cnpj(cnpj_encontrado),
                            'cnpj_formatado': cnpj_encontrado,
                            'padrao': 'Padrão 3: Máscara ##.###.###/####-##',
                            'aba': nome_aba,
                            'celula': f'{self._get_column_letter(j)}{i+2}',
                            'valor_original': valor_str
                        }
        return None

    def buscar_nome_cliente(self, df: pd.DataFrame, nome_aba: str) -> Optional[str]:
        """Busca o nome do cliente após palavras-chave como 'Cliente:'"""
        self._log(f"[Nome Cliente] Buscando em aba '{nome_aba}'...")

        for i, row in df.iterrows():
            for j, valor in enumerate(row):
                if pd.isna(valor):
                    continue

                valor_str = str(valor).strip()
                valor_lower = valor_str.lower()

                # Procurar por palavra-chave de cliente
                for palavra in self.PALAVRAS_CHAVE_CLIENTE:
                    if palavra in valor_lower:
                        self._log(f"  Palavra-chave '{palavra}' encontrada em ({i}, {j})")

                        # Tentar extrair nome da mesma célula (após "Cliente:")
                        idx = valor_lower.index(palavra) + len(palavra)
                        nome_candidato = valor_str[idx:].strip()

                        # Se tem conteúdo após a palavra-chave
                        if nome_candidato and len(nome_candidato) > 3:
                            # Remover pontuação inicial
                            nome_candidato = nome_candidato.lstrip(':').strip()
                            if nome_candidato and len(nome_candidato) > 3:
                                self._log(f"  Nome encontrado na mesma célula: '{nome_candidato}'")
                                return nome_candidato

                        # Buscar na célula à direita
                        if j + 1 < len(row):
                            nome_candidato = str(row.iloc[j + 1]).strip()
                            if nome_candidato and nome_candidato.lower() not in ['nan', 'none', ''] and len(nome_candidato) > 3:
                                self._log(f"  Nome encontrado à direita: '{nome_candidato}'")
                                return nome_candidato

                        # Buscar na célula abaixo
                        if i + 1 < len(df):
                            nome_candidato = str(df.iloc[i + 1, j]).strip()
                            if nome_candidato and nome_candidato.lower() not in ['nan', 'none', ''] and len(nome_candidato) > 3:
                                self._log(f"  Nome encontrado abaixo: '{nome_candidato}'")
                                return nome_candidato

        return None

    def buscar_cnpj_em_aba(self, df: pd.DataFrame, nome_aba: str) -> Optional[Dict]:
        self._log(f"\n=== Processando aba: {nome_aba} ===")

        resultado = self.buscar_padrao1_celula_ao_lado(df, nome_aba)
        if resultado:
            # Buscar nome do cliente também
            nome_cliente = self.buscar_nome_cliente(df, nome_aba)
            if nome_cliente:
                resultado['nome_cliente'] = nome_cliente
            return resultado

        resultado = self.buscar_padrao2_cnpj_colado(df, nome_aba)
        if resultado:
            # Buscar nome do cliente também
            nome_cliente = self.buscar_nome_cliente(df, nome_aba)
            if nome_cliente:
                resultado['nome_cliente'] = nome_cliente
            return resultado

        resultado = self.buscar_padrao3_regex_mascara(df, nome_aba)
        if resultado:
            # Buscar nome do cliente também
            nome_cliente = self.buscar_nome_cliente(df, nome_aba)
            if nome_cliente:
                resultado['nome_cliente'] = nome_cliente
            return resultado

        return None

    def buscar_cnpj_em_arquivo(self, caminho_arquivo: str) -> Dict:
        caminho = Path(caminho_arquivo)

        resultado_arquivo = {
            'arquivo': caminho.name,
            'caminho_completo': str(caminho.absolute()),
            'cnpj': None,
            'cnpj_formatado': None,
            'nome_cliente': None,
            'padrao': None,
            'aba': None,
            'celula': None,
            'valor_original': None,
            'sucesso': False,
            'erro': None
        }

        try:
            self._log(f"\n{'='*60}")
            self._log(f"Processando arquivo: {caminho.name}")

            excel_file = pd.ExcelFile(caminho_arquivo, engine='openpyxl')
            self._log(f"Abas encontradas: {excel_file.sheet_names}")

            for nome_aba in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=nome_aba, header=None)
                resultado_aba = self.buscar_cnpj_em_aba(df, nome_aba)

                if resultado_aba:
                    resultado_arquivo.update({
                        'cnpj': resultado_aba['cnpj'],
                        'cnpj_formatado': resultado_aba['cnpj_formatado'],
                        'nome_cliente': resultado_aba.get('nome_cliente'),
                        'padrao': resultado_aba['padrao'],
                        'aba': resultado_aba['aba'],
                        'celula': resultado_aba['celula'],
                        'valor_original': resultado_aba['valor_original'],
                        'sucesso': True
                    })
                    break

            if not resultado_arquivo['sucesso']:
                resultado_arquivo['erro'] = "CNPJ não encontrado"

        except Exception as e:
            resultado_arquivo['erro'] = f"Erro: {str(e)}"
            self._log(f"❌ ERRO: {str(e)}")

        return resultado_arquivo

    def buscar_cnpj_em_multiplas_planilhas(self, caminhos_arquivos: List[str]) -> List[Dict]:
        resultados = []

        print(f"\n{'='*60}")
        print(f"EXTRATOR DE CNPJ - MÚLTIPLAS PLANILHAS")
        print(f"{'='*60}")
        print(f"Total de arquivos: {len(caminhos_arquivos)}\n")

        for i, caminho in enumerate(caminhos_arquivos, 1):
            print(f"[{i}/{len(caminhos_arquivos)}] {Path(caminho).name}", end=" ... ")

            resultado = self.buscar_cnpj_em_arquivo(caminho)
            resultados.append(resultado)

            if resultado['sucesso']:
                msg = f"✅ {resultado['cnpj_formatado']}"
                if resultado.get('nome_cliente'):
                    msg += f" | {resultado['nome_cliente'][:40]}"
                print(msg)
            else:
                print(f"❌ {resultado['erro']}")

        # Resumo
        encontrados = sum(1 for r in resultados if r['sucesso'])
        print(f"\n{'='*60}")
        print(f"✅ CNPJs encontrados: {encontrados}/{len(resultados)}")
        print(f"{'='*60}\n")

        return resultados

    def exportar_resultados_excel(self, resultados: List[Dict], caminho_saida: str):
        df = pd.DataFrame(resultados)
        df.to_excel(caminho_saida, index=False, engine='openpyxl')
        print(f"✅ Resultados exportados: {caminho_saida}")


def obter_arquivos_excel(caminho: str) -> list:
    caminho_path = Path(caminho)

    if caminho_path.is_file():
        if caminho_path.suffix.lower() in ['.xlsx', '.xls', '.xlsm']:
            return [str(caminho_path)]
        return []

    elif caminho_path.is_dir():
        arquivos = []
        for extensao in ['*.xlsx', '.xls', '*.xlsm']:
            arquivos.extend(caminho_path.glob(extensao))
        return [str(f) for f in arquivos]

    return []


def main():
    parser = argparse.ArgumentParser(description='Extrai CNPJ de planilhas Excel')
    parser.add_argument('caminho', help='Pasta ou arquivo Excel')
    parser.add_argument('--output', '-o', default='cnpjs_encontrados.xlsx', help='Arquivo de saída')
    parser.add_argument('--debug', action='store_true', help='Modo debug')

    args = parser.parse_args()

    arquivos = obter_arquivos_excel(args.caminho)

    if not arquivos:
        print(f"\n❌ Nenhum arquivo Excel encontrado em: {args.caminho}")
        return 1

    extrator = ExtratorCNPJ()
    if args.debug:
        extrator.ativar_debug()

    resultados = extrator.buscar_cnpj_em_multiplas_planilhas(arquivos)
    extrator.exportar_resultados_excel(resultados, args.output)

    # CNPJs únicos
    cnpjs_unicos = {}
    for r in resultados:
        if r['sucesso']:
            cnpj = r['cnpj_formatado']
            if cnpj not in cnpjs_unicos:
                cnpjs_unicos[cnpj] = []
            cnpjs_unicos[cnpj].append(r['arquivo'])

    if cnpjs_unicos:
        print(f"\n{'='*60}")
        print("CNPJs ÚNICOS ENCONTRADOS")
        print(f"{'='*60}")
        for cnpj, arquivos in sorted(cnpjs_unicos.items()):
            print(f"\n📋 {cnpj} ({len(arquivos)} arquivo(s))")
            for arq in arquivos[:5]:
                print(f"   - {arq}")
            if len(arquivos) > 5:
                print(f"   ... e mais {len(arquivos) - 5} arquivo(s)")

    return 0


if __name__ == '__main__':
    exit(main())
