# Opção 804 — Geração de CTRCs (Modal Aquaviário)

> **Módulo**: Embarcador
> **Páginas de ajuda**: Compartilha documentação com opção 004 (mesma tela, modal diferente)
> **Atualizado em**: 2026-02-14

## Função
Gera documentos fiscais de transportes para **modal aquaviário**. É uma variante da opção 004 específica para operações de transporte via navegação (rios, lagos, oceanos).

## Quando Usar
- Para emitir CT-es de operações de transporte aquaviário
- Para documentar cargas transportadas por via navegável
- Quando o modal de transporte é aquaviário (e não rodoviário, aéreo ou ferroviário)

## Pré-requisitos
- Cliente cadastrado no sistema
- Notas fiscais das mercadorias a transportar
- Dados do trajeto aquaviário (portos, embarcações, etc.)

## Relação com Opção 004

A opção 804 **é a mesma opção 004**, mas adaptada para **modal aquaviário**:

| Opção | Modal | Descrição |
|-------|-------|-----------|
| 004 | Rodoviário | Modal padrão (caminhões, carretas, etc.) |
| 604 | Aéreo | Modal aéreo (aviões, cargas aéreas) |
| 804 | Aquaviário | Modal aquaviário (navios, barcaças, etc.) |

## Campos / Interface

Os campos são **idênticos à opção 004**, com adaptações para modal aquaviário:

- **Placa de Coleta**: Substituído por identificação da embarcação (quando aplicável)
- **Origem/Destino**: Portos ou locais de embarque/desembarque
- **Dados de Transporte**: Informações específicas do modal aquaviário

Para detalhes completos dos campos, consultar documentação da **opção 004**.

## Fluxo de Uso

### Geração de CT-e Aquaviário
1. Acessar opção 804
2. Escolher tipo de documento (Normal, Carga Fechada, Subcontrato, etc.)
3. Informar dados da operação (adaptados para modal aquaviário):
   - Embarcação (em vez de veículo)
   - Porto de origem
   - Porto de destino
   - Dados da carga
4. Capturar chave de acesso da NF-e ou informar dados manualmente
5. Definir tomador do frete (CIF ou FOB)
6. Confirmar geração do pré-CT-e
7. Enviar ao SEFAZ pela opção 007

### Tipos de Documentos Disponíveis
Mesmos tipos da opção 004:
- **N - CT-e Normal**: Operação padrão de transporte aquaviário
- **F - CT-e Carga Fechada (FEC)**: Transporte direto sem transbordo
- **3 - Subcontrato recepção**: Subcontratação de transporte
- **S - Subcontrato não fiscal**: Controle operacional (sem valor fiscal)
- E outros tipos conforme documentação da opção 004

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 004 | Geração de CTRCs (modal rodoviário) - mesma funcionalidade |
| 604 | Geração de CTRCs (modal aéreo) - mesma funcionalidade |
| 007 | Aprovação de CT-es - envio ao SEFAZ |
| 008 | Impressão de subcontratos não fiscais |
| 009 | Impressão de documentos fiscais municipais |
| 006 | Geração de CTRCs em lotes (pode incluir modal aquaviário) |
| 071 | Consultar e alterar NF-es/CT-es antes de gerar CTRCs |
| 600 | Recepção de arquivos EDI (pode incluir operações aquaviárias) |

## Observações e Gotchas

### Modal Aquaviário vs. Rodoviário
- **Legislação**: Regras fiscais específicas para transporte aquaviário
- **Embarcação**: Em vez de placa de veículo, identificação da embarcação
- **Portos**: Origem e destino são portos ou locais de embarque/desembarque
- **Documentação**: Pode requerer documentos adicionais específicos do modal

### Particularidades do Modal
- **Controle de gelo**: Opção 004 menciona controle de gelo (item 11 da documentação) que pode ser relevante para cargas refrigeradas em transporte aquaviário
- **Multimodal**: Operações aquaviárias frequentemente fazem parte de operações multimodais (tipo M na opção 004)

### Funcionalidades Compartilhadas
A opção 804 compartilha TODAS as funcionalidades da opção 004:
- Geração de CT-e Normal, Cortesia, Devolução, Reversa, FEC, Multimodal, Simplificado
- Subcontratação (tipos 3, S, 4, 5, V, L, 6, 1, Y, X, H, G)
- Verificações automáticas
- Definições de CFOP e CST
- Tributação de ICMS e ISS
- Produtor rural, Exportação e Importação
- Unitização
- Alteração e cancelamento (opção 004)
- Carta de Correção (opção 736)

### Referência Completa
Para documentação completa de campos, processos e regras, consultar **documentação da opção 004**, aplicando adaptações necessárias para modal aquaviário.

### Observação Importante
A opção 804 **não é uma opção separada** com documentação própria. É simplesmente a **opção 004 configurada para modal aquaviário**. Toda a documentação, processos e regras da opção 004 se aplicam, com as adaptações mencionadas acima para o modal específico.
