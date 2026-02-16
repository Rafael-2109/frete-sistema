# POP-D06 — Registrar Ocorrências

**Categoria**: D — Operacional: Transporte e Entrega
**Prioridade**: P1 (Alta — rastreabilidade e resolução de problemas)
**Status**: PARCIAL
**Executor Atual**: Rafael (ad-hoc, quando parceiro informa)
**Executor Futuro**: Stephanie/Rafael
**Versão**: 1.0
**Data**: 2026-02-16
**Autor**: Claude (Agente Logístico)

---

## Objetivo

Registrar ocorrências que impedem ou atrasam a entrega de CTRCs, garantindo rastreabilidade, comunicação entre unidades (origem/destino) e resolução sistemática de pendências. Este processo permite instruções entre equipes, escalonamento de problemas e compliance com prazos de resolução.

---

## Trigger

- **Durante Transferência**: Avaria, falta, roubo, sinistro identificado em trânsito ou na chegada ([Opção 033](../operacional/033-ocorrencias-de-transferencia.md))
- **Durante Entrega**: Destinatário ausente, recusa, endereço incorreto, falta de documento ([Opção 038](../operacional/038-baixa-entregas-ocorrencias.md))
- **Monitoramento Diário**: Consulta de CTRCs com ocorrência pendente via [Opção 108](../operacional/108-ocorrencias-entrega.md) ou [Opção 133](../operacional/133-ocorrencias-ctrcs.md)
- **Final do Dia**: REGRA SSW — nenhum CTRC com ocorrência deve restar sem instrução ao final do dia

---

## Frequência

**Diária**:
- **Manhã**: Consultar **[Opção 133](../operacional/133-ocorrencias-ctrcs.md)** (Minhas Ocorrências) para verificar instruções recebidas de outras unidades
- **Tarde**: Consultar **[Opção 108](../operacional/108-ocorrencias-entrega.md)** (Instruções para Ocorrências) para enviar instruções a CTRCs com ocorrência registrada no dia
- **Fim do Dia**: Validar que TODOS os CTRCs com ocorrência do dia receberam instrução (responsabilidade da unidade origem ou anterior)

**Ad-hoc**: Quando parceiro/motorista informar problema durante operação

---

## Pré-requisitos

1. **Tabela de Ocorrências** ([Opção 405](../cadastros/405-tabela-ocorrencias.md)) configurada com códigos padrão CarVia
2. **Classificação de Ocorrências**:
   - **Pendência do Cliente**: Responsabilidade do remetente/destinatário (ex: ausente, sem documento)
   - **Responsabilidade da Transportadora**: Problema operacional (ex: avaria, extravio)
3. **Acesso ao SSW** com perfil operacional na unidade que registra a ocorrência
4. **SSWMobile** (recomendado): parceiro/motorista com app para registro em tempo real
5. **Contato com remetente/destinatário** (para instruções de resolução)

---

## Passo-a-Passo

### ETAPA 1: Identificar e Registrar Ocorrência

**Contexto A — Durante Transferência (Opção 033):**
1. Acessar **[Opção 033](../operacional/033-ocorrencias-de-transferencia.md) — Registrar Ocorrências de Transferência**
2. Informar número do Manifesto ou CTRC com problema
3. Selecionar código da ocorrência (ex: "20 — Avaria", "25 — Falta de Volume")
4. Preencher:
   - Data/hora da ocorrência
   - Descrição detalhada (obrigatório para avaria/sinistro)
   - Fotos (se SSWMobile ou sistema integrado)
5. Confirmar registro
6. Sistema gera notificação para unidade origem e destino

**Contexto B — Durante Entrega (Opção 038):**
1. Acessar **[Opção 038](../operacional/038-baixa-entregas-ocorrencias.md) — Registrar Baixa de Entregas** (ver POP-D05)
2. Selecionar CTRC e escolher ocorrência não-finalizadora (ex: "10 — Destinatário Ausente")
3. Preencher data/hora e observações
4. Confirmar registro
5. CTRC fica pendente, aguardando instrução da unidade origem

### ETAPA 2: Consultar Ocorrências Pendentes de Instrução

**Se você é a UNIDADE DESTINO (recebeu CTRC com ocorrência):**
1. Acessar **[Opção 108](../operacional/108-ocorrencias-entrega.md) — Instruções para Ocorrências**
2. Sistema exibe CTRCs da sua unidade com ocorrência pendente de instrução
3. Para cada CTRC:
   - Analisar tipo de ocorrência (Pendência Cliente vs Responsabilidade Transportadora)
   - Contatar remetente/destinatário para obter instrução (reagendar, devolver, etc.)
   - Registrar instrução no sistema (campos específicos por tipo)
