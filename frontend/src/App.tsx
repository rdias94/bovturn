import { useEffect, useRef, useState } from "react";
import {
  perguntarAgente,
  health,
  type RespostaAgente,
  type Cenario,
} from "./api";
import ClientesView from "./ClientesView";
import ConfinamentoView from "./ConfinamentoView";
import AnaliseView from "./AnaliseView";

interface Msg {
  autor: "voce" | "agente";
  texto: string;
}

const brl = (v?: number, dec = 0) =>
  v === undefined || v === null
    ? "—"
    : v.toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
        minimumFractionDigits: dec,
        maximumFractionDigits: dec,
      });

const EXEMPLOS = [
  "50 nelore macho 220kg a 10 reais o kg, irrigado",
  "comprei 80 garrotes de 300kg a 320 a arroba, quanto engorda em 4 meses?",
  "vale a pena 40 fêmeas de 200kg a 9 reais o kg no sequeiro?",
];

export default function App() {
  const [telefone, setTelefone] = useState("+5565999999999");
  const [texto, setTexto] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [sessao, setSessao] = useState<Record<string, unknown>>({});
  const [carregando, setCarregando] = useState(false);
  const [ultima, setUltima] = useState<RespostaAgente | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [banco, setBanco] = useState<string>("");
  const [aba, setAba] = useState<
    "agente" | "clientes" | "confinamento" | "analise"
  >("agente");
  const fimRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    health()
      .then((h) => setBanco(h.banco))
      .catch(() => setBanco("offline"));
  }, []);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, carregando]);

  async function enviar(msg?: string) {
    const conteudo = (msg ?? texto).trim();
    if (!conteudo || carregando) return;
    setErro(null);
    setTexto("");
    setMsgs((m) => [...m, { autor: "voce", texto: conteudo }]);
    setCarregando(true);
    try {
      const r = await perguntarAgente(conteudo, telefone, sessao);
      setMsgs((m) => [...m, { autor: "agente", texto: r.resposta }]);
      setSessao(r.contexto_sessao || {});
      setUltima(r);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha na conexão");
    } finally {
      setCarregando(false);
    }
  }

  function novaConversa() {
    setMsgs([]);
    setSessao({});
    setUltima(null);
    setErro(null);
  }

  const resumo = ultima?.resumo && !ultima.resumo.erro ? ultima.resumo : null;

  return (
    <div className="min-h-svh bg-neutral-100 text-neutral-800">
      {/* Cabeçalho */}
      <header className="sticky top-0 z-10 border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <img
              src="/pasture-logo.png"
              alt="Pasture — Aceleradora Pecuária"
              className="h-8 w-auto"
            />
            <span className="h-8 w-px bg-neutral-200" />
            <div className="leading-tight">
              <h1 className="text-base font-bold text-neutral-900">
                BovTurn Intelligence
              </h1>
              <p className="text-xs text-neutral-500">
                Agente de giro · pecuária de corte
              </p>
            </div>
          </div>
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
              banco === "conectado"
                ? "bg-emerald-100 text-emerald-700"
                : "bg-neutral-200 text-neutral-600"
            }`}
            title={`banco: ${banco}`}
          >
            {banco === "conectado" ? "● banco ao vivo" : `● ${banco || "..."}`}
          </span>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 px-4">
          {(["agente", "clientes", "confinamento", "analise"] as const).map(
            (t) => (
              <button
                key={t}
                onClick={() => setAba(t)}
                className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
                  aba === t
                    ? "border-emerald-600 text-emerald-700"
                    : "border-transparent text-neutral-500 hover:text-neutral-800"
                }`}
              >
                {t === "agente"
                  ? "Agente"
                  : t === "clientes"
                    ? "Clientes"
                    : t === "confinamento"
                      ? "Confinamento"
                      : "Análise"}
              </button>
            ),
          )}
        </nav>
      </header>

      {aba === "clientes" && <ClientesView />}
      {aba === "confinamento" && <ConfinamentoView />}
      {aba === "analise" && <AnaliseView />}

      {aba === "agente" && (
      <main className="mx-auto grid max-w-5xl gap-4 px-4 py-4 lg:grid-cols-[1fr_minmax(0,420px)]">
        {/* Coluna do chat */}
        <section className="flex min-h-[60svh] flex-col rounded-2xl border border-neutral-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-neutral-100 px-4 py-2.5">
            <label className="flex items-center gap-2 text-xs text-neutral-500">
              Cliente (telefone)
              <input
                value={telefone}
                onChange={(e) => setTelefone(e.target.value)}
                className="w-40 rounded-lg border border-neutral-200 px-2 py-1 text-sm text-neutral-800 outline-none focus:border-emerald-500"
              />
            </label>
            <button
              onClick={novaConversa}
              className="rounded-lg px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-100"
            >
              nova conversa
            </button>
          </div>

          {/* Mensagens */}
          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {msgs.length === 0 && (
              <div className="mx-auto mt-6 max-w-md text-center">
                <p className="text-sm text-neutral-500">
                  Manda uma mensagem como você mandaria no WhatsApp. O agente
                  responde com a voz do consultor e calcula o giro.
                </p>
                <div className="mt-4 space-y-2">
                  {EXEMPLOS.map((ex) => (
                    <button
                      key={ex}
                      onClick={() => enviar(ex)}
                      className="block w-full rounded-xl border border-neutral-200 px-3 py-2 text-left text-sm text-neutral-600 hover:border-emerald-400 hover:bg-emerald-50"
                    >
                      “{ex}”
                    </button>
                  ))}
                </div>
              </div>
            )}

            {msgs.map((m, i) => (
              <div
                key={i}
                className={`flex ${m.autor === "voce" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm leading-relaxed ${
                    m.autor === "voce"
                      ? "rounded-br-sm bg-emerald-600 text-white"
                      : "rounded-bl-sm bg-neutral-100 text-neutral-800"
                  }`}
                >
                  {m.texto}
                </div>
              </div>
            ))}

            {carregando && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-sm bg-neutral-100 px-3.5 py-2 text-sm text-neutral-400">
                  digitando…
                </div>
              </div>
            )}
            {erro && (
              <div className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">
                {erro}
              </div>
            )}
            <div ref={fimRef} />
          </div>

          {/* Input */}
          <div className="border-t border-neutral-100 p-3">
            <div className="flex items-end gap-2">
              <textarea
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    enviar();
                  }
                }}
                rows={1}
                placeholder="Ex: 50 nelore macho 220kg a 10 reais o kg, irrigado"
                className="max-h-32 flex-1 resize-none rounded-xl border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
              />
              <button
                onClick={() => enviar()}
                disabled={carregando || !texto.trim()}
                className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
              >
                Enviar
              </button>
            </div>
          </div>
        </section>

        {/* Painel de resultado */}
        <aside className="space-y-3">
          {!resumo && (
            <div className="rounded-2xl border border-dashed border-neutral-300 bg-white/50 p-6 text-center text-sm text-neutral-400">
              Os números do giro aparecem aqui quando o agente tiver dados
              suficientes (peso + preço).
            </div>
          )}

          {resumo && (
            <>
              <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-neutral-900">
                    {resumo.semaforo} {resumo.classificacao}
                  </h2>
                  <span className="text-2xl font-bold text-neutral-900">
                    {resumo.score?.toFixed(0)}
                    <span className="text-sm font-normal text-neutral-400">
                      /100
                    </span>
                  </span>
                </div>
                {resumo.fonte_gmd && (
                  <p className="mt-1 text-xs text-neutral-500">
                    GMD {resumo.gmd_usado} kg/dia · {resumo.fonte_gmd}
                  </p>
                )}
                <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <Linha rotulo="Margem/cab" valor={brl(resumo.margem_cab)} />
                  <Linha
                    rotulo="Custo @ produzida"
                    valor={brl(resumo.custo_arroba)}
                  />
                  <Linha
                    rotulo="Lucro (base)"
                    valor={brl(resumo.lucro_base)}
                    destaque={(resumo.lucro_base ?? 0) >= 0 ? "bom" : "ruim"}
                  />
                  <Linha
                    rotulo="Lucro (pessimista)"
                    valor={brl(resumo.lucro_pessimista)}
                    destaque={resumo.pior_positivo ? "bom" : "ruim"}
                  />
                  <Linha
                    rotulo="Equilíbrio"
                    valor={`${brl(resumo.preco_equilibrio)}/@`}
                  />
                  <Linha
                    rotulo="Rentab."
                    valor={`${resumo.rent_am?.toFixed(1)}% a.m.`}
                  />
                </dl>
                {resumo.usou_dados_cliente && (
                  <p className="mt-3 rounded-lg bg-emerald-50 px-2 py-1 text-xs text-emerald-700">
                    ✓ usando histórico real da fazenda
                  </p>
                )}
              </div>

              {ultima?.cenarios && <Cenarios cenarios={ultima.cenarios} />}
            </>
          )}

          {ultima?.dados_faltando && ultima.dados_faltando.length > 0 && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
              Faltando para refinar: {ultima.dados_faltando.join(", ")}
            </div>
          )}
        </aside>
      </main>
      )}
    </div>
  );
}

