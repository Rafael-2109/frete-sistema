"""
Identificador de documentos de redes de atacarejo

Detecta automaticamente:
- Rede: ATACADAO, TENDA, ASSAI
- Tipo: PROPOSTA ou PEDIDO

Utiliza os prefixos de CNPJ definidos em app/portal/utils/grupo_empresarial.py
"""

import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import pdfplumber

# Importa os prefixos do módulo existente
from app.portal.utils.grupo_empresarial import GRUPOS_EMPRESARIAIS, GrupoEmpresarial


@dataclass
class IdentificacaoDocumento:
    """Resultado da identificação de um documento"""
    rede: str  # 'ATACADAO', 'TENDA', 'ASSAI'
    tipo: str  # 'PROPOSTA', 'PEDIDO'
    numero_documento: Optional[str] = None
    confianca: float = 0.0  # 0.0 a 1.0
    detalhes: Optional[Dict] = None


class IdentificadorDocumento:
    """
    Identifica automaticamente a rede e tipo de documento a partir de um PDF

    Uso:
        identificador = IdentificadorDocumento()
        resultado = identificador.identificar(pdf_path)
        print(f"Rede: {resultado.rede}, Tipo: {resultado.tipo}")
    """

    # Padrões de texto para identificação de REDE (complementar aos CNPJs)
    PADROES_TEXTO_REDE = {
        'ATACADAO': [
            r'ATACADAO\s*S\.?A\.?',
            r'A\s*T\s*A\s*C\s*A\s*D\s*A\s*O',  # Texto espaçado (formato matricial)
            r'CCPMERM01',  # Código do sistema Atacadão (Proposta)
            r'Proposta\s+de\s+Compra',  # Header proposta Atacadão
        ],
        'TENDA': [
            r'TENDA\s*ATACADO',
            r'TENDA\s*DISTRIBUICAO',
            r'T\s*E\s*N\s*D\s*A',  # Texto espaçado
        ],
        'ASSAI': [
            r'ASSAI\s*ATACADISTA',
            r'SENDAS\s*DISTRIBUIDORA',
            r'A\s*S\s*S\s*A\s*I',  # Texto espaçado
        ]
    }

    # Padrões para identificação de TIPO
    PADROES_TIPO = {
        'PROPOSTA': {
            'textos': [
                r'Proposta\s+de\s+Compra',
                r'PROPOSTA\s+DE\s+COMPRA',
                r'Proposta:?\s*\d+',
                r'Proposta\s+N[º°]?\s*\d+',
            ],
            'peso': [1.0, 1.0, 0.9, 0.9]
        },
        'PEDIDO': {
            'textos': [
                r'PEDIDO\s+DE\s+COMPRA',
                r'P\s*E\s*D\s*I\s*D\s*O\s+D\s*E\s+C\s*O\s*M\s*P\s*R\s*A',  # Texto espaçado
                r'P\s+E\s+D\s+I\s+D\s+O',  # Apenas PEDIDO muito espaçado
                r'Pedido\s+EDI',  # "Pedido EDI" sem número
                r'Numero:\s*\d+',  # Campo Numero: XXXX (específico do Atacadão PEDIDO)
                r'Local\s+de\s+Entrega:',  # Campo que só existe em PEDIDO
                r'M\s*E\s*R\s*C\s*A\s*D\s*O\s*R\s*I\s*A',  # Header da tabela de produtos
                r'ORDEM\s+DE\s+COMPRA',
            ],
            'peso': [1.0, 1.0, 0.9, 0.8, 0.9, 0.7, 0.6, 0.8]
        }
    }

    # Padrões para extrair número do documento
    PADROES_NUMERO = {
        'ATACADAO_PROPOSTA': r'Proposta:?\s*(\d+)',
        'ATACADAO_PEDIDO': r'Numero:\s*(\d+)',  # Campo "Numero: 988186" no canto superior direito
        'TENDA': r'Pedido:?\s*(\d+)',
        'ASSAI': r'Pedido:?\s*(\d+)',
    }

    def __init__(self):
        self.texto_completo = ""
        self.texto_primeira_pagina = ""
        self._build_cnpj_patterns()

    def _build_cnpj_patterns(self):
        """Constrói padrões de CNPJ a partir do GRUPOS_EMPRESARIAIS"""
        self.padroes_cnpj = {}

        for codigo_grupo, info in GRUPOS_EMPRESARIAIS.items():
            rede = codigo_grupo.upper()
            padroes = []

            for prefixo in info['prefixos']:
                # Padrão sem formatação: 93209765
                padroes.append(prefixo)

                # Padrão com formatação parcial: 93.209.765
                if len(prefixo) == 8:
                    formatado = f"{prefixo[:2]}\\.?{prefixo[2:5]}\\.?{prefixo[5:8]}"
                    padroes.append(formatado)

            self.padroes_cnpj[rede] = padroes

    def identificar(self, pdf_path: str) -> IdentificacaoDocumento:
        """
        Identifica a rede e tipo de documento

        Args:
            pdf_path: Caminho do arquivo PDF

        Returns:
            IdentificacaoDocumento com rede, tipo e número
        """
        # Extrai texto do PDF
        self._extrair_texto(pdf_path)

        # Identifica a rede
        rede, confianca_rede = self._identificar_rede()

        # Identifica o tipo
        tipo, confianca_tipo = self._identificar_tipo()

        # Extrai número do documento
        numero = self._extrair_numero_documento(rede, tipo)

        # Calcula confiança geral
        confianca = (confianca_rede + confianca_tipo) / 2

        return IdentificacaoDocumento(
            rede=rede,
            tipo=tipo,
            numero_documento=numero,
            confianca=confianca,
            detalhes={
                'confianca_rede': confianca_rede,
                'confianca_tipo': confianca_tipo,
                'texto_encontrado': self.texto_primeira_pagina[:500] if self.texto_primeira_pagina else None
            }
        )

    def _extrair_texto(self, pdf_path: str):
        """Extrai texto do PDF usando pdfplumber"""
        self.texto_completo = ""
        self.texto_primeira_pagina = ""

        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extrai primeira página para identificação
                if pdf.pages:
                    self.texto_primeira_pagina = pdf.pages[0].extract_text() or ""

                # Extrai texto completo (primeiras 3 páginas)
                for i, page in enumerate(pdf.pages[:3]):
                    texto = page.extract_text() or ""
                    self.texto_completo += texto + "\n"

        except Exception as e:
            print(f"Erro ao extrair texto do PDF: {e}")

    def _identificar_rede(self) -> Tuple[str, float]:
        """
        Identifica a rede do documento usando CNPJs e padrões de texto

        Returns:
            Tupla (nome_rede, confianca)
        """
        melhor_rede = "DESCONHECIDA"
        melhor_score = 0.0

        texto = self.texto_primeira_pagina

        # 1. Primeiro tenta identificar por CNPJ (mais confiável)
        for rede, padroes in self.padroes_cnpj.items():
            for padrao in padroes:
                if re.search(padrao, texto):
                    # CNPJ encontrado tem alta confiança
                    if 0.95 > melhor_score:
                        melhor_score = 0.95
                        melhor_rede = rede
                    break

        # 2. Se não encontrou por CNPJ, tenta por padrões de texto
        if melhor_score < 0.9:
            for rede, padroes in self.PADROES_TEXTO_REDE.items():
                for padrao in padroes:
                    if re.search(padrao, texto, re.IGNORECASE):
                        score = 0.8  # Texto tem confiança menor que CNPJ
                        if score > melhor_score:
                            melhor_score = score
                            melhor_rede = rede
                        break

        return melhor_rede, melhor_score

    def _identificar_tipo(self) -> Tuple[str, float]:
        """
        Identifica o tipo de documento (PROPOSTA ou PEDIDO)

        Returns:
            Tupla (tipo, confianca)
        """
        melhor_tipo = "DESCONHECIDO"
        melhor_score = 0.0

        texto = self.texto_primeira_pagina

        for tipo, config in self.PADROES_TIPO.items():
            score = 0.0
            matches = 0

            for i, padrao in enumerate(config['textos']):
                if re.search(padrao, texto, re.IGNORECASE):
                    score += config['peso'][i]
                    matches += 1

            # Normaliza score
            if matches > 0:
                score_normalizado = score / sum(config['peso'])
                if score_normalizado > melhor_score:
                    melhor_score = score_normalizado
                    melhor_tipo = tipo

        return melhor_tipo, melhor_score

    def _extrair_numero_documento(self, rede: str, tipo: str) -> Optional[str]:
        """
        Extrai o número do documento

        Args:
            rede: Nome da rede identificada
            tipo: Tipo do documento identificado

        Returns:
            Número do documento ou None
        """
        texto = self.texto_primeira_pagina

        # Monta chave para buscar padrão
        chave = f"{rede}_{tipo}"

        # Tenta padrão específico primeiro
        if chave in self.PADROES_NUMERO:
            match = re.search(self.PADROES_NUMERO[chave], texto, re.IGNORECASE)
            if match:
                return match.group(1)

        # Tenta padrão genérico da rede
        if rede in self.PADROES_NUMERO:
            match = re.search(self.PADROES_NUMERO[rede], texto, re.IGNORECASE)
            if match:
                return match.group(1)

        # Tenta padrões genéricos
        padroes_genericos = [
            r'Proposta:?\s*(\d+)',
            r'Pedido\s+EDI:?\s*N?\s*(\d+)',
            r'Pedido:?\s*(\d+)',
            r'N[º°]\s*(\d+)',
        ]

        for padrao in padroes_genericos:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                return match.group(1)

        return None


def identificar_documento(pdf_path: str) -> IdentificacaoDocumento:
    """
    Função utilitária para identificar documento

    Args:
        pdf_path: Caminho do arquivo PDF

    Returns:
        IdentificacaoDocumento
    """
    identificador = IdentificadorDocumento()
    return identificador.identificar(pdf_path)


# Para testes
if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        resultado = identificar_documento(pdf_path)
        print(f"\n=== Identificação do Documento ===")
        print(f"Rede: {resultado.rede}")
        print(f"Tipo: {resultado.tipo}")
        print(f"Número: {resultado.numero_documento}")
        print(f"Confiança: {resultado.confianca:.2%}")
        print(f"\nDetalhes: {resultado.detalhes}")
    else:
        print("Uso: python identificador.py <arquivo.pdf>")