4. Confirmar instrução
5. Sistema notifica unidade origem e libera CTRC para ação

**Se você é a UNIDADE ORIGEM (enviou CTRC que teve ocorrência):**
1. Acessar **[Opção 133](../operacional/133-ocorrencias-ctrcs.md) — Minhas Ocorrências**
2. Sistema exibe CTRCs da sua origem com ocorrências registradas por outras unidades
3. Para cada CTRC:
   - Ler instrução recebida da unidade destino
   - Tomar ação conforme instrução (ex: contatar cliente, autorizar devolução, enviar documento)
4. Atualizar status da ocorrência no sistema
5. Se ocorrência resolvida: fechar ocorrência (CTRC volta para fluxo normal)

### ETAPA 3: Segregar Volumes com Instrução Automática (se habilitado)

1. Se configurado **Opção 291 — Segregar Volumes com Instrução Automática**:
2. Ao registrar ocorrência de avaria/falta, sistema:
   - Separa fisicamente os volumes afetados (orientação de armazenagem)
   - Gera instrução automática para unidade origem (ex: "Volume segregado, aguardar vistoria")
3. Verificar área de segregação física e etiquetar volumes conforme sistema

### ETAPA 4: Liberar Ocorrências Finalizadoras para EDI (se necessário)

1. Se ocorrência é **finalizadora** (ex: "Entregue com Ressalva") mas bloqueada para envio EDI:
2. Acessar **Opção 943 — Liberar Ocorrências Finalizadoras para EDI**
3. Selecionar código da ocorrência
4. Autorizar envio para clientes/sistemas integrados
5. Sistema passa a enviar status via EDI/WebService

### ETAPA 5: Estornar Ocorrência (se registrada incorretamente)

1. Acessar **[Opção 138](../comercial/138-estorno-baixa-entrega.md) — Estornar Baixa de Entrega** (mesma opção para ocorrências)
2. Informar CTRC e justificativa do estorno
3. Sistema reverte ocorrência e permite novo registro

### ETAPA 6: Monitorar Prazo de Resolução (REGRA CRÍTICA)

**REGRA SSW**: Nenhum CTRC com ocorrência deve restar sem instrução ao final do dia.

1. **Antes de encerrar expediente**:
   - Consultar **[Opção 108](../operacional/108-ocorrencias-entrega.md)** (se você é destino) → todos CTRCs devem ter instrução enviada
   - Consultar **[Opção 133](../operacional/133-ocorrencias-ctrcs.md)** (se você é origem) → todas instruções recebidas devem ter ação registrada
2. Se houver CTRC sem instrução:
   - **< 3 dias**: Stephanie tenta contato com cliente/parceiro (telefone, WhatsApp, email)
   - **≥ 3 dias**: Escalonar para Rafael (contato comercial de alto nível ou decisão de devolução)
3. Registrar tentativas de contato no campo "Observações" do CTRC

---

## Contexto CarVia

