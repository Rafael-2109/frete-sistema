---
name: operando-portal-atacadao
description: >-
  Automacao do PORTAL WEB Atacadao (Hodie Booking, hodiebooking.com.br) via
  Playwright. Usar SOMENTE quando o usuario mencionar EXPLICITAMENTE o portal,
  site, ou Hodie Booking do Atacadao. A solicitacao DEVE conter "Atacadao"
  combinado com "portal", "site", "Hodie", "hodiebooking", ou verbo que
  implique navegacao web ("abrir", "navegar", "acessar", "entrar no").
  Exemplos que DEVEM trigar: "imprimir protocolo no portal Atacadao",
  "ver agendamentos no site do Atacadao", "agendar entrega no portal
  Atacadao", "abrir portal do Atacadao", "navegar no Hodie Booking",
  "entrar no site Atacadao e ver pedidos", "acessar o portal pra imprimir".
  Exemplos que NAO DEVEM trigar (sem mencao ao portal): "consultar saldo
  Atacadao", "verificar agendamento Atacadao", "pedidos do Atacadao" —
  resolvidas localmente por gerindo-expedicao, monitorando-entregas ou
  consultando-sql. NAO USAR para CarVia (gerindo-carvia), SSW
  (operando-ssw), ou dados locais sem portal.
allowed-tools: Read, Bash, Glob, Grep
---

# operando-portal-atacadao

Executa operacoes no **portal Atacadao** (Hodie Booking) via scripts Playwright standalone.
Portal: `https://atacadao.hodiebooking.com.br`

---

## REGRAS CRITICAS

1. Sessao **OBRIGATORIA** — `storage_state_atacadao.json` deve existir antes de qualquer operacao
2. Se sessao expirada, **PARAR** e instruir usuario a fazer re-login interativo (CAPTCHA manual)
3. `--dry-run` e **OBRIGATORIO** na primeira execucao de `agendar_lote.py` — MESMO que usuario peca "direto"
4. Screenshot capturado **ANTES** de qualquer submit destrutivo — evidencia do formulario
5. Agente DEVE usar AskUserQuestion para confirmar antes de agendar sem --dry-run
6. NUNCA inventar protocolos, pedidos ou dados — usar EXATAMENTE o que o portal retorna
7. De-Para de produtos (`ProdutoDeParaAtacadao`) deve estar completo ANTES de agendar

## ANTI-ALUCINACAO

- **Protocolos**: Sempre numeros inteiros capturados do portal. NAO inventar.
- **Produtos**: Codigos do Atacadao != nossos codigos. Sempre usar De-Para.
- **Status**: EXATAMENTE o texto do portal (ex: "Aguardando aprovacao"). NAO traduzir.
- **Resultados do script**: Apresentar EXATAMENTE o que o JSON de saida retorna.
- **Sessao**: Portal tem CAPTCHA. Re-login NAO pode ser automatizado.
- **CSV do portal**: Colunas do CSV podem mudar. NAO assumir nomes de colunas — usar os que o script retorna em `registros[0].keys()`.
- **Fidelidade ao output**: Ao reportar resultados, citar valores EXATAMENTE do JSON de saida. NAO parafrasear status, NAO inventar contadores, NAO arredondar valores.

### Mapeamento CSV do Relatorio → Sistema Local

O CSV exportado de `/relatorio/itens` tem colunas com nomes diferentes do nosso sistema:

| Coluna CSV Portal | Equivalente no Sistema | CUIDADO |
|-------------------|----------------------|---------|
| `Agendamento` (col ~16) | protocolo (separacao.protocolo) | NAO usar coluna "Protocolo" do CSV — pode ser outro campo |
| `Data Agendamento` (col ~15) | data agendada (agendamentos_entrega.data_agendada) | NAO usar "Data Desejada" |
| `Status` | status do agendamento | Valores EXATOS do portal, ex: "Aguardando check-in" = valido/nao recebido |
| `Codigo` | PODE ser duplicado por item | NAO usar como chave unica |
| `Embarque` | mascarado pelo portal | NAO confundir com embarque.id do sistema |

## TRATAMENTO DE ERROS

| Erro | Causa | Acao |
|------|-------|------|
| `RuntimeError: sessao expirada` | Storage state invalido | Pedir re-login interativo |
| Redirecionamento para /login | Sessao expirou | Idem |
| Timeout ao carregar tabela | Portal lento | Aumentar timeout, tentar novamente |
| `Produto sem De-Para` | Mapeamento incompleto | Listar produtos faltantes, NAO agendar |
| `Botao nao encontrado` | Seletores mudaram | Verificar `PORTAL_NAVEGACAO.md`, atualizar config |
| Timeout no download CSV | Portal lento ou sem dados | Reportar erro, sugerir reduzir --dias |
| CSV vazio (0 registros) | Sem agendamentos no periodo | Reportar claramente "0 registros", NAO inventar dados |
| Erro no cruzamento local | Tabela/coluna ausente | Reportar cruzamento_erro, manter dados do portal |

---

## Decision Tree

