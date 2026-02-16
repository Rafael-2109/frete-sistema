# Opcao 004 — Emissao de CTRCs

> **Modulo**: Operacional — Fiscal / Comercial
> **Paginas de ajuda**: 19 paginas consolidadas
> **Atualizado em**: 2026-02-14
> **NOTA**: Este arquivo e EXTREMAMENTE extenso (69KB). Esta documentacao resume os pontos principais.

## Funcao
Emite CTRCs (Conhecimentos de Transporte), RPSs (transporte municipal), Subcontratos nao fiscais e documentos complementares. E a opcao central para criacao de pre-CTRCs antes do envio ao SEFAZ.

## Quando Usar
- Emitir CT-e para transporte interestadual/intermunicipal
- Emitir RPS para transporte municipal (origem = destino)
- Emitir Subcontrato nao fiscal (legislacao permite)
- Emitir CT-e Complementar (ICMS, Redespacho, outros valores)
- Alterar ou cancelar pre-CTRCs (antes do envio ao SEFAZ)

## Pre-requisitos
- Cliente cadastrado (opcao 483)
- Tabela de frete cadastrada (opcoes 417, 418, etc.) OU frete informado
- Veicul o de coleta cadastrado (opcao 026)
- (Opcional) XML da NF-e importado (opcao 006)
- (Opcional) Etiquetas sequenciais NR1/NR2 para conferencia

## Campos / Interface (Principais)

### Tipo de Documento
- **CT-e**: transporte interestadual/intermunicipal (origem ≠ destino fiscal)
- **RPS**: transporte municipal (origem = destino fiscal) — ISS em vez de ICMS
- **Subcontrato nao fiscal**: operacao permitida por legislacao

### Dados Basicos
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **CNPJ Remetente** | Sim | Quem envia a mercadoria |
| **CNPJ Destinatario** | Sim | Quem recebe a mercadoria |
| **CNPJ Pagador** | Nao | Terceiro que paga o frete (default = remetente CIF / destinatario FOB) |
| **Placa de Coleta** | Sim | Veiculo que coletou (ou ARMAZEM se cliente trouxe) |
| **NR1 / NR2** | Nao | Etiquetas sequenciais para conferencia SSWBar |

### Nota Fiscal
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **Nota Fiscal** | Sim | Numero da NF-e (9 digitos) |
| **Serie** | Nao | Serie da NF-e |
| **Data Emissao** | Sim | Data de emissao da NF-e |
| **Chave NF-e** | Sim (CT-e) | Chave de acesso de 44 digitos |
| **CFOP** | Sim (alguns EDIs) | Codigo fiscal de operacao |
| **Peso (Kg)** | Sim | Peso total da carga |
| **Volume (m3)** | Nao | Cubagem (pode ser calculada via opcao 185) |
| **Qtd Volumes** | Sim | Quantidade de volumes |
| **Valor Mercadoria** | Sim | Valor total da mercadoria |

### Frete
| Campo | Descricao |
|-------|-----------|
| **Tipo** | CIF (remetente paga) ou FOB (destinatario paga) |
| **Frete Peso** | Valor calculado ou informado |
| **Despacho** | Taxa fixa de despacho |
| **Pedagio** | Valor de pedagio |
| **GRIS** | Gerenciamento de risco |
| **TDE / TDC / TAR / TRT / TDA** | Taxas adicionais |
| **ICMS** | Calculado automaticamente ou informado |

## Fluxo de Uso

### Emissao Normal (com Tabela)
1. Acessar opcao 004
2. Informar CNPJ Remetente e Destinatario
3. Sistema busca tabela de frete automaticamente (opcoes 417/418)
4. Informar dados da NF-e (numero, chave, peso, volumes, valor)
5. Informar placa de coleta
6. (Opcional) Informar NR1/NR2 se usar etiquetas sequenciais
7. Sistema calcula frete automaticamente
8. Gravar pre-CTRC
9. Enviar ao SEFAZ (opcao 007) ou imprimir RPS (opcao 009)

### Emissao com Frete Informado
1. Seguir passos 1-6 acima
2. Informar valores de frete manualmente (nao usa tabela)
3. Gravar pre-CTRC
4. Enviar ao SEFAZ (opcao 007)

### Emissao de Subcontrato
1. Escolher tipo "Subcontrato nao fiscal"
2. Informar CNPJ Subcontratante
3. Informar dados da carga
4. Informar se deve "Cobrar Frete" do CTRC origem (FOB a vista)
5. Gravar
6. Imprimir (opcao 008) — NAO envia ao SEFAZ
7. (Opcional) Transformar em fiscal depois (opcao 531)

### Emissao de CT-e Complementar
- **ICMS**: complementar valor de ICMS
- **Redespacho Intermediario**: terceira transportadora na cadeia
- **Outros valores**: adicionar valores ao frete original

### Alterar pre-CTRC (antes do SEFAZ)
1. Acessar opcao 004 (link no rodape "Alterar")
2. Informar numero do CTRC
3. Modificar dados necessarios
4. Gravar

