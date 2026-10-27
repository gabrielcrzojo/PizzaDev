# PizzaDev

Aplicação de delivery de pizzas, com backend em FastAPI e protótipo do frontend em Next.js, React, TypeScript
e Tailwind CSS. A interface possui catálogo demonstrativo, detalhes dos produtos, sacola local e animação inicial. O backend implementa autenticação, catálogo e o ciclo
completo de pedidos até a entrega, sem funcionalidades de pagamento.

## Estrutura

```text
.
├── api/
│   ├── app/              # Aplicação, rotas, modelos e configuração
│   ├── alembic/          # Migrações do banco de dados
│   ├── alembic.ini
│   ├── .env.example
│   └── requirements.txt
├── web/                  # Frontend Next.js (App Router)
│   ├── src/
│   │   └── app/          # Página inicial, layout e estilos globais
│   ├── package.json
│   └── package-lock.json
├── .github/workflows/    # Verificações do frontend
├── .gitignore
└── README.md
```

O ambiente virtual e os arquivos gerais do repositório ficam na raiz. A configuração
local (`api/.env`) e o banco SQLite (`api/banco.db`) são ignorados pelo Git.

## Executar a API

Na raiz do repositório, com Python 3.10 ou superior:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
cp api/.env.example api/.env
```

Se já existir `api/.env`, preserve sua configuração. Defina uma chave secreta
aleatória em `SECRET_KEY` antes de executar a aplicação.

```bash
python -m alembic -c api/alembic.ini upgrade head
python -m uvicorn app.main:app --app-dir api --reload
```

A documentação interativa fica em <http://127.0.0.1:8000/docs>.

Os comandos também podem ser executados dentro de `api/`, usando
`python -m alembic upgrade head` e `python -m uvicorn app.main:app --reload`.
O caminho do banco é fixado em `api/banco.db`, independentemente do diretório de execução.

Consulte [api/README.md](api/README.md) para os fluxos de autenticação,
o catálogo de endpoints, as permissões de pedidos, o provisionamento do primeiro
administrador e os comandos de teste.

## Referência

O projeto foi construído com base no [curso de FastAPI do canal Hashtag](https://youtube.com/playlist?list=PLpdAy0tYrnKy3TvpCT-x7kGqMQ5grk1Xq&si=dHZ_ALkBaDQ46cPr),
com adaptações e funcionalidades adicionais para o PizzaDev. Consulte também a
documentação da API para detalhes sobre os fluxos implementados.

## Frontend

Use Node.js 22.13 ou superior da linha 22 e npm 10 ou superior. O frontend funciona independentemente da API
e não precisa de variáveis de ambiente nesta etapa.

```bash
cd web
# Se usar nvm:
nvm install
nvm use
npm ci
npm run dev
```

Abra <http://localhost:3000>. O protótipo abre com a apresentação animada e o cardápio. A sacola funciona em memória e é reiniciada ao recarregar; não envia pedidos à API.

Para validar e executar a versão de produção:

```bash
npm run check
npm start
```

`check` executa lint, verificação de tipos e build. Esses mesmos passos são
executados pelo GitHub Actions em pushes e pull requests que alteram o frontend.
Consulte [web/README.md](web/README.md) para as convenções de organização.
