window.OnboardingEngine.register({
  id: 'hora.modelos_unificar',
  titulo: 'Unificar modelos duplicados',
  requirePerm: { modulo: 'modelos', acao: 'aprovar' },
  autoStartRoute: '/hora/modelos/unificar',
  steps: [
    { element: '#campo-canonico',        title: 'Modelo canonico',  description: 'O modelo que vai PERMANECER. Todos os outros viram aliases dele.' },
    { element: '#campo-aliases',         title: 'Modelos a fundir', description: 'Selecione N modelos duplicados. Suas tabelas (chassis, pedidos, conferencias) vao apontar para o canonico.' },
    { element: '#btn-preview',           title: 'Preview (dry-run)', description: '<strong>Sempre rode antes!</strong> Mostra exatamente quantos registros mudam, sem alterar banco.' },
    { element: '#btn-executar-merge',    title: 'Executar merge',   description: 'Operacao de alta consequencia. UPDATE em 6 FKs em transacao unica. Aliases ficam ativo=False.' }
  ]
});
