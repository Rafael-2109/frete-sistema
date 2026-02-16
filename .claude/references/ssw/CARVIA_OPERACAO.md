# CarVia Logistica — Operacao e Processos

> **Criado em**: 2026-02-15
> **Fonte**: Rafael Nascimento (idealizador e operador)
> **Objetivo**: Base de conhecimento para mapear processos CarVia ↔ SSW e criar POPs

---

## 1. Perfil da Empresa

| Item | Detalhe |
|------|---------|
| **Razao Social** | CARVIA LOGISTICA E TRANSPORTE LTDA |
| **Dominio SSW** | CV1 |
| **Sigla SSW** | CAR (unidade), CARP (CarVia Polo), MTZ (Matriz) |
| **Base fisica** | Santana de Parnaiba/SP — dentro do CD da Nacom Goya |
| **Inicio** | Agosto/2025 (criacao), Janeiro/2026 (operacao efetiva) |
| **Seguradora** | ESSOR Seguros |
| **Averbacao** | Automatica via AT&M (averba.com.br) — integrada ao SSW |
| **Contabilidade** | Externa — extrai relatorios do SSW (experiencia com 100+ transportadoras SSW) |

### Origem

A CarVia nasceu do setor logistico da **Nacom Goya**, industria de alimentos lider no setor com 30+ anos de experiencia em distribuicao para o Brasil inteiro. Ao operar como **cliente** de transportadoras por decadas, a equipe acumulou conhecimento profundo sobre:
- Quais transportadoras sao boas por regiao
- Quais parceiros retornam informacoes reais de rastreamento
- As particularidades de cada estado e tipo de cliente
- Os "macetes" para conseguir entregar no prazo

Viram que outras empresas sofriam para encontrar transportadoras de qualidade e decidiram **abrir uma transportadora** usando sua rede de parceiros, subcontratando-os e oferecendo servico de qualidade.

### Diferencial competitivo

- **Nasceu do lado do cliente** — sabe exatamente onde uma transportadora falha
- Rede de parceiros em **todos os estados**
- Conhecimento das particularidades de cada estado e tipo de cliente
- Expertise em agendamento de entregas
- Filosofia: resolver problemas internamente, nunca transferir ao cliente

---

## 2. Equipe

5 pessoas compartilhadas com outras empresas do grupo Nacom:

| Pessoa | Funcao CarVia | Funcao Grupo | SSW hoje | SSW futuro |
|--------|---------------|--------------|----------|------------|
| **Rafael** | Tudo (cadastros, CTe, faturamento, analise) | Logistica Nacom + criador CarVia | Unico usuario | Supervisao |
| **Jessica** | Comercial — prospecta, recebe demandas, envia cotacoes, monitora entregas | Prospecta transportadoras Nacom | Nao usa | Cotacao, acompanhamento |
| **Jaqueline** | Financeiro — faturas, pagamentos | Financeiro do grupo (exceto Nacom) | Nao usa | Faturamento, contas a pagar, conciliacao |
| **Stephanie** | Monitoramento de entregas | Monitoramento entregas Nacom | Nao usa | Rastreamento, ocorrencias |
| **Talita** | Auditoria de faturas | Auditoria Nacom | Nao usa | Auditoria CTe vs faturas transportadoras |

> **Observacao**: Equipe financeira Nacom e chefiada pelo Marcus. As mesmas pessoas atendem todo o grupo exceto a Nacom (que tem equipe propria pelo tamanho da operacao).

---

## 3. Clientes

| # | Cliente | Segmento | Tipo de carga | Peso tipico | Destino tipico |
|---|---------|----------|---------------|-------------|----------------|
| 1-4 | **MotoChefe** (4 empresas) | Motos eletricas | Motos desmontadas em caixas (~140x40x60cm, ~60kg) | Leve | Revendedores, lojas, consumidor final |
| 5 | **NotCo** | Leite vegetal (Tetrapak) | Paletes | 1.000-2.000 kg | Supermercados, distribuidores, atacados |
| 6 | **Cliente FOB Nacom** | Alimentos | Variado | Variado | Variado |

### Numeros atuais (1 mes de operacao)

| Metrica | Valor |
|---------|-------|
| Fretes realizados | 17 |
| Faturamento total | R$ 30.000 |
| Fracionados | 10 (59%) |
| Diretas | 7 (41%) |
| — Caminhao proprio | 4 |
| — Agregado | 2 |
| — Transportadora | 1 |

