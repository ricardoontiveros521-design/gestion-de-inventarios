import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import database as db

st.set_page_config(
    page_title="Gestor de Inventarios",
    layout="wide",
    page_icon="📦",
)

db.init_db()

# ── Session state defaults ─────────────────────────────────────────────
for key, val in [("grid_rows", 6), ("grid_cols", 10), ("sel_cell", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Global CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Make all map buttons the same height */
div[data-testid="stButton"] > button {
    height: 58px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    padding: 2px 4px !important;
    line-height: 1.2 !important;
    white-space: normal !important;
    word-break: break-word !important;
    transition: filter 0.15s ease;
}
div[data-testid="stButton"] > button:hover { filter: brightness(0.9); }

/* Empty cell style */
.empty-cell + div[data-testid="stButton"] > button {
    background: transparent !important;
    color: #adb5bd !important;
    border: 1px dashed #ced4da !important;
    font-weight: 400 !important;
    font-size: 18px !important;
}
/* Status colors via :has() – works in all modern browsers */
[data-testid="stVerticalBlock"]:has(.c-default) [data-testid="stButton"] > button
    { background:#dee2e6 !important; color:#343a40 !important; border:1px solid #adb5bd !important; }
[data-testid="stVerticalBlock"]:has(.c-yellow) [data-testid="stButton"] > button
    { background:#ffc107 !important; color:#212529 !important; border:1px solid #e5ac00 !important; }
[data-testid="stVerticalBlock"]:has(.c-green) [data-testid="stButton"] > button
    { background:#198754 !important; color:#fff !important; border:1px solid #146c43 !important; }
[data-testid="stVerticalBlock"]:has(.c-red) [data-testid="stButton"] > button
    { background:#dc3545 !important; color:#fff !important; border:1px solid #b02a37 !important; }
[data-testid="stVerticalBlock"]:has(.c-purple) [data-testid="stButton"] > button
    { background:#6f42c1 !important; color:#fff !important; border:1px solid #59359a !important; }

/* Row number column */
div[data-testid="stColumn"]:first-child div[data-testid="stMarkdownContainer"] p {
    line-height: 58px !important;
    font-weight: 700;
    color: #6c757d;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

st.title("📦 Gestor de Inventarios")

tab_layout, tab_diff, tab_rhythm = st.tabs(
    ["🗺️ Layout", "📋 Diferencias", "🔄 Ritmo de Inventarios"]
)


# ═══════════════════════════════════════════════════════════════════════
# TAB 1 · LAYOUT  (mapa visual interactivo)
# ═══════════════════════════════════════════════════════════════════════
with tab_layout:

    # ── Grid size controls ────────────────────────────────────────────
    cfg1, cfg2, cfg3 = st.columns([1, 1, 4])
    ROWS = cfg1.number_input("Filas", 1, 25, st.session_state.grid_rows, key="nrows")
    COLS = cfg2.number_input("Columnas", 1, 30, st.session_state.grid_cols, key="ncols")
    st.session_state.grid_rows = int(ROWS)
    st.session_state.grid_cols = int(COLS)

    cfg3.markdown(
        "🟡 Inventario iniciado &nbsp;&nbsp;"
        "🟢 Entregado &nbsp;&nbsp;"
        "🔴 Diferencias registradas &nbsp;&nbsp;"
        "🟣 Conteo programado hoy"
    )

    # ── Data ──────────────────────────────────────────────────────────
    locations = db.get_locations()
    diff_locs, delivery_locs, start_locs, today_count = db.get_location_status()

    loc_by_pos: dict = {}
    if not locations.empty:
        for _, loc in locations.iterrows():
            r, c = int(loc["row_pos"]), int(loc["col_pos"])
            if 0 <= r < ROWS and 0 <= c < COLS:
                loc_by_pos[(r, c)] = loc

    def _css_class(loc_id: int) -> str:
        if loc_id in diff_locs:       return "c-red"
        if loc_id in today_count:     return "c-purple"
        if loc_id in delivery_locs:   return "c-green"
        if loc_id in start_locs:      return "c-yellow"
        return "c-default"

    # ── Column header row ─────────────────────────────────────────────
    header = st.columns([0.35] + [1] * COLS)
    header[0].markdown(" ")
    for c in range(COLS):
        header[c + 1].markdown(
            f"<p style='text-align:center;color:#6c757d;font-size:11px;"
            f"font-weight:700;margin:0'>{c + 1}</p>",
            unsafe_allow_html=True,
        )

    # ── Grid rows ─────────────────────────────────────────────────────
    for r in range(ROWS):
        row_cols = st.columns([0.35] + [1] * COLS)
        row_cols[0].markdown(str(r + 1))          # row number

        for c in range(COLS):
            with row_cols[c + 1]:
                pos = (r, c)

                if pos in loc_by_pos:
                    loc = loc_by_pos[pos]
                    css = _css_class(int(loc["id"]))
                    # Hidden marker for CSS :has() targeting
                    st.markdown(
                        f'<span class="{css}" style="display:none"></span>',
                        unsafe_allow_html=True,
                    )
                    label = loc["name"]
                else:
                    st.markdown(
                        '<span class="empty-cell" style="display:none"></span>',
                        unsafe_allow_html=True,
                    )
                    label = "+"

                if st.button(label, key=f"map_{r}_{c}", use_container_width=True):
                    st.session_state.sel_cell = (r, c)
                    st.rerun()

    # ── Selection / edit panel ────────────────────────────────────────
    if st.session_state.sel_cell is not None:
        sel_r, sel_c = st.session_state.sel_cell
        sel_pos = (sel_r, sel_c)

        st.divider()

        if sel_pos in loc_by_pos:
            loc = loc_by_pos[sel_pos]
            lid = int(loc["id"])
            st.markdown(
                f"### 📍 {loc['name']}  "
                f"<span style='font-size:14px;color:#6c757d'>Fila {sel_r+1} · Columna {sel_c+1}</span>",
                unsafe_allow_html=True,
            )

            p1, p2 = st.columns(2)
            with p1:
                with st.form("form_edit_loc"):
                    new_name = st.text_input("Nombre", value=loc["name"])
                    new_zone = st.text_input("Zona", value=loc["zone"] or "")
                    if st.form_submit_button("💾 Guardar cambios", use_container_width=True):
                        ok, msg = db.update_location(lid, new_name, new_zone)
                        if ok:
                            st.session_state.sel_cell = None
                            st.rerun()
                        else:
                            st.error(msg)
            with p2:
                st.markdown(" ")
                st.markdown(" ")
                if st.button("🗑️ Eliminar ubicación", type="secondary", use_container_width=True):
                    db.delete_location(lid)
                    st.session_state.sel_cell = None
                    st.rerun()
                if st.button("✖ Cerrar panel", use_container_width=True):
                    st.session_state.sel_cell = None
                    st.rerun()
        else:
            st.markdown(
                f"### ➕ Nueva ubicación  "
                f"<span style='font-size:14px;color:#6c757d'>Fila {sel_r+1} · Columna {sel_c+1}</span>",
                unsafe_allow_html=True,
            )
            with st.form("form_add_loc", clear_on_submit=True):
                c1, c2 = st.columns(2)
                name_in = c1.text_input("Nombre *", placeholder="RACK-A1")
                zone_in = c2.text_input("Zona", placeholder="Almacén Norte")
                sub, cancel = st.columns(2)
                if sub.form_submit_button("Agregar", use_container_width=True):
                    if name_in.strip():
                        ok, msg = db.add_location(name_in, zone_in, sel_r, sel_c)
                        if ok:
                            st.session_state.sel_cell = None
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("El nombre es obligatorio.")
            if st.button("✖ Cancelar", use_container_width=True):
                st.session_state.sel_cell = None
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# TAB 2 · DIFERENCIAS
# ═══════════════════════════════════════════════════════════════════════
with tab_diff:
    st.subheader("Registro de Diferencias")

    locations = db.get_locations()
    if locations.empty:
        st.warning("Primero define ubicaciones en la pestaña **Layout**.")
    else:
        with st.expander("➕ Registrar diferencia"):
            with st.form("form_add_diff", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                art_in   = c1.text_input("Artículo *")
                loc_in   = c2.selectbox("Ubicación *", locations["name"].tolist())
                diff_in  = c3.number_input(
                    "Diferencia", value=0.0, step=1.0,
                    help="Negativo = faltante · Positivo = sobrante",
                )
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
            if locs_filter:
                filt = filt[filt["location"].isin(locs_filter)]
            if tipo_filter == "Faltantes":
                filt = filt[filt["difference"] < 0]
            elif tipo_filter == "Sobrantes":
                filt = filt[filt["difference"] > 0]

            display = filt[
                ["id", "article", "location", "zone", "difference", "price", "impact", "created_date"]
            ].copy()
            display.columns = [
                "ID", "Artículo", "Ubicación", "Zona",
                "Diferencia", "Precio ($)", "Impacto ($)", "Fecha",
            ]
            display["Fecha"] = pd.to_datetime(display["Fecha"]).dt.strftime("%d/%m/%Y")

            def _color_num(val):
                if not isinstance(val, (int, float)):
                    return ""
                if val < 0:
                    return "color:#dc3545; font-weight:700"
                if val > 0:
                    return "color:#198754; font-weight:700"
                return ""

            st.dataframe(
                display.style.map(_color_num, subset=["Diferencia", "Impacto ($)"]),
                use_container_width=True,
                hide_index=True,
            )

            with st.expander("🗑️ Eliminar registro"):
                if not filt.empty:
                    del_id = st.selectbox("ID a eliminar", filt["id"].tolist())
                    if st.button("Eliminar", type="secondary"):
                        db.delete_difference(int(del_id))
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# TAB 3 · RITMO DE INVENTARIOS
# ═══════════════════════════════════════════════════════════════════════
with tab_rhythm:
    st.subheader("Ritmo de Inventarios")

    locations = db.get_locations()
    if locations.empty:
        st.warning("Primero define ubicaciones en la pestaña **Layout**.")
    else:
        rhythm = db.get_rhythm()
        today  = date.today()

        def _parse_date(val):
            if val and pd.notna(val) and str(val).strip():
                try:
                    return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
                except ValueError:
                    pass
            return None

        with st.expander("✏️ Editar ritmo de una ubicación"):
            if not rhythm.empty:
                sel = st.selectbox("Ubicación", rhythm["location"].tolist(), key="rhythm_sel")
                row = rhythm[rhythm["location"] == sel].iloc[0]

                with st.form("form_edit_rhythm"):
                    c1, c2, c3 = st.columns(3)
                    freq_val = int(row["frequency_days"]) if pd.notna(row["frequency_days"]) else 30
                    freq_in  = c1.number_input("Frecuencia (días)", 1, 365, freq_val)

                    has_start = c2.checkbox(
                        "¿Tiene fecha de inicio?", value=bool(_parse_date(row["start_date"]))
                    )
                    has_deliv = c3.checkbox(
                        "¿Tiene fecha de entrega?", value=bool(_parse_date(row["delivery_date"]))
                    )
                    start_in = deliv_in = None
                    if has_start:
                        start_in = c2.date_input(
                            "Fecha inicio",
                            value=_parse_date(row["start_date"]) or today,
                            key="s_date",
                        )
                    if has_deliv:
                        deliv_in = c3.date_input(
                            "Fecha entrega",
                            value=_parse_date(row["delivery_date"]) or today,
                            key="d_date",
                        )
                    if st.form_submit_button("Guardar", use_container_width=True):
                        db.update_rhythm(
                            int(row["location_id"]),
                            freq_in,
                            start_in if has_start else None,
                            deliv_in if has_deliv else None,
                        )
                        st.success("Actualizado.")
                        st.rerun()

        st.divider()

        rhythm = db.get_rhythm()
        rows_out = []
        for _, r in rhythm.iterrows():
            last   = _parse_date(r["delivery_date"])
            freq   = int(r["frequency_days"]) if pd.notna(r["frequency_days"]) else None
            nxt    = (last + timedelta(days=freq)) if last and freq else None
            days   = (today - last).days if last else None
            ov     = bool(nxt and nxt < today)
            dt     = bool(nxt and nxt == today)
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

        show = [
            "Ubicación", "Zona", "Frecuencia (días)",
            "Inicio", "Entrega", "Días transcurridos", "Siguiente conteo",
        ]

        def _style_row(row):
            n = len(row)
            if row["_st"] == "overdue": return ["background:#ffe5e5; color:#7f0000"] * n
            if row["_st"] == "today":   return ["background:#ede7f6; color:#311b92"] * n
            return [""] * n

        styled = (
            rdf[show + ["_st"]]
            .style.apply(_style_row, axis=1)
            .hide(subset=["_st"], axis=1)
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.caption("🟣 Conteo programado para hoy  |  🔴 Vencido")
