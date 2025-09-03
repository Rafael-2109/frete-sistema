# 📊 FLUXOGRAMA: Sincronização de Notas Fiscais

## Fluxo Principal de Processamento

```mermaid
flowchart TD
    Start([Início: Buscar NFs últimos 5 dias]) --> CheckCanceled{NF Cancelada?}
    
    CheckCanceled -->|Sim| ExistsInFat{Existe em<br/>FaturamentoProduto?}
    CheckCanceled -->|Não| CheckProcessed{Já processada?}
    
    ExistsInFat -->|Sim e status != Cancelado| ProcessCancel[Processar Cancelamento]
    ExistsInFat -->|Não ou já cancelada| Skip1[Pular NF]
    
    ProcessCancel --> DeleteMov[Apagar MovimentacaoEstoque]
    DeleteMov --> UpdateStatus[Status = 'Cancelado']
    UpdateStatus --> NextNF
    
    CheckProcessed -->|Sim| Skip2[Pular NF]
    CheckProcessed -->|Não| CheckTipoEnvio{Tipo Envio?}
    
    CheckTipoEnvio -->|Total| FindEmbarque1[Buscar em EmbarqueItem]
    CheckTipoEnvio -->|Parcial| CountEmbarque{Quantos<br/>EmbarqueItem?}
    
    FindEmbarque1 --> ProcessNF1[Processar NF]
    
    CountEmbarque -->|1| GetLoteId1[Pegar separacao_lote_id]
    CountEmbarque -->|2+ sem NF| CalcScore[Calcular Score]
    CountEmbarque -->|0| NoOrder[Pedido não encontrado]
    
    GetLoteId1 --> ProcessNF2[Processar NF]
    
    CalcScore --> SelectBest[Selecionar melhor match]
    SelectBest --> GetLoteId2[Pegar separacao_lote_id]
    GetLoteId2 --> ProcessNF3[Processar NF]
    
    NoOrder --> CreateMovNoLote[Criar MovimentacaoEstoque<br/>SEM separacao_lote_id]
    CreateMovNoLote --> CreateAlert[Criar Alerta]
    
    ProcessNF1 --> UpdateEmbarque[Atualizar EmbarqueItem<br/>nota_fiscal = NF]
    ProcessNF2 --> UpdateEmbarque
    ProcessNF3 --> UpdateEmbarque
    
    UpdateEmbarque --> UpdateSeparacao[Atualizar Separacao<br/>numero_nf = NF<br/>sincronizado_nf = True]
    
    UpdateSeparacao --> CreateMov[Criar MovimentacaoEstoque<br/>com separacao_lote_id e NF]
    
    CreateMov --> NextNF
    CreateAlert --> NextNF
    Skip1 --> NextNF
    Skip2 --> NextNF
    
    NextNF{Mais NFs?}
    NextNF -->|Sim| CheckCanceled
    NextNF -->|Não| End([Fim])
    
    style ProcessCancel fill:#ff9999
    style CreateAlert fill:#ffcc99
    style UpdateSeparacao fill:#99ff99
    style CalcScore fill:#99ccff
```

## Algoritmo de Score para Separações Parciais

```mermaid
flowchart LR
    Start([NF com produtos]) --> Loop{Para cada<br/>produto NF}
    
    Loop --> Match{Produto existe<br/>em EmbarqueItem?}
    
    Match -->|Sim| CalcDiff[Calcular diferença<br/>de quantidade]
    Match -->|Não| Score0[Score = 0]
    
    CalcDiff --> CalcScore[Score = 100 - diferença%]
    
    CalcScore --> AddScore[Somar ao score total]
    Score0 --> AddScore
    
    AddScore --> NextProd{Mais<br/>produtos?}
    
    NextProd -->|Sim| Loop
    NextProd -->|Não| AvgScore[Score Final =<br/>total / matches]
    
    AvgScore --> Decision{Score >= 80%?}
    
    Decision -->|Sim| Accept[✅ Match confiável]
    Decision -->|60-79%| Warning[⚠️ Match duvidoso]
    Decision -->|< 60%| Reject[❌ Match ruim]
    
    style Accept fill:#99ff99
    style Warning fill:#ffcc99
    style Reject fill:#ff9999
```

