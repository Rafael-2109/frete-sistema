# Opção 938 — Administradoras de Cartões

> **Módulo**: Sistema (Controle)
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Parametrização das administradoras de cartões utilizadas pela transportadora para recebimento de fretes via cartão de débito e crédito.

## Quando Usar
- Cadastrar administradora de cartões contratada
- Configurar dias de crédito (débito e crédito)
- Definir tarifas cobradas pela administradora
- Vincular conta bancária que receberá os créditos
- Configurar integração Pin Pad (ADYEN ou SITEF)

## Pré-requisitos
- Contrato com administradora de cartões
- Conta bancária cadastrada (opção 904)
- Para Pin Pad: integração com ADYEN ou SITEF configurada
- Máquinas de cartões cadastradas (opção 924)

## Processo

```
Opção 938 - Cadastra e parametriza administradora
         ↓
Opção 924 - Cadastra máquinas de cartões
         ↓
Opção 048 ou SSWMobile - Recebimento de frete via cartão
```

## Campos / Interface

### Tela Principal

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Empresa** | Não | Se multiempresa utilizada |
| **Administradora** | Sim | Escolher no link (SUMUP, CIELO, REDE, PAGSEGURO, GETNET, IZETTLE, MERCADO PAGO, PAYLEVEN, PAGCOM, STONE, SAFRAPAY, PICPAY, SIPAG, SICRED, BANRISUL, BANESE, ADYEN, SITEF) |
| **Bandeira cartão (opc)** | Não | Visa, Mastercard, Elo, Hipercard, American Express, Diners Club, Banricompras. Se omitida, qualquer bandeira aceita |
| **Número contrato** | Sim | Número do contrato com administradora. Se não existe, informar qualquer número |
| **Banco/ag/ccor (DV opc)** | Sim | Conta cadastrada (opção 904) que receberá os créditos |
| **Crédito D+** | Sim (2 campos) | Dias úteis de crédito na conta para: **Cartão de Crédito** e **Cartão de Débito** |
| **Tarifa (%)** | Sim | Tarifa debitada (% sobre crédito) pela administradora |

### Configurações Específicas

#### ADYEN (Pin Pad)
- Unidades (opção 401) vinculadas a API KEYs da ADYEN
- Cada unidade recebe sua API KEY

#### SITEF (Pin Pad)
- Todos Pin Pads (PDVs) cadastrados com:
  - Código PDV
  - Código da loja Sitef
  - Token
- **Limpar usuário**: desvincular usuário do PDV quando liquidação não foi concluída (opção 048)

## Administradoras e CNPJs

| # | Administradora | CNPJ (complemento contas opção 540) |
|---|----------------|-------------------------------------|
| 1 | SUMUP | 16668076000120 |
| 2 | CIELO | 01027058000191 |
| 3 | REDE | 01425787000104 |
| 4 | PAGSEGURO UOL | 08561701000101 |
| 5 | GETNET | 10440482000154 |
| 6 | IZETTLE | 17344776000121 |
| 7 | MERCADO PAGO | 10573521000191 |
| 8 | PAYLEVEN | 15185132000102 |
| 9 | PAGCOM | 10344530000100 |
| 10 | STONE | 16501555000157 |
| 11 | SAFRAPAY | 58160789000128 |
| 12 | PICPAY | 22896431000110 |
| 13 | SIPAG | 02038232000164 |
| 14 | SICRED | 01181521000155 |
| 15 | BANRISUL | 92934215000106 |
| 16 | BANESE | 03847413000102 |
| 98 | ADYEN | 14796606000190 |
| 99 | SITEF | 55649404000100 |

## Fluxo de Uso

### Cadastrar Administradora

1. Acesse opção 938
2. Selecione empresa (se multiempresa)
3. Escolha administradora no link
4. Informe bandeira (opcional)
5. Informe número do contrato
6. Selecione banco/agência/conta (opção 904)
7. Defina dias de crédito (débito e crédito)
8. Defina tarifa (%)
9. Confirme cadastro

### Configurar Pin Pad ADYEN

1. Cadastre administradora ADYEN
2. Vincule unidades (opção 401) a API KEYs da ADYEN
3. Teste recebimento via opção 048

### Configurar Pin Pad SITEF

1. Cadastre administradora SITEF
2. Cadastre todos Pin Pads (PDVs):
   - Código PDV
   - Código loja Sitef
   - Token
3. Teste recebimento via opção 048
4. Se liquidação não concluir, use "Limpar usuário"

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 048 | Liquidação de CTRC ou fatura via cartão |
| 401 | Unidades (para ADYEN - API KEYs) |
| 540 | Contas contábeis (CNPJs como complementos) |
| 904 | Cadastro de contas bancárias |
| 924 | Cadastro de máquinas de cartões |
| SSWMobile | Recebimento de fretes via cartão pelo motorista |

## Observações e Gotchas

### Pin Pad vs Máquina de Cartão
- **Pin Pad**: integração direta (ADYEN ou SITEF) via opção 048
- **Máquina de cartão**: manual, cadastrada na opção 924

### Dias de Crédito
- **Dias úteis** (não corridos)
- Diferentes para **Débito** e **Crédito**
- Exemplo: Débito D+1, Crédito D+30

### Tarifa
- Percentual sobre o valor creditado
- Debitada automaticamente pela administradora
- Informar % conforme contrato

### Conta Bancária
- Deve estar cadastrada na opção 904
- Receberá os créditos descontada a tarifa
- Pode ser compartilhada entre administradoras

### Bandeira Opcional
- Se não informada, aceita qualquer bandeira na liquidação (opção 048)
- Se informada, restringe a essa bandeira

### Limpar Usuário (SITEF)
- Necessário quando liquidação não conclui corretamente
- Desvincular usuário do PDV para permitir nova tentativa
- Evita bloqueio do Pin Pad

### Multiempresa
- Campo Empresa só se multiempresa ativada
- Padrão: 01

### CNPJs como Complementos
- Utilizados em contas contábeis (opção 540)
- Facilita rastreamento por administradora

### Manuais de Integração
- **ADYEN**: Consultar manual específico
- **SITEF**: Consultar manual específico
- Contatar SSW se necessário
