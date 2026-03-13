Abaixo segue a avaliação do Agent SDK emcima do prompt que ele informou que recebeu no inicio da sessão:


Avaliação honesta do prompt v3.7.0 — pontos fortes e problemas reais.

O que funciona bem
Routing strategy é sólida. Domain detection (Nacom vs CarVia), boundary pré/pós-faturamento, e entity resolution (R9) são decisões arquiteturais acertadas.
Memory protocol com critérios de utilidade (PRESCRITIVA/CONTEXTUAL/PROCEDIMENTAL/CORRETIVA) é boa taxonomia.
Linguagem operacional (I7) traduzindo P1-P7 para linguagem natural é essencial para operadores.
Problemas reais
1. Prompt é gigante demais (~670 linhas XML)
Cada sessão paga esse custo de tokens. Muito conteúdo é referência estática que poderia ser lazy-loaded. O bloco MCP tools (~100 linhas) documenta assinaturas que o modelo já recebe via tool schemas. O bloco SSW routing (18 linhas de passos procedurais) deveria estar na skill, não no system prompt.

Impacto: custo por sessão, competição com contexto útil (memórias, dados operacionais).

2. Identidade esquizofrênica
O prompt diz Voce NAO e Claude Code mas roda literalmente dentro do Claude Code SDK com Write, Edit, Bash, Agent tools. O modelo recebe instruções conflitantes — o system prompt diz "chat web" mas o SDK injeta "You are Claude Code, Anthropic's official CLI". Isso gera confusão de comportamento.

Impacto: o agente às vezes age como dev (lê código, cria arquivos) quando deveria agir como operador.

3. Regras numeração quebrada
R1, R2, R3, R4, R5, R6 ausente, R7, R8, R9. I1 ausente, começa em I2. Sugere regras deletadas sem renumerar. Parece desleixo para o modelo — pode gerar dúvida se há instrução faltando.

4. R0 é parcialmente redundante com o boot
O R0 diz "PRIMEIRA MENSAGEM: list_memories → view_memories (SILENCIOSO)". Mas o sistema já injeta <user_memories> com 4 memórias no boot. Então o agente carrega memórias duas vezes — uma pelo boot e outra pelo R0 initialization. Desperdício de tokens e latência.

Sugestão: R0 init deveria ser "verifique se memórias já foram injetadas no boot; se sim, skip list/view".

5. dev_only_skills desperdiça tokens
São 6 linhas listando skills que o agente não pode usar ("resolvendo-problemas", "ralph-wiggum", etc.) + "Se o usuario pedir, responda usando skills operacionais." Listar o que NÃO fazer gasta tokens sem benefício claro. Melhor simplesmente não registrar essas skills.

6. Regras de negócio são resumo, não fonte
P1-P7 está resumido em 3 linhas com "ler REGRAS_P1_P7.md para completo". Mas são as regras mais críticas do sistema. Cada decisão de priorização exige um Read extra. Se o prompt já é grande, vale trocar conteúdo de baixo valor (MCP tool signatures) por conteúdo de alto valor (P1-P7 completo).

7. Sem estratégia de degradação
Quando tool falha, a instrução é "INFORME o usuário e sugira tentar novamente". Não há:

Fallback entre tools (ex: se mcp_sql falha, tentar consultando-sql via Skill)
Limite de retries
Escalonamento (quando parar de tentar e escalar para humano)
8. Contexto operacional é raso
O boot injeta apenas pedidos_urgentes_d2=1 e separacoes_pendentes=1154. Falta:

Quais clientes têm urgência
Alertas de produção/ruptura
Idade do backlog
Tendência (crescendo/estável/diminuindo)
O agente começa cada sessão quase cego sobre o estado real da operação.

9. Coordenação de subagentes é artificialmente limitada
"Delegue para 1 subagente por vez" quando o Agent tool suporta execução paralela. Para casos como "raio-X de 3 pedidos", poderiam rodar em paralelo.

10. Prompt não adapta por perfil de usuário
Rafael (tech lead) e Gabriella (Compras) recebem o mesmo prompt. Debug mode, cross-user access, reflection_bank — tudo isso é irrelevante para Gabriella. Deveria haver prompt tiers ou injeção condicional.

Priorização sugerida
#	Melhoria	Impacto	Esforço
1	Eliminar redundância R0 init vs boot injection	Latência, custo	Baixo
2	Mover MCP signatures e SSW routing para skills	-150 linhas, custo	Médio
3	Incluir P1-P7 completo, remover dev_only_skills	Qualidade de decisão	Baixo
4	Enriquecer operational_context no boot	Proatividade	Médio
5	Prompt tiers por perfil de usuário	Eficiência	Alto
6	Resolver identidade SDK vs agent web	Consistência	Alto
Quer que eu aprofunde em algum ponto específico?