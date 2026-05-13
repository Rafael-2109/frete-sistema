#!/bin/bash
#
# init-artifact.sh — Cria projeto Vite + React + TS + Tailwind em <project-dir>.
#
# V1 (MVP): SEM shadcn/ui pre-instalado. Componentes Tailwind direto.
# V2 (futuro): pre-buildar templates/base/ com shadcn/ui + Radix tarball.
#
# Adaptado de anthropics/skills/web-artifacts-builder/scripts/init-artifact.sh
# Migrado para pnpm em 2026-05-13 — sintoma assimetrico revelador:
# `npm install` funcionava em DEV local mas falhava SO em prod (Render),
# deixando node_modules/@parcel/config-default AUSENTE apos exit 0.
# Causa: ambiente (npm hoisting heuristico + cache mutavel em FS Render),
# nao codigo. pnpm tem CAS store + hoisting deterministico — ver bundle-artifact.sh.
#
# Uso:
#   bash init-artifact.sh <project-dir>
#
# Variaveis de ambiente:
#   ARTIFACT_LOG_FILE  Opcional. Caminho de arquivo de log (default: stderr)

set -e

# ===== Validacao =====
if [ -z "$1" ]; then
  echo "ERRO: uso: $0 <project-dir>" >&2
  exit 1
fi

PROJECT_DIR="$1"

# Detectar Node
if ! command -v node &> /dev/null; then
  echo "ERRO: Node.js nao encontrado. Instale Node 18+." >&2
  exit 2
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
echo "[init] Node version: $(node -v)"

if [ "$NODE_VERSION" -lt 18 ]; then
  echo "ERRO: Node 18+ requerido. Atual: $(node -v)" >&2
  exit 3
fi

# Garantir pnpm (skill oficial Anthropic usa pnpm — CAS store + hoisting
# deterministico resolvem bugs npm em ambientes peculiares como Render).
# Node 16.10+ traz corepack built-in que gerencia pnpm/yarn.
if ! command -v pnpm &> /dev/null; then
  echo "[init] pnpm nao encontrado — tentando corepack enable..."
  if command -v corepack &> /dev/null; then
    corepack enable 2>&1 | tail -5
    corepack prepare pnpm@latest --activate 2>&1 | tail -5
  else
    echo "[init] corepack indisponivel — instalando pnpm via npm -g..."
    npm install -g pnpm
  fi
fi
echo "[init] pnpm version: $(pnpm -v 2>&1)"

# Vite version: SEMPRE pinar em 5.4.11.
# Historico (IMP-2026-05-13-005/-006, 13/05/2026):
#   - Vite 6+/7+ (vite@latest no Render) puxa Rolldown/OXC/@swc como deps.
#   - Conflito de peer-deps com Parcel 2.12 faz pnpm/npm com --legacy-peer-deps
#     suprimir o erro e SILENCIOSAMENTE nao linkar tarballs em node_modules/@parcel/.
#   - Resultado: node_modules/@parcel/ existe mas VAZIO, parcel falha com
#     "Cannot find extended parcel config" via @parcel/core require interno.
# Fix: pinar 5.x ate migrar bundling para vite-plugin-singlefile (elimina Parcel).
VITE_VERSION="5.4.11"
echo "[init] Vite: $VITE_VERSION (pin obrigatorio — Vite 6+/7+ quebra Parcel 2.12)"

# Detectar sed (macOS vs Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
  SED_INPLACE="sed -i ''"
else
  SED_INPLACE="sed -i"
fi

# ===== Criar projeto =====
echo "[init] Criando projeto Vite em $PROJECT_DIR..."

# `pnpm create vite` NAO respeita path absoluto em todas as versoes.
# Workaround: separar parent + basename, rodar com basename relativo
# a partir do parent dir.
PARENT_DIR="$(dirname "$PROJECT_DIR")"
BASENAME="$(basename "$PROJECT_DIR")"

mkdir -p "$PARENT_DIR"
cd "$PARENT_DIR"

# create-vite cria pasta com nome BASENAME no cwd ($PARENT_DIR).
# pnpm create vite usa sintaxe direta: pnpm create vite <name> --template <tpl>
pnpm create vite "$BASENAME" --template react-ts

# Sanity: pasta foi criada?
if [ ! -d "$PROJECT_DIR" ]; then
    echo "ERRO: pnpm create vite nao criou $PROJECT_DIR" >&2
    exit 4
fi

cd "$PROJECT_DIR"

# Limpar template default — remover QUALQUER <link rel="icon" ...>
# (Vite 4.x usa /vite.svg, Vite 5.x usa /favicon.svg, futuras versoes podem mudar).
# Parcel falha resolvendo o asset se nao removermos, pois bundle.html nao tem
# nenhum favicon (e nem precisa — eh artifact embutido).
$SED_INPLACE '/<link rel="icon"/d' index.html
$SED_INPLACE 's/<title>.*<\/title>/<title>Artifact<\/title>/' index.html

