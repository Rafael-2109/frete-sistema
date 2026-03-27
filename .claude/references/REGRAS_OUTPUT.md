# Regras de Qualidade de Output do Agente

**Ultima Atualizacao**: 26/03/2026

Regras complementares de formatacao e linguagem para o agente web.
Regras criticas de seguranca operacional (I2-I4) permanecem inline no `system_prompt.md`.

---

## I1: Distinguir Pedidos vs Clientes

Ao reportar resultados de busca, separar contagens:
- ERRADO: "6 clientes encontrados"
- CORRETO: "6 pedidos de 5 clientes (Consuma com 2 pedidos)"

---

## I5: Linguagem Operacional

**Use linguagem natural — operador nao conhece codigos internos (P1-P7, FOB, RED, etc.)**

Traduza para linguagem clara:

| Interno | Diga ao usuario |
|---------|-----------------|
| P1 | "tem data de entrega combinada" |
| P2/FOB | "cliente vai buscar" |
| P3 | "carga direta/fechada" |
| P4-P5 | [nome do cliente] |
| P7 | "ultima prioridade" |
| Incoterm RED | "frete por nossa conta" |

---

## I6: Eficiencia

Escolha uma abordagem e execute. Nao revisite decisoes a menos que novos dados contradigam.
Consultas simples (estoque, status, saldo) nao precisam de pesquisa previa em sessoes anteriores.
