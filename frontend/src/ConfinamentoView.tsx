import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import {
  calcularConfinamento,
  matrizConfinamento,
  type EntradaConfinamento,
  type ResultadoConfinamento,
  type MatrizConfinamento,
} from "./api";

const PADRAO: EntradaConfinamento = {
  peso_entrada_kg: 420,
  gmd_inicial: 1.9,
  decaimento_gmd: 0.0095,
  rendimento_carcaca: 50,
  rendimento_ganho: 60,
  preco_compra_arroba: 300,
  preco_venda_arroba: 310,
  custo_kg_ms: 1.4,
  consumo_pct_pv: 2.2,
  diaria_operacional: 1.6,
  dias_max: 180,
};

const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

export default function ConfinamentoView() {
  const [form, setForm] = useState<EntradaConfinamento>(PADRAO);
  const [res, setRes] = useState<ResultadoConfinamento | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [matriz, setMatriz] = useState<MatrizConfinamento | null>(null);

  useEffect(() => {
    matrizConfinamento().then(setMatriz).catch(() => {});
  }, []);

  function set(k: keyof EntradaConfinamento, v: string) {
    setForm({ ...form, [k]: parseFloat(v.replace(",", ".")) || 0 });
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
    ["peso_entrada_kg", "Peso de entrada (kg)", "1"],
    ["gmd_inicial", "Ganho de peso inicial (kg/dia)", "0.01"],
    ["decaimento_gmd", "Queda do ganho por dia", "0.0001"],
    ["rendimento_carcaca", "Rend. carcaça entrada (%)", "0.1"],
    ["rendimento_ganho", "Rend. carcaça do ganho (%)", "0.1"],
    ["preco_compra_arroba", "Compra (R$/@ carcaça)", "1"],
    ["preco_venda_arroba", "Venda (R$/@ carcaça)", "1"],
    ["custo_kg_ms", "Custo kg MS (R$)", "0.01"],
    ["consumo_pct_pv", "Consumo MS (% PV)", "0.1"],
    ["diaria_operacional", "Diária operacional (R$)", "0.1"],
  ];

  const inp =
    "w-full rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm outline-none focus:border-emerald-500";
  const r = res?.resumo;

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-4">
      <form onSubmit={calcular} className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold text-neutral-900">Cenário de confinamento</h2>
        <p className="mb-3 text-xs text-neutral-500">
          O ganho cai ao longo do cocho — o motor acha os <b>dias ótimos</b> (lucro máximo).
        </p>
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
          {campos.map(([k, label, step]) => (
            <label key={k} className="block">
              <span className="text-[11px] text-neutral-500">{label}</span>
              <input type="number" step={step} className={inp} value={form[k]}
                onChange={(e) => set(k, e.target.value)} required />
            </label>
          ))}
        </div>
        <button type="submit" disabled={carregando}
          className="mt-3 rounded-xl bg-emerald-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-40">
          {carregando ? "Calculando…" : "Calcular curva"}
        </button>
        {erro && <p className="mt-2 text-sm text-red-600">{erro}</p>}
      </form>

      {r && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi titulo="Dias ótimos (cocho)" valor={`${r.dias_otimos}`} sub={`breakeven ${r.breakeven_dias ?? "—"} d`} cor="#1f4e5f" />
            <Kpi titulo="Lucro máximo/cab" valor={brl(r.lucro_maximo)} sub="no ponto ótimo" cor={r.viavel ? "#059669" : "#dc2626"} />
            <Kpi titulo="Ganho carcaça médio" valor={`${r.ganho_carcaca_medio} kg/d`} sub={`GMD ${r.gmd_medio} kg/d`} cor="#1f4e5f" />
            <Kpi titulo="Rend. carcaça" valor={`${r.rendimento_carcaca_entrada}→${r.rendimento_carcaca_saida}%`} sub="entrada → saída" cor="#1f4e5f" />
          </div>

          <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
            <h3 className="mb-1 text-sm font-semibold text-neutral-900">
              Lucro acumulado × dias de cocho
            </h3>
            <p className="mb-2 text-xs text-neutral-500">
              Linha sobe, atinge o pico (dias ótimos) e <b>cai</b> — confinar além disso queima lucro.
            </p>
            <div className="h-64">
              <ResponsiveContainer>
                <LineChart data={res!.curva} margin={{ left: 0, right: 12, top: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="dia" fontSize={11} label={{ value: "dias de cocho", position: "insideBottom", offset: -2, fontSize: 11 }} />
                  <YAxis fontSize={11} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
                  <Tooltip formatter={(v: any) => brl(Number(v))} labelFormatter={(d) => `Dia ${d}`} />
                  <ReferenceLine y={0} stroke="#94a3b8" />
                  <ReferenceLine x={r.dias_otimos} stroke="#059669" strokeDasharray="4 3"
                    label={{ value: `ótimo ${r.dias_otimos}d`, fontSize: 11, fill: "#059669", position: "top" }} />
                  <Line type="monotone" dataKey="lucro" stroke="#1f4e5f" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
              <Item r="Peso de saída" v={`${r.peso_saida_kg} kg`} />
              <Item r="@ entrada → saída" v={`${r.arroba_entrada} → ${r.arroba_saida}`} />
              <Item r="Custo @ produzida" v={brl(r.custo_arroba_produzida)} />
              <Item r="Ágio na reposição" v={`${brl(r.agio_cab)}/cab`} destaque={r.agio_cab > 0 ? "ruim" : "bom"} />
            </dl>
          </div>
        </>
      )}

      {matriz && <Heatmap matriz={matriz} />}
    </div>
  );
}

