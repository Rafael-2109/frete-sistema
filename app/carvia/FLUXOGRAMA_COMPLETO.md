# CarVia — Fluxograma Completo do Modulo

**Gerado em**: 2026-04-19
**Escopo**: Visao 100% conectada do modulo CarVia — arquitetura, fluxo de dados, lifecycles, workers e pontos de aprofundamento.

**Stats**: 96 arquivos | ~55.5K LOC | 103 templates | 29 routes | 11 models | 26+ services | 3 workers RQ

> Este documento e um **mapa de alto nivel**. Para aprofundamento tecnico, consulte os sub-docs referenciados em cada secao:
> [CLAUDE.md](CLAUDE.md) · [CONFERENCIA.md](CONFERENCIA.md) · [FINANCEIRO.md](FINANCEIRO.md) · [FLUXOS_CRIACAO.md](FLUXOS_CRIACAO.md) · [IMPORTACAO.md](IMPORTACAO.md) · [COTACAO.md](COTACAO.md) · [SSW_INTEGRATION.md](SSW_INTEGRATION.md) · [AUDIT_ADMIN_SERVICE.md](AUDIT_ADMIN_SERVICE.md)

---

## 1. Arquitetura Geral (Camadas)

```mermaid
flowchart TB
    subgraph ENTRADA["PONTOS DE ENTRADA"]
        E1[Portaria Hook<br/>portaria/routes.py:374]
        E2[Importacao Upload<br/>/carvia/importar]
        E3[Emissao SSW UI<br/>POST /api/nfs/id/emitir-cte-ssw]
        E4[Cotacao Comercial<br/>/carvia/cotacoes-v2]
        E5[Conciliacao OFX/CSV<br/>/carvia/extrato-bancario]
        E6[Admin/Manual<br/>wizard DEPRECATED]
    end

    subgraph ROUTES["ROUTES - 29 blueprints"]
        R1[dashboard_routes]
        R2[importacao_routes<br/>+ importacao_config]
        R3[nf_routes / operacao_routes<br/>subcontrato_routes]
        R4[fatura_routes<br/>cte_complementar_routes<br/>custo_entrega_routes]
        R5[conciliacao_routes<br/>fluxo_caixa_routes<br/>despesa/receita_routes]
        R6[cotacao_v2_routes<br/>pedido_routes / frete_routes<br/>cliente_routes]
        R7[api_routes / scanner_routes<br/>simulador_routes<br/>exportacao_routes]
        R8[admin_routes / aprovacao<br/>conta_corrente / comissao<br/>config / tabela / gerencial]
    end

    subgraph SERVICES["SERVICES - 26+ orquestradores"]
        S1[ImportacaoService<br/>parsers/importacao_service.py:60]
        S2[CarviaFreteService<br/>documentos/carvia_frete_service.py:32]
        S3[SswEmissaoService<br/>documentos/ssw_emissao_service.py:40]
        S4[ConferenciaService<br/>+ AprovacaoFreteService<br/>documentos/]
        S5[LinkingService<br/>MatchingService<br/>documentos/]
        S6[CarviaConciliacaoService<br/>+ PreVinculoService<br/>+ HistoricoMatchService<br/>financeiro/]
        S7[CotacaoService<br/>CarviaTabelaService<br/>pricing/]
        S8[CustoEntregaFaturaService<br/>FluxoCaixaService<br/>ComissaoService<br/>ContaCorrenteService]
    end

    subgraph MODELS["MODELS - 11 arquivos / 30+ tabelas"]
        M1[documentos.py<br/>Nf - NfItem - NfVeiculo<br/>Operacao - OperacaoNf - Subcontrato]
        M2[frete.py<br/>Frete - EmissaoCte]
        M3[faturas.py<br/>FaturaCliente - FaturaTransportadora<br/>+ Itens]
        M4[cte_custos.py<br/>CteComplementar - CustoEntrega<br/>CustoEntregaAnexo - EmissaoCteComp]
        M5[financeiro.py<br/>Despesa - Receita<br/>ContaMovimentacao - ExtratoLinha<br/>Conciliacao - PreVinculo - HistoricoMatch]
        M6[cotacao.py - clientes.py<br/>Cotacao - CotacaoMoto<br/>Pedido - PedidoItem<br/>Cliente - ClienteEndereco]
        M7[tabelas.py - config_moto.py<br/>TabelaFrete - CidadeAtendida<br/>GrupoCliente - CategoriaMoto<br/>ModeloMoto - PrecoCategoria - Config]
        M8[admin - aprovacao<br/>comissao - conta_corrente<br/>AdminAudit - AprovacaoFrete<br/>ComissaoFechamento - CC_Transp]
    end

    subgraph WORKERS["WORKERS RQ - 3 filas"]
        W1[ssw_cte_jobs<br/>fila: high / 10min]
        W2[ssw_cte_complementar_jobs<br/>fila: default]
        W3[verificar_ctrc_ssw_jobs<br/>fila: default / backfill]
    end

    subgraph EXT["EXTERNOS"]
        X1[Playwright SSW<br/>.claude/skills/operando-ssw]
        X2[S3 file_storage<br/>carvia/ctes_xml - ctes_pdf<br/>nfs_pdf - faturas_pdf]
        X3[PostgreSQL Render]
        X4[Modulos siblings<br/>transportadoras - tabelas<br/>vinculos - embarques - portaria]
    end

    ENTRADA --> ROUTES
    ROUTES --> SERVICES
    SERVICES --> MODELS
    MODELS --> X3
    SERVICES --> WORKERS
    WORKERS --> X1
    WORKERS --> SERVICES
    SERVICES --> X2
    SERVICES -.lazy imports.-> X4

    classDef entry fill:#fef3c7,stroke:#f59e0b,color:#78350f
    classDef route fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a
    classDef service fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef model fill:#fce7f3,stroke:#db2777,color:#831843
    classDef worker fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
    classDef ext fill:#e5e7eb,stroke:#6b7280,color:#1f2937

    class E1,E2,E3,E4,E5,E6 entry
    class R1,R2,R3,R4,R5,R6,R7,R8 route
    class S1,S2,S3,S4,S5,S6,S7,S8 service
    class M1,M2,M3,M4,M5,M6,M7,M8 model
    class W1,W2,W3 worker
    class X1,X2,X3,X4 ext
```

