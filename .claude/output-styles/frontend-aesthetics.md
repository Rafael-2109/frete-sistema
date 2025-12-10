---
description: Estilo para geracao de frontends bonitos e distintos, evitando estetica generica de IA
---

# Frontend Aesthetics Style

Ao gerar codigo frontend (HTML, CSS, JavaScript, templates), siga estas diretrizes para criar interfaces distintivas e profissionais.

## PROBLEMA A EVITAR

Claude tende a convergir para estetica generica "AI slop":
- Fontes genericas (Arial, Inter, Roboto)
- Esquemas de cores cliches (gradientes roxos em fundo branco)
- Layouts previsiveis
- Design cookie-cutter sem personalidade

## DIRETRIZES DE DESIGN

### 1. TIPOGRAFIA

**NUNCA use:** Inter, Roboto, Open Sans, Lato, fontes de sistema

**USE para diferentes contextos:**

| Contexto | Fontes Recomendadas |
|----------|---------------------|
| Codigo/Tech | JetBrains Mono, Fira Code, Space Grotesk |
| Editorial | Playfair Display, Crimson Pro, Fraunces |
| Startup | Clash Display, Satoshi, Cabinet Grotesk |
| Tecnico | IBM Plex family, Source Sans 3 |
| Distintivo | Bricolage Grotesque, Obviously, Newsreader |

**Principio de pareamento:** Alto contraste = interessante
- Display + monospace
- Serif + geometric sans
- Pesos extremos: 100/200 vs 800/900 (nao 400 vs 600)
- Saltos de tamanho 3x+ (nao 1.5x)

### 2. COR E TEMA

- Comprometa-se com uma estetica coesa
- Use CSS variables para consistencia
- Cores dominantes com acentos fortes > paletas timidas distribuidas igualmente
- Inspire-se em temas de IDE e esteticas culturais

**Variacoes de tema:**
- Dark mode com acentos neon
- Light mode com tons terrosos
- Monocromatico com um acento vibrante
- Paletas inspiradas em decadas (70s, 80s, etc)

### 3. MOTION E ANIMACAO

- Use animacoes para efeitos e micro-interacoes
- Priorize solucoes CSS-only para HTML
- Foque em momentos de alto impacto
- Uma entrada de pagina bem orquestrada com reveals escalonados (`animation-delay`) > micro-interacoes espalhadas

```css
/* Exemplo de entrada escalonada */
.card {
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.6s ease forwards;
}

.card:nth-child(1) { animation-delay: 0.1s; }
.card:nth-child(2) { animation-delay: 0.2s; }
.card:nth-child(3) { animation-delay: 0.3s; }

@keyframes fadeInUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

### 4. BACKGROUNDS

- Crie atmosfera e profundidade
- NAO use cores solidas como default
- Camadas de gradientes CSS
- Padroes geometricos sutis
- Efeitos contextuais que combinam com a estetica

```css
/* Exemplo de background atmosferico */
.hero {
  background:
    radial-gradient(ellipse at top, rgba(99, 102, 241, 0.15), transparent),
    radial-gradient(ellipse at bottom, rgba(236, 72, 153, 0.1), transparent),
    linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
```

### 5. O QUE EVITAR

- Familias de fontes overused (Inter, Roboto, Arial)
- Esquemas de cores cliches (gradientes roxos em branco)
- Layouts e padroes de componentes previsiveis
- Design cookie-cutter sem carater especifico do contexto
- Cards com border-radius padrao e sombras genericas
- Botoes com gradiente azul/roxo padrao

## EXEMPLO DE IMPLEMENTACAO

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #0a0a0f;
      --bg-secondary: #12121a;
      --text-primary: #e4e4e7;
      --text-muted: #71717a;
      --accent: #22d3ee;
      --accent-glow: rgba(34, 211, 238, 0.3);
    }

    body {
      font-family: 'Space Grotesk', sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
    }

    code, .mono {
      font-family: 'JetBrains Mono', monospace;
    }

    .card {
      background: var(--bg-secondary);
      border: 1px solid rgba(255,255,255,0.05);
      border-radius: 12px;
      backdrop-filter: blur(10px);
    }

    .btn-primary {
      background: var(--accent);
      color: var(--bg-primary);
      font-weight: 600;
      box-shadow: 0 0 20px var(--accent-glow);
      transition: all 0.2s ease;
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 0 30px var(--accent-glow);
    }
  </style>
</head>
```

## CONTEXTO NACOM GOYA

Para dashboards e templates do sistema de fretes:

- **Tema sugerido:** Dark mode profissional com acentos em cyan/teal
- **Tipografia:** Space Grotesk (UI) + JetBrains Mono (dados/numeros)
- **Paleta:**
  - Background: #0f172a (slate-900)
  - Cards: #1e293b (slate-800)
  - Accent: #22d3ee (cyan-400)
  - Success: #4ade80 (green-400)
  - Warning: #fbbf24 (amber-400)
  - Danger: #f87171 (red-400)

Interprete criativamente e faca escolhas inesperadas que parecam genuinamente projetadas para o contexto.
