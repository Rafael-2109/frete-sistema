# Opção 071 — Notas Fiscais Importadas via EDI (Contratação de Veículos)

> **Módulo**: Operacional — Importação e Geração de CTRCs
> **Páginas de ajuda**: 38 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Armazena e gerencia Notas Fiscais importadas via EDI de diversos clientes, permitindo alteração, consulta e preparação para geração de CTRCs em lote pela opção 006.

## Quando Usar
- Consultar Notas Fiscais recebidas via EDI antes de gerar CTRCs
- Alterar dados de Notas Fiscais importadas (placa, mercadoria, expedidor, etc.)
- Verificar status de importação de arquivos EDI
- Configurar processos específicos de clientes (DAFITI, PROCEDA, Magazine Luiza, etc.)

## Pré-requisitos
- EDI configurado na opção 600 e opção 603
- Cliente remetente cadastrado na opção 483
- Programas de importação SSW configurados (ssw2703, ssw1341, ssw1726, ssw1769, etc.)

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Período de importação | Sim | Período em que NF-es foram importadas no SSW via EDI |
| CNPJ remetente/pagador | Não | Filtro por responsável pelos dados do EDI |
| Placa da coleta | Não | Filtro por placa informada na importação |
| Código de mercadoria | Não | Filtro por tipo de mercadoria |
| Código de espécie | Não | Filtro por espécie da mercadoria |
| Conferente | Não | Filtro por conferente associado |
| Tabela Genérica | Não | Permite uso de tabela genérica de fretes |
| Carregar em placa provisória | Não | CTRCs gerados ficam apontados na placa (opção 020) |
| CNPJ expedidor | Não | Expedidor a ser atribuído nos CTRCs |
| CNPJ recebedor | Não | Recebedor a ser atribuído nos CTRCs, permite agrupamento |

## Integrações com Clientes Específicos

### DAFITI / CFG (CNPJ raiz: 11200418)
- **Recebe**: ssw2703 (via Webhook SSW com token gerado em ssw2173) ou ssw2353 (via e-mail/FTP/SFTP)
- **Envia**: ssw1953 F1 (ocorrências WS), ssw1953 F2 (ocorrências coleta WS), ssw1329 F4 (XMLs CT-es via SFTP), ssw3305 (consumo CO2 CSV)
- **Processo**: Emissões exclusivas via opção 006, usar código de mercadoria para negociações comerciais
- **Configuração**: Usar opções 609 (unitização), processos 51369/52380/52396 (opção 811)

### PROCEDA 5.0 (diversos embarcadores)
- **Recebe**: ssw1341 F4 (NOTFIS), ssw1341 F17 (NOTFIS devolução)
- **Envia**: ssw1341 F1 (CONEMB período), F2 (OCOREN período), F3 (DOCCOB), F5 (CONEMB fatura), F6 (OCOREN fatura), F8 (OCOREN coleta), F9/F10/F11/F12/F13/F14/F15/F16/F18 (variações)
- **Processo**: Importação via FTP/SFTP/e-mail/A3, emissão via opção 006, tabela ocorrências na opção 908

### Magazine Luiza / Magalu Log (CNPJ raiz: 47960950, 24230747)
- **Recebe**: ssw2185 (API com token fixo SSW)
- **Envia**: ssw1668 F1 (ocorrências exceto entrega), ssw1668 F2 (somente ocorrência entrega), ssw2825 (CSV fatura), ssw3310 (CSV a faturar)
- **Processo**: Gerar CTRCs via opção 006, ocorrências enviadas automaticamente

### XML CT-e Padrão (diversos embarcadores)
- **Recebe**: ssw1726 (XML individual ou ZIP), configuração via opção 603 (FTP/SFTP/A3), NOTFIS por e-mail notfis.XXX@ssw.inf.br
- **Processo**: Importar via opção 600 (informar Sigla Subcontratante da opção 485), compactar múltiplos arquivos com Winzip

### PROCEDA 3.0 A (diversos embarcadores)
- **Recebe**: ssw1769 F6 (NOTFIS), F7 (NOTFIS coleta reversa), F8 (NOTFIS redespacho intermediário)
- **Envia**: ssw1769 F1-F5, F9-F14 (CONEMB, OCOREN, DOCCOB em variações)
- **Processo**: Similar ao PROCEDA 5.0

## Fluxo de Uso
1. Cliente envia arquivo EDI (FTP/SFTP/e-mail/API/Webhook)
2. Programa SSW específico processa arquivo e grava na opção 071
3. Usuário acessa opção 071 para consultar/alterar NF-es importadas
4. Usuário acessa opção 006 para gerar CTRCs em lote
5. Sistema valida dados, gera pré-CTRCs e envia ao SEFAZ
6. Ocorrências enviadas automaticamente ao cliente via EDI configurado

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 006 | Geração de CTRCs em lote a partir de NF-es importadas |
| 600 | Programas de importação/exportação EDI |
| 603 | Configuração automática de envio/recebimento EDI |
| 608 | Recebe XML NF-e/CT-e via arquivo ou chave |
| 602 | Relaciona arquivos EDIs processados |
| 101 | Link "Arquivos EDI" mostra status dos envios |
| 908 | Tabela de ocorrências padrão embarcador (DExPARA) |
| 483 | Cadastro de clientes remetentes |
| 485 | Cadastro de subcontratantes |
| 381 | Configurações específicas de cliente |
| 388 | Configurações adicionais de cliente |

## Observações e Gotchas
- **Recebimento por e-mail**: Enviar para notfis.XXX@ssw.inf.br (XXX = domínio transportadora), limite 30MB, cliente deve estar cadastrado como EDI na opção 603
- **Múltiplos arquivos**: Compactar com Winzip antes de importar
- **Token SSW**: Gerado via opção 2173 para APIs/Webhooks, liberado ao CNPJ cliente, domínio cria usuário/senha (opção 925)
- **Automatização**: Opção 603 permite configurar recebimento/envio automático via FTP/SFTP/e-mail/A3
- **Retroativo**: Transportadora pode parametrizar envio retroativo até 30 dias (opção 603, campo "último processamento")
- **Alterações**: NF-es importadas podem ser alteradas antes de gerar CTRCs
- **Consolidador EDI**: Campo gravado pelo EDI define agrupamento automático de NF-es (disponível para N-Normal, H-Redespacho, G-Redespacho Intermediário)
- **Unitização**: Configurada pela opção 609, reconhecida pela opção 006, EDI atualiza parâmetros via opção 071
- **Chave NF-e**: Sistema verifica online se NF-es estão canceladas (lotes até 100 NF-es)
- **Duplicidade**: Opção 903/Operação configura dias que NF não pode ser reutilizada
- **XMLs de outros sistemas**: Importar via opção 006/X, séries devem ser diferentes das cadastradas (opção 920), dados fiscais devem coincidir
- **Processos específicos**: ssw1329, ssw1341, ssw1668, ssw1726, ssw1769, ssw1888, ssw1926, ssw2185, ssw2353, ssw2703, ssw2825, ssw3305, ssw3310, ssw3509

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
