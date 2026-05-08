window.OnboardingEngine.register({
  id: 'hora.pecas_estoque',
  titulo: 'Estoque de pecas',
  requirePerm: { modulo: 'pecas_estoque', acao: 'editar' },
  autoStartRoute: '/hora/pecas/estoque',
  steps: [
    { element: '#filtro-loja',           title: 'Filtre por loja',     description: 'Cada peca tem saldo separado por loja. Saldo = SUM(movimentos), nao ha tabela materializada.' },
    { element: '#tabela-pecas',          title: 'Lista de pecas',      description: 'Capacete, retrovisor, bateria, acessorios. Saldo positivo apenas. Negativo e bug — abrir issue.' },
    { element: '#btn-ajuste-manual',     title: 'Ajuste manual',       description: 'AJUSTE_POS / AJUSTE_NEG. Use so com motivo (inventario, achado, perda). <strong>Auditavel.</strong>' },
    { element: '#btn-transferir',        title: 'Transferir entre lojas', description: 'TRANSFERENCIA_OUT na origem + TRANSFERENCIA_IN no destino. Atomico — falha bloqueia ambos.' }
  ]
});
