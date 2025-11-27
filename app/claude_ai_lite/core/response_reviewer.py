"""
Response Reviewer v2.0 - Minimalista

Verifica apenas o que é verificável deterministicamente:
1. Cliente do contexto presente na resposta
2. Contradição "não encontrado" vs dados existentes
3. Total mencionado bate com dados reais

FILOSOFIA:
- Sem chamadas extras ao Claude (custo zero)
- Sem falsos positivos (só verifica o verificável)
- Correção automática apenas para casos seguros

Criado em: 24/11/2025
Atualizado: 27/11/2025 - v2.0: Versão minimalista, sem Claude extra
"""

import re
import json
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class ResponseReviewer:
    """
    Revisão minimalista de respostas.

    Verifica coerência básica SEM chamar Claude novamente.
    Foco em detecções determinísticas com baixo falso positivo.
    """

    def __init__(self, claude_client=None):
        """
        Args:
            claude_client: Ignorado na v2 (mantido para compatibilidade)
        """
        # Cliente não é mais usado na v2, mas mantemos para interface compatível
        self._client = claude_client

    def revisar_resposta(
        self,
        pergunta: str,
        resposta_gerada: str,
        contexto_dados: str,
        dominio: str = "logistica",
        estado_estruturado: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Revisa a resposta para garantir coerência básica.

        Args:
            pergunta: Pergunta original do usuário
            resposta_gerada: Resposta gerada pelo Claude
            contexto_dados: Dados reais do sistema (string formatada)
            dominio: Domínio da consulta
            estado_estruturado: JSON do estado atual (PILAR 3)

        Returns:
            Tuple (resposta_possivelmente_corrigida, metadados_revisao)
        """
        problemas = []
        resposta_final = resposta_gerada

        # Parseia estado se disponível
        estado = self._parse_estado(estado_estruturado)

        # Extrai dados do contexto para verificação
        dados_info = self._extrair_info_dados(contexto_dados)

        # 1. Verifica cliente do contexto
        problema_cliente = self._verificar_cliente_contexto(
            resposta_gerada, estado, contexto_dados
        )
        if problema_cliente:
            problemas.append(problema_cliente)
            # Se cliente errado, sinaliza para reprocessar
            if problema_cliente.get('acao') == 'reprocessar':
                return resposta_gerada, {
                    'revisao': 'contexto_invalido',
                    'problema_contexto': problema_cliente.get('descricao'),
                    'reprocessar': True,
                    'problemas': problemas
                }

        # 2. Verifica contradição "não encontrado" vs dados
        problema_contradicao = self._verificar_contradicao(
            resposta_gerada, dados_info
        )
        if problema_contradicao:
            problemas.append(problema_contradicao)

        # 3. Verifica total mencionado vs dados reais
        problema_total, correcao = self._verificar_total(
            resposta_gerada, dados_info
        )
        if problema_total:
            problemas.append(problema_total)
            if correcao:
                resposta_final = correcao
                logger.info(f"[REVIEWER] Corrigido total: {problema_total}")

        # Monta resultado
        return resposta_final, {
            'revisao': 'problemas' if problemas else 'ok',
            'problemas': problemas,
            'corrigido': resposta_final != resposta_gerada
        }

    def _parse_estado(self, estado_estruturado: str) -> Dict[str, Any]:
        """Parseia o estado JSON se disponível."""
        if not estado_estruturado:
            return {}

        try:
            return json.loads(estado_estruturado)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _extrair_info_dados(self, contexto_dados: str) -> Dict[str, Any]:
        """
        Extrai informações úteis do contexto de dados.

        Returns:
            Dict com:
            - tem_dados: bool
            - total_mencionado: int ou None (se encontrado no contexto)
            - clientes: list de clientes mencionados
        """
        info = {
            'tem_dados': False,
            'total_mencionado': None,
            'clientes': []
        }

        if not contexto_dados:
            return info

        contexto_lower = contexto_dados.lower()

        # Verifica se tem dados
        indicadores_dados = [
            'num_pedido', 'vcd', 'pedido', 'cliente',
            'raz_social', 'cod_produto', 'encontrad'
        ]
        info['tem_dados'] = any(ind in contexto_lower for ind in indicadores_dados)

        # Extrai total se mencionado no contexto
        # Padrões como "Total: 5", "Encontrados: 10", "5 resultados"
        match_total = re.search(
            r'(?:total|encontrad\w*|resultado\w*)[:\s]*(\d+)',
            contexto_lower
        )
        if match_total:
            info['total_mencionado'] = int(match_total.group(1))

        # Extrai clientes mencionados
        # Procura padrões como "raz_social_red: NOME" ou "cliente: NOME"
        matches_cliente = re.findall(
            r'(?:raz_social_red|cliente)[:\s]*["\']?([A-Z][A-Z\s]{2,30})',
            contexto_dados,
            re.IGNORECASE
        )
        info['clientes'] = [c.strip().upper() for c in matches_cliente]

        return info

    def _verificar_cliente_contexto(
        self,
        resposta: str,
        estado: Dict,
        contexto_dados: str
    ) -> Optional[Dict]:
        """
        Verifica se o cliente esperado está sendo tratado corretamente.

        Detecta situações onde:
        - Estado tem cliente_atual mas resposta não o menciona
        - Resposta menciona cliente diferente do contexto
        """
        # Extrai cliente esperado do estado
        ref = estado.get('REFERENCIA', {})
        cliente_esperado = ref.get('cliente_atual') or ref.get('cliente')

        if not cliente_esperado:
            return None

        cliente_upper = cliente_esperado.upper()
        resposta_upper = resposta.upper()
        contexto_upper = contexto_dados.upper() if contexto_dados else ""

        # Caso 1: Cliente esperado não está nos dados retornados
        # Isso indica que a query não filtrou corretamente
        if cliente_upper not in contexto_upper:
            # Verifica se há outros clientes nos dados (problema grave)
            outros_clientes = re.findall(
                r'RAZ_SOCIAL_RED[:\s]*["\']?([A-Z][A-Z\s]{2,30})',
                contexto_upper
            )
            if outros_clientes:
                return {
                    'tipo': 'cliente_errado_nos_dados',
                    'esperado': cliente_esperado,
                    'encontrados': outros_clientes[:3],
                    'descricao': f"Dados retornados não são do cliente {cliente_esperado}",
                    'acao': 'reprocessar'
                }

        # Caso 2: Resposta menciona cliente diferente
        # (menos grave, pode ser formatação)
        if cliente_upper not in resposta_upper:
            # Só é problema se a resposta menciona outros clientes
            menciona_cliente = any(
                termo in resposta.lower()
                for termo in ['cliente', 'empresa', 'razão social']
            )
            if menciona_cliente:
                return {
                    'tipo': 'cliente_ausente_resposta',
                    'esperado': cliente_esperado,
                    'descricao': f"Resposta não menciona cliente {cliente_esperado}",
                    'acao': 'verificar'  # Apenas alerta, não reprocessa
                }

        return None

    def _verificar_contradicao(
        self,
        resposta: str,
        dados_info: Dict
    ) -> Optional[Dict]:
        """
        Verifica se resposta diz "não encontrado" mas há dados.

        Este é um erro grave onde o Claude ignora os dados fornecidos.
        """
        tem_dados = dados_info.get('tem_dados', False)

        # Padrões que indicam "não encontrado"
        padroes_negacao = [
            r'não\s+encontr',
            r'nenhum\s+resultado',
            r'não\s+há\s+(?:dados|registros|pedidos)',
            r'não\s+existe',
            r'sem\s+dados',
            r'não\s+localizei',
            r'não\s+foi\s+possível\s+encontrar'
        ]

        resposta_lower = resposta.lower()
        diz_nao_encontrou = any(
            re.search(padrao, resposta_lower)
            for padrao in padroes_negacao
        )

        if tem_dados and diz_nao_encontrou:
            return {
                'tipo': 'contradicao_dados',
                'descricao': 'Resposta diz "não encontrado" mas contexto tem dados',
                'acao': 'alertar'
            }

        return None

    def _verificar_total(
        self,
        resposta: str,
        dados_info: Dict
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Verifica se total mencionado na resposta bate com dados.

        Se detectar discrepância, tenta corrigir automaticamente.

        Returns:
            Tuple (problema_ou_none, resposta_corrigida_ou_none)
        """
        total_contexto = dados_info.get('total_mencionado')

        if total_contexto is None:
            return None, None

        # Procura totais mencionados na resposta
        # Padrões como "5 pedidos", "encontrei 10 itens", "total de 3"
        padroes_total = [
            r'(\d+)\s*(?:pedidos?|itens?|registros?|resultados?)',
            r'(?:total|encontr\w*|há|existem?)\s*(?:de\s+)?(\d+)',
            r'(\d+)\s*(?:cliente|produto)',
        ]

        for padrao in padroes_total:
            match = re.search(padrao, resposta.lower())
            if match:
                total_resposta = int(match.group(1))

                # Tolera diferença se for 0 vs dados (já tratado em contradição)
                if total_resposta == 0:
                    continue

                # Verifica se o total está errado
                if total_resposta != total_contexto:
                    # Tenta corrigir
                    # Substitui apenas a primeira ocorrência do número errado
                    correcao = re.sub(
                        rf'\b{total_resposta}\b(\s*(?:pedidos?|itens?|registros?|resultados?))',
                        f'{total_contexto}\\1',
                        resposta,
                        count=1
                    )

                    return {
                        'tipo': 'total_incorreto',
                        'mencionado': total_resposta,
                        'correto': total_contexto,
                        'descricao': f'Total {total_resposta} corrigido para {total_contexto}',
                        'acao': 'corrigido'
                    }, correcao

        return None, None


# =============================================================================
# SINGLETON E FACTORY
# =============================================================================

_reviewer: Optional[ResponseReviewer] = None


def get_reviewer() -> ResponseReviewer:
    """Retorna instância singleton do reviewer."""
    global _reviewer
    if _reviewer is None:
        _reviewer = ResponseReviewer()
    return _reviewer