# Tambem deletar o arquivo public/vite.svg ou public/favicon.svg se existir
# (Parcel ainda tenta processar arquivos do public/ — limpar evita surpresas).
rm -f public/vite.svg public/favicon.svg 2>/dev/null || true

# ===== Instalar baseline =====
echo "[init] Instalando dependencies baseline..."
pnpm install

# Pin Vite SEMPRE (compat Parcel 2.12, ver bloco de comentario no inicio).
# Mesmo em Node 20+: create-vite puxa Vite latest por padrao, e e necessario
# sobrescrever para 5.4.11 antes de qualquer outra dep ser resolvida.
echo "[init] Pinando Vite a $VITE_VERSION (sempre, compat Parcel)..."
pnpm add -D "vite@$VITE_VERSION"

# ===== Tailwind + utils =====
echo "[init] Instalando Tailwind + utils..."
pnpm add -D tailwindcss@3.4.1 postcss autoprefixer @types/node tailwindcss-animate
pnpm install class-variance-authority clsx tailwind-merge lucide-react

# ===== shadcn/ui — 40+ componentes (tarball oficial Anthropic) =====
# Caminho do tarball relativo ao script (SCRIPT_DIR resolvido via BASH_SOURCE)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPONENTS_TARBALL="$SCRIPT_DIR/shadcn-components.tar.gz"

if [ -f "$COMPONENTS_TARBALL" ]; then
    echo "[init] Instalando Radix UI deps (shadcn)..."
    pnpm install \
      @radix-ui/react-accordion @radix-ui/react-aspect-ratio @radix-ui/react-avatar \
      @radix-ui/react-checkbox @radix-ui/react-collapsible @radix-ui/react-context-menu \
      @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-hover-card \
      @radix-ui/react-label @radix-ui/react-menubar @radix-ui/react-navigation-menu \
      @radix-ui/react-popover @radix-ui/react-progress @radix-ui/react-radio-group \
      @radix-ui/react-scroll-area @radix-ui/react-select @radix-ui/react-separator \
      @radix-ui/react-slider @radix-ui/react-slot @radix-ui/react-switch \
      @radix-ui/react-tabs @radix-ui/react-toast @radix-ui/react-toggle \
      @radix-ui/react-toggle-group @radix-ui/react-tooltip
    pnpm install \
      sonner cmdk vaul embla-carousel-react react-day-picker \
      react-resizable-panels date-fns react-hook-form @hookform/resolvers zod next-themes
else
    echo "[init] AVISO: tarball nao encontrado em $COMPONENTS_TARBALL — pulando shadcn"
fi

# ===== Config Tailwind =====
echo "[init] Configurando Tailwind..."
# Parcel @parcel/transformer-postcss exige config em JSON puro (nao aceita
# JS CommonJS/ESM como Vite/Webpack). Usar .postcssrc.json e o formato
# canonico para Parcel. Remover quaisquer postcss.config.* gerados pelo
# create-vite para nao confundir.
rm -f postcss.config.js postcss.config.cjs postcss.config.mjs
cat > .postcssrc.json << 'EOF'
{
  "plugins": {
    "tailwindcss": {},
    "autoprefixer": {}
  }
}
EOF

cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
EOF

# ===== index.css com Tailwind + design tokens =====
echo "[init] Criando index.css..."
cat > src/index.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 0 0% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 0 0% 3.9%;
    --primary: 0 0% 9%;
    --primary-foreground: 0 0% 98%;
    --secondary: 0 0% 96.1%;
    --secondary-foreground: 0 0% 9%;
    --muted: 0 0% 96.1%;
    --muted-foreground: 0 0% 45.1%;
    --accent: 0 0% 96.1%;
    --accent-foreground: 0 0% 9%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 89.8%;
    --input: 0 0% 89.8%;
    --ring: 0 0% 3.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 0 0% 3.9%;
    --foreground: 0 0% 98%;
    --card: 0 0% 3.9%;
    --card-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 0 0% 9%;
    --secondary: 0 0% 14.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 0 0% 14.9%;
    --muted-foreground: 0 0% 63.9%;
    --accent: 0 0% 14.9%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 14.9%;
    --input: 0 0% 14.9%;
    --ring: 0 0% 83.1%;
  }
}

@layer base {
  * { @apply border-border; }
  body { @apply bg-background text-foreground; }
}
EOF

# ===== Path aliases =====
echo "[init] Configurando path aliases @/..."
node -e "
const fs = require('fs');
const config = JSON.parse(fs.readFileSync('tsconfig.json', 'utf8'));
config.compilerOptions = config.compilerOptions || {};
config.compilerOptions.baseUrl = '.';
config.compilerOptions.paths = { '@/*': ['./src/*'] };
fs.writeFileSync('tsconfig.json', JSON.stringify(config, null, 2));
"

