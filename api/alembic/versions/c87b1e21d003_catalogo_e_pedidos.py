"""Catálogo, valores decimais e controle de concorrência dos pedidos."""

import sqlalchemy as sa

from alembic import op

revision = "c87b1e21d003"
down_revision = "f2ddf0e0a5d5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "produtos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("descricao", sa.String(1000), nullable=False),
        sa.Column("sabor", sa.String(120), nullable=False),
        sa.Column("tamanho", sa.String(40), nullable=False),
        sa.Column("preco", sa.Numeric(12, 2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.CheckConstraint("preco > 0", name="ck_produtos_preco"),
    )
    # batch_alter_table preserva os dados também no SQLite, que não oferece
    # ALTER COLUMN. As tabelas filhas são reconstruídas após a tabela de pedidos.
    with op.batch_alter_table("pedidos") as batch:
        batch.alter_column("preco", existing_type=sa.Float(), type_=sa.Numeric(12, 2))
        batch.add_column(
            sa.Column("versao", sa.Integer(), nullable=False, server_default="1")
        )
        batch.create_check_constraint("ck_pedidos_preco", "preco >= 0")
    with op.batch_alter_table("pedidos") as batch:
        batch.alter_column("versao", server_default=None)
    with op.batch_alter_table("itens_pedido") as batch:
        batch.alter_column(
            "preco_unitario", existing_type=sa.Float(), type_=sa.Numeric(12, 2)
        )
        batch.add_column(sa.Column("produto_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_itens_produto", "produtos", ["produto_id"], ["id"])
        batch.create_check_constraint("ck_itens_quantidade", "quantidade > 0")
        batch.create_check_constraint("ck_itens_preco", "preco_unitario >= 0")

    op.create_index("ix_pedidos_usuario", "pedidos", ["usuario"])
    op.create_index("ix_itens_pedido_pedido", "itens_pedido", ["pedido"])


def downgrade():
    op.drop_index("ix_itens_pedido_pedido", table_name="itens_pedido")
    op.drop_index("ix_pedidos_usuario", table_name="pedidos")
    with op.batch_alter_table("itens_pedido") as batch:
        batch.drop_constraint("fk_itens_produto", type_="foreignkey")
        batch.drop_constraint("ck_itens_quantidade", type_="check")
        batch.drop_constraint("ck_itens_preco", type_="check")
        batch.drop_column("produto_id")
        batch.alter_column(
            "preco_unitario", existing_type=sa.Numeric(12, 2), type_=sa.Float()
        )
    with op.batch_alter_table("pedidos") as batch:
        batch.drop_constraint("ck_pedidos_preco", type_="check")
        batch.drop_column("versao")
        batch.alter_column("preco", existing_type=sa.Numeric(12, 2), type_=sa.Float())
    op.drop_table("produtos")
