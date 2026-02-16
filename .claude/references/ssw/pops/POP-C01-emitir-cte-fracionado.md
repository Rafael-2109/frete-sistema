# POP-C01 — Emitir CT-e para Frete Fracionado

> **Categoria**: C — Operacional: Emissao
> **Prioridade**: P1 (Alta — processo mais frequente)
> **Status anterior**: JA FAZ
> **Criado em**: 2026-02-15
> **Executor atual**: Rafael
> **Executor futuro**: Rafael / Jaqueline

---

## Objetivo

Emitir CT-e (Conhecimento de Transporte Eletronico) para fretes fracionados — modalidade onde a CarVia subcontrata uma transportadora parceira que faz a coleta e entrega. O CT-e e o documento fiscal que autoriza o transporte e e a base para o faturamento ao cliente.

---

## Trigger

- Frete fracionado aprovado pelo cliente
- NF-e do cliente disponivel (chave de 44 digitos)
- Transportadora parceira definida (ja cadastrada como unidade T no SSW)

---

## Frequencia

Diario — processo mais frequente da operacao CarVia (59% dos fretes).

---

## Pre-requisitos

| Requisito | Opcao SSW | Status CarVia |
|-----------|-----------|---------------|
| Cliente cadastrado | [483](../cadastros/483-cadastro-clientes.md) | Verificar se ja existe |
| Tabela de frete cadastrada | 420 (por rota) | Deve existir para rota |
| NF-e do cliente | Recebida pelo cliente | Chave de 44 digitos |
| Unidade destino cadastrada | 401 (Tipo T) | Parceiro deve existir |
| Cidades atendidas | [402](../cadastros/402-cidades-atendidas.md) | Destino da NF deve estar vinculado |
| Custos parceiro | [408](../comercial/408-comissao-unidades.md) | Tabela do parceiro cadastrada |

---

## Passo-a-Passo

### ETAPA 1 — Preparacao

1. Verificar se o cliente esta cadastrado ([opcao 483](../cadastros/483-cadastro-clientes.md))
   - **Se novo**: Cadastrar via POP-A01
2. Verificar se a rota esta implantada
   - **Se nova**: Implantar via POP-A10
3. Ter em maos: chave da NF-e (44 digitos), peso, quantidade de volumes, valor da mercadoria

---

### ETAPA 2 — Alterar Unidade para CAR

4. No SSW, verificar que a unidade ativa e **CAR** (nao MTZ)
   - A emissao do CT-e deve ser feita na unidade operacional CAR
   - Se estiver em MTZ ou outra unidade, trocar para CAR

---

### ETAPA 3 — Emitir Pre-CTRC (Opcao 004)

5. Acessar [opcao **004**](../operacional/004-emissao-ctrcs.md)
6. Preencher dados basicos:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Tipo documento** | CT-e Normal (N) | Padrao para frete fracionado |
| **CNPJ Remetente** | CNPJ de quem envia a mercadoria | Cliente ou embarcador |
| **CNPJ Destinatario** | CNPJ de quem recebe | Destinatario final |
| **CNPJ Pagador** | (deixar default) | Remetente se CIF, Destinatario se FOB |
| **Placa de coleta** | **ARMAZEM** | ← Especifico para fracionado. NAO usar placa real |
| **Tipo de frete** | CIF ou FOB | Conforme negociado com cliente |

> **ATENCAO**: Para frete fracionado, a placa de coleta DEVE ser **ARMAZEM** (ou **ARMA999**). Isso indica que a mercadoria foi trazida pelo cliente ao armazem, sem coleta dedicada. Para carga direta, usar placa real (ver POP-C02).

7. Preencher dados da NF-e:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Chave NF-e** | 44 digitos | Copiar e colar — verificar todos os digitos |
| **Nota Fiscal** | Numero da NF-e | 9 digitos |
| **Serie** | Serie da NF-e | Se houver |
| **Data emissao** | Data de emissao da NF-e | |
| **Peso (Kg)** | Peso total da carga | |
| **Qtd Volumes** | Quantidade de volumes | |
| **Valor mercadoria** | Valor total | |

8. Clicar em **SIMULAR**

---

### ETAPA 4 — Verificar Simulacao

9. Analisar resultado da simulacao:

| Componente | O que verificar |
|------------|-----------------|
| **Frete Peso** | Valor calculado vs esperado |
| **Despacho** | Taxa fixa (se aplicavel) |
| **Pedagio** | Valor de pedagio |
| **GRIS** | Gerenciamento de risco (percentual sobre valor mercadoria) |
| **TDE/TDC/TAR/TRT/TDA** | Taxas adicionais (se aplicaveis) |
| **ICMS** | Calculado automaticamente |
| **Valor total do frete** | Conferir com cotacao aprovada pelo cliente |

**Se valor estiver DIFERENTE do esperado**:
- Verificar tabela de frete (opcao 420) — preco correto por rota?
- Verificar parametros ([opcao 062](../comercial/062-parametros-frete.md)) — componentes extras?
- Verificar se a cidade do destinatario esta no polo correto (P/R/I)
- Se necessario, informar frete manualmente (campo "Frete Informado")

**Se valor estiver CORRETO**: Prosseguir

---

### ETAPA 5 — Gravar Pre-CTRC

10. Clicar no botao **Play** (gravar)
11. Sistema pergunta: **"Confirma a emissao?"** → Clicar **Sim**
12. Sistema pergunta: **"Deseja enviar email ao pagador?"** → Clicar **NAO**
    - A CarVia nao envia email de CT-e ao cliente neste momento
13. **Pre-CTRC criado** — anotar o numero

> **IMPORTANTE**: O Pre-CTRC ainda NAO tem valor fiscal. Ele so se torna valido apos autorizacao pelo SEFAZ (etapa 6).

**Se precisar ALTERAR o Pre-CTRC**:
- Acessar [opcao 004](../operacional/004-emissao-ctrcs.md) → link "Alterar" no rodape
- Informar numero do CTRC
- Modificar dados → Gravar

**Se precisar CANCELAR o Pre-CTRC**:
- Acessar [opcao 004](../operacional/004-emissao-ctrcs.md) → link "Cancelar" no rodape
- Informar numero do CTRC → Confirmar

---

### ETAPA 6 — Enviar CT-e ao SEFAZ (Opcao 007)

14. Acessar [opcao **007**](../operacional/007-emissao-cte-complementar.md)
15. Verificar: **"QUANTIDADE DE CTRCS A SEREM IMPRESSOS"** — deve mostrar pelo menos 1
16. Configurar filtros (opcional):
    - Tipo de frete: CIF ou FOB
    - UFs de destino: se quiser filtrar
17. Clicar em **"DIGITADOS POR MIM"**
    - Sistema exibe CT-es pendentes de envio
18. Clicar em **"Enviar CT-es ao SEFAZ"**
19. Aguardar autorizacao:
    - **Autorizado**: CT-e recebe numero definitivo e protocolo SEFAZ
    - **Rejeitado**: Verificar motivo. Causas comuns:
      - Chave NF-e invalida ou ja utilizada
      - CNPJ remetente/destinatario com problemas na Receita
      - Certificado digital vencido
20. **CT-e autorizado** — averbacao e feita automaticamente pela AT&M

> **Modo automatico (903=A/S)**: Se configurado, o SSW envia pre-CT-es automaticamente a cada 1 minuto. Nesse caso, a etapa 6 se resume a verificar se o CT-e foi autorizado.

---

### ETAPA 7 — Imprimir CT-e (se necessario)

21. Na [opcao **007**](../operacional/007-emissao-cte-complementar.md), apos autorizacao:
    - Se necessario imprimir DACTE (documento fisico): usar funcao de impressao
    - Se operacao sem papel: CT-e digital ja esta disponivel no sistema
22. Grampear CT-e com NF-e (se impresso) e colocar no escaninho da filial destino

---

### ETAPA 8 — Proximo Passo

Para **frete fracionado**, apos o CT-e autorizado:
- **NAO** e necessario criar romaneio, manifesto ou MDF-e (a transportadora parceira cuida disso)
- Proximo passo: **Faturamento** (POP-E02) — quando houver CTRCs suficientes para gerar fatura

---

## Diferenca entre Fracionado e Carga Direta

| Aspecto | Fracionado (POP-C01) | Carga Direta (POP-C02) |
|---------|---------------------|----------------------|
| Placa de coleta | **ARMAZEM** | Placa REAL do veiculo |
| Transportadora | Parceiro faz coleta/entrega | CarVia ou agregado |
| Apos CT-e | Vai para faturamento | Romaneio → MDF-e → Embarque |
| MDF-e | NAO necessario (parceiro faz) | Obrigatorio (interestadual) |
| Contratacao (072) | NAO necessario | Obrigatorio |
| POP-G01 | NAO se aplica | SE APLICA (sequencia legal) |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Simulacao nao calcula frete | Tabela de frete nao encontrada | Verificar 420 (rota), [402](../cadastros/402-cidades-atendidas.md) (cidade vinculada) |
| Valor do frete diverge da cotacao | Polo errado (P/R/I) ou tabela desatualizada | Verificar [402](../cadastros/402-cidades-atendidas.md) (polo da cidade) e 420 (valores) |
| SEFAZ rejeita: chave NF-e invalida | Chave NF-e digitada errada | Conferir todos os 44 digitos |
| SEFAZ rejeita: duplicidade | CT-e ja emitido para esta NF-e | Verificar se ja existe CT-e ([opcao 101](../comercial/101-resultado-ctrc.md)) |
| SEFAZ rejeita: certificado digital | Certificado A1 vencido | Contatar Equipe SSW |
| CT-e com valor R$ 0,00 | Nenhuma tabela encontrada e frete nao informado | Informar frete manualmente ou corrigir tabelas |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Unidade ativa = CAR | Menu principal → unidade selecionada |
| Pre-CTRC criado | [Opcao 004](../operacional/004-emissao-ctrcs.md) → "Relacionar CTRCs nao impressos" → CTRC na lista |
| CT-e autorizado | [Opcao 007](../operacional/007-emissao-cte-complementar.md) → fila "Autorizados" → CT-e presente |
| Averbacao realizada | [Opcao 101](../comercial/101-resultado-ctrc.md) → pesquisar CT-e → resumo averbacao (protocolo, data) |
| Cliente cadastrado | [Opcao 483](../cadastros/483-cadastro-clientes.md) → pesquisar CNPJ → dados preenchidos |
| Tabela de frete existe | Opcao 420 → pesquisar rota → tabela encontrada |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A01 | Cadastrar cliente — se cliente novo |
| POP-A10 | Implantar nova rota — se rota nova |
| POP-C02 | Emitir CTe carga direta — variante para carga direta |
| POP-E01 | Pre-faturamento — verificar CTRCs disponiveis |
| POP-E02 | Faturar — proximo passo |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
