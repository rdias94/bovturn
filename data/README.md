# Dados da planilha (réplica local)

A planilha Google (`1xq62c9QZLgIsV_StMh3yHo3C8P2Tq33M5fQJVLvy-co`) está privada para download automático. A réplica local usa o mesmo modelo **V15 BZBM VPAgro** (arquivo em `source/v15_bzbm_vpagro.xlsm`).

## Estrutura

| Caminho | Conteúdo |
|---------|----------|
| `source/v15_bzbm_vpagro.xlsm` | Cópia mestre do Excel |
| `planilha_v15_bzbm/*.csv` | Uma CSV por aba (45 abas) |
| `planilha_v15_bzbm/manifest.json` | Índice de abas e dimensões |

## Atualizar a réplica

```bash
cd ~/bovturn
source venv/bin/activate
python scripts/sincronizar_planilha.py
```

Depois de baixar uma versão nova do Google (**Arquivo → Fazer download → Microsoft Excel**):

```bash
python scripts/sincronizar_planilha.py --origem ~/Downloads/sua_planilha.xlsx
```

Se a planilha estiver **pública** (qualquer pessoa com o link, leitor), uma aba específica:

```bash
python scripts/sincronizar_planilha.py --gid 2424350
```

O `gid` aparece na URL do Google Sheets (`#gid=2424350`).
