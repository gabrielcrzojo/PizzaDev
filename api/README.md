# API do PizzaDev

FastAPI, SQLAlchemy, JWT e Alembic. Implementa contas, catálogo e o ciclo completo
de pedidos, sem processamento de pagamentos. As rotas em português e os endpoints
existentes foram preservados. O frontend é independente e ainda não está integrado.

## Executar

Na raiz, use Python 3.10 ou superior:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
# Apenas no primeiro setup; preserve o .env existente.
cp api/.env.example api/.env
```

Defina `SECRET_KEY` com uma chave aleatória (`python -c 'import secrets;
print(secrets.token_hex(32))'`). `ALGORITHM` aceita HS256, HS384 ou HS512;
`ACCESS_TOKEN_EXPIRE_MINUTES` deve ser positivo. `DATABASE_URL` é opcional e
usa por padrão `api/banco.db`, independentemente do diretório de execução.
`CORS_ORIGINS` aceita origens explícitas separadas por vírgulas.
Para outro banco, instale o driver correspondente; a suíte valida SQLite.

```bash
python -m alembic -c api/alembic.ini upgrade head
python -m uvicorn app.main:app --app-dir api --reload
```

Swagger: <http://127.0.0.1:8000/docs>. O contrato OpenAPI fica em `/openapi.json`.
Execute migrações antes de iniciar cada nova versão; faça backup do banco existente.
A migração mantém pedidos/itens antigos, cujo `produto_id` permanece nulo.
Novos itens exigem um produto cadastrado.

## Endpoints

| Método e caminho | Permissão e comportamento |
| --- | --- |
| `GET /health` | Saúde da aplicação e conexão com o banco |
| `GET /auth/`, `GET /orders/` | Disponibilidade, compatibilidade com a versão inicial |
| `POST /auth/criar_conta` | Cadastro público: `nome`, `email`, `senha` |
| `POST /auth/login` | Login JSON: `email`, `senha`; retorna access e refresh token |
| `POST /auth/login.form` | OAuth2/Swagger: `username` recebe email |
| `POST /auth/refresh` | Refresh token no cabeçalho Bearer; retorna novo access token |
| `GET /auth/me` | Perfil da conta autenticada, sem hash de senha |
| `PATCH /auth/me` | Atualiza `nome` da própria conta |
| `GET /products/` | Catálogo público de produtos ativos |
| `GET /products/{produto_id}` | Detalhe público de produto ativo |
| `GET /products/admin` | Administrador: catálogo incluindo inativos |
| `POST /products/` | Administrador: cadastra produto |
| `PUT /products/{produto_id}` | Administrador: substitui dados do produto; permite reativação |
| `DELETE /products/{produto_id}` | Administrador: desativa sem apagar histórico |
| `POST /orders/pedido` | Cria pedido vazio; JSON `{"usuario": 1}`; retorna mensagem e `id` |
| `GET /orders/listar` | Cliente: próprios pedidos; administrador: todos; filtro `status` |
| `GET /orders/listar/pedidos-usuario` | Próprios pedidos, inclusive para administradores |
| `GET /orders/pedido/{id_pedido}` | Consulta total, status e itens |
| `POST /orders/pedido/adicionar-item/{id_pedido}` | JSON `produto_id`, `quantidade` |
| `PATCH /orders/pedido/{id_pedido}/itens/{id_item}` | JSON `quantidade` |
| `DELETE /orders/pedido/remover-item/{id_item}` | Remove item e recalcula total |
| `POST /orders/pedido/finalizar/{id_pedido}` | Confirma pedido com pelo menos um item |
| `POST /orders/pedido/cancelar/{id_pedido}` | Cancela pedido pendente ou finalizado |
| `PATCH /orders/pedido/{id_pedido}/status` | Administrador: avança a operação; JSON `status` |

Listagens usam `offset` (padrão 0) e `limit` (padrão 20, máximo 100), com ordem
estável: produtos por ID crescente, pedidos por ID decrescente.
Autenticação: `Authorization: Bearer <access_token>`. No Swagger use **Authorize**.
Refresh tokens não autorizam operações e access tokens não renovam a sessão.
Contas inativas são bloqueadas mesmo quando têm um token ainda válido.

