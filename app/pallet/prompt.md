<processo_previo>
    A gestão de pallet funciona da seguinte maneira:
    1- Os pedidos da carteira de pedidos são transformados em Separacao.
    2- As separações são agrupadas na cotação de frete e gerado um embarque.
    3- Nesse embarque é impresso as separações para a equipe separar, informar quantos pallets foram utilizados e seguir para o faturamento.
    4- Na etapa do faturamento, a equipe de separação informa se o transportador trouxe pallet para troca.
    5- Ao realizar 
</processo_previo>
<processo>
    <embarque>
        No embarque, é avaliado se o transportador aceita NF de pallet emitido contra ele, caso aceite então é emitido 1 nf de pallet para todos EmbarqueItem que não possuir NF de pallet (definição em campo na tabela de  transportadora).
        Caso o transportador não aceite nf de pallet, então será emitido contra o cliente caso ele aceite (definição em campo na tabela de contatos_agendamento).
        Caso a nf seja preenchida no Embarque, ela representará a remessa de pallet para todas as nfs dos EmbarqueItem daquele Embarque.
        Caso seja preenchido previamente uma nf de pallet no Embarque e posteriormente seja preenchida uma nf de pallet em um EmbarqueItem, então a NF de venda desse EmbarqueItem não estará mais sendo representada pela NF de pallet do Embarque e sim do EmbarqueItem.
        Crie FK com o numero da NF quando a NF for preenchida ou quando a NF de pallet for preenchida.
        Coloque o gatilho tambem no ProcessadorFaturamento e garanta que todas as origens de preenchimento da NF de pallet ou da NF seja sincronizado esse FK para evitar que a NF de pallet fique órfã.
    </embarque>
    <perspectiva>
        O controle dos pallets ocorrerá emcima do detentor da obrigação sobre os pallets.
        A cobrança será sob a perspectiva da empresa Nacom Goya e deverá ocorrer emcima da transportadora que realizou a entrega / pessoa responsavel por cuidar dos pallets / cliente para liberar data de agendamento de coleta.
    </perspectiva>
    <nf_pallet_transportadora>
        Caso a NF de pallet seja emitida contra a transportadora, cobraremos ela de retornar os pallets / vale pallet, em caso de não retorno em 30 dias, transformaremos a nf de remessa em cobrança para a transportadora.
        <cliente_emite_vale>
            Caso o cliente emita vale pallet, o transportador deverá retornar o vale pallet.
            A entrega do vale pallet encerrará a sua responsabilidade com os pallets e transferirá a responsabilidade para a nossa empresa Nacom Goya e encerrará a cobrança pela nf de remessa.
            <nf_remessa>
                Diante da emissão de vale pallets, a nf de remessa perde o valor perante a cobrança, mas a empresa ainda terá que cobrar o cliente pela recusa da nf de remessa de pallet e isso deverá ser acompanhado pela equipe para finalizar o processo com a nf de remessa.
            </nf_remessa>
            <vale_pallet>
                Nesse caso, o vale pallet passará a ser o documento com poder de recebimento dos pallets mas ele tem data de vencimento (normalmente 1 ano após a emissão), portanto deveremos resolver o quanto antes.
                <objetivo_processo>
                    1- Cobrar a transportadora de entregar o vale pallet.
                    2- Tentar vender os pallets contidos no vale pallet se for mais vantajoso
                    3- Caso a opção seja de coletar os pallets, deveremos cotar um frete para realizar a coleta.
                    4- Enviar os vale pallets para coleta / venda, acompanhando a resolução
                    5- No caso de uma venda, os vale pallets são finalizados com a nf de venda.
                    6- No caso de uma coleta, os vale pallets são finalizados com o recebimento dos pallets.
                </objetivo_processo>
                <criacao_vale>
                    O vale pallet deverá ser criado manualmente no sistema e referenciar uma nf de venda/pallet (visto que elas possuirão FK, poderá referenciar qualquer uma das 2 e com isso estar relacionada as 2)
                    O vale deverá ser criado com data de emissão, quantidade e data de validade
                    Deverão haver campos para:
                    1- Acompanhar a posse do vale pallet
                    2- Rastrear o recebimento dos vale pallets, endereçamento no arquivo (pasta / aba)
                    3- Responsavel pela coleta / empresa que foi vendida
                    4- Tipo de resolução (Venda / Coleta)
                    5- Valor da venda / Custo da coleta
                </criacao_vale>
                <responsabilidade>
                    No momento que o vale pallet for gerado, a responsabilidade passará a ser da transportadora que realizou o Embarque de entregar o vale pallet
                    No momento que o vale for entregue a nossa empresa, a responsabilidade será nossa.
                </responsabilidade>
                <resolucao>
                    As nossas opções de solucionar um vale serão:
                    1- Emitir nf de venda para a transportadora em caso de não entrega dos vale pallets dentro do prazo.
                    2- Cotar com uma empresa a venda dos vale pallets.
                    3- Agendar a coleta e contratar uma transportadora para realizar a coleta dos pallets
                    Ao realizar uma venda, a nf de venda resolverá o vale pallet.
                    Ao realizar uma coleta, o recebimento resolverá o vale pallet.
                </resolucao>
                <controle>
                    Deverá ser controlado através de uma tabela, FK com a NF de remessa com campos:
                    - nf_remessa
                    - validade Date
                    - recebido Boolean
                    - enviado_coleta Boolean
                    - responsavel_coleta (transportadora)
                    - recebimento_pallet
                </controle>
            </vale_pallet>
        </cliente_emite_vale>
    </nf_pallet_transportadora>
