# Opcao 177 — App Android (SSW Mobile)

> **Modulo**: Comercial
> **Paginas de ajuda**: 2 paginas consolidadas (referencias nas opcoes 152 e 620)
> **Atualizado em**: 2026-02-14

## Funcao
Disponibiliza versoes Android das opcoes 152 (Enderecamento de CTRC no armazem) e 620 (Montagem de diversos paletes e gaiolas) para operacao mobile com tablets/smartphones. Permite operacao de armazenagem e separacao com mobilidade, sem necessidade de microcomputador fixo.

## Quando Usar
- Operar enderecamento de volumes no armazem com mobilidade (opcao 152)
- Realizar separacao de volumes em ate 6 paletes/gaiolas usando dispositivo movel (opcao 620)
- Executar conferencia de armazenagem em campo sem acesso a computador fixo
- Agilizar processo de separacao e carregamento com dispositivo portatil

## Pre-requisitos
- Dispositivo Android (tablet ou smartphone)
- App SSW Mobile instalado via opcao 177
- Leitor de codigo de barras integrado ao dispositivo ou camera do dispositivo
- Conexao com internet (para sincronizacao com servidor SSW)
- Usuarios e permissoes configurados no sistema SSW

## Funcionalidades Disponiveis

### Opcao 152 — Enderecamento de CTRC no Armazem (Android)
| Funcao | Descricao |
|--------|-----------|
| Colocar volume no endereco | Capturar endereco primeiro, depois capturar volume (vincula volume ao endereco) |
| Retirar volume do endereco | Capturar volume diretamente sem capturar endereco (desvincula volume do endereco) |
| Consultar localizacao | Consultar CTRC e seus volumes capturando codigo do CTRC ou do volume |
| Sons de alerta | Sons de alertas podem ser aumentados pela Equipe SSW (JPZ) |

#### Processo de Enderecamento
1. **Identificacao de volumes**: Volumes identificados com codigo de barras pela opcao 011 ou SSWBAR
2. **Identificacao de endereco**: Etiquetas de endereco (opcao 011) com formato:
   - **Unidade**: Identificada automaticamente pelo login do usuario
   - **Rua**: Espaco entre prateleiras/racks/porta-pallets
   - **Numero**: Prateleira, rack, porta-pallet ou espaco vertical
   - **Apto (apartamento)**: Espaco horizontal onde volumes/pallets sao empilhados

3. **Colocacao**: Capturar endereco (habilita local) → Capturar volumes (vincula ao endereco)
4. **Retirada**: Capturar volume diretamente (remove de qualquer endereco)
5. **Saida do CTRC**: Opcoes 025 e 035 apagam automaticamente enderecamentos dos volumes

### Opcao 620 — Montagem de Diversos Paletes e Gaiolas (Android)
| Funcao | Descricao |
|--------|-----------|
| Apontamento de volumes | Separacao de volumes para ate 6 paletes ou gaiolas simultaneos |
| Placa Provisoria | Formato XXX9999 (XXX=sigla unidade destino, 9999=numero sequencial) |
| Limite de carregamento | Alerta atingimento de limites (quantidade, valor, peso) e cria nova Placa Provisoria automaticamente |
| Etiqueta de gaiola/palete | Emitir etiqueta transformando Placa Provisoria em Gaiola/Palete (facilita transbordo) |
| Integracao com Manifesto | Placa Provisoria concluida fica disponivel na opcao 020 para geracao de Manifesto Operacional |

#### Processo de Separacao
1. **Infraestrutura**: Microcomputador com opcao 620 e leitor de codigo de barras (ou Android via opcao 177), ate 6 paletes/gaiolas ao entorno
2. **Configuracao**: Definir limites de carregamento (quantidade volumes, valor mercadoria, peso real) por Placa Provisoria
3. **Separacao**: Capturar volume (NR, codigo cliente, chave DANFE, chave DACTE) → Tela informa qual Placa Provisoria/palete/gaiola colocar volume
4. **Conclusao**: Ao atingir limite ou manualmente, concluir Placa Provisoria (nova e iniciada automaticamente com numeracao sequencial)
5. **Unitizacao**: Opcionalmente, transformar Placa Provisoria em Gaiola/Palete (impressao de etiqueta)
6. **Manifesto**: Placa Provisoria concluida disponivel na opcao 020 (unidade destino do Manifesto pode ser diferente da Placa Provisoria por causa de transbordo)

## Campos / Interface

### App Android (Opcao 177)
| Campo | Descricao |
|-------|-----------|
| Login | Usuario que efetua a operacao |
| Unidade | Unidade onde operacao e realizada |
| Codigo de barras | Campo de captura (endereco, volume, NR, chave DANFE, chave DACTE) |
| Modo | Incluir/Retirar (opcao 152) ou Separacao (opcao 620) |

