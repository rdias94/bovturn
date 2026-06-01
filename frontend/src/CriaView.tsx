import { useState } from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { projetarCria, type CriaEntrada, type CriaResultado } from "./api";

const PADRAO: Partial<CriaEntrada> = {
  matrizes: 1000,
  taxa_prenhez: 0.85,
  mortalidade_bezerro: 0.04,
  idade_primeiro_parto_meses: 36,
  taxa_descarte_vacas: 0.16,
  taxa_crescimento_rebanho: 0.0,
  peso_desmame_kg: 210,
  preco_kg_bezerro: 13.5,
  custo_pasto_arrendamento: 480,
  custo_sal_mineral: 180,
  custo_sanidade: 90,
  custo_mao_de_obra: 150,
  custo_outros: 60,
  anos: 5,
};

const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const COR: Record<string, string> = { bom: "#059669", atencao: "#d97706", ruim: "#dc2626" };

export default function CriaView() {
  const [form, setForm] = useState<Partial<CriaEntrada>>(PADRAO);
  const [res, setRes] = useState<CriaResultado | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function set(k: keyof CriaEntrada, v: string) {
    setForm({ ...form, [k]: parseFloat(v.replace(",", ".")) || 0 });
  }

  async function projetar() {
    setErro(null);
    setCarregando(true);
    try {
      setRes(await projetarCria(form));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha na projeção");
    } finally {
      setCarregando(false);
    }
  }

  const inp = "w-full rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm outline-none focus:border-emerald-500";
  const repro: [keyof CriaEntrada, string, string][] = [
    ["matrizes", "Matrizes (expostas)", "1"],
    ["taxa_prenhez", "Prenhez (0-1)", "0.01"],
    ["mortalidade_bezerro", "Mort. bezerro (0-1)", "0.01"],
    ["idade_primeiro_parto_meses", "Idade 1º parto (meses)", "1"],
    ["taxa_descarte_vacas", "Descarte vacas (0-1)", "0.01"],
    ["taxa_crescimento_rebanho", "Crescim. rebanho (0-1)", "0.01"],
    ["peso_desmame_kg", "Peso desmame (kg)", "1"],
    ["preco_kg_bezerro", "Preço bezerro (R$/kg)", "0.1"],
  ];
  const custos: [keyof CriaEntrada, string][] = [
    ["custo_pasto_arrendamento", "Pasto/arrend."],
    ["custo_sal_mineral", "Sal/mineral"],
    ["custo_sanidade", "Sanidade"],
    ["custo_mao_de_obra", "Mão de obra"],
    ["custo_outros", "Outros"],
  ];
  const r = res?.resumo;
  const rp = res?.reprodutivo;

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-4">
      <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold text-neutral-900">Cria — rebanho + reprodutivo</h2>
        <p className="mb-3 text-xs text-neutral-500">Quem produz bezerro são as fêmeas expostas. Custo da vaca por componentes (R$/vaca/ano).</p>
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          {repro.map(([k, label, step]) => (
            <label key={k} className="block">
              <span className="text-[11px] text-neutral-500">{label}</span>
              <input type="number" step={step} className={inp} value={form[k] as number} onChange={(e) => set(k, e.target.value)} />
            </label>
          ))}
        </div>
        <p className="mb-1 mt-3 text-[11px] font-medium text-neutral-500">Custo da vaca/ano (R$/vaca) — por componente</p>
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-5">
          {custos.map(([k, label]) => (
            <label key={k} className="block">
              <span className="text-[11px] text-neutral-500">{label}</span>
              <input type="number" step="1" className={inp} value={form[k] as number} onChange={(e) => set(k, e.target.value)} />
            </label>
          ))}
        </div>
        <button onClick={projetar} disabled={carregando}
          className="mt-3 rounded-xl bg-emerald-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-40">
          {carregando ? "Projetando…" : "Projetar rebanho"}
        </button>
        {erro && <p className="mt-2 text-sm text-red-600">{erro}</p>}
      </div>

      {r && rp && res && (
        <>
          <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold text-neutral-900">Índices reprodutivos</h3>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <Ind t="Prenhez" v={`${rp.taxa_prenhez_pct}%`} verdito={rp.taxa_prenhez_verdito} />
              <Ind t="Natalidade" v={`${rp.taxa_natalidade_pct}%`} verdito="" />
              <Ind t="Desmame" v={`${rp.taxa_desmame_pct}%`} verdito={rp.taxa_desmame_verdito} />
              <Ind t="Mort. bezerro" v={`${rp.mortalidade_bezerro_pct}%`} verdito={rp.mortalidade_verdito} />
              <Ind t="IEP" v={`${rp.iep_meses} m`} verdito={rp.iep_verdito} />
              <Ind t="Idade 1º parto" v={`${rp.idade_primeiro_parto_meses} m`} verdito={rp.ipp_verdito} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi t="Custo da vaca/ano" v={brl(r.custo_vaca_ano)} s="soma dos componentes" cor="#1f4e5f" />
            <Kpi t="Custo do bezerro" v={brl(r.custo_por_bezerro)} s="custo total ÷ desmamados" cor="#1f4e5f" />
            <Kpi t="Lucro por bezerro" v={brl(r.lucro_por_bezerro)} s={`venda ${brl(r.preco_venda_bezerro)}`} cor={r.viavel ? "#059669" : "#dc2626"} />
            <Kpi t="Lucro/vaca exposta" v={brl(r.lucro_por_vaca_exposta)} s={`${r.kg_desmamado_por_vaca}kg desmamado/vaca · desfrute ${r.desfrute_pct}%`} cor={r.lucro_por_vaca_exposta >= 0 ? "#059669" : "#dc2626"} />
          </div>

          <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
            <h3 className="mb-2 text-sm font-semibold text-neutral-900">Lucro total por ano</h3>
            <div className="h-44">
              <ResponsiveContainer>
                <BarChart data={res.anos} margin={{ left: 4, right: 8, top: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="ano" fontSize={11} />
                  <YAxis fontSize={11} tickFormatter={(v) => `${(v / 1e6).toFixed(1)}M`} />
                  <Tooltip formatter={(v: any) => brl(Number(v))} />
                  <Bar dataKey="lucro_total" fill="#059669" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Ind({ t, v, verdito }: { t: string; v: string; verdito: string }) {
  const cor = COR[verdito];
  return (
    <div className="rounded-xl border border-neutral-100 bg-neutral-50 p-2.5">
      <p className="text-[11px] text-neutral-500">{t}</p>
      <p className="text-lg font-bold" style={{ color: cor ?? "#0f172a" }}>{v}</p>
      {cor && <p className="text-[10px]" style={{ color: cor }}>{verdito === "bom" ? "● bom" : verdito === "atencao" ? "● atenção" : "● ruim"}</p>}
    </div>
  );
}

function Kpi({ t, v, s, cor }: { t: string; v: string; s: string; cor: string }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-3 shadow-sm">
      <p className="text-xs text-neutral-500">{t}</p>
      <p className="mt-1 text-xl font-bold" style={{ color: cor }}>{v}</p>
      <p className="text-[11px] text-neutral-400">{s}</p>
    </div>
  );
}
