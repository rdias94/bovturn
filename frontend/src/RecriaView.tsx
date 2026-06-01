import { useState } from "react";
import { calcularRecria, type RecriaEntrada, type RecriaResultado } from "./api";

const PADRAO: Partial<RecriaEntrada> = {
  peso_entrada_kg: 200,
  peso_saida_kg: 400,
  gmd: 0.6,
  preco_kg_compra: 13,
  preco_kg_venda: 11.5,
  custo_kg_suplemento: 2.5,
  custo_mdo_cab_mes: 12,
  custo_gastos_prod_cab_mes: 18,
  custo_sanidade_cab: 25,
};

const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

export default function RecriaView() {
  const [form, setForm] = useState<Partial<RecriaEntrada>>(PADRAO);
  const [res, setRes] = useState<RecriaResultado | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function set(k: keyof RecriaEntrada, v: string) {
    setForm({ ...form, [k]: parseFloat(v.replace(",", ".")) || 0 });
  }

  async function calcular() {
    setErro(null);
    setCarregando(true);
    try {
      setRes(await calcularRecria(form));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha no cálculo");
    } finally {
      setCarregando(false);
    }
  }

  const inp = "w-full rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm outline-none focus:border-emerald-500";
  const campos: [keyof RecriaEntrada, string, string][] = [
    ["peso_entrada_kg", "Bezerro entrada (kg)", "1"],
    ["peso_saida_kg", "Boi magro saída (kg)", "1"],
    ["gmd", "GMD (kg/dia)", "0.01"],
    ["preco_kg_compra", "Compra bezerro (R$/kg)", "0.1"],
    ["preco_kg_venda", "Venda magro (R$/kg)", "0.1"],
    ["custo_kg_suplemento", "Custo suplemento (R$/kg)", "0.1"],
    ["custo_mdo_cab_mes", "MDO (R$/cab/mês)", "0.5"],
    ["custo_gastos_prod_cab_mes", "Gastos prod. (R$/cab/mês)", "0.5"],
    ["custo_sanidade_cab", "Sanidade (R$/cab)", "1"],
  ];
  const r = res?.resultado;

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-4">
      <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold text-neutral-900">Recria — bezerro → boi magro</h2>
        <p className="mb-3 text-xs text-neutral-500">
          Compra o bezerro ao desmame (por kg) e leva até 390–420 kg para vender à engorda. Arrobas de peso vivo (30 kg).
        </p>
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
          {campos.map(([k, label, step]) => (
            <label key={k} className="block">
              <span className="text-[11px] text-neutral-500">{label}</span>
              <input type="number" step={step} className={inp} value={form[k] as number} onChange={(e) => set(k, e.target.value)} />
            </label>
          ))}
        </div>
        <button onClick={calcular} disabled={carregando}
          className="mt-3 rounded-xl bg-emerald-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-40">
          {carregando ? "Calculando…" : "Calcular recria"}
        </button>
        {erro && <p className="mt-2 text-sm text-red-600">{erro}</p>}
      </div>

      {r && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi t="Duração" v={`${r.dias} dias`} s={`${r.meses} meses · ${r.ganho_kg}kg`} cor="#1f4e5f" />
            <Kpi t="Margem/cab" v={brl(r.margem_cab)} s={`TIR ${r.tir_am_pct}% a.m.`} cor={r.viavel ? "#059669" : "#dc2626"} />
            <Kpi t="Custo @ produzida" v={brl(r.custo_arroba_produzida)} s={`${brl(r.custo_kg_produzido)}/kg`} cor="#1f4e5f" />
            <Kpi t="@ produzidas" v={`${r.arrobas_produzidas}@`} s={`${r.arroba_entrada} → ${r.arroba_saida}@ vivo`} cor="#1f4e5f" />
          </div>
          <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
              <Item r="Custo do bezerro" v={brl(r.custo_animal)} />
              <Item r="Custo operacional" v={brl(r.custo_operacional)} />
              <Item r="Custo total/cab" v={brl(r.custo_total)} />
              <Item r="Receita (venda magro)" v={brl(r.receita)} />
            </dl>
          </div>
        </>
      )}
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

function Item({ r, v }: { r: string; v: string }) {
  return (
    <div>
      <dt className="text-xs text-neutral-400">{r}</dt>
      <dd className="font-semibold text-neutral-900">{v}</dd>
    </div>
  );
}
