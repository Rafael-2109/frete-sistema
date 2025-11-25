"""
Extrator Inteligente - Delega ao Claude a extração completa.

FILOSOFIA v3.5.1 - PILAR 3:
- O Claude recebe CONTEXTO ESTRUTURADO (JSON), não texto livre
- Isso elimina ambiguidade e interpretações erradas
- O Claude sabe EXATAMENTE o estado atual da conversa

O Claude deve ter LIBERDADE para:
- Extrair QUALQUER entidade que encontrar
- Inferir intenções de forma natural
- Usar contexto estruturado para entender referências
- Calcular datas, quantidades, etc.

Criado em: 24/11/2025
Atualizado: 24/11/2025 - Contexto estruturado (PILAR 3)
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class IntelligentExtractor:
    """
    Extrator que delega TODO o trabalho ao Claude.

    NOVO v3.5.1: Recebe contexto ESTRUTURADO em JSON.
    """

    def __init__(self, claude_client):
        self._client = claude_client

    def extrair(
        self,
        texto: str,
        contexto_estruturado: str = None,
        conhecimento_negocio: str = None
    ) -> Dict[str, Any]:
        """
        Extrai TUDO do texto usando Claude de forma livre.

        Args:
            texto: Mensagem do usuário
            contexto_estruturado: JSON estruturado do estado da conversa
            conhecimento_negocio: Aprendizados do negócio (opcional)

        Returns:
            Dict com extração completa e livre
        """
        hoje = datetime.now().strftime("%d/%m/%Y")
        ano_atual = datetime.now().year

        # Monta seção de contexto estruturado
        secao_contexto = ""
        if contexto_estruturado and contexto_estruturado.strip():
            secao_contexto = f"""
=== ESTADO ATUAL DA CONVERSA (JSON) ===
{contexto_estruturado}
=== FIM DO ESTADO ===

IMPORTANTE - REGRAS BASEADAS NO ESTADO:
1. Se RASCUNHO_ATIVO.existe = true:
   - Qualquer menção a data é MODIFICAÇÃO do rascunho existente
   - "pro dia 27/11" = alterar data_expedicao do rascunho para 2025-11-27
   - "confirmo" ou "sim" = confirmar o rascunho atual
   - "cancela" = cancelar o rascunho
   - Use o num_pedido do rascunho se não for mencionado

2. Se ESTADO.aguardando = "escolha_opcao":
   - O usuário provavelmente está escolhendo uma opção (A, B, C)
   - Qualquer menção a data JUNTO com opção modifica a opção escolhida

3. Se ENTIDADES_CONHECIDAS tem dados:
   - Use esses valores quando o usuário disser "esse pedido", "esse cliente"
   - Não pergunte por num_pedido se já está nas ENTIDADES_CONHECIDAS

"""

        # Prompt que confia no Claude + contexto estruturado
        system_prompt = f"""Você é um extrator de informações para um sistema de logística de uma INDÚSTRIA DE ALIMENTOS.

DATA DE HOJE: {hoje}
{secao_contexto}
{f"CONHECIMENTO DO NEGÓCIO:{chr(10)}{conhecimento_negocio}{chr(10)}" if conhecimento_negocio else ""}
TAREFA: Analise o texto e extraia TODAS as informações relevantes.

RETORNE um JSON com:
{{
    "intencao": "o que o usuário QUER FAZER (verbo no infinitivo)",
    "tipo": "consulta|acao|modificacao|confirmacao|cancelamento|clarificacao|outro",
    "entidades": {{
        // EXTRAIA TUDO que encontrar, sem restrições!
        // "num_pedido": "VCD123456",
        // "cliente": "nome do cliente",
        // "data_expedicao": "2025-11-27" (SEMPRE em formato ISO se for data),
        // "data_agendamento": "2025-11-28",
        // "quantidade": 100,
        // "produto": "azeitona verde",
        // "opcao": "A" (se usuário escolheu opção),
        // ... qualquer outra informação relevante
    }},
    "ambiguidade": {{
        "existe": true/false,
        "pergunta": "pergunta para esclarecer (se existe=true)",
        "opcoes": ["opção 1", "opção 2"]
    }},
    "contexto_usado": "quais dados do ESTADO você usou",
    "confianca": 0.0 a 1.0
}}