### Cancelar pre-CTRC (antes do SEFAZ)
1. Acessar opcao 004 (link no rodape "Cancelar")
2. Informar numero do CTRC
3. Confirmar cancelamento

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| **002** | Cotacao de frete — usa mesmas tabelas |
| **006** | Importacao XML — gera pre-CTRCs em lote |
| **007** | Envio ao SEFAZ — autoriza CT-es |
| **008** | Impressao Subcontratos nao fiscais |
| **009** | Impressao RPS + geracao NFS-e |
| **011** | Impressao de etiquetas de volumes |
| **020** | Emissao de Manifesto — exige CTRC impresso |
| **061** | Rateio de frete entre CTRCs |
| **084** | Cubagem/pesagem — alimenta dados para emissao |
| **085** | Liquidacao frete origem (Subcontratos) |
| **092** | Alterar "Cobrar Frete" de Subcontrato |
| **115** | Atualizar dados DANFE (NR1/NR2, data, CFOP) |
| **118** | Liberacao para etiquetagem |
| **172** | Unificacao de RPSs provisorios em RPS fiscal |
| **388** | Cadastro clientes — mascara etiqueta, pagador, series NF |
| **401** | Cadastro unidades — inscricao municipal, tipo formulario RPS |
| **402** | Cadastro cidades — aliquota ISS |
| **417/418** | Tabelas de frete |
| **483** | Cadastro clientes — dados basicos |
| **485** | Cadastro transportadoras (redespacho/subcontrato) |
| **531** | Tornar fiscal Subcontratos nao fiscais |
| **SSWBar** | Conferencia eletronica — usa NR1/NR2 |

## Observacoes e Gotchas

### Pre-CTRC vs CTRC Autorizado
- **Pre-CTRC**: criado na opcao 004, ainda NAO tem valor fiscal
- **CTRC Autorizado**: apos opcao 007 (CT-e) ou opcao 009 (RPS), passa a ter valor fiscal
- **Alteracao**: so pode alterar PRE-CTRC (antes do envio ao SEFAZ)
- **Cancelamento**: pre-CTRC = opcao 004; CTRC autorizado = opcao 024 (com restricoes)

### Placa de Coleta
- **Obrigatorio** — DANFEs devem ser carimbadas com a placa
- **ARMAZEM** ou **ARMA999** — usar quando cliente trouxe mercadoria ao armazem
- **Identificacao de volumes**: placa vincula volumes ao CTRC (opcao 011)

### Etiquetas Sequenciais (NR1/NR2)
- **NR1**: primeira etiqueta, grudada na NF-e
- **NR**: etiquetas intermediarias, grudadas nos volumes (qtd = qtd volumes)
- **NR2**: ultima etiqueta, grudada na NF-e
- **Formula validacao**: NR1 + Qtd Volumes + 1 = NR2
- **Conferencia**: SSWBar captura NRs durante descarga e valida sequencia

### Cubagem/Pesagem Obrigatoria
- Configurar em opcao 903/Operacao
- Se ativo, CTRC nao imprime sem cubagem/pesagem (opcao 084 ou opcao 185)

### RPS vs CT-e
- **RPS**: transporte municipal (mesma cidade origem/destino) — tributa ISS
- **CT-e**: transporte intermunicipal/interestadual — tributa ICMS
- **Criterio**: origem do frete = cidade atendida pela transportadora (qualquer unidade) OU cidade expedidora
- **Inscricao Municipal**: necessaria para emitir RPS (opcao 401)

### Subcontrato Nao Fiscal
- **Legislacao**: usar apenas quando permitido por lei
- **Impressao**: opcao 008 (NAO envia ao SEFAZ)
- **Tornar fiscal**: opcao 531 (emite CT-e/RPS capeando o nao fiscal)
- **Cobrar Frete**: se FOB a vista, subcontratada cobra frete do cliente e repassa ao subcontratante (opcao 085)

### Tabela de Frete
- **Busca automatica**: sistema busca tabela por remetente + origem + destino + codigo mercadoria
- **Prioridade**: tabela especifica (com CNPJ) > tabela generica
- **Frete informado**: se nao houver tabela, informar valores manualmente

### Complementar
- **ICMS**: usado quando ICMS original foi calculado errado
- **Redespacho Intermediario**: quando ha 3+ transportadoras na cadeia
- **Outros valores**: adicionar valores ao frete (ex: taxa extra negociada depois)

### CT-e Redespacho Intermediario
- **Limite de volumes**: gera NRs e etiquetas ate 500 volumes (transferencias nao conferem volumes)

### Fatura/Bloqueto na Expedicao
- **Condicoes**: CTRC impresso + cliente com credito banco/carteira + periodicidade diaria + gera fatura/bloqueto = S (opcao 401)
- **Impressao automatica**: apos opcao 007, sistema pergunta se quer imprimir fatura/bloqueto
- **Reimpressao**: opcao 017

### Numero de Controle
- **Obrigatorio**: numero fisico do formulario (grafica) = numero impresso no DACTE
- **Livro Fiscal**: numero correto e essencial para Livro Fiscal e Sintegra

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
| [POP-A04](../pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas |
| [POP-A08](../pops/POP-A08-cadastrar-veiculo.md) | Cadastrar veiculo |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-B03](../pops/POP-B03-parametros-frete.md) | Parametros frete |
| [POP-C01](../pops/POP-C01-emitir-cte-fracionado.md) | Emitir cte fracionado |
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
| [POP-C03](../pops/POP-C03-emitir-cte-complementar.md) | Emitir cte complementar |
| [POP-C06](../pops/POP-C06-cancelar-cte.md) | Cancelar cte |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