---

## 2. Fluxo de Dados — Bifurcacao VENDA vs COMPRA

**Regra de ouro** ([CONFERENCIA.md](CONFERENCIA.md)): CarVia opera em **2 dominios independentes** com eixo unificado em `CarviaFrete`.

- **VENDA** (receita): tabela CarVia -> `CarviaOperacao` -> `CarviaFaturaCliente` - conferencia manual
- **COMPRA** (custo): tabela Nacom -> `CarviaSubcontrato` -> `CarviaFaturaTransportadora` - conferencia automatica

```mermaid
flowchart LR
    subgraph ORIG["ORIGEM"]
        COT[CarviaCotacao<br/>COT-###]
        EMB[Embarque Nacom<br/>app/embarques]
    end

    subgraph EIXO["EIXO CENTRAL - CarviaFrete"]
        FRETE["CarviaFrete<br/>UK embarque_id+cnpj_emit+cnpj_dest<br/>status_conferencia: PENDENTE/APROVADO/DIVERGENTE"]
    end

    subgraph VENDA["LADO VENDA - tabela CarVia"]
        NF[CarviaNf<br/>PDF/XML]
        OP[CarviaOperacao<br/>CTe-### / cte_valor]
        JNC[CarviaOperacaoNf<br/>junction N:N]
        CTC[CarviaCteComplementar<br/>COMP-###]
        FC[CarviaFaturaCliente<br/>FAT-### / PAGA]
    end

    subgraph COMPRA["LADO COMPRA - tabela Nacom"]
        SUB[CarviaSubcontrato<br/>Sub-### / valor_cotado]
        CE[CarviaCustoEntrega<br/>PENDENTE/VINCULADO_FT/PAGO]
        FT[CarviaFaturaTransportadora<br/>FTRANSP-### / PAGO]
    end

    subgraph FIN["FINANCEIRO"]
        EXT[CarviaExtratoLinha<br/>OFX/CSV/MANUAL]
        CONC[CarviaConciliacao<br/>junction extrato-doc]
        PVN[CarviaPreVinculo<br/>ATIVO/RESOLVIDO]
        HIST[CarviaHistoricoMatch<br/>aprendizado append-only]
        MOV[CarviaContaMovimentacao<br/>saldo SUM]
    end

    COT -->|aprovacao| PED[CarviaPedido]
    PED -->|embarque provisorio| EMB
    EMB -->|portaria hook<br/>lancar_frete_carvia| FRETE
    FRETE -->|operacao_id| OP
    FRETE -->|subcontrato_id 1:N| SUB
    NF -.->|importacao| JNC
    JNC --> OP
    OP -->|cte_xml importado| FRETE
    SUB -->|cte_xml importado| FRETE

    OP -->|fatura_cliente_id| FC
    CTC -->|fatura_cliente_id| FC
    OP --> CTC

    SUB -->|fatura_transportadora_id| FT
    CE -->|fatura_transportadora_id| FT
    CE -->|frete_id| FRETE
    CTC -->|frete_id| FRETE

    FC -->|conciliar| CONC
    FT -->|conciliar| CONC
    CE -.->|propagacao PAGO| FT
    EXT --> CONC
    EXT -.-> PVN
    PVN -.->|fatura chega| COT
    CONC -.->|append log| HIST
    FC & FT -.->|saldo| MOV

    classDef eixo fill:#fde68a,stroke:#ca8a04,stroke-width:3px
    classDef venda fill:#d1fae5,stroke:#059669
    classDef compra fill:#fee2e2,stroke:#dc2626
    classDef fin fill:#e0e7ff,stroke:#4f46e5

    class FRETE eixo
    class NF,OP,JNC,CTC,FC venda
    class SUB,CE,FT compra
    class EXT,CONC,PVN,HIST,MOV fin
```

