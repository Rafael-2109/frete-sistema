 Ótimo, agora preciso implantar esse mesmo agendamento em 2 outros lugares e diante da forma como se é agendado (baixa planilha, preenche e sobe a planilha) penso em talvez fazer de uma forma otimizada, veja:

Há mais 2 lugares onde se agenda pedido, na carteira de pedidos (onde se agenda por separacao) e em listar_entregas.html (onde se agenda por nf).

Diante das informações necessarias para se realizar o agendamento, Separacao possui todas (tanto que essa rota agenda baseado nessas informações) e em listar_entregas (modelo EntregaMonitorada enriquecido com AgendamentoEntrega) onde há necessidade de capturar o pedido_cliente através do num_pedido de Separacao.

Os botões ao qual me refiro são: listar_entregas.html no modal há uma função que identifica o portal do cliente e direciona pro fluxo por portal, hoje está implantado apenas do Atacadão nesse botão porem agora preciso implantar o do Sendas, o botão que habilita é através dessa parte do html:
"<div id="botoes-portal" style="display: block;" class="mb-3">
                <div class="alert alert-info">
                <strong>🌐 Portal Disponível:</strong> <span id="nome-portal">Portal Atacadão</span>
                </div>
                <div class="d-grid gap-2">
                <button type="button" class="btn btn-primary" id="btn-agendar-portal">
                    📅 Agendar no Portal
                </button>
                <button type="button" class="btn btn-info" id="btn-verificar-protocolo">
                    🔍 Verificar Protocolo no Portal
                </button>
                </div>
                <hr>
            </div>" \
(hoje está configurado apenas Atacadão, mas o objetivo da implantação é habilitar pro Sendas tbm).
\
O agendamento é realizado exatamente da mesma maneira e utilizando exatamente as mesmas informações, porem visto que o processo de agendamento do Sendas é em lote, pensei talvez em "cachear" ou "guardar" todas as demandas de agendamento de listar_entregas e da carteira visto que nesses 2 locais o agendamento é solicitado individualmente (por nf ou por separação) diferentemente da rota de programacao por lote.

Na carteira agrupada, o agendamento é solicitado através do botão:
"<button class="btn btn-outline-info btn-sm" onclick="carteiraAgrupada.agendarNoPortal 'LOTE_20250911_134635_484', '2025-09-18')" title="Agendar no portal">
                            <i class="fas fa-calendar-plus"></i> Agendar
                        </button>"
E no card de separação, realizado através do botão:\
<button class="btn btn-outline-success btn-sm" onclick="window.PortalAgendamento.agendarNoPortal 'LOTE_20250912_113218_387')" 
title="Agendar no portal do cliente">
                                <i class="fas fa-calendar-plus"></i> Agendar
                            </button>
As 2 funções deveriam fazer a mesma coisa, não sei se há diferença mas acredito que não.

Avalie profundamente, pense em uma forma de aproveitar tudo que a rota de agendar em lote já faz para implantar nesses 2 lugares respeitando as diferenças e conferindo as informações necessarias e pense profundamente em uma estratégia para otimizar a solicitação talvez cacheada.


Preciso de um ajuste, vamos verificar o caminho do protocolo do agendamento para cada um dos 3 fluxos.
Vi que existe uma variavel chamada observacao_unica que é redundante e está causando problema pois sendo gravada na planilha de agendamento do Sendas em preencher_planilha, quando essa coluna deveria usar protocolo para manter a rastreabilidade entre Separacao X agenda do portal.

Garanta que o protocolo seja gravado na Separacao / AgendamentoEntrega no momento da captura dos dados respeitando os 3 fluxos e esse mesmo protocolo seja gravado na coluna da planilha do Sendas para garantir rastreabilidade Sistema X Sendas.
Apenas lembrando que no fluxo 1 é 1 protocolo por CNPJ.
Alem disso preciso alterar a Mascara para "AG_(cnpj-7 ATÉ -4)_ddmmyyyy_HHMM"

Evidencias:
Sobrescrevendo e quebrando a rastreabilidade:
- preencher_multiplos_cnpjs: observacao_unica = f"AG_MULTI_{timestamp_obs}"
- preencher_planilha: observacao_unica = f"AGEND_{cnpj[-4:]}_{data_agendamento.strftime('%Y%m%d')}"

Geração do protocolo:
- buscar_dados_completos_cnpj: protocolo = f"AGEND_{cnpj[-4:]}_{data_agendamento.strftime('%Y%m%d')}"
- criar_separacoes_do_saldo: protocolo = f"AGEND_{cnpj[-4:]}_{data_agendamento.strftime('%Y%m%d')}"
- processar_agendamento_sendas_async: protocolo = f"AGEND_{cnpj[-4:]}_{data_agendamento.strftime('%Y%m%d')}"
- adicionar_na_fila - protocolo = f"AGEND_{cnpj_lote[-4:]}_{data_agendamento.strftime('%Y%m%d')}"

Pense profundamente!
Qualquer duvida me pergunte!