# 12 — Embarcador

> **Fonte**: `visao_geral_embarcador.htm` (06/12/2025)
> **Links internos**: 36 | **Imagens**: 4

## Sumario

Modulo para embarcadores (quem expede mercadorias). Integra embarcador com transportadoras contratadas de forma online. O embarcador calcula o frete e a transportadora usa no CT-e.

---

## Conceito

O SSW expandiu para alem de transportadoras: agora **embarcadores** tambem usam o sistema, integrando processos com transportadoras contratadas.

### Inovacoes
1. **Calculo do frete pelo embarcador** — reutilizado pelas transportadoras no CT-e
2. **Identificacao de volumes** — rastreabilidade ate entrega final
3. **Carregamento digital** — veiculos da transportadora com emissao de manifestos
4. **Integracao online** — rastreamento e financeiro sincronizados
5. **Transportadora propria** — embarcador pode criar/operar sua propria transportadora

---

## Configuracoes

### Unidades (opção 401)

| Tipo de Unidade | Descricao |
|-----------------|-----------|
| **Terceira** | Transportadora contratada. Embarcador nao tem instalacao fisica |
| **Filial** | Transporte operado pelo proprio embarcador |
| **Embarcador** | Onde a expedicao ocorre. Emite o CEE. Inicio da operacao |
| **Alternativa** | Para tipos de mercadoria especificos (transportadoras diferentes por regiao) |

> Unidades sao **virtuais** (sigla 3 caracteres) associadas a transportadoras reais. Nao mudam com troca de transportadora.

### Outras configuracoes

| Opcao | Funcao |
|-------|--------|
| [402](../cadastros/402-cidades-atendidas.md) | Cidades atendidas por unidade |
| [401](../cadastros/401-cadastro-unidades.md) | Associar transportadora a unidade (dominio SSW ou CNPJ) |
| [417](../comercial/417-418-420-tabelas-frete.md) | Tabela Combinada de frete |
| [418](../comercial/417-418-420-tabelas-frete.md) | Tabela Percentual de frete |
| 618 | Aprovacao de tabelas pelas transportadoras |
| [403](../cadastros/403-rotas.md) | Rotas (distancias, prazos, redespacho) |
| [405](../cadastros/405-tabela-ocorrencias.md) | Tabela de ocorrencias |
| [406](../cadastros/406-tipos-mercadorias.md) | Tipos de mercadorias |
| [925](../cadastros/925-cadastro-usuarios.md)/[918](../cadastros/918-cadastro-grupos.md) | Usuarios e autoridades |

> Beneficios plenos so com transportadoras que tambem usam o SSW.

---

## Operacao

### CEE — Controle de Expedicao do Embarcador

- Gerado automaticamente a partir de XML de NF-e
- Identifica transportadora contratada
- Disponibiliza frete calculado para o CT-e da transportadora
- Eliminam-se conferencias de frete e faturas

| Opcao | Funcao |
|-------|--------|
| [105](../comercial/105-agendar-mapa-embarcador.md) | Emissao manual / alteracao do CEE (enquanto nao em Manifesto) |
| [403](../cadastros/403-rotas.md) | Redespacho (troca de transportadora na rota) |

### Identificacao de Volumes
- **SSWBar** gera etiqueta a partir do codigo EAN
- Etiqueta contem numero de rastreamento (codigo de barras + QR Code)
- Mantem-se ate entrega no destinatario

### Carregamento nos Veiculos
- Efetuado com SSWBar
- Manifesto dos CEEs carregados emitido pela [opção 020](../operacional/020-manifesto-carga.md)
- Manifesto = documento formal de passagem da mercadoria a transportadora

### Saida dos Veiculos (opção 025)
- Atualiza site de rastreamento
- Se unidade tem certificado digital → MDF-e das NF-es e emitido

### Consultas
| Opcao | Funcao |
|-------|--------|
| [101](../comercial/101-resultado-ctrc.md) | Consulta do CEE |
| [102](../comercial/102-consulta-ctrc.md) | Consulta a partir do cliente |
| 106 | Performance de entregas (no prazo) |

---

## Fretes a Pagar

| Opcao | Funcao |
|-------|--------|
| [056](../relatorios/056-informacoes-gerenciais.md) | Mapa de pagamentos — relacao de CEEs entregues |
| 963 | Agendamento do processamento do mapa |

> Mapa deve ser enviado ao Contas a Pagar para pagamento das transportadoras.

---

## Fluxo do Embarcador

```
XML NF-e → CEE (automatico) → Identificação volumes (SSWBar)
                                      ↓
                              Carregamento (SSWBar)
                                      ↓
                              Manifesto (020)
                                      ↓
                              Saída veículo (025) + MDF-e
                                      ↓
                              Transportadora opera (CT-e com frete do CEE)
                                      ↓
                              Rastreamento online (ssw.inf.br)
                                      ↓
                              Entrega → Mapa fretes a pagar (056)
```

---

## Contexto CarVia

### Opcoes que CarVia usa
| Opcao | Status | Quem Faz |
|-------|--------|----------|
| — | POTENCIALMENTE UTIL | — |

> CarVia e **transportadora**, nao embarcador. Nao usa o modulo embarcador diretamente, mas o portal pode ser oferecido para clientes CarVia acompanharem entregas.

### Opcoes que CarVia NAO usa (mas deveria)
| Opcao | Funcao | Impacto |
|-------|--------|---------|
| 117 | Monitoracao de embarcadores | Permite clientes acompanharem entregas online |
| 103/104/[105](../comercial/105-agendar-mapa-embarcador.md) | Operacao CEE (emissao, controle, agendamento) | Clientes nao conseguem rastrear entregas sozinhos — tudo manual por telefone/WhatsApp |

### Responsaveis
- **Atual**: Ninguem (modulo nao implantado)
- **Futuro**: Jessica (se implantar portal cliente)
