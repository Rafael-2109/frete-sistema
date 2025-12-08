---
name: memoria-usuario
description: Gerencia memoria persistente do usuario. Use para salvar/recuperar preferencias, fatos aprendidos e contexto entre sessoes. Exemplos: 'lembre que prefiro respostas diretas', 'o que voce sabe sobre mim?', 'esqueca minhas preferencias'.
---

# Skill: Memória do Usuário

Esta skill gerencia a memória persistente por usuário, permitindo que Claude lembre informações entre sessões diferentes.

## Quando Usar

- Usuário pede para lembrar algo: "Lembre que prefiro respostas diretas"
- Usuário pergunta o que Claude sabe: "O que você sabe sobre mim?"
- Usuário quer apagar memórias: "Esqueça minhas preferências"
- Ajustar comportamento baseado em preferências salvas

## Scripts Disponíveis

### Ver Memórias

```bash
python .claude/skills/memoria-usuario/scripts/memoria.py view --user-id USER_ID
python .claude/skills/memoria-usuario/scripts/memoria.py view --user-id USER_ID --path /memories/preferences.xml
```

### Salvar Memória

```bash
python .claude/skills/memoria-usuario/scripts/memoria.py save --user-id USER_ID --path /memories/preferences.xml --content "<prefs>direto</prefs>"
```

### Atualizar Memória (substituir texto)

```bash
python .claude/skills/memoria-usuario/scripts/memoria.py update --user-id USER_ID --path /memories/preferences.xml --old "direto" --new "objetivo e direto"
```

### Deletar Memória

```bash
python .claude/skills/memoria-usuario/scripts/memoria.py delete --user-id USER_ID --path /memories/preferences.xml
```

### Limpar Todas as Memórias

```bash
python .claude/skills/memoria-usuario/scripts/memoria.py clear --user-id USER_ID
```

## Estrutura de Paths Recomendada

```
/memories/
├── user.xml          # Informações básicas do usuário
├── preferences.xml   # Preferências de comunicação
├── context/
│   ├── company.xml   # Informações da empresa
│   └── role.xml      # Cargo/responsabilidades
└── learned/
    └── terms.xml     # Termos específicos aprendidos
```

## Formato XML Recomendado

```xml
<!-- /memories/user.xml -->
<user>
    <name>Rafael</name>
    <role>Dono da empresa</role>
</user>

<!-- /memories/preferences.xml -->
<preferences>
    <communication>direto e objetivo</communication>
    <detail_level>alto quando pedido</detail_level>
    <language>portugues</language>
</preferences>

<!-- /memories/context/company.xml -->
<company>
    <name>Nacom Goya</name>
    <industry>Alimentos - Conservas</industry>
    <key_clients>Atacadao, Assai</key_clients>
</company>
```

## Importante

- Memórias são isoladas por usuário (user_id)
- Persistem entre sessões diferentes
- NÃO armazene histórico de conversas (já é feito automaticamente)
- Use para FATOS e PREFERÊNCIAS, não para mensagens
