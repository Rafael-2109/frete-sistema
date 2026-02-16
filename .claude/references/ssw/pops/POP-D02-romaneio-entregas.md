# POP-D02 — Criar Romaneio de Entregas

> **Categoria**: D — Operacional: Transporte e Entrega
> **Prioridade**: P1 (Alta — pre-requisito do MDF-e)
> **Status anterior**: PARCIAL
> **Criado em**: 2026-02-15
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Criar o Romaneio de Entregas no SSW, que relaciona CTRCs a um veiculo/motorista para entrega. O romaneio e o documento que organiza a carga, define a sequencia de entregas, e aciona automaticamente a ocorrencia "Saiu para Entrega". E tambem pre-requisito para o MDF-e (POP-D03).

---

## Trigger

- CT-e autorizado pelo SEFAZ (opcao 007)
- Carga direta com veiculo e motorista definidos
- Etapa 5 do POP-G01 (Sequencia Legal Obrigatoria)

---

## Frequencia

Por demanda — a cada carga direta.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| CT-e autorizado | [007](../operacional/007-emissao-cte-complementar.md) | CT-e com status "Autorizado" |
| Veiculo cadastrado | [026](../relatorios/026-cadastro-veiculos.md) | Placa, tipo, capacidade |
| Motorista cadastrado | [028](../operacional/028-relacao-motoristas.md) | CPF, CNH valida, telefones |
| Contratacao do veiculo | [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) | CTRB/OS criado (POP-D01) — recomendado |
| CTRCs na unidade CAR | — | CTRCs devem estar disponiveis na unidade |
| Setores definidos | [404](../cadastros/404-setores-coleta-entrega.md) | Opcional — para ordenacao por setor/CEP |

---

## Passo-a-Passo

### ETAPA 1 — Acessar Opcao 035

1. Acessar [opcao **035**](../operacional/035-romaneio-entregas.md) no SSW
2. Verificar que a unidade ativa e **CAR**

---

### ETAPA 2 — Informar Veiculo e Motorista

3. Preencher campos obrigatorios:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Veiculo** | Placa do veiculo | Deve estar cadastrado em [026](../relatorios/026-cadastro-veiculos.md) |
| **Motorista** | CPF do motorista | Deve estar cadastrado em [028](../operacional/028-relacao-motoristas.md) |
| **Data entrega** | Data prevista de entrega | Data em que a entrega sera feita |
| **Itinerante** | N (padrao) | S = romaneio nao retorna no mesmo dia |
| **Ajudante** | — | Somente se controle ativo em 903 |

> **Romaneio Itinerante**: Usar quando a entrega leva mais de 1 dia (ex: carga para outro estado). Comprovantes so entram na Capa (opcao 040) apos "Retorno do Veiculo".

---

### ETAPA 3 — Selecionar CTRCs

4. Sistema exibe CTRCs disponiveis para entrega na unidade CAR
5. Selecionar os CTRCs que serao carregados neste romaneio:
   - Clicar em cada CTRC para selecionar
   - Ou usar filtros para localizar CTRCs especificos
6. Verificar totais do romaneio:
   - Quantidade de CTRCs
   - Peso total
   - Valor total de mercadoria

**CTRCs NAO aparecem como disponiveis se**:
- Tem codigo de ocorrencia (ex: devolvido, reentrega pendente)
- Ja estao em outro romaneio nao cancelado
- Nao estao na unidade CAR

---

### ETAPA 4 — Definir Sequencia de Entregas (Opcional)

> Configurado em opcao 903/Operacao.

**Se 903 = N (ordenacao por SETOR/CEP)**:
- Sistema ordena automaticamente por setor e CEP
- Nenhuma acao necessaria

**Se 903 = S (ordenacao por digitacao)**:
7. Campo **"SEQUENCIA DO ROTEIRO"** estara habilitado
8. Definir a ordem em que as entregas serao feitas
9. Dica: Definir ordem inversa da entrega (primeiro CTRC digitado = ultimo entregue), especialmente se usar SSWBar (volumes carregados por ultimo sao os primeiros a descarregar)

---

### ETAPA 5 — Confirmar Emissao

10. Verificar todos os dados estao corretos
11. Clicar em **Confirmar** / **Emitir Romaneio**
12. Sistema registra automaticamente:
    - Ocorrencia **"85 — Saiu para Entrega"** em cada CTRC
    - SMP automatico (se GR configurada em 903)
    - MDF-e de Romaneio (se [opcao 236](../comercial/236-consulta-reimpressao-romaneios-entrega.md) configurada para emissao automatica em 401)

> **ATENCAO ao SMP**: Se SMP obrigatorio (903) e for rejeitado, a impressao do romaneio pode ser bloqueada. Verificar [opcao 117](../comercial/117-monitoracao-embarcadores.md) em caso de problemas.

13. **Romaneio criado** — anotar o numero

---

### ETAPA 6 — Impressoes (Opcional)

Apos emissao do romaneio, estao disponiveis:

| Documento | Funcao | Quando usar |
|-----------|--------|-------------|
| **Romaneio** | Documento interno com lista de entregas | Sempre |
| **DACTEs** | Documentos fiscais de cada CTRC | Se operacao com papel |
| **DANFEs** | Notas fiscais dos remetentes | Se necessario |
| **Roteiro** | Mapa com locais de entrega numerados | Se motorista nao usa GPS |
| **GPS** | Arquivo IGO para navegador | Se motorista usa GPS |
| **Comprovantes de Entrega** | Formularios para assinatura | Se nao usa SSWMobile |