---

## 4. Servicos e Modalidades

### 4.1 Frete Fracionado

**Como funciona**: CarVia subcontrata transportadoras especializadas que ja trabalham com a Nacom Goya, usando as mesmas condicoes comerciais.

- Transportadora parceira faz a coleta e entrega
- CarVia emite CT-e, fatura e cobra do cliente
- CarVia paga a transportadora parceira (conta a pagar)
- **Margem**: diferenca entre preco CarVia (tabela 420) e custo parceiro (tabela 408)

### 4.2 Frete Dedicado

Tres sub-modalidades:

| Modalidade | Frota | Capacidade |
|------------|-------|------------|
| **Proprio** | VUC + Truck | 3.500 kg / 14.000 kg |
| **Agregado** | 100+ motoristas cadastrados | Fiorino (600kg) ate Truck (14.000kg) |
| **Transportadora parceira** | 20+ empresas | Truck e carretas bau/sider (ate 33.000kg) |

**Tipos de carreta**:
- **Bau** — porta traseira, carreta de aluminio
- **Sider** — laterais em lona, possivel abrir toda a lateral

### 4.3 Coleta

- Cobra taxa de coleta
- Procura casar com frete retorno de entregas da Nacom para otimizar custo
- Se carga esta no CD (Santana de Parnaiba): aguarda transportadora coletar

---

## 5. Fluxo Operacional Atual

### 5.1 Fluxo Completo (como funciona HOJE)

```
DEMANDA
  Jessica recebe solicitacao de frete do cliente
  ↓
COTACAO
  Jessica solicita cotacao ao Rafael
  ↓
  Rafael analisa no SISTEMA FRETES (app Nacom) → identifica melhor opcao
  ↓
  Operacao ja prevista no SSW?
  ├─ SIM → Cota no SSW (opcao 002) → retorna preco
  └─ NAO → IMPLANTACAO DE NOVA ROTA (ver 5.2)
  ↓
  Rafael retorna cotacao para Jessica
  Jessica envia cotacao ao cliente
  ↓
APROVACAO
  Cliente aprova → Jessica pede NF ao cliente
  Jessica contacta transportadora para agendar coleta
  ↓
CADASTROS
  Rafael cadastra cliente no SSW (483) se novo
  ↓
COLETA
  Carga no CD? → Aguarda transportadora coletar
  Carga fora? → Casa com retorno de entrega Nacom
  ↓
EMISSAO
  Rafael altera unidade para CAR no SSW
  Opcao 004: Normal (N), placa "ARMAZEM" (fracionado) ou placa real (direto)
  Digita chave NF → Simular frete → Ajusta se necessario → Gravar
  Confirma → Nao envia email ao pagador
  Envia CT-e ao SEFAZ
  Opcao 007: imprime CTes
  ↓
FRACIONADO                          DIRETO
  Altera unidade para MTZ            Gerenciadora de risco (fora SSW)
  Fatura na opcao 437                Cadastra motorista, veiculo
  Envia fatura para Jessica           Romaneio (035)
  Jessica envia ao cliente            Manifesto (??? — nunca fizeram)
  ↓                                  ↓
RECEBIMENTO                        RECEBIMENTO
  Cliente deposita na conta           Cliente deposita na conta
  (sem boleto, sem cobranca           (sem boleto, sem cobranca
   bancaria)                           bancaria)
```

### 5.2 Implantacao de Nova Rota (processo detalhado)

Quando uma cidade/regiao nao esta cadastrada no SSW:

