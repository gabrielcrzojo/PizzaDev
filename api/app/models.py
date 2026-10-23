from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, relationship

from .config import DATABASE_URL

# As rotas síncronas podem atender requisições SQLite em threads diferentes.
db = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
    pool_pre_ping=True,
)


def habilitar_chaves_estrangeiras(conexao, _registro):
    """Faz o SQLite aplicar os vínculos entre usuários, pedidos e itens."""
    cursor = conexao.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


if db.dialect.name == "sqlite":
    event.listen(db, "connect", habilitar_chaves_estrangeiras)


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column("nome", String)
    email = Column("email", String, nullable=False, unique=True)
    senha = Column("senha", String, nullable=False)
    ativo = Column("ativo", Boolean, default=True)
    admin = Column("admin", Boolean, default=False)

    def __init__(self, nome, email, senha, ativo=True, admin=False):
        self.nome = nome
        self.email = email
        self.senha = senha
        self.ativo = ativo
        self.admin = admin


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    status = Column("status", String, default="PENDENTE")
    usuario = Column(
        "usuario", Integer, ForeignKey("usuarios.id"), nullable=False, index=True
    )
    preco = Column("preco", Numeric(12, 2), nullable=False)

    versao = Column(Integer, nullable=False, default=1)
    itens = relationship("ItemPedido", order_by="ItemPedido.id", lazy="selectin")
    __mapper_args__ = {"version_id_col": versao}
    __table_args__ = (CheckConstraint("preco >= 0", name="ck_pedidos_preco"),)

    def __init__(self, status="PENDENTE", usuario=None, preco=0.0):
        self.status = status
        self.usuario = usuario
        self.preco = preco


class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    quantidade = Column("quantidade", Integer, nullable=False)
    sabor = Column("sabor", String, nullable=False)
    tamanho = Column("tamanho", String, nullable=False)
    preco_unitario = Column("preco_unitario", Numeric(12, 2), nullable=False)
    pedido = Column(
        "pedido", Integer, ForeignKey("pedidos.id"), nullable=False, index=True
    )

    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=True)
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_itens_quantidade"),
        CheckConstraint("preco_unitario >= 0", name="ck_itens_preco"),
    )

    def __init__(
        self, quantidade, sabor, tamanho, preco_unitario, pedido, produto_id=None
    ):
        self.produto_id = produto_id
        self.quantidade = quantidade
        self.sabor = sabor
        self.tamanho = tamanho
        self.preco_unitario = preco_unitario
        self.pedido = pedido


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    descricao = Column(String(1000), nullable=False, default="")
    sabor = Column(String(120), nullable=False)
    tamanho = Column(String(40), nullable=False)
    preco = Column(Numeric(12, 2), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)
    __table_args__ = (CheckConstraint("preco > 0", name="ck_produtos_preco"),)
