"""
Response Reviewer - Self-Consistency Check

Responsável por revisar respostas antes de enviar ao usuário:
1. Verifica se a resposta é coerente com os dados
2. Detecta alucinações (informações não presentes no contexto)
3. Valida uso de campos corretos (conforme CLAUDE.md)
4. Verifica completude (pergunta foi respondida?)

Criado em: 24/11/2025
Limite: 200 linhas
"""

import logging
from typing import Dict, Any, Tuple, Optional
import re

logger = logging.getLogger(__name__)


class ResponseReviewer:
    """Revisa respostas do Claude antes de enviar ao usuário."""

    def __init__(self, claude_client):
        """
        Args:
            claude_client: Instância do ClaudeClient
        """
        self._client = claude_client

    def revisar_resposta(
        self,
        pergunta: str,
        resposta_gerada: str,
        contexto_dados: str,
        dominio: str = "logistica"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Revisa a resposta para garantir coerência com os dados.

        Args:
            pergunta: Pergunta original do usuário
            resposta_gerada: Resposta gerada pelo Claude
            contexto_dados: Dados reais do sistema
            dominio: Domínio da consulta

        Returns:
            Tuple (resposta_revisada, metadados_revisao)
        """
        # 1. Verificação rápida local (sem chamar API)
        problemas_locais = self._verificar_problemas_locais(resposta_gerada, contexto_dados)

        if problemas_locais:
            logger.warning(f"[REVIEWER] Problemas locais detectados: {problemas_locais}")
            # Corrige localmente se possível
            resposta_corrigida = self._corrigir_localmente(resposta_gerada, problemas_locais)
            if resposta_corrigida != resposta_gerada:
                return resposta_corrigida, {
                    'revisao': 'local',
                    'problemas': problemas_locais,
                    'corrigido': True
                }

        # 2. Se resposta curta ou simples, não precisa revisão via API
        if self._resposta_simples(resposta_gerada):
            return resposta_gerada, {'revisao': 'nao_necessaria'}

        # 3. Revisão via Claude (para respostas complexas)
        resultado_revisao = self._revisar_via_claude(
            pergunta, resposta_gerada, contexto_dados
        )

        if resultado_revisao.get('precisa_correcao'):
            resposta_final = resultado_revisao.get('resposta_corrigida', resposta_gerada)
            return resposta_final, {
                'revisao': 'claude',
                'problemas': resultado_revisao.get('problemas', []),
                'corrigido': True
            }

        return resposta_gerada, {'revisao': 'aprovada'}

    def _verificar_problemas_locais(self, resposta: str, contexto: str) -> list:
        """Verifica problemas sem chamar API."""
        problemas = []

        # 1. Detecta números inventados (não presentes no contexto)
        numeros_resposta = set(re.findall(r'\b\d+(?:[.,]\d+)?\b', resposta))
        numeros_contexto = set(re.findall(r'\b\d+(?:[.,]\d+)?\b', contexto))

        # Filtra números comuns que podem ser gerados
        numeros_comuns = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '100'}
        numeros_suspeitos = numeros_resposta - numeros_contexto - numeros_comuns

        # Verifica se são valores significativos (mais de 2 dígitos)
        for num in numeros_suspeitos:
            try:
                valor = float(num.replace(',', '.'))
                if valor > 10 and num not in contexto:
                    problemas.append(f"Número '{num}' não encontrado nos dados")
            except ValueError:
                pass

        # 2. Detecta nomes de campos incorretos
        campos_incorretos = self._detectar_campos_incorretos(resposta)
        if campos_incorretos:
            problemas.extend(campos_incorretos)

        # 3. Detecta contradições óbvias
        contradicoes = self._detectar_contradicoes(resposta, contexto)
        if contradicoes:
            problemas.extend(contradicoes)

        return problemas

    def _detectar_campos_incorretos(self, resposta: str) -> list:
        """
        Detecta uso de nomes de campos incorretos.

        Baseado nas definições do CLAUDE.md (referência oficial do sistema).
        """
        # === CAMPOS INCORRETOS (NÃO EXISTEM) ===
        # Mapeamento: campo_errado -> (correcao, modelo)
        CAMPOS_ERRADOS = {
            # Datas - erros comuns
            'data_agendamento_pedido': ('agendamento', 'Separacao'),
            'data_expedicao_pedido': ('expedicao', 'Separacao'),
            'data_entrega': ('data_entrega_pedido', 'CarteiraPrincipal'),
            'agendamento_status': ('agendamento', 'Separacao'),

            # Cliente - erros comuns
            'razao_social': ('raz_social_red', 'Separacao/CarteiraPrincipal'),
            'nome_cliente': ('raz_social_red', 'Separacao'),
            'cliente_nome': ('raz_social_red', 'Separacao'),

            # Produto - erros comuns
            'codigo_produto': ('cod_produto', 'Separacao/CarteiraPrincipal'),
            'produto_codigo': ('cod_produto', 'Separacao'),
            'descricao_produto': ('nome_produto', 'Separacao/CarteiraPrincipal'),

            # Quantidade - erros comuns
            'quantidade': ('qtd_saldo', 'Separacao'),
            'qtd_saldo_produto_pedido': ('qtd_saldo', 'Separacao - use qtd_saldo, não existe em Separacao'),
            'quantidade_saldo': ('qtd_saldo', 'Separacao'),

            # Localização - erros comuns
            'estado': ('cod_uf', 'Separacao'),
            'uf': ('cod_uf', 'Separacao'),
            'cidade': ('nome_cidade', 'Separacao'),

            # Status - erros comuns
            'status_pedido': ('status', 'Separacao'),
            'sincronizado': ('sincronizado_nf', 'Separacao'),
        }

        # === CAMPOS CORRETOS POR MODELO (referência) ===
        # Usado para validar se um campo existe no modelo correto
        CAMPOS_CORRETOS = {
            'Separacao': [
                'num_pedido', 'cod_produto', 'nome_produto', 'qtd_saldo', 'valor_saldo',
                'cnpj_cpf', 'raz_social_red', 'nome_cidade', 'cod_uf', 'rota', 'sub_rota',
                'expedicao', 'agendamento', 'protocolo', 'roteirizacao', 'status',
                'sincronizado_nf', 'peso', 'pallet', 'data_pedido', 'criado_em',
                'observ_ped_1', 'tipo_envio', 'separacao_lote_id', 'numero_nf'
            ],
            'CarteiraPrincipal': [
                'num_pedido', 'cod_produto', 'nome_produto', 'cnpj_cpf', 'raz_social_red',
                'qtd_produto_pedido', 'qtd_saldo_produto_pedido', 'preco_produto_pedido',
                'data_entrega_pedido', 'observ_ped_1', 'vendedor', 'equipe_vendas',
                'municipio', 'estado', 'pedido_cliente', 'tags_pedido'
            ],
            'Pedido': [
                'num_pedido', 'separacao_lote_id', 'status', 'nf', 'nf_cd',
                'cnpj_cpf', 'raz_social_red', 'nome_cidade', 'cod_uf',
                'expedicao', 'agendamento', 'protocolo', 'data_pedido',
                'valor_saldo_total', 'peso_total', 'pallet_total',
                'transportadora', 'valor_frete'
            ]
        }

        problemas = []
        resposta_lower = resposta.lower()

        # Verifica campos errados
        for campo_errado, (correcao, modelo) in CAMPOS_ERRADOS.items():
            if campo_errado.lower() in resposta_lower:
                problemas.append(f"Campo incorreto: '{campo_errado}' → Use '{correcao}' ({modelo})")

        return problemas

    def _detectar_contradicoes(self, resposta: str, contexto: str) -> list:
        """Detecta contradições entre resposta e contexto."""
        problemas = []

        # Verifica se resposta menciona "não encontrado" mas contexto tem dados
        if 'não encontr' in resposta.lower() or 'nao encontr' in resposta.lower():
            if 'num_pedido' in contexto.lower() or 'VCD' in contexto:
                problemas.append("Resposta diz 'não encontrado' mas contexto tem dados")

        # Verifica se resposta menciona quantidade zero mas contexto tem valores
        if 'quantidade: 0' in resposta.lower() or 'qtd: 0' in resposta.lower():
            # Procura por quantidades no contexto
            qtds = re.findall(r'qtd[_\w]*:\s*(\d+)', contexto, re.IGNORECASE)
            if qtds and any(int(q) > 0 for q in qtds):
                problemas.append("Resposta menciona quantidade zero mas dados têm valores")

        return problemas

    def _corrigir_localmente(self, resposta: str, problemas: list) -> str:
        """Tenta corrigir problemas localmente sem chamar API."""
        resposta_corrigida = resposta

        for problema in problemas:
            # Corrige campos incorretos
            if 'data_agendamento_pedido' in problema.lower():
                resposta_corrigida = resposta_corrigida.replace(
                    'data_agendamento_pedido', 'agendamento'
                )
            if 'data_expedicao_pedido' in problema.lower():
                resposta_corrigida = resposta_corrigida.replace(
                    'data_expedicao_pedido', 'expedição'
                )

        return resposta_corrigida

    def _resposta_simples(self, resposta: str) -> bool:
        """Verifica se resposta é simples (não precisa revisão via API)."""
        # Respostas curtas
        if len(resposta) < 200:
            return True

        # Respostas que são principalmente listas/tabelas
        linhas = resposta.split('\n')
        linhas_lista = sum(1 for linha in linhas if linha.strip().startswith('-') or linha.strip().startswith('•'))
        if linhas_lista > len(linhas) * 0.5:
            return True

        return False

    def _revisar_via_claude(
        self,
        pergunta: str,
        resposta: str,
        contexto: str
    ) -> Dict[str, Any]:
        """Revisão detalhada via Claude API."""

        prompt_revisao = f"""Você é um revisor de qualidade. Verifique se a RESPOSTA abaixo é coerente com os DADOS.

PERGUNTA DO USUÁRIO:
{pergunta}

DADOS REAIS DO SISTEMA:
{contexto[:2000]}

RESPOSTA GERADA:
{resposta}

VERIFICAÇÃO:
1. A resposta usa APENAS informações presentes nos DADOS?
2. Há números ou valores que não existem nos DADOS?
3. Há informações inventadas ou suposições?
4. A pergunta foi respondida completamente?

Se a resposta está OK, responda APENAS: {{"ok": true}}

Se há problemas, responda APENAS em JSON:
{{
    "ok": false,
    "problemas": ["lista de problemas encontrados"],
    "resposta_corrigida": "resposta corrigida baseada apenas nos dados"
}}

IMPORTANTE: Responda APENAS o JSON, sem explicações."""

        try:
            resposta_revisao = self._client.completar(
                pergunta="Revise esta resposta",
                system_prompt=prompt_revisao,
                use_cache=False
            )

            # Parseia resposta
            import json
            resposta_limpa = resposta_revisao.strip()
            if resposta_limpa.startswith('```'):
                linhas = resposta_limpa.split('\n')
                resposta_limpa = '\n'.join(linhas[1:-1])

            resultado = json.loads(resposta_limpa)

            if resultado.get('ok', False):
                return {'precisa_correcao': False}
            else:
                return {
                    'precisa_correcao': True,
                    'problemas': resultado.get('problemas', []),
                    'resposta_corrigida': resultado.get('resposta_corrigida', resposta)
                }

        except Exception as e:
            logger.warning(f"[REVIEWER] Erro na revisão via Claude: {e}")
            return {'precisa_correcao': False, 'erro': str(e)}


def get_reviewer() -> ResponseReviewer:
    """Factory para obter instância do reviewer."""
    from ..claude_client import get_claude_client
    return ResponseReviewer(get_claude_client())
