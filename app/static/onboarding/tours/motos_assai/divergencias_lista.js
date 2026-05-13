// app/static/onboarding/tours/motos_assai/divergencias_lista.js
// Tour da tela de Divergencias (Plano Fase 4 + 5).
// P2 fix 9 (2026-05-13): preencher gap de tour para feature ja em producao.
window.OnboardingEngine.register({
  id: 'motos_assai.divergencias_lista',
  titulo: 'Divergencias — visao geral',
  autoStartRoute: '/motos-assai/divergencias',
  steps: [
    {
      element: '#divergencias-filtros',
      title: 'Filtros',
      description: 'Filtre por <strong>tipo</strong> (CHASSI_NAO_CADASTRADO, MODELO_DIVERGENTE, NF_CHASSI_FORA_CARREGAMENTO, etc.) e <strong>status</strong> (Abertas / Resolvidas / Todas). Use para focar nas divergencias do dia.'
    },
    {
      element: '#divergencias-tabela',
      title: 'Lista centralizada',
      description: 'Cada linha = 1 divergencia. Coluna <strong>Tipo</strong> indica o problema; coluna <strong>Origem</strong> mostra a NF/Sep/Carregamento envolvido.'
    },
    {
      element: '.btn-resolver-divergencia',
      title: 'Resolver divergencia',
      description: 'Cada divergencia tem opcoes de resolucao:<br>'
        + '<strong>CCe:</strong> aplicar Carta de Correcao da NF.<br>'
        + '<strong>Substituir chassi:</strong> trocar chassi origem -> destino (cross-loja inclusive).<br>'
        + '<strong>Alterar Carregamento:</strong> reabrir e reescanear.<br>'
        + '<strong>Cancelar NF:</strong> cascata completa (reverter FATURADA, limpar embarque, vinculo historico).<br>'
        + '<strong>Ignorar:</strong> marca como resolvida com observacao (sem mudanca de estado).'
    },
    {
      element: '#divergencias-tabela tbody tr:first-child',
      title: 'Detalhes',
      description: 'Clique na linha para expandir e ver dados JSON da divergencia (loja, NF, chassis envolvidos, motivos).'
    }
  ]
});
