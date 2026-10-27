"use client";
import Image from "next/image";
import { useRef, useState } from "react";
const pizzas = [
  {
    id: "margherita",
    name: "Margherita Verace",
    category: "Clássicas",
    price: 58,
    tag: "Vegetariana",
    description:
      "Tomate San Marzano, mozzarella de búfala, manjericão fresco e azeite extravirgem.",
  },
  {
    id: "diavola",
    name: "Diavola Artigianale",
    category: "Especiais",
    price: 68,
    tag: "Levemente picante",
    description:
      "Molho de tomate, fior di latte, salame picante artesanal e manjericão fresco.",
  },
  {
    id: "funghi",
    name: "Tartufo & Funghi",
    category: "Especiais",
    price: 76,
    tag: "Vegetariana",
    description:
      "Base bianca, mozzarella, cogumelos porcini, lâminas de trufa negra e tomilho.",
  },
];
const sizes = [
  { name: "Individual", cm: "25 cm · 4 fatias", extra: 0 },
  { name: "Média", cm: "30 cm · 6 fatias", extra: 20 },
  { name: "Grande", cm: "35 cm · 8 fatias", extra: 38 },
];
type Item = { id: number; size: number; qty: number };
const money = (n: number) =>
  n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
function Photo({ id, hero = false }: { id: string; hero?: boolean }) {
  return (
    <Image
      src={`/images/${id}.png`}
      alt={`Pizza ${pizzas.find((p) => p.id === id)?.name}, vista de cima`}
      width={1280}
      height={1280}
      preload={hero}
      sizes={
        hero
          ? "(max-width: 600px) 90vw, 50vw"
          : "(max-width: 600px) 85vw, 350px"
      }
    />
  );
}
export default function HomePage() {
  const [filter, setFilter] = useState("Todas"),
    [selected, setSelected] = useState(0),
    [size, setSize] = useState(0),
    [qty, setQty] = useState(1),
    [bag, setBag] = useState<Item[]>([]),
    [message, setMessage] = useState(""),
    [animation, setAnimation] = useState(0);
  const detail = useRef<HTMLDialogElement>(null),
    cart = useRef<HTMLDialogElement>(null);
  const pizza = pizzas[selected],
    count = bag.reduce((n, i) => n + i.qty, 0),
    total = bag.reduce(
      (n, i) => n + (pizzas[i.id].price + sizes[i.size].extra) * i.qty,
      0,
    );
  function choose(id: number) {
    setSelected(id);
    setSize(0);
    setQty(1);
    detail.current?.showModal();
  }
  function add() {
    setBag((old) =>
      old.some((i) => i.id === selected && i.size === size)
        ? old.map((i) =>
            i.id === selected && i.size === size
              ? { ...i, qty: i.qty + qty }
              : i,
          )
        : [...old, { id: selected, size, qty }],
    );
    detail.current?.close();
    setMessage(`${pizza.name} adicionada à sacola.`);
  }
  return (
    <>
      <header className="header">
        <a className="brand" href="#inicio">
          PizzaDev<sup>®</sup>
        </a>
        <nav aria-label="Navegação principal">
          <a href="#inicio">Início</a>
          <a href="#cardapio">Cardápio</a>
          <a href="#sobre">Nossa essência</a>
        </nav>
        <button
          className="bag"
          aria-label={`Abrir sacola, ${count} itens`}
          onClick={() => cart.current?.showModal()}
        >
          <svg
            width="18"
            height="21"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            aria-hidden="true"
          >
            <path d="M5 7h14l1 14H4L5 7Z" />
            <path d="M8 8V6a4 4 0 0 1 8 0v2" />
          </svg>
          <span>Sacola</span>
          <b>{count}</b>
        </button>
      </header>
      <main>
        <section className="hero" id="inicio">
          <div className="hero-copy">
            <h1>
              O simples.
              <br />O tempo.
              <br />
              <em>A boa pizza.</em>
            </h1>
            <p className="description">
              Massa leve, ingredientes de verdade e o abraço do forno a lenha.
              Um pedacinho de Nápoles, na sua mesa.
            </p>
            <a className="primary" href="#cardapio">
              Escolha sua pizza <span>↗</span>
            </a>
          </div>
          <div className="hero-art">
            <div className="orbit" />
            <div className="hero-pizza" key={animation}>
              <Photo id="margherita" hero />
            </div>
            <button
              className="replay"
              onClick={() => setAnimation((n) => n + 1)}
              aria-label="Repetir animação da pizza"
            >
              ↻ <span>Mais uma fornada</span>
            </button>
            <small className="caption">01 / MARGHERITA VERACE</small>
          </div>
        </section>
        <div className="principles">
          <i>Farinha, água, tempo e paixão.</i>
          <span>
            <b>48h</b> de fermentação
          </span>
          <span>
            <b>450°C</b> de puro calor
          </span>
          <span>
            <b>100%</b> artesanal
          </span>
        </div>
        <section className="menu" id="cardapio">
          <div className="section-title">
            <div>
              <p className="eyebrow">DA NOSSA COZINHA PARA VOCÊ</p>
              <h2>
                Encontre a sua <em>preferida.</em>
              </h2>
            </div>
          </div>
          <div className="toolbar">
            <div className="filters" aria-label="Categorias">
              {["Todas", "Clássicas", "Especiais"].map((f) => (
                <button
                  key={f}
                  aria-pressed={filter === f}
                  onClick={() => setFilter(f)}
                >
                  {f}
                  {filter === f ? " ·" : ""}
                </button>
              ))}
            </div>
          </div>
          <div className="grid">
            {pizzas.map(
              (p, index) =>
                (filter === "Todas" || filter === p.category) && (
                  <button
                    className="card"
                    key={p.id}
                    onClick={() => choose(index)}
                    aria-label={`Escolher ${p.name}`}
                  >
                    <div className="card-art">
                      <span className="number">0{index + 1}</span>
                      <span className="tag">{p.tag}</span>
                      <Photo id={p.id} />
                    </div>
                    <div className="card-info">
                      <p className="eyebrow">{p.category} · DA CASA</p>
                      <h3>{p.name}</h3>
                      <p>{p.description}</p>
                      <div className="card-bottom">
                        <span>
                          <small>A partir de</small>
                          <strong>{money(p.price)}</strong>
                        </span>
                        <span className="arrow">↗</span>
                      </div>
                    </div>
                  </button>
                ),
            )}
          </div>
        </section>
        <section className="about" id="sobre">
          <div>
            <p className="eyebrow">A NOSSA ESSÊNCIA</p>
            <h2>
              O ingrediente secreto
              <br />é <em>respeitar o tempo.</em>
            </h2>
            <p>
              Acreditamos que uma boa pizza começa muito antes do forno. No
              descanso da massa, na escolha dos ingredientes e no cuidado de
              quem faz.
            </p>
            <a href="#cardapio">Experimente essa história &nbsp; ↗</a>
          </div>
          <div>
            {[
              [
                "Devagar se faz melhor.",
                "48 horas de fermentação para uma massa leve, cheia de sabor e com bordas generosas.",
              ],
              [
                "O essencial, bem escolhido.",
                "Tomate, queijo, manjericão. Cada ingrediente tem seu lugar e sua razão de estar aqui.",
              ],
              [
                "O encontro com o fogo.",
                "O calor intenso do forno dá vida à crosta dourada e ao centro macio que a gente ama.",
              ],
            ].map(([title, text]) => (
              <article key={title}>
                <div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
        <section className="closing">
          <p className="eyebrow">BUON APPETITO!</p>
          <h2>
            Sua próxima boa memória
            <br />
            começa com uma <em>pizza.</em>
          </h2>
          <a className="primary" href="#cardapio">
            Vamos escolher? <span>↗</span>
          </a>
        </section>
      </main>
      <footer>
        <a className="brand" href="#inicio">
          PizzaDev®
        </a>
        <small>Protótipo interativo · Pedidos e valores demonstrativos</small>
      </footer>
      <div role="status" className="toast">
        {message && (
          <>
            <span>{message}</span>
            <button
              onClick={() => {
                setMessage("");
                cart.current?.showModal();
              }}
            >
              Ver sacola ↗
            </button>
            <button aria-label="Fechar aviso" onClick={() => setMessage("")}>
              ×
            </button>
          </>
        )}
      </div>
      <dialog
        ref={detail}
        aria-label={`Detalhes de ${pizza.name}`}
        className="product-dialog"
        onClick={(e) => {
          if (e.target === e.currentTarget) detail.current?.close();
        }}
      >
        <div className="dialog-top">
          <span className="eyebrow">DO FORNO PARA SUA MESA</span>
          <button
            className="close"
            aria-label="Fechar detalhe"
            onClick={() => detail.current?.close()}
          >
            ×
          </button>
        </div>
        <div className="product-layout">
          <div className="detail-art">
            <Photo id={pizza.id} />
          </div>
          <div className="product-info">
            <p className="eyebrow">{pizza.tag}</p>
            <h2>{pizza.name}</h2>
            <p>{pizza.description}</p>
            <p className="allergens">Contém glúten e leite.</p>
            <fieldset>
              <legend>Escolha o tamanho</legend>
              <div className="sizes">
                {sizes.map((s, i) => (
                  <button
                    key={s.name}
                    aria-pressed={size === i}
                    onClick={() => setSize(i)}
                  >
                    {s.name}
                    <small>{s.cm}</small>
                  </button>
                ))}
              </div>
            </fieldset>
            <div className="purchase">
              <div className="stepper">
                <button
                  aria-label="Diminuir quantidade"
                  disabled={qty === 1}
                  onClick={() => setQty((n) => n - 1)}
                >
                  −
                </button>
                <output aria-live="polite">{qty}</output>
                <button
                  aria-label="Aumentar quantidade"
                  disabled={qty === 20}
                  onClick={() => setQty((n) => n + 1)}
                >
                  +
                </button>
              </div>
              <strong>{money((pizza.price + sizes[size].extra) * qty)}</strong>
            </div>
            <button className="primary full" onClick={add}>
              Adicionar à sacola <span>↗</span>
            </button>
          </div>
        </div>
      </dialog>
      <dialog
        ref={cart}
        aria-label="Sua sacola"
        className="cart-dialog"
        onClick={(e) => {
          if (e.target === e.currentTarget) cart.current?.close();
        }}
      >
        <div className="dialog-top">
          <h2>
            Sua sacola <em>({count})</em>
          </h2>
          <button
            className="close"
            aria-label="Fechar sacola"
            onClick={() => cart.current?.close()}
          >
            ×
          </button>
        </div>
        {bag.length ? (
          <>
            {bag.map((item, index) => (
              <article className="cart-item" key={`${item.id}-${item.size}`}>
                <Photo id={pizzas[item.id].id} />
                <div>
                  <h3>{pizzas[item.id].name}</h3>
                  <p>
                    {sizes[item.size].name} · {item.qty} un.
                  </p>
                  <strong>
                    {money(
                      (pizzas[item.id].price + sizes[item.size].extra) *
                        item.qty,
                    )}
                  </strong>
                </div>
                <button
                  aria-label={`Remover ${pizzas[item.id].name} ${sizes[item.size].name}`}
                  onClick={() =>
                    setBag((old) => old.filter((_, i) => i !== index))
                  }
                >
                  ×
                </button>
              </article>
            ))}
            <div className="cart-total">
              <span>Subtotal</span>
              <strong>{money(total)}</strong>
            </div>
            <p className="demo-note">
              Esta é uma demonstração. Nenhum pedido ou pagamento será enviado.
            </p>
            <button
              className="primary full"
              onClick={() => {
                setBag([]);
                cart.current?.close();
                setMessage(
                  "Demonstração concluída! Nenhum pedido real foi enviado.",
                );
              }}
            >
              Concluir demonstração <span>✓</span>
            </button>
          </>
        ) : (
          <div className="empty">
            <span>♡</span>
            <h3>Uma boa pizza está esperando.</h3>
            <p>Escolha sua preferida para começar.</p>
            <button
              className="primary"
              onClick={() => {
                cart.current?.close();
                document.getElementById("cardapio")?.scrollIntoView();
              }}
            >
              Explorar cardápio ↗
            </button>
          </div>
        )}
      </dialog>
    </>
  );
}
