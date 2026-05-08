window.OnboardingEngine.register({
  id: 'hora.tagplus_conta',
  titulo: 'Configurar conta TagPlus',
  requirePerm: { modulo: 'tagplus', acao: 'editar' },
  autoStartRoute: '/hora/tagplus/conta',
  steps: [
    { element: '#campo-client-id',       title: 'Client ID do TagPlus',    description: 'Vem do painel do TagPlus. Cole aqui — e o identificador da sua conta OAuth.' },
    { element: '#campo-client-secret',   title: 'Client Secret (criptografado)', description: 'Salvamos com Fernet (HORA_TAGPLUS_ENC_KEY). <strong>Nunca aparece em plaintext de novo.</strong>' },
    { element: '#btn-iniciar-oauth',     title: 'Autorizar via OAuth',     description: 'Abre TagPlus pra voce logar. Token volta no callback e fica salvo em hora_tagplus_token.' },
    { element: '#secao-checklist',       title: 'Checklist de prontidao',  description: 'Conta + token + mapeamento de produtos + formas de pagamento. NFe so emite com tudo verde.' }
  ]
});
