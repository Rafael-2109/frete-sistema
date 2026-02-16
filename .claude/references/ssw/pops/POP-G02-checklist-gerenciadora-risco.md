# POP-G02 — Checklist Gerenciadora de Risco

> **Categoria**: G — Compliance, Frota e Gestao
> **Prioridade**: P0 (URGENTE — complemento do G01)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-15
> **Executor atual**: Rafael
> **Executor futuro**: Rafael (supervisao) + operacional

---

## Objetivo

Garantir que TODA carga direta passe pela consulta obrigatoria na gerenciadora de risco ANTES do embarque. A gerenciadora valida motorista, veiculo e carga, autorizando ou bloqueando o transporte conforme regras da seguradora ESSOR.

---

## Trigger

- **TODA carga direta**, antes do embarque (etapa 2 do POP-G01)
- Aplica-se a: caminhao proprio, agregado e transportadora parceira
- Execucao: APOS cadastro de motorista/veiculo, ANTES da emissao do CT-e

---

## Frequencia

Por demanda — a cada carga direta.

---

## Pre-requisitos

| Requisito | Opcao SSW | Verificar |
|-----------|-----------|-----------|
| Veiculo cadastrado | [026](../relatorios/026-cadastro-veiculos.md) | Placa, RNTRC, tipo, proprietario, capacidade |
| Motorista cadastrado | [028](../operacional/028-relacao-motoristas.md) | CPF, CNH, validade, telefones |
| Seguradora configurada | 903/GR | ESSOR ativa como gerenciadora |
| PGR configurado | [390](../comercial/390-cadastro-especies-mercadorias.md) | Limites de valores de mercadoria |
| Rota definida | [403](../cadastros/403-rotas.md) | Origem, destino, distancia, UFs percurso |

---

## Contexto CarVia

### Seguradora
- **ESSOR Seguros** — seguradora da CarVia
- **AT&M** (averba.com.br) — gerenciadora de averbacao, integrada ao SSW
- Averbacao e **automatica** apos autorizacao do CT-e ([opcao 007](../operacional/007-emissao-cte-complementar.md))

### Situacao Atual
- Rafael opera **por intuicao** nas regras de seguro
- NAO consulta formalmente a gerenciadora antes de cada carga
- **Risco**: Sinistro sem cobertura por nao ter seguido protocolo da seguradora

---

## Passo-a-Passo

### ETAPA 1 — Verificar Configuracao SSW (Unica vez / Periodica)

> Esta etapa so precisa ser feita na implantacao ou quando mudar gerenciadora.

1. Acessar opcao **903** → secao **Gerenciamento de Risco**
2. Verificar configuracao:

| Parametro | Valor recomendado | Descricao |
|-----------|-------------------|-----------|
| Gerenciadora | [Nome da gerenciadora ESSOR] | Integrada via WebService |
| Tipo de validacao | **Individual** | Cavalo, carreta, motorista validados individualmente |
| Em caso de nao conformidade | **B — Bloqueia** | Bloqueia emissao se nao atender regras |
| SMP rejeitada impede | **S — Sim** | Impede MDF-e ([025](../operacional/025-saida-veiculos.md)) e Romaneio ([035](../operacional/035-romaneio-entregas.md)) |

3. Acessar [opcao **390**](../comercial/390-cadastro-especies-mercadorias.md) — PGR (Plano de Gerenciamento de Risco)
4. Verificar limites de valor de mercadoria configurados:

| Faixa de valor | Requisitos |
|----------------|-----------|
| Ate R$ [valor] | Rastreador |
| R$ [valor] a R$ [valor] | Rastreador + Isca eletronica |
| Acima de R$ [valor] | Rastreador + Isca + Escolta |

> **[ACAO PENDENTE]**: Confirmar com ESSOR quais sao os limites e requisitos exatos.

---

### ETAPA 2 — Verificar Liberacoes do Veiculo (Opcao 026)

5. Acessar [opcao **026**](../relatorios/026-cadastro-veiculos.md)
6. Pesquisar pela placa do veiculo
7. Verificar campos de liberacao:

