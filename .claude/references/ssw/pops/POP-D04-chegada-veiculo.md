# POP-D04 — Registrar Chegada de Veículo

**Categoria**: D — Operacional: Transporte e Entrega
**Prioridade**: P2 (Média)
**Status**: A IMPLANTAR
**Executor Atual**: Rafael
**Executor Futuro**: Stephanie
**Versão**: 1.0
**Data**: 2026-02-16
**Autor**: Claude (Agente Logístico)

---

## Objetivo

Registrar a chegada de veículos de transferência na unidade destino, liberando os CTRCs transportados para operações de entrega ou novas transferências. Este processo garante rastreabilidade da carga e atualiza o status dos documentos no sistema SSW.

---

## Trigger

- Chegada física de veículo com Manifesto Operacional de transferência na base CarVia
- Notificação do parceiro informando chegada de carga consolidada
- Consulta de CTRCs em trânsito (Opção 057) indicando veículo próximo

---

## Frequência

**Operacional**: A cada chegada de veículo com Manifesto de transferência

**Verificação Diária**: Consultar Opção 057 (CTRCs em trânsito) para identificar cargas previstas

---

## Pré-requisitos

1. **Manifesto Operacional emitido** na unidade origem (Opção 029)
2. **Acesso ao SSW** com perfil operacional na unidade CAR ou CARP
3. **Código de barras do Manifesto** (se usar leitura automática) ou número do Manifesto
4. **Conferentes cadastrados** (se controle ativado em 903/Operação)
5. **Veículo e motorista cadastrados** no sistema

---

## Passo-a-Passo

### ETAPA 1: Acessar Registro de Chegada
1. Logar no SSW com usuário operacional
2. Acessar **[Opção 030](../operacional/030-chegada-de-veiculo.md) — Registrar Chegada de Veículos**
3. Sistema exibe Manifestos em trânsito com destino à unidade logada

### ETAPA 2: Identificar o Manifesto
**Opção A — Código de Barras:**
1. Posicionar cursor no campo "Código de Barras"
2. Fazer leitura do código impresso no Manifesto
3. Sistema localiza automaticamente o Manifesto

**Opção B — Seleção Manual:**
1. Localizar Manifesto na lista (filtro por data/origem/veículo)
2. Clicar sobre o Manifesto desejado
3. Sistema abre tela de registro

### ETAPA 3: Registrar Dados de Chegada
1. **Data/Hora Chegada**: Preencher automaticamente (agora) ou ajustar manualmente
2. **Início Descarga** (OPCIONAL): Registrar se houver controle de tempo de descarga
3. **Fim Descarga** (OPCIONAL): Registrar após conclusão da descarga física
4. **Conferentes** (se habilitado): Selecionar colaboradores responsáveis pela conferência
5. **Observações** (OPCIONAL): Registrar ocorrências na chegada (atraso, avaria, falta)

### ETAPA 4: Confirmar Registro
1. Revisar dados preenchidos
2. Clicar em **Confirmar** ou pressionar **F10**
3. Sistema atualiza status do Manifesto para "Chegado"
4. CTRCs ficam disponíveis para entrega ou nova transferência

### ETAPA 5: Verificar Atualização (SSWBar)
1. Se usar **SSWBar** (coletor de dados):
   - Chegada é registrada automaticamente durante leitura de descarga
   - Verificar sincronização com sistema principal
2. Se discrepância: registrar manualmente via Opção 030

### ETAPA 6: Monitorar Descarregamento (Opcional)
1. Acessar **Opção 264 — Acompanhamento de Descarregamento**
2. Verificar progresso da descarga em tempo real
3. Identificar volumes pendentes ou divergências

---

## Contexto CarVia

| Aspecto | Hoje | Futuro (Pós-Implantação) |
|---------|------|--------------------------|
| **Modelo Operacional** | Carga direta (CD → Parceiro → Cliente final). Sem transferências entre bases CarVia. | Consolidação regional: CD → Hub CarVia → Parceiros locais. Manifestos de transferência ativos. |
| **Executor** | N/A (POP não aplicável hoje) | Stephanie registra chegadas no hub regional (ex: CARP — CarVia Polo) |
| **Volume Estimado** | 0 Manifestos/dia | 5-10 Manifestos/semana (estimativa inicial após implantação de hub) |
| **Controle de Descarga** | N/A | Usar SSWBar com controle de tempo (início/fim descarga) para métricas operacionais |
| **Monitoramento** | N/A | Stephanie consulta diariamente Opção 057 (CTRCs em trânsito) para antecipar chegadas |
| **Status Atual** | **A IMPLANTAR** — POP se torna relevante quando CarVia adotar modelo de consolidação/hub | Após implantação: treinamento Stephanie em SSWBar + Opção 030 + Opção 264 |