## Estados de MovimentacaoEstoque

```mermaid
stateDiagram-v2
    [*] --> Previsto: Criação inicial
    
    Previsto --> Faturado: NF processada
    Previsto --> Cancelado: Pedido cancelado
    
    Faturado --> Cancelado: NF cancelada
    
    Cancelado --> [*]
    Faturado --> [*]
    
    note right of Previsto
        Separacao existe
        sincronizado_nf = False
    end note
    
    note right of Faturado
        NF vinculada
        sincronizado_nf = True
        Sai da carteira
    end note
    
    note right of Cancelado
        MovimentacaoEstoque apagada
        FaturamentoProduto.status = 'Cancelado'
    end note
```

## Impacto do sincronizado_nf

```mermaid
graph TD
    Sep[Separacao] --> Check{sincronizado_nf?}
    
    Check -->|False| InCart[✅ Aparece na Carteira]
    Check -->|False| InStock[✅ Projeta Estoque]
    Check -->|False| CanEdit[✅ Pode Editar]
    
    Check -->|True| OutCart[❌ Não aparece na Carteira]
    Check -->|True| OutStock[❌ Não projeta Estoque]
    Check -->|True| NoEdit[❌ Não pode Editar]
    Check -->|True| HasNF[📄 Tem NF vinculada]
    
    style InCart fill:#99ff99
    style InStock fill:#99ff99
    style CanEdit fill:#99ff99
    style OutCart fill:#ff9999
    style OutStock fill:#ff9999
    style NoEdit fill:#ff9999
    style HasNF fill:#99ccff
```

## Validações na Importação da Carteira

```mermaid
flowchart TD
    Import([Importação Carteira]) --> CheckQtd{Alterou<br/>qtd_produto?}
    
    CheckQtd -->|Sim| HasCotacao1{Separacao<br/>COTADA?}
    CheckQtd -->|Não| CheckCancel{Alterou<br/>qtd_cancelada?}
    
    HasCotacao1 -->|Sim| Alert1[⚠️ Alerta:<br/>Pedido já cotado]
    HasCotacao1 -->|Não| Update1[✅ Atualizar]
    
    CheckCancel -->|Sim| HasCotacao2{Separacao<br/>COTADA?}
    CheckCancel -->|Não| CheckStatus{Mudou para<br/>cancelado?}
    
    HasCotacao2 -->|Sim| Alert2[⚠️ Alerta:<br/>Cancelamento em cotado]
    HasCotacao2 -->|Não| Update2[✅ Atualizar]
    
    CheckStatus -->|Sim| HasCotacao3{Separacao<br/>COTADA?}
    CheckStatus -->|Não| Continue[Continuar importação]
    
    HasCotacao3 -->|Sim| Alert3[❌ Alerta:<br/>Não pode cancelar cotado]
    HasCotacao3 -->|Não| Update3[✅ Cancelar]
    
    Alert1 --> Log[Registrar no log]
    Alert2 --> Log
    Alert3 --> Log
    Update1 --> Continue
    Update2 --> Continue
    Update3 --> Continue
    Log --> Continue
    
    Continue --> Next{Mais itens?}
    Next -->|Sim| CheckQtd
    Next -->|Não| End([Fim])
    
    style Alert1 fill:#ffcc99
    style Alert2 fill:#ffcc99
    style Alert3 fill:#ff9999
    style Update1 fill:#99ff99
    style Update2 fill:#99ff99
    style Update3 fill:#99ff99
```

---

**Visualização**: Abra este arquivo em um editor que suporte Mermaid (VS Code com extensão, GitHub, etc.)  
**Última Atualização**: 29/01/2025