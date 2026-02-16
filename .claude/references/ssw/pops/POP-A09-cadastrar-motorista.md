# POP-A09 — Cadastrar Motorista

**Categoria**: A — Implantação e Cadastros
**Prioridade**: P2 (Média — necessário para cargas diretas com terceiros)
**Status**: A IMPLANTAR
**Executor Atual**: Rafael
**Executor Futuro**: Rafael
**Data**: 2026-02-16
**Autor**: Claude (Agente Logístico)

---

## Objetivo

Cadastrar motoristas (próprios, agregados ou terceiros) no SSW Sistemas com dados completos (CPF, CNH, validade, vínculo com transportadora), garantindo emissão correta de MDF-e, liberação pela gerenciadora de risco e rastreamento de histórico operacional.

---

## Trigger

- CarVia contrata motorista próprio ou agregado
- Parceiro informa novo motorista para carga direta
- Gerenciadora de risco (AT&M) exige cadastro prévio para liberar viagem
- SEFAZ rejeita MDF-e por dados incompletos do motorista
- Motorista bloqueado por quarentena ([Opção 228](../comercial/228-motorista-quarentena.md)) precisa ser desbloqueado

---

## Frequência

- **Sob demanda**: Sempre que novo motorista for contratado ou indicado por parceiro
- **Mensal**: Revisão de CNH vencidas e bloqueios em quarentena

---

## Pré-requisitos

- [ ] CPF do motorista
- [ ] Número e validade da CNH (Carteira Nacional de Habilitação)
- [ ] Dados do proprietário/transportadora a qual motorista está vinculado
- [ ] Usuário com permissão de acesso à **[Opção 028](../operacional/028-relacao-motoristas.md) — Cadastro de Motoristas**
- [ ] Se gerenciadora de risco ativa: **[Opção 903](../cadastros/903-parametros-gerais.md) — Gerenciamento de Risco** configurada

---

## Passo-a-Passo

### ETAPA 1: Acessar Cadastro de Motoristas
- **Acesso SSW**: Abrir **[Opção 028](../operacional/028-relacao-motoristas.md) — Cadastro de Motoristas**
- **Novo cadastro**: Clicar em "Incluir" ou "Novo"

### ETAPA 2: Preencher Dados Obrigatórios [CONFIRMAR campos exatos]
- **CPF**: Digitar CPF sem pontos/traços (11 dígitos)
- **Nome Completo**: Informar nome conforme CNH
- **CNH**: Número da Carteira Nacional de Habilitação
- **Validade CNH**: Informar no formato DDMMAA (6 dígitos)
  - Exemplo: 15/08/2028 → digitar **150828**
- **Categoria CNH**: Selecionar categoria (C, D, E, etc.)

### ETAPA 3: Vincular a Transportadora/Proprietário
- **Relação com Transportadora**: Selecionar status do vínculo
  - Opções típicas: Funcionário, Agregado, Terceiro, Autônomo
- **Proprietário**: Se motorista for agregado, vincular ao proprietário do veículo
- **Unidade**: Selecionar unidade responsável (CAR ou CARP para CarVia)

### ETAPA 4: Verificar Bloqueios e Quarentena
- **Motorista Bloqueado**: Verificar se há bloqueio administrativo
  - Motorista bloqueado NÃO pode ser incluído em manifestos ([Opção 020](../operacional/020-manifesto-carga.md))
- **Quarentena ([Opção 228](../comercial/228-motorista-quarentena.md))**: Consultar se motorista está em quarentena temporária
  - Motivos comuns: acidente, multa grave, vencimento CNH
  - Se em quarentena: resolver pendência antes de ativar

### ETAPA 5: Configurar Gerenciadora de Risco (se aplicável)
- **[Opção 903](../cadastros/903-parametros-gerais.md) — Gerenciamento de Risco**: Configurar liberação automática ou manual
  - Se AT&M: Motorista pode precisar aprovação prévia antes de primeira viagem
- **Cadastro de Ajudantes ([Opção 163](../comercial/163-cadastro-ajudantes.md))**: Se motorista tiver ajudante, cadastrar separadamente

### ETAPA 6: Validar e Salvar
- **Último Movimento**: Sistema preenche automaticamente com data do cadastro
- **Número Alternativo (Opção 047)**: Se necessário, configurar número alternativo para acesso
- **Salvar**: Confirmar cadastro

### ETAPA 7: Testar em Manifesto
- **[Opção 020](../operacional/020-manifesto-carga.md) — Manifesto**: Tentar incluir motorista em manifesto de teste
- **MDF-e**: Emitir MDF-e de teste e verificar se SEFAZ aceita dados do motorista

---

