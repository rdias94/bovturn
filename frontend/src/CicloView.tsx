import { useState } from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell,
} from "recharts";
import { calcularCiclo, compararCiclo, type CicloEntrada, type CicloResultado, type Intensidade } from "./api";

const PADRAO: Partial<CicloEntrada> = {
  peso_entrada_kg: 220,
  preco_kg_bezerro: 13.0,
  rc_entrada: 50,
  peso_transicao_kg: 380,
  gmd_aguas: 0.7,
  gmd_seca: 0.35,
  pct_periodo_aguas: 0.5,
  custo_pasto_recria_cab_mes: 15,
  custo_suplemento_recria_cab_mes: 25,
  custo_mdo_cab_mes: 10,
  custo_sanidade_cab_ano: 60,
  modo_engorda: "pasto",
  peso_final_kg: 540,
  rc_final: 53,
  arroba_abate_alvo: 0,
  gmd_engorda_pasto: 0.8,
  custo_engorda_pasto_cab_mes: 55,
  gmd_confinamento: 1.5,
  consumo_pct_pv_conf: 2.3,
  preco_saca_milho: 65,
  pct_milho_dieta: 0.56,
  custo_ms_outros: 0.86,
  diaria_operacional_conf: 1.6,
  preco_venda_arroba: 349.7,
};