function Linha({
  rotulo,
  valor,
  destaque,
}: {
  rotulo: string;
  valor: string;
  destaque?: "bom" | "ruim";
}) {
  return (
    <div>
      <dt className="text-xs text-neutral-400">{rotulo}</dt>
      <dd
        className={`font-semibold ${
          destaque === "bom"
            ? "text-emerald-600"
            : destaque === "ruim"
              ? "text-red-600"
              : "text-neutral-900"
        }`}
      >
        {valor}
      </dd>
    </div>
  );
}

function Cenarios({ cenarios }: { cenarios: Cenario[] }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <h2 className="mb-2 text-sm font-semibold text-neutral-900">6 cenários</h2>
      <div className="grid grid-cols-2 gap-2">
        {cenarios.map((c) => {
          const positivo = c.lucro_liquido >= 0;
          return (
            <div
              key={c.tipo}
              className="rounded-xl border border-neutral-100 bg-neutral-50 p-2.5"
            >
              <p className="text-xs font-medium capitalize text-neutral-500">
                {c.tipo}
              </p>
              <p
                className={`text-sm font-bold ${positivo ? "text-emerald-600" : "text-red-600"}`}
              >
                {(c.lucro_liquido / 1000).toLocaleString("pt-BR", {
                  maximumFractionDigits: 0,
                })}
                k
              </p>
              <p className="text-[11px] text-neutral-400">
                GMD {c.gmd} · score {c.score_viabilidade.toFixed(0)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
