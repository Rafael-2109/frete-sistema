"""
Carregador de Agent Definitions a partir de .claude/agents/*.md.

Le arquivos Markdown com frontmatter YAML e converte para AgentDefinition
do claude_agent_sdk, permitindo que sub-agents customizados funcionem via
Agent SDK web (Task tool com subagent_type).

Mapeamento frontmatter -> AgentDefinition:
- name -> dict key (subagent_type usado no Task tool)
- description -> AgentDefinition.description
- markdown body (apos ---) -> AgentDefinition.prompt
- tools (csv) -> AgentDefinition.tools (list)
- model -> AgentDefinition.model (mapeado para "opus"|"sonnet"|"haiku"|None)
- skills (csv) -> AgentDefinition.skills (list, nativo SDK >= 0.1.49)
                   Fallback: injetado como texto no prompt (SDK < 0.1.49)
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger('sistema_fretes')

# Mapeamento de valores de model do frontmatter para valores aceitos pelo SDK.
# AgentDefinition.model aceita Literal["sonnet", "opus", "haiku", "inherit"] | None.
_MODEL_MAP: Dict[str, str] = {
    "opus": "opus",
    "opus-4-8": "opus",
    "opus_4_8": "opus",
    "opus-4-7": "opus",
    "opus_4_7": "opus",
    "opus-4-6": "opus",
    "opus_4_6": "opus",
    "sonnet": "sonnet",
    "sonnet-4-6": "sonnet",
    "sonnet_4_6": "sonnet",
    "haiku": "haiku",
    "haiku-4-5": "haiku",
    "haiku_4_5": "haiku",
    "inherit": "inherit",
}


def _check_sdk_native_fields() -> bool:
    """
    Verifica se AgentDefinition tem campo 'skills' nativo (SDK >= 0.1.49).

    Executado uma vez no import do modulo. Se True, skills sao passadas via
    campo nativo do AgentDefinition. Se False, fallback para injecao de texto
    no prompt (comportamento original).

    Returns:
        True se SDK tem campos skills/memory/mcpServers, False caso contrario
    """
    try:
        from claude_agent_sdk import AgentDefinition
        import dataclasses
        fields = {f.name for f in dataclasses.fields(AgentDefinition)}
        return 'skills' in fields
    except Exception:
        return False


def _check_effort_field() -> bool:
    """
    Verifica se AgentDefinition tem campo 'effort' nativo (SDK >= 0.1.74).

    SDK 0.1.74 oficializou 'xhigh' no Literal de effort (entre 'high' e 'max',
    Opus 4.7+ (4.7/4.8) com fallback para 'high' em outros modelos). Antes desse
    SDK, effort por subagente so era passavel via extra_args (workaround).

    Returns:
        True se SDK >= 0.1.74 (campo effort presente), False caso contrario
    """
    try:
        from claude_agent_sdk import AgentDefinition
        import dataclasses
        fields = {f.name for f in dataclasses.fields(AgentDefinition)}
        return 'effort' in fields
    except Exception:
        return False


# Detectado uma vez no import — zero overhead por agent carregado
_SDK_HAS_NATIVE_FIELDS = _check_sdk_native_fields()
_SDK_HAS_EFFORT_FIELD = _check_effort_field()

# Valores aceitos pelo Literal de effort (SDK 0.1.74+)
# - low/medium/high/max: suportados em todos modelos com tier compativel
# - xhigh: Opus 4.7+ (4.7/4.8); fallback para 'high' em outros modelos
# - max: Opus-tier only (Opus 4.5+); fallback para 'high' em Sonnet/Haiku
_VALID_EFFORTS: set[str] = {"low", "medium", "high", "xhigh", "max"}


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parseia frontmatter YAML e corpo markdown de um arquivo .md.

    Espera formato:
    ---
    key: value
    ---
    corpo markdown

    Args:
        content: Conteudo completo do arquivo .md

    Returns:
        Tupla (frontmatter_dict, markdown_body)

    Raises:
        ValueError: Se o formato do frontmatter estiver invalido
    """
    content = content.strip()

    if not content.startswith("---"):
        raise ValueError("Arquivo nao comeca com '---' (frontmatter ausente)")

    # Encontrar o segundo '---'
    second_sep = content.find("---", 3)
    if second_sep == -1:
        raise ValueError("Frontmatter nao fechado (segundo '---' ausente)")

    frontmatter_raw = content[3:second_sep].strip()
    body = content[second_sep + 3:].strip()

    # Parse YAML simples (key: value) sem depender de pyyaml
    # para frontmatter trivial. Se falhar, tenta yaml.safe_load.
    frontmatter = _parse_yaml_simple(frontmatter_raw)

    if frontmatter is None:
        try:
            import yaml
            frontmatter = yaml.safe_load(frontmatter_raw) or {}
        except Exception as e:
            raise ValueError(f"Frontmatter YAML invalido: {e}")

    return frontmatter, body