function Kpi({ titulo, valor, sub, cor }: { titulo: string; valor: string; sub: string; cor: string }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-3 shadow-sm">
      <p className="text-xs text-neutral-500">{titulo}</p>
      <p className="mt-1 text-xl font-bold" style={{ color: cor }}>{valor}</p>
      <p className="text-[11px] text-neutral-400">{sub}</p>
    </div>
  );
}

function Heatmap({ matriz }: { matriz: MatrizConfinamento }) {
  const todos = matriz.linhas.flatMap((l) => l.custos);
  const min = Math.min(...todos);
  const max = Math.max(...todos);
  const cor = (v: number) => {
    const t = max === min ? 0.5 : (v - min) / (max - min);
    return `hsl(${(1 - t) * 120}, 70%, 82%)`;
  };
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-neutral-900">Matriz · custo da @ produzida (R$/@)</h2>
      <p className="mb-3 text-xs text-neutral-500">
        Referência: ganho de carcaça (kg/dia) × custo da diária. Verde = mais barato.
      </p>
      <div className="overflow-x-auto">
        <table className="border-collapse text-[11px]">
          <thead>
            <tr>
              <th className="sticky left-0 bg-white px-2 py-1 text-left text-neutral-500">ganho \ diária</th>
              {matriz.diarias.map((d) => (
                <th key={d} className="px-2 py-1 font-medium text-neutral-600">{d.toFixed(2)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matriz.linhas.map((l) => (
              <tr key={l.ganho_carcaca}>
                <td className="sticky left-0 bg-white px-2 py-1 font-medium text-neutral-700">{l.ganho_carcaca.toFixed(3)}</td>
                {l.custos.map((c, j) => (
                  <td key={j} className="px-2 py-1 text-center text-neutral-800" style={{ background: cor(c) }}>{c.toFixed(0)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Item({ r, v, destaque }: { r: string; v: string; destaque?: "bom" | "ruim" }) {
  return (
    <div>
      <dt className="text-xs text-neutral-400">{r}</dt>
      <dd className={`font-semibold ${destaque === "bom" ? "text-emerald-600" : destaque === "ruim" ? "text-red-600" : "text-neutral-900"}`}>{v}</dd>
    </div>
  );
}
