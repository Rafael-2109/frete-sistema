# Claude Agent SDK does not support nested subagent delegation

**Nested subagent delegation is explicitly prohibited in the Anthropic Claude Agent SDK (Python).** The SDK enforces a strict single-level hierarchy — a parent agent can delegate to subagents, but those subagents cannot spawn their own sub-subagents. This is an intentional architectural decision, not a missing feature, and is enforced both structurally (in the type system) and at runtime (by withholding the Agent tool from subagent contexts). Anthropic recommends chaining subagents from the main conversation, using Skills, or leveraging the experimental Agent Teams feature as alternatives for workflows that need deeper coordination.

## The type system makes nesting structurally impossible

The core enforcement mechanism is straightforward: `AgentDefinition` and `ClaudeAgentOptions` are deliberately asymmetric. Only `ClaudeAgentOptions` — the top-level query configuration — accepts an `agents` dictionary. The `AgentDefinition` dataclass that defines each subagent has no such parameter:

```python
@dataclass
class AgentDefinition:
    description: str
    prompt: str
    tools: list[str] | None = None
    model: Literal["sonnet", "opus", "haiku", "inherit"] | None = None
```

```python
@dataclass
class ClaudeAgentOptions:
    # ... other fields ...
    agents: dict[str, AgentDefinition] | None = None
    # ... other fields ...
```

**There is no `agents` field on `AgentDefinition`**, making it impossible to define sub-subagents at the type level. The parent configures subagents through `ClaudeAgentOptions.agents`, but each `AgentDefinition` can only specify its own prompt, description, tool access, and model — never its own child agents.

## Runtime enforcement: the Agent tool is withheld from subagents

Beyond the type-level constraint, the SDK also enforces the limit at runtime. The `Agent` tool (previously called `Task`) is the mechanism through which the parent invokes subagents. When a subagent is spawned, this tool is **never exposed** to it. A subagent's available tools include `Bash`, `Glob`, `Grep`, `LS`, `Read`, `Edit`, `Write`, `WebFetch`, `WebSearch`, and others — but **the Agent tool is notably absent**. The official documentation at platform.claude.com states this explicitly:

> *"Subagents cannot spawn their own subagents. Don't include `Agent` in a subagent's `tools` array."*

And the Claude Code documentation reinforces:

> *"This prevents infinite nesting (subagents cannot spawn other subagents) while still gathering necessary context."*

Because nesting is prevented architecturally, **there are no depth limit constants or recursion guards** in the SDK source code. None are needed. GitHub Issue #4182 on `anthropics/claude-code`, titled "Sub-Agent Task Tool Not Exposed When Launching Nested Agents," confirmed this is a known, intentional limitation and was closed as a duplicate.

## How context flows between parent and subagent

Each subagent starts with a **completely fresh 200K-token context window** — no parent conversation history is carried over. The data flow is tightly controlled through two narrow channels:

- **Parent → Subagent**: The only input channel is the `Agent` tool's `prompt` string. All file paths, error messages, or decisions the subagent needs must be packed into this single prompt. The subagent also receives its own system prompt from `AgentDefinition.prompt` and project-level `CLAUDE.md` configuration, but nothing from the parent's conversation.
- **Subagent → Parent**: Only the subagent's **final message** returns to the parent as the Agent tool result. All intermediate tool calls, reasoning steps, and intermediate results stay inside the subagent's context and are never exposed.

This isolation is a feature, not a bug. It means subagent context windows are independent — when the main conversation compacts (summarizes to free space), subagent transcripts are unaffected. Each subagent's transcript persists independently and is cleaned up based on a configurable retention period (default: **30 days**).

The Agent tool's input and output schemas reflect this narrow interface:

| Direction | Schema fields |
|-----------|--------------|
| Input (parent → subagent) | `description` (3–5 word label), `prompt` (task text), `subagent_type` (which agent to invoke) |
| Output (subagent → parent) | `result` (final text), `usage` (token stats), `total_cost_usd`, `duration_ms` |

## Cost and performance realities of flat multi-agent architectures

Even with only single-level delegation, the token economics of multi-agent workflows are significant. Each subagent opens its own context window and generates its own token consumption independently. Practitioners and Anthropic's own documentation report these multipliers:

