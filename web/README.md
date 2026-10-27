# Frontend do PizzaDev

Protótipo em Next.js, React e TypeScript. Use Node.js 22.13+ da linha 22 e npm 10+.

```bash
npm ci
npm run dev
```

Abra http://localhost:3000. Não requer API ou variáveis de ambiente.

## Experiência

- Página editorial responsiva, inspirada nos modelos fornecidos.
- Animação inicial de entrada e rotação da pizza (1,4 s), repetível em “Mais uma fornada”. Respeita `prefers-reduced-motion`.
- Filtros Todas, Clássicas e Especiais; três sabores demonstrativos.
- Detalhe com tamanho, quantidade (1–20 por adição), preço calculado e informação de alérgenos.
- Sacola em memória: agrega sabor/tamanho, permite remover itens e concluir uma simulação. Recarregar limpa a sacola. Nenhum pedido real é enviado.
- Diálogos nativos com foco modal, fechamento por Escape e botões de fechar.

## Arquivos

`src/app/page.tsx`: catálogo e interações locais. `src/app/globals.css`: identidade visual, responsividade e animações. `public/images/`: três imagens geradas com ImageGen e README com os prompts completos.

## Validação

`npm run check` executa ESLint, TypeScript e build de produção. `npm start` executa o build. Desenvolvimento e produção usam Webpack.

Para validar manualmente: filtre Especiais; abra um produto; altere tamanho e quantidade; adicione à sacola; confira subtotal; remova um item; conclua a demonstração; verifique o estado vazio. Confira também navegação por teclado e viewport móvel.

A integração futura deve usar preços e regras da API; os dados atuais são exclusivamente demonstrativos.
