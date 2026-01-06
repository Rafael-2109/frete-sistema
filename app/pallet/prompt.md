<objetivo>
    1- Controlar o saldo devedor de pallets das transportadoras e clientes.
    2- Controlar as NFs de remessa e os vale paletes, documentos esses que possuem o direito sobre os pallets.
    3- Controlar as tratativas nas NFs de remessa.
        A- Devolução
        B- Cancelamento
        C- Recusa
        D- Substituição
</objetivo>

<processo_previo>
    A gestão de pallet funciona da seguinte maneira:
    1- Os pedidos da carteira de pedidos são transformados em Separacao.
    2- As separações são agrupadas na cotação de frete e gerado um embarque.
    3- Nesse embarque é impresso as separações para a equipe separar, informar quantos pallets foram utilizados e seguir para o faturamento.
    4- Na etapa do faturamento, a equipe de separação informa se o transportador trouxe pallet para troca.
    5- Caso o transportador não tenha trago pallets, emitiremos NF de remessa para ele caso ele aceite.
    6- Caso ele não aceite, emitiremos para o cliente caso ele aceite.
    7- Controlaremos os pallets até que sejam retornados ou faturados e trataremos a NF de devolução.
</processo_previo>

<processo>
    <embarque>
        No embarque, é avaliado se o transportador aceita NF de pallet emitido contra ele, caso aceite então é emitido 1 nf de pallet para todos EmbarqueItem que não possuir NF de pallet (definição em campo na tabela de transportadora).
        Caso o transportador não aceite nf de pallet, então será emitido contra o cliente caso ele aceite (definição em campo na tabela de contatos_agendamento).
        Caso a nf seja preenchida no Embarque, ela representará a remessa de pallet para todas as nfs dos EmbarqueItem daquele Embarque.
        Caso seja preenchido previamente uma nf de pallet no Embarque e posteriormente seja preenchida uma nf de pallet em um EmbarqueItem, então a NF de venda desse EmbarqueItem não estará mais sendo representada pela NF de pallet do Embarque e sim do EmbarqueItem.
        Crie FK com o numero da NF quando a NF for preenchida ou quando a NF de pallet for preenchida.
        Coloque o gatilho tambem no ProcessadorFaturamento e garanta que todas as origens de preenchimento da NF de pallet ou da NF seja sincronizado esse FK para evitar que a NF de pallet fique órfã.
    </embarque>
</processo>

<responsabilidade_transportadora>
    Cobraremos a transportadora do retorno dos vale pallets / canhoto assinado em 30 dias, caso não ocorra transformaremos a nf de remessa em cobrança para a transportadora.
    Caso a NF seja emitida contra a transportadora, ela será responsavel pelo retorno dos pallets, salvo se for enviado canhoto assinado / vale pallet.
    A responsabilidade da transportadora se encerra no momento da entrega dos pallets / vale pallets / canhoto assinado.
</responsabilidade_transportadora>

