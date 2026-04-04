# Objetivo principal - Conciliar Extrato - Remessa CNAB - Titulos a receber.

1- Identifique todos os critérios e formas de conciliação / baixa dos recebimentos e extratos no Odoo antes de começar.

2- Identifique todos os fluxos, entendendo como o match do extrato + titulos + cnab são realizados, garantindo que seja sempre possivel finalizar a operação (Match entre os 3 + conciliação no Odoo entre titulo e extrato) independente da ordem ou da falta de alguma informação, exemplo:
A- Sistema possui titulo mas não possui extrato - Quando conciliado com o CNAB, o extrato será conciliado depois? Como?
B- Titulo já está conciliado com extrato - Quando for conciliar com o CNAB, o CNAB será conciliado com o extrato e o titulo?

3- Preciso que verifique se os extratos estão sendo identificados e importados do Odoo automaticamente pelo scheduler no momento que forem importados no Odoo, após verificar e corrigir caso necessario, remova a sessão de Extratos Pendentes de Importação e corrija a exibição da pagina pois ao selecioanr 100 por pagina a pagina está cortando, não sendo possivel selecionar as paginas.

4- Preciso que a importação e match do arquivo CNAB seja realizado o match com o extrato, independente da ordem de importação
Ps: Caso seja importado o arquivo CNAB e realizado o match com os titulos ANTES de importar o extrato, deverá ter uma forma de realizar o match posteriormente com o extrato.

5- Foi utilizado o script python scripts/sincronizar_extratos.py --odoo-completo e retornou a mensagem de que X extratos foram reconciliados, porem os extratos não foram reconciliados no sistema, ou seja, ainda é possivel realizar match no extrato com titulo no sistema, portanto preciso que verifique os critérios de "match".

6- Mesmo com extrato importado, a conciliação pelo CNAB está mantendo o extrato com status "Pendente" na tela de conciliação do CNAB