```
Imprimir PEDIDO(s) do portal? (detalhe ou listagem)
  -> Resolver filial para CNPJ: resolvendo-entidades (se usuario passou nome/numero de filial)
  -> Modo detalhe: imprimir_pedidos.py --pedido 457652 [--cnpj 75315333003043] [--dry-run]
  -> Modo listagem: imprimir_pedidos.py --cnpj 75315333003043 [--dry-run]
  -> Gera PDF em /tmp/pedidos_atacadao/
  -> Output: {"sucesso": true, "modo": "detalhe"|"listagem", "pdf_path": "...", "pdf_size_kb": N}

Imprimir PROTOCOLO(s) de agendamento? (senha de entrega)
  -> NAO usar imprimir_pedidos.py — usar impressao_protocolo.py diretamente
  -> from app.portal.atacadao.impressao_protocolo import gerar_pdf_protocolo_atacadao
  -> gerar_pdf_protocolo_atacadao(protocolo="12345")
  -> Gera PDF em /tmp/protocolos_atacadao/
  -> DISTINCAO: protocolo = senha de agendamento (numero inteiro). Pedido = numero do pedido no portal.

Consultar agendamentos futuros de um CNPJ?
  -> consultar_agendamentos.py --cnpj 12345678000190 [--dias 30] [--cruzar-local]
  -> Sem --cruzar-local: exporta CSV + retorna registros e resumo por_status
  -> Com --cruzar-local: adiciona resumo_cruzamento com contadores:
     agendamento_disponivel, agenda_perdida, em_dia, entregue, sem_cruzamento
  -> Output: {"sucesso": true, "total_registros": N, "csv_path": "...",
              "resumo": {"total": N, "por_status": {...}},
              "resumo_cruzamento": {...} (se --cruzar-local)}

Consultar saldo disponivel para agendamento (pedido/filial)?
  -> consultar_saldo.py --pedido VCD12345 [--filial CNPJ]
  -> Captura produtos com quantidades do portal

Agendar entrega em lote?
  -> Verificar De-Para: consultar_saldo.py --pedido X (confirma mapeamento)
  -> agendar_lote.py --lote-id LOTE123 --data 2026-03-15 --dry-run
  -> AskUserQuestion: "Confirmar agendamento?"
  -> agendar_lote.py --lote-id LOTE123 --data 2026-03-15

Sessao expirada?
  -> NAO usar esta skill. Instruir: "python -m app.portal.atacadao.login_interativo"

Consultar dados de agendamento SEM acessar portal?
  -> NAO usar esta skill. Usar consultando-sql ou gerindo-expedicao
```

---

## Arquitetura

```
Agente Web
  1. Le atacadao_defaults.json (timeouts, veiculos, status)
  2. Verifica sessao via browser_atacadao_login (MCP tool) ou script
  3. AskUserQuestion (dados variaveis: protocolo, pedido, data)
  4. Executa script [--dry-run] -> preview
  5. AskUserQuestion ("Confirmar execucao?") [se destrutivo]
  6. Executa script sem --dry-run -> executa de verdade
```

Scripts sao standalone (Playwright sync), importam de `app.portal.atacadao.*`.
Requerem `create_app()` + `app.app_context()` quando acessam banco (acoes 2-4).

---

## Scripts

| # | Script | Proposito | Status |
|---|--------|-----------|--------|
| 0 | `atacadao_common.py` | Funcoes compartilhadas (sessao, sessao download, screenshot, saida JSON) | IMPLEMENTADO |
| 1 | `imprimir_pedidos.py` | Imprimir pedidos como PDF — detalhe (--pedido) ou listagem (--cnpj) | IMPLEMENTADO |
| 2 | `consultar_agendamentos.py` | Export CSV de agendamentos futuros por CNPJ, cruzamento local opcional | IMPLEMENTADO |
| 3 | `consultar_saldo.py` | Consultar saldo disponivel por pedido/filial | PENDENTE |
| 4 | `agendar_lote.py` | Agendar entrega em lote (--dry-run obrigatorio) | PENDENTE |

---

## Infraestrutura Existente (reutilizada)

| Arquivo | Papel | Usado por |
|---------|-------|-----------|
| `app/portal/atacadao/config.py` | URLs, seletores, veiculos, timeouts | Todos |
| `app/portal/atacadao/playwright_client.py` | AtacadaoPlaywrightClient (sync, ~700 LOC) | Todos |
| `app/portal/atacadao/login_interativo.py` | Login com CAPTCHA, re-login | Sessao |
| `app/portal/atacadao/impressao_protocolo.py` | GeradorPDFProtocoloAtacadao (protocolos, NAO pedidos) | Impressao de protocolos |
| `app/portal/atacadao/verificacao_protocolo.py` | VerificadorProtocoloAtacadao | Script 2 |
| `app/portal/atacadao/models.py` | ProdutoDeParaAtacadao | Scripts 3, 4 |
| `app/portal/atacadao/routes_agendamento.py` | Rotas Flask (preparar, gravar, confirmar) | Script 4 |

---

## MCP Tool

| Tool | Proposito |
|------|-----------|
| `browser_atacadao_login` (C5) | Carrega sessao Atacadao no browser MCP, verifica validade |

---

## References (carregar sob demanda)

| Quando o agente precisa de... | Ler |
|-------------------------------|-----|
| Seletores e caminhos do portal | [PORTAL_NAVEGACAO.md](references/PORTAL_NAVEGACAO.md) |
| URLs, veiculos, timeouts padrao | `atacadao_defaults.json` |
| Config existente (seletores) | `app/portal/atacadao/config.py` |
