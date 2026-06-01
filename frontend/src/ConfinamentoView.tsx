import { useEffect, useState } from "react";
import {
  calcularConfinamento,
  matrizConfinamento,
  type EntradaConfinamento,
  type ResultadoConfinamento,
  type MatrizConfinamento,
} from "./api";

const PADRAO: EntradaConfinamento = {
  diaria: 15.0,
  ganho_carcaca: 1.0,
  preco_venda: 330,
  custo_animal: 4400,
  dias: 100,
  arroba_entrada: 12,
};

const brl = (v: number) =>
  v.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });

export default function ConfinamentoView() {
  const [form, setForm] = useState<EntradaConfinamento>(PADRAO);
  const [res, setRes] = useState<ResultadoConfinamento | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [matriz, setMatriz] = useState<MatrizConfinamento | null>(null);

  useEffect(() => {
    matrizConfinamento().then(setMatriz).catch(() => {});
  }, []);

  function set(campo: keyof EntradaConfinamento, valor: string) {
    setForm({ ...form, [campo]: parseFloat(valor.replace(",", ".")) || 0 });
  }

  async function calcular(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      setRes(await calcularConfinamento(form));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha no cálculo");
    } finally {
      setCarregando(false);
    }
  }

  const campos: [keyof EntradaConfinamento, string, string][] = [
    ["diaria", "Custo da diária (R$/dia)", "0.01"],
    ["ganho_carcaca", "Ganho de carcaça (kg/dia)", "0.001"],
    ["preco_venda", "Preço de venda (R$/@)", "0.1"],
    ["custo_animal", "Custo do animal (R$/cab)", "1"],
    ["dias", "Dias de cocho", "1"],
    ["arroba_entrada", "@ de carcaça na entrada", "0.1"],
  ];

  const inp =
    "w-full rounded-xl border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-emerald-500";

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-4">
    <div className="grid gap-4 lg:grid-cols-[minmax(0,360px)_1fr]">
      <section className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold text-neutral-900">
          Cenário de confinamento
        </h2>
        <p className="mb-3 text-xs text-neutral-500">
          Custo da @ produzida e viabilidade por cabeça.
        </p>
        <form onSubmit={calcular} className="space-y-2.5">
          {campos.map(([k, label, step]) => (
            <label key={k} className="block">
              <span className="text-xs text-neutral-500">{label}</span>
              <input
                type="number"
                step={step}
                className={inp}
                value={form[k]}
                onChange={(e) => set(k, e.target.value)}
                required
              />
            </label>
          ))}
          <button
            type="submit"
            disabled={carregando}
            className="w-full rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {carregando ? "Calculando…" : "Calcular"}
          </button>
        </form>
        {erro && (
          <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
            {erro}
          </p>
        )}
      </section>

      <section className="space-y-3">
        {!res ? (
          <div className="rounded-2xl border border-dashed border-neutral-300 bg-white/50 p-6 text-center text-sm text-neutral-400">
            Preencha e calcule para ver o resultado do confinamento.
          </div>
        ) : (
          <>
            <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-neutral-900">
                  {res.semaforo} {res.viavel ? "Viável" : "Inviável"}
                </h2>
                <span
                  className={`text-2xl font-bold ${res.margem_cab >= 0 ? "text-emerald-600" : "text-red-600"}`}
                >
                  {brl(res.margem_cab)}
                  <span className="text-sm font-normal text-neutral-400">
                    {" "}
                    /cab
                  </span>
                </span>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <Item r="Custo da @ produzida" v={brl(res.custo_arroba_produzida)} />
                <Item r="@ produzidas" v={`${res.arrobas_produzidas} @`} />
                <Item r="@ final (carcaça)" v={`${res.arroba_final} @`} />
                <Item r="Preço de equilíbrio" v={`${brl(res.preco_equilibrio)}/@`} />
                <Item r="Custo alimentação" v={brl(res.custo_alimentacao)} />
                <Item r="Custo total/cab" v={brl(res.custo_total)} />
                <Item r="Receita/cab" v={brl(res.receita)} />
                <Item
                  r="Custo máx. do animal viável"
                  v={brl(res.custo_animal_max_viavel)}
                />
              </dl>
            </div>
            <p className="rounded-xl bg-neutral-100 px-3 py-2 text-xs text-neutral-500">
              Custo da @ = diária × 15 ÷ ganho de carcaça. Margem = (@ final ×
              preço) − custo do animal − dias × diária.
            </p>
          </>
        )}
      </section>
    </div>

      {matriz && <Heatmap matriz={matriz} />}
    </div>
  );
}

function Heatmap({ matriz }: { matriz: MatrizConfinamento }) {
  const todos = matriz.linhas.flatMap((l) => l.custos);
  const min = Math.min(...todos);
  const max = Math.max(...todos);
  // verde (custo baixo) → amarelo → vermelho (custo alto)
  const cor = (v: number) => {
    const t = max === min ? 0.5 : (v - min) / (max - min);
    const h = (1 - t) * 120; // 120=verde, 0=vermelho
    return `hsl(${h}, 70%, 82%)`;
  };
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-neutral-900">
        Matriz · custo da @ produzida (R$/@)
      </h2>
      <p className="mb-3 text-xs text-neutral-500">
        Linhas: ganho de carcaça (kg/dia) · Colunas: custo da diária (R$/dia).
        Verde = mais barato.
      </p>
      <div className="overflow-x-auto">
        <table className="border-collapse text-[11px]">
          <thead>
            <tr>
              <th className="sticky left-0 bg-white px-2 py-1 text-left text-neutral-500">
                ganho \ diária
              </th>
              {matriz.diarias.map((d) => (
                <th key={d} className="px-2 py-1 font-medium text-neutral-600">
                  {d.toFixed(2)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matriz.linhas.map((l) => (
              <tr key={l.ganho_carcaca}>
                <td className="sticky left-0 bg-white px-2 py-1 font-medium text-neutral-700">
                  {l.ganho_carcaca.toFixed(3)}
                </td>
                {l.custos.map((c, j) => (
                  <td
                    key={j}
                    className="px-2 py-1 text-center text-neutral-800"
                    style={{ background: cor(c) }}
                  >
                    {c.toFixed(0)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Item({ r, v }: { r: string; v: string }) {
  return (
    <div>
      <dt className="text-xs text-neutral-400">{r}</dt>
      <dd className="font-semibold text-neutral-900">{v}</dd>
    </div>
  );
}
