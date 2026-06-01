import { useEffect, useState } from "react";
import {
  listarClientes,
  cadastrarCliente,
  type Cliente,
  type NovoCliente,
} from "./api";

const VAZIO: NovoCliente = {
  nome: "",
  telefone: "+55",
  fazenda: "",
  estado: "",
  tem_sequeiro: false,
  tem_irrigado: false,
  forrageiras: [],
};

export default function ClientesView() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [form, setForm] = useState<NovoCliente>(VAZIO);
  const [forrText, setForrText] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  function carregar() {
    listarClientes()
      .then(setClientes)
      .catch((e) => setErro(e.message));
  }

  useEffect(carregar, []);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setOk(null);
    setSalvando(true);
    try {
      const forrageiras = forrText
        .split(",")
        .map((f) => f.trim())
        .filter(Boolean);
      const r = await cadastrarCliente({
        ...form,
        estado: form.estado || undefined,
        forrageiras,
      });
      setOk(r.mensagem);
      setForm(VAZIO);
      setForrText("");
      carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao cadastrar");
    } finally {
      setSalvando(false);
    }
  }

  const campo =
    "w-full rounded-xl border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-emerald-500";

  return (
    <main className="mx-auto grid max-w-5xl gap-4 px-4 py-4 lg:grid-cols-[minmax(0,380px)_1fr]">
      {/* Formulário */}
      <section className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold text-neutral-900">
          Cadastrar cliente
        </h2>
        <p className="mb-3 text-xs text-neutral-500">
          O agente passa a responder com o contexto da fazenda deste número.
        </p>
        <form onSubmit={salvar} className="space-y-2.5">
          <input
            className={campo}
            placeholder="Nome do produtor"
            value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
            required
          />
          <input
            className={campo}
            placeholder="WhatsApp (+55 65 9...)"
            value={form.telefone}
            onChange={(e) => setForm({ ...form, telefone: e.target.value })}
            required
          />
          <input
            className={campo}
            placeholder="Nome da fazenda"
            value={form.fazenda}
            onChange={(e) => setForm({ ...form, fazenda: e.target.value })}
            required
          />
          <input
            className={`${campo} w-24`}
            placeholder="UF"
            maxLength={2}
            value={form.estado}
            onChange={(e) => setForm({ ...form, estado: e.target.value })}
          />
          <div>
            <span className="text-xs text-neutral-500">
              Sistema (pode ter os dois)
            </span>
            <div className="mt-1 flex gap-4">
              <label className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={form.tem_sequeiro}
                  onChange={(e) =>
                    setForm({ ...form, tem_sequeiro: e.target.checked })
                  }
                />
                Sequeiro
              </label>
              <label className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={form.tem_irrigado}
                  onChange={(e) =>
                    setForm({ ...form, tem_irrigado: e.target.checked })
                  }
                />
                Irrigado
              </label>
            </div>
          </div>
          <label className="block">
            <span className="text-xs text-neutral-500">
              Forrageiras (separe por vírgula)
            </span>
            <input
              className={campo}
              placeholder="Ex: Miyagui, Mombaça, Marandu"
              value={forrText}
              onChange={(e) => setForrText(e.target.value)}
            />
          </label>
          <button
            type="submit"
            disabled={salvando}
            className="w-full rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {salvando ? "Salvando…" : "Cadastrar"}
          </button>
        </form>
        {ok && (
          <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
            {ok}
          </p>
        )}
        {erro && (
          <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
            {erro}
          </p>
        )}
      </section>

      {/* Lista */}
      <section className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-neutral-900">
          Clientes cadastrados ({clientes.length})
        </h2>
        {clientes.length === 0 ? (
          <p className="text-sm text-neutral-400">Nenhum cliente ainda.</p>
        ) : (
          <ul className="divide-y divide-neutral-100">
            {clientes.map((c) => (
              <li
                key={c.telefone}
                className="flex items-center justify-between py-2.5"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-neutral-900">
                    {c.nome}
                  </p>
                  <p className="text-xs text-neutral-500">
                    {c.fazenda}
                    {c.estado ? ` · ${c.estado}` : ""} · {c.telefone}
                  </p>
                  {c.forrageiras.length > 0 && (
                    <p className="mt-0.5 truncate text-[11px] text-neutral-400">
                      🌱 {c.forrageiras.join(", ")}
                    </p>
                  )}
                </div>
                <div className="shrink-0 text-right">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      c.sistema === "irrigado"
                        ? "bg-sky-100 text-sky-700"
                        : c.sistema === "misto"
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {c.sistema}
                  </span>
                  <p className="mt-1 text-[11px] text-neutral-400">
                    {c.giros_historico} giro(s)
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