> **Operacao Sem Papel** (903): Se ativo, DACTEs so sao impressos para clientes que exigem papel (381) ou motoristas sem SSWMobile (028). Codigo de barras do DACTE impresso no Romaneio substitui documento.

---

### ETAPA 7 — Proximo Passo (Sequencia Legal)

Apos romaneio criado, seguir para:

```
Romaneio criado ← VOCE ESTA AQUI
      ↓
6. Criar Manifesto + MDF-e (POP-D03, opcoes [020](../operacional/020-manifesto-carga.md)/[025](../operacional/025-saida-veiculos.md))
      ↓
7. EMBARQUE (so apos MDF-e autorizado)
```

**Se transporte MUNICIPAL (mesma cidade)**:
- MDF-e NAO e obrigatorio
- Pode embarcar diretamente apos o romaneio

---

## Cancelamento de Romaneio

Se precisar cancelar o romaneio (opcao **037**):

### Pode cancelar quando:
- Nenhum CTRC do romaneio recebeu ocorrencia (alem da "85 — Saiu para Entrega")

### NAO pode cancelar quando:
- Algum CTRC ja recebeu ocorrencia de entrega ou devolucao

### O que o cancelamento faz:
- Remove ocorrencia "85 — Saiu para Entrega" (mantem texto de instrucao)
- Cancela automaticamente: Manifesto Operacional, MDF-e, CIOT, Vale Pedagio associados

---

## Romaneio vs Manifesto Operacional

| Aspecto | Romaneio (035) | Manifesto (020) |
|---------|----------------|-----------------|
| **Finalidade** | Organizar entregas ao destinatario final | Transferencia entre unidades |
| **Quando usar** | Carga saindo para ENTREGA | Carga saindo para OUTRA UNIDADE |
| **MDF-e** | Via [opcao 236](../comercial/236-consulta-reimpressao-romaneios-entrega.md) (MDF-e de Romaneio) | Via [opcao 025](../operacional/025-saida-veiculos.md) (saida de veiculo) |
| **Ocorrencia** | "85 — Saiu para Entrega" | Nao gera ocorrencia automatica |
| **Baixa** | [Opcao 038](../operacional/038-baixa-entregas-ocorrencias.md) (baixa de entrega) | [Opcao 030](../operacional/030-chegada-de-veiculo.md) (chegada de veiculo) |

> **Para CarVia carga direta**: Na maioria dos casos, usar Romaneio (035) pois a carga vai direto para o destinatario final. Usar Manifesto (020) somente se a carga precisa passar por uma unidade intermediaria antes da entrega.

---

## Baixa Obrigatoria do Dia Anterior

**Regra SSW**: Todos os CTRCs do romaneio do dia anterior devem receber ocorrencia (entrega, devolucao, reentrega, etc.) antes de emitir novo romaneio no dia seguinte.

**Excecao**: Setores sem controle de retorno ([opcao 404](../cadastros/404-setores-coleta-entrega.md)).

**Se nao der baixa**: Sistema bloqueia emissao de novo romaneio.

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Nenhum CTRC disponivel | CTRCs nao estao na unidade CAR ou ja em romaneio | Verificar [opcao 081](../operacional/081-romaneio.md) (CTRCs disponiveis) |
| SMP rejeitada | Telefone do motorista incorreto | Corrigir em [opcao 028](../operacional/028-relacao-motoristas.md) |
| Bloqueio: baixa dia anterior pendente | Romaneio anterior nao baixado | Dar baixa nos CTRCs do dia anterior ([038](../operacional/038-baixa-entregas-ocorrencias.md)) |
| Romaneio nao cancela | CTRC ja recebeu ocorrencia | Resolver ocorrencia antes de cancelar |
| Veiculo nao encontrado | Nao cadastrado em [026](../relatorios/026-cadastro-veiculos.md) | Cadastrar (POP-A08) |
| Motorista nao encontrado | Nao cadastrado em [028](../operacional/028-relacao-motoristas.md) | Cadastrar (POP-A09) |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Romaneio criado | [Opcao 035](../operacional/035-romaneio-entregas.md) → pesquisar por numero → existe |
| CTRCs no romaneio | Opcao 129 → CTRCs em romaneios → listar |
| Ocorrencia 85 registrada | [Opcao 101](../comercial/101-resultado-ctrc.md) → CTRC → ocorrencia "Saiu para Entrega" |
| SMP enviado | [Opcao 117](../comercial/117-monitoracao-embarcadores.md) → sem recusas recentes |
| Motorista cadastrado | [Opcao 028](../operacional/028-relacao-motoristas.md) → CPF → dados preenchidos |
| Veiculo cadastrado | [Opcao 026](../relatorios/026-cadastro-veiculos.md) → placa → dados preenchidos |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-G01 | Sequencia legal — este POP e a etapa 5 |
| POP-C02 | Emitir CTe carga direta — pre-requisito |
| POP-D01 | Contratar veiculo — recomendado antes |
| POP-D03 | Manifesto/MDF-e — proximo passo |
| POP-D05 | Baixa de entrega — fechar ciclo |
| POP-D06 | Ocorrencias — registrar problemas |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