## Contexto CarVia (Hoje vs Futuro)

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **Motoristas Próprios** | Não possui — 100% operação subcontratada | Pode contratar motoristas ou agregar carreteiros |
| **Cadastro de Motoristas** | Parceiros (unidades T) cadastram seus motoristas no SSW deles | CarVia cadastra motoristas de cargas diretas previamente |
| **Cargas Diretas** | Rafael informa CPF do motorista na hora da contratação ([Opção 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) e no manifesto ([Opção 020](../operacional/020-manifesto-carga.md)) | Motorista cadastrado previamente — manifesto puxa dados automaticamente |
| **Gerenciadora de Risco** | AT&M é usada para averbação, mas liberação de motorista não é rastreada | [Opção 903](../cadastros/903-parametros-gerais.md) configurada: motorista só liberado após aprovação AT&M |
| **CNH Vencida** | Não há controle — risco de SEFAZ rejeitar MDF-e | Relatório mensal ([Opção 028](../operacional/028-relacao-motoristas.md)) identifica CNHs vencidas |
| **Bloqueio/Quarentena** | Não utilizado | Motorista com acidente/multa grave entra em quarentena ([Opção 228](../comercial/228-motorista-quarentena.md)) até análise |
| **Histórico Operacional** | Não rastreado | Último Movimento mostra data da última viagem do motorista |

---

## Erros Comuns e Soluções

| Erro | Causa | Solução |
|------|-------|---------|
| **SEFAZ rejeita MDF-e por CPF inválido** | CPF digitado errado ou com pontos/traços | Cadastrar CPF somente com 11 dígitos numéricos |
| **CNH vencida** | Validade não atualizada no cadastro | Acessar [Opção 028](../operacional/028-relacao-motoristas.md), atualizar campo Validade CNH com nova data |
| **Motorista bloqueado não aparece no manifesto** | Bloqueio administrativo ativo | Verificar motivo do bloqueio; se resolvido, desbloquear na [Opção 028](../operacional/028-relacao-motoristas.md) |
| **Gerenciadora de risco não libera motorista** | Motorista não cadastrado na AT&M | Enviar dados do motorista para AT&M via [Opção 903](../cadastros/903-parametros-gerais.md); aguardar aprovação |
| **Motorista em quarentena ([Opção 228](../comercial/228-motorista-quarentena.md))** | Pendência não resolvida (acidente, multa) | Acessar [Opção 228](../comercial/228-motorista-quarentena.md), verificar pendência, resolver e remover de quarentena |
| **Formato data inválido** | Data digitada com barras ou 8 dígitos | Usar formato DDMMAA (6 dígitos): 15/08/28 → **150828** |
| **Ajudante não cadastrado** | Ajudante não registrado na [Opção 163](../comercial/163-cadastro-ajudantes.md) | Cadastrar ajudante separadamente antes de incluir no manifesto |
| **Último Movimento não atualiza** | Sistema não registra viagem automaticamente | Verificar se manifesto ([Opção 020](../operacional/020-manifesto-carga.md)) foi finalizado corretamente |

---

## Verificação Playwright

| Checkpoint | Script Playwright | Asserção |
|------------|-------------------|----------|
| **Motorista cadastrado** | `await page.goto('/ssw/opcao/028'); await page.fill('#cpf', '12345678901'); await page.click('#buscar');` | `await expect(page.locator('.dados-motorista')).toBeVisible()` |
| **CNH válida** | `await page.goto('/ssw/opcao/028'); await page.fill('#cpf', '12345678901'); await page.click('#buscar');` | `await expect(page.locator('#validade_cnh')).not.toContainText(/20(20\|21\|22\|23\|24\|25)/)` (não vencida) |
| **Motorista não bloqueado** | `await page.goto('/ssw/opcao/028'); await page.fill('#cpf', '12345678901'); await page.click('#buscar');` | `await expect(page.locator('#status')).not.toContainText('BLOQUEADO')` |
| **Motorista não em quarentena** | `await page.goto('/ssw/opcao/228'); await page.fill('#cpf', '12345678901'); await page.click('#buscar');` | `await expect(page.locator('.sem-resultados')).toBeVisible()` |
| **Manifesto aceita motorista** | `await page.goto('/ssw/opcao/020'); await page.fill('#cpf_motorista', '12345678901'); await page.click('#validar');` | `await expect(page.locator('.motorista-aprovado')).toBeVisible()` |
| **MDF-e emitido sem erro** | `await page.goto('/ssw/opcao/020'); await page.fill('#cpf_motorista', '12345678901'); await page.click('#emitir_mdfe');` | `await expect(page.locator('.sucesso-mdfe')).toBeVisible()` |

---

## POPs Relacionados

| Código | Título | Relação |
|--------|--------|---------|
| **POP-A08** | Cadastrar Veículo | Veículo será vinculado ao motorista no manifesto ([Opção 020](../operacional/020-manifesto-carga.md)) |
| **POP-D03** | Montar Manifesto de Carga | Manifesto usa CPF do motorista cadastrado para emissão de MDF-e |
| **POP-D01** | Emitir CT-e | CT-e pode incluir CPF do motorista responsável pela coleta/entrega |
| **POP-C04** | Contratar Frete com Parceiro ([Opção 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) | Contratação registra CPF do motorista — cadastro prévio facilita |
| **POP-E05** | Gerenciar Bloqueios e Quarentena ([Opção 228](../comercial/228-motorista-quarentena.md)) | Motorista bloqueado não pode ser usado até resolução |
| **POP-F06** | Integrar com Gerenciadora de Risco ([Opção 903](../cadastros/903-parametros-gerais.md)) | Motorista precisa aprovação da AT&M antes de primeira viagem |

---

## Histórico de Revisões

| Versão | Data | Autor | Alterações |
|--------|------|-------|------------|
| 1.0 | 2026-02-16 | Claude (Agente Logístico) | Criação inicial do POP baseado em doc SSW [Opção 028](../operacional/028-relacao-motoristas.md) — Cadastro de Motoristas (nota: doc 028 foca em relatório; campos de cadastro marcados com [CONFIRMAR]) |