<resolucao_pallet>
    O cliente poderá devolver os pallets no ato do recebimento ou poderá gerar um crédito dos pallets a serem retirados posteriormente através do canhoto assinado ou vale pallet caso o cliente emita.
    <nf_remessa>
        <valor_da_nf>
            Diante da emissão de vale pallets o direito de recebimento dos pallets ficará exclusivamente com o detentor dos vale pallets, isso deverá ser acompanhado pela equipe para finalizar o processo com a nf de remessa.
        </valor_da_nf>
        <resolucao_nf>
            Visto que o cliente não devolveu os pallets no ato do recebimento, ele dará entrada na NF, assinará o canhoto e poderá emitir o vale pallet
            No momento da coleta dos pallets, o cliente emitirá uma NF de devolução referenciando a NF de pallet.
        </resolucao_nf>
    </nf_remessa>
    <direito_pallet>
        Caso o cliente emita vale pallet, ele passará a ser o documento com poder de recebimento dos pallets, caso contrario o documento para retirada dos pallets será o canhoto assinado.
        A retirada dos pallets tem data de vencimento (normalmente 1 ano após a emissão), portanto deveremos resolver o quanto antes.
    </direito_pallet>
    <criacao_vale_sistema>
        <nomenclatura>
            Chamarei o documento de direito dos pallets de vale pallet, sendo ele efetivamente um vale pallet ou o canhoto assinado.
        </nomenclatura>
        O vale pallet deverá ser criado manualmente no sistema e referenciar uma nf de venda/pallet (visto que elas possuirão FK, poderá referenciar qualquer uma das 2 e com isso estar relacionada as 2)
        O vale deverá ser criado com data de emissão, quantidade e data de validade
        Deverão haver campos para:
        1- Acompanhar a posse do vale pallet
        2- Rastrear o recebimento dos vale pallets, endereçamento no arquivo (pasta / aba)
        3- Responsavel pela coleta / empresa que foi vendida
        4- Tipo de resolução (Venda / Coleta)
        5- Valor da venda
        6- Custo da coleta
        7- Tipo do vale (vale pallet / canhoto assinado)
    </criacao_vale_sistema>
    <resolucao>
        As nossas opções de resolver um vale são:
        1- Emitir nf de venda para a transportadora em caso de não entrega dos vale pallets dentro do prazo.
        2- Cotar com uma empresa a venda dos pallets.
        3- Cotar a coleta dos pallets com uma transportadora.        
        No caso de uma venda ou coleta, devemos agendar a coleta com o cliente.
        A resolução do vale pallet ou canhoto, finalizará no nosso recebimento ou emissão da NF de venda.
    </resolucao>
</resolucao_pallet>

<resolucao_nf_remessa>
    A NF de remessa de pallet poderá ser resolvida através de:
    1- Cancelamento da NF
    2- 
</resolucao_nf_remessa>

<tipos_movimentacao>
    <saidas>
        <remessa>
        # Somam ao saldo devedor automaticamente
            l10n_br_tipo_pedido = [&quot;vasilhame&quot;,&quot;Saída: Remessa de Vasilhame&quot;]
            Esse tipo acrescentará na conta do cliente / transportadora. (Verifique pelo CNPJ em transportadora / contatos_agendamento se é cliente ou transportadora)
        </remessa>
        <venda>
        # Reduzem do saldo devedor da nf de pallet vinculada manualmente
            As vendas já são importadas para o sistema e deverão gerar um abatimento para ser vinculado manualmentea a uma remessa.
            Avalie se os campos preenchidos na MovimentacaoEstoque ao importar um faturamento de pallet do Odoo são compativeis com o controle.
        </venda>
    </saidas>
    <entradas>
        <compra>
        # Não interferem na conta credora / devedora dos clientes e transportadoras
            As compras tambem já estão sendo importadas do Odoo mas elas não entram na conta pois apenas alimentam o nosso estoque, no caso ela é utilizada para controle de estoque e não para controlar o estoque em terceiros.
        </compra>
        <devolucao>
        # Reduzem do saldo devedor automaticamente.
            Caso o cliente não devolva os pallets no ato do recebimento, ele dará entrada na NF de pallet e no ato da devolução dos pallets, ele emitirá a NFD dos pallets.
        </devolucao>
        <cancelamento>
        # Reduzem do saldo devedor automaticamente.
            Caso o cliente devolva os pallets no ato do recebimento da mercadoria e esteja dentro do prazo de cancelamento da NF, então a NF de pallet será cancelada e indicado no campo "Motivo" que se refere a devolução dos pallets.
        </cancelamento>
        <nf_remessa_recusada>
        # Reduzem do saldo devedor automaticamente.
            Vejo que os retornos já estão sendo importados pelo sistema, mas acredito que haja necessidade de ajustar alguns campos para manter compatibilidade com o controle.
            Deverão baixar a NF de remessa automaticamente.
        </nf_remessa_recusada>
    </entradas>
</tipos_movimentacao>

