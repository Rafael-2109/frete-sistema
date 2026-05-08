window.OnboardingEngine.register({
  id: 'motos_assai.modelos_assai',
  titulo: 'Catalogo de modelos Q.P.A.',
  adminOnly: true,
  autoStartRoute: '/motos-assai/modelos',
  steps: [
    { element: '#tabela-modelos',        title: 'Modelos cadastrados',        description: 'X11_MINI, DOT, SOL... Cada um tem codigo + descricao + regex de chassi para validacao.' },
    { element: '#campo-regex-chassi',    title: 'Regex de chassi',            description: 'Padrao esperado (ex: ^MZX\\d{10}$). Validacao nao-bloqueante na conferencia — so sinaliza divergencia.' },
    { element: '#secao-aliases',         title: 'Aliases',                    description: '3 tipos: ALIAS_TIPO_QPA (codigo exato), ALIAS_TIPO_DESCRICAO_QPA (substring), ALIAS_TIPO_LIVRE.' },
    { element: '#btn-salvar-modelo',     title: 'Salvar',                     description: 'Modelo + aliases ficam disponiveis para todos os parsers (pedido, recibo, NF Q.P.A.).' }
  ]
});
