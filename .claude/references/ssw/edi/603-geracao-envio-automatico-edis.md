# Opção 603 — Geração e Envio Automático de EDIs

> **Módulo**: EDI
> **Páginas de ajuda**: 17 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Parametriza a geração e envio automático de EDIs (Eletronic Data Interchange) para clientes, permitindo automação completa do processo de troca de informações.

## Quando Usar
- Para configurar envio automático de arquivos EMBARCADOS, COBRANÇA e OCORRÊNCIAS
- Para definir periodicidade e critérios de geração de EDIs
- Para automatizar integração eletrônica com clientes

## Pré-requisitos
- Ajuste de lay-out pela Equipe SSW (programas desenvolvidos conforme especificação do cliente)
- CNPJ do cliente cadastrado

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ completo ou corpo do CNPJ | Sim | 14 dígitos (completo) ou 8 dígitos (raiz) |
| Seleção - Cliente | Sim | Emitente ou pagador |
| Seleção - Classificação | Sim | Número do CTRC ou formulário fiscal |
| Seleção - Tipos de CTRCs | Sim | Tipos de documentos a incluir |
| Periodicidade | Sim | Horários e dias da semana, dias do mês, ou após faturamento |
| Nome do arquivo | Sim | Nome livre + data/hora + extensão |
| Emails | Sim | Emails destino separados por ponto-e-vírgula |
| Observações | Não | Texto interno sobre processo de geração e envio |
| Último envio | Informativo | Datas dos últimos envios |

## Fluxo de Uso

### Configuração Inicial
1. Solicitar à Equipe SSW ajuste de lay-out conforme especificação do cliente
2. Acessar opção 603
3. Informar CNPJ completo (14 dígitos) ou raiz (8 dígitos)
4. Definir critérios de seleção (cliente, classificação, tipos de CTRCs)
5. Configurar periodicidade de geração
6. Definir nome do arquivo
7. Cadastrar emails destino
8. Incluir observações relevantes
9. Confirmar configuração

### Estabilização do Envio
1. Cadastrar email da transportadora além do cliente (para acompanhamento)
2. Verificar opção 604 diariamente para confirmar sucesso
3. Após confirmar funcionamento, retirar email da transportadora

### Operação
- Arquivos gerados automaticamente nos horários/dias configurados
- Acompanhar situação via opção 604
- Arquivos não enviados devem ser processados manualmente

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 600 | Geração manual de arquivos EDI (alternativa ao automático) |
| 604 | Situação dos arquivos EDIs gerados/enviados automaticamente |
| 602 | Relaciona arquivos EDIs processados no período |
| 101 | Link "Arquivos EDI" permite verificar status dos envios |
| 006 | Geração de CTRCs em lotes (usa arquivos NOTFIS recebidos via EDI) |
| 071 | Consultar e alterar NF-es/CT-es antes de gerar CTRCs |

## Tipos de Arquivos Gerados

### EMBARCADOS
Informações de CTRCs gerados.

### COBRANÇA
Informações de faturas geradas.

### OCORRÊNCIAS
Informações de ocorrências de CTRCs.

## Observações e Gotchas

### Escolha de Critérios
- **Prioridade CNPJ completo**: Sistema tenta primeiro localizar por 14 dígitos
- **Fallback para raiz**: Se não encontrar, usa 8 primeiros dígitos (corpo do CNPJ)
- **Benefício da raiz**: Todas as empresas do grupo usam mesmos critérios

### Periodicidade
- **Horários e dias da semana**: Define geração em horários específicos
- **Dias do mês**: Define dias do mês para geração
- **Após faturamento**: Gera quando faturamento ocorrer (processamento às 00:00h)
- **Arquivos diários**: Devem ter horário 00:00h marcado

### Formato de Arquivo
- **Quebra de linha**: Todos os arquivos são gerados com quebra de linha no final dos registros
- **Download e email**: Formato mantido em ambos os casos
- **Tratamento diferente**: Contatar Equipe SSW se necessário

### Clientes sem Email
- Efetuar download do arquivo pela opção 604
- Salvar em pasta do micro
- Enviar manualmente ao cliente conforme exigido

### Acompanhamento Diário
- Verificar opção 604 diariamente
- Arquivos não enviados: enviar manualmente
- Observação "SEM MOVIMENTO": Nenhum registro encontrado para geração

### Processo Completo
1. **Ajuste do lay-out**: Equipe SSW desenvolve programa conforme especificação do cliente
2. **Parametrização**: Opção 603 define critérios de geração e envio por CNPJ
3. **Situação**: Opção 604 mostra arquivos gerados/enviados
4. **Histórico**: Opção 602 relaciona arquivos processados
5. **Status**: Opção 101 (link Arquivos EDI) mostra status de envios

### Métodos de Envio
- **Email**: Configurado diretamente na opção 603
- **FTP/SFTP**: Dados de acesso configurados na opção 603
- **Web Service**: URL, usuário e senha configurados na opção 603

### Programas EDI Específicos
Diversos programas especializados por cliente (exemplos incluídos na documentação):
- Whirpool (ssw0778, ssw1951, ssw2066, ssw2092, ssw2911, ssw3135)
- Intelipost (ssw1990)
- Multilaser (ssw3056)
- Total Biotecnologia (ssw3191)
- Dafiti - Consumo CO2 (ssw3305)
- Grupo Boticário (ssw3307, ssw3377)
- Calçados Beira Rio (ssw3432)
- Grendene - Reforma Tributária (ssw3468)

Cada programa atende layout específico do cliente e pode incluir múltiplas funções (recepção NOTFIS, envio de embarcados, cobrança, ocorrências, comprovantes, etc.)
