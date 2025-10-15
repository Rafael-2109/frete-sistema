"""
Extrator de CNPJ de Múltiplas Planilhas Excel
Data: 14/10/2025

OBJETIVO:
Buscar CNPJ em planilhas Excel usando 3 padrões diferentes:
1. Célula ao lado de "CNPJ" ou "CNPJ:"
2. String no formato "CNPJ{numero}"
3. Qualquer texto com máscara ##.###.###/####-##

MODO DE USO:
    from app.motochefe.services.extrator_cnpj_planilhas import ExtratorCNPJ

    extrator = ExtratorCNPJ()

    # Buscar em múltiplas planilhas
    resultados = extrator.buscar_cnpj_em_multiplas_planilhas([
        '/caminho/planilha1.xlsx',
        '/caminho/planilha2.xls',
        '/caminho/planilha3.xlsx'
    ])

    # Exibir resultados
    for resultado in resultados:
        print(f"Arquivo: {resultado['arquivo']}")
        print(f"CNPJ encontrado: {resultado['cnpj']}")
        print(f"Padrão usado: {resultado['padrao']}")
        print(f"Localização: Aba '{resultado['aba']}' - Célula {resultado['celula']}")
"""

import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Optional


class ExtratorCNPJ:
    """Classe para extrair CNPJ de planilhas Excel usando múltiplos padrões"""

    # Regex para CNPJ com máscara: ##.###.###/####-##
    REGEX_CNPJ_MASCARA = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'

    # Regex para CNPJ sem máscara: 14 dígitos
    REGEX_CNPJ_SEM_MASCARA = r'\b\d{14}\b'

    # Palavras-chave que indicam CNPJ na célula anterior/superior
    PALAVRAS_CHAVE_CNPJ = [
        'cnpj', 'cnpj:', 'c.n.p.j', 'c.n.p.j.', 'c.n.p.j:',
        'cadastro nacional', 'cadastro de pessoa jurídica'
    ]

    def __init__(self):
        """Inicializa o extrator"""
        self.debug = False

    def ativar_debug(self):
        """Ativa modo debug com logs detalhados"""
        self.debug = True

    def _log(self, mensagem: str):
        """Log condicional baseado em debug"""
        if self.debug:
            print(f"[DEBUG] {mensagem}")

    def limpar_cnpj(self, cnpj: str) -> str:
        """Remove caracteres especiais do CNPJ, mantendo apenas números"""
        if not cnpj:
            return ""
        return re.sub(r'[^\d]', '', str(cnpj))

    def validar_cnpj(self, cnpj: str) -> bool:
        """
        Valida se CNPJ tem 14 dígitos
        (Validação simplificada - não verifica dígito verificador)
        """
        cnpj_limpo = self.limpar_cnpj(cnpj)
        return len(cnpj_limpo) == 14

    def formatar_cnpj(self, cnpj: str) -> str:
        """Formata CNPJ no padrão ##.###.###/####-##"""
        cnpj_limpo = self.limpar_cnpj(cnpj)
        if len(cnpj_limpo) != 14:
            return cnpj  # Retorna original se inválido

        return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"

    def buscar_padrao1_celula_ao_lado(self, df: pd.DataFrame, nome_aba: str) -> Optional[Dict]:
        """
        PADRÃO 1: Busca CNPJ na célula ao lado (direita) de "CNPJ" ou "CNPJ:"

        Exemplo:
            | CNPJ: | 12.345.678/0001-90 |
            | CNPJ  | 12345678000190     |
        """
        self._log(f"[Padrão 1] Buscando em aba '{nome_aba}'...")

        for i, row in df.iterrows():
            for j, valor in enumerate(row):
                if pd.isna(valor):
                    continue

                valor_str = str(valor).strip().lower()

                # Verifica se célula contém palavra-chave
                if any(palavra in valor_str for palavra in self.PALAVRAS_CHAVE_CNPJ):
                    self._log(f"  Palavra-chave encontrada em ({i}, {j}): '{valor}'")

                    # Buscar CNPJ na célula à direita
                    if j + 1 < len(row):
                        cnpj_candidato = str(row.iloc[j + 1]).strip()

                        if self.validar_cnpj(cnpj_candidato):
                            return {
                                'cnpj': self.limpar_cnpj(cnpj_candidato),
                                'cnpj_formatado': self.formatar_cnpj(cnpj_candidato),
                                'padrao': 'Padrão 1: Célula ao lado de "CNPJ"',
                                'aba': nome_aba,
                                'celula': f'{self._get_column_letter(j+1)}{i+2}',  # +2 porque Excel começa em 1 e tem header 
                                'valor_original': cnpj_candidato
                            }

                    # Buscar CNPJ na célula abaixo
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
        """
        PADRÃO 2: Busca string no formato "CNPJ{numero}" (colado, sem espaço)

        Exemplo:
            "CNPJ12.345.678/0001-90"
            "CNPJ12345678000190"
            "C.N.P.J.12345678000190"
        """
        self._log(f"[Padrão 2] Buscando em aba '{nome_aba}'...")

        for i, row in df.iterrows():
            for j, valor in enumerate(row):
                if pd.isna(valor):
                    continue

                valor_str = str(valor).strip()
                valor_lower = valor_str.lower()

                # Verificar se contém palavra-chave + número
                if any(palavra in valor_lower for palavra in self.PALAVRAS_CHAVE_CNPJ):
                    # Extrair números após a palavra-chave
                    # Remove a palavra-chave e pega os números
                    for palavra in self.PALAVRAS_CHAVE_CNPJ:
                        if palavra in valor_lower:
                            # Pegar tudo após a palavra-chave
                            idx = valor_lower.index(palavra) + len(palavra)
                            resto = valor_str[idx:].strip()

                            # Extrair CNPJ (pode ter máscara ou não)
                            cnpj_candidato = self.limpar_cnpj(resto[:20])  # Pegar primeiros 20 chars para segurança

                            if self.validar_cnpj(cnpj_candidato):
                                return {
                                    'cnpj': cnpj_candidato,
                                    'cnpj_formatado': self.formatar_cnpj(cnpj_candidato),
                                    'padrao': 'Padrão 2: CNPJ colado (ex: "CNPJ12345678000190")',
                                    'aba': nome_aba,
                                    'celula': f'{self._get_column_letter(j)}{i+2}',
                                    'valor_original': valor_str
                                }

        return None

    def buscar_padrao3_regex_mascara(self, df: pd.DataFrame, nome_aba: str) -> Optional[Dict]:
        """
        PADRÃO 3: Busca qualquer texto com máscara ##.###.###/####-##

        Exemplo:
            "12.345.678/0001-90"
            "Empresa XYZ - CNPJ: 12.345.678/0001-90"
        """
        self._log(f"[Padrão 3] Buscando em aba '{nome_aba}'...")

        for i, row in df.iterrows():
            for j, valor in enumerate(row):
                if pd.isna(valor):
                    continue

                valor_str = str(valor).strip()

                # Buscar padrão de CNPJ com máscara
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

    def buscar_cnpj_em_aba(self, df: pd.DataFrame, nome_aba: str) -> Optional[Dict]:
        """
        Busca CNPJ em uma aba específica usando os 3 padrões em ordem de prioridade

        Retorna o primeiro CNPJ encontrado ou None
        """
        self._log(f"\n=== Processando aba: {nome_aba} ===")

        # Padrão 1: Célula ao lado de "CNPJ"
        resultado = self.buscar_padrao1_celula_ao_lado(df, nome_aba)
        if resultado:
            self._log(f"✅ CNPJ encontrado com Padrão 1: {resultado['cnpj_formatado']}")
            return resultado

        # Padrão 2: CNPJ colado (ex: "CNPJ12345678000190")
        resultado = self.buscar_padrao2_cnpj_colado(df, nome_aba)
        if resultado:
            self._log(f"✅ CNPJ encontrado com Padrão 2: {resultado['cnpj_formatado']}")
            return resultado

        # Padrão 3: Regex com máscara
        resultado = self.buscar_padrao3_regex_mascara(df, nome_aba)
        if resultado:
            self._log(f"✅ CNPJ encontrado com Padrão 3: {resultado['cnpj_formatado']}")
            return resultado

        self._log(f"❌ Nenhum CNPJ encontrado na aba '{nome_aba}'")
        return None

    def buscar_cnpj_em_arquivo(self, caminho_arquivo: str) -> Dict:
        """
        Busca CNPJ em todas as abas de um arquivo Excel

        Retorna dicionário com resultado da busca
        """
        caminho = Path(caminho_arquivo)

        resultado_arquivo = {
            'arquivo': caminho.name,
            'caminho_completo': str(caminho.absolute()),
            'cnpj': None,
            'cnpj_formatado': None,
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
            self._log(f"{'='*60}")

            # Ler todas as abas
            excel_file = pd.ExcelFile(caminho_arquivo, engine='openpyxl')

            self._log(f"Abas encontradas: {excel_file.sheet_names}")

            for nome_aba in excel_file.sheet_names:
                # Ler aba como DataFrame (sem assumir header)
                df = pd.read_excel(
                    excel_file,
                    sheet_name=nome_aba,
                    header=None  # Não assumir header para buscar em qualquer lugar
                )

                # Buscar CNPJ na aba
                resultado_aba = self.buscar_cnpj_em_aba(df, nome_aba)

                if resultado_aba:
                    resultado_arquivo.update({
                        'cnpj': resultado_aba['cnpj'],
                        'cnpj_formatado': resultado_aba['cnpj_formatado'],
                        'padrao': resultado_aba['padrao'],
                        'aba': resultado_aba['aba'],
                        'celula': resultado_aba['celula'],
                        'valor_original': resultado_aba['valor_original'],
                        'sucesso': True
                    })
                    break  # Parar na primeira aba que encontrar CNPJ

            if not resultado_arquivo['sucesso']:
                resultado_arquivo['erro'] = "CNPJ não encontrado em nenhuma aba"

        except Exception as e:
            resultado_arquivo['erro'] = f"Erro ao processar arquivo: {str(e)}"
            self._log(f"❌ ERRO: {str(e)}")

        return resultado_arquivo

    def buscar_cnpj_em_multiplas_planilhas(self, caminhos_arquivos: List[str]) -> List[Dict]:
        """
        Busca CNPJ em múltiplas planilhas Excel

        Args:
            caminhos_arquivos: Lista de caminhos para arquivos Excel

        Returns:
            Lista de dicionários com resultados de cada arquivo
        """
        resultados = []

        print(f"\n{'='*60}")
        print(f"EXTRATOR DE CNPJ - MÚLTIPLAS PLANILHAS")
        print(f"{'='*60}")
        print(f"Total de arquivos a processar: {len(caminhos_arquivos)}\n")

        for i, caminho in enumerate(caminhos_arquivos, 1):
            print(f"\n[{i}/{len(caminhos_arquivos)}] Processando: {Path(caminho).name}")

            resultado = self.buscar_cnpj_em_arquivo(caminho)
            resultados.append(resultado)

            # Exibir resultado resumido
            if resultado['sucesso']:
                print(f"  ✅ CNPJ: {resultado['cnpj_formatado']}")
                print(f"  📋 Padrão: {resultado['padrao']}")
                print(f"  📄 Aba: {resultado['aba']} | Célula: {resultado['celula']}")
            else:
                print(f"  ❌ {resultado['erro']}")

        # Resumo final
        print(f"\n{'='*60}")
        print("RESUMO FINAL")
        print(f"{'='*60}")

        encontrados = sum(1 for r in resultados if r['sucesso'])
        nao_encontrados = len(resultados) - encontrados

        print(f"✅ CNPJs encontrados: {encontrados}")
        print(f"❌ CNPJs não encontrados: {nao_encontrados}")
        print(f"📊 Total processado: {len(resultados)}")

        return resultados

    def exportar_resultados_csv(self, resultados: List[Dict], caminho_saida: str):
        """
        Exporta resultados para CSV

        Args:
            resultados: Lista de resultados da busca
            caminho_saida: Caminho do arquivo CSV de saída
        """
        df = pd.DataFrame(resultados)
        df.to_csv(caminho_saida, index=False, encoding='utf-8-sig')
        print(f"\n✅ Resultados exportados para: {caminho_saida}")

    def exportar_resultados_excel(self, resultados: List[Dict], caminho_saida: str):
        """
        Exporta resultados para Excel

        Args:
            resultados: Lista de resultados da busca
            caminho_saida: Caminho do arquivo Excel de saída
        """
        df = pd.DataFrame(resultados)
        df.to_excel(caminho_saida, index=False, engine='openpyxl')
        print(f"\n✅ Resultados exportados para: {caminho_saida}")

    def _get_column_letter(self, col_idx: int) -> str:
        """Converte índice de coluna (0-based) para letra Excel (A, B, C...)"""
        result = ""
        col_idx += 1  # Converter para 1-based

        while col_idx > 0:
            col_idx -= 1
            result = chr(col_idx % 26 + 65) + result
            col_idx //= 26

        return result


# ============================================================
# EXEMPLO DE USO
# ============================================================

if __name__ == '__main__':
    """Exemplo de uso do extrator"""

    # Criar instância do extrator
    extrator = ExtratorCNPJ()

    # Ativar modo debug para ver logs detalhados
    extrator.ativar_debug()

    # Lista de arquivos para processar
    arquivos = [
        '/caminho/para/planilha1.xlsx',
        '/caminho/para/planilha2.xls',
        '/caminho/para/planilha3.xlsx',
    ]

    # Buscar CNPJ em múltiplas planilhas
    resultados = extrator.buscar_cnpj_em_multiplas_planilhas(arquivos)

    # Exportar resultados
    extrator.exportar_resultados_excel(resultados, '/tmp/cnpjs_encontrados.xlsx')

    # Ou processar resultados individualmente
    for resultado in resultados:
        if resultado['sucesso']:
            print(f"\nArquivo: {resultado['arquivo']}")
            print(f"CNPJ: {resultado['cnpj_formatado']}")
            print(f"Localização: {resultado['aba']} - {resultado['celula']}")