def _parse_yaml_simple(raw: str) -> Optional[dict]:
    """
    Parser YAML minimalista para frontmatter simples (key: value por linha).

    Suporta apenas strings simples e listas CSV (tools: Read, Bash, Glob).
    Retorna None se encontrar estrutura complexa que precisa de yaml.safe_load.

    Args:
        raw: String do frontmatter (entre os ---)

    Returns:
        dict com os campos parseados, ou None se parsing simples falhar
    """
    result = {}

    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        colon_idx = line.find(":")
        if colon_idx == -1:
            # Linha sem ':', nao eh key:value simples
            return None

        key = line[:colon_idx].strip()
        value = line[colon_idx + 1:].strip()

        # Detectar estrutura complexa (listas YAML, dicts aninhados)
        if value.startswith("[") or value.startswith("{"):
            return None
        if value.startswith("|") or value.startswith(">"):
            return None

        result[key] = value

    return result


def _map_model(model_str: Optional[str]) -> Optional[str]:
    """
    Mapeia string de model do frontmatter para valor aceito pelo SDK.

    Args:
        model_str: Valor do campo 'model' no frontmatter (ex: "opus-4-6")

    Returns:
        String aceita pelo SDK ("opus"|"sonnet"|"haiku"|"inherit") ou None
    """
    if not model_str:
        return None

    model_lower = model_str.strip().lower()
    mapped = _MODEL_MAP.get(model_lower)

    if mapped is None:
        logger.warning(
            f"[AGENT_LOADER] Model '{model_str}' nao reconhecido. "
            f"Valores aceitos: {list(_MODEL_MAP.keys())}. Usando None (herda do pai)."
        )

    return mapped


def _parse_tools(tools_value) -> Optional[list]:
    """
    Parseia tools do frontmatter — aceita AMBOS formatos:

    1. String CSV (formato padrao Claude Code CLI):
       tools: Read, Bash, Glob, Grep

    2. Lista YAML:
       tools:
         - Read
         - Bash

    Args:
        tools_value: String CSV OU lista YAML de tool names

    Returns:
        Lista de tools ou None se vazio
    """
    if not tools_value:
        return None

    # Formato lista YAML
    if isinstance(tools_value, list):
        tools = [str(t).strip() for t in tools_value if str(t).strip()]
        return tools if tools else None

    # Formato string CSV (padrao)
    if isinstance(tools_value, str):
        tools = [t.strip() for t in tools_value.split(",") if t.strip()]
        return tools if tools else None

    return None


def _parse_skills(skills_value) -> Optional[list]:
    """
    Parseia skills do frontmatter — aceita AMBOS formatos:

    1. String CSV (formato legado):
       skills: gerindo-expedicao, cotando-frete

    2. Lista YAML (formato oficial Claude Code CLI):
       skills:
         - gerindo-expedicao
         - cotando-frete

    Quando _parse_frontmatter cai em yaml.safe_load (formato lista),
    o valor vem como list[str] em vez de str. Esta funcao aceita ambos
    para manter compatibilidade bidirecional (Claude Code CLI + Agent SDK web).

    Args:
        skills_value: String CSV OU lista YAML de skill names

    Returns:
        Lista de skill names ou None se vazio
    """
    if not skills_value:
        return None

    # Formato lista YAML (oficial Claude Code CLI)
    if isinstance(skills_value, list):
        skills = [str(s).strip() for s in skills_value if str(s).strip()]
        return skills if skills else None

    # Formato string CSV (legado)
    if isinstance(skills_value, str):
        skills = [s.strip() for s in skills_value.split(",") if s.strip()]
        return skills if skills else None

    # Tipo inesperado — logar e retornar None para nao quebrar
    logger.warning(
        f"[AGENT_LOADER] _parse_skills: tipo inesperado {type(skills_value).__name__} — ignorado"
    )
    return None