| Campo | O que verificar |
|-------|-----------------|
| RNTRC | Numero valido e nao expirado |
| Autorizacao gerenciadora | Status da liberacao (aprovado/reprovado/expirado) |
| Data de validade | Liberacao vigente (nao expirada) |
| Rastreador | Equipamento instalado e ativo (se exigido pela faixa de valor) |

**Se veiculo NAO APROVADO ou liberacao expirada**:
- **PARAR** — Nao prosseguir com este veiculo
- Opcoes:
  a) Solicitar nova autorizacao a gerenciadora
  b) Usar outro veiculo aprovado

---

### ETAPA 3 — Verificar Liberacoes do Motorista (Opcao 028)

8. Acessar [opcao **028**](../operacional/028-relacao-motoristas.md)
9. Pesquisar pelo CPF do motorista
10. Verificar campos de liberacao:

| Campo | O que verificar |
|-------|-----------------|
| CNH | Valida e dentro da validade |
| Autorizacao gerenciadora | Status da liberacao (aprovado/reprovado/expirado) |
| Data de validade | Liberacao vigente |
| Telefones | Preenchidos corretamente (usados para SMP automatico) |

**Se motorista NAO APROVADO ou liberacao expirada**:
- **PARAR** — Nao prosseguir com este motorista
- Opcoes:
  a) Solicitar nova autorizacao a gerenciadora
  b) Usar outro motorista aprovado

---

### ETAPA 4 — Verificar Requisitos da Carga (Opcao 390)

11. Calcular valor total da mercadoria (soma dos valores das NF-es)
12. Consultar [opcao **390**](../comercial/390-cadastro-especies-mercadorias.md) para identificar faixa de valor
13. Verificar se requisitos da faixa estao atendidos:

| Requisito | Onde verificar | Obrigatorio quando |
|-----------|---------------|-------------------|
| Rastreador ativo | Veiculo ([026](../relatorios/026-cadastro-veiculos.md)) | Acima de R$ [valor] |
| Isca eletronica | Gerenciadora | Acima de R$ [valor] |
| Escolta armada | Contratacao separada | Acima de R$ [valor] |
| SMP solicitado | Automatico na saida ([025](../operacional/025-saida-veiculos.md)/[035](../operacional/035-romaneio-entregas.md)) | Sempre |

> **Nota**: Para valores baixos (abaixo da faixa minima), a gerenciadora pode nao exigir consulta. Confirmar com ESSOR.

---

### ETAPA 5 — Registrar Consulta (Processo Fora do SSW)

> **Processo atual (temporario — ate integrar)**: Consultar gerenciadora por fora.

14. Acessar portal da gerenciadora (link a definir)
15. Informar dados:
    - CPF do motorista
    - Placa do veiculo
    - Valor da carga
    - Origem e destino
16. Aguardar resposta:
    - **APROVADO**: Registrar numero do protocolo/SMP
    - **REPROVADO**: **PARAR. Nao embarcar.**
    - **PENDENTE**: Aguardar liberacao antes de prosseguir

> **Processo futuro (com integracao)**: O SSW dispara SMP automaticamente na saida ([opcao 025](../operacional/025-saida-veiculos.md)) e na emissao do Romaneio ([opcao 035](../operacional/035-romaneio-entregas.md)). Quando a integracao estiver configurada:
> - A consulta sera automatica
> - O resultado aparece no SSW ([opcao 117](../comercial/117-monitoracao-embarcadores.md) para verificar recusas)
> - A impressao do DAMDFE pode ser bloqueada ate aprovacao do SMP

---

### ETAPA 6 — Checklist Final

Antes de liberar para as proximas etapas (CT-e, Romaneio, MDF-e):

```
CHECKLIST GERENCIADORA DE RISCO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ ] Veiculo com RNTRC valido
[ ] Veiculo aprovado na gerenciadora
[ ] Rastreador ativo (se exigido)
[ ] Motorista com CNH valida
[ ] Motorista aprovado na gerenciadora
[ ] Telefones do motorista atualizados
[ ] Valor da carga verificado vs faixa PGR
[ ] Requisitos da faixa atendidos (isca, escolta, etc.)
[ ] Protocolo/SMP registrado

RESULTADO: [ ] APROVADO → Prosseguir para POP-C02 (Emitir CTe)
           [ ] REPROVADO → PARAR. Trocar motorista/veiculo.
```