```
1. IDENTIFICAR PARCEIRO
   No Sistema Fretes: qual transportadora melhor atende essa regiao para a Nacom?
   ↓
2. CRIAR UNIDADE (opcao 401)
   Tipo: T (Terceiro)
   Sigla: codigo IATA da cidade (ex: CGR = Campo Grande)
   Nome: Transportadora - Cidade/UF (ex: Alemar - Campo Grande/MS)
   Endereco: da transportadora na cidade
   Dados seguro: ESSOR
   Conta bancaria: da CarVia
   Dados fiscais: CNPJ da CarVia
   ↓
3. EXTRAIR TABELA DO SISTEMA FRETES
   Tabela da transportadora parceira com precos por polo
   ↓
4. CRIAR TABELAS CARVIA (padronizacao)
   Para cada unidade: 3 tabelas com polos P/R/I
   Ex: CARP-CGRP (CarVia Polo → Campo Grande Polo)
       CARP-CGRR (CarVia Polo → Campo Grande Regiao)
       CARP-CGRI (CarVia Polo → Campo Grande Interior)
   ↓
5. EXTRAIR VINCULOS DO SISTEMA FRETES
   Cidades atendidas por polo + lead times
   ↓
6. CADASTRAR CIDADES (opcao 402)
   Todas as cidades que a transportadora atende pela filial
   Com polos (P/R/I) e lead times padronizados
   ↓
7. CADASTRAR FORNECEDOR (opcao 478)
   Transportadora parceira como fornecedor
   ↓
8. CADASTRAR CUSTOS (opcao 408)
   Custo de subcontratacao = tabela do Sistema Fretes
   ↓
9. CADASTRAR ROTA (opcao 403)
   Ex: CAR → CGR
   ↓
10. CADASTRAR TABELAS DE PRECO (opcao 420)
    3 tabelas por rota: CARP-CGRP, CARP-CGRR, CARP-CGRI
```

> **Ponto importante**: O Sistema Fretes (app Nacom) e a **fonte de verdade** para precos de transportadoras. O SSW recebe uma versao "CarVia" dessas tabelas (com margem). A opcao 408 no SSW e espelho do Sistema Fretes.

---

## 6. Infraestrutura SSW

### Opcoes SSW utilizadas HOJE

| Opcao | Nome | Uso |
|-------|------|-----|
| 002 | Cotacao | Cotar fretes para clientes |
| 004 | Emissao CTRC | Emitir CTe individual |
| 007 | Envio CTe SEFAZ | Enviar e imprimir CTes |
| 035 | Romaneio | Criar romaneio (carga direta, pouca pratica) |
| 401 | Cadastro Unidades | Criar unidades terceiro (parceiros) |
| 402 | Cidades Atendidas | Cadastrar cidades com polos e lead times |
| 403 | Rotas | Cadastrar rotas CAR → destino |
| 408 | Custos/Comissoes | Cadastrar custo de subcontratacao |
| 420 | Tabelas por Rota | Cadastrar tabelas de preco CarVia |
| 437 | Faturamento Manual | Emitir faturas |
| 478 | Cadastro Fornecedor | Cadastrar transportadoras parceiras |
| 483 | Cadastro Clientes | Cadastrar clientes |

### Estrutura de unidades no SSW

| Sigla | Tipo | Descricao |
|-------|------|-----------|
| MTZ | Matriz | Matriz da CarVia |
| CAR | Filial | Unidade operacional CarVia (Santana de Parnaiba) |
| CARP | — | Usado nas tabelas (CarVia Polo) |
| CGR | Terceiro | Alemar - Campo Grande/MS (exemplo) |
| ... | Terceiro | Demais parceiros por cidade |

### Estrategia de siglas

- **Cada parceiro/filial = uma unidade T no SSW** com sigla IATA da cidade
- **3 tabelas por unidade**: Polo (P), Regiao (R), Interior (I)
- **Nomenclatura tabelas**: CARP-[SIGLA][POLO] (ex: CARP-CGRP)

---

## 7. Gaps e Necessidades (priorizado por Rafael)

### 7.1 FINANCEIRO — Prioridade ALTA

**Situacao atual**: So emite fatura (437). Sem boleto, sem cobranca bancaria, sem contas a pagar no SSW, conciliacao manual.

| Necessidade | Status | Opcoes SSW relacionadas |
|-------------|--------|------------------------|
| Conciliacao pagamentos vs recebimentos | Manual (Rafael calcula) | 569, 458 |
| Analise de resultados por CTRC | Nao faz | 101, 056 |
| Cadastro e validacao de custos | Parcial (408) | 408, 072, 486 |
| Contas a pagar (transportadoras subcontratadas) | Nao faz no SSW | 475, 486, 476 |
| Cobranca bancaria (boleto) | Nao faz | 444 |
| Integracao com transportadoras SSW (contas a pagar) | Sabe que existe, nao sabe como | EDI/parceiros |

### 7.2 COMERCIAL — Prioridade MEDIA-ALTA