</processo>
<inclusao>
    <contatos_agendamento>
        Acrescente a informação se o cliente aceita nf de pallet na UI, exportação e importação por excel
    </contatos_agendamento>
    <transportadora> 
        Acrescente a informação se a transportadora aceita nf de pallet de pallet na UI, exportação e importação por excel
    </transportadora>
</inclusao>
<registro_movimentacao>
    <saidas>
        <remessa>
        # Somam ao saldo devedor automaticamente
            l10n_br_tipo_pedido = [&quot;vasilhame&quot;,&quot;Saída: Remessa de Vasilhame&quot;]
            Esse tipo acrescentará a conta do cliente / transportadora. (Verifique pelo CNPJ em transportadora / contatos_agendamento se é cliente ou transportadora)
        </remessa>
        <venda>
        # Reduzem do saldo devedor da nf de pallet vinculada manualmente
            As vendas já são importadas para o sistema e deverão gerar um abatimento para ser vinculado manualmentea uma remessa.
            Avalie se os campos preenchidos na MovimentacaoEstoque ao importar um faturamento de pallet do Odoo são compativeis com o controle.
        </venda>
    </saidas>
    <entradas>
        <compra>
        # Não interferem na conta credora / devedora dos clientes e transportadoras
            As compras tambem já estão sendo importadas do Odoo mas elas não entram na conta pois apenas alimentam o nosso estoque, no caso ela é utilizada para controle de estoque e não para controlar o estoque em terceiros.
        </compra>
        <retorno_remessa>
        # Reduzem do saldo devedor automaticamente.
            Vejo que os retornos já estão sendo importados pelo sistema, mas acredito que haja necessidade de ajustar alguns campos para manter compatibilidade com o controle.
            Deverão baixar a NF de remessa automaticamente.
        </retorno_remessa>
    </entradas>
</registro_movimentacao>

3. POP - PROCEDIMENTO OPERACIONAL PADRÃO
Gestão de Pallets - Instrumento de Trabalho
FLUXO PRINCIPAL

