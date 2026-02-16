# POP-D07 — Controlar Comprovantes de Entrega

**Categoria**: D — Operacional: Transporte e Entrega
**Prioridade**: P1 (Alta — prova jurídica de entrega)
**Status**: A IMPLANTAR
**Executor Atual**: Ninguém
**Executor Futuro**: Stephanie
**Data**: 2026-02-16
**Autor**: Claude (Agente Logístico)

---

## Objetivo

Garantir que todos os comprovantes de entrega sejam capturados, escaneados e arquivados no SSW Sistemas, assegurando prova jurídica de que a mercadoria foi entregue ao destinatário correto. Sem o comprovante, a CarVia fica exposta a contestações de clientes, recusas de seguro e prejuízos financeiros.

---

## Trigger

- Motorista retorna ao CD após rota de entregas
- Cliente solicita segunda via de comprovante
- Seguradora exige comprovação de entrega para sinistro
- Auditoria interna ou fiscal

---

## Frequência

- **Diária**: Após cada retorno de veículo com entregas realizadas
- **Sob demanda**: Quando cliente ou seguradora solicitar comprovante específico

---

## Pré-requisitos

- [ ] Motorista possui acesso ao SSW Mobile configurado (Opção 945)
- [ ] Scanner (SSWScan) disponível e configurado
- [ ] Impressora térmica para capas de comprovantes (Opção 040)
- [ ] Usuário com permissão para Opção 040, 049, 038, 428
- [ ] Parceiros (unidades T) orientados sobre captura de comprovantes

---

## Passo-a-Passo

### ETAPA 1: Captura do Comprovante pelo Motorista
- **Durante a entrega**: Motorista utiliza SSW Mobile para capturar foto do comprovante assinado pelo destinatário
- **Alternativa papel**: Se cliente assinar papel físico, motorista traz o documento ao CD
- **Validação**: Comprovante deve conter assinatura legível, CPF/RG do recebedor, data e hora

### ETAPA 2: Retorno do Veículo ao CD
- **Acesso SSW**: Abrir **Opção 040** — Capa de Comprovantes
- **Romaneios itinerantes**: Sistema lista CTRCs do veículo que retornou
- **Impressão**: Imprimir capa para organizar comprovantes físicos em ordem

### ETAPA 3: Gravação da Ocorrência "SAIU PARA ENTREGA"
- **Acesso SSW**: Abrir **[Opção 049](../operacional/049-controle-comprovantes.md) — Controle (Saiu para Entrega)**
- **Leitura código de barras**: Escanear código de barras do CTRC
- **Sistema**: Grava automaticamente ocorrência "SAIU PARA ENTREGA" com data/hora

### ETAPA 4: Escaneamento de Comprovantes em Papel
- **SSWScan**: Abrir aplicativo de escaneamento
- **Scan**: Digitalizar cada comprovante físico seguindo ordem da capa (Opção 040)
- **Vinculação**: Sistema vincula arquivo escaneado ao CTRC correspondente
- **Qualidade**: Garantir que assinatura e dados do recebedor estejam legíveis na imagem

### ETAPA 5: Arquivamento Digital
- **Acesso SSW**: Abrir **Opção 428 — Arquivamento de Comprovantes**
- **Verificação**: Confirmar que todos os CTRCs da rota possuem comprovante anexado
- **Armazenamento**: Sistema armazena comprovantes em repositório seguro

### ETAPA 6: Consulta e Validação
- **Acesso SSW**: Abrir **[Opção 038](../operacional/038-baixa-entregas-ocorrencias.md) — Link "Comprovantes"** ou **[Opção 101](../comercial/101-resultado-ctrc.md)**
- **Busca**: Localizar CTRC específico
- **Visualização**: Verificar se comprovante está anexado e legível
- **Segunda via**: Se necessário, exportar PDF para envio ao cliente

---

