# 01 — Implantacao do SSW

> **Fonte**: `visao_geral_implantacao.htm` (18/10/2025)
> **Links internos**: 106 | **Imagens**: 2

## Sumario

Roteiro padrao para implantar o SSW numa transportadora. O SSW e especifico para transportadoras, entao a implantacao segue um fluxo pre-definido.

---

## 1. Providencias Iniciais

| Acao | Opcao | Detalhes |
|------|-------|---------|
| Cadastro de usuarios | [925](../cadastros/925-cadastro-usuarios.md) | 3 usuarios Master cadastrados pelo Suporte SSW |
| Grupos de usuarios | [918](../cadastros/918-cadastro-grupos.md) | Define cargo/funcao (autoridades e acessos) |
| Configurar micro | Link no rodape do Menu | Cada estacao deve ser configurada |
| Suporte SSW | Chat, telefone, email | `suporte@ssw.inf.br`, `implantacao@ssw.inf.br` |

---

## 2. Implantacao Basica

### Cadastros obrigatorios (ordem sugerida)

| Passo | Opcao | O que fazer |
|-------|-------|-------------|
| 1 | [401](../cadastros/401-cadastro-unidades.md) | Cadastrar TODAS as unidades (matriz, filiais, parceiros) — atencao dados fiscais |
| 2 | [402](../cadastros/402-cidades-atendidas.md) | Vincular cidades atendidas as unidades (desnecessario para carga completa) |
| 3 | [403](../cadastros/403-rotas.md) | Cadastrar rotas (distancia, prazo entre unidades) — desnecessario para carga completa |
| 4 | [904](../cadastros/904-bancos-contas-bancarias.md) | Cadastrar contas bancarias. Bloquetos devem estar homologados pelo banco |
| 5 | [903](../cadastros/903-parametros-gerais.md) | Definir parametros gerais (usuario master) |
| 6 | [483](../cadastros/483-cadastro-clientes.md) | Cadastrar clientes pagadores com tabela de frete. Demais sao auto-cadastrados |
| 7 | [417](../comercial/417-418-420-tabelas-frete.md)/[418](../comercial/417-418-420-tabelas-frete.md)/[420](../comercial/417-418-420-tabelas-frete.md) | Cadastrar tabelas de frete — **parte mais trabalhosa** da implantacao |
| 8 | [406](../cadastros/406-tipos-mercadorias.md)/407 | Tipos e especies de mercadorias (quanto menos codigos, melhor) |
| 9 | [026](../relatorios/026-cadastro-veiculos.md)/[028](../operacional/028-relacao-motoristas.md) | Cadastrar veiculos e motoristas (frota + terceiros) |
| 10 | [405](../cadastros/405-tabela-ocorrencias.md) | Ajustar tabela de ocorrencias |

### Treinamento
- Normalmente num sabado, semanas antes da operacao
- 1:30h de duracao (disponivel em video)
- Objetivo: tirar medo do usuario, ensinar o basico

### Apos treinamento
- Validar tabelas de frete (emitir CTRCs em paralelo ao sistema anterior)
- Testar EDIs (inclusive averbacao)
- Conferir tributacao ICMS (opção 410) e ISS ([opção 402](../cadastros/402-cidades-atendidas.md))

### Operacao definitiva
- Certificado digital A1 instalado ([opção 903](../cadastros/903-parametros-gerais.md)/Certificado Digital)
- CNPJ credenciado no SEFAZ da UF
- CT-es e MDF-es configurados pela Equipe SSW
- Limpeza da base e colocacao em operacao pela Equipe SSW

---

## 3. SSWBar (Codigo de Barras)

**Funcao**: Identificacao, carregamento e descarregamento de volumes.

### Infraestrutura por estacao
| Item | Preco aprox. |
|------|-------------|
| Carrinho de oficina | R$ 200 |
| Notebook basico (SSD, Windows) | R$ 1.200 |
| Leitor laser | R$ 150 |
| Impressora codigo de barras | R$ 1.200+ |

### Operacao SSWBar
1. **Coleta**: volumes amarrados a DANFE via etiquetas sequenciais
2. **Identificacao**: grudagem de etiquetas na descarga (entrada no armazem)
3. **Entrada**: descargas de coletas/transferencias (opção 022, opção 264)
4. **Saida**: carregamentos de transferencia ([opção 020](../operacional/020-manifesto-carga.md)) e entrega ([opção 035](../operacional/035-romaneio-entregas.md))

---

## 4. SSWMobile (App Motorista)

**Funcao**: Rastreamento em tempo real da coleta ate entrega.

### Configuracoes
- Setores de coleta/entrega ([opção 404](../cadastros/404-setores-coleta-entrega.md)) com faixas de CEP
- Setores do veiculo ([opção 013](../operacional/013-veiculo-sugerido-setor.md))

### Operacao
- **Coletas**: integra com [opção 003](../operacional/003-ordem-coleta-gerenciamento.md), atualiza em tempo real
- **Transferencias**: localizacao a cada 5-10 min ([opção 101](../comercial/101-resultado-ctrc.md))
- **Entregas**: integra com [opção 038](../operacional/038-baixa-entregas-ocorrencias.md), ocorrencias em tempo real
- **Conferente**: funcoes adicionais ([opção 925](../cadastros/925-cadastro-usuarios.md)/Habilitar SSWMobile)

---

## 5. SSWScan (Escaneamento)

**Funcao**: Digitalizar comprovantes de entrega + baixa automatica.

- Instalar SSWScan 2 ([opção 398](../comercial/398-escanear-comprovantes-entregas.md))
- Qualquer escaner funciona (multifuncional ou dedicado)
- [Opção 903](../cadastros/903-parametros-gerais.md)/Operacao pode configurar baixa automatica pelo scan

