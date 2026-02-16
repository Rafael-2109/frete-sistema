# Opção 600 — EDI (Integração Eletrônica)

> **Módulo**: EDI
> **Páginas de ajuda**: 87 páginas consolidadas (217KB)
> **Atualizado em**: 2026-02-14

## Função
Concentra TODOS os programas que fazem importação e geração (envio) de arquivos EDI de clientes. É o hub central para todas as integrações eletrônicas no SSW.

## Quando Usar
- Para receber arquivos NOTFIS de clientes via EDI
- Para gerar e enviar arquivos EMBARCADOS, COBRANÇA e OCORRÊNCIAS
- Para importar XMLs de NF-es do Portal Nacional
- Para integração entre transportadoras que usam SSW

## Pré-requisitos
- Programas de importação/exportação ajustados pela Equipe SSW
- CNPJ do cliente cadastrado
- Arquivo recebido ou disponível para geração

## Tipos de EDI Disponíveis

### EDI — NOTFIS (Recepção de Notas Fiscais)
- **Layout padrão**: PROCEDA NOTFIS (versão 3.0A - Ano 2000)
- **Função**: Receber informações de NF-es para geração de CTRCs
- **Registros obrigatórios**: 000 (HEADER), 310 (UNH), 311 (Embarcadora), 312 (Destinatário), 313 (Nota Fiscal), 318 (Valor Total)
- **Formatos**: Alfanumérico (A) maiúsculo, Numérico (N)
- **Status**: M (obrigatório), C (condicional)
- **Limitações**: Peso real max 99999,999 Kg, cubagem max 999,9999 m³

### EDI — Layouts Específicos por Cliente
Múltiplos layouts personalizados desenvolvidos pela Equipe SSW:
- **PROCEDA**: Padrão mais comum (maioria dos clientes)
- **Intelipost**: Padrão, Reversa e Devolução
- **Whirpool**: CONEMB, DOCCOB, OCORREN
- **Multilaser**: Notas despachadas
- **Total Biotecnologia**: Check list de faturas pendentes
- **Dafiti**: Consumo de CO2
- **Grupo Boticário**: Ocorrências para auditoria
- **Calçados Beira Rio**: NOTFIS com agrupamento definido
- **Grendene**: NOTFIS com Reforma Tributária
- E muitos outros...

### EDI — EMBARCADOS
- **Função**: Gerar arquivo com informações de CTRCs gerados
- **Uso**: Enviar ao cliente informações sobre documentos emitidos
- **Periodicidade**: Configurável (diário, semanal, após faturamento, etc.)

### EDI — COBRANÇA
- **Função**: Gerar arquivo com informações de faturas geradas
- **Uso**: Integração financeira com cliente
- **Formatos**: CSV, TXT, XML (conforme layout do cliente)

### EDI — OCORRÊNCIAS
- **Função**: Gerar arquivo com ocorrências de CTRCs
- **Uso**: Rastreamento e visibilidade para cliente
- **Atualização**: Pode ser automática ou sob demanda

### EDI — Arquivos Especiais
- **Romaneio de Entregas**: Via Web Service
- **Comprovantes de Entrega**: Via Web Service ou FTP/SFTP
- **Relatórios de Auditoria**: Conforme padrão do cliente
- **Pré-faturas**: Importação de dados do cliente

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Cliente (CNPJ) | Sim | CNPJ do cliente (pode pesquisar por nome via link) |
| Envia Arquivo / Recebe Arquivo | Sim | Selecionar operação desejada (rodapé) |
| Nome do arquivo | Condicional | Para recepção: caminho completo do arquivo |
| Pasta destino | Condicional | Para geração: onde salvar arquivo gerado |
| Período | Condicional | Para geração: período dos dados a incluir |

## Fluxo de Uso

### Recepção de Arquivos NOTFIS
1. Cliente envia arquivo NOTFIS (via email, FTP, SFTP ou portal)
2. Salvar arquivo em pasta do micro (ou recepção automática via opção 603)
3. Acessar opção 600
4. Informar CNPJ do cliente
5. Clicar em "RECEBE ARQUIVO"
6. Informar nome/caminho do arquivo
7. Sistema importa e mostra quantidades (NFs lidas vs. incluídas)
8. Se quantidades diferentes: verificar arquivo (item "Como Recuperar Arquivo Danificado" abaixo)
9. NF-es importadas ficam disponíveis na opção 071 para correção
10. Gerar CTRCs pela opção 006