REGRAS IMPORTANTES:
1. DATAS: Calcule e retorne em formato ISO (YYYY-MM-DD). Ano: {ano_atual}
   - "dia 27/11" → "2025-11-27"
   - "amanhã" → calcule baseado em hoje
   - "semana que vem" → calcule data aproximada

2. CONTEXTO ESTRUTURADO: Use o JSON do ESTADO ATUAL para entender referências.
   - Se tem RASCUNHO_ATIVO, mensagens são sobre ELE
   - Se tem ENTIDADES_CONHECIDAS.num_pedido, use quando disser "esse pedido"

3. MODIFICAÇÕES COM RASCUNHO:
   - "crie pro dia X" + rascunho ativo = MODIFICAR data do rascunho
   - tipo = "modificacao"
   - data_expedicao = nova data

4. AMBIGUIDADE - Só pergunte se REALMENTE não souber:
   - Se tem rascunho ativo, data mencionada é para a expedição (não pergunte)
   - Se tem num_pedido no contexto, use-o (não pergunte)
   - Só pergunte quando não houver como inferir

5. SEPARAÇÃO:
   - data_expedicao = saída do armazém
   - data_agendamento = entrega ao cliente
   - "criar para dia X" geralmente é data_expedicao

Retorne APENAS o JSON, sem explicações."""

        try:
            resposta = self._client.completar(texto, system_prompt, use_cache=False)
            return self._parse_resposta(resposta)
        except Exception as e:
            logger.error(f"[INTELLIGENT_EXTRACTOR] Erro: {e}")
            return self._fallback(texto)

    def _parse_resposta(self, resposta: str) -> Dict[str, Any]:
        """Parseia resposta JSON do Claude."""
        try:
            resposta_limpa = resposta.strip()

            # Remove blocos markdown
            if resposta_limpa.startswith("```"):
                linhas = resposta_limpa.split("\n")
                # Remove primeira e última linha (```json e ```)
                resposta_limpa = "\n".join(linhas[1:-1] if linhas[-1].strip() == "```" else linhas[1:])

            resultado = json.loads(resposta_limpa)

            # Normaliza entidades (remove nulls)
            if 'entidades' in resultado:
                resultado['entidades'] = {
                    k: v for k, v in resultado['entidades'].items()
                    if v is not None and str(v).lower() not in ('null', 'none', '')
                }

            logger.info(f"[INTELLIGENT_EXTRACTOR] Extraído: tipo={resultado.get('tipo')}, "
                       f"intencao={resultado.get('intencao')}, "
                       f"entidades={list(resultado.get('entidades', {}).keys())}")

            return resultado

        except json.JSONDecodeError as e:
            logger.warning(f"[INTELLIGENT_EXTRACTOR] JSON inválido: {e}")
            logger.debug(f"Resposta recebida: {resposta[:500]}")
            return self._fallback("")

    def _fallback(self, texto: str) -> Dict[str, Any]:
        """Resposta padrão quando extração falha."""
        return {
            "intencao": "entender",
            "tipo": "outro",
            "entidades": {"texto_original": texto},
            "confianca": 0.0,
            "erro": "Falha na extração inteligente"
        }


# Singleton
_extractor: Optional[IntelligentExtractor] = None


def get_intelligent_extractor() -> IntelligentExtractor:
    """Retorna instância do extrator inteligente."""
    global _extractor
    if _extractor is None:
        from ..claude_client import get_claude_client
        _extractor = IntelligentExtractor(get_claude_client())
    return _extractor


def extrair_inteligente(
    texto: str,
    contexto: str = None,
    conhecimento: str = None
) -> Dict[str, Any]:
    """Função de conveniência para extração inteligente."""
    return get_intelligent_extractor().extrair(texto, contexto, conhecimento)
