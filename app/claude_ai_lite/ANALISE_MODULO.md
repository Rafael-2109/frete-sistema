ETAPAS DO FLUXO REAL (conforme orchestrator.py)
#	Etapa	Quem Executa	Descrição
1	Obter Estado Estruturado	🔧 CÓDIGO	obter_estado_json() monta JSON com estado da conversa (entidades, rascunho, opções) - execução determinística

1.1	Carregar Conhecimento de Negócio	🔧 CÓDIGO	_carregar_conhecimento_negocio() busca aprendizados do banco - execução determinística

2	Verificar Comando de Aprendizado	🔧 CÓDIGO	LearningService.detectar_comando() usa REGEX para detectar "Lembre que...", "Esqueça..." - execução determinística

3	Extração Inteligente	🤖 CLAUDE	extrair_inteligente() envia texto + contexto JSON ao Claude que retorna: {intencao, tipo, entidades, ambiguidade, confianca}

3.1	Mapear Entidades	🔧 CÓDIGO	mapear_extracao() traduz campos do Claude (ex: "cliente" → "raz_social_red") usando dicionário fixo MAPEAMENTO_CAMPOS

3.2	Atualizar Estado	🔧 CÓDIGO	EstadoManager.atualizar_do_extrator() atualiza o estado JSON com entidades extraídas - execução determinística

3.3	Tratar Clarificação	🔧 CÓDIGO	Se dominio == "clarificacao", formata pergunta de esclarecimento - execução determinística

4	Buscar Memória	🔧 CÓDIGO	MemoryService.formatar_contexto_memoria() busca histórico do banco - execução determinística

5	Tratamento Especial	🔧 CÓDIGO	Roteia para handlers específicos (_processar_follow_up, _processar_acao) baseado em condicionais

6	Encontrar Capacidade	🔧 CÓDIGO	find_capability() percorre lista de capacidades e chama pode_processar() - execução determinística

7	Executar Capacidade	🔧 CÓDIGO	capacidade.executar() executa query SQL e retorna dados - execução determinística

8	Gerar Resposta	🤖 CLAUDE	responder.gerar_resposta() envia dados + estado JSON ao Claude que gera texto natural

8.1	Revisar Resposta (Self-Consistency)	🔧 CÓDIGO + 🤖 CLAUDE	Primeiro faz verificações locais com regex. Se necessário, chama Claude para revisão

9	Registrar na Memória	🔧 CÓDIGO	MemoryService.registrar_conversa_completa() salva no banco - execução determinística

9.1	Atualizar Contexto	🔧 CÓDIGO	ConversationContextManager.atualizar_estado() atualiza estado local - execução determinística

LEGENDA:
🤖 CLAUDE = Etapa processada pela API do Claude (comportamento não-determinístico)
🔧 CÓDIGO = Etapa executada por código Python (comportamento determinístico/engessado)
RESUMO SIMPLIFICADO:
Etapas onde CLAUDE decide/processa:
Extração Inteligente (etapa 3) - Claude interpreta a mensagem livremente
Gerar Resposta (etapa 8) - Claude formata a resposta em linguagem natural
Revisão via Claude (parte da etapa 8.1) - Claude valida coerência (opcional)
Etapas ENGESSADAS pelo código:
Todas as outras (1, 1.1, 2, 3.1, 3.2, 3.3, 4, 5, 6, 7, 8.1 parcial, 9, 9.1)
COMPARAÇÃO COM O README.md

✅ ESTÁ CORRETO NO README:
Fluxo de 9 etapas - README documenta corretamente o fluxo em 9 etapas principais
Estado Estruturado (PILAR 3) - README descreve bem a estrutura JSON do estado
Extração Inteligente delega ao Claude - README afirma "DELEGA 100% ao Claude" ✅
Entity Mapper como TRADUTOR - README diz "É um TRADUTOR, não um FILTRO" ✅
Responder recebe estado JSON - README documenta que responder recebe estado_estruturado ✅
Self-Consistency Check - README documenta o ResponseReviewer ✅

⚠️ IMPRECISÕES/LACUNAS NO README:
Item	No README	Realidade no Código
Detecção de Aprendizado	Diz "detectar_comando" mas não explica	Usa REGEX fixo (PADROES_LEMBRAR, PADROES_ESQUECER) - não é Claude
find_capability	Diz que "encontra capacidade"	Execução determinística - percorre lista e chama pode_processar()
Execução de Capacidade	README não detalha	Cada capacidade executa SQL/queries no banco - código fixo

Revisão Local	Menciona "Self-Consistency Check"	Primeiro faz verificações com REGEX (campos errados, números suspeitos) antes de chamar Claude

AutoLoader	Diz que "gera loader automaticamente"	Chama Claude para gerar JSON de loader - mas execução do loader é determinística
Prioridade de Fontes	Documenta ["usuario", "rascunho", "extrator", ...]	Código respeita isso em atualizar_do_extrator() - verificação com código fixo
📋 FALTANDO NO README:
Verificações Locais no Reviewer - O README não detalha que há verificações com regex ANTES de chamar Claude:
_verificar_problemas_locais() usa regex para detectar números suspeitos
_detectar_campos_incorretos() usa dicionário CAMPOS_ERRADOS
_detectar_contradicoes() verifica padrões
Fallback para Classificador Legado - README não documenta que se USAR_EXTRATOR_INTELIGENTE = False, o sistema usa o classificador antigo
Execução das Capabilities - README não deixa claro que as capacidades executam queries SQL determinísticas no banco

CONCLUSÃO FINAL
Aspecto	Análise
% de etapas com Claude	~25% (3 de ~12 sub-etapas)
% de etapas engessadas	~75% (9 de ~12 sub-etapas)
README preciso?	~85% preciso - Documenta bem o fluxo alto-nível, mas omite detalhes de implementações determinísticas
O sistema é majoritariamente ENGESSADO, com Claude sendo usado estrategicamente em:
Entrada (interpretar a mensagem do usuário)
Saída (formatar resposta natural)
Validação opcional (revisar coerência)
Todas as operações de busca de dados, mapeamento de campos, execução de queries, gerenciamento de estado são código Python determinístico.