---

## Regras da Seguradora ESSOR (A CONFIRMAR)

> **ATENCAO**: As regras abaixo sao baseadas nas praticas gerais de mercado. Devem ser confirmadas DIRETAMENTE com a ESSOR Seguros.

| Regra | Status | Impacto se violar |
|-------|--------|-------------------|
| CT-e deve estar autorizado ANTES do embarque | [CONFIRMAR] | Sinistro sem cobertura |
| MDF-e deve estar ativo durante transporte interestadual | [CONFIRMAR] | Sinistro sem cobertura |
| Motorista deve estar aprovado na gerenciadora | [CONFIRMAR] | Sinistro sem cobertura |
| Veiculo deve estar aprovado na gerenciadora | [CONFIRMAR] | Sinistro sem cobertura |
| Rastreador deve estar ativo durante todo o transporte | [CONFIRMAR] | Sinistro sem cobertura |
| Averbacao deve ser feita antes do inicio do transporte | Automatica via AT&M | Averbacao ocorre automaticamente na autorizacao do CT-e |
| NF de outro UF (ex: NF do RJ, operacao em SP) | [CONFIRMAR] | Pode nao ter cobertura |

**ACAO**: Rafael deve ligar para ESSOR e solicitar as regras completas de cobertura do seguro de transporte. Documentar aqui.

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Gerenciadora nao responde | Servidor indisponivel | Aguardar e tentar novamente. Se urgente, documentar tentativa |
| Motorista reprovado | Antecedentes, CNH vencida | Trocar motorista |
| Veiculo reprovado | RNTRC expirado, rastreador inativo | Corrigir RNTRC ou ativar rastreador |
| SMP recusado na [opcao 025](../operacional/025-saida-veiculos.md) | Telefone incorreto do motorista | Corrigir telefone na [opcao 028](../operacional/028-relacao-motoristas.md) |
| Transacoes recusadas nao consultadas | Falta de monitoramento | Verificar [opcao 117](../comercial/117-monitoracao-embarcadores.md) diariamente |

---

## Monitoramento Diario

### Opcao 117 — Transacoes de WebService Recusadas
Verificar **diariamente** para detectar problemas com:
- SMP (Solicitacao de Monitoramento Preventivo)
- Atualizacao cadastral (autorizacoes de veiculos/motoristas)
- EDI de averbacao (seguradoras)

### Opcao 056 — Relatorio 165 (Conferencia de Averbacao)
Verificar diariamente:
- Todos os CT-es autorizados no dia anterior foram averbados?
- Alguma rejeicao de averbacao?
- Percentual de documentos averbados (Relatorio 01 — Situacao Geral)

---

## Verificacao Playwright (Parcial)

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| GR ativa no SSW | 903 → Gerenciamento de Risco → configuracao ativa |
| PGR configurado | [390](../comercial/390-cadastro-especies-mercadorias.md) → limites de valor cadastrados |
| Veiculo com RNTRC | [026](../relatorios/026-cadastro-veiculos.md) → pesquisar placa → campo RNTRC preenchido |
| Motorista com CNH valida | [028](../operacional/028-relacao-motoristas.md) → pesquisar CPF → validade CNH |
| SMP bem-sucedido | [117](../comercial/117-monitoracao-embarcadores.md) → verificar ausencia de recusas recentes |
| Averbacao completa | [056](../relatorios/056-informacoes-gerenciais.md) → Relatorio 165 → 100% averbados |

> **Nota**: A consulta a gerenciadora de risco em si ocorre FORA do SSW (portal da gerenciadora). O Playwright pode verificar as configuracoes no SSW e monitorar resultados, mas nao pode executar a consulta na gerenciadora.

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-G01 | Sequencia legal — este POP e a etapa 2 |
| POP-A08 | Cadastrar veiculo — pre-requisito |
| POP-A09 | Cadastrar motorista — pre-requisito |
| POP-C02 | Emitir CTe carga direta — proximo passo apos aprovacao |
| POP-D03 | Manifesto/MDF-e — SMP automatico na saida |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
