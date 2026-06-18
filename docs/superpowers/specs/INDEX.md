<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-18
-->
# Specs — indice
> **Papel:** mapa das specs de design. So ponteiros.

- [Simulador 3D — Expansão para Conservas Nacom (carga mista pallet + moto)](2026-06-18-simulador-3d-conservas-nacom-design.md) — expande o simulador de motos para conservas palletizadas no mesmo baú; Camada 1 monta pallets PBR (regras 1–4, folga 5cm, overbooking 50%, modos A–D) em Python; Camada 2 estende o bin-packer com perfil multi-slab (estrado+coluna) p/ caminho crítico e empacotamento em 2 fases (Nacom embaixo); sem migration
- [Roteirizacao "Ver no Mapa" — Ampliacao](2026-06-16-roteirizacao-ver-no-mapa-design.md) — custo parametrico por tipo de veiculo (custo_km/motorista/fixo/depreciacao), motor Route Optimization API (sem limite 25), flag volta, dias, incluir/remover on-demand, rotas salvas + cotacao por rota; mono-veiculo; bin-packer fora
- [PAD-A — Arquitetura de Artefatos](2026-06-01-arquitetura-de-artefatos-design.md) — padrao deterministico docs+scripts
- [Onda D — Consolidacao de resolvedores em app/resolvedores](2026-06-01-consolidacao-resolvedores-design.md) — spec da consolidacao dos 7 resolvedores de entidades (Caminho C); EXECUTADA
- [Onda D — Fase 2: resultado do baseline golden-set](2026-06-01-fase2-baseline-resultado.md) — CLIs antigos vs app.resolvedores no mesmo banco (gate da consolidacao); registro historico
- [Atacadao — Split NF por Protocolo ST](2026-06-02-atacadao-split-protocolo-st-design.md) — quebra 1 pedido Atacadao RJ em 2 pedidos Odoo (ST vs demais)
- [HORA — Desconsiderar moto de NF de compra](2026-06-03-hora-desconsiderar-moto-nf-design.md) — flag reversível por item: tira do estoque/recebimento e remove a HoraMoto, valida não-em-pedido/não-recebido
- [HORA — Unificar tela de Pedido de Venda + filtro loja/vendedor + fix desconto](2026-06-03-hora-unificar-pedido-venda-design.md) — tela "Novo pedido" vira única (cria+edita, remove venda_detalhe); critério loja/vendedor por usuário; fix drift de centavos no desconto
- [HORA — Pedido de Venda: editar item (moto travada), Enter=Próximo, chassi autocomplete + regressões](2026-06-03-hora-pedido-venda-edicao-autocomplete-design.md) — editar moto só ajusta desconto/valor (trocar = remover+readicionar); Enter avança campo; chassi vira autocomplete; restaura recursos CRÍTICOS+ALTOS perdidos na unificação
- [HORA — Pedido de Venda: unificação multi-item das 2 telas + submit único (FU-2/3/5)](2026-06-04-hora-pedido-venda-unificacao-multi-item-design.md) — componente de lista de motos idêntico em criação e edição; N motos na criação; um único "Salvar Pedido" que reconcilia header+itens+pagamentos numa transação
- [Transferência de Estoque (Odoo) — tela admin unificada (3 modos)](2026-06-06-transferencia-estoque-odoo-ui-design.md) — local→local, lote→lote, código→código; painel ao vivo A/B/C do código origem + autocomplete; admin-only; simular→confirmar; generaliza o spec de 2026-05-22
- [Lojas HORA — Notificação WhatsApp de NF emitida e pedido confirmado (réplica N8N)](2026-06-06-hora-tagplus-notificacao-whatsapp-design.md) — módulo HORA: gatilhos NF aprovada (webhook_handler) + pedido confirmado (confirmar_venda) → grupo único + DM do vendedor (via usuarios, fallback só-grupo); NF com PDF DANFE anexado (base64 via OpenClaw); fila hora_nfe; require_hora_perm; model hora_. Substitui a tentativa no domínio Nacom (revertida)
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
- [Text-to-SQL — Arquitetura (MASTER)](2026-06-07-text-to-sql-arquitetura-MASTER-design.md) — achados completos do pipeline SQL do agente + decomposicao em 4 subsistemas S0-S3 (sub-planos em plans/); tese: Opus autor unico, permissao≠geracao
- [Aprendizado automatico por efetividade (skills + scripts ad-hoc)](2026-06-07-aprendizado-efetividade-skills-design.md) — avalia no fim da sessao se a skill resolveu (funil estagio0->Haiku->Sonnet); ramos lembrete-usuario (auto) / lembrete-todos + codigo (inbox unificada); conserta directive_promotion shadow sem UI; Fase 2 = scripts ad-hoc via cluster semantico
- [Aprendizado Fase 2 — scripts ad-hoc → skill](2026-06-12-aprendizado-adhoc-fase2-design.md) — captura Bash substantivo pos-sessao (problema ≤100c via Haiku + embedding), cluster pgvector 0.85, criterios C1-C6, quadrifurcacao (skill nova / extensao / roteamento→Fase 1 / descarte com trava), bypass p/ gap nomeado; Camada A (dev) = fase seguinte
- [Limpeza de deprecados/obsoletos + reforço de organização (6 ondas)](2026-06-15-limpeza-deprecados-design.md) — umbrella: teto Moderado faseado, arquivar em _deprecated/, mapa de NÃO-TOCAR (módulos em trabalho ativo), Ondas A-F (lixo/utils-mortos/docs-raiz/.claude/org/anti-drift); fora de escopo = gated v28+/v29+
- [Curadoria semântica do README → text_to_SQL (proposta)](2026-06-15-curadoria-semantica-text2sql.md) — README_MAPEAMENTO_SEMANTICO (jun/2025) curado e verificado campo-a-campo: 152 já-cobertos, 78 lacunas ADICIONAR, 10 drift, 48 business_rules; aplicação via overlays (3 novos: relatorio_faturamento_importado/despesas_extras/usuarios); aguardando aprovação
- [CarVia — Consistência de comissões: ajustes (débito/crédito) + filtro por data de corte](2026-06-15-carvia-comissao-ajustes-design.md) — alteração/cancelamento de `cte_valor` de CTe já comissionado gera `CarviaComissaoAjuste` (delta) abatido no próximo fechamento do mesmo vendedor; nunca total negativo (bloqueia criação); tela de criação só com data final; ✅ EXECUTADO (na main; editar_comissao tb migrado; migration par .sql/.py)