- **Standard multi-agent (subagents)**: **4–7× more tokens** than a single-agent session
- **Agent Teams (experimental, peer-to-peer)**: **~15× more tokens** than a single session
- **Five parallel subagents on the Pro plan**: rate-limited in approximately **15 minutes** in real-world testing
- Anthropic's architecture whitepaper notes that multi-agent systems broadly use **10–15× more tokens** than single agents

Model selection per subagent matters considerably for cost control. The SDK supports routing subagents to different models via the `model` parameter — `haiku` for simple research/exploration, `sonnet` for standard tasks, and `opus` for complex reasoning. Over **90% of tokens** in heavy sessions are prompt cache reads at reduced rates, which partially offsets the multiplier. The SDK tracks per-model cost breakdowns in the result message, giving visibility into where tokens are consumed.

Context quality also degrades at scale. Multiple practitioners report that **response quality drops noticeably at roughly two-thirds context capacity**, and that user preferences or warnings established early in a session can be lost after automatic compaction. There is no built-in mechanism to prevent multiple subagents from editing the same files simultaneously, which creates coordination challenges in parallel execution.

## Three workarounds for deeper coordination needs

Anthropic documents three alternatives for workflows that seem to require nested delegation:

**Chaining subagents from the main conversation** is the simplest approach. Instead of having subagent A spawn subagent B, the parent agent invokes A, receives its result, and then invokes B with A's output included in B's prompt. This keeps the single-level constraint while achieving sequential multi-step delegation. The parent acts as a manual routing layer.

**Skills** provide reusable procedural knowledge that can be attached to subagents. Instead of nesting agents for domain expertise, a subagent can load Skills that give it step-by-step instructions for complex tasks. Skills use progressive disclosure to avoid context bloat and can substitute for what might otherwise require a deeper agent hierarchy.

**Agent Teams** (experimental as of February 2026) enable peer-to-peer communication between agents running in separate sessions. Unlike subagents, teammates can communicate with each other rather than only reporting back to a parent. However, Agent Teams also cannot nest — teammates cannot spawn sub-teams — and the token cost is approximately **15× baseline**, making them expensive for routine use.

A known but unsupported hack involves having subagents invoke `claude -p` through the Bash tool to spawn new CLI sessions. This creates de facto nesting but introduces severe problems: loss of visibility, complex error handling, no context sharing, resource management chaos, and inconsistent behavior. Anthropic does not endorse this approach.

## Conclusion

The Claude Agent SDK's prohibition on nested subagent delegation is a deliberate architectural choice, enforced at both the type level (`AgentDefinition` lacks an `agents` parameter) and at runtime (the `Agent` tool is excluded from subagent contexts). No recursion guards exist because none are needed — the tool simply isn't available. The design reflects a clear philosophy: **subagents are disposable, isolated workers that receive a prompt and return a result**, not autonomous orchestrators capable of building their own agent hierarchies. For practitioners, the practical implication is that all orchestration logic must live in the parent agent, which chains subagent calls sequentially or fans them out in parallel. The cost multiplier of **4–7× for subagents** (and up to **15× for Agent Teams**) means that even single-level delegation demands careful token budgeting. Anyone designing multi-step pipelines with this SDK should plan for flat hierarchies with explicit parent-mediated handoffs rather than expecting recursive delegation to emerge naturally.



Inclusive, os casos que possuem NF gravada, na tela de embarques/{id}, na coluna de         
  "STATUS/AÇÕES" o "Badge" está ficando como "Pendente" ao invés de "OK".                     
  Acredito que isso ainda não tinhamos mexido, mas o gatilho para gerar e persistir o         
  alerta, poderá ser esse campo + data_embarque pois ambos definem o critério do alerta:      
  1- NF preenchida                                                                            
  2- data_embarque = Tem registro na portaria vinculado a esse embarque com "Saida" gravada.  
                                                                                              
  Os locais que teriamos que mexer seriam                                                     
  1- Os critérios do "Alerta" (data_embarque + badge "Pendente")
  2- Os critérios desse badge "Pendente" localizados em embarques/{id}, na coluna de         
  "STATUS/AÇÕES"
  3- 