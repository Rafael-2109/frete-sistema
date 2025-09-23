Preciso fazer um estudo nas funções de sincronizacao do Odoo.

Há 2 chamadas para o fluxo que envolve app/odoo/services/faturamento_service.py e depois app/odoo/services/carteira_service.py.

1ª vem de app/odoo/routes/sincronizacao_integrada.py que chama app/odoo/services/sincronizacao_integrada_service.py onde esse arquivo chama:

- resultado_faturamento = self._sincronizar_faturamento_seguro()

- Que por sua vez chama a função que coordena todo o fluxo de sincronização através do Odoo:
resultado_fat = self.faturamento_service.sincronizar_faturamento_incremental(
                minutos_janela=43200,     # 30 dias para garantir que pegue tudo recente
                primeira_execucao=False,
                minutos_status=43200      # 30 dias também para status
            )

- def sincronizar_faturamento_incremental(self, minutos_janela=40, primeira_execucao=False, minutos_status=1560) -> Dict[str, Any]:

Essa função é quem gerencia o fluxo e as ações da sincronização do faturamento, ela é responsavel por:



