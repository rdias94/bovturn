"""
BovTurn — Gerador de Cenários de Confinamento (Excel)
=====================================================
Gera, a partir das fórmulas (matemática padrão de confinamento), TODOS os
cenários possíveis e exporta para .xlsx. Arquivo nosso, calculado do zero.

Lógica central (validada contra a referência):
  custo_da_@_produzida = custo_diária × 15 ÷ ganho_de_carcaça_kg_dia
  (15 kg de carcaça = 1 arroba)

Viabilidade (break-even por cabeça):
  @ produzidas    = dias × ganho_carcaça ÷ 15
  @ final         = @ entrada + @ produzidas
  custo_total     = custo_animal + dias × diária + custos_fixos
  receita         = @ final × preço_venda
  margem/cab      = receita − custo_total
"""

import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.utils import get_column_letter

SAIDA = os.path.expanduser("~/Downloads/BovTurn_Confinamento_Cenarios.xlsx")

# ── Parâmetros ajustáveis (viabilidade) ───────────────────────
DIAS = 100              # dias de cocho
ARROBA_ENTRADA = 12.0   # @ de carcaça na entrada (boi magro)
CUSTOS_FIXOS_CAB = 0.0  # sanidade/fixos por cabeça (R$)

ARROBA_KG = 15.0        # kg de carcaça por arroba

# ── Faixas ────────────────────────────────────────────────────
def faixa(ini, fim, passo):
    vals, v = [], ini
    while v <= fim + 1e-9:
        vals.append(round(v, 4))
        v += passo
    return vals

GANHOS_MATRIZ = faixa(0.700, 1.500, 0.025)   # ganho carcaça kg/dia
DIARIAS_MATRIZ = faixa(12.00, 18.00, 0.25)   # custo diária R$/dia

DIARIAS = faixa(14.0, 17.0, 0.25)            # viabilidade
GANHOS = faixa(0.90, 1.30, 0.05)
PRECOS = faixa(320.0, 345.0, 2.5)
CUSTOS_ANIMAL = faixa(4000.0, 4800.0, 100.0)

# ── Estilos ───────────────────────────────────────────────────
AZUL = "1F4E5F"
VERDE = "2E7D32"
hdr = Font(bold=True, color="FFFFFF")
hdr_fill = PatternFill("solid", fgColor=AZUL)
titulo = Font(bold=True, size=14, color=AZUL)
centro = Alignment(horizontal="center", vertical="center")
borda = Border(*(Side(style="thin", color="D9D9D9"),) * 4)


def estilo_header(cell):
    cell.font = hdr
    cell.fill = hdr_fill
    cell.alignment = centro
    cell.border = borda


wb = Workbook()

# ══════════════════════════════════════════════════════════════
# 1) MATRIZ — Custo da @ produzida
# ══════════════════════════════════════════════════════════════
ws = wb.active
ws.title = "Custo @ Produzida"
ws["B2"] = "Custo da @ produzida em confinamento (R$/@)"
ws["B2"].font = titulo
ws["B3"] = "Linhas: ganho de carcaça (kg/dia) · Colunas: custo da diária (R$/dia)"
ws["B3"].font = Font(italic=True, size=10, color="666666")
ws["B4"] = "Fórmula: custo_@ = diária × 15 ÷ ganho_de_carcaça"
ws["B4"].font = Font(italic=True, size=10, color="666666")

r0, c0 = 6, 2  # canto da matriz
canto = ws.cell(row=r0, column=c0, value="ganho \\ diária")
estilo_header(canto)
for j, d in enumerate(DIARIAS_MATRIZ):
    cell = ws.cell(row=r0, column=c0 + 1 + j, value=d)
    estilo_header(cell)
    cell.number_format = "0.00"
for i, g in enumerate(GANHOS_MATRIZ):
    rh = ws.cell(row=r0 + 1 + i, column=c0, value=g)
    estilo_header(rh)
    rh.number_format = "0.000"
    for j, d in enumerate(DIARIAS_MATRIZ):
        v = d * ARROBA_KG / g
        cell = ws.cell(row=r0 + 1 + i, column=c0 + 1 + j, value=round(v, 0))
        cell.number_format = "0"
        cell.alignment = centro
        cell.border = borda

# Heatmap: verde (custo baixo) → amarelo → vermelho (custo alto)
ini = get_column_letter(c0 + 1) + str(r0 + 1)
fim = get_column_letter(c0 + len(DIARIAS_MATRIZ)) + str(r0 + len(GANHOS_MATRIZ))
ws.conditional_formatting.add(
    f"{ini}:{fim}",
    ColorScaleRule(
        start_type="min", start_color="63BE7B",
        mid_type="percentile", mid_value=50, mid_color="FFEB84",
        end_type="max", end_color="F8696B",
    ),
)
ws.freeze_panes = ws.cell(row=r0 + 1, column=c0 + 1)
ws.column_dimensions["B"].width = 14

# ══════════════════════════════════════════════════════════════
# 2) VIABILIDADE — todos os cenários (fatorial completo)
# ══════════════════════════════════════════════════════════════
wv = wb.create_sheet("Viabilidade (todos)")
cols = [
    "Diária (R$/dia)", "Ganho carcaça (kg/dia)", "Preço venda (R$/@)",
    "Custo animal (R$/cab)", "Dias cocho", "@ entrada", "@ produzidas",
    "@ final", "Custo alimentação", "Custo total", "Receita",
    "Margem/cab (R$)", "Custo @ produzida (R$)", "Viável?",
]
for j, c in enumerate(cols, start=1):
    estilo_header(wv.cell(row=1, column=j, value=c))
