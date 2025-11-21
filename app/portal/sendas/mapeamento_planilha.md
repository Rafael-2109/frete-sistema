# Mapeamento de Campos da Planilha do Sendas

**Última atualização**: 21/11/2025
**Versão**: 2.0 - Layout atualizado com 3 novas colunas de data

---

## Estrutura da Planilha (26 colunas)

| Coluna | Linha 3 (Cabeçalho) | Linha 4 (Exemplo) | Ação | Explicação |
|--------|---------------------|-------------------|------|------------|
| A | Demanda | 1 | Preenchimento | ID sequencial por agendamento. Mesmo número para todos os itens do mesmo protocolo |
| B | Razão Social - Fornecedor | NACOM GOYA IND COM ALIMENTOS LTDA | - | Vem da planilha modelo |
| C | Nome Fantasia - Fornecedor | NACOM GOYA | - | Vem da planilha modelo |
| D | Unidade de destino | SENDAS 923 CD MANAUS | Extração | Usar FilialDeParaSendas.filial para traduzir CNPJ |
| E | UF Destino | AM | - | Vem da planilha modelo |
| F | Fluxo de operação | Recebimento | - | Vem da planilha modelo |
| G | Código do pedido Cliente | 19447861-923 | Extração | Máscara: pedido_cliente + "-" + número da filial |
| H | Código Produto Cliente | 93734 | Extração | Usar ProdutoDeParaSendas para traduzir códigos |
| I | Código Produto SKU Fornecedor | - | - | Vem da planilha modelo (opcional) |
| J | EAN | - | - | Vem da planilha modelo (opcional) |
| K | Setor | - | - | Vem da planilha modelo (opcional) |
| **L** | **Entrega De** | - | **Preenchimento** | **NOVA - Preencher com Data sugerida de entrega (DD/MM/YYYY)** |
| **M** | **Entrega Até** | - | **Preenchimento** | **NOVA - Preencher com Data sugerida de entrega (DD/MM/YYYY)** |
| **N** | **Data Ideal** | - | **Preenchimento** | **NOVA - Preencher com Data sugerida de entrega (DD/MM/YYYY)** |
| O | Descrição do Item | AZEITONA PTA CAMPO BELO FAT 1,01KG | - | Vem da planilha modelo |
| P | Quantidade total | 20 | - | Vem da planilha modelo |
| Q | Saldo disponível | 20 | - | Vem da planilha modelo |
| R | Unidade de medida | CX | - | Vem da planilha modelo |
| S | Quantidade entrega | - | Preenchimento | Quantidade a entregar (respeitar Saldo disponível) |
| T | Data sugerida de entrega | - | Preenchimento | Data de agendamento no formato DD/MM/YYYY |
| U | ID de agendamento (opcional) | - | - | Opcional |
| V | Reserva de Slot (opcional) | - | - | Opcional |
| W | Característica da carga | Paletizada | Preenchimento | Campo select, SEMPRE usar "Paletizada" |
| X | Característica do veículo | - | Preenchimento | Campo select, calcular pelo peso total |
| Y | Transportadora CNPJ (opcional) | - | - | Opcional |
| Z | Observação/ Fornecedor (opcional) | - | Preenchimento | Gravar protocolo do agendamento |

---

## Colunas Removidas (Layout Antigo)

| Coluna Antiga | Nome | Status |
|---------------|------|--------|
| L | Número do pedido Trizy | **REMOVIDA** - Não existe mais no layout do Sendas |

---

## Novas Colunas (Adicionadas em Nov/2025)

| Coluna | Nome | Descrição | Valor |
|--------|------|-----------|-------|
| L | Entrega De | Data mínima de entrega | Usar mesma data de "Data sugerida de entrega" |
| M | Entrega Até | Data máxima de entrega | Usar mesma data de "Data sugerida de entrega" |
| N | Data Ideal | Data ideal de entrega | Usar mesma data de "Data sugerida de entrega" |

---

## Característica do Veículo (Coluna X)

Calcular com base no peso total do agendamento:

| Veículo | Peso Máximo (KG) |
|---------|------------------|
| Utilitário | 800 |
| Caminhão VUC 3/4 | 2.000 |
| Caminhão 3/4 (2 eixos) 16T | 4.000 |
| Caminhão Truck (6x2) 23T | 8.000 |
| Carreta Simples Toco (3 eixos) 25T | 25.000 |
| Caminhão (4 eixos) 31T | Acima de 25.000 |

---

## Fluxo de Preenchimento

1. **Importar planilha modelo** do portal Sendas (contém colunas B-R já preenchidas)
2. **Comparar solicitações** com disponibilidade na planilha modelo
3. **Exportar planilha** combinando:
   - Dados da planilha modelo (colunas B-R)
   - Novas datas de entrega (colunas L, M, N) = Data sugerida
   - Dados editáveis (colunas S-Z)
4. **Upload** no Portal Sendas

---

## Observações Importantes

- A coluna "Demanda" (A) deve ter o mesmo número para todos os itens do mesmo protocolo
- As 3 novas colunas de data (L, M, N) são preenchidas automaticamente com a mesma data
- O formato de data deve ser DD/MM/YYYY
- A coluna "Número do pedido Trizy" foi **removida** do layout em Nov/2025