---

## 6. Parcerias com Outras Transportadoras

### 3 modos de operacao

| Modo | Descricao | Integracao |
|------|-----------|-----------|
| 1 | Parceiro usa SSW da contratante (como filial) | Automatica |
| 2 | Parceiro usa seu proprio SSW | Automatica online |
| 3 | Parceiro usa outro sistema | Troca de arquivos EDI |

### Configuracoes
- Unidade parceira ([opção 401](../cadastros/401-cadastro-unidades.md)) + cidades ([opção 402](../cadastros/402-cidades-atendidas.md)) + rotas ([opção 403](../cadastros/403-rotas.md))
- Transportadora subcontratada ([opção 478](../financeiro/478-cadastro-fornecedores.md)) + tabela comissionamento ([opção 408](../comercial/408-comissao-unidades.md))
- Agendamento calculo comissao ([opção 903](../cadastros/903-parametros-gerais.md)/Agendar processamento)

### Comissionamento
- **Modo 1**: MAPA na [opção 056](../relatorios/056-informacoes-gerenciais.md) (processamento agendado)
- **Modo 2**: Capas de comprovantes (opção 040) faturadas ([opção 436](../financeiro/436-faturamento-geral.md))
- **Modo 3**: Faturas recebidas conferidas (opção 607)
- Todos creditam CCF ([opção 486](../financeiro/486-conta-corrente-fornecedor.md))

---

## 7. Remuneracao de Veiculos de Coleta/Entrega

- Setorizar unidade ([opção 404](../cadastros/404-setores-coleta-entrega.md))
- Tabelas de remuneracao por unidade ([opção 409](../comercial/409-remuneracao-veiculos.md))
- CIOT para TAC ([opção 903](../cadastros/903-parametros-gerais.md)/PEF) — e-Frete recomendado
- Demonstrativo (opção 076) → OS (opção 075) → CCF ([opção 486](../financeiro/486-conta-corrente-fornecedor.md)) → Contas a Pagar ([opção 475](../financeiro/475-contas-a-pagar.md))

---

## 8. Remuneracao de Veiculos de Transferencia

- Tabelas por rota (opção 399) ou por veiculo ([opção 499](../comercial/499-replicar-config-ctrb-transferencia-veiculo.md))
- Contratacao ([opção 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) apos Manifesto ([opção 020](../operacional/020-manifesto-carga.md))
- OS para agregado, CTRB para carreteiro
- CCF ([opção 486](../financeiro/486-conta-corrente-fornecedor.md)) → Contas a Pagar ([opção 475](../financeiro/475-contas-a-pagar.md))

---

## Arvore de Navegacao

```
Implantacao
├── Providencias Iniciais
│   ├── opção 925 (usuarios)
│   └── opção 918 (grupos)
├── Implantacao Basica
│   ├── opção 401 (unidades)
│   ├── opção 402 (cidades)
│   ├── opção 403 (rotas)
│   ├── opção 904 (bancos)
│   ├── opção 903 (parametros)
│   ├── opção 483 (clientes)
│   ├── opção 417/418/420 (tabelas frete)
│   ├── opção 406/407 (mercadorias)
│   ├── opção 026/028 (veiculos/motoristas)
│   └── opção 405 (ocorrencias)
├── SSWBar → opção 011, 022, 264, 020, 035
├── SSWMobile → opção 003, 013, 038, 404
├── SSWScan → opção 398
├── Parcerias → opção 401, 478, 408, 607, 486
├── Remuneracao Coleta/Entrega → opção 409, 076, 075, 486
└── Remuneracao Transferencia → opção 399, 499, 072, 486
```

---

## Contexto CarVia

### Opcoes que CarVia usa

| Opcao | POP | Status | Quem Faz |
|-------|-----|--------|----------|
| [483](../cadastros/483-cadastro-clientes.md) | A01 | ATIVO | Rafael |
| [384](../financeiro/384-cadastro-clientes.md) | A01 | ATIVO | Rafael |
| [401](../cadastros/401-cadastro-unidades.md) | A02 | ATIVO | Rafael |
| [402](../cadastros/402-cidades-atendidas.md) | A03 | ATIVO | Rafael |
| [403](../cadastros/403-rotas.md) | A04 | ATIVO | Rafael |
| [478](../financeiro/478-cadastro-fornecedores.md) | A05 | ATIVO | Rafael |
| [408](../comercial/408-comissao-unidades.md) | A06 | ATIVO | Rafael |
| [420](../comercial/417-418-420-tabelas-frete.md) | A07 | ATIVO | Rafael |
| [026](../relatorios/026-cadastro-veiculos.md) | A08 | PARCIAL | Rafael |
| [028](../operacional/028-relacao-motoristas.md) | A09 | PARCIAL | Rafael |

> **A10** (Implantar nova rota completa) e ATIVO — Rafael executa o fluxo 401→402→403→478→408→420 de ponta a ponta.

### Opcoes que CarVia NAO usa (mas deveria)

Todos os cadastros basicos estao ativos ou parciais. Nao ha lacunas criticas neste modulo.

| Opcao | POP | Pendencia |
|-------|-----|-----------|
| [026](../relatorios/026-cadastro-veiculos.md) | A08 | Cadastro incompleto — falta RNTRC de alguns veiculos |
| [028](../operacional/028-relacao-motoristas.md) | A09 | Cadastro sob demanda, sem processo formal |

### Responsaveis

- **Atual**: Rafael (todos os cadastros)
- **Futuro**: Rafael (sem plano de transicao — cadastros basicos sao estrategicos)
