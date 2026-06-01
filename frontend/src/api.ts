// Cliente da API BovTurn (FastAPI no Railway)
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface PrecoEntrada {
  preco_kg: number;
  preco_arroba: number;
  valor_mercado_cab: number;
  frete_cab: number;
  comissao_cab: number;
  custo_total_cab: number;
}

export interface Cenario {
  tipo: string;
  nome: string;
  gmd: number;
  preco_venda_arroba: number;
  n_animais: number;
  peso_saida_kg: number;
  peso_saida_arroba: number;
  custo_arroba_produzida: number;
  margem_cab: number;
  lucro_liquido: number;
  rentabilidade_am: number;
  score_viabilidade: number;
  classificacao_viabilidade: string;
}

export interface Resumo {
  semaforo?: string;
  score?: number;
  classificacao?: string;
  n_animais?: number;
  peso_saida?: number;
  gmd_usado?: number;
  fonte_gmd?: string;
  preco_entrada?: PrecoEntrada;
  custo_arroba?: number;
  margem_cab?: number;
  lucro_base?: number;
  lucro_pessimista?: number;
  rent_am?: number;
  pior_positivo?: boolean;
  preco_equilibrio?: number;
  usou_dados_cliente?: boolean;
  erro?: string;
}

export interface RespostaAgente {
  resposta: string;
  cenarios: Cenario[] | null;
  resumo: Resumo | null;
  contexto_sessao: Record<string, unknown>;
  confianca: string;
  dados_faltando: string[];
  usou_cliente: boolean;
}

export async function perguntarAgente(
  mensagem: string,
  telefone: string,
  sessao: Record<string, unknown>,
): Promise<RespostaAgente> {
  const r = await fetch(`${API_URL}/api/agente/testar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensagem, telefone, sessao }),
  });
  if (!r.ok) throw new Error(`Erro ${r.status} ao falar com o agente`);
  return r.json();
}

export async function health(): Promise<{ status: string; banco: string }> {
  const r = await fetch(`${API_URL}/health`);
  return r.json();
}

export interface Cliente {
  telefone: string;
  nome: string;
  fazenda: string;
  estado: string | null;
  sistema: string;
  forrageiras: string[];
  giros_historico: number;
}

export interface NovoCliente {
  nome: string;
  telefone: string;
  fazenda: string;
  estado?: string;
  tem_sequeiro: boolean;
  tem_irrigado: boolean;
  forrageiras: string[];
  area_util_ha?: number;
}

export async function listarClientes(): Promise<Cliente[]> {
  const r = await fetch(`${API_URL}/api/clientes/`);
  if (!r.ok) throw new Error(`Erro ${r.status} ao listar clientes`);
  return r.json();
}

export async function cadastrarCliente(
  dados: NovoCliente,
): Promise<{ sucesso: boolean; mensagem: string }> {
  const r = await fetch(`${API_URL}/api/clientes/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || `Erro ${r.status}`);
  return data;
}

export interface EntradaConfinamento {
  peso_entrada_kg: number;
  gmd_inicial: number;
  decaimento_gmd: number;
  rendimento_carcaca: number;
  rendimento_ganho: number;
  preco_compra_arroba: number;
  preco_venda_arroba: number;
  preco_saca_milho: number;
  pct_milho_dieta: number;
  custo_ms_outros: number;
  consumo_pct_pv: number;
  diaria_operacional: number;
  dias_max: number;
}

export interface ResumoConfinamento {
  dias_otimos: number;
  breakeven_dias: number | null;
  lucro_maximo: number;
  margem_cab: number;
  peso_saida_kg: number;
  gmd_medio: number;
  ganho_carcaca_medio: number;
  rendimento_carcaca_entrada: number;
  rendimento_carcaca_saida: number;
  arroba_entrada: number;
  arroba_saida: number;
  arrobas_produzidas: number;
  custo_animal: number;
  custo_operacional: number;
  custo_arroba_produzida: number;
  receita: number;
  agio_cab: number;
  viavel: boolean;
  semaforo: string;
}

export interface PontoCurva {
  dia: number;
  gmd: number;
  peso_vivo: number;
  rc_atual: number;
  arroba_carcaca: number;
  receita: number;
  custo_acumulado: number;
  lucro: number;
  diaria: number;
}

export interface ResultadoConfinamento {
  sucesso: boolean;
  resumo: ResumoConfinamento | null;
  curva: PontoCurva[];
  dias_otimos: number;
  breakeven_dias: number | null;
}

export async function calcularConfinamento(
  e: EntradaConfinamento,
): Promise<ResultadoConfinamento> {
  const r = await fetch(`${API_URL}/api/confinamento/calcular`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(e),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || `Erro ${r.status}`);
  return data;
}

export interface MatrizConfinamento {
  diarias: number[];
  ganhos: number[];
  linhas: { ganho_carcaca: number; custos: number[] }[];
}

export async function matrizConfinamento(): Promise<MatrizConfinamento> {
  const r = await fetch(`${API_URL}/api/confinamento/matriz`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!r.ok) throw new Error(`Erro ${r.status} na matriz`);
  return r.json();
}

export interface AnaliseEntrada {
  peso_entrada_kg: number;
  preco_compra_arroba: number;
  preco_venda_arroba: number;
  dias_giro: number;
  sistema_hidrico: string;
  sistema_producao: string;
  sexo: string;
  area_ha: number;
  lotacao_ua_ha: number;
  custo_mdo_cab_mes: number;
  custo_gastos_prod_cab_mes: number;
  preco_saca_milho: number;
}

export interface CurvaPonto {
  fator: number;
  rotulo: string;
  margem_cab: number;
  tir_am_pct: number;
}

