# POP-A08 — Cadastrar Veículo

**Categoria**: A — Implantação e Cadastros
**Prioridade**: P2 (Média — necessário quando CarVia tiver veículos próprios ou agregados)
**Status**: A IMPLANTAR
**Executor Atual**: Rafael
**Executor Futuro**: Rafael
**Data**: 2026-02-16
**Autor**: Claude (Agente Logístico)

---

## Objetivo

Cadastrar veículos da frota (própria ou agregada) no SSW Sistemas com dados completos (placa, tipo, RNTRC, odômetro), garantindo emissão correta de MDF-e e rastreamento de quilometragem para controle de manutenção e custos operacionais.

---

## Trigger

- CarVia adquire veículo próprio
- Novo agregado (carreteiro) assina contrato com CarVia
- SEFAZ rejeita MDF-e por RNTRC inválido
- Necessidade de rastreamento de odômetro para manutenção preventiva

---

## Frequência

- **Sob demanda**: Sempre que novo veículo for incorporado à frota
- **Mensal**: Revisão de RNTRC para evitar vencimentos

---

## Pré-requisitos

- [ ] Documento do veículo (CRLV) em mãos
- [ ] RNTRC válido (Registro Nacional de Transportadores Rodoviários de Carga)
- [ ] Tipo de veículo previamente cadastrado na **[Opção 097](../operacional/097-controle.md) — Tabela de Tipos de Veículo**
- [ ] Usuário com permissão de acesso à **[Opção 026](../relatorios/026-cadastro-veiculos.md) — Cadastro de Veículos**
- [ ] Se veículo for reboque/semirreboque: saber qual trator será vinculado

---

## Passo-a-Passo

### ETAPA 1: Acessar Cadastro de Veículos
- **Acesso SSW**: Abrir **[Opção 026](../relatorios/026-cadastro-veiculos.md) — Cadastro de Veículos**
- **Novo cadastro**: Clicar em "Incluir" ou "Novo"

### ETAPA 2: Preencher Dados Obrigatórios
- **Placa**: Digitar placa no formato AAA-1234 ou AAA1A23 (padrão Mercosul)
- **Tipo de Veículo**: Selecionar na lista (tabela 097)
  - Verificar se tipo possui motor (caminhão, trator) ou não (reboque, semirreboque)
- **Quantidade de Eixos**: Informar número de eixos (define posições de pneus na [Opção 316](../relatorios/316-movimentacao-pneus.md))
- **RNTRC**: Informar número válido (campo crítico para MDF-e)

### ETAPA 3: Configurar Odômetro (se aplicável)
- **Possui Odômetro?**: Marcar "Sim" se veículo tem motor
  - **Quantidade de Dígitos**: Informar quantos dígitos tem o odômetro (ex: 6 dígitos = 999.999 km)
  - **Km Odômetro Atual**: Digitar quilometragem atual mostrada no painel
  - **Quantidade de Voltas**: Iniciar com 0 (incrementa automaticamente quando odômetro zera)
- **Cálculo automático**: Sistema calcula **Km Veículo Total** usando fórmula:
  ```
  Km Veículo = (Qtde Voltas × 1.000.000) + Km Odômetro
  ```
- **Veículos sem motor**: Receberão odômetro do trator ao qual forem acoplados

### ETAPA 4: Atualização Automática de Odômetro (configurar)
- **API Google**: Configurar transferência automática se veículo tiver rastreador
- **Coleta/Entrega Manual**: [Opção 038](../operacional/038-baixa-entregas-ocorrencias.md) permite atualizar manualmente
- **Ordem de Serviço**: [Opção 131](../relatorios/131-ordens-servico.md) registra quilometragem ao abrir OS de manutenção
- **Usuário FRT**: Necessário para atualização manual fora do fluxo padrão

### ETAPA 5: Vincular à Unidade
- **Unidade**: Selecionar unidade responsável pelo veículo
  - Para CarVia: CAR (Santana de Parnaíba) ou CARP (CarVia Polo)

### ETAPA 6: Validar e Salvar
- **Data de Cadastramento**: Sistema preenche automaticamente
- **Verificação RNTRC**: Confirmar que número está correto (rejeição SEFAZ é comum)
- **Salvar**: Confirmar cadastro

### ETAPA 7: Configurar Login SSW Mobile (se aplicável)
- **Opção 945**: Configurar placa como login do motorista no SSW Mobile
- **Senha**: Definir senha padrão (ex: últimos 4 dígitos da placa)

---

## Contexto CarVia (Hoje vs Futuro)

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **Frota Própria** | Não possui — 100% operação subcontratada | Pode adquirir veículos ou agregar carreteiros |
| **Cadastro de Veículos** | Parceiros (unidades T) cadastram seus veículos no SSW deles | CarVia cadastra veículos próprios/agregados no SSW CAR |
| **Placa "ARMAZEM"** | Usada para fracionado sem veículo específico | Mantida para operações internas do CD |
| **Placa Real (Carga Direta)** | Informada manualmente na emissão CT-e ([Opção 004](../operacional/004-emissao-ctrcs.md)) | Cadastrada previamente — CT-e puxa dados automaticamente |
| **RNTRC** | Não controlado (responsabilidade do parceiro) | CarVia valida RNTRC de agregados antes de cadastrar |
| **Odômetro** | Não rastreado | Rastreamento para manutenção preventiva (troca óleo a cada 30.000 km) |
| **MDF-e** | Emitido pelo parceiro | CarVia emite MDF-e próprio com dados corretos do veículo |

---

## Erros Comuns e Soluções

| Erro | Causa | Solução |
|------|-------|---------|
| **SEFAZ rejeita MDF-e por RNTRC inválido** | RNTRC vencido ou digitado errado | Consultar RNTRC válido no site da ANTT antes de cadastrar; atualizar cadastro ([Opção 026](../relatorios/026-cadastro-veiculos.md)) |
| **Tipo de veículo não existe** | Tipo não cadastrado na tabela 097 | Acessar [Opção 097](../operacional/097-controle.md) e cadastrar tipo antes de incluir veículo |
| **Odômetro não atualiza automaticamente** | API Google não configurada ou veículo sem rastreador | Configurar API ou atualizar manualmente via [Opção 038](../operacional/038-baixa-entregas-ocorrencias.md) (coleta/entrega) ou [Opção 131](../relatorios/131-ordens-servico.md) (OS) |
| **Quantidade de eixos errada** | Informação incorreta no cadastro | Corrigir na [Opção 026](../relatorios/026-cadastro-veiculos.md); impacta controle de pneus ([Opção 316](../relatorios/316-movimentacao-pneus.md)) |
| **Veículo sem motor recebe odômetro fixo** | Reboque/semirreboque não herda do trator | Verificar se trator está vinculado corretamente no manifesto ([Opção 020](../operacional/020-manifesto-carga.md)) |
| **Usuário sem permissão FRT** | Tentativa de atualizar odômetro manualmente | Solicitar permissão FRT ao administrador SSW (Rafael) |
| **Placa Mercosul não aceita** | Sistema não reconhece padrão AAA1A23 | Atualizar SSW para versão compatível com padrão Mercosul |

---

## Verificação Playwright

| Checkpoint | Script Playwright | Asserção |
|------------|-------------------|----------|
| **Veículo cadastrado** | `await page.goto('/ssw/opcao/026'); await page.fill('#placa', 'ABC-1234'); await page.click('#buscar');` | `await expect(page.locator('.dados-veiculo')).toBeVisible()` |
| **RNTRC válido** | `await page.goto('/ssw/opcao/026'); await page.fill('#placa', 'ABC-1234'); await page.click('#buscar');` | `await expect(page.locator('#rntrc')).not.toBeEmpty()` |
| **Tipo de veículo correto** | `await page.goto('/ssw/opcao/026'); await page.fill('#placa', 'ABC-1234'); await page.click('#buscar');` | `await expect(page.locator('#tipo_veiculo')).toContainText(/TRATOR\|SEMIRREBOQUE\|CAMINHÃO/)` |
| **Odômetro atualizado** | `await page.goto('/ssw/opcao/026'); await page.fill('#placa', 'ABC-1234'); await page.click('#buscar');` | `await expect(page.locator('#km_veiculo')).not.toContainText('0')` |
| **MDF-e emitido sem erro** | `await page.goto('/ssw/opcao/020'); await page.fill('#placa', 'ABC-1234'); await page.click('#emitir_mdfe');` | `await expect(page.locator('.sucesso-mdfe')).toBeVisible()` |

---

## POPs Relacionados

| Código | Título | Relação |
|--------|--------|---------|
| **POP-A09** | Cadastrar Motorista | Motorista será vinculado ao veículo no manifesto ([Opção 020](../operacional/020-manifesto-carga.md)) |
| **POP-A06** | Cadastrar Tipos de Veículo ([Opção 097](../operacional/097-controle.md)) | Tipo de veículo é pré-requisito para cadastrar veículo |
| **POP-D03** | Montar Manifesto de Carga | Manifesto usa placa cadastrada para emissão de MDF-e |
| **POP-D01** | Emitir CT-e | CT-e pode usar placa do veículo cadastrado |
| **POP-G02** | Gerenciar Manutenção de Veículos ([Opção 131](../relatorios/131-ordens-servico.md)) | OS de manutenção atualiza odômetro automaticamente |
| **POP-D06** | Rastrear Carga (SSW Mobile) | Placa é login do motorista no SSW Mobile (Opção 945) |

---

## Histórico de Revisões

| Versão | Data | Autor | Alterações |
|--------|------|-------|------------|
| 1.0 | 2026-02-16 | Claude (Agente Logístico) | Criação inicial do POP baseado em doc SSW [Opção 026](../relatorios/026-cadastro-veiculos.md) — Cadastro de Veículos |
