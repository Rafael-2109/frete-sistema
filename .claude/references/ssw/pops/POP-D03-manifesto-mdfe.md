# POP-D03 — Criar Manifesto e Emitir MDF-e

> **Categoria**: D — Operacional: Transporte e Entrega
> **Prioridade**: P0 (URGENTE — obrigatorio interestadual, nunca fizeram)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-15
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Criar o Manifesto Operacional no SSW e emitir o MDF-e (Manifesto Eletronico de Documentos Fiscais) junto ao SEFAZ. O MDF-e e **obrigatorio para qualquer transporte interestadual** e a CarVia **nunca emitiu um MDF-e** ate o momento.

---

## Trigger

- Carga direta com destino em **outro estado** (transporte interestadual)
- CT-e ja autorizado pelo SEFAZ
- Veiculo e motorista definidos e cadastrados

---

## Frequencia

Por demanda — a cada carga direta interestadual.

---

## Pre-requisitos

### Cadastros obrigatorios
| Cadastro | Opcao SSW | O que verificar |
|----------|-----------|-----------------|
| Veiculo (cavalo) | [026](../relatorios/026-cadastro-veiculos.md) | Placa cadastrada, RNTRC valido |
| Carreta (se aplicavel) | [026](../relatorios/026-cadastro-veiculos.md) | Placa cadastrada |
| Proprietario | [027](../operacional/027-relacao-proprietarios-veiculos.md) | RNTRC atualizado (SEFAZ valida) |
| Motorista | [028](../operacional/028-relacao-motoristas.md) | CPF, telefones (para SMP automatico) |
| Unidade origem | [401](../cadastros/401-cadastro-unidades.md) | CAR configurada |
| Unidade destino | [401](../cadastros/401-cadastro-unidades.md) | Sigla destino cadastrada |
| Rota | [403](../cadastros/403-rotas.md) | Previsao chegada e UFs de percurso cadastradas |

### Documentos obrigatorios
- CT-e **autorizado** pelo SEFAZ ([opcao 007](../operacional/007-emissao-cte-complementar.md))
- Contratacao do veiculo realizada ([opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) — recomendado antes do manifesto

### Configuracoes SSW
- Certificado digital A1 valido (configurado pela Equipe SSW)
- Inscricao Estadual configurada

---

## Passo-a-Passo

### PARTE 1 — Criar Manifesto Operacional (Opcao 020)

#### 1.1 Montar a Placa Provisoria

1. Acessar [opcao **020**](../operacional/020-manifesto-carga.md) no SSW
2. No campo **CARRETA PROVISORIA**, informar um nome descritivo:
   - Use um identificador unico (ex: `SP001`, `MG002`, `CARGA-MOTOCHEFE-15FEV`)
   - Pode ser qualquer nome — e apenas para identificar o agrupamento de CTRCs
3. Clicar para abrir a tela de carregamento

#### 1.2 Carregar CTRCs

4. No campo **CARREGAR CTRC**, digitar serie + numero + digito verificador **sem separador**
   - Zeros a esquerda sao desnecessarios
   - Tecla **`+`** mantem a serie e posiciona cursor no proximo numero
   - **Alternativa**: Clicar em **"VER APONTADOS"** para ver todos os CTRCs disponiveis e selecionar com mouse
   - **Alternativa 2**: Informar apenas a serie para carregar TODOS os CTRCs da serie
5. Repetir para cada CTRC da carga
6. Verificar **TOTAIS DESTE CARREGAMENTO**:
   - Quantidade de CTRCs
   - Peso total (kg)
   - Volume (m3)
   - Valor de mercadoria
   - Frete
7. Conferir se os totais estao corretos

**FILTROS disponiveis** (para localizar CTRCs):
- Serie
- Cidade destino
- Unidade destino
- Cliente remetente/destinatario
- Data de emissao

#### 1.3 Emitir o Manifesto

8. Clicar em **"EMITIR O MANIFESTO"**
9. Preencher dados do manifesto:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Placa da carreta** | Placa REAL definitiva | Deve estar cadastrada em [026](../relatorios/026-cadastro-veiculos.md) |
| **Conferente** | Numero do conferente | Somente se controle ativo em 903 |
| **Unidade destino** | Sigla da unidade (ex: CGR) | Deve estar cadastrada em [401](../cadastros/401-cadastro-unidades.md) |
| **Previsao de chegada** | Data/hora sugerida | Sugerida pela rota ([403](../cadastros/403-rotas.md)), pode alterar |
| **UFs de percurso** | UFs que o veiculo percorrera | Sugeridas pela rota ([403](../cadastros/403-rotas.md)), ajustar se necessario. UFs de origem e destino sao informadas mas NAO impressas no MDF-e |

10. Confirmar emissao
11. **Manifesto Operacional criado** — anotar o numero do manifesto

---

### PARTE 2 — Dar Saida e Emitir MDF-e (Opcao 025)

#### 2.1 Registrar Saida do Veiculo

12. Acessar [opcao **025**](../operacional/025-saida-veiculos.md)
13. Localizar o veiculo: informar placa do **cavalo** ou codigo de barras do **manifesto**
14. Sistema exibe todos os Manifestos carregados no veiculo
15. **IMPORTANTE**: Desmarcar manifestos que **NAO devem receber saida**
    - Manifestos desmarcados nao serao incluidos no MDF-e
    - MDF-e associado a manifesto desmarcado sera encerrado automaticamente
16. Confirmar dados exibidos:

| Dado | Verificar |
|------|-----------|
| Proprietario | Nome do proprietario do veiculo |
| TAC | Se transportador autonomo |
| CTRB/OS | Numero da contratacao ([opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) |
| Previsao de chegada | Data/hora prevista |
| UFs de percurso | Lista correta de UFs |

#### 2.2 Emitir MDF-e no SEFAZ

17. Clicar para confirmar saida
18. Sistema automaticamente:
    - Submete MDF-e ao SEFAZ — **um MDF-e por UF destino**
    - Encerra MDF-es anteriores se necessario
    - Dispara **SMP** (Solicitacao de Monitoramento Preventivo) automatico
    - Gera EDI de averbacao para seguradora (ESSOR via AT&M)

19. Verificar resultado:
    - **MDF-e Autorizado** → Prosseguir
    - **MDF-e Rejeitado** → Ver secao "Erros Comuns"

#### 2.3 Imprimir DAMDFE

20. Escolher tipo de DAMDFE para imprimir:

| Tipo | Quando usar |
|------|-------------|
| **DAMDFE Sintetico** | Muitos CT-es (>100). Nao lista CTRCs individuais |
| **DAMDFE sem valor de frete** | Padrao. Lista CTRCs sem mostrar fretes |
| **DAMDFE com valor de frete** | Quando motorista precisa saber fretes |

21. Imprimir e **entregar ao motorista**

> **ATENCAO**: Cada novo DAMDFE emitido substitui o anterior. Motorista deve carregar APENAS o DAMDFE mais recente.

#### 2.4 Impressoes adicionais (se necessario)

Na opcao 025, alem do DAMDFE, estao disponiveis:
- **Manifesto Operacional**: Documento interno SSW
- **DACTEs do Manifesto**: Todos os DACTEs dos CTRCs
- **DANFEs do Manifesto**: Todas as DANFEs dos CTRCs
- **Manifesto CB CT-e**: Chaves em codigo de barras (util para parceiros sem SSW)

---

### PARTE 3 — Apos o Embarque

#### 3.1 Chegada no Destino

22. Quando o veiculo chegar ao destino, o operador na unidade destino deve registrar a chegada:
    - [Opcao **030**](../operacional/030-chegada-de-veiculo.md) — Chegada de Veiculo
    - Capturar codigo de barras do Manifesto
    - Sistema **encerra MDF-e automaticamente** no SEFAZ

> **CarVia hoje**: Como as unidades destino sao parceiros (Tipo T), quem registra a chegada?
> **[DEFINIR]**: Verificar se a CarVia precisa registrar a chegada ou se o parceiro faz isso.
> **Alternativa**: Se o parceiro nao usa SSW, o Rafael pode registrar a chegada manualmente na opcao 030 quando receber confirmacao de entrega.

#### 3.2 Encerramento Automatico

- MDF-es sem chegada registrada aos **29 dias** sao encerrados automaticamente pelo SSW
- Isso evita rejeicoes no SEFAZ, mas NAO e a forma correta de encerrar
- **Sempre registrar a chegada ([030](../operacional/030-chegada-de-veiculo.md))** quando o veiculo chegar ao destino

---

## Regras do MDF-e

### Agrupamento por UF destino
- O SSW gera **um unico MDF-e por CNPJ emissor e UF destino**
- Varios Manifestos Operacionais podem resultar em um unico MDF-e
- Encerramentos e inclusoes sao feitos automaticamente

### Limite de CT-es
- SEFAZ aceita maximo de **2.048 Kb** no XML (cerca de 10.000 CT-es)
- Para muitos CT-es, usar DAMDFE Sintetico

### Cancelamento
- Somente ate **24 horas** apos emissao
- Somente se veiculo NAO passou por posto fiscal ou radar ANTT
- Opcao **024** para cancelar Manifesto e MDF-e
- **Se saida ja registrada (025)**: Cancelamento IMPEDIDO

### Duplicidade
- SEFAZ rejeita MDF-e se existir anterior com mesma origem, destino e placa sem chegada registrada (030)
- **Solucao**: Registrar chegada do MDF-e anterior ou cancelar (024)

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| MDF-e rejeitado: RNTRC invalido | RNTRC do proprietario expirado ou incorreto | Corrigir em [opcao 027](../operacional/027-relacao-proprietarios-veiculos.md) |
| MDF-e rejeitado: duplicado | MDF-e anterior com mesma origem/destino/placa sem chegada | Registrar chegada ([030](../operacional/030-chegada-de-veiculo.md)) ou cancelar anterior (024) |
| MDF-e rejeitado: certificado digital | Certificado A1 vencido ou nao configurado | Contatar Equipe SSW para renovar |
| SMP rejeitada | Telefone do motorista incorreto na [028](../operacional/028-relacao-motoristas.md) | Corrigir telefones do motorista |
| Manifesto sem CTRCs disponiveis | CTRCs nao estao na unidade ou ja manifestados | Verificar se CT-es estao autorizados e na unidade CAR |
| UFs de percurso incorretas | Rota ([403](../cadastros/403-rotas.md)) nao cadastrada ou incorreta | Cadastrar/corrigir rota na [opcao 403](../cadastros/403-rotas.md) |
| Vale Pedagio nao aparece | CTRB/OS ([072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) nao gerado | Fazer contratacao do veiculo ([072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) ANTES da saida |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Manifesto criado | Opcao 023 → pesquisar por numero → manifesto existe |
| CTRCs carregados | Opcao 023 → verificar lista de CTRCs no manifesto |
| MDF-e autorizado | Opcao 201 → verificar fila "AUTORIZADOS" → MDF-e presente |
| DAMDFE gerado | [Opcao 025](../operacional/025-saida-veiculos.md) → link "MDF-e" disponivel para impressao |
| SMP disparado | [Opcao 117](../comercial/117-monitoracao-embarcadores.md) → verificar se SMP foi enviado sem recusa |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-G01 | Sequencia legal — este POP e a etapa 6 |
| POP-C02 | Emitir CTe carga direta — pre-requisito |
| POP-D02 | Romaneio de entregas — pre-requisito |
| POP-D01 | Contratar veiculo — recomendado antes do manifesto |
| POP-D04 | Registrar chegada — encerramento do MDF-e |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
