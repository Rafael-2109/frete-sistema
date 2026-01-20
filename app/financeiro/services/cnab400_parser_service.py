"""
Parser para arquivos de retorno CNAB400.

Este service é responsável por ler e extrair dados de arquivos .ret (retorno bancário)
no formato CNAB400 (400 bytes por linha).

Características do CNAB400:
- Cada linha tem exatamente 400 caracteres
- Registro tipo 0: Header do arquivo
- Registro tipo 1: Detalhe (transações)
- Registro tipo 9: Trailer do arquivo
- Encoding: latin-1 (ISO-8859-1)
- Valores monetários: sem separador decimal (centavos)
- Datas: DDMMAA ou AAMMDD dependendo do campo

Uso:
    parser = Cnab400ParserService()
    resultado = parser.parse_arquivo(conteudo_arquivo)
    # resultado = {'header': {...}, 'detalhes': [...], 'trailer': {...}, 'erros': [...]}
"""

from datetime import date
from typing import Dict, List, Optional, Any
import re


class Cnab400ParserService:
    """Parser para arquivos de retorno CNAB400"""

    # Mapeamento de códigos de ocorrência para descrições
    OCORRENCIAS = {
        '02': 'Entrada Confirmada',
        '03': 'Entrada Rejeitada',
        '05': 'Liquidação sem Registro',
        '06': 'Liquidação Normal',
        '07': 'Liquidação por Conta',
        '08': 'Liquidação por Saldo',
        '09': 'Baixado Automaticamente',
        '10': 'Baixado conforme Instruções',
        '11': 'Títulos em Ser',
        '12': 'Abatimento Concedido',
        '13': 'Abatimento Cancelado',
        '14': 'Alteração de Vencimento',
        '15': 'Liquidação em Cartório',
        '16': 'Título Pago em Cheque',
        '17': 'Liquidação após Baixa',
        '19': 'Confirmação de Instrução',
        '20': 'Confirmação de Alteração',
        '21': 'Entrada de Título via Banco Correspondente',
        '22': 'Entrada de Título via Correios',
        '23': 'Encaminhado a Protesto',
        '24': 'Sustação de Protesto',
        '25': 'Protestado e Baixado',
        '26': 'Instrução Rejeitada',
        '27': 'Confirmação de Alteração de Dados',
        '28': 'Débito de Tarifas/Custas',
        '29': 'Ocorrência do Sacado',
        '30': 'Alteração de Outros Dados Rejeitada',
    }

    # Mapeamento de códigos de banco para nomes
    BANCOS = {
        '001': 'Banco do Brasil',
        '033': 'Santander',
        '104': 'Caixa Econômica Federal',
        '237': 'Bradesco',
        '274': 'BMP Money Plus',
        '341': 'Itaú',
        '422': 'Safra',
        '748': 'Sicredi',
        '756': 'Sicoob',
    }

    def parse_arquivo(self, conteudo: str) -> Dict[str, Any]:
        """
        Parse completo do arquivo CNAB400.

        Args:
            conteudo: Conteúdo do arquivo .ret como string

        Returns:
            Dicionário com:
            - header: Dados do header (tipo 0)
            - detalhes: Lista de registros de detalhe (tipo 1)
            - trailer: Dados do trailer (tipo 9)
            - erros: Lista de erros encontrados durante o parse
        """
        linhas = conteudo.strip().split('\n')
        resultado = {
            'header': None,
            'detalhes': [],
            'trailer': None,
            'erros': []
        }

        for i, linha in enumerate(linhas, 1):
            # Remove caracteres de controle e garante 400 caracteres
            linha = linha.rstrip('\r\n')
            if len(linha) < 400:
                linha = linha.ljust(400)
            elif len(linha) > 400:
                linha = linha[:400]

            # Identifica tipo de registro pelo primeiro caractere
            tipo = linha[0]

            try:
                if tipo == '0':
                    resultado['header'] = self._parse_header(linha)
                elif tipo == '1':
                    detalhe = self._parse_detalhe(linha, i)
                    if detalhe:
                        resultado['detalhes'].append(detalhe)
                elif tipo == '9':
                    resultado['trailer'] = self._parse_trailer(linha)
                # Ignora outros tipos (2, 3, etc. - registros opcionais)
            except Exception as e:
                resultado['erros'].append({
                    'linha': i,
                    'tipo': tipo,
                    'erro': str(e),
                    'conteudo': linha[:50] + '...' if len(linha) > 50 else linha
                })

        return resultado

    def _parse_header(self, linha: str) -> Dict[str, Any]:
        """
        Parse do registro header (tipo 0).

        Layout BMP 274:
        - Posição 1: Tipo registro (0)
        - Posição 2: Código retorno (2)
        - Posição 3-9: Literal "RETORNO"
        - Posição 10-11: Código serviço (01=Cobrança)
        - Posição 12-26: Literal "COBRANCA"
        - Posição 27-46: Código empresa (CNPJ)
        - Posição 47-76: Nome empresa
        - Posição 77-79: Código banco
        - Posição 80-94: Nome banco
        - Posição 95-100: Data gravação (AAMMDD)
        """
        codigo_banco = linha[76:79].strip()

        return {
            'tipo_registro': '0',
            'codigo_retorno': linha[1:2],
            'literal_retorno': linha[2:9].strip(),
            'codigo_servico': linha[9:11],
            'literal_servico': linha[11:26].strip(),
            'codigo_empresa': linha[26:46].strip(),
            'cnpj_empresa': self._normalizar_cnpj(linha[26:40]),
            'nome_empresa': linha[46:76].strip(),
            'codigo_banco': codigo_banco,
            'nome_banco': self.BANCOS.get(codigo_banco, linha[79:94].strip()),
            'data_arquivo': self._parse_data_ddmmaa(linha[94:100]),  # DDMMAA no header também
            'sequencial': linha[394:400].strip(),
        }

    def _parse_detalhe(self, linha: str, num_linha: int) -> Dict[str, Any]:
        """
        Parse do registro detalhe (tipo 1).

        Layout BMP 274 - Posições principais:
        - 1: Tipo registro (1)
        - 2-3: Tipo inscrição (01=CPF, 02=CNPJ)
        - 4-17: CNPJ/CPF do pagador (sacado)
        - 38-62: Identificação título empresa
        - 63-70: Zeros
        - 71-82: Nosso número
        - 109-110: Código ocorrência
        - 111-116: Data ocorrência (DDMMAA)
        - 117-126: Seu número (NF/Parcela)
        - 147-152: Data vencimento (DDMMAA)
        - 153-165: Valor título (13 dígitos, 2 decimais implícitos)
        - 176-188: Despesas cobrança
        - 228-240: Abatimento
        - 241-253: Desconto
        - 254-266: Valor pago
        - 267-279: Juros mora
        - 395-400: Sequencial
        """
        codigo_ocorrencia = linha[108:110]

        return {
            'tipo_registro': '1',
            'numero_linha': num_linha,
            'tipo_inscricao': linha[1:3],  # 01=CPF, 02=CNPJ
            'cnpj_pagador': self._normalizar_cnpj(linha[3:17]),
            'identificacao_empresa': linha[37:62].strip(),
            'nosso_numero': linha[70:82].strip(),
            'codigo_ocorrencia': codigo_ocorrencia,
            'descricao_ocorrencia': self.OCORRENCIAS.get(codigo_ocorrencia, 'Desconhecida'),
            'data_ocorrencia': self._parse_data_ddmmaa(linha[110:116]),
            'seu_numero': linha[116:126].strip(),
            'data_vencimento': self._parse_data_ddmmaa(linha[146:152]),
            'valor_titulo': self._parse_valor(linha[152:165]),
            'valor_despesas': self._parse_valor(linha[175:188]),
            'valor_abatimento': self._parse_valor(linha[227:240]),
            'valor_desconto': self._parse_valor(linha[240:253]),
            'valor_pago': self._parse_valor(linha[253:266]),
            'valor_juros': self._parse_valor(linha[266:279]),
            'outros_creditos': self._parse_valor(linha[279:292]),
            'motivo_ocorrencia': linha[318:328].strip(),
            'sequencial': linha[394:400].strip(),
            'linha_original': linha,
        }

    def _parse_trailer(self, linha: str) -> Dict[str, Any]:
        """
        Parse do registro trailer (tipo 9).

        Layout BMP 274:
        - Posição 1: Tipo registro (9)
        - Posição 2-3: Código retorno
        - Posição 4-6: Código serviço
        - Posição 7-10: Código banco
        - Posição 18-25: Quantidade títulos
        - Posição 26-39: Valor total
        - Posição 395-400: Sequencial
        """
        return {
            'tipo_registro': '9',
            'codigo_retorno': linha[1:3],
            'codigo_servico': linha[3:6],
            'codigo_banco': linha[6:10].strip(),
            'qtd_titulos': self._parse_inteiro(linha[17:25]),
            'valor_total': self._parse_valor(linha[25:39]),
            'sequencial': linha[394:400].strip(),
        }

    @staticmethod
    def _parse_valor(valor_str: str) -> float:
        """
        Converte valor CNAB (sem separador decimal) para float.

        CNAB400 armazena valores monetários como inteiros representando centavos.
        Ex: "0000002472730" = R$ 24.727,30

        Args:
            valor_str: String com valor em centavos (13 dígitos)

        Returns:
            Valor em reais como float
        """
        valor = valor_str.strip()
        if not valor:
            return 0.0
        # Remove caracteres não numéricos
        valor = ''.join(filter(str.isdigit, valor))
        if not valor:
            return 0.0
        return int(valor) / 100

    @staticmethod
    def _parse_inteiro(valor_str: str) -> int:
        """Converte string para inteiro, retornando 0 se inválido"""
        valor = valor_str.strip()
        if not valor:
            return 0
        valor = ''.join(filter(str.isdigit, valor))
        return int(valor) if valor else 0

    @staticmethod
    def _parse_data_ddmmaa(data_str: str) -> Optional[date]:
        """
        Converte data no formato DDMMAA para objeto date.

        Args:
            data_str: String com 6 caracteres (DDMMAA)

        Returns:
            Objeto date ou None se inválido
        """
        if not data_str or len(data_str) != 6:
            return None
        # Remove espaços
        data_str = data_str.strip()
        if len(data_str) != 6 or not data_str.isdigit():
            return None
        try:
            dia = int(data_str[0:2])
            mes = int(data_str[2:4])
            ano = int(data_str[4:6])
            # Converte ano de 2 dígitos para 4
            # Assume: 00-49 = 2000-2049, 50-99 = 1950-1999
            ano = 2000 + ano if ano < 50 else 1900 + ano
            # Valida data
            if dia < 1 or dia > 31 or mes < 1 or mes > 12:
                return None
            return date(ano, mes, dia)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_data_aammdd(data_str: str) -> Optional[date]:
        """
        Converte data no formato AAMMDD para objeto date.

        Args:
            data_str: String com 6 caracteres (AAMMDD)

        Returns:
            Objeto date ou None se inválido
        """
        if not data_str or len(data_str) != 6:
            return None
        data_str = data_str.strip()
        if len(data_str) != 6 or not data_str.isdigit():
            return None
        try:
            ano = int(data_str[0:2])
            mes = int(data_str[2:4])
            dia = int(data_str[4:6])
            ano = 2000 + ano if ano < 50 else 1900 + ano
            if dia < 1 or dia > 31 or mes < 1 or mes > 12:
                return None
            return date(ano, mes, dia)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalizar_cnpj(cnpj: str) -> str:
        """
        Normaliza CNPJ para formato XX.XXX.XXX/XXXX-XX.

        Args:
            cnpj: String com CNPJ (pode conter formatação)

        Returns:
            CNPJ formatado ou string original se inválido
        """
        # Remove tudo que não é dígito
        cnpj = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
        return cnpj

    def extrair_nf_parcela(self, seu_numero: str) -> tuple:
        """
        Extrai NF e Parcela do campo "Seu Número".

        Formatos suportados:
        - "143820/001" → NF=143820, Parcela=1
        - "143820/01"  → NF=143820, Parcela=1
        - "143204-01"  → NF=143204, Parcela=1
        - "143204-1"   → NF=143204, Parcela=1
        - "142972"     → NF=142972, Parcela=1 (sem parcela = parcela 1)

        Args:
            seu_numero: Valor do campo "Seu Número" do CNAB

        Returns:
            Tupla (nf, parcela) ou (None, None) se formato inválido
        """
        if not seu_numero:
            return (None, None)

        seu_numero = seu_numero.strip()

        # Regex para capturar NF e Parcela com separador
        # Suporta separadores / ou - e parcelas com ou sem zeros à esquerda
        match = re.match(r'^(\d+)[/-]0*(\d+)$', seu_numero)
        if match:
            return (match.group(1), match.group(2))

        # Se não tem separador, assume que é só NF com parcela 1
        match_apenas_nf = re.match(r'^(\d+)$', seu_numero)
        if match_apenas_nf:
            return (match_apenas_nf.group(1), '1')

        return (None, None)