---

## 3. State Machines — Lifecycle de Status

**Regra R4**: status e **irreversivel** exceto cancelamento. Cancelar e criar novo — NUNCA mover para tras.

```mermaid
stateDiagram-v2
    direction LR
    state "CarviaOperacao (VENDA)" as O {
        [*] --> RASCUNHO
        RASCUNHO --> COTADO
        COTADO --> CONFIRMADO
        CONFIRMADO --> FATURADO
        RASCUNHO --> CANCELADO
        COTADO --> CANCELADO
        CONFIRMADO --> CANCELADO
    }

    state "CarviaSubcontrato (COMPRA)" as S {
        [*] --> PENDENTE_s
        PENDENTE_s --> COTADO_s
        COTADO_s --> CONFIRMADO_s
        CONFIRMADO_s --> FATURADO_s
        FATURADO_s --> CONFERIDO_s
    }

    state "CarviaFrete (EIXO - Phase C)" as F {
        [*] --> PENDENTE_f
        PENDENTE_f --> APROVADO : ConferenciaService auto
        PENDENTE_f --> DIVERGENTE : tolerancia excedida
        DIVERGENTE --> APROVADO : AprovacaoFrete resolvida
    }

    state "CarviaFaturaTransportadora (2 status)" as FT {
        state "status_conferencia" as SC {
            EM_CONFERENCIA --> CONFERIDO : Gate1+Gate2
            EM_CONFERENCIA --> DIVERGENTE_ft
        }
        state "status_pagamento" as SP {
            PENDENTE_p --> PAGO_p : conciliacao 100%
        }
    }

    state "CarviaCustoEntrega" as CE {
        [*] --> PENDENTE_ce
        PENDENTE_ce --> VINCULADO_FT
        VINCULADO_FT --> PAGO_ce : propagacao FT
    }

    state "CarviaPreVinculo" as PV {
        [*] --> ATIVO
        ATIVO --> RESOLVIDO : fatura chega
        ATIVO --> CANCELADO_pv : usuario
    }
```

---

## 4. Workers SSW — Emissao CTe via Playwright

**Regra R15**: workers Playwright (60-120s+) DEVEM aplicar **SSL Drop Resilience** — ver [SSW_INTEGRATION.md](SSW_INTEGRATION.md).

