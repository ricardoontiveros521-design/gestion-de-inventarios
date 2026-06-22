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

# ── Global styles ──────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .loc-box {
        display:inline-flex; align-items:center; justify-content:center;
        width:90px; height:55px; border-radius:8px; font-weight:700;
        font-size:11px; text-align:center; padding:4px; margin:3px;
        border:2px solid rgba(0,0,0,.15); word-break:break-word;
        vertical-align:top;
    }
    .loc-empty  { width:90px; height:55px; margin:3px; display:inline-block; vertical-align:top; }
    .loc-default{ background:#e9ecef; color:#343a40; }
    .loc-yellow { background:#ffc107; color:#212529; }
    .loc-green  { background:#198754; color:#fff; }
    .loc-red    { background:#dc3545; color:#fff; }
    .loc-purple { background:#6f42c1; color:#fff; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📦 Gestor de Inventarios")

tab_layout, tab_diff, tab_rhythm = st.tabs(
    ["🗺️ Layout", "📋 Diferencias", "🔄 Ritmo de Inventarios"]
)


# ═══════════════════════════════════════════════════════════════════════
# TAB 1 · LAYOUT
# ═══════════════════════════════════════════════════════════════════════
with tab_layout:
    st.subheader("Mapa de Ubicaciones")

    col_form, col_legend = st.columns([4, 1])

    with col_legend:
        st.markdown(
            """
            **Leyenda**
            - 🟡 Iniciado
            - 🟢 Entregado
            - 🔴 Diferencias
            - 🟣 Conteo hoy
            """
        )

    with col_form:
        with st.expander("➕ Agregar ubicación"):
            with st.form("form_add_loc", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                name_in = c1.text_input("Nombre *", placeholder="RACK-A1")
                zone_in = c2.text_input("Zona", placeholder="Almacén Norte")
                row_in  = c3.number_input("Fila", 0, 30, 0)
                col_in  = c4.number_input("Columna", 0, 30, 0)
                if st.form_submit_button("Agregar", use_container_width=True):
                    if name_in.strip():
                        ok, msg = db.add_location(name_in, zone_in, row_in, col_in)
                        if ok:
                            st.success(f"✅ {name_in.upper()} agregado.")
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("El nombre es obligatorio.")

    locations = db.get_locations()

    if locations.empty:
        st.info("Sin ubicaciones. Usa el formulario de arriba para agregar la primera.")
    else:
        diff_locs, delivery_locs, start_locs, today_count = db.get_location_status()

        max_r = int(locations["row_pos"].max()) + 1
        max_c = int(locations["col_pos"].max()) + 1

        grid = {
            (int(r["row_pos"]), int(r["col_pos"])): r
            for _, r in locations.iterrows()
        }

        html_rows = []
        for r in range(max_r):
            cells = []
            for c in range(max_c):
                if (r, c) in grid:
                    loc = grid[(r, c)]
                    lid = int(loc["id"])
                    if   lid in diff_locs:     css = "loc-red"
                    elif lid in today_count:   css = "loc-purple"
                    elif lid in delivery_locs: css = "loc-green"
                    elif lid in start_locs:    css = "loc-yellow"
                    else:                      css = "loc-default"
                    tooltip = loc["zone"] or ""
                    cells.append(
                        f'<div class="loc-box {css}" title="{tooltip}">{loc["name"]}</div>'
                    )
                else:
                    cells.append('<div class="loc-empty"></div>')
            html_rows.append("".join(cells))

        map_html = (
            '<div style="overflow-x:auto;">'
            + "".join(
                f'<div style="white-space:nowrap;">{row}</div>' for row in html_rows
            )
            + "</div>"
        )
        st.markdown(map_html, unsafe_allow_html=True)

        st.divider()
        with st.expander("🗑️ Eliminar ubicación"):
            del_name = st.selectbox(
                "Ubicación a eliminar",
                locations["name"].tolist(),
                key="del_loc_sel",
            )
            st.caption("⚠️ Se eliminan también sus diferencias y ritmo asociados.")
            if st.button("Eliminar", type="secondary", key="btn_del_loc"):
                lid = int(locations[locations["name"] == del_name]["id"].values[0])
                db.delete_location(lid)
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# TAB 2 · DIFERENCIAS
# ═══════════════════════════════════════════════════════════════════════
with tab_diff:
    st.subheader("Registro de Diferencias")

    locations = db.get_locations()
    if locations.empty:
        st.warning("Primero agrega ubicaciones en la pestaña **Layout**.")
    else:
        with st.expander("➕ Registrar diferencia"):
            with st.form("form_add_diff", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                art_in   = c1.text_input("Artículo *")
                loc_in   = c2.selectbox("Ubicación *", locations["name"].tolist())
                diff_in  = c3.number_input(
                    "Diferencia",
                    value=0.0,
                    step=1.0,
                    help="Negativo = faltante · Positivo = sobrante",
                )
                price_in = c4.number_input("Precio ($)", min_value=0.0, value=0.0, step=0.01)
                st.caption(f"Fecha automática: **{date.today().strftime('%d/%m/%Y')}**")
                if st.form_submit_button("Registrar", use_container_width=True):
                    if art_in.strip():
                        lid = int(
                            locations[locations["name"] == loc_in]["id"].values[0]
                        )
                        db.add_difference(art_in, lid, diff_in, price_in)
                        st.success("Diferencia registrada.")
                        st.rerun()
                    else:
                        st.warning("El artículo es obligatorio.")

        df = db.get_differences()
        if df.empty:
            st.info("Sin diferencias registradas.")
        else:
            total_impact = df["impact"].sum()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Registros",      len(df))
            m2.metric("Faltantes",      int((df["difference"] < 0).sum()))
            m3.metric("Sobrantes",      int((df["difference"] > 0).sum()))
            m4.metric("Impacto neto ($)", f"${total_impact:,.2f}")

            st.divider()

            f1, f2 = st.columns([3, 1])
            locs_filter = f1.multiselect(
                "Filtrar por ubicación", df["location"].unique().tolist()
            )
            tipo_filter = f2.radio(
                "Tipo", ["Todos", "Faltantes", "Sobrantes"], horizontal=True
            )

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

            styled = display.style.map(
                _color_num, subset=["Diferencia", "Impacto ($)"]
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)

            with st.expander("🗑️ Eliminar registro"):
                if not filt.empty:
                    del_id = st.selectbox("ID a eliminar", filt["id"].tolist())
                    if st.button("Eliminar registro", type="secondary"):
                        db.delete_difference(int(del_id))
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# TAB 3 · RITMO DE INVENTARIOS
# ═══════════════════════════════════════════════════════════════════════
with tab_rhythm:
    st.subheader("Ritmo de Inventarios")

    locations = db.get_locations()
    if locations.empty:
        st.warning("Primero agrega ubicaciones en la pestaña **Layout**.")
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

        # ── Edit panel ────────────────────────────────────────────────
        with st.expander("✏️ Editar ritmo de una ubicación"):
            if not rhythm.empty:
                sel = st.selectbox(
                    "Selecciona ubicación", rhythm["location"].tolist(), key="rhythm_sel"
                )
                row = rhythm[rhythm["location"] == sel].iloc[0]

                with st.form("form_edit_rhythm"):
                    c1, c2, c3 = st.columns(3)
                    freq_val = int(row["frequency_days"]) if pd.notna(row["frequency_days"]) else 30
                    freq_in  = c1.number_input("Frecuencia (días)", 1, 365, freq_val)

                    has_start  = c2.checkbox("¿Tiene fecha de inicio?",
                                             value=bool(_parse_date(row["start_date"])))
                    has_deliv  = c3.checkbox("¿Tiene fecha de entrega?",
                                             value=bool(_parse_date(row["delivery_date"])))

                    start_in = deliv_in = None
                    if has_start:
                        start_in = c2.date_input(
                            "Fecha inicio",
                            value=_parse_date(row["start_date"]) or today,
                            key="start_date_in",
                        )
                    if has_deliv:
                        deliv_in = c3.date_input(
                            "Fecha entrega",
                            value=_parse_date(row["delivery_date"]) or today,
                            key="deliv_date_in",
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

        # ── Build computed table ──────────────────────────────────────
        rhythm = db.get_rhythm()
        rows   = []
        for _, r in rhythm.iterrows():
            last_date  = _parse_date(r["delivery_date"])
            days_since = (today - last_date).days if last_date else None
            freq       = int(r["frequency_days"]) if pd.notna(r["frequency_days"]) else None
            next_count = (last_date + timedelta(days=freq)) if last_date and freq else None
            overdue    = bool(next_count and next_count < today)
            due_today  = bool(next_count and next_count == today)

            rows.append(
                {
                    "Ubicación":          r["location"],
                    "Zona":               r["zone"] or "",
                    "Frecuencia (días)":  freq or "",
                    "Inicio":             r["start_date"] or "",
                    "Entrega":            r["delivery_date"] or "",
                    "Días transcurridos": days_since if days_since is not None else "",
                    "Siguiente conteo":   next_count.strftime("%d/%m/%Y") if next_count else "",
                    "_st":                "overdue" if overdue else ("today" if due_today else ""),
                }
            )

        rdf = pd.DataFrame(rows)

        m1, m2, m3 = st.columns(3)
        m1.metric("Ubicaciones",  len(rdf))
        m2.metric("Conteo hoy 🟣", int((rdf["_st"] == "today").sum()))
        m3.metric("Vencidos 🔴",   int((rdf["_st"] == "overdue").sum()))

        show = [
            "Ubicación", "Zona", "Frecuencia (días)",
            "Inicio", "Entrega", "Días transcurridos", "Siguiente conteo",
        ]

        def _style_row(row):
            s = row["_st"]
            n = len(row)
            if s == "overdue":
                return ["background-color:#ffe5e5; color:#7f0000"] * n
            if s == "today":
                return ["background-color:#ede7f6; color:#311b92"] * n
            return [""] * n

        styled_rhythm = (
            rdf[show + ["_st"]]
            .style.apply(_style_row, axis=1)
            .hide(subset=["_st"], axis=1)
        )
        st.dataframe(styled_rhythm, use_container_width=True, hide_index=True)
        st.caption("🟣 Conteo programado para hoy  |  🔴 Vencido (siguiente conteo ya pasó)")
