"""
ProdutoResolver - Resolução flexível de produtos por texto.

Responsabilidades:
1. Buscar produtos por nome parcial usando ilike
2. Buscar por código (exato ou parcial)
3. Buscar por sinônimos/variações
4. Retornar sugestões quando houver múltiplas correspondências

Usa CadastroPalletizacao como fonte de dados de produtos.

Criado em: 24/11/2025
Limite: 200 linhas
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProdutoEncontrado:
    """Produto encontrado na busca."""
    cod_produto: str
    nome_produto: str
    palletizacao: float
    peso_bruto: float
    score: float = 1.0  # Score de relevância
    match_tipo: str = ""  # exato_codigo, exato_nome, parcial_nome, parcial_codigo


class ProdutoResolver:
    """Resolver de produtos com busca flexível."""

    @staticmethod
    def buscar_produto(
        termo: str,
        limite: int = 5
    ) -> Dict:
        """
        Busca produtos de forma flexível em CadastroPalletizacao.

        Args:
            termo: Texto para buscar (código, nome parcial, etc)
            limite: Máximo de resultados

        Returns:
            Dict com:
            - sucesso: bool
            - produtos: List[ProdutoEncontrado]
            - match_unico: bool (se achou exatamente 1)
            - sugestoes: List (se achou múltiplos)
        """
        try:
            from app.producao.models import CadastroPalletizacao
            from sqlalchemy import or_, func

            termo_limpo = termo.strip()
            termo_lower = termo_limpo.lower()

            produtos_encontrados = []
            ids_vistos = set()

            # === FASE 1: Busca por código EXATO ===
            produto_codigo = CadastroPalletizacao.query.filter(
                func.lower(CadastroPalletizacao.cod_produto) == termo_lower,
                CadastroPalletizacao.ativo == True
            ).first()

            if produto_codigo:
                produtos_encontrados.append(ProdutoEncontrado(
                    cod_produto=produto_codigo.cod_produto,
                    nome_produto=produto_codigo.nome_produto,
                    palletizacao=produto_codigo.palletizacao or 0,
                    peso_bruto=produto_codigo.peso_bruto or 0,
                    score=100,
                    match_tipo='exato_codigo'
                ))
                ids_vistos.add(produto_codigo.id)

            # === FASE 2: Busca por nome EXATO (case insensitive) ===
            produto_nome_exato = CadastroPalletizacao.query.filter(
                func.lower(CadastroPalletizacao.nome_produto) == termo_lower,
                CadastroPalletizacao.ativo == True
            ).first()

            if produto_nome_exato and produto_nome_exato.id not in ids_vistos:
                produtos_encontrados.append(ProdutoEncontrado(
                    cod_produto=produto_nome_exato.cod_produto,
                    nome_produto=produto_nome_exato.nome_produto,
                    palletizacao=produto_nome_exato.palletizacao or 0,
                    peso_bruto=produto_nome_exato.peso_bruto or 0,
                    score=95,
                    match_tipo='exato_nome'
                ))
                ids_vistos.add(produto_nome_exato.id)

            # Se encontrou exato, retorna
            if produtos_encontrados:
                return {
                    'sucesso': True,
                    'produtos': produtos_encontrados,
                    'match_unico': len(produtos_encontrados) == 1,
                    'sugestoes': []
                }

            # === FASE 3: Busca por nome PARCIAL (ilike) ===
            produtos_parcial_nome = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.nome_produto.ilike(f'%{termo_limpo}%'),
                CadastroPalletizacao.ativo == True
            ).limit(limite * 2).all()

            for p in produtos_parcial_nome:
                if p.id not in ids_vistos:
                    # Calcula score baseado em posição do match
                    nome_lower = p.nome_produto.lower()
                    if nome_lower.startswith(termo_lower):
                        score = 80
                    elif f' {termo_lower}' in nome_lower:
                        score = 70
                    else:
                        score = 60

                    produtos_encontrados.append(ProdutoEncontrado(
                        cod_produto=p.cod_produto,
                        nome_produto=p.nome_produto,
                        palletizacao=p.palletizacao or 0,
                        peso_bruto=p.peso_bruto or 0,
                        score=score,
                        match_tipo='parcial_nome'
                    ))
                    ids_vistos.add(p.id)

            # === FASE 4: Busca por código PARCIAL (ilike) ===
            produtos_parcial_cod = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.cod_produto.ilike(f'%{termo_limpo}%'),
                CadastroPalletizacao.ativo == True
            ).limit(limite).all()

            for p in produtos_parcial_cod:
                if p.id not in ids_vistos:
                    produtos_encontrados.append(ProdutoEncontrado(
                        cod_produto=p.cod_produto,
                        nome_produto=p.nome_produto,
                        palletizacao=p.palletizacao or 0,
                        peso_bruto=p.peso_bruto or 0,
                        score=50,
                        match_tipo='parcial_codigo'
                    ))
                    ids_vistos.add(p.id)

            # Ordena por score (maior primeiro)
            produtos_encontrados.sort(key=lambda x: x.score, reverse=True)

            # Limita resultados
            produtos_encontrados = produtos_encontrados[:limite]

            if not produtos_encontrados:
                return {
                    'sucesso': False,
                    'erro': f'Nenhum produto encontrado para "{termo}"',
                    'produtos': [],
                    'match_unico': False,
                    'sugestoes': []
                }

            # Prepara sugestões se múltiplos
            sugestoes = []
            if len(produtos_encontrados) > 1:
                sugestoes = [
                    f"- {p.cod_produto}: {p.nome_produto}"
                    for p in produtos_encontrados
                ]

            return {
                'sucesso': True,
                'produtos': produtos_encontrados,
                'match_unico': len(produtos_encontrados) == 1,
                'sugestoes': sugestoes
            }

        except Exception as e:
            logger.error(f"[PRODUTO_RESOLVER] Erro ao buscar produto: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'produtos': [],
                'match_unico': False,
                'sugestoes': []
            }

    @staticmethod
    def formatar_sugestoes(termo: str, sugestoes: List[str]) -> str:
        """Formata mensagem de sugestões para o usuário."""
        return (
            f"Encontrei múltiplos produtos para '{termo}':\n\n"
            f"{chr(10).join(sugestoes)}\n\n"
            "Qual desses você quis dizer? Informe o código ou seja mais específico."
        )


def resolver_produto_texto(texto: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    Função de conveniência para resolver produto de um texto.

    Returns:
        Tuple (cod_produto, nome_produto, mensagem)
        - Se encontrou único: (codigo, nome, "")
        - Se múltiplos: (None, None, mensagem_sugestoes)
        - Se nenhum: (None, None, mensagem_erro)
    """
    resultado = ProdutoResolver.buscar_produto(texto)

    if not resultado['sucesso']:
        return None, None, resultado.get('erro', 'Produto não encontrado')

    if resultado['match_unico']:
        produto = resultado['produtos'][0]
        return produto.cod_produto, produto.nome_produto, ""

    # Múltiplos encontrados
    return None, None, ProdutoResolver.formatar_sugestoes(
        texto, resultado['sugestoes']
    )