| Aspecto | Hoje | Futuro (Pós-Implantação POP) |
|---------|------|------------------------------|
| **Registro de Ocorrências** | Ad-hoc. Rafael registra quando parceiro informa problema. Sem sistematização. | **Stephanie monitora diariamente** [Opção 108](../operacional/108-ocorrencias-entrega.md) (CTRCs da CarVia com ocorrência). Rafael só escalado após 3 dias sem resolução. |
| **Instruções entre Unidades** | Manual via telefone/WhatsApp. Sem registro formal no SSW. Informação se perde. | **100% via SSW** ([Opção 108](../operacional/108-ocorrencias-entrega.md)/[133](../operacional/133-ocorrencias-ctrcs.md)). Histórico completo de comunicação registrado no sistema. Auditável. |
| **Parceiros e SSWMobile** | Parceiros sem SSWMobile registram ocorrência por telefone (Rafael digita manualmente). Atraso de horas/dias. | **Exigir SSWMobile** de parceiros principais (Alemar, TNT). Registro em tempo real. CarVia recebe notificação automática. |
| **Tipos de Ocorrências** | Códigos genéricos (ex: "Problema na Entrega"). Sem detalhamento. | **Padronizar tabela [405](../cadastros/405-tabela-ocorrencias.md)** ([Opção 405](../cadastros/405-tabela-ocorrencias.md)): códigos específicos (ex: "10.1 — Ausente 1ª Tentativa", "10.2 — Ausente 2ª Tentativa", "15.1 — Recusa sem Justificativa", "15.2 — Recusa por Avaria"). Permite análise de causa raiz. |
| **Segregação Física** | Não utilizada. Volumes com avaria/falta ficam misturados. Risco de entrega errada. | **Habilitar Opção 291**. Área física dedicada para volumes segregados no CD Nacom. Etiqueta vermelha "SEGREGADO — NÃO EXPEDIR". |
| **EDI de Ocorrências** | Não habilitado. Clientes não recebem status de ocorrência (só reclamam quando atrasa). | **Habilitar Opção 943** para códigos principais (Ausente, Recusa, Avaria). Cliente/sistema ERP recebe notificação automática. Reduz ligações. |
| **SLA de Resolução** | Sem SLA. Ocorrências ficam pendentes semanas. Cliente reclama, Rafael corre atrás. | **SLA por tipo**: <br>- Ausente/Recusa: 24h (reagendar) <br>- Avaria: 48h (vistoria + decisão) <br>- Extravio: 72h (rastreamento + sinistro). <br>Stephanie monitora diariamente. Indicador mensal: % resolvidas no SLA. |
| **Responsabilidade** | Tudo com Rafael (gargalo). Ocorrências operacionais competem com comercial/estratégico. | **Stephanie assume operacional** (80% dos casos: ausente, reagendamento, doc faltante). Rafael só casos críticos: sinistro, cliente VIP, decisão comercial (desconto, devolução). |

---

## Erros Comuns e Soluções

| Erro | Causa Provável | Solução |
|------|----------------|---------|
| Código de ocorrência não encontrado ([Opção 033](../operacional/033-ocorrencias-de-transferencia.md)/[038](../operacional/038-baixa-entregas-ocorrencias.md)) | Código não cadastrado OU inativo na tabela [405](../cadastros/405-tabela-ocorrencias.md) | 1. Acessar **[Opção 405](../cadastros/405-tabela-ocorrencias.md)** (Tabela de Ocorrências). 2. Verificar se código existe e está ativo. 3. Se não existe: solicitar cadastro ao administrador SSW (Rafael). |
| Sistema não permite registrar ocorrência | CTRC já baixado com ocorrência finalizadora OU usuário sem permissão | 1. Consultar histórico do CTRC (Opção 057) — verificar se já foi baixado. 2. Se baixado: usar **[Opção 138](../comercial/138-estorno-baixa-entrega.md)** para estornar antes de registrar nova ocorrência. 3. Validar perfil operacional no SSW. |
| Instrução não chega na unidade origem ([Opção 133](../operacional/133-ocorrencias-ctrcs.md)) | Erro de sincronização OU instrução não confirmada corretamente | 1. Verificar se instrução foi CONFIRMADA (não basta preencher, precisa clicar em Confirmar). 2. Aguardar sincronização (pode levar até 5 min). 3. Se > 10 min: contatar suporte SSW ou usar comunicação paralela (telefone) e registrar manualmente. |
| CTRC com ocorrência há > 3 dias sem instrução | Cliente não atende OU decisão complexa (comercial/jurídico) | 1. **Escalonar para Rafael** (enviar resumo: CTRC, ocorrência, tentativas de contato). 2. Rafael decide: forçar devolução, acionar seguradora, ou desconto/bonificação. 3. Registrar decisão no campo Observações do CTRC. |
| Volume segregado não localizado fisicamente | Etiquetagem inadequada OU área de segregação desorganizada | 1. **Revisar processo de segregação** (treinamento equipe CD Nacom). 2. Usar etiquetas VERMELHAS padronizadas ("SEGREGADO — NÃO EXPEDIR"). 3. Área física dedicada e sinalizada. 4. Inventário semanal de segregados (checklist). |
| EDI de ocorrência não enviado ao cliente | Código bloqueado (Opção 943) OU integração EDI inativa | 1. Verificar **Opção 943** — liberar código para envio. 2. Validar configuração EDI do cliente (903/Cliente ou módulo de integração). 3. Se cliente não tem EDI: enviar email manual (template padrão). |
| SSWMobile não sincroniza ocorrência | Sinal fraco OU app desatualizado OU erro de login | 1. Motorista/parceiro: forçar sincronização manual no app (botão "Sincronizar"). 2. Verificar versão do SSWMobile (atualizar se disponível). 3. Se erro persistir: registrar manualmente via [Opção 033](../operacional/033-ocorrencias-de-transferencia.md)/[038](../operacional/038-baixa-entregas-ocorrencias.md) e notificar suporte SSW. |

