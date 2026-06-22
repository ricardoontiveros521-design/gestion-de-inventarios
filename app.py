import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import database as db

st.set_page_config(page_title="Gestor de Inventarios", layout="wide", page_icon="📦")
db.init_db()

# ── Session state defaults ─────────────────────────────────────────────
DEFAULTS = {
    "tool_name": "",
    "tool_type": "rack",
    "tool_mode": "paint",   # paint | erase
    "grid_rows": 10,
    "grid_cols": 15,
    "grid":      None,      # loaded lazily
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

def load_grid():
    st.session_state.grid = db.get_grid()

if st.session_state.grid is None:
    load_grid()

# ── CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Grid cell buttons ─────────────────────────────────── */
div[data-testid="stButton"] > button {
    height: 52px !important;
    width: 100% !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    padding: 2px 1px !important;
    white-space: normal !important;
    word-break: break-all !important;
    line-height: 1.15 !important;
    border-radius: 3px !important;
    transition: filter .1s, transform .05s;
}
div[data-testid="stButton"] > button:hover { filter: brightness(.88); transform: scale(.97); }

/* ── Status (highest priority) ─────────────────────────── */
[data-testid="stVerticalBlock"]:has(.sc-diff) [data-testid="stButton"] > button
    { background:#dc3545 !important; color:#fff !important; border:2px solid #b02a37 !important; }
[data-testid="stVerticalBlock"]:has(.sc-today) [data-testid="stButton"] > button
    { background:#6f42c1 !important; color:#fff !important; border:2px solid #59359a !important; }
[data-testid="stVerticalBlock"]:has(.sc-delivered) [data-testid="stButton"] > button
    { background:#198754 !important; color:#fff !important; border:2px solid #146c43 !important; }
[data-testid="stVerticalBlock"]:has(.sc-started) [data-testid="stButton"] > button
    { background:#ffc107 !important; color:#212529 !important; border:2px solid #e5ac00 !important; }

/* ── Block types (only when no status class present) ─────── */
[data-testid="stVerticalBlock"]:has(.ct-rack) [data-testid="stButton"] > button
    { background:#cfe2ff !important; color:#003a70 !important; border:1px solid #9ec5fe !important; }
[data-testid="stVerticalBlock"]:has(.ct-zone) [data-testid="stButton"] > button
    { background:#d1e7dd !important; color:#0a3622 !important; border:1px solid #a3cfbb !important; }
[data-testid="stVerticalBlock"]:has(.ct-office) [data-testid="stButton"] > button
    { background:#fff3cd !important; color:#664d03 !important; border:1px solid #ffe69c !important; }
[data-testid="stVerticalBlock"]:has(.ct-dock) [data-testid="stButton"] > button
    { background:#f8d7da !important; color:#58151c !important; border:1px solid #f1aeb5 !important; }
[data-testid="stVerticalBlock"]:has(.ct-aisle) [data-testid="stButton"] > button
    { background:repeating-linear-gradient(45deg,#e9ecef,#e9ecef 4px,#f8f9fa 4px,#f8f9fa 8px) !important;
      color:#868e96 !important; border:1px solid #ced4da !important; }
[data-testid="stVerticalBlock"]:has(.ct-empty) [data-testid="stButton"] > button
    { background:transparent !important; color:#dee2e6 !important;
      border:1px dashed #dee2e6 !important; font-size:16px !important; }

/* Row header cells */
[data-testid="stVerticalBlock"]:has(.row-hdr) [data-testid="stMarkdownContainer"] p {
    line-height:52px !important; font-weight:700; color:#6c757d;
    text-align:center; font-size:11px; margin:0;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════════
st.title("📦 Gestor de Inventarios")

tab_layout, tab_diff, tab_rhythm = st.tabs(
    ["🗺️ Layout", "📋 Diferencias", "🔄 Ritmo de Inventarios"]
)

# ─────────────────────────────────────────────────────────────────────
# TAB 1 · LEGO LAYOUT BUILDER
# ─────────────────────────────────────────────────────────────────────
with tab_layout:

    ROWS = st.session_state.grid_rows
    COLS = st.session_state.grid_cols
    grid = st.session_state.grid

    # ── Status data ──────────────────────────────────────────────────
    diff_locs, delivery_locs, start_locs, today_count = db.get_location_status()
    locations    = db.get_locations()
    loc_by_name  = {row["name"]: row for _, row in locations.iterrows()}

    def cell_css(cell):
        """Return the CSS class that determines the cell's color."""
        if cell is None:
            return "ct-empty"
        ctype = cell["type"]
        name  = cell["name"]
        loc   = loc_by_name.get(name)
        if loc is not None:
            lid = int(loc["id"])
            if lid in diff_locs:     return "sc-diff"
            if lid in today_count:   return "sc-today"
            if lid in delivery_locs: return "sc-delivered"
            if lid in start_locs:    return "sc-started"
        return f"ct-{ctype}"

    # ── TOOL BAR ─────────────────────────────────────────────────────
    st.markdown("### 🧱 Herramienta")

    TYPE_LABELS = {
        "rack":   "🟦 Rack / Estantería",
        "aisle":  "⬜ Pasillo",
        "zone":   "🟩 Zona / Área",
        "office": "🟨 Oficina / Admin",
        "dock":   "🟥 Andén / Muelle",
    }

    tb1, tb2, tb3, tb4, tb5 = st.columns([3, 2, 1, 1, 1])

    tool_name = tb1.text_input(
        "Nombre del bloque",
        value=st.session_state.tool_name,
        placeholder="ej: RACK-A1, PASILLO-1, RECEPCIÓN…",
        key="inp_tool_name",
        label_visibility="collapsed",
    )
    st.session_state.tool_name = tool_name

    tool_type = tb2.selectbox(
        "Tipo",
        list(TYPE_LABELS.keys()),
        format_func=lambda k: TYPE_LABELS[k],
        index=list(TYPE_LABELS.keys()).index(st.session_state.tool_type),
        key="sel_tool_type",
        label_visibility="collapsed",
    )
    st.session_state.tool_type = tool_type

    if tb3.button("🖊️ Pintar", use_container_width=True,
                  type="primary" if st.session_state.tool_mode == "paint" else "secondary"):
        st.session_state.tool_mode = "paint"
        st.rerun()

    if tb4.button("🗑️ Borrar", use_container_width=True,
                  type="primary" if st.session_state.tool_mode == "erase" else "secondary"):
        st.session_state.tool_mode = "erase"
        st.rerun()

    # Preview badge
    mode = st.session_state.tool_mode
    if mode == "erase":
        tb5.markdown("**Modo:** 🗑️ Borrar")
    elif tool_name.strip():
        _, fg = db.CELL_TYPES.get(tool_type, ("#eee", "#333"))[1:]
        bg, fg = db.CELL_TYPES[tool_type][1], db.CELL_TYPES[tool_type][2]
        tb5.markdown(
            f'<span style="background:{bg};color:{fg};padding:4px 8px;'
            f'border-radius:4px;font-weight:700;font-size:12px">'
            f'{tool_name.strip()}</span>',
            unsafe_allow_html=True,
        )
    else:
        tb5.markdown('<span style="color:#aaa;font-size:12px">↑ escribe un nombre</span>',
                     unsafe_allow_html=True)

    # ── Grid config ──────────────────────────────────────────────────
    with st.expander("⚙️ Tamaño de la cuadrícula"):
        gc1, gc2, gc3 = st.columns([1, 1, 2])
        new_rows = gc1.number_input("Filas",    1, 25, ROWS, key="cfg_rows")
        new_cols = gc2.number_input("Columnas", 1, 30, COLS, key="cfg_cols")
        if gc3.button("Aplicar tamaño", use_container_width=True):
            st.session_state.grid_rows = int(new_rows)
            st.session_state.grid_cols = int(new_cols)
            st.rerun()
        gc3.markdown(" ")
        if gc3.button("🧹 Borrar todo el mapa", type="secondary", use_container_width=True):
            db.clear_grid()
            load_grid()
            st.rerun()

    st.divider()

    # ── LEGEND ───────────────────────────────────────────────────────
    lcols = st.columns(9)
    legends = [
        ("🟦", "Rack"),
        ("⬜", "Pasillo"),
        ("🟩", "Zona"),
        ("🟨", "Oficina"),
        ("🟥", "Andén"),
        ("🔴", "Diferencias"),
        ("🟢", "Entregado"),
        ("🟡", "Iniciado"),
        ("🟣", "Conteo hoy"),
    ]
    for lc, (ico, txt) in zip(lcols, legends):
        lc.markdown(f"{ico} {txt}")

    st.markdown("**👆 Haz clic en una celda para pintar o borrar**")

    # ── GRID CANVAS ──────────────────────────────────────────────────

    # Column headers
    hdr = st.columns([0.4] + [1] * COLS)
    hdr[0].markdown(" ")
    for c in range(COLS):
        hdr[c + 1].markdown(
            f"<p style='text-align:center;font-size:10px;font-weight:700;"
            f"color:#6c757d;margin:0'>{c + 1}</p>",
            unsafe_allow_html=True,
        )

    # Grid rows
    for r in range(ROWS):
        row_cols = st.columns([0.4] + [1] * COLS)

        # Row number
        row_cols[0].markdown(
            f'<span class="row-hdr"></span>{r + 1}',
            unsafe_allow_html=True,
        )

        for c in range(COLS):
            with row_cols[c + 1]:
                cell  = grid.get((r, c))
                css   = cell_css(cell)

                # Hidden CSS marker
                st.markdown(
                    f'<span class="{css}" style="display:none"></span>',
                    unsafe_allow_html=True,
                )

                label = cell["name"] if cell else "+"

                if st.button(label, key=f"g_{r}_{c}", use_container_width=True):
                    if mode == "erase":
                        db.erase_cell(r, c)
                        load_grid()
                        st.rerun()
                    else:
                        name = st.session_state.tool_name.strip()
                        if not name:
                            st.toast("⚠️ Escribe un nombre antes de pintar", icon="⚠️")
                        else:
                            db.paint_cell(r, c, name, st.session_state.tool_type)
                            load_grid()
                            st.rerun()

    # ── LOCATION SUMMARY ─────────────────────────────────────────────
    st.divider()
    grid_names = db.get_grid_locations()
    if grid_names:
        st.markdown(f"#### 📋 Ubicaciones en el mapa ({len(grid_names)})")
        chunk_size = 6
        for i in range(0, len(grid_names), chunk_size):
            chunk = grid_names[i: i + chunk_size]
            cols  = st.columns(chunk_size)
            for col, name in zip(cols, chunk):
                loc  = loc_by_name.get(name)
                lid  = int(loc["id"]) if loc is not None else None
                if lid in diff_locs:       bg, fg = "#dc3545", "#fff"
                elif lid in today_count:   bg, fg = "#6f42c1", "#fff"
                elif lid in delivery_locs: bg, fg = "#198754", "#fff"
                elif lid in start_locs:    bg, fg = "#ffc107", "#212529"
                else:                      bg, fg = "#cfe2ff", "#003a70"
                col.markdown(
                    f'<div style="background:{bg};color:{fg};padding:6px 8px;'
                    f'border-radius:6px;font-weight:700;font-size:12px;'
                    f'text-align:center;margin-bottom:4px">{name}</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("El mapa está vacío — pinta tu almacén usando la herramienta de arriba.")


# ─────────────────────────────────────────────────────────────────────
# TAB 2 · DIFERENCIAS
# ─────────────────────────────────────────────────────────────────────
with tab_diff:
    st.subheader("Registro de Diferencias")
    locations = db.get_locations()

    if locations.empty:
        st.warning("Primero pinta ubicaciones en la pestaña **Layout**.")
    else:
        with st.expander("➕ Registrar diferencia"):
            with st.form("form_add_diff", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                art_in   = c1.text_input("Artículo *")
                loc_in   = c2.selectbox("Ubicación *", locations["name"].tolist())
                diff_in  = c3.number_input("Diferencia", value=0.0, step=1.0,
                                           help="Negativo=faltante · Positivo=sobrante")
                price_in = c4.number_input("Precio ($)", min_value=0.0, value=0.0, step=0.01)
                st.caption(f"Fecha automática: **{date.today().strftime('%d/%m/%Y')}**")
                if st.form_submit_button("Registrar", use_container_width=True):
                    if art_in.strip():
                        lid = int(locations[locations["name"] == loc_in]["id"].values[0])
                        db.add_difference(art_in, lid, diff_in, price_in)
                        st.success("Diferencia registrada.")
                        st.rerun()
                    else:
                        st.warning("El artículo es obligatorio.")

        df = db.get_differences()
        if df.empty:
            st.info("Sin diferencias registradas.")
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Registros",        len(df))
            m2.metric("Faltantes",        int((df["difference"] < 0).sum()))
            m3.metric("Sobrantes",        int((df["difference"] > 0).sum()))
            m4.metric("Impacto neto ($)", f"${df['impact'].sum():,.2f}")
            st.divider()

            f1, f2 = st.columns([3, 1])
            locs_filter = f1.multiselect("Filtrar ubicación", df["location"].unique().tolist())
            tipo_filter = f2.radio("Tipo", ["Todos", "Faltantes", "Sobrantes"], horizontal=True)

            filt = df.copy()
            if locs_filter:      filt = filt[filt["location"].isin(locs_filter)]
            if tipo_filter == "Faltantes": filt = filt[filt["difference"] < 0]
            elif tipo_filter == "Sobrantes": filt = filt[filt["difference"] > 0]

            disp = filt[["id","article","location","zone","difference","price","impact","created_date"]].copy()
            disp.columns = ["ID","Artículo","Ubicación","Zona","Diferencia","Precio ($)","Impacto ($)","Fecha"]
            disp["Fecha"] = pd.to_datetime(disp["Fecha"]).dt.strftime("%d/%m/%Y")

            def _cn(v):
                if not isinstance(v, (int, float)): return ""
                return "color:#dc3545;font-weight:700" if v < 0 else ("color:#198754;font-weight:700" if v > 0 else "")

            st.dataframe(disp.style.map(_cn, subset=["Diferencia","Impacto ($)"]),
                         use_container_width=True, hide_index=True)

            with st.expander("🗑️ Eliminar registro"):
                if not filt.empty:
                    del_id = st.selectbox("ID a eliminar", filt["id"].tolist())
                    if st.button("Eliminar", type="secondary"):
                        db.delete_difference(int(del_id))
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────
# TAB 3 · RITMO
# ─────────────────────────────────────────────────────────────────────
with tab_rhythm:
    st.subheader("Ritmo de Inventarios")
    locations = db.get_locations()

    if locations.empty:
        st.warning("Primero pinta ubicaciones en la pestaña **Layout**.")
    else:
        rhythm = db.get_rhythm()
        today  = date.today()

        def _pd(val):
            if val and pd.notna(val) and str(val).strip():
                try: return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
                except ValueError: pass
            return None

        with st.expander("✏️ Editar ritmo de una ubicación"):
            if not rhythm.empty:
                sel = st.selectbox("Ubicación", rhythm["location"].tolist(), key="rsel")
                row = rhythm[rhythm["location"] == sel].iloc[0]
                with st.form("form_rhythm"):
                    c1, c2, c3 = st.columns(3)
                    fv      = int(row["frequency_days"]) if pd.notna(row["frequency_days"]) else 30
                    freq_in = c1.number_input("Frecuencia (días)", 1, 365, fv)
                    has_s   = c2.checkbox("¿Tiene fecha de inicio?",   value=bool(_pd(row["start_date"])))
                    has_d   = c3.checkbox("¿Tiene fecha de entrega?",  value=bool(_pd(row["delivery_date"])))
                    si = di = None
                    if has_s: si = c2.date_input("Inicio",  value=_pd(row["start_date"])    or today, key="si")
                    if has_d: di = c3.date_input("Entrega", value=_pd(row["delivery_date"]) or today, key="di")
                    if st.form_submit_button("Guardar", use_container_width=True):
                        db.update_rhythm(int(row["location_id"]), freq_in,
                                         si if has_s else None, di if has_d else None)
                        st.success("Actualizado.")
                        st.rerun()

        st.divider()
        rhythm = db.get_rhythm()
        rows_out = []
        for _, r in rhythm.iterrows():
            last  = _pd(r["delivery_date"])
            freq  = int(r["frequency_days"]) if pd.notna(r["frequency_days"]) else None
            nxt   = (last + timedelta(days=freq)) if last and freq else None
            days  = (today - last).days if last else None
            ov    = bool(nxt and nxt < today)
            dt    = bool(nxt and nxt == today)
            rows_out.append({
                "Ubicación":          r["location"],
                "Zona":               r["zone"] or "",
                "Frecuencia (días)":  freq or "",
                "Inicio":             r["start_date"] or "",
                "Entrega":            r["delivery_date"] or "",
                "Días transcurridos": days if days is not None else "",
                "Siguiente conteo":   nxt.strftime("%d/%m/%Y") if nxt else "",
                "_st":                "overdue" if ov else ("today" if dt else ""),
            })

        rdf = pd.DataFrame(rows_out)
        m1, m2, m3 = st.columns(3)
        m1.metric("Ubicaciones",   len(rdf))
        m2.metric("Conteo hoy 🟣", int((rdf["_st"] == "today").sum()))
        m3.metric("Vencidos 🔴",   int((rdf["_st"] == "overdue").sum()))

        show = ["Ubicación","Zona","Frecuencia (días)","Inicio","Entrega",
                "Días transcurridos","Siguiente conteo"]

        def _sr(row):
            n = len(row)
            if row["_st"] == "overdue": return ["background:#ffe5e5;color:#7f0000"] * n
            if row["_st"] == "today":   return ["background:#ede7f6;color:#311b92"] * n
            return [""] * n

        st.dataframe(
            rdf[show + ["_st"]].style.apply(_sr, axis=1).hide(subset=["_st"], axis=1),
            use_container_width=True, hide_index=True,
        )
        st.caption("🟣 Conteo programado para hoy  |  🔴 Vencido")
