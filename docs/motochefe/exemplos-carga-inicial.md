<!-- doc:meta
tipo: how-to
camada: L3
sot_de: Dados de exemplo e roteiro de teste para a carga inicial (importacao em 3 fases) do modulo Motochefe
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 📋 EXEMPLO DE DADOS PARA TESTE - CARGA INICIAL MOTOCHEFE

> **Papel:** Fornecer dados de exemplo prontos e um roteiro de teste para validar a importacao em 3 fases da carga inicial do modulo Motochefe.

## Indice

- [FASE 1: CONFIGURAÇÕES BASE](#fase-1-configurações-base)
- [FASE 2: CADASTROS DEPENDENTES](#fase-2-cadastros-dependentes)
- [FASE 3: PRODUTOS E CLIENTES](#fase-3-produtos-e-clientes)
- [INSTRUÇÕES DE USO](#-instruções-de-uso)
- [RESULTADO ESPERADO](#-resultado-esperado)
- [TESTES ADICIONAIS](#-testes-adicionais)

Use estes dados de exemplo para testar o sistema de importação.

---

## FASE 1: CONFIGURAÇÕES BASE

### 1_Equipes (copie para Excel)

| equipe_vendas | responsavel_movimentacao | custo_movimentacao | incluir_custo_movimentacao | tipo_precificacao | markup | tipo_comissao | valor_comissao_fixa | percentual_comissao | comissao_rateada | permitir_montagem | permitir_prazo | permitir_parcelamento |
|---------------|--------------------------|-------------------|---------------------------|-------------------|--------|---------------|---------------------|---------------------|------------------|-------------------|----------------|----------------------|
| Equipe Sul | NACOM | 500 | SIM | TABELA | 0 | FIXA_EXCEDENTE | 200 | 0 | SIM | SIM | NAO | NAO |
| Equipe Norte | NACOM | 450 | NAO | CUSTO_MARKUP | 1000 | PERCENTUAL | 0 | 5 | SIM | SIM | SIM | SIM |

### 2_Transportadoras

| transportadora | cnpj | telefone | chave_pix | banco | cod_banco | agencia | conta |
|----------------|------|----------|-----------|-------|-----------|---------|-------|
| Transportes ABC | 12.345.678/0001-90 | (11) 98765-4321 | 12345678000190 | Banco do Brasil | 001 | 1234 | 56789-0 |
| Frete Rápido | 98.765.432/0001-10 | (21) 97654-3210 | 98765432000110 | Itaú | 341 | 5678 | 12345-6 |

### 3_Empresas

| empresa | cnpj_empresa | chave_pix | banco | cod_banco | agencia | conta | tipo_conta | baixa_compra_auto | saldo |
|---------|--------------|-----------|-------|-----------|---------|-------|------------|------------------|-------|
| Sogima Motos | 11.222.333/0001-44 | 11222333000144 | Bradesco | 237 | 1111 | 22222-3 | FABRICANTE | SIM | 50000 |
| Conta Operacional | 22.333.444/0001-55 | 22333444000155 | Santander | 033 | 2222 | 33333-4 | OPERACIONAL | NAO | 30000 |

### 4_CrossDocking (APENAS 1 LINHA)

| nome | descricao | responsavel_movimentacao | custo_movimentacao | incluir_custo_movimentacao | tipo_precificacao | markup | tipo_comissao | valor_comissao_fixa | percentual_comissao | comissao_rateada | permitir_montagem |
|------|-----------|--------------------------|-------------------|---------------------------|-------------------|--------|---------------|---------------------|---------------------|------------------|-------------------|
| CrossDocking Genérico | Para clientes CrossDocking | RJ | 300 | SIM | TABELA | 0 | FIXA_EXCEDENTE | 150 | 0 | SIM | NAO |

### 5_Custos (APENAS 1 LINHA)

| custo_montagem | custo_movimentacao_devolucao | data_vigencia_inicio |
|----------------|------------------------------|---------------------|
| 150 | 300 | 01/01/2025 |

---

## FASE 2: CADASTROS DEPENDENTES

### 1_Vendedores

| vendedor | equipe_vendas |
|----------|---------------|
| João Silva | Equipe Sul |
| Maria Santos | Equipe Sul |
| Carlos Oliveira | Equipe Norte |
| Ana Costa | Equipe Norte |

### 2_Modelos

| nome_modelo | potencia_motor | autopropelido | preco_tabela | descricao |
|-------------|----------------|---------------|--------------|-----------|
| Voltz EV1 Sport | 2000W | SIM | 8500 | Moto elétrica esportiva |
| Voltz EV1 Cargo | 2000W | NAO | 7800 | Moto elétrica de carga |
| Voltz EV2 Premium | 3000W | SIM | 10500 | Moto elétrica premium |

---

## FASE 3: PRODUTOS E CLIENTES

### 1_Clientes

| cnpj_cliente | cliente | vendedor | crossdocking | endereco_cliente | numero_cliente | bairro_cliente | cidade_cliente | estado_cliente | cep_cliente | telefone_cliente | email_cliente |
|--------------|---------|----------|--------------|------------------|----------------|----------------|----------------|----------------|-------------|------------------|---------------|
| 11.222.333/0001-44 | Empresa XYZ Ltda | João Silva | NAO | Rua ABC | 123 | Centro | São Paulo | SP | 01310-100 | (11) 3456-7890 | contato@xyz.com.br |
| 22.333.444/0001-55 | Comércio 123 ME | Maria Santos | NAO | Av. Principal | 456 | Jardins | São Paulo | SP | 01401-001 | (11) 3456-7891 | vendas@123.com.br |
| 33.444.555/0001-66 | CrossDocking Cliente | Carlos Oliveira | SIM | Rua CD | 789 | Industrial | Guarulhos | SP | 07011-000 | (11) 3456-7892 | cd@cliente.com.br |

### 2_Motos

| numero_chassi | numero_motor | nome_modelo | cor | ano_fabricacao | nf_entrada | data_nf_entrada | data_entrada | fornecedor | custo_aquisicao | status | status_pagamento_custo | empresa_pagadora | observacao | pallet |
|---------------|--------------|-------------|-----|----------------|-----------|----------------|--------------|------------|----------------|--------|----------------------|------------------|------------|--------|
| 9BWZZZ377VT001001 | MOTOR001 | Voltz EV1 Sport | Branco | 2024 | NF-001 | 15/01/2025 | 16/01/2025 | Voltz Motors | 7200 | DISPONIVEL | PENDENTE | Sogima Motos | Moto nova | P-001 |
| 9BWZZZ377VT001002 | MOTOR002 | Voltz EV1 Sport | Preto | 2024 | NF-001 | 15/01/2025 | 16/01/2025 | Voltz Motors | 7200 | DISPONIVEL | PAGO | Sogima Motos | | P-002 |
| 9BWZZZ377VT001003 | MOTOR003 | Voltz EV1 Cargo | Vermelho | 2024 | NF-002 | 20/01/2025 | 21/01/2025 | Voltz Motors | 6500 | DISPONIVEL | PENDENTE | | Aguardando revisão | P-003 |
| 9BWZZZ377VT001004 | MOTOR004 | Voltz EV2 Premium | Azul | 2025 | NF-003 | 25/01/2025 | 26/01/2025 | Voltz Motors | 8800 | DISPONIVEL | PAGO | Conta Operacional | | P-004 |
| 9BWZZZ377VT001005 | | Voltz EV1 Sport | Branco | 2024 | NF-004 | 30/01/2025 | 31/01/2025 | Voltz Motors | 7200 | VENDIDA | PAGO | Sogima Motos | Vendida em Jan/25 | |

---

## 📝 INSTRUÇÕES DE USO

### 1. Copiar Dados para Excel

1. Abaixe os templates da tela de importação
2. Copie os dados das tabelas acima
3. Cole nas abas correspondentes dos templates
4. Salve os arquivos

### 2. Importar no Sistema

1. Acesse: `http://localhost:5000/motochefe/carga-inicial`
2. Fase 1: Upload do arquivo preenchido
3. Aguardar confirmação de sucesso
4. Fase 2: Upload do arquivo preenchido
5. Aguardar confirmação de sucesso
6. Fase 3: Upload do arquivo preenchido
7. Confirmar conclusão

### 3. Validar Dados Importados

```sql
-- Verificar equipes
SELECT * FROM equipe_vendas_moto;

-- Verificar vendedores
SELECT v.*, e.equipe_vendas
FROM vendedor_moto v
JOIN equipe_vendas_moto e ON v.equipe_vendas_id = e.id;

-- Verificar modelos
SELECT * FROM modelo_moto;

-- Verificar clientes
SELECT c.*, v.vendedor
FROM cliente_moto c
JOIN vendedor_moto v ON c.vendedor_id = v.id;

-- Verificar motos
SELECT m.*, mo.nome_modelo
FROM moto m
JOIN modelo_moto mo ON m.modelo_id = mo.id;
```

---

## ✅ RESULTADO ESPERADO

Após importação bem-sucedida:

- ✅ 2 Equipes de Vendas
- ✅ 2 Transportadoras
- ✅ 2 Empresas
- ✅ 1 CrossDocking
- ✅ 1 Custo Operacional
- ✅ 4 Vendedores (2 por equipe)
- ✅ 3 Modelos de Motos
- ✅ 3 Clientes
- ✅ 5 Motos (3 disponíveis, 1 vendida)

**Total:** 23 registros importados

---

## 🔄 TESTES ADICIONAIS

### Teste 1: UPSERT (Re-execução)
1. Importe os dados normalmente
2. Altere o `custo_montagem` de 150 para 200 na Fase 1
3. Re-importe Fase 1
4. **Resultado esperado:** Custo atualizado sem duplicar registros

### Teste 2: Validação de FK
1. Tente importar vendedor com equipe inexistente
2. **Resultado esperado:** Erro informando equipe não encontrada

### Teste 3: Validação de Unicidade
1. Tente importar chassi duplicado
2. **Resultado esperado:** Sistema atualiza moto existente (UPSERT)

### Teste 4: Campo Obrigatório
1. Deixe campo `equipe_vendas` vazio em vendedor
2. **Resultado esperado:** Erro informando campo obrigatório

---

**FIM DOS EXEMPLOS**
