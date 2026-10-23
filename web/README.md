# Frontend do PizzaDev

Base em Next.js com App Router, React, TypeScript estrito, Tailwind CSS e ESLint.
Use Node.js 22.13 ou superior da linha 22 (`.nvmrc`) e npm 10 ou superior. O `package-lock.json` registra as
versões instaladas e deve ser versionado.

## Executar

Dentro de `web/`:

```bash
npm ci
npm run dev
```

Acesse <http://localhost:3000>. A página inicial é branca e intencionalmente vazia.
Não há dependência da API, chamadas de rede de negócio, login ou dados simulados.
Não é necessário criar um `.env` nesta etapa.

| Comando | Finalidade |
| --- | --- |
| `npm run dev` | Servidor de desenvolvimento |
| `npm run lint` | ESLint, sem avisos permitidos |
| `npm run typecheck` | Gera os tipos das rotas e verifica TypeScript |
| `npm run build` | Build de produção |
| `npm start` | Executa o build de produção |
| `npm run check` | Lint, tipos e build em sequência |

## Organização

```text
src/
└── app/
    ├── page.tsx       # Página inicial: /
    ├── globals.css
    └── layout.tsx
```

A estrutura contém apenas arquivos utilizados. Crie pastas de funcionalidades,
componentes compartilhados e integração HTTP quando houver implementação para elas.
Use o alias `@/` para importar de `src/`. Rotas e layouts ficam em `app/`.

## Renderização e evolução

A página inicial é um Server Component pré-renderizado no build. Não há
`output: "export"`: a aplicação mantém a possibilidade de renderizar conteúdo
dinâmico no servidor quando necessário. A execução de produção usa `next start`.

Desenvolvimento e build usam Webpack, suportado pelo Next.js, para compatibilidade
com ambientes que restringem as portas internas utilizadas pelo Turbopack.

Adicione `"use client"` somente aos componentes que precisarem de estado, eventos
ou APIs do navegador. O CSS global já importa Tailwind; não há identidade visual
definida e as fontes atuais são do sistema, sem download no build.

Quando os fluxos forem implementados, introduza as dependências necessárias para
consultas, carrinho e formulários. A integração HTTP será definida com base no
contrato OpenAPI concluído do FastAPI. Preços, permissões e regras
de pedidos permanecem sob responsabilidade da API. Segredos nunca devem usar
o prefixo público `NEXT_PUBLIC_`.

## Integração contínua

O workflow `../.github/workflows/web.yml` instala com `npm ci` e executa
`npm run check`. A verificação pode ser iniciada manualmente no GitHub Actions.
Nenhum serviço de backend ou banco de dados é necessário para validar esta base.

Referências: [instalação do Next.js](https://nextjs.org/docs/app/getting-started/installation),
[ESLint](https://nextjs.org/docs/app/api-reference/config/eslint) e
[Tailwind com Next.js](https://tailwindcss.com/docs/installation/framework-guides/nextjs).