def _build_prompt_with_skills(body: str, skills_str: Optional[str]) -> str:
    """
    Constroi prompt final incluindo skills disponiveis como texto.

    Fallback para SDK < 0.1.49 onde AgentDefinition nao tem campo 'skills'.
    Quando _SDK_HAS_NATIVE_FIELDS=True, esta funcao NAO e chamada — skills
    sao passadas via campo nativo AgentDefinition.skills.

    Args:
        body: Corpo markdown do arquivo .md
        skills_str: String CSV de skills (ex: "gerindo-expedicao, cotando-frete")

    Returns:
        Prompt completo com secao de skills (se aplicavel)
    """
    if not skills_str:
        return body

    skills = [s.strip() for s in skills_str.split(",") if s.strip()]
    if not skills:
        return body

    # Evitar duplicacao se o corpo ja contem secao de skills
    if "Skills Disponiveis" in body or "skills disponiveis" in body.lower():
        return body

    skills_section = (
        "\n\n## Skills Disponiveis\n\n"
        "Este agente pode usar as seguintes skills via Skill tool: "
        + ", ".join(skills)
        + ".\n"
    )

    return body + skills_section


def load_agent_definitions(agents_dir: str) -> dict:
    """
    Le .claude/agents/*.md e converte para dict[str, AgentDefinition].

    Cada arquivo .md com frontmatter valido gera uma entrada no dict.
    Arquivos com erro sao logados e ignorados (nao bloqueiam os demais).

    SDK >= 0.1.49: skills passadas via AgentDefinition.skills (nativo).
    SDK < 0.1.49: skills injetadas como texto no prompt (fallback).

    Args:
        agents_dir: Caminho para o diretorio .claude/agents/

    Returns:
        dict[str, AgentDefinition] com agents parseados.
        Retorna dict vazio se diretorio nao existir ou nao tiver agents validos.
    """
    try:
        from claude_agent_sdk import AgentDefinition
    except ImportError:
        logger.debug("[AGENT_LOADER] claude_agent_sdk nao disponivel — agents ignorados")
        return {}

    agents_path = Path(agents_dir)

    if not agents_path.is_dir():
        logger.debug(f"[AGENT_LOADER] Diretorio nao encontrado: {agents_dir}")
        return {}

    agent_files = sorted(agents_path.glob("*.md"))

    if not agent_files:
        logger.debug(f"[AGENT_LOADER] Nenhum arquivo .md em: {agents_dir}")
        return {}

    agents: dict = {}

    for agent_file in agent_files:
        try:
            content = agent_file.read_text(encoding="utf-8")

            frontmatter, body = _parse_frontmatter(content)

            # Campo obrigatorio: name
            name = frontmatter.get("name")
            if not name:
                logger.warning(
                    f"[AGENT_LOADER] {agent_file.name}: frontmatter sem 'name' — ignorado"
                )
                continue

            # Campo obrigatorio: description
            description = frontmatter.get("description")
            if not description:
                logger.warning(
                    f"[AGENT_LOADER] {agent_file.name}: frontmatter sem 'description' — ignorado"
                )
                continue

            # Campos opcionais
            model = _map_model(frontmatter.get("model"))
            tools = _parse_tools(frontmatter.get("tools"))
            skills_str = frontmatter.get("skills")
            skills_list = _parse_skills(skills_str)

            # SDK 0.1.51+: Campos de controle de subagentes
            disallowed_tools = _parse_tools(frontmatter.get("disallowed_tools"))
            # max_turns: aceitar tanto int (yaml.safe_load) quanto str (parser simples).
            # Quando frontmatter tem listas YAML (ex: skills:), cai em yaml.safe_load
            # que retorna numeros como int. Parser simples retornaria str.
            # Bug historico (2026-05): chamada `.strip()` em int explodia AttributeError
            # e descartava 7 agents (todos com max_turns: N + skills: lista YAML).
            max_turns_raw = frontmatter.get("max_turns")
            max_turns: Optional[int] = None
            if max_turns_raw is not None:
                if isinstance(max_turns_raw, int) and max_turns_raw > 0:
                    max_turns = max_turns_raw
                elif isinstance(max_turns_raw, str) and max_turns_raw.strip().isdigit():
                    max_turns = int(max_turns_raw)
            initial_prompt = frontmatter.get("initial_prompt")

            # SDK 0.1.74+: effort nativo no AgentDefinition (Literal aceita 'xhigh')
            # Validar contra _VALID_EFFORTS — silenciosamente ignora valores invalidos
            # para nao quebrar carregamento (fallback: subagente herda effort do main).
            effort_raw = frontmatter.get("effort")
            effort: Optional[str] = None
            if effort_raw:
                effort_norm = str(effort_raw).strip().lower()
                if effort_norm in _VALID_EFFORTS:
                    effort = effort_norm
                else:
                    logger.warning(
                        f"[AGENT_LOADER] {agent_file.name}: effort '{effort_raw}' invalido. "
                        f"Aceitos: {sorted(_VALID_EFFORTS)}. Subagente herdara effort do main."
                    )

            # Prompt: nativo (SDK >= 0.1.49) ou fallback (texto no prompt)
            if _SDK_HAS_NATIVE_FIELDS:
                # SDK carrega skills nativamente via AgentDefinition.skills
                prompt = body
            else:
                # Fallback: injetar skills como texto no prompt
                prompt = _build_prompt_with_skills(body, skills_str)

            # Construir AgentDefinition
            agent_kwargs = {
                "description": description,
                "prompt": prompt,
                "tools": tools,
                "model": model,
            }

            # Campos nativos do SDK >= 0.1.49
            if _SDK_HAS_NATIVE_FIELDS and skills_list:
                agent_kwargs["skills"] = skills_list

            # SDK 0.1.51+: Campos de controle de subagentes
            if disallowed_tools:
                agent_kwargs["disallowedTools"] = disallowed_tools
            if max_turns is not None:
                agent_kwargs["maxTurns"] = max_turns
            if initial_prompt:
                agent_kwargs["initialPrompt"] = initial_prompt

            # SDK 0.1.74+: effort por subagente (xhigh = Opus 4.7+)
            # Forward-compat: so passa se SDK suporta o campo (nao quebra em < 0.1.74)
            if effort and _SDK_HAS_EFFORT_FIELD:
                agent_kwargs["effort"] = effort
            elif effort and not _SDK_HAS_EFFORT_FIELD:
                logger.debug(
                    f"[AGENT_LOADER] {name}: effort='{effort}' ignorado (SDK < 0.1.74 sem campo nativo)"
                )

            agent_def = AgentDefinition(**agent_kwargs)

            agents[name] = agent_def

            # Log com indicacao de skills nativas vs injetadas
            skills_mode = (
                f"native:{skills_list}"
                if _SDK_HAS_NATIVE_FIELDS and skills_list
                else f"injected:{skills_str}" if skills_str else "none"
            )
            controls = []
            if disallowed_tools:
                controls.append(f"deny={disallowed_tools}")
            if max_turns:
                controls.append(f"maxTurns={max_turns}")
            if effort:
                controls.append(f"effort={effort}")
            logger.debug(
                f"[AGENT_LOADER] Carregado: {name} | "
                f"model={model} | tools={tools} | "
                f"skills={skills_mode} | "
                f"controls={controls or 'none'} | "
                f"prompt_len={len(prompt)} chars"
            )

        except Exception as e:
            logger.warning(
                f"[AGENT_LOADER] Erro ao carregar {agent_file.name}: {e} — ignorado"
            )
            continue

    if agents:
        logger.info(
            f"[AGENT_LOADER] {len(agents)} agents carregados: {list(agents.keys())} "
            f"(skills={'native' if _SDK_HAS_NATIVE_FIELDS else 'text-injected'})"
        )

    return agents
