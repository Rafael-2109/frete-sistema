"""
Validador de preços para pedidos de redes de atacarejo

Compara os preços extraídos dos documentos (Proposta/Pedido)
com os preços cadastrados na TabelaRede por:
- Rede (ATACADAO, TENDA, ASSAI)
- Região (obtida via UF através de RegiaoTabelaRede)
- Código do produto (código Nacom)
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from dataclasses import dataclass

from .models import TabelaRede, RegiaoTabelaRede


@dataclass
class ResultadoValidacaoPreco:
    """Resultado da validação de preço de um item"""
    codigo: str
    preco_documento: float
    preco_tabela: Optional[float]
    divergente: bool
    diferenca: float  # diferença em valor
    diferenca_percentual: float  # diferença em %
    mensagem: str


@dataclass
class ResultadoValidacao:
    """Resultado completo da validação de um documento"""
    rede: str
    uf: str
    regiao: Optional[str]
    total_itens: int
    itens_validados: int
    itens_divergentes: int
    itens_sem_tabela: int  # Sem preço cadastrado na TabelaRede
    tem_divergencia: bool
    validacoes: List[ResultadoValidacaoPreco]
    valor_total_documento: float
    valor_total_tabela: float


class ValidadorPrecos:
    """
    Valida preços de documentos contra a TabelaRede

    Uso:
        validador = ValidadorPrecos()
        resultado = validador.validar(
            rede='ATACADAO',
            uf='SP',
            itens=[{'codigo': '35642', 'valor_unitario': 199.48, 'quantidade': 15}, ...]
        )

        if resultado.tem_divergencia:
            print(f"Divergências encontradas: {resultado.itens_divergentes}")
    """

    def __init__(self, tolerancia_percentual: float = 0.0):
        """
        Args:
            tolerancia_percentual: Margem de tolerância para divergência (ex: 0.01 = 1%)
        """
        self.tolerancia_percentual = tolerancia_percentual
        self.cache_regiao = {}  # Cache de UF → Região

    def validar(self,
                rede: str,
                uf: str,
                itens: List[Dict[str, Any]],
                campo_codigo: str = 'nosso_codigo',
                campo_preco: str = 'valor_unitario',
                campo_quantidade: str = 'quantidade') -> ResultadoValidacao:
        """
        Valida preços de uma lista de itens

        Args:
            rede: Nome da rede (ATACADAO, TENDA, ASSAI)
            uf: Estado (SP, RJ, etc.)
            itens: Lista de dicionários com os itens
            campo_codigo: Nome do campo com o código do produto (default: nosso_codigo)
            campo_preco: Nome do campo com o preço unitário
            campo_quantidade: Nome do campo com a quantidade

        Returns:
            ResultadoValidacao com os detalhes
        """
        rede = rede.upper()
        uf = uf.upper()

        # Busca a região pela UF
        regiao = self._buscar_regiao(rede, uf)

        validacoes = []
        total_itens = 0
        itens_validados = 0
        itens_divergentes = 0
        itens_sem_tabela = 0
        valor_total_documento = 0.0
        valor_total_tabela = 0.0

        for item in itens:
            codigo = item.get(campo_codigo)
            preco_doc = item.get(campo_preco)
            quantidade = item.get(campo_quantidade, 1)

            # Se não tem código de produto (nosso_codigo), pula
            if not codigo:
                continue

            total_itens += 1

            # Converte preço para float
            if isinstance(preco_doc, Decimal):
                preco_doc = float(preco_doc)
            else:
                preco_doc = float(preco_doc) if preco_doc else 0.0

            # Busca preço na tabela
            preco_tabela = None
            if regiao:
                tabela = TabelaRede.buscar_preco(rede, regiao, codigo)
                if tabela:
                    preco_tabela = float(tabela.preco)

            # Calcula valores totais
            valor_item_doc = preco_doc * quantidade
            valor_total_documento += valor_item_doc

            if preco_tabela is not None:
                valor_item_tabela = preco_tabela * quantidade
                valor_total_tabela += valor_item_tabela
                itens_validados += 1

                # Verifica divergência
                diferenca = preco_doc - preco_tabela
                diferenca_percentual = (diferenca / preco_tabela * 100) if preco_tabela > 0 else 0

                # Considera divergente se fora da tolerância
                divergente = abs(diferenca_percentual) > (self.tolerancia_percentual * 100)

                if divergente:
                    itens_divergentes += 1
                    mensagem = f"Preço divergente: Doc R${preco_doc:.2f} vs Tabela R${preco_tabela:.2f} ({diferenca_percentual:+.2f}%)"
                else:
                    mensagem = "OK"

                validacoes.append(ResultadoValidacaoPreco(
                    codigo=codigo,
                    preco_documento=preco_doc,
                    preco_tabela=preco_tabela,
                    divergente=divergente,
                    diferenca=diferenca,
                    diferenca_percentual=diferenca_percentual,
                    mensagem=mensagem
                ))
            else:
                # Sem preço cadastrado na tabela
                itens_sem_tabela += 1
                validacoes.append(ResultadoValidacaoPreco(
                    codigo=codigo,
                    preco_documento=preco_doc,
                    preco_tabela=None,
                    divergente=False,  # Não considera divergente, apenas sem tabela
                    diferenca=0,
                    diferenca_percentual=0,
                    mensagem=f"Preço não encontrado na TabelaRede para {rede}/{regiao or uf}/{codigo}"
                ))

        return ResultadoValidacao(
            rede=rede,
            uf=uf,
            regiao=regiao,
            total_itens=total_itens,
            itens_validados=itens_validados,
            itens_divergentes=itens_divergentes,
            itens_sem_tabela=itens_sem_tabela,
            tem_divergencia=itens_divergentes > 0,
            validacoes=validacoes,
            valor_total_documento=valor_total_documento,
            valor_total_tabela=valor_total_tabela
        )

    def validar_filial(self,
                       rede: str,
                       filial: Dict[str, Any],
                       campo_uf: str = 'estado') -> ResultadoValidacao:
        """
        Valida preços de uma filial completa (conveniente para uso com summary do processor)

        Args:
            rede: Nome da rede
            filial: Dict com dados da filial (incluindo 'produtos' e UF)
            campo_uf: Nome do campo com a UF

        Returns:
            ResultadoValidacao
        """
        uf = filial.get(campo_uf, '')
        produtos = filial.get('produtos', [])

        return self.validar(rede=rede, uf=uf, itens=produtos)

    def _buscar_regiao(self, rede: str, uf: str) -> Optional[str]:
        """
        Busca a região correspondente a uma UF (com cache)
        """
        cache_key = f"{rede}_{uf}"

        if cache_key in self.cache_regiao:
            return self.cache_regiao[cache_key]

        regiao_obj = RegiaoTabelaRede.buscar_regiao(rede, uf)
        regiao = regiao_obj.regiao if regiao_obj else None

        self.cache_regiao[cache_key] = regiao
        return regiao


def validar_precos_documento(rede: str,
                              uf: str,
                              itens: List[Dict[str, Any]],
                              tolerancia: float = 0.0) -> ResultadoValidacao:
    """
    Função utilitária para validar preços de um documento

    Args:
        rede: Nome da rede (ATACADAO, TENDA, ASSAI)
        uf: Estado
        itens: Lista de itens com nosso_codigo e valor_unitario
        tolerancia: Tolerância percentual (0.01 = 1%)

    Returns:
        ResultadoValidacao
    """
    validador = ValidadorPrecos(tolerancia_percentual=tolerancia)
    return validador.validar(rede=rede, uf=uf, itens=itens)


def validar_documento_completo(rede: str,
                                summary: Dict[str, Any],
                                tolerancia: float = 0.0) -> Dict[str, ResultadoValidacao]:
    """
    Valida todas as filiais de um documento

    Args:
        rede: Nome da rede
        summary: Summary gerado pelo PedidoProcessor
        tolerancia: Tolerância percentual

    Returns:
        Dict com CNPJ → ResultadoValidacao
    """
    validador = ValidadorPrecos(tolerancia_percentual=tolerancia)
    resultados = {}

    for filial in summary.get('por_filial', []):
        cnpj = filial.get('cnpj', '')
        uf = filial.get('estado', '')
        produtos = filial.get('produtos', [])

        resultado = validador.validar(rede=rede, uf=uf, itens=produtos)
        resultados[cnpj] = resultado

    return resultados