Cadastros nunca concedem privilégios; emails são normalizados e únicos.
Senhas são armazenadas com bcrypt e limitadas a 72 bytes UTF-8, sem truncamento.
O refresh token tem validade de sete dias; não há revogação individual de sessão.

## Primeiro administrador e exemplo de uso

Cadastre uma conta pela API e promova-a por um comando local explícito:

```bash
cd api
python -m app.admin promover admin@example.com
```

Faça login com essa conta e crie um produto:

```json
{
  "nome": "Pizza de queijo",
  "descricao": "Pizza tradicional",
  "sabor": "Queijo",
  "tamanho": "M",
  "preco": "39.90",
  "ativo": true
}
```

O cliente consulta `/auth/me` para obter seu ID, cria um pedido, adiciona itens
com `{"produto_id": 1, "quantidade": 2}` e finaliza. O administrador acompanha
os pedidos e avança o status até a entrega. Nenhuma etapa exige pagamento.

## Regras de pedidos

- Clientes só consultam e alteram os próprios pedidos. Administradores podem
  operar pedidos de outros usuários ativos e criar pedidos para eles.
- Itens só podem ser alterados enquanto o pedido está `PENDENTE`.
- Cada inclusão aceita quantidade inteira entre 1 e 100. Inclusões repetidas
  criam linhas independentes, preservando o preço de cada momento.
- Preços são definidos pelo catálogo no servidor. O total usa `Decimal` e
  `Numeric(12,2)`. Valores monetários são strings decimais no JSON de resposta.
- O preço unitário, sabor e tamanho ficam registrados no item; alterações ou
  desativação do produto não alteram o histórico nem o preço acordado.
- Fluxo: `PENDENTE → FINALIZADO → PREPARANDO → EM_ENTREGA → ENTREGUE`.
  Finalização significa confirmação do pedido, sem cobrança.
- Cliente pode cancelar em `PENDENTE` ou `FINALIZADO`. Administrador também pode
  cancelar em `PREPARANDO`, pelo endpoint de status. Estados finais são imutáveis.
- Cada alteração é transacional. Uma versão do pedido impede que atualizações
  simultâneas sobrescrevam totais ou revertam estados silenciosamente.

Erros: `401` para token/credenciais inválidos; `403` para falta de permissão;
`404` para recurso ausente; `409` para estado ou versão conflitante; `422` para
entrada inválida. Cadastro duplicado mantém `400` por compatibilidade.
Após `409` concorrente, consulte o pedido antes de decidir repetir uma operação.

## Organização e validação

`app/main.py` compõe routers e CORS; `config.py` carrega configuração;
`models.py` define persistência; `schemas.py` define contratos; `services.py`
centraliza regras de pedidos; `dependencies.py` cuida das sessões e permissões;
os módulos de rotas organizam autenticação, catálogo e pedidos.
Comentários explicam decisões e regras relevantes. O ORM síncrono usa rotas
`def`, executadas pelo FastAPI fora do loop assíncrono.

```bash
pip install -r api/requirements-dev.txt
ruff check api
ruff format --check api
cd api
python -m unittest discover -s tests -v
```

A suíte HTTP usa uma chave exclusiva e bancos temporários, sem gravar no banco
local. Cobre autenticação, permissões, catálogo, ciclo de pedidos, cálculos,
concorrência e migrações. GitHub Actions executa essas verificações.

## Cobertura da referência

Referência fornecida: <https://youtu.be/Jcndo1UKBOM>. O vídeo não ficou acessível,
mas foi consultado o [material escrito oficial do curso de FastAPI da Hashtag](https://www.hashtagtreinamentos.com/curso-de-fastapi-python).
Ele descreve cadastro/login/refresh, criação, listagem, consulta, inclusão e remoção
de itens, cancelamento e finalização. Esses fluxos estão implementados e testados.
Preservamos o prefixo `/orders` e o campo `usuario` existentes neste repositório;
o material escrito usa `/pedidos` e apresenta variações de nomes entre as aulas.
A inclusão foi aprimorada para receber `produto_id` e buscar o preço no servidor.
Catálogo administrativo, atualização de quantidade, perfil, paginação e avanço
operacional até `ENTREGUE` complementam o escopo de referência.