---

## Verificação Playwright

| ID | Verificação | Seletor/Ação | Resultado Esperado |
|----|-------------|--------------|-------------------|
| V1 | Acessar Opção 033 (Ocorrências de Transferência) | `click('text=033')` ou navegação por menu | Tela "Registrar Ocorrências de Transferência" exibida |
| V2 | Informar Manifesto/CTRC (exemplo: CTRC 123456) | `fill('input[name="numeroCTRC"]', '123456')` + Enter | CTRC 123456 localizado, dados exibidos |
| V3 | Selecionar ocorrência (exemplo: "20 — Avaria") | `selectOption('select[name="ocorrencia"]', '20')` | Ocorrência "20 — Avaria" selecionada, campo descrição obrigatório habilitado |
| V4 | Preencher descrição | `fill('textarea[name="descricao"]', 'Caixa amassada no canto superior esquerdo')` | Descrição preenchida |
| V5 | Confirmar registro | `click('button:has-text("Confirmar")')` ou `press('F10')` | Mensagem "Ocorrência registrada com sucesso" |
| V6 | Acessar Opção 108 (Instruções para Ocorrências) | `click('text=108')` | Tela "Instruções para Ocorrências" exibida com lista de CTRCs pendentes |
| V7 | Verificar CTRC 123456 na lista | `locator('table tbody tr:has-text("123456")')` | CTRC 123456 aparece com ocorrência "20 — Avaria" e status "Aguardando Instrução" |
| V8 | Selecionar CTRC e adicionar instrução | `click('tr:has-text("123456")')` → `fill('textarea[name="instrucao"]', 'Contatar cliente para vistoria')` | Instrução preenchida |
| V9 | Confirmar instrução | `click('button:has-text("Confirmar Instrução")')` | Mensagem "Instrução enviada com sucesso", CTRC removido da lista pendente |
| V10 | Acessar Opção 133 (Minhas Ocorrências) na unidade origem | `click('text=133')` | Tela "Minhas Ocorrências" exibida com CTRC 123456 e instrução "Contatar cliente para vistoria" |
| V11 | Verificar notificação EDI (se habilitado) | Consultar log de integração EDI ou sistema do cliente | Status "Avaria" enviado via EDI com descrição e instrução |

**Notas de Automação**:
- Validar campo descrição obrigatório para ocorrências críticas (avaria, sinistro): `expect(page.locator('textarea[name="descricao"]')).toBeRequired()`
- Aguardar sincronização entre Opção 108 (destino) e Opção 133 (origem): `page.waitForTimeout(5000)` ou polling até instrução aparecer
- Capturar anexos (fotos): se SSWMobile, verificar upload via `input[type="file"]` ou API de anexo

---

## POPs Relacionados

| POP | Título | Relação |
|-----|--------|---------|
| POP-D05 | Registrar Baixa de Entrega | **Pré-requisito**: Ocorrências de entrega são registradas via Opção 038 durante baixa |
| POP-D04 | Registrar Chegada de Veículo | **Condicional**: Ocorrências de transferência (avaria/falta) registradas via Opção 033 na chegada |
| POP-C09 | Configurar Tabela de Ocorrências (Opção 405) | **Cadastro**: Define códigos de ocorrência usados neste POP |
| POP-F05 | Estornar Baixa/Ocorrência (Opção 138) | **Correção**: Usado quando ocorrência foi registrada incorretamente |
| POP-M06 | Segregar Volumes (Opção 291) | **Operacional**: Processo físico de segregação vinculado a ocorrências de avaria/falta |
| POP-I03 | Liberar Ocorrências para EDI (Opção 943) | **Integração**: Habilita envio de status de ocorrência para clientes via EDI |
| POP-M03 | Consultar CTRCs Atrasados (Relatório 011) | **Suporte**: Complementar — identifica CTRCs com ocorrência pendente há > X dias |

---

## Histórico de Revisões

| Versão | Data | Autor | Alterações |
|--------|------|-------|------------|
| 1.0 | 2026-02-16 | Claude (Agente Logístico) | Criação inicial do POP. Status: PARCIAL — hoje Rafael registra ocorrências ad-hoc sem monitoramento sistemático. Futuro: Stephanie assume monitoramento diário (Opção 108/133) com SLA por tipo de ocorrência. Rafael escalado apenas em casos críticos (≥ 3 dias ou decisão comercial). |