const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const brl2 = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function CicloView() {
  const [form, setForm] = useState<Partial<CicloEntrada>>(PADRAO);
  const [res, setRes] = useState<CicloResultado | null>(null);
  const [comp, setComp] = useState<Intensidade[] | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function set(k: keyof CicloEntrada, v: string) {
    setForm({ ...form, [k]: parseFloat(v.replace(",", ".")) || 0 });
  }

  async function calcular() {
    setErro(null);
    setCarregando(true);
    try {
      const [r, c] = await Promise.all([calcularCiclo(form), compararCiclo(form)]);
      setRes(r);
      setComp(c.intensidades);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha no cálculo");
    } finally {
      setCarregando(false);
    }
  }

  const inp = "w-full rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm outline-none focus:border-emerald-500";
  const conf = form.modo_engorda === "confinamento";

  const compra: [keyof CicloEntrada, string, string][] = [
    ["peso_entrada_kg", "Bezerro entrada (kg)", "1"],
    ["preco_kg_bezerro", "Preço bezerro (R$/kg)", "0.1"],
    ["rc_entrada", "RC entrada (%)", "0.5"],
    ["preco_venda_arroba", "Venda boi gordo (R$/@)", "1"],
  ];
  const recria: [keyof CicloEntrada, string, string][] = [
    ["peso_transicao_kg", "Transição p/ engorda (kg)", "1"],
    ["gmd_aguas", "GMD águas (kg/d)", "0.05"],
    ["gmd_seca", "GMD seca (kg/d)", "0.05"],
    ["pct_periodo_aguas", "% do ciclo em águas (0-1)", "0.05"],
    ["custo_pasto_recria_cab_mes", "Pasto recria (R$/cab/mês)", "1"],
    ["custo_suplemento_recria_cab_mes", "Suplemento recria (R$/cab/mês)", "1"],
    ["custo_mdo_cab_mes", "Mão de obra (R$/cab/mês)", "1"],
    ["custo_sanidade_cab_ano", "Sanidade (R$/cab/ano)", "1"],
  ];
  const engPasto: [keyof CicloEntrada, string, string][] = [
    ["peso_final_kg", "Boi gordo final (kg)", "1"],
    ["rc_final", "RC abate (%)", "0.5"],
    ["gmd_engorda_pasto", "GMD engorda pasto (kg/d)", "0.05"],
    ["custo_engorda_pasto_cab_mes", "Custo engorda (R$/cab/mês)", "1"],
  ];
  const engConf: [keyof CicloEntrada, string, string][] = [
    ["peso_final_kg", "Boi gordo final (kg)", "1"],
    ["rc_final", "RC abate (%)", "0.5"],
    ["gmd_confinamento", "GMD confinamento (kg/d)", "0.05"],
    ["consumo_pct_pv_conf", "Consumo MS (%PV)", "0.1"],
    ["preco_saca_milho", "Milho (R$/saca)", "1"],
    ["pct_milho_dieta", "% milho na dieta (0-1)", "0.05"],
    ["custo_ms_outros", "Custo MS outros (R$/kg)", "0.01"],
    ["diaria_operacional_conf", "Diária operacional (R$)", "0.1"],
  ];

  const Grupo = ({ titulo, campos }: { titulo: string; campos: [keyof CicloEntrada, string, string][] }) => (
    <>
      <p className="mb-1 mt-3 text-[11px] font-medium text-neutral-500">{titulo}</p>
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {campos.map(([k, label, step]) => (
          <label key={k} className="block">
            <span className="text-[11px] text-neutral-500">{label}</span>
            <input type="number" step={step} className={inp} value={form[k] as number} onChange={(e) => set(k, e.target.value)} />
          </label>
        ))}
      </div>
    </>
  );

  const desembBars = res
    ? [
        { nome: "Bezerro", valor: res.desembolso.bezerro, pct: res.desembolso_pct.bezerro, cor: "#1f4e5f" },
        { nome: "Recria", valor: res.desembolso.recria, pct: res.desembolso_pct.recria, cor: "#5b8c5a" },
        { nome: "Engorda", valor: res.desembolso.engorda, pct: res.desembolso_pct.engorda, cor: "#d97706" },
      ]
    : [];

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-4">
      <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold text-neutral-900">Ciclo completo — Recria + Engorda</h2>
        <p className="mb-2 text-xs text-neutral-500">
          O giro inteiro: compra o bezerro, recria a pasto (GMD sazonal águas/seca) e termina a pasto ou em confinamento.
        </p>

        <div className="mb-1 flex gap-2">
          {(["pasto", "confinamento"] as const).map((m) => (
            <button key={m} onClick={() => setForm({ ...form, modo_engorda: m })}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${
                form.modo_engorda === m ? "bg-emerald-600 text-white" : "bg-neutral-100 text-neutral-600"
              }`}>
              Engorda: {m === "pasto" ? "a pasto" : "confinamento"}
            </button>
          ))}
        </div>

        <Grupo titulo="Compra & venda" campos={compra} />
        <Grupo titulo="Recria a pasto" campos={recria} />
        <Grupo titulo={conf ? "Engorda — confinamento" : "Engorda — a pasto"} campos={conf ? engConf : engPasto} />

        <button onClick={calcular} disabled={carregando}
          className="mt-3 rounded-xl bg-emerald-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-40">
          {carregando ? "Calculando…" : "Calcular ciclo"}
        </button>
        {erro && <p className="mt-2 text-sm text-red-600">{erro}</p>}
      </div>

      {res && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi t="Custo @ produzida" v={brl2(res.custo_arroba_produzida)} s="operacional ÷ @ produzidas" cor="#1f4e5f" />
            <Kpi t="GMD global do ciclo" v={`${res.gmd_global} kg/d`} s={`${res.meses_total} meses · ${res.dias_total} d`} cor="#1f4e5f" />
            <Kpi t="Lucro por cabeça" v={brl(res.lucro_cab)} s={`${brl2(res.lucro_arroba)}/@ produzida`} cor={res.viavel ? "#059669" : "#dc2626"} />
            <Kpi t="TIR" v={`${res.tir_am_pct}% a.m.`} s={`receita ${brl(res.receita)}`} cor={res.tir_am_pct > 0 ? "#059669" : "#dc2626"} />
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
              <h3 className="mb-3 text-sm font-semibold text-neutral-900">Fases do ciclo</h3>
              <Fase nome="Recria (pasto)" dias={res.dias_recria} meses={res.meses_recria} gmd={res.gmd_recria}
                de={res.peso_entrada_kg} ate={res.peso_transicao_kg} custo={res.custo_recria} cor="#5b8c5a" />
              <Fase nome={`Engorda (${res.modo_engorda})`} dias={res.dias_engorda} meses={res.meses_engorda} gmd={res.gmd_engorda}
                de={res.peso_transicao_kg} ate={res.peso_final_kg} custo={res.custo_engorda} cor="#d97706" />
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <Item r="@ entrada → final" v={`${res.arroba_entrada} → ${res.arroba_final}`} />
                <Item r="@ produzidas" v={`${res.arrobas_produzidas} @`} />
                <Item r="RC entrada → abate" v={`${res.rc_entrada}% → ${res.rc_final}%`} />
                <Item r="Custo total/@ (c/ bezerro)" v={brl2(res.custo_total_arroba)} />
              </dl>
            </div>

            <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
              <h3 className="mb-3 text-sm font-semibold text-neutral-900">Desembolso estratificado</h3>
              {desembBars.map((d) => (
                <div key={d.nome} className="mb-2.5">
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-neutral-600">{d.nome}</span>
                    <span className="font-semibold text-neutral-800">{brl(d.valor)} · {d.pct}%</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-neutral-100">
                    <div className="h-full rounded-full" style={{ width: `${d.pct}%`, background: d.cor }} />
                  </div>
                </div>
              ))}
              <p className="mt-3 text-[11px] text-neutral-400">
                Total {brl(res.custo_total)}/cab. O bezerro costuma ser o maior peso do giro completo.
              </p>
              {res.detalhe_engorda?.custo_kg_ms && (
                <p className="mt-1 text-[11px] text-neutral-400">
                  Dieta confinamento: {brl2(res.detalhe_engorda.custo_kg_ms)}/kgMS · {res.detalhe_engorda.cms_dia}kgMS/dia.
                </p>
              )}
            </div>
          </div>

          {comp && (
            <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
              <h3 className="mb-1 text-sm font-semibold text-neutral-900">Comparação de intensidades — qual entrega a @ mais barata?</h3>
              <p className="mb-3 text-xs text-neutral-500">
                Mesma compra/venda/pesos, três estratégias de recria+engorda. Verde = melhor custo da @.
              </p>
              <div className="h-44">
                <ResponsiveContainer>
                  <BarChart data={comp} margin={{ left: 4, right: 8, top: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="nome" fontSize={9} interval={0} tickFormatter={(v: string) => v.split(" ")[0]} />
                    <YAxis fontSize={11} tickFormatter={(v) => `R$${v}`} />
                    <Tooltip formatter={(v: any) => brl2(Number(v))} />
                    <Bar dataKey="custo_arroba_produzida" radius={[4, 4, 0, 0]}>
                      {comp.map((c, i) => <Cell key={i} fill={c.melhor ? "#059669" : "#94a3b8"} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-neutral-500">
                    <tr>
                      <th className="py-1 pr-2">Sistema</th><th className="px-2">Meses</th><th className="px-2">GMD global</th>
                      <th className="px-2">Custo @</th><th className="px-2">Lucro/cab</th><th className="px-2">TIR a.m.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comp.map((c) => (
                      <tr key={c.nome} className={`border-t border-neutral-100 ${c.melhor ? "bg-emerald-50" : ""}`}>
                        <td className="py-1.5 pr-2 font-medium text-neutral-800">{c.nome}{c.melhor && " ★"}</td>
                        <td className="px-2 text-neutral-600">{c.meses_total}</td>
                        <td className="px-2 text-neutral-600">{c.gmd_global}</td>
                        <td className="px-2 font-semibold" style={{ color: c.melhor ? "#059669" : "#0f172a" }}>{brl2(c.custo_arroba_produzida)}</td>
                        <td className="px-2 text-neutral-600">{brl(c.lucro_cab)}</td>
                        <td className="px-2 text-neutral-600">{c.tir_am_pct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Fase({ nome, dias, meses, gmd, de, ate, custo, cor }: {
  nome: string; dias: number; meses: number; gmd: number; de: number; ate: number; custo: number; cor: string;
}) {
  return (
    <div className="mb-2 flex items-center gap-3">
      <div className="h-8 w-1.5 rounded-full" style={{ background: cor }} />
      <div className="flex-1">
        <p className="text-sm font-medium text-neutral-800">{nome}</p>
        <p className="text-[11px] text-neutral-500">{de}→{ate}kg · {dias}d ({meses}m) · GMD {gmd}</p>
      </div>
      <span className="text-sm font-semibold text-neutral-700">{custo.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 })}</span>
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
