# Opcao 487 — Tabela TDE Externa

> **Modulo**: Financeiro
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Cadastro de TDE (Taxa de Dificuldade de Entrega) por combinacao remetente/destinatario, complementar as tabelas de frete internas dos clientes.

## Quando Usar
- Cadastrar TDE especifico para combinacao remetente/destinatario
- Definir entrega dificil para cliente especifico
- Configurar taxa adicional para destinos de dificil acesso
- Complementar TDEs ja cadastrados nas tabelas de frete (opcoes 417, 418)
- Gerar relatorio de clientes com TDE (opcao 473)

## Pre-requisitos
- CNPJ/CPF do remetente cadastrado (opcao 483)
- CNPJ/CPF do destinatario cadastrado (opcao 483)
- Valor de TDE definido

## Campos / Interface

### Cadastro de TDE
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ remetente | Sim | CNPJ/CPF do remetente |
| CNPJ destinatario | Sim | CNPJ/CPF do destinatario |
| Valor TDE | Sim | Valor da taxa de dificuldade de entrega |
| Percentual TDE | Condicional | Percentual sobre valor do frete (alternativa a valor fixo) |

## Fluxo de Uso

### Cadastrar TDE por Remetente/Destinatario
1. Acessar opcao 487
2. Informar CNPJ remetente
3. Informar CNPJ destinatario
4. Definir valor ou percentual de TDE
5. Gravar cadastro

### Gerar Relatorio de Clientes com TDE (Opcao 473)
1. Acessar opcao 473
2. Selecionar filtros:
   - Raiz CNPJ (8 numeros - pagador ou destinatario)
   - Unidade responsavel (opcao 483)
   - Filtros adicionais (praca, UF, cidade)
3. Escolher relatorio:
   - **Tabelas de fretes com TDE**: TDEs cadastradas nas tabelas de frete (opcoes 417, 418)
   - **Valor TDE**: Tabelas TDE cadastradas pela opcao 487 (pode enviar por e-mail)
   - **Clientes com prazo adicional para Entrega Dificil**: prazos cadastrados pela opcao 698
   - **Destinatarios Entrega Dificil e servicos adicionais**: combina opcoes 483, 394, 487
4. Gerar relatorio (PDF ou Excel)
5. Enviar por e-mail (opcional)

### Disponibilizar TDE no Site da Transportadora
1. Cadastrar TDEs pela opcao 487
2. Disponibilizar link no site:
   - **HTML**: https://ssw.inf.br/2/tde?s=XXX&output=html
   - **PDF**: https://ssw.inf.br/2/tde?s=XXX#
3. Substituir XXX pelo dominio da transportadora

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 394 | Raiz do CNPJ - marca entrega dificil por raiz |
| 417, 418 | Tabelas de frete - TDE cadastrado internamente nas tabelas |
| 473 | Relacao de clientes com TDE - gera relatorios combinando opcoes 487, 417, 418, 394, 483, 698 |
| 483 | Cadastro de clientes - marca entrega dificil por CNPJ, define servicos adicionais |
| 698 | Prazo adicional para Entrega Dificil - define prazo adicional |

## Observacoes e Gotchas

### Duas Formas de Cadastrar TDE
1. **Tabela de frete interna** (opcoes 417, 418): TDE cadastrado na propria tabela do cliente
2. **Tabela TDE externa** (opcao 487): combina remetente + destinatario para definir TDE

### Relatorio 473 - Combinacao
- Lista TDEs de **ambas** as formas (tabela interna + externa)
- Filtros disponiveis: raiz CNPJ, unidade responsavel, praca, UF, cidade
- Opcoes de saida: PDF ou Excel
- Envio por e-mail disponivel

### Raiz CNPJ (Opcao 394)
- 8 primeiros numeros do CNPJ
- Identifica empresa com todas as suas filiais
- Pode ser pagador ou destinatario
- Marca entrega dificil para toda a raiz (todas as filiais)

### Entrega Dificil - Multiplas Origens
- **CNPJ individual** (opcao 483): marca entrega dificil por CNPJ especifico
- **Raiz CNPJ** (opcao 394): marca entrega dificil para toda a raiz (todas as filiais)
- **Destinatarios** (opcao 487): marca entrega dificil por combinacao remetente/destinatario

### Servicos Adicionais (Opcao 483)
- Agendamento
- Paletizacao
- Separacao
- Outros servicos especificos
- Listados no relatorio "Destinatarios Entrega Dificil e servicos adicionais"

### Prazo Adicional (Opcao 698)
- Define prazo adicional para entrega dificil
- Listado em relatorio separado na opcao 473
- Complementa TDE com prazo estendido

### Links Publicos para Site
- **HTML**: exibicao direta no navegador
- **PDF**: download em PDF
- Formato: https://ssw.inf.br/2/tde?s=DOMINIO&output=html (ou #pdf)
- Dominio = sigla/codigo da transportadora no SSW
- Listam clientes destinatarios por cidade com entrega dificil

### Aplicacao de TDE
- TDE aplicado automaticamente no calculo de frete
- Baseado em remetente + destinatario (opcao 487)
- Ou baseado em tabela de frete do cliente (opcoes 417, 418)
- Ou baseado em marca de entrega dificil (opcoes 394, 483)

### Valor vs Percentual
- **Valor fixo**: taxa fixa aplicada por entrega
- **Percentual**: percentual sobre valor do frete
- Sistema escolhe qual aplicar baseado no cadastro

### Excel e E-mail
- Relatorio 473 permite exportacao para Excel
- Envio por e-mail disponivel para facilitar comunicacao com clientes
- Util para divulgar clientes com TDE ou entrega dificil

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