### Geração de Arquivos (EMBARCADOS / COBRANÇA / OCORRÊNCIAS)
1. Acessar opção 600
2. Informar CNPJ do cliente
3. Clicar em "ENVIA ARQUIVO"
4. Selecionar tipo de arquivo (EMBARCADOS, COBRANÇA ou OCORRÊNCIAS)
5. Definir período (se aplicável)
6. Informar pasta destino
7. Sistema gera arquivo na pasta indicada
8. Enviar arquivo ao cliente (ou usar opção 603 para envio automático)

### Geração Automática (Recomendado)
Em vez de geração manual pela opção 600, configurar opção 603 para:
- Geração automática em horários/dias definidos
- Envio automático via email ou FTP/SFTP
- Acompanhamento via opção 604

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 006 | Geração de CTRCs em lotes (usa NF-es importadas pela opção 600) |
| 071 | Consultar e alterar NF-es/CT-es importadas |
| 603 | Geração e envio automático de EDIs (alternativa automatizada) |
| 604 | Situação dos arquivos EDIs gerados/enviados automaticamente |
| 602 | Histórico de arquivos EDIs processados |
| 101 | Link "Arquivos EDI" mostra status de envios |
| 608 | Importação de XMLs gravados em pasta do micro |
| 102 | Histórico das gerações de arquivos (subopção EDI) |

## Observações e Gotchas

### Recuperação de Arquivo Danificado
Se arquivo recebido está danificado:
1. Abrir com editor de texto (EDIT, WRITE, WORDPAD, etc.)
2. Localizar campos deslocados (endereço, CEP, CNPJ, etc.)
3. Remover caracteres especiais (-, /, *, cedilhas, acentos)
4. Verificar que todos os campos têm mesmo formato e posição
5. Usar especificação do cliente para conferir lay-out
6. Salvar arquivo com correções
7. Tentar reimportar

### Registros Obrigatórios PROCEDA NOTFIS
- **000**: HEADER
- **310**: HEADER
- **311**: DADOS DA TRANSPORTADORA
- **312**: DADOS DO DESTINATARIO
- **313**: DADOS DA NOTA FISCAL
- **318**: VALOR TOTAL DO ARQUIVO (último campo)

### Atualização de Cadastro
EDI atualiza cadastro do cliente conforme configuração (item da Ajuda da opção 483).

### Valores Máximos
- Peso real: 99999,999 Kg
- Cubagem: 999,9999 m³

### Apagamento de NFs
NF-es importadas são apagadas da opção 071 em 10 dias (geradoras de CTRCs ou não).

### Histórico
- **Opção 102** (subopção EDI): Histórico das gerações de arquivos
- Link "OCORRÊNCIAS": Acesso direto às ocorrências

### Processo Recomendado
Para RECEPÇÃO:
1. Ajuste de programas pela Equipe SSW
2. Recepção de arquivos (manual ou automática via opção 603)
3. Importação pela opção 600
4. Correção pela opção 071 (se necessário)
5. Geração de CTRCs pela opção 006

Para ENVIO:
1. Ajuste de programas pela Equipe SSW
2. Configuração da opção 603 (geração e envio automático)
3. Acompanhamento via opção 604
4. Ou geração manual pela opção 600 quando necessário

### Benefícios da Automação (Opção 603)
- Geração em horários definidos
- Envio automático via email/FTP/SFTP/Web Service
- Acompanhamento via opção 604
- Redução de erros manuais
- Maior agilidade no processo

### Métodos de Recepção/Envio
- **Email**: Recepção via xml@ssw.inf.br ou envio automático
- **FTP/SFTP**: Configuração de acesso na opção 603
- **Web Service**: URL, usuário e senha na opção 603
- **Portal Nacional NF-e**: Busca automática de XMLs
- **Manual**: Opção 608 para importar XMLs de pasta local

### Observação Importante
Esta opção 600 é extremamente extensa (87 páginas de documentação, 217KB). Cada cliente pode ter layout específico com regras próprias. Para detalhes de layout específico de cliente, consultar documentação do programa EDI correspondente ou contatar Equipe SSW EDI (edi@ssw.inf.br).