SEPARAÇÃO → EMBARQUE → FATURAMENTO → CONTROLE PALLET → VALE PALLET → RESOLUÇÃO
ETAPA 1: Sincronização com Odoo (Diária)
Responsável: Equipe de Logística/Faturamento Acesso: Menu Pallet → Botão Sincronizar Odoo (canto superior direito) Tela: sincronizar.html Campos:
Campo	Descrição	Valor Padrão
Tipo de Sincronização	Remessas, Vendas ou Tudo	Tudo
Período (dias)	Quantos dias retroativos buscar	30
Ação: Clique em Iniciar Sincronização O que acontece:
Sistema busca no Odoo NFs com l10n_br_tipo_pedido = "vasilhame" → Cria REMESSA
Sistema busca no Odoo NFs com produto 208000012 (PALLET) → Cria SAIDA (venda)
Determina automaticamente se destinatário é TRANSPORTADORA ou CLIENTE pelo CNPJ
ETAPA 2: Dashboard - Monitoramento Diário
Acesso: Menu Pallet → Página inicial Tela: index.html Cards de Resumo:
Card	Cor	Descrição	Ação
Pallets em Terceiros	Azul	Total de pallets não baixados	Informativo
Registrar Saída	Verde	Criar saída manual	Clique para acessar
Registrar Retorno	Amarelo	Criar retorno manual	Clique para acessar
Vale Pallets	Ciano	Quantidade pendente	Clique para listar
Alertas de Prazo (aparecem quando aplicável):
Alerta	Cor	Critério	Urgência
Remessas Vencidas	Vermelho	> 30 dias sem baixa	CRÍTICO
Remessas Prestes a Vencer	Amarelo	25-30 dias	ATENÇÃO
Vendas Pendentes de Vínculo	Ciano	Vendas sem remessa vinculada	AÇÃO NECESSÁRIA
Vales Vencidos	Vermelho	Validade expirada	CRÍTICO
ETAPA 3: Vincular Venda à Remessa
Quando: Após sincronização, quando aparecem "Vendas Pendentes de Vínculo" Acesso: Dashboard → Seção "Vendas Pendentes de Vínculo" → Botão 🔗 (link) Tela: vincular_venda.html Campos exibidos da Venda:
NF da venda
Quantidade de pallets
Data
Comprador
Ação:
Selecione a REMESSA que esta venda abate (radio button)
Clique em Vincular
Resultado:
Venda recebe movimento_baixado_id = ID da remessa
Remessa é marcada como baixado = True
Ambos saem do saldo "em terceiros"
ETAPA 4: Registrar Retorno Manual
Quando: Pallets físicos retornaram sem passar pelo Odoo Acesso: Dashboard → Card Registrar Retorno Tela: registrar_retorno.html Campos:
Campo	Obrigatório	Descrição
Tipo Destinatário	Sim	TRANSPORTADORA ou CLIENTE
CNPJ	Sim	CNPJ de quem retornou
Nome	Não	Nome para referência
Quantidade	Sim	Número de pallets retornados
NF	Não	NF de retorno se houver
Observação	Não	Notas adicionais
Resultado: Cria movimentação tipo ENTRADA ⚠️ IMPORTANTE: Após registrar retorno, é necessário BAIXAR manualmente a remessa correspondente.
ETAPA 5: Baixar Movimento (Remessa)
Quando: Após retorno de pallets, para encerrar pendência Acesso: Dashboard → Ver Todos os Movimentos → Botão Baixar no movimento REMESSA Tela: baixar_movimento.html Campos:
Campo	Descrição
Retorno Vinculado	Selecione o movimento de ENTRADA correspondente
Observação	Motivo ou nota da baixa
Resultado: Remessa marcada como baixado = True, sai do saldo "em terceiros"
ETAPA 6: Criar Vale Pallet
Quando: Cliente emitiu vale pallet físico que transportadora deve entregar Acesso: Menu Pallet → Vale Pallets → Botão Novo Vale Tela: vale_pallet_form.html Campos Obrigatórios:
Campo	Descrição	Exemplo
NF Pallet	NF de remessa que originou o vale	123456
Data Emissão	Data de emissão do vale	04/01/2026
Data Validade	Prazo final (default: +30 dias)	04/02/2026
Quantidade	Pallets no vale	10
Campos de Rastreamento:
Campo	Descrição
Cliente (CNPJ/Nome)	Quem emitiu o vale
Transportadora (CNPJ/Nome)	Responsável por entregar
Posse Atual	TRANSPORTADORA, NACOM ou CLIENTE
Pasta/Aba Arquivo	Localização física do documento
ETAPA 7: Receber Vale Pallet
Quando: Transportadora entregou o vale físico na Nacom Acesso: Vale Pallets → Botão Receber (ícone mão) Ação: Confirmação com 1 clique Resultado:
recebido = True
posse_atual = NACOM
Responsabilidade passa para Nacom resolver
ETAPA 8: Enviar para Resolução
Quando: Nacom decidiu vender ou coletar os pallets Acesso: Vale Pallets → Botão Enviar Resolução Tela: enviar_resolucao.html Campos:
Campo	Descrição
Tipo Resolução	VENDA ou COLETA
Responsável	Empresa compradora ou transportadora de coleta
CNPJ	CNPJ do responsável
Valor	Valor da venda ou custo da coleta
ETAPA 9: Resolver Vale Pallet
Quando: Venda finalizada com NF ou coleta concluída Acesso: Vale Pallets → Botão Resolver Tela: resolver_vale.html Campos:
Campo	Descrição
NF Resolução	NF de venda ou recebimento da coleta
Valor Final	Valor efetivo (pode diferir do estimado)
Observação	Notas finais
Resultado: Vale marcado como resolvido = True, sai das pendências
FLUXOGRAMA DE STATUS DO VALE PALLET

┌─────────────┐
│  PENDENTE   │ ← Vale criado, na posse da TRANSPORTADORA
└──────┬──────┘
       │ [Transportadora entrega]
       ▼
┌─────────────┐
│  RECEBIDO   │ ← Vale na posse da NACOM
└──────┬──────┘
       │ [Nacom decide ação]
       ▼
┌─────────────┐
│EM RESOLUÇÃO │ ← Enviado para VENDA ou COLETA
└──────┬──────┘
       │ [Venda/Coleta concluída]
       ▼
┌─────────────┐
│  RESOLVIDO  │ ← Processo finalizado
└─────────────┘
TELAS DO SISTEMA
Tela	URL	Função
Dashboard	/pallet/	Visão geral e alertas
Movimentos	/pallet/movimentos	Lista de todas movimentações
Registrar Saída	/pallet/registrar-saida	Criar saída manual
Registrar Retorno	/pallet/registrar-retorno	Criar entrada manual
Sincronizar	/pallet/sync	Importar do Odoo
Vincular Venda	/pallet/vincular-venda/{id}	Vincular venda à remessa
Vale Pallets	/pallet/vales	Listar vale pallets
Novo Vale	/pallet/vales/novo	Criar vale pallet
Editar Vale	/pallet/vales/{id}	Editar vale pallet
AÇÕES RÁPIDAS (BOTÕES)
Ícone	Ação	Onde Aparece
🔗	Vincular	Vendas pendentes
👁️	Ver movimentos	Saldos por destinatário
✋	Receber	Vale pallet pendente
📤	Enviar resolução	Vale recebido
✅	Resolver	Vale em resolução
🗑️	Excluir	Vale pallet
📝	Editar	Vale pallet