# tsconfig.app.json (Vite 5.x cria esse arquivo separado)
if [ -f "tsconfig.app.json" ]; then
  node -e "
  const fs = require('fs');
  const content = fs.readFileSync('tsconfig.app.json', 'utf8');
  const stripped = content.split('\n').filter(l => !l.trim().startsWith('//')).join('\n');
  const config = JSON.parse(stripped.replace(/\/\*[\s\S]*?\*\//g, '').replace(/,(\s*[}\]])/g, '\$1'));
  config.compilerOptions = config.compilerOptions || {};
  config.compilerOptions.baseUrl = '.';
  config.compilerOptions.paths = { '@/*': ['./src/*'] };
  fs.writeFileSync('tsconfig.app.json', JSON.stringify(config, null, 2));
  "
fi

cat > vite.config.ts << 'EOF'
import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
EOF

# ===== Lib utils (cn helper) =====
mkdir -p src/lib
cat > src/lib/utils.ts << 'EOF'
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
EOF

# ===== Extrair tarball oficial shadcn (40+ componentes) =====
if [ -f "$COMPONENTS_TARBALL" ]; then
    echo "[init] Extraindo shadcn components do tarball..."
    tar -xzf "$COMPONENTS_TARBALL" -C src/
    echo "[init] shadcn OK — 40+ componentes em src/components/ui/"
else
    # Fallback se tarball nao baixou: criar baseline manual
    echo "[init] Fallback: criando 7 componentes baseline (sem Radix)..."
    mkdir -p src/components/ui

    cat > src/components/ui/button.tsx << 'EOF'
import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
type Size = "default" | "sm" | "lg" | "icon";

const variants: Record<Variant, string> = {
  default: "bg-primary text-primary-foreground hover:bg-primary/90",
  destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
  outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  ghost: "hover:bg-accent hover:text-accent-foreground",
  link: "text-primary underline-offset-4 hover:underline",
};
const sizes: Record<Size, string> = {
  default: "h-10 px-4 py-2",
  sm: "h-9 rounded-md px-3 text-xs",
  lg: "h-11 rounded-md px-8",
  icon: "h-10 w-10",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";
EOF

cat > src/components/ui/card.tsx << 'EOF'
import * as React from "react";
import { cn } from "@/lib/utils";

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)} {...props} />
  ),
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("text-2xl font-semibold leading-none tracking-tight", className)} {...props} />
  ),
);
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
  ),
);
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center p-6 pt-0", className)} {...props} />
  ),
);
CardFooter.displayName = "CardFooter";
EOF

cat > src/components/ui/input.tsx << 'EOF'
import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
EOF

cat > src/components/ui/label.tsx << 'EOF'
import * as React from "react";
import { cn } from "@/lib/utils";

export const Label = React.forwardRef<HTMLLabelElement, React.LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => (
    <label
      ref={ref}
      className={cn("text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70", className)}
      {...props}
    />
  ),
);
Label.displayName = "Label";
EOF

cat > src/components/ui/badge.tsx << 'EOF'
import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "secondary" | "destructive" | "outline";
const variants: Record<Variant, string> = {
  default: "border-transparent bg-primary text-primary-foreground",
  secondary: "border-transparent bg-secondary text-secondary-foreground",
  destructive: "border-transparent bg-destructive text-destructive-foreground",
  outline: "text-foreground",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: Variant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
EOF

cat > src/components/ui/separator.tsx << 'EOF'
import * as React from "react";
import { cn } from "@/lib/utils";

export interface SeparatorProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "horizontal" | "vertical";
}

export const Separator = React.forwardRef<HTMLDivElement, SeparatorProps>(
  ({ className, orientation = "horizontal", ...props }, ref) => (
    <div
      ref={ref}
      role="none"
      className={cn(
        "shrink-0 bg-border",
        orientation === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]",
        className,
      )}
      {...props}
    />
  ),
);
Separator.displayName = "Separator";
EOF

cat > src/components/ui/table.tsx << 'EOF'
import * as React from "react";
import { cn } from "@/lib/utils";

export const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <div className="relative w-full overflow-auto">
      <table ref={ref} className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  ),
);
Table.displayName = "Table";

export const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => (
    <thead ref={ref} className={cn("[&_tr]:border-b", className)} {...props} />
  ),
);
TableHeader.displayName = "TableHeader";

export const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => (
    <tbody ref={ref} className={cn("[&_tr:last-child]:border-0", className)} {...props} />
  ),
);
TableBody.displayName = "TableBody";

export const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(
  ({ className, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn("border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted", className)}
      {...props}
    />
  ),
);
TableRow.displayName = "TableRow";

export const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <th
      ref={ref}
      className={cn("h-12 px-4 text-left align-middle font-medium text-muted-foreground", className)}
      {...props}
    />
  ),
);
TableHead.displayName = "TableHead";

export const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <td ref={ref} className={cn("p-4 align-middle", className)} {...props} />
  ),
);
TableCell.displayName = "TableCell";
EOF

    echo "[init] shadcn baseline OK: button, card, input, label, badge, separator, table"
fi  # fim do fallback shadcn (tarball nao disponivel)

echo "[init] OK — projeto pronto em $PROJECT_DIR"
echo "[init] Worker deve preencher src/App.tsx (e outros componentes) e rodar bundle-artifact.sh"