### Opcao 620 — Tela Principal (Android)
| Campo | Descricao |
|-------|-----------|
| Seq | Sequencia de 1 a 6 identificando separacao de volumes |
| Placa Provisoria | XXX9999 (XXX=unidade destino, 9999=sequencial) |
| Qtde volumes | Limite de volumes por Placa Provisoria (opcional) |
| Mercad (R$) | Limite de valor de mercadoria por Placa Provisoria (opcional) |
| Peso (Kg) | Limite de peso real por Placa Provisoria (opcional) |
| Concluir | Conclui Placa Provisoria atual e inicia nova com numeracao sequencial |
| Etiqueta | Emite etiqueta para transformar Placa Provisoria em gaiola/palete |
| Novo | Configura nova Placa Provisoria (seq 1-6, unidade origem, unidade destino, gaiola opcional) |

## Fluxo de Uso

### Instalacao do App Android
1. Acessar opcao 177 no SSW (navegador)
2. Baixar app SSW Mobile para Android
3. Instalar app no dispositivo movel
4. Configurar acesso ao servidor SSW
5. Fazer login com usuario e senha do SSW

### Enderecamento com Android (Opcao 152)
1. Abrir app SSW Mobile
2. Selecionar funcao de Enderecamento (opcao 152)
3. Colocar volume: Capturar endereco → Capturar volume
4. Retirar volume: Capturar volume diretamente
5. Consultar: Capturar codigo do CTRC ou volume

### Separacao com Android (Opcao 620)
1. Abrir app SSW Mobile
2. Selecionar funcao de Montagem de Paletes/Gaiolas (opcao 620)
3. Configurar limites de carregamento (opcional)
4. Configurar ate 6 Placas Provisorias (Novo: seq, unidade origem, unidade destino, gaiola opcional)
5. Capturar volume → App informa qual Placa Provisoria/palete/gaiola
6. Ao atingir limite ou manualmente, clicar em Concluir
7. Opcionalmente, emitir etiqueta de gaiola/palete
8. Manifestar Placa Provisoria na opcao 020

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 011 | Impressao de etiquetas de volumes e enderecos |
| 019 | Relatorio de CTRCs disponiveis para transferencia (mostra volumes nos enderecos) |
| 020 | Emissao de Manifesto Operacional (recebe Placas Provisorias da opcao 620) |
| 021 | Cadastro de gaiolas |
| 025 | Saida de CTRC da unidade (apaga enderecamentos automaticamente) |
| 035 | Saida de CTRC da unidade (apaga enderecamentos automaticamente) |
| 081 | Relatorio de CTRCs disponiveis para entrega (mostra volumes nos enderecos) |
| 101 | Consulta de localizacao de volumes (mostra enderecos) |
| 388 | Configuracao de mascara de codigo de barras do cliente |
| 903 | Autorizacao e operacao com pre-CTRCs (opcao 620 pode usar pre-CTRCs antes de autorizacao SEFAZ) |
| SSWBAR | Impressao de etiquetas de volumes |

## Observacoes e Gotchas
- **Sons de alerta ajustaveis**: Sons de alertas do app Android podem ser aumentados pela Equipe SSW (JPZ) — solicitar ajuste se necessario
- **Colocar vs Retirar**: Para colocar, capturar endereco primeiro. Para retirar, capturar volume diretamente
- **Segunda captura**: Segunda captura do mesmo endereco desabilita o endereco. Segunda captura do mesmo volume retira-o do endereco
- **Chave NF-e ou CT-e**: Se capturada, todos os volumes respectivos sao considerados (colocar ou retirar)
- **Saida automatica**: Opcoes 025 e 035 apagam automaticamente enderecamentos ao dar saida do CTRC
- **Codigo do cliente**: Mascara cadastrada (opcao 388) e reconhecida pela opcao 620
- **Mais de 6 destinos**: Combinar diversas estacoes para separar mais de 6 destinos simultaneamente
- **Placa Provisoria vs Manifesto**: Unidade destino do Manifesto Operacional pode ser diferente da Placa Provisoria (troca de veiculo em transbordo)
- **Gaiola/Palete facilita transbordo**: Transbordo e realizado com apenas um volume (gaiola/palete unitizada)
- **Pre-CTRCs**: Opcao 620 pode operar com pre-CTRCs antes da autorizacao SEFAZ (configurar na opcao 903)
- **Limites opcionais**: Limites de quantidade, valor e peso sao opcionais — quando atingidos, sistema alerta e permite conclusao automatica da Placa Provisoria
- **Etiqueta de gaiola/palete**: Para emitir, capturar codigo de barras de 2 volumes da separacao desejada
- **Gaiola deve estar cadastrada**: Gaiola deve estar previamente cadastrada na opcao 021 antes de ser usada
- **Sequencia de 1 a 6**: Opcao 620 permite ate 6 Placas Provisorias simultaneas (seq 1 a 6)
