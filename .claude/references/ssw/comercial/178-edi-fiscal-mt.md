# Opcao 178 — Geracao de Arquivo EDI Fiscal MT

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Gera arquivo Convenio EDI Fiscal versao 3.00 para transmissao ao portal da SEFAZ-MT. Arquivo consolida dados de MDF-es com CT-es de destino final MT e CT-es de passagem por MT. Permite complementacao de dados das NF-es dos CTRCs (chaves de acesso, CFOP, data de emissao, IE do Substituto Tributario) via opcao 115.

## Quando Usar
- Gerar arquivo EDI Fiscal MT obrigatorio para circulacao de mercadorias no Mato Grosso
- Transmitir dados de MDF-es com CT-es destino MT e/ou CT-es de passagem
- Retransmitir arquivo gerado anteriormente (em caso de erro ou solicitacao da SEFAZ)
- Complementar dados fiscais das NF-es dos CTRCs para atender exigencias do EDI Fiscal MT

## Pre-requisitos
- Unidade conveniada com a SEFAZ-MT (cadastro na opcao 401)
- MDF-es emitidos separando CT-es destino final MT e CT-es destino outras UFs
- Manifestos Operacionais correspondentes aos MDF-es
- Dados complementares das NF-es (chaves de acesso, CFOP, data de emissao, IE Substituto Tributario) inseridos via opcao 115, se necessario
- Acesso ao portal da SEFAZ-MT para transmissao do arquivo

## Campos / Interface

### Tela Principal
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Unidade autorizada | Sim | Unidade (opcao 401) conveniada com a SEFAZ-MT. Abre nova tela para informar Manifestos Operacionais |
| Retransmitir carga numero | Nao | Disponibiliza arquivo gerado anteriormente (informar numero da carga) |
| Numero da ultima carga gerada | Informativo | Numero do ultimo arquivo EDI Fiscal MT gerado |

### Tela de Selecao de Manifestos
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Manifestos Operacionais | Sim | Informar TODOS os Manifestos Operacionais dos MDF-es que se destinam ao MT e os que passarao por la (de passagem) |

### Dados Complementares (Opcao 115)
| Campo | Descricao |
|-------|-----------|
| Chaves-de-acesso NF-e | Chaves de acesso das Notas Fiscais dos CTRCs |
| CFOP | Codigo Fiscal de Operacoes e Prestacoes |
| Data de emissao | Data de emissao das Notas Fiscais |
| IE do Substituto Tributario | Inscricao Estadual do destinatario de outra UF que recebe mercadoria no MT (no substituto) |

## Fluxo de Uso

### Geracao de Arquivo EDI Fiscal MT
1. Emitir MDF-es separando CT-es destino final MT e CT-es destino outras UFs (passagem)
2. Complementar dados das NF-es via opcao 115 (chaves de acesso, CFOP, data de emissao, IE Substituto Tributario)
3. Acessar opcao 178
4. Selecionar unidade autorizada conveniada com SEFAZ-MT
5. Informar TODOS os Manifestos Operacionais dos MDF-es (destino MT e passagem)
6. Gerar arquivo EDI Fiscal MT (formato Convenio EDI Fiscal versao 3.00)
7. Baixar arquivo gerado
8. Transmitir arquivo ao portal da SEFAZ-MT
9. Aguardar processamento e validacao pela SEFAZ

### Retransmissao de Arquivo
1. Acessar opcao 178
2. Informar numero da carga em "Retransmitir carga numero"
3. Baixar arquivo gerado anteriormente
4. Transmitir novamente ao portal da SEFAZ-MT

### Complementacao de Dados das NF-es (Opcao 115)
1. Acessar opcao 115
2. Localizar CTRCs com NF-es a complementar
3. Informar chaves de acesso NF-e, CFOP, data de emissao, IE Substituto Tributario
4. Salvar dados complementares
5. Gerar arquivo EDI Fiscal MT pela opcao 178

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 115 | Complementacao de dados das NF-es dos CTRCs (chaves de acesso, CFOP, data de emissao, IE Substituto Tributario) |
| 401 | Cadastro de unidades (define unidades conveniadas com SEFAZ-MT) |
| MDF-e | Manifestos Eletronicos de Documentos Fiscais (fonte de dados para arquivo EDI) |
| Manifestos Operacionais | Identificam cargas a serem incluidas no arquivo EDI |
| SSWBar 2 | Descarga de Manifestos de outras unidades (informar cavalo e Manifesto) |

## Observacoes e Gotchas
- **Separacao obrigatoria de MDF-es**: MDF-es devem ser emitidos separando CT-es destino final MT e CT-es destino outras UFs (passagem). Sistema NAO aceita os 2 tipos de CT-es no mesmo MDF-e
- **CT-es de passagem**: Se veiculo tem destino MT, CT-es de passagem devem ser manifestados diretamente para unidade fora do MT (nao misturar com CT-es destino MT no mesmo MDF-e)
- **Informar TODOS os Manifestos**: Na geracao do arquivo, informar TODOS os Manifestos Operacionais do MDF-e (tanto destino MT quanto passagem)
- **Dados complementares opcionais**: Dados da opcao 115 normalmente nao sao necessarios no CTRC, mas sao utilizados no arquivo EDI Fiscal MT para atender exigencias da SEFAZ
- **IE do Substituto Tributario**: Campo especifico para destinatario de outra UF que recebe mercadoria no MT (regime de substituicao tributaria)
- **Lay-out do arquivo**: Convenio EDI Fiscal versao 3.00 — consultar documentacao SEFAZ-MT para detalhes do formato
- **Editar arquivo**: Se necessario editar arquivo, utilizar NOTEPAD++ (nao usar Bloco de Notas padrao)
- **SSWBar 2 para descarga**: Para descargas de Manifestos de outras unidades, utilizar SSWBar 2 (informar cavalo e Manifesto)
- **Retransmissao**: Funcao de retransmissao permite reenviar arquivo sem necessidade de regerar (util em caso de erro na primeira transmissao)
- **Numero da ultima carga**: Sistema exibe numero da ultima carga gerada para referencia e controle
- **Transmissao obrigatoria**: Apos geracao, arquivo DEVE ser transmitido ao portal da SEFAZ-MT para circulacao legal de mercadorias no estado
- **Convenio com SEFAZ**: Unidade deve estar previamente conveniada com SEFAZ-MT (cadastro na opcao 401) para gerar arquivo EDI Fiscal