Padrao canonico:
1. **Snapshot ORM** em variaveis locais (`ctrc_numero_local`, `filial_local`, ...)
2. **Liberar conexao**: `db.session.commit() + close() + engine.dispose()` ANTES do Playwright
3. **Re-busca + retry 3x** com backoff 1s/2s/4s apos Playwright

```mermaid
sequenceDiagram
    autonumber
    participant UI as UI Browser
    participant RT as api_routes.py
    participant SE as SswEmissaoService
    participant RQ as Redis Queue
    participant WK as Worker ssw_cte_jobs
    participant PW as Playwright headless
    participant SSW as SSW web
    participant S3 as S3 file_storage
    participant DB as PostgreSQL

    UI->>RT: POST /api/nfs/{id}/emitir-cte-ssw
    RT->>SE: preparar_emissao(nf_id, placa, valor)
    SE->>SE: UF filial map, auto-extrai motos
    SE->>DB: CREATE CarviaEmissaoCte PENDENTE
    SE->>RQ: enqueue fila=high timeout=10min
    RT-->>UI: {job_id, emissao_id}

    loop polling a cada 5s
        UI->>RT: GET /api/emissao-cte/{id}/status
        RT-->>UI: etapa atual
    end

    WK->>DB: snapshot ORM (ctrc, filial, chave)
    WK->>DB: commit + close + dispose (R15)
    WK->>PW: emitir_cte_004.py<br/>--enviar-sefaz --consultar-101
    PW->>SSW: login / 004 / 007 SEFAZ / 101
    SSW-->>PW: XML + DACTE (60-120s)
    PW-->>WK: resultado JSON + paths /tmp

    WK->>WK: ensure_connection (retry 3x)
    WK->>SE: importar_resultado_cte(emissao, resultado)
    SE->>S3: upload XML para carvia/ctes_xml/
    SE->>S3: upload DACTE para carvia/ctes_pdf/
    SE->>DB: INSERT CarviaOperacao<br/>ctrc_numero, chave, paths
    SE->>DB: UPDATE emissao.status=SUCESSO

    opt Fatura 437
        WK->>PW: gerar_fatura_ssw_437.py
        PW-->>WK: PDF fatura
        SE->>DB: INSERT CarviaFaturaCliente
    end
```

---

## 5. Fluxos Principais — 7 Pontos de Aprofundamento

| # | Fluxo | Ponto de entrada | Orquestrador | Sub-doc |
|---|-------|------------------|--------------|---------|
| **F1** | **Cotacao -> Embarque -> Frete** (fluxo oficial) | `/carvia/cotacoes-v2` + Portaria | `CarviaFreteService.lancar_frete_carvia` | [FLUXOS_CRIACAO.md](FLUXOS_CRIACAO.md) |
| **F2** | **Importacao documentos** (NF+CTe+Fatura) | `/carvia/importar` | `ImportacaoService.salvar_importacao` + `LinkingService` | [IMPORTACAO.md](IMPORTACAO.md) |
| **F3** | **Emissao SSW CTe** (Playwright) | `POST /api/nfs/<id>/emitir-cte-ssw` | `SswEmissaoService` + workers RQ | [SSW_INTEGRATION.md](SSW_INTEGRATION.md) |
| **F4** | **Conferencia Frete -> Fatura Transp** (Gate 1 + Gate 2) | `/carvia/faturas-transportadora/<id>` | `ConferenciaService` + `AprovacaoFreteService` | [CONFERENCIA.md](CONFERENCIA.md) |
| **F5** | **Conciliacao Bancaria** (OFX/CSV -> docs) | `/carvia/conciliacao` + `/extrato-bancario` | `CarviaConciliacaoService` + propagacao FT->CE | [FINANCEIRO.md](FINANCEIRO.md) |
| **F6** | **Pre-vinculo Extrato <-> Cotacao** (frete pre-pago) | Botao em `cotacoes/detalhe.html` | `PreVinculoService` + `HistoricoMatchService` | [FINANCEIRO.md](FINANCEIRO.md) (R16-R17) |
| **F7** | **CTe Complementar** (CustoEntrega -> opcao 222) | `/carvia/custos-entrega/<id>/gerar-cte-complementar` | `ssw_cte_complementar_jobs` + `cte_complementar_persistencia` | [SSW_INTEGRATION.md](SSW_INTEGRATION.md) |

