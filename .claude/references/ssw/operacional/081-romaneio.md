# Opção 081 — CTRCs Disponíveis para Entrega (Romaneio)

> **Módulo**: Operacional — Planejamento de Entregas
> **Páginas de ajuda**: Parte das 6 páginas consolidadas da opção 030
> **Atualizado em**: 2026-02-14

## Função
Relaciona CTRCs disponíveis para entrega no armazém, permitindo planejamento e roteirização de entregas antes do carregamento físico dos veículos.

## Quando Usar
- Planejar carregamento de veículos de entrega
- Roteirizar entregas para otimizar rotas
- Selecionar CTRCs por setores, clientes, datas ou características específicas
- Gerar etiquetas de sequência de roteiro para facilitar carregamento

## Pré-requisitos
- CTRCs com chegada registrada (opção 030) na unidade
- CTRCs não apontados em Romaneio (opção 035)
- CTRCs sem ocorrência tipo PRÉ-ENTREGA
- CTRCs não segregados (opção 091)
- CTRCs não denegados (opção 007)

## Campos / Interface — Filtros
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Setores | Não | Seleciona setores (opção 404) com totalizadores (CTRCs, m3, peso, valor) |
| Subcontratante | Não | Seleciona CTRCs de subcontratantes (opção 485) |
| Previsão de entrega | Não | CTRCs com data prevista de entrega no período |
| Entrega em cidades | Não | CTRCs de cidades atendidas (opção 402) no período |
| Entrega agendada | Não | CTRCs com agendamento (opção 015) no período |
| Trânsito c/previsão até | Não | CTRCs em trânsito com previsão futura de chegada |
| Só clientes pagadores ABC | Não | Seleciona por Classificação ABC (opção 102) |
| Pessoa destinatária | Não | Jurídica, física ou ambas |
| Ocorrências | Não | CTRCs com última ocorrência específica (opção 405) |
| CNPJ cliente | Não | CTRCs do cliente informado |
| CNPJ raiz cliente | Não | Apenas raiz do CNPJ |
| Situação do CTRC | Não | Pré-CTRCs (até 15 dias), CTRCs autorizados, Segregados |
| Entrega Difícil | Não | CTRCs marcados como Entrega Difícil |
| CTRCs com pendências | Não | Com pendências atribuídas nesta unidade |
| Listar pendências/instruções | Não | Lista última ocorrência/instrução |
| CTRCs descarregados | Não | Com início (opção 078) ou fim (opção 064) de descarga |
| Unidade destino final | Não | P=Parceiro com local diferenciado (opção 422) |
| CTRCs Reversa | Não | N=sem reversa, S=só reversa, T=todos |
| Com agendamento obrigatório | Não | Destinatários exigem agendamento (opção 483) |
| CTRCs prioritários | Não | Mercadoria prioritária (opção 010) |
| Tipo de produtos | Não | Perigosos (código ONU), Anvisa, perecível, vacina |
| CTRCs endereçados | Não | Com volumes endereçados no armazém (opção 152) |
| Relacionar produtos | Não | S=detalhar produtos das NF-es no relatório |
| Excel | Não | Disponibiliza relação em formato Excel |

## Funções de Roteirização (Rodapé)
| Link | Descrição |
|------|-----------|
| Sem roteirizar | Relatório básico dos filtros, CTRCs por Setor (vide RELATÓRIO 1) |
| Roteirizar por setor / Retorna | Roteirização individual dos setores, cada setor recebe número do roteiro, limite 300 pontos/setor, "Retorna" faz roteiro terminar na unidade |
| Roteirizar juntos / Retorna | Roteirização única de todos setores marcados, limite 300 pontos, útil para completar carga |
| Relatório | Relatório da roteirização anterior (vide RELATÓRIO 2), reconhece "Relacionar Produtos=S" |
| Mapa | Mapa da roteirização anterior, link "Atualizar" refaz roteiro após correção de localização, link "Corrigir" ajusta pingo errado |
| Etiqueta roteiro | Informa Número da Sequência após captura do código de barras do volume, anotar no volume com pincel atômico |
| CTRCs em Romaneio | Traz opção 129 com CTRCs em Romaneio de Entregas |