## Contexto CarVia (Hoje vs Futuro)

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **Responsável** | Ninguém (processo não implantado) | Stephanie (operacional) |
| **Captura** | Parceiros fazem entregas, mas CarVia NÃO valida comprovantes | CarVia cobra comprovantes de parceiros OU captura internamente |
| **Risco** | Alto — sem comprovante, cliente pode contestar entrega | Baixo — comprovante disponível em 100% das entregas |
| **Conhecimento** | Rafael não entendia importância jurídica do comprovante | Equipe treinada: comprovante = prova jurídica |
| **Parceiros (unidades T)** | Não há controle se parceiros capturam no SSW deles | SLA com parceiros: entregar comprovante em até 48h após entrega |
| **Seguradora ESSOR** | Sem comprovante, sinistro pode ser negado | Comprovante anexado facilita aprovação de sinistros |

---

## Erros Comuns e Soluções

| Erro | Causa | Solução |
|------|-------|---------|
| **Comprovante ilegível** | Foto borrada no SSW Mobile | Orientar motorista a capturar em boa iluminação, confirmar nitidez antes de enviar |
| **CTRC sem comprovante** | Motorista esqueceu de capturar ou perdeu papel | Acionar parceiro para solicitar segunda via ao cliente; em último caso, ligar para cliente pedindo confirmação por e-mail |
| **Opção 428 não disponível** | Usuário sem permissão | Solicitar permissão ao administrador SSW (Rafael) |
| **Scanner não reconhece código de barras** | Código danificado ou configuração SSWScan | Digitar número CTRC manualmente na Opção 049 |
| **Parceiro não envia comprovante** | Falta de processo ou negligência | Incluir em contrato: multa de R$ 50 por comprovante não entregue em 48h |
| **Cliente recusa assinatura** | Entrega autorizada sem presença do destinatário | Fotografar mercadoria no local + capturar dados de quem autorizou (portaria, vizinho) |

---

## Verificação Playwright

| Checkpoint | Script Playwright | Asserção |
|------------|-------------------|----------|
| **Comprovante capturado** | `await page.goto('/ssw/opcao/038'); await page.fill('#ctrc', '{numero}'); await page.click('#buscar');` | `await expect(page.locator('.comprovante-anexado')).toBeVisible()` |
| **Ocorrência "SAIU PARA ENTREGA" gravada** | `await page.goto('/ssw/opcao/101'); await page.fill('#ctrc', '{numero}'); await page.click('#historico');` | `await expect(page.locator('text=SAIU PARA ENTREGA')).toBeVisible()` |
| **Capa impressa** | `await page.goto('/ssw/opcao/040'); await page.selectOption('#veiculo', '{placa}'); await page.click('#imprimir');` | `await page.waitForEvent('download')` |
| **Comprovante arquivado** | `await page.goto('/ssw/opcao/428'); await page.fill('#data_inicio', '{data}'); await page.click('#listar');` | `await expect(page.locator('#total-arquivados')).toContainText(/[1-9]\d*/)` |

---

## POPs Relacionados

| Código | Título | Relação |
|--------|--------|---------|
| **POP-D01** | Emitir CT-e (Conhecimento de Transporte Eletrônico) | Comprovante vincula-se ao CTRC gerado pelo CT-e |
| **POP-D03** | Montar Manifesto de Carga | Manifesto lista CTRCs que terão comprovantes capturados |
| **POP-D06** | Rastrear Carga em Tempo Real | Rastreamento mostra status "Entregue", comprovante prova a entrega |
| **POP-E02** | Processar Ocorrências de Entrega | Ocorrência "SAIU PARA ENTREGA" (Opção 049) é etapa deste POP |
| **POP-F05** | Gerenciar Sinistros com Seguradora | Comprovante é documento essencial para aprovação de sinistro ESSOR |

---

## Histórico de Revisões

| Versão | Data | Autor | Alterações |
|--------|------|-------|------------|
| 1.0 | 2026-02-16 | Claude (Agente Logístico) | Criação inicial do POP baseado em docs SSW Opções 038, 040, 049, 428, SSWScan e SSW Mobile |