export interface AnaliseResultado {
  base: {
    gmd: number;
    peso_saida_kg: number;
    preco_venda_arroba: number;
    preco_compra_arroba: number;
    custo_arroba_produzida: number;
    score: number;
    classificacao: string;
    n_animais: number;
  };
  metricas: {
    tir_am_pct: number;
    tir_am_verdito: string;
    lucratividade_pct: number;
    lucratividade_verdito: string;
    desembolso_cab_mes: number;
    desembolso_cab_mes_verdito: string;
    desembolso_por_arroba: number;
    agio_bezerro_pct: number;
    agio_bezerro_verdito: string;
    relacao_troca_milho: number;
    relacao_troca_verdito: string;
    margem_cab: number;
    receita_cab: number;
    perfil_desembolso: Record<string, number>;
    perfil_desembolso_pct: Record<string, number>;
  };
  estatistica: {
    n_cenarios: number;
    pct_bom: number;
    pct_atencao: number;
    pct_ruim: number;
    margem_media: number;
    margem_min: number;
    margem_max: number;
    tir_media_pct: number;
  };
  sensibilidade: { gmd: CurvaPonto[]; compra: CurvaPonto[]; venda: CurvaPonto[] };
  histograma_margem: { faixa: number; n: number }[];
  preco_saca_milho: number;
}

export async function analisarGiro(
  e: AnaliseEntrada,
): Promise<AnaliseResultado> {
  const r = await fetch(`${API_URL}/api/analise/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(e),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || `Erro ${r.status}`);
  return data;
}

export interface CriaEntrada {
  matrizes: number;
  taxa_prenhez: number;
  mortalidade_bezerro: number;
  idade_primeiro_parto_meses: number;
  taxa_descarte_vacas: number;
  taxa_crescimento_rebanho: number;
  peso_desmame_kg: number;
  preco_kg_bezerro: number;
  custo_pasto_arrendamento: number;
  custo_sal_mineral: number;
  custo_sanidade: number;
  custo_mao_de_obra: number;
  custo_outros: number;
  anos: number;
}

export interface AnoCria {
  ano: number;
  matrizes: number;
  expostas: number;
  bezerros_desmamados: number;
  custo_total: number;
  receita_total: number;
  lucro_total: number;
  custo_por_bezerro: number;
  lucro_por_bezerro: number;
  lucro_por_vaca_exposta: number;
  kg_desmamado_por_vaca: number;
  desfrute_pct: number;
}

export interface CriaResultado {
  anos: AnoCria[];
  reprodutivo: {
    taxa_prenhez_pct: number;
    taxa_prenhez_verdito: string;
    taxa_natalidade_pct: number;
    taxa_desmame_pct: number;
    taxa_desmame_verdito: string;
    mortalidade_bezerro_pct: number;
    mortalidade_verdito: string;
    iep_meses: number;
    iep_verdito: string;
    idade_primeiro_parto_meses: number;
    ipp_verdito: string;
  };
  resumo: {
    custo_vaca_ano: number;
    custo_por_bezerro: number;
    preco_venda_bezerro: number;
    lucro_por_bezerro: number;
    lucro_por_vaca_exposta: number;
    kg_desmamado_por_vaca: number;
    desfrute_pct: number;
    viavel: boolean;
    semaforo: string;
    rebanho_inicial: number;
    rebanho_final: number;
  };
  componentes_custo: Record<string, number>;
}

export async function projetarCria(e: Partial<CriaEntrada>): Promise<CriaResultado> {
  const r = await fetch(`${API_URL}/api/cria/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(e),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || `Erro ${r.status}`);
  return data;
}

export interface EngordaEntrada {
  peso_entrada_kg: number;
  frame_score: number;
  peso_vaca_adulta: number;
  sexo: string;
  rendimento_carcaca: number;
  gmd_esperado: number;
  preco_compra_arroba: number;
  preco_venda_arroba: number;
  diaria_total: number;
}

export interface EngordaResultado {
  resultado: {
    frame_score: number;
    frame_origem: string;
    sexo: string;
    arroba_abate: number;
    peso_abate_kg: number;
    arroba_entrada: number;
    arrobas_produzidas: number;
    dias: number;
    custo_animal: number;
    custo_operacional: number;
    custo_total: number;
    receita: number;
    margem_cab: number;
    custo_arroba_produzida: number;
    agio_cab: number;
    tir_am_pct: number;
    viavel: boolean;
    semaforo: string;
  };
  tabela_frame: { frame: number; arroba_abate: number; peso_abate_kg: number }[];
}

export async function calcularEngorda(e: Partial<EngordaEntrada>): Promise<EngordaResultado> {
  const r = await fetch(`${API_URL}/api/engorda/calcular`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(e),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || `Erro ${r.status}`);
  return data;
}

export interface RecriaEntrada {
  peso_entrada_kg: number;
  peso_saida_kg: number;
  gmd: number;
  preco_kg_compra: number;
  preco_kg_venda: number;
  custo_kg_suplemento: number;
  custo_mdo_cab_mes: number;
  custo_gastos_prod_cab_mes: number;
  custo_sanidade_cab: number;
}

export interface RecriaResultado {
  resultado: {
    dias: number;
    meses: number;
    ganho_kg: number;
    arrobas_produzidas: number;
    arroba_entrada: number;
    arroba_saida: number;
    custo_animal: number;
    custo_operacional: number;
    custo_total: number;
    receita: number;
    margem_cab: number;
    custo_arroba_produzida: number;
    custo_kg_produzido: number;
    relacao_compra_venda: number;
    tir_am_pct: number;
    viavel: boolean;
    semaforo: string;
  };
}

export async function calcularRecria(e: Partial<RecriaEntrada>): Promise<RecriaResultado> {
  const r = await fetch(`${API_URL}/api/recria/calcular`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(e),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || `Erro ${r.status}`);
  return data;
}
