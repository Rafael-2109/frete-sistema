<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Specs — indice
> **Papel:** mapa das specs de design. So ponteiros.

- [PAD-A — Arquitetura de Artefatos](2026-06-01-arquitetura-de-artefatos-design.md) — padrao deterministico docs+scripts
- [Atacadao — Split NF por Protocolo ST](2026-06-02-atacadao-split-protocolo-st-design.md) — quebra 1 pedido Atacadao RJ em 2 pedidos Odoo (ST vs demais)
- [HORA — Desconsiderar moto de NF de compra](2026-06-03-hora-desconsiderar-moto-nf-design.md) — flag reversível por item: tira do estoque/recebimento e remove a HoraMoto, valida não-em-pedido/não-recebido
- [HORA — Unificar tela de Pedido de Venda + filtro loja/vendedor + fix desconto](2026-06-03-hora-unificar-pedido-venda-design.md) — tela "Novo pedido" vira única (cria+edita, remove venda_detalhe); critério loja/vendedor por usuário; fix drift de centavos no desconto
- [HORA — Pedido de Venda: editar item (moto travada), Enter=Próximo, chassi autocomplete + regressões](2026-06-03-hora-pedido-venda-edicao-autocomplete-design.md) — editar moto só ajusta desconto/valor (trocar = remover+readicionar); Enter avança campo; chassi vira autocomplete; restaura recursos CRÍTICOS+ALTOS perdidos na unificação
- [HORA — Pedido de Venda: unificação multi-item das 2 telas + submit único (FU-2/3/5)](2026-06-04-hora-pedido-venda-unificacao-multi-item-design.md) — componente de lista de motos idêntico em criação e edição; N motos na criação; um único "Salvar Pedido" que reconcilia header+itens+pagamentos numa transação
- [Simulador 3D de Carga de Motos — Design Spec](2026-04-03-simulador-carga-3d-design.md)
- [Reforma Modulo Pessoal — Controle Financeiro](2026-04-05-pessoal-controle-financeiro-design.md)
- [Design — Features SDK Claude Agent 0.1.60](2026-04-16-agent-sdk-0160-features-design.md)
- [Módulo Pessoal — Evolução em 4 Fases](2026-04-20-pessoal-evolucao-fases-design.md)
- [HORA — Transferência entre Filiais + Registro de Avaria](2026-04-22-hora-transferencia-e-avaria-design.md)
- [Chat in-app + alertas do sistema — Design Spec](2026-04-23-chat-inapp-design.md)
- [HORA — Cadastro, Estoque e Faturamento de Peças](2026-05-05-hora-pecas-design.md)
- [Módulo Motos Assaí — Design](2026-05-07-motos-assai-design.md)
- [Fallback OCR para pedidos HORA via imagem (print de WhatsApp)](2026-05-08-hora-pedido-imagem-ocr-design.md)
- [Skills e Agentes para Módulo motos_assai — Design Spec](2026-05-08-motos-assai-skills-agents-design.md)
- [Onboarding Tours — Lojas HORA + Motos Assaí](2026-05-08-onboarding-tours-hora-assai-design.md)
- [Sistema de Playbooks — Aprendizado Procedimental do Agente](2026-05-11-sistema-playbooks-design.md)
- [Carregamento, Divergência e Fluxo NF — Design](2026-05-12-motos-assai-carregamento-divergencia-design.md)
- [Enriquecimento da exibição de Subagents no Chat Web — Design](2026-05-14-subagent-ui-enrichment-design.md)
- [Spec — Ajuste de Inventário NACOM/LF + Infraestrutura Reutilizável](2026-05-17-ajuste-inventario-nacom-lf-design.md)
- [Spec — Transferência de saldo entre códigos (Odoo) mantendo lote](2026-05-22-transferencia-saldo-codigos-odoo-design.md)
- [Relatório de Confronto de Inventário — Design](2026-05-26-relatorio-confronto-inventario-design.md)
- [Inventário Cíclico — Contagem parcial por quant + Plano de ajustes — Design](2026-05-31-inventario-ciclico-contagem-ajustes-design.md)
- [Design — Capacitar `gestor-estoque-odoo` para remessa inter-company FB→LF (insumo direto, avulsa)](2026-06-02-capacitacao-gestor-remessa-fb-lf-design.md)
- [consultando-venda-loja (design)](2026-06-02-skill-consultando-venda-loja-design.md) — skill READ de vendas Lojas HORA (Onda F)
- [carregando-motos-assai (design)](2026-06-02-skill-carregando-motos-assai-design.md) — skill READ+WRITE de carregamento Motos Assai (Onda F)