---

## 6. Regras Criticas Resumidas

| # | Regra | Impacto |
|---|-------|---------|
| **R1** | Modulo isolado (sem deps Embarque/Frete/Financeiro Nacom) | Lazy imports obrigatorios |
| **R2** | Lazy imports em routes e services | Evita circular imports |
| **R3** | `peso_utilizado = max(bruto, cubado)` — sempre recalcular | Stale -> cotacao errada |
| **R4** | Status irreversivel (CONFIRMADO !-> COTADO) | Cancelar + criar novo |
| **R5** | Fatura so vincula `fatura_id IS NULL` + status elegivel | Nunca desvincular pos-faturamento |
| **R6** | Classificacao CTe por `CARVIA_CNPJ` env var | CarVia vs Subcontrato |
| **R7** | `numero_sequencial_transportadora` auto-increment por transportadora | Unique partial index |
| **R8** | Numeracao CTe-### / Sub-### / COMP-### | Macro `carvia_ref` para UI |
| **R10** | Fluxo unico Cotacao->Portaria (wizard DEPRECATED) | `CarviaFreteService` e orquestrador unico |
| **R11** | Conciliacao 100% auto-quita titulo | Propagacao FT -> CE |
| **R13** | Condicoes comerciais propagam Cotacao -> Frete | 5 campos informativos |
| **R14** | Admin hard delete com `CarviaAdminAudit` | 12 gaps conhecidos |
| **R15** | SSL drop resilience workers Playwright | commit+close+dispose antes |
| **R16** | Pre-vinculo extrato-cotacao (frete pre-pago) | Soft vinculo, nao polui conciliacao |
| **R17** | Historico match append-only (aprendizado) | Boost scoring 1.4x |

---

## 7. Interdependencias com outros Modulos

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/transportadoras/models.py` | `Transportadora` | Campo `razao_social` (NAO `nome`), `cnpj`, `freteiro`, `ativo` |
| `app/tabelas/models.py` | `TabelaFrete` | FK de subcontratos. NAO tem campo `ativo` (filtrar via `Transportadora.ativo`) |
| `app/odoo/utils/cte_xml_parser.py` | `CTeXMLParser` | Classe pai de `CTeXMLParserCarvia` |
| `app/utils/calculadora_frete.py` | `CalculadoraFrete` | Calculo unificado de frete |
| `app/utils/frete_simulador.py` | `buscar_cidade_unificada` | Resolve nome+UF -> Cidade obj |
| `app/vinculos/models.py` | `CidadeAtendida` | Vinculos cidade -> transportadora via `codigo_ibge` |
| `app/utils/grupo_empresarial.py` | `GrupoEmpresarialService` | Filiais mesma transportadora |
| `app/utils/file_storage.py` | `get_file_storage()` | Upload/download anexos (S3/local) |
| `app/embarques/` | `Embarque`, `EmbarqueItem` | Hook da portaria cria `CarviaFrete` |
| `app/portaria/routes.py:374` | Hook saida portaria | Dispara `lancar_frete_carvia` |

> **Exporta para**: apenas `app/__init__.py` (registro do blueprint). Modulo e isolado — sem dependentes externos.

---

## 8. Permissao

Toggle `sistema_carvia` no model `Usuario`.
Decorator `@require_carvia()` em `app/utils/auth_decorators.py`.
Menu condicional em `base.html`: `{% if current_user.sistema_carvia %}`.

Badge de aprovacoes pendentes: context processor em `app/carvia/__init__.py:24` injeta `carvia_aprovacoes_pendentes`.

---

## 9. Como ler este fluxograma

1. **Comece pela secao 1** (arquitetura) para entender as camadas.
2. **Secao 2** mostra o DADO fluindo (VENDA/COMPRA + eixo central CarviaFrete).
3. **Secao 3** mostra os ESTADOS (lifecycles).
4. **Secao 4** e deep-dive do SSW (o unico worker externo).
5. **Secao 5** lista os 7 fluxos principais com link para sub-doc de cada.
6. **Secao 6-8** sao regras/interdependencias/auth.

Para aprofundar cada fluxo: abrir o sub-doc referenciado na tabela da secao 5.
