
3- Arrumar filtros da movimentacao estoque
4- Exportar respeitando filtros se houver (tabela muito grande)

5- Criar tela com acesso através do dashboard de manufatura para "Analise de Produção" exibindo os produtos com tipo_movimentacao = "PRODUCAO".
Na linha contendo um botão para abrir um modal e nesse modal conter todos os componentes incluindo abrindo recursivamente os componentes dos intermediarios com as quantidades para ajustes manuais.
Os ajustes manuais na verdade serão realizados através da criação de uma nova linha de ajuste, portanto no modal deverá exibir "Consumo | Ajuste | Consumo Real"(Realizar dinamicamente através de JS)(Permitir preenchimento em Ajuste ou Consumo Real, preencher sempre o outro dinamicamente.)
Não partir consumo para quando o estoque ficar negativo nos componentes.

7- Utilizar ordem de produção do excel, se for vazio ou repetido, gerar ordem de produção pelo sistema.

No modal de "Estrutura dos componentes", não considerar consumo de água e produtos intermediarios deverão limitar o estoque a "0" (considerar consumo dos componentes)
No minimo possivel de produção, considerar consumo do menos nivel dos produtos e ignorar a agua.