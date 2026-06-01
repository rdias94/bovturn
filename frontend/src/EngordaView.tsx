import { useState } from "react";
import { calcularEngorda, type EngordaEntrada, type EngordaResultado } from "./api";

const PADRAO: Partial<EngordaEntrada> = {
  peso_entrada_kg: 360,
  frame_score: 6,
  peso_vaca_adulta: 475,
  sexo: "macho",
  rendimento_carcaca: 53,
  gmd_esperado: 1.1,
  preco_compra_arroba: 330,
  preco_venda_arroba: 349.7,
  diaria_total: 6.5,
};

const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

export default function EngordaView() {
  const [form, setForm] = useState<Partial<EngordaEntrada>>(PADRAO);
  const [res, setRes] = useState<EngordaResultado | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function set(k: keyof EngordaEntrada, v: string | number) {
    setForm({ ...form, [k]: typeof v === "string" && k !== "sexo" ? parseFloat(v.replace(",", ".")) || 0 : v });
  }

  async function calcular() {
    setErro(null);
    setCarregando(true);
    try {
      setRes(await calcularEngorda(form));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha no cálculo");
    } finally {
      setCarregando(false);
    }
  }

  const inp = "w-full rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm outline-none focus:border-emerald-500";
  const r = res?.resultado;

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-4">
      <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold text-neutral-900">Engorda — peso de abate por frame score</h2>
        <p className="mb-3 text-xs text-neutral-500">
          O peso final sai do <b>frame</b>. Defina pelo <b>peso da vaca adulta</b> (jeito prático) — deixe 0 para usar o frame manual. Fonte: frame score Nelore (SciELO).
        </p>
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          <label className="block">
            <span className="text-[11px] text-neutral-500">Sexo</span>
            <select className={inp} value={form.sexo} onChange={(e) => set("sexo", e.target.value)}>
              <option value="macho">Macho</option>
              <option value="femea">Fêmea</option>
            </select>
          </label>
          <label className="block">
            <span className="text-[11px] font-medium text-emerald-700">Peso da vaca adulta (kg)</span>
            <input type="number" step="5" className={inp} value={form.peso_vaca_adulta}
              onChange={(e) => set("peso_vaca_adulta", e.target.value)} />
          </label>
          <label className="block">
            <span className="text-[11px] text-neutral-500">…ou frame direto (1–11): <b>{form.frame_score}</b></span>
            <input type="range" min={1} max={11} step={1} className="w-full" value={form.frame_score}
              onChange={(e) => { setForm({ ...form, frame_score: parseFloat(e.target.value), peso_vaca_adulta: 0 }); }} />
          </label>
          {([
            ["peso_entrada_kg", "Peso entrada (kg)", "1"],
            ["gmd_esperado", "GMD (kg/dia)", "0.01"],
            ["rendimento_carcaca", "Rend. carcaça (%)", "0.1"],
            ["preco_compra_arroba", "Compra (R$/@)", "1"],
            ["preco_venda_arroba", "Venda (R$/@)", "1"],
            ["diaria_total", "Diária total (R$/dia)", "0.1"],
          ] as [keyof EngordaEntrada, string, string][]).map(([k, label, step]) => (
            <label key={k} className="block">
              <span className="text-[11px] text-neutral-500">{label}</span>
              <input type="number" step={step} className={inp} value={form[k] as number} onChange={(e) => set(k, e.target.value)} />
            </label>
          ))}
        </div>
        <button onClick={calcular} disabled={carregando}
          className="mt-3 rounded-xl bg-emerald-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-40">
          {carregando ? "Calculando…" : "Calcular engorda"}
        </button>
        {erro && <p className="mt-2 text-sm text-red-600">{erro}</p>}
      </div>

      {r && res && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi t="Peso de abate" v={`${r.peso_abate_kg} kg`} s={`${r.arroba_abate}@ · frame ${r.frame_score} (${r.frame_origem})`} cor="#1f4e5f" />
            <Kpi t="Dias de engorda" v={`${r.dias}`} s={`${r.arrobas_produzidas}@ a produzir`} cor="#1f4e5f" />
            <Kpi t="Margem/cab" v={brl(r.margem_cab)} s={`TIR ${r.tir_am_pct}% a.m.`} cor={r.viavel ? "#059669" : "#dc2626"} />
            <Kpi t="Custo @ produzida" v={brl(r.custo_arroba_produzida)} s={`ágio ${brl(r.agio_cab)}/cab`} cor="#1f4e5f" />
          </div>

          <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
            <h3 className="mb-2 text-sm font-semibold text-neutral-900">
              Frame score → peso de abate ({r.sexo}) · cada ponto = 1@ de carcaça
            </h3>
            <div className="flex flex-wrap gap-2">
              {res.tabela_frame.map((t) => (
                <div key={t.frame}
                  className={`rounded-xl border px-3 py-2 text-center ${
                    t.frame === r.frame_score ? "border-emerald-500 bg-emerald-50" : "border-neutral-200 bg-neutral-50"
                  }`}>
                  <p className="text-[11px] text-neutral-500">frame {t.frame}</p>
                  <p className="text-sm font-bold text-neutral-900">{t.arroba_abate}@</p>
                  <p className="text-[11px] text-neutral-400">{t.peso_abate_kg} kg</p>
                </div>
              ))}
            </div>
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
