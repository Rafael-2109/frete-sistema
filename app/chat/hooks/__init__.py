"""
Hooks de integracao do chat com outros modulos.

Cada submodulo expoe funcoes que encapsulam a chamada ao SystemNotifier
com o payload correto para seu evento. Workers/services externos podem
chamar essas funcoes em blocos try/except best-effort — sem risco de
quebrar o fluxo principal.

Tasks 21-23:
- recebimento.notify_recebimento_finalizado(recebimento)
- dfe_bloqueado.notify_dfe_bloqueado(dfe_info, operadores_ids)
- cte_divergente.notify_cte_divergente(cte_info, controllers_ids)

Ativacao pendente: ver app/chat/CLAUDE.md para instrucoes de onde
adicionar a chamada em cada worker.
"""