**Situacao atual**: Tabelas cadastradas (420/408), cotacao funciona (002). Mas nao entende como o "preco de venda" e formado na simulacao.

| Necessidade | Status | Opcoes SSW relacionadas |
|-------------|--------|------------------------|
| Entender formacao de preco na simulacao | Nao entende todos os custos | 062, 004 (simular) |
| Garantir que comissoes (408) = Sistema Fretes | Valida manualmente | 408 |
| Entender custos extras na composicao | Nao sabe quais custos existem | 062, 903 |

### 7.3 EMISSOES — Prioridade ALTA

**Situacao atual**: Emite CTe normal (004/007). Nao sabe emitir CT-e complementar, manifesto, nem cadastrar custos extras.

| Necessidade | Status | Opcoes SSW relacionadas |
|-------------|--------|------------------------|
| CT-e complementar | Nunca emitiu, nao sabe como | 007 (complementar) |
| Custos extras (TDE, diaria, pernoite) | Nao sabe onde cadastrar | 459, 462 |
| Manifesto (MDF-e) | **Nunca fez, nao sabe como** | 020, 025 |
| Romaneio | Sabe o que e, pouca pratica | 035 |
| Simulacao de frete (004) | Frequentemente nao calcula certo | 004, 062 |

### 7.4 CONTROLE OPERACIONAL — Prioridade MEDIA

| Necessidade | Status | Opcoes SSW relacionadas |
|-------------|--------|------------------------|
| Comprovante de entrega | Nao controla | 040, 049, 428 |
| Contratacao formal de veiculo | Nao sabe o que e | 072 |
| Ocorrencias de entrega | Nao registra | 033, 038, 108 |
| Rastreamento de cargas | Jessica faz informalmente | 057 |

### 7.5 FISCAL — Prioridade BAIXA

**Situacao atual**: Contabilidade externa cuida, extrai relatorios do SSW. SSW atualiza regras tributarias automaticamente.

| Necessidade | Status | Opcoes SSW relacionadas |
|-------------|--------|------------------------|
| Extrair relatorios fiscais | Contabilidade faz | 512, 515, 567 |
| Entender se necessario | Baixa urgencia | — |

### 7.6 FROTA — Prioridade BAIXA

**Situacao atual**: 2 caminhoes proprios, sem controle de custos no SSW.

| Necessidade | Status | Opcoes SSW relacionadas |
|-------------|--------|------------------------|
| Controle de custos (combustivel, manutencao) | Nao faz | 026, 320, 131, 314 |
| Cadastro veiculos/motoristas | Parcial | 026, 028 |

### 7.7 QUESTOES LEGAIS — Prioridade ALTA

| Necessidade | Status | Risco |
|-------------|--------|-------|
| Regras da seguradora (CT-e antes do embarque) | Segue por intuicao | Sinistro sem cobertura |
| Operacoes permitidas (NF de outro UF) | Nao sabe se pode | Fiscal/tributario |
| Averbacao obrigatoria | Automatica via AT&M | Baixo (sistema cuida) |
| Regras da gerenciadora de risco | Segue parcialmente | Seguro |

> **Risco critico**: Rafael opera por intuicao nas regras legais/seguro. Um sinistro sem CT-e emitido antes do embarque pode nao ter cobertura.

---

## 8. Mapa: Processo CarVia → Opcao SSW → Documentacao

