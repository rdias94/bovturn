import { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { analisarGiro, type AnaliseEntrada, type AnaliseResultado } from "./api";

const PADRAO: AnaliseEntrada = {
  peso_entrada_kg: 220,
  preco_compra_arroba: 300,
  preco_venda_arroba: 315,
  dias_giro: 240,
  sistema_hidrico: "irrigado",
  sistema_producao: "recria_engorda",
  sexo: "macho",
  area_ha: 100,
  lotacao_ua_ha: 10,
  custo_mdo_cab_mes: 9.86,
  custo_gastos_prod_cab_mes: 41.48,
  preco_saca_milho: 65,
};

const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

const COR = {
  bom: "#059669",
  atencao: "#d97706",
  ruim: "#dc2626",
  neutro: "#64748b",
};
const corVerdito = (v: string) => COR[v as keyof typeof COR] ?? COR.neutro;

export default function AnaliseView() {
  const [form, setForm] = useState<AnaliseEntrada>(PADRAO);
  const [res, setRes] = useState<AnaliseResultado | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function set(k: keyof AnaliseEntrada, v: string) {
    setForm({ ...form, [k]: k === "sistema_hidrico" ? v : parseFloat(v.replace(",", ".")) || 0 });
  }

  async function analisar() {
    setErro(null);
    setCarregando(true);
    try {
      setRes(await analisarGiro(form));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha na análise");
    } finally {
      setCarregando(false);
    }
  }

  const inp =
    "w-full rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm outline-none focus:border-emerald-500";

  return (
    <div className="mx-auto max-w-6xl px-4 py-4">
      {/* Form compacto */}
      <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 lg:grid-cols-6">
          <Campo l="Peso entrada (kg)"><input type="number" className={inp} value={form.peso_entrada_kg} onChange={(e) => set("peso_entrada_kg", e.target.value)} /></Campo>
          <Campo l="Compra (R$/@)"><input type="number" className={inp} value={form.preco_compra_arroba} onChange={(e) => set("preco_compra_arroba", e.target.value)} /></Campo>
          <Campo l="Venda (R$/@)"><input type="number" className={inp} value={form.preco_venda_arroba} onChange={(e) => set("preco_venda_arroba", e.target.value)} /></Campo>
          <Campo l="Dias de giro"><input type="number" className={inp} value={form.dias_giro} onChange={(e) => set("dias_giro", e.target.value)} /></Campo>
          <Campo l="Sistema">
            <select className={inp} value={form.sistema_hidrico} onChange={(e) => set("sistema_hidrico", e.target.value)}>
              <option value="sequeiro">Sequeiro</option>
              <option value="irrigado">Irrigado</option>
              <option value="confinamento">Confinamento</option>
            </select>
          </Campo>
          <Campo l="Milho (R$/sc)"><input type="number" className={inp} value={form.preco_saca_milho} onChange={(e) => set("preco_saca_milho", e.target.value)} /></Campo>
        </div>
        <button onClick={analisar} disabled={carregando} className="mt-3 rounded-xl bg-emerald-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-40">
          {carregando ? "Analisando 441 cenários…" : "Analisar"}
        </button>
        {erro && <p className="mt-2 text-sm text-red-600">{erro}</p>}
      </div>

      {!res ? (
        <p className="mt-8 text-center text-sm text-neutral-400">
          Rode a análise para ver o painel — varremos GMD × compra × venda e medimos tudo.
        </p>
      ) : (
        <div className="mt-4 space-y-4">
          {/* KPIs */}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi titulo="TIR ao mês" valor={`${res.metricas.tir_am_pct}%`} verdito={res.metricas.tir_am_verdito} sub="retorno mensal composto" />
            <Kpi titulo="Desembolso/cab/mês" valor={brl(res.metricas.desembolso_cab_mes)} verdito={res.metricas.desembolso_cab_mes_verdito} sub="custo operacional" />
            <Kpi titulo="Ágio do bezerro" valor={`${res.metricas.agio_bezerro_pct}%`} verdito={res.metricas.agio_bezerro_verdito} sub="@ compra vs @ venda" />
            <Kpi titulo="Troca @/milho" valor={`${res.metricas.relacao_troca_milho} sc`} verdito={res.metricas.relacao_troca_verdito} sub="sacas de milho por @" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {/* Visão estatística */}
            <Painel titulo={`Visão estatística · ${res.estatistica.n_cenarios} cenários`}>
              <div className="flex h-5 w-full overflow-hidden rounded-full">
                <div style={{ width: `${res.estatistica.pct_bom}%`, background: COR.bom }} />
                <div style={{ width: `${res.estatistica.pct_atencao}%`, background: COR.atencao }} />
                <div style={{ width: `${res.estatistica.pct_ruim}%`, background: COR.ruim }} />
              </div>
              <div className="mt-3 space-y-1.5 text-sm">
                <Legenda cor={COR.bom} label="Bom" v={`${res.estatistica.pct_bom}%`} />
                <Legenda cor={COR.atencao} label="Atenção" v={`${res.estatistica.pct_atencao}%`} />
                <Legenda cor={COR.ruim} label="Ruim (prejuízo)" v={`${res.estatistica.pct_ruim}%`} />
                <div className="mt-2 border-t border-neutral-100 pt-2 text-xs text-neutral-500">
                  Margem média <b className="text-neutral-800">{brl(res.estatistica.margem_media)}</b>/cab
                  · Faixa: {brl(res.estatistica.margem_min)} a {brl(res.estatistica.margem_max)}
                  · TIR média: {res.estatistica.tir_media_pct}% a.m.
                </div>
              </div>
            </Painel>

            {/* Perfil de desembolso */}
            <Painel titulo="Perfil de desembolso (R$/cab)">
              <div className="space-y-2">
                {Object.entries(res.metricas.perfil_desembolso)
                  .filter(([, v]) => v > 0)
                  .sort((a, b) => b[1] - a[1])
                  .map(([k, v], i) => {
                    const pct = res.metricas.perfil_desembolso_pct[k] ?? 0;
                    return (
                      <div key={k}>
                        <div className="flex justify-between text-xs">
                          <span className="text-neutral-600">{rotuloPerfil(k)}</span>
                          <span className="text-neutral-500">
                            {brl(v)} · {pct}%
                          </span>
                        </div>
                        <div className="mt-0.5 h-2 rounded bg-neutral-100">
                          <div
                            className="h-2 rounded"
                            style={{ width: `${pct}%`, background: PALETA[i % PALETA.length] }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            </Painel>
          </div>

          {/* Sensibilidade */}
          <div className="grid gap-4 lg:grid-cols-3">
            <CurvaPanel titulo="Margem × GMD" dados={res.sensibilidade.gmd} />
            <CurvaPanel titulo="Margem × Preço de compra" dados={res.sensibilidade.compra} />
            <CurvaPanel titulo="Margem × Preço de venda" dados={res.sensibilidade.venda} />
          </div>

          {/* Histograma */}
          <Painel titulo="Distribuição da margem/cab (todos os cenários)">
            <div className="h-48">
              <ResponsiveContainer>
                <BarChart data={res.histograma_margem}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="faixa" tickFormatter={(v) => brl(v)} fontSize={11} />
                  <YAxis fontSize={11} />
                  <Tooltip formatter={(v: any) => `${v} cenários`} labelFormatter={(v) => `≈ ${brl(Number(v))}/cab`} />
                  <Bar dataKey="n" radius={[4, 4, 0, 0]}>
                    {res.histograma_margem.map((d, i) => (
                      <Cell key={i} fill={d.faixa >= 0 ? COR.bom : COR.ruim} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Painel>

          {/* Score + benchmarks */}
          <Painel titulo="Como ler os números">
            <div className="grid gap-3 text-xs text-neutral-600 sm:grid-cols-2">
              <div>
                <b className="text-neutral-800">Score {res.base.score}/100 — {res.base.classificacao}</b>
                <p className="mt-1">Soma de: rentabilidade do giro (35), lucratividade (25), clima (20) e spread preço−custo da @ (20). &lt;40 alto risco · 40–66 moderado · 66–86 favorável · ≥86 muito favorável.</p>
              </div>
              <div>
                <b className="text-neutral-800">Cores das métricas</b>
                <p className="mt-1">🟢 bom · 🟡 atenção · 🔴 ruim, conforme parâmetros de referência (TIR ≥2%/mês, ágio &lt;20%, troca ≥3 sc/@, desembolso &lt;R$70/cab/mês). Ajustáveis.</p>
              </div>
            </div>
          </Painel>
        </div>
      )}
    </div>
  );
}

const PALETA = ["#059669", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ef4444", "#14b8a6"];
const rotuloPerfil = (k: string) =>
  ({
    compra_animal: "Compra",
    nutricao: "Nutrição",
    mao_de_obra: "Mão de obra",
    gastos_producao: "Gastos prod.",
    arrendamento: "Arrend.",
    sanidade: "Sanidade",
  })[k] ?? k;

function Campo({ l, children }: { l: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-[11px] text-neutral-500">{l}</span>
      {children}
    </label>
  );
}

function Kpi({ titulo, valor, verdito, sub }: { titulo: string; valor: string; verdito: string; sub: string }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-3 shadow-sm">
      <p className="text-xs text-neutral-500">{titulo}</p>
      <p className="mt-1 text-2xl font-bold" style={{ color: corVerdito(verdito) }}>
        {valor}
      </p>
      <p className="text-[11px] text-neutral-400">{sub}</p>
    </div>
  );
}

function Painel({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-neutral-900">{titulo}</h3>
      {children}
    </div>
  );
}

function Legenda({ cor, label, v }: { cor: string; label: string; v: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="size-3 rounded-sm" style={{ background: cor }} />
      <span className="text-neutral-600">{label}</span>
      <b className="ml-auto text-neutral-900">{v}</b>
    </div>
  );
}

function CurvaPanel({ titulo, dados }: { titulo: string; dados: { rotulo: string; margem_cab: number }[] }) {
  return (
    <Painel titulo={titulo}>
      <div className="h-40">
        <ResponsiveContainer>
          <LineChart data={dados} margin={{ left: -10, right: 8, top: 4 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="rotulo" fontSize={10} interval="preserveStartEnd" />
            <YAxis fontSize={10} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
            <Tooltip formatter={(v: any) => brl(Number(v))} />
            <Line type="monotone" dataKey="margem_cab" stroke="#059669" strokeWidth={2} dot={{ r: 2 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Painel>
  );
}