## Processo de Roteirização
1. **Opção 030**: Chegada do veículo, CTRCs disponíveis para entrega
2. **Opção 081**: Planejamento e roteirização sugerida (sequência matemática de menor distância)
3. **SSWBar + Opção 035**: Carregamento físico define sequência DEFINITIVA no Romaneio
4. **SSWMobile**: Motorista segue roteiro e faz baixa de entregas (complementar: opção 038)

## Sequência do Roteiro
- **Número do pingo no mapa**: Identifica volumes para facilitar carregamento
- **Identificação**: 2 formas
  - **Link Etiqueta Roteiro**: Capturar código de barras do volume, anotar sequência com pincel atômico
  - **SSWBar função R**: Imprimir etiqueta 3cm x 3cm

## RELATÓRIO 1 — Sem Roteirizar
| Coluna | Descrição |
|--------|-----------|
| CTRC * | Indica mercadoria com entrega prioritária |
| NFISCAL * | Indica CTRC com Notas Fiscais agrupadas |
| AGENDAMENTO | Data de agendamento (opção 015), OBRIGATORIO indica exigência (opção 483) |
| KgREA | Peso real para dimensionar carga |
| B | S=cliente pagador bloqueado para transporte (opção 483/Crédito) |
| PREVCHEGADA | Previsão de chegada do CTRC em trânsito |
| MANIFESTO/END | Último Manifesto (P=pallet, G=gaiola), END=endereço armazém (opção 152) |
| SERVADIC | D=acesso difícil, E=entrega difícil, A=agendamento, P=palatização, S=separação, C=capatazia, V=veículo dedicado, G=gelo |
| PER | Tempo de permanência (dias) na unidade |
| CTRC DEV/REV | Devolução/reversa a coletar em remetentes com mesmo CNPJ/CPF (evita 2 viagens) |

## RELATÓRIO 2 — Roteirizados
| Coluna | Descrição |
|--------|-----------|
| ETIQ | Número da etiqueta (número do pingo no mapa) |
| I | X=etiqueta mostrada pela opção 081 (anotada) ou impressa SSWBar/R |
| AGENDAMENTO | Data agendamento (opção 015), OBRIGATORIO indica exigência |
| B | S=cliente bloqueado (opção 483/Crédito) |
| MANIFESTO/END | Último Manifesto (P/G=pallet/gaiola), END=endereço armazém |
| PER | Tempo de permanência (dias) na unidade |

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 030 | Chegada — CTRCs disponíveis após chegada |
| 035 | Carregamento SSWBar + emissão Romaneio (sequência definitiva) |
| 038 | Baixa de entregas (complementar ao SSWMobile) |
| SSWBar | Carregamento de volumes obedecendo roteiro |
| SSWMobile | Roteiro de entregas com sequência definitiva |
| 015 | Agendamento de entregas |
| 404 | Cadastro de setores |
| 402 | Cidades atendidas |
| 485 | Subcontratantes |
| 405 | Códigos de ocorrência |
| 483 | Configurações de cliente (agendamento obrigatório, entrega difícil) |
| 091 | Segregação de CTRCs |
| 152 | Endereçamento de volumes no armazém |
| 129 | CTRCs em Romaneio de Entregas |

## Observações e Gotchas
- **Roteirização sobrepõe**: Nova roteirização substitui sequência anterior, necessário trocar anotações/etiquetas
- **Roteiro sugerido ≠ roteiro definitivo**: SSWBar/opção 035 define sequência DEFINITIVA no Romaneio
- **Limite 300 pontos**: Máximo por roteiro (setor ou juntos)
- **Localização errada**: Corrigir antes de anotar volumes ou imprimir etiquetas (link "Corrigir" no mapa, depois "Atualizar")
- **Clientes sem localização**: Considerados na sede da unidade, localização pode ser corrigida manualmente
- **Setores**: Opção 404, usados por unidades principais (opção 402) e alternativas (opção 395)
- **CTRCs não disponíveis**: Já apontados (opção 035), ocorrência PRÉ-ENTREGA, segregados (opção 091), denegados (opção 007)
- **Lembretes do cliente**: Impresso no relatório se cadastrado (opção 055)
- **PREVCHEGADA subcontratante**: Mostrado no relatório se subcontratante identifica unidade em "Domínio/Unidade do parceiro" (opção 401)
- **CTRCs disponíveis para coleta**: Devolução/Reversa com mesmo endereço de entrega, mostrado no relatório
- **Atualização automática mapa**: Após "Corrigir" localização, usar "Atualizar" para recalcular sequência

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