| Processo CarVia | Opcoes SSW | Doc SSW | Status CarVia |
|-----------------|------------|---------|---------------|
| Cotar frete | 002 | comercial/002-cotacao-de-frete.md | Usa |
| Cadastrar unidade parceira | 401 | cadastros/401-cadastro-unidades.md | Usa |
| Cadastrar cidades | 402 | cadastros/402-cidades-atendidas.md | Usa |
| Cadastrar rotas | 403 | cadastros/403-rotas.md | Usa |
| Cadastrar custos parceiro | 408 | comercial/408-custos-resultado-ctrc.md | Usa |
| Cadastrar tabela preco | 420 | comercial/417-418-420-tabelas-frete.md | Usa |
| Cadastrar fornecedor | 478 | financeiro/478-dados-fornecedor.md | Usa |
| Cadastrar cliente | 483 | cadastros/483-cadastro-clientes.md | Usa |
| Emitir CTRC | 004 | operacional/004-emissao-ctrcs.md | Usa |
| Enviar CTe SEFAZ | 007 | operacional/007-emissao-cte.md | Usa |
| Criar romaneio | 035 | operacional/035-romaneio-entregas.md | Parcial |
| Faturar | 437 | financeiro/436-faturamento-geral.md | Usa (manual) |
| Pre-faturamento | 435 | financeiro/435-pre-faturamento.md | Nao usa |
| Manifesto / MDF-e | 020, 025 | operacional/020-manifesto-carga.md | **Nao sabe** |
| CTe complementar | 007 | operacional/007-emissao-cte-complementar.md | **Nao sabe** |
| Custos extras | 459 | financeiro/459-relacao-adicionais.md | **Nao sabe** |
| Contratacao veiculo | 072 | operacional/072-contratacao-de-veiculo-de-transferencia.md | **Nao sabe** |
| Contas a pagar | 475 | financeiro/475-contas-a-pagar.md | **Nao faz** |
| CCF (conta corrente fornecedor) | 486 | financeiro/486-conta-corrente-fornecedor.md | **Nao faz** |
| Cobranca bancaria | 444 | financeiro/444-cobranca-bancaria.md | **Nao faz** |
| Liquidacao | 048 | financeiro/048-liquidacao-a-vista.md | **Nao faz** |
| Conciliacao bancaria | 569 | contabilidade/569-conciliacao-bancaria.md | **Nao faz** |
| Resultado por CTRC | 101 | comercial/101-resultado-ctrc.md | **Nao faz** |
| Comprovante entrega | 040, 049, 428 | operacional/049-controle-comprovantes.md | **Nao faz** |
| Ocorrencias | 033, 038, 108 | operacional/033-ocorrencias-de-transferencia.md | **Nao faz** |
| Parametros de frete | 062 | — | **Nao conhece** |
| Parametros gerais | 903 | cadastros/903-parametros-gerais.md | **Nao conhece** |
| Relatorios gerenciais | 056 | visao-geral/06-info-gerenciais.md | **Nao usa** |
| Controle frota | 026, 131, 320 | relatorios/131-ordens-servico.md | **Nao faz** |

---

## 9. Relacao Sistema Fretes (Nacom) ↔ SSW (CarVia)

```
SISTEMA FRETES (Nacom)              SSW (CarVia)
━━━━━━━━━━━━━━━━━━━━               ━━━━━━━━━━━━━
Tabelas de transportadoras  ──→  Opcao 408 (custos/comissoes)
  (fonte de verdade)               (espelho do sistema fretes)

Vinculos (cidades + polos)  ──→  Opcao 402 (cidades atendidas)
  (origem dos dados)               (cadastro manual)

Cotacao interna             ──→  Opcao 002 (cotacao SSW)
  (analise previa)                 (cotacao oficial ao cliente)

Lead times                  ──→  Opcao 402 (prazo por cidade)

Precos por polo (P/R/I)    ──→  Opcao 420 (tabela por rota)
                                   (com margem CarVia)
```

> **Oportunidade futura**: Automatizar a sincronizacao Sistema Fretes → SSW para novas rotas.

---

## 10. Proximos Passos

### Fase 5A — Processos Prioritarios (criar POPs)

Baseado nas prioridades do Rafael, os primeiros POPs devem cobrir:

| # | POP | Urgencia | Justificativa |
|---|-----|----------|---------------|
| 1 | Emissao de Manifesto (MDF-e) | **URGENTE** | Obrigatorio para cargas interestaduais |
| 2 | Regras legais (CT-e antes embarque, NF de outro UF) | **URGENTE** | Risco de sinistro sem cobertura |
| 3 | Contas a pagar (transportadoras subcontratadas) | ALTA | Fluxo financeiro incompleto |
| 4 | Conciliacao cobrado vs pago | ALTA | Controle financeiro critico |
| 5 | Formacao de preco / simulacao | ALTA | Entender por que simulacao falha |
| 6 | CTe complementar e custos extras | MEDIA | Necessario quando surgir caso |
| 7 | Resultado por CTRC | MEDIA | Visao de lucratividade |
| 8 | Contratacao formal de veiculo | MEDIA | Formalizar custos de carga direta |
| 9 | Cobranca bancaria (boleto) | MEDIA | Profissionalizar recebimento |
| 10 | Comprovante de entrega | MEDIA | Controle operacional |
