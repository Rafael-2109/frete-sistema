# Dashboard de Métricas

## Objetivo
Exibir métricas básicas do sistema em uma página simples para validar o workflow Ralph Wiggum.

## Requisitos

1. **Rota**: Página acessível em `/metricas`
2. **Métricas a exibir**:
   - Total de pedidos no mês atual
   - Total de separações pendentes (sincronizado_nf=False)
   - Total de embarques do mês atual
3. **Atualização**: Manual (refresh da página)
4. **Menu**: Link no menu principal (base.html)

## Critérios de Aceite

- [ ] Rota `/metricas` funcional e acessível
- [ ] 3 cards com números formatados no padrão brasileiro (usar filtro `numero_br`)
- [ ] Link no menu base.html (seção Operacional ou nova seção Métricas)
- [ ] Consultas otimizadas (máximo 3 queries SQL)
- [ ] Template segue padrão visual existente (Bootstrap)

## Notas Técnicas

### Estrutura de Arquivos
```
app/metricas/
├── __init__.py
├── routes.py
└── services.py (opcional)

app/templates/metricas/
└── dashboard.html
```

### Queries Sugeridas
```python
# Pedidos do mês
CarteiraPrincipal.query.filter(
    extract('month', CarteiraPrincipal.data_pedido) == mes_atual,
    extract('year', CarteiraPrincipal.data_pedido) == ano_atual
).count()

# Separações pendentes
Separacao.query.filter_by(sincronizado_nf=False).count()

# Embarques do mês
Embarque.query.filter(
    extract('month', Embarque.data_embarque) == mes_atual,
    extract('year', Embarque.data_embarque) == ano_atual
).count()
```

### Padrões a Seguir
- Consultar CLAUDE.md para nomes de campos
- Usar filtro `numero_br(0)` para formatação
- Seguir padrão de rotas existente (Blueprint)