---

## Erros Comuns e Soluções

| Erro | Causa Provável | Solução |
|------|----------------|---------|
| Manifesto não aparece na lista (Opção 030) | Manifesto não foi emitido na origem OU destino incorreto no Manifesto | 1. Verificar com unidade origem se Manifesto foi gerado (Opção 029). 2. Conferir unidade destino no Manifesto (deve ser CAR ou CARP) |
| Código de barras não reconhecido | Código danificado ou leitura incorreta | Usar seleção manual na lista de Manifestos (filtro por data/veículo) |
| Sistema não permite confirmar chegada | Manifesto já registrado como chegado OU usuário sem permissão | 1. Verificar status do Manifesto (consultar histórico). 2. Validar perfil operacional no SSW (903/Operação) |
| CTRCs não ficam disponíveis após registro | Manifesto com status incorreto OU CTRCs com restrição | 1. Verificar status do Manifesto (deve estar "Chegado"). 2. Consultar CTRCs individualmente (Opção 057) para identificar restrições |
| Discrepância entre SSWBar e sistema | Sincronização pendente ou falha de comunicação | 1. Forçar sincronização no SSWBar. 2. Registrar manualmente via Opção 030 se sincronização falhar |
| Conferentes não aparecem para seleção | Controle desabilitado OU conferentes não cadastrados | 1. Habilitar controle de conferentes em 903/Operação. 2. Cadastrar conferentes no sistema (Opção 90X — cadastros) |

---

## Verificação Playwright

| ID | Verificação | Seletor/Ação | Resultado Esperado |
|----|-------------|--------------|-------------------|
| V1 | Acessar Opção 030 | `click('text=030')` ou navegação por menu | Tela "Registrar Chegada de Veículos" exibida |
| V2 | Lista de Manifestos carregada | `locator('table tbody tr').count()` | > 0 se houver Manifestos em trânsito nos últimos 5 dias |
| V3 | Selecionar Manifesto (exemplo: 1234) | `click('tr:has-text("1234")')` | Tela de registro aberta com dados do Manifesto |
| V4 | Campo Data/Hora Chegada preenchido | `locator('input[name="dataHoraChegada"]').inputValue()` | Data/hora atual (formato SSW: DD/MM/YYYY HH:MM) |
| V5 | Confirmar registro | `click('button:has-text("Confirmar")')` ou `press('F10')` | Mensagem "Chegada registrada com sucesso" OU retorno à lista com Manifesto removido |
| V6 | Verificar status do Manifesto | Consultar Opção 029 (Manifestos) e buscar Manifesto 1234 | Status = "Chegado" |
| V7 | CTRCs disponíveis para operação | Consultar Opção 057 (CTRCs em trânsito) | CTRCs do Manifesto 1234 NÃO aparecem mais em trânsito (liberados para entrega) |

**Notas de Automação**:
- SSW usa IDs dinâmicos → preferir seletores por texto ou atributos estáveis (name, id de formulário)
- Aguardar carregamento após cliques: `page.waitForLoadState('networkidle')`
- Validar mensagens de sucesso/erro: `expect(page.locator('.mensagem-sucesso')).toBeVisible()`

---

## POPs Relacionados

| POP | Título | Relação |
|-----|--------|---------|
| POP-D02 | Emitir Manifesto Operacional | **Pré-requisito**: Manifesto deve ser emitido na origem antes da chegada |
| POP-D05 | Registrar Baixa de Entrega | **Sequencial**: Após chegada, CTRCs são entregues e recebem baixa |
| POP-D06 | Registrar Ocorrências | **Condicional**: Se houver avaria/falta na chegada, registrar ocorrência antes de liberar CTRCs |
| POP-M04 | Monitorar CTRCs em Trânsito (Opção 057) | **Suporte**: Usado para antecipar chegadas e identificar atrasos |
| POP-M05 | Acompanhar Descarregamento (Opção 264) | **Suporte**: Monitora progresso da descarga em tempo real |

---

## Histórico de Revisões

| Versão | Data | Autor | Alterações |
|--------|------|-------|------------|
| 1.0 | 2026-02-16 | Claude (Agente Logístico) | Criação inicial do POP. Status: A IMPLANTAR (relevante após implantação de modelo de consolidação/hub regional) |
