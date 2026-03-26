#!/usr/bin/env python3
"""
Hook PreToolUse: Enriquecer subagentes com framework aristotelico.

Detecta quando o Agent tool spawna subagentes que se beneficiam de
raciocinio estruturado e injeta instrucoes do framework aristotelico:

- feature-dev (plugin): code-explorer, code-architect, code-reviewer
- Built-in: Plan (deliberacao), Explore (mapeamento)

NAO injeta para subagentes locais com prompts domain-specific
(analista-carteira, especialista-odoo, etc.) — esses ja tem
instrucoes ultra-especificas que o framework generico diluiria.

Abordagem via hook garante que o enriquecimento sobrevive a updates
do plugin (que sobrescreveriam edicoes diretas nos .md do plugin).

Exit 0 sempre — nunca bloqueia.
"""

import json
import sys


# Framework aristotelico por tipo de subagente
FRAMEWORK_POR_SUBAGENTE = {
    "code-explorer": (
        "FRAMEWORK DELIBERATIVO — Causa Material:\n"
        "Ao explorar o codebase, estruture sua analise identificando:\n"
        "- SUBSTRATO: Quais dados, tabelas, APIs e recursos compoe esta area do codigo?\n"
        "- PADRAO: Que padroes arquiteturais, convencoes e abstracoes existem?\n"
        "- MECANISMO: Como o fluxo de dados/controle opera (request → route → service → model → DB → template)?\n"
        "- DEPENDENCIAS: Que modulos upstream/downstream seriam afetados por mudancas aqui?\n"
        "Priorize fatos ESSENCIAIS (sem os quais a feature quebraria) sobre ACIDENTAIS (cosmeticos)."
    ),
    "code-architect": (
        "FRAMEWORK DELIBERATIVO — Quatro Causas para Design:\n"
        "Ao projetar a arquitetura, analise cada decisao usando:\n"
        "- MATERIAL: Que recursos/dados/tabelas a feature vai consumir ou produzir?\n"
        "- FORMAL: Qual padrao existente no codebase esta feature deve seguir? (convencoes, abstracoes)\n"
        "- EFICIENTE: Que mecanismos/processos/agentes executarao cada transformacao?\n"
        "- FINAL: Qual o TELOS (proposito real)? O que constitui sucesso vs fracasso?\n"
        "PRE-MORTEM: Antes de finalizar, imagine que a arquitetura JA FALHOU. "
        "Liste 2-3 modos de falha e como o design os previne."
    ),
    "code-reviewer": (
        "FRAMEWORK DELIBERATIVO — Dynamis/Energeia + Essencia/Acidente:\n"
        "Ao revisar codigo, aplique triagem de consequencias:\n"
        "- ESSENCIAL: Issues que, se nao corrigidos, causam bugs, perda de dados ou regressao "
        "(logica errada, SQL injection, race conditions, dados inconsistentes)\n"
        "- ACIDENTAL: Issues cosmeticos que nao afetam funcionalidade "
        "(formatacao, naming preferences, comentarios faltando)\n"
        "Reporte TODOS os issues, mas PRIORIZE essenciais no topo.\n"
        "PRE-MORTEM: Para cada issue essencial, descreva o cenario de falha concreto "
        "(\"Se X nao for corrigido, quando Y acontecer, Z sera o resultado\")."
    ),
    # Fallback para feature-dev generico (slash command)
    "feature-dev": (
        "FRAMEWORK DELIBERATIVO — Quatro Causas:\n"
        "Ao desenvolver a feature, considere em cada fase:\n"
        "- Exploracao: Mapeie o SUBSTRATO (causa material) — dados, tabelas, APIs envolvidos\n"
        "- Clarificacao: Defina o TELOS (causa final) — o que constitui sucesso real?\n"
        "- Arquitetura: Integre as 4 causas — material, formal, eficiente, final\n"
        "- Review: Aplique pre-mortem (dynamis) e triagem essencial/acidental\n"
        "Referencia completa: .claude/references/FRAMEWORK_ARISTOTELICO.md"
    ),
}

# Subagentes built-in do Claude Code que se beneficiam do framework
FRAMEWORK_BUILTIN = {
    "Plan": (
        "FRAMEWORK DELIBERATIVO — Quatro Causas para Planejamento:\n"
        "Ao planejar a implementacao, estruture sua analise:\n"
        "- FINAL (telos): Qual o estado desejado? O que constitui sucesso vs fracasso?\n"
        "- MATERIAL (substrato): Que arquivos, tabelas, APIs, dados existem e serao afetados?\n"
        "- FORMAL (padrao): Quais convencoes e padroes do codebase a implementacao deve seguir?\n"
        "- EFICIENTE (mecanismo): Qual a cadeia de mudancas? Que executa cada transformacao?\n"
        "PRE-MORTEM: Antes de finalizar o plano, imagine que ele JA FALHOU. "
        "Quais modos de falha nao foram mapeados? Quais dependencias sao frageis?"
    ),
    "Explore": (
        "FRAMEWORK DELIBERATIVO — Causa Material:\n"
        "Ao explorar o codebase, priorize mapear o SUBSTRATO:\n"
        "- Quais dados, tabelas, APIs e recursos compoe esta area?\n"
        "- Quais dependencias upstream/downstream existem?\n"
        "Ao reportar findings, distinga ESSENCIAL (sem isso a tarefa falha) "
        "de ACIDENTAL (detalhe cosmético que nao afeta funcionalidade)."
    ),
}


def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return

        event = json.loads(input_data)

        tool_name = event.get("tool_name", "")
        if tool_name != "Agent":
            return

        tool_input = event.get("tool_input", {})
        subagent_type = tool_input.get("subagent_type", "")

        if not subagent_type:
            return

        # Verificar se e um subagente feature-dev ou built-in
        # Formatos possiveis: "feature-dev:code-architect", "Plan", "Explore", etc.
        framework_text = None

        if "feature-dev" in subagent_type:
            # Plugin feature-dev: extrair tipo especifico
            parts = subagent_type.split(":")
            specific_type = parts[1] if len(parts) > 1 else "feature-dev"
            framework_text = FRAMEWORK_POR_SUBAGENTE.get(
                specific_type,
                FRAMEWORK_POR_SUBAGENTE["feature-dev"]  # fallback
            )
        elif subagent_type in FRAMEWORK_BUILTIN:
            # Agentes built-in (Plan, Explore)
            framework_text = FRAMEWORK_BUILTIN[subagent_type]

        if framework_text:
            # Output vai para stdout — Claude Code injeta como contexto adicional
            print(framework_text)

    except Exception:
        # Nunca bloquear por erro no hook
        pass


if __name__ == "__main__":
    main()
