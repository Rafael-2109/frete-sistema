from app import create_app, db
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.cadastros_agendamento.models import ContatoAgendamento
from datetime import date

app = create_app()

with app.app_context():
    print("=" * 60)
    print("DIAGNÓSTICO DO FILTRO 'AGEND. PENDENTE'")
    print("=" * 60)
    
    # 1. Contar total de entregas não finalizadas
    entregas_nao_finalizadas = EntregaMonitorada.query.filter(
        EntregaMonitorada.status_finalizacao == None
    ).count()
    print(f"\n1. Total de entregas não finalizadas: {entregas_nao_finalizadas}")
    
    # 2. Listar contatos de agendamento com forma preenchida
    contatos_com_forma = ContatoAgendamento.query.filter(
        ContatoAgendamento.forma != None,
        ContatoAgendamento.forma != '',
        ContatoAgendamento.forma != 'SEM AGENDAMENTO'
    ).all()
    
    print(f"\n2. Contatos com forma de agendamento cadastrada: {len(contatos_com_forma)}")
    for contato in contatos_com_forma[:5]:  # Primeiros 5
        print(f"   - CNPJ: {contato.cnpj} | Forma: {contato.forma} | Contato: {contato.contato}")
    
    # 3. Buscar entregas desses CNPJs sem agendamento
    cnpjs_com_forma = [c.cnpj for c in contatos_com_forma]
    
    # Subquery para entregas que JÁ têm agendamento
    subquery = db.session.query(AgendamentoEntrega.entrega_id).distinct()
    
    # Entregas que precisam de agendamento mas não têm
    entregas_sem_agendamento = EntregaMonitorada.query.filter(
        EntregaMonitorada.cnpj_cliente.in_(cnpjs_com_forma),
        ~EntregaMonitorada.id.in_(subquery),
        EntregaMonitorada.status_finalizacao == None
    ).all()
    
    print(f"\n3. Entregas que DEVERIAM aparecer em 'Agend. Pendente': {len(entregas_sem_agendamento)}")
    for entrega in entregas_sem_agendamento[:10]:  # Primeiras 10
        # Verificar se tem agendamento
        tem_agendamento = AgendamentoEntrega.query.filter_by(entrega_id=entrega.id).count()
        contato = ContatoAgendamento.query.filter_by(cnpj=entrega.cnpj_cliente).first()
        
        print(f"\n   NF: {entrega.numero_nf}")
        print(f"   Cliente: {entrega.cliente} (CNPJ: {entrega.cnpj_cliente})")
        print(f"   Tem agendamento? {tem_agendamento > 0} ({tem_agendamento} agendamentos)")
        print(f"   Contato cadastrado? {contato is not None}")
        if contato:
            print(f"   Forma cadastrada: {contato.forma}")
            print(f"   Contato: {contato.contato}")
    
    # 4. Verificar se há problema com CNPJ específico
    print("\n4. Debug para NF específica:")
    nf_teste = input("Digite o número da NF que deveria aparecer (ou Enter para pular): ").strip()
    
    if nf_teste:
        entrega = EntregaMonitorada.query.filter_by(numero_nf=nf_teste).first()
        if entrega:
            print(f"\n   NF encontrada: {entrega.numero_nf}")
            print(f"   Cliente: {entrega.cliente}")
            print(f"   CNPJ: {entrega.cnpj_cliente}")
            print(f"   Status finalização: {entrega.status_finalizacao}")
            print(f"   Data agenda: {entrega.data_agenda}")
            
            # Verificar agendamentos
            agendamentos = AgendamentoEntrega.query.filter_by(entrega_id=entrega.id).all()
            print(f"   Agendamentos: {len(agendamentos)}")
            for ag in agendamentos:
                print(f"      - Data: {ag.data_agendada} | Forma: {ag.forma_agendamento} | Status: {ag.status}")
            
            # Verificar contato
            contato = ContatoAgendamento.query.filter_by(cnpj=entrega.cnpj_cliente).first()
            if contato:
                print(f"   Contato cadastrado: Sim")
                print(f"   Forma: {contato.forma}")
                print(f"   Contato: {contato.contato}")
            else:
                print(f"   Contato cadastrado: Não")
                
            # Verificar se deveria aparecer no filtro
            if (not entrega.status_finalizacao and 
                contato and 
                contato.forma and 
                contato.forma != '' and 
                contato.forma != 'SEM AGENDAMENTO' and
                len(agendamentos) == 0):
                print("\n   ✅ DEVERIA aparecer em 'Agend. Pendente'")
            else:
                print("\n   ❌ NÃO deveria aparecer em 'Agend. Pendente'")
                if entrega.status_finalizacao:
                    print(f"      Motivo: Entrega finalizada com status '{entrega.status_finalizacao}'")
                elif not contato:
                    print("      Motivo: Não tem contato cadastrado")
                elif not contato.forma or contato.forma == '' or contato.forma == 'SEM AGENDAMENTO':
                    print(f"      Motivo: Forma inválida ou vazia: '{contato.forma}'")
                elif len(agendamentos) > 0:
                    print("      Motivo: Já tem agendamento(s)")
        else:
            print(f"   NF {nf_teste} não encontrada!")
    
    print("\n" + "=" * 60) 