wv.freeze_panes = "A2"

linha = 2
n_viaveis = 0
margens = []
for diaria in DIARIAS:
    for ganho in GANHOS:
        arrobas_prod = DIAS * ganho / ARROBA_KG
        arroba_final = ARROBA_ENTRADA + arrobas_prod
        custo_alim = DIAS * diaria
        custo_arroba = diaria * ARROBA_KG / ganho
        for preco in PRECOS:
            receita = arroba_final * preco
            for custo_animal in CUSTOS_ANIMAL:
                custo_total = custo_animal + custo_alim + CUSTOS_FIXOS_CAB
                margem = receita - custo_total
                viavel = margem > 0
                if viavel:
                    n_viaveis += 1
                margens.append(margem)
                vals = [
                    diaria, ganho, preco, custo_animal, DIAS,
                    ARROBA_ENTRADA, round(arrobas_prod, 2), round(arroba_final, 2),
                    round(custo_alim, 2), round(custo_total, 2), round(receita, 2),
                    round(margem, 2), round(custo_arroba, 2),
                    "SIM" if viavel else "NÃO",
                ]
                for j, v in enumerate(vals, start=1):
                    cell = wv.cell(row=linha, column=j, value=v)
                    if j in (1, 2, 3):
                        cell.number_format = "0.00"
                    elif j in (9, 10, 11, 12, 13):
                        cell.number_format = "#,##0"
                    if j == 14:
                        cell.alignment = centro
                        cell.fill = PatternFill(
                            "solid", fgColor="C6EFCE" if viavel else "FFC7CE")
                        cell.font = Font(color="006100" if viavel else "9C0006", bold=True)
                linha += 1

total = linha - 2
for col, w in {"A": 14, "B": 18, "C": 16, "D": 18, "E": 11, "F": 11,
               "G": 13, "H": 11, "I": 16, "J": 13, "K": 13, "L": 15,
               "M": 18, "N": 10}.items():
    wv.column_dimensions[col].width = w

# ══════════════════════════════════════════════════════════════
# 3) PARÂMETROS
# ══════════════════════════════════════════════════════════════
wp = wb.create_sheet("Parâmetros")
wp["B2"] = "Parâmetros do modelo (ajustáveis)"
wp["B2"].font = titulo
params = [
    ("Dias de cocho", DIAS, "dias"),
    ("@ de carcaça na entrada", ARROBA_ENTRADA, "@"),
    ("Custos fixos por cabeça", CUSTOS_FIXOS_CAB, "R$"),
    ("kg de carcaça por arroba", ARROBA_KG, "kg/@"),
    ("", "", ""),
    ("Fórmula custo @ produzida", "diária × 15 ÷ ganho_carcaça", ""),
    ("Fórmula margem/cab", "@final × preço − custo_animal − dias×diária", ""),
]
for i, (nome, val, un) in enumerate(params, start=4):
    wp.cell(row=i, column=2, value=nome).font = Font(bold=bool(nome))
    wp.cell(row=i, column=3, value=val)
    wp.cell(row=i, column=4, value=un).font = Font(color="666666")
wp.column_dimensions["B"].width = 30
wp.column_dimensions["C"].width = 42

# ══════════════════════════════════════════════════════════════
# 4) RESUMO
# ══════════════════════════════════════════════════════════════
wr = wb.create_sheet("Resumo", 0)
wr["B2"] = "BovTurn — Cenários de Confinamento"
wr["B2"].font = Font(bold=True, size=16, color=VERDE)
wr["B3"] = "Gerado estatisticamente a partir das fórmulas (cálculo próprio)."
wr["B3"].font = Font(italic=True, size=10, color="666666")
resumo = [
    ("Total de cenários de viabilidade", f"{total:,}".replace(",", ".")),
    ("Cenários viáveis", f"{n_viaveis:,}".replace(",", ".")),
    ("% viáveis", f"{(n_viaveis/total*100):.1f}%" if total else "—"),
    ("Melhor margem/cab", f"R$ {max(margens):,.0f}".replace(",", ".") if margens else "—"),
    ("Pior margem/cab", f"R$ {min(margens):,.0f}".replace(",", ".") if margens else "—"),
    ("Margem média/cab", f"R$ {sum(margens)/len(margens):,.0f}".replace(",", ".") if margens else "—"),
    ("", ""),
    ("Matriz custo @", f"{len(GANHOS_MATRIZ)} ganhos × {len(DIARIAS_MATRIZ)} diárias = {len(GANHOS_MATRIZ)*len(DIARIAS_MATRIZ)} combinações"),
]
for i, (nome, val) in enumerate(resumo, start=5):
    wr.cell(row=i, column=2, value=nome).font = Font(bold=bool(nome))
    wr.cell(row=i, column=3, value=val)
wr.column_dimensions["B"].width = 34
wr.column_dimensions["C"].width = 40

wb.save(SAIDA)
print(f"OK -> {SAIDA}")
print(f"Matriz: {len(GANHOS_MATRIZ)}x{len(DIARIAS_MATRIZ)} | Viabilidade: {total:,} cenários | {n_viaveis:,} viáveis")
