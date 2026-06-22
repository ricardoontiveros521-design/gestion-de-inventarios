import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import database as db

st.set_page_config(page_title="Gestor de Inventarios", layout="wide", page_icon="📦")
db.init_db()

if "sel_slot" not in st.session_state:
    st.session_state.sel_slot = None

# ══════════════════════════════════════════════════════════════════════
# SVG HELPERS
# ══════════════════════════════════════════════════════════════════════

def _zone_style(slot_key, slot_map, diff_locs, delivery_locs, start_locs, today_count, selected):
    if slot_key not in slot_map:
        return "#e9ecef", "#9aabbc", "#adb5bd", "1"
    lid = slot_map[slot_key]["id"]
    sel = slot_key == selected
    stroke, sw = ("#ff6b35", "3.5") if sel else ("#6c757d", "1.5")
    if lid in diff_locs:       return "#dc3545", "#fff",    stroke, sw
    if lid in today_count:     return "#6f42c1", "#fff",    stroke, sw
    if lid in delivery_locs:   return "#198754", "#fff",    stroke, sw
    if lid in start_locs:      return "#ffc107", "#1a1a1a", stroke, sw
    return "#cfe2ff", "#003a70", stroke, sw


def _rect(slot_key, fallback_label, x, y, w, h,
          slot_map, diff_locs, delivery_locs, start_locs, today_count, selected,
          vertical=False, font_size=11):
    bg, fg, stroke, sw = _zone_style(
        slot_key, slot_map, diff_locs, delivery_locs, start_locs, today_count, selected
    )
    label = slot_map[slot_key]["name"] if slot_key in slot_map else fallback_label
    cx, cy = x + w / 2, y + h / 2
    r = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" '
         f'fill="{bg}" stroke="{stroke}" stroke-width="{sw}"/>')
    if vertical:
        t = (f'<text transform="rotate(-90 {cx} {cy})" x="{cx}" y="{cy+4}" '
             f'text-anchor="middle" fill="{fg}" font-size="{font_size}" '
             f'font-weight="700" font-family="Arial,sans-serif">{label}</text>')
    else:
        lines = label.split("\n")
        n = len(lines)
        ty = cy - (n - 1) * 7
        spans = "".join(
            f'<tspan x="{cx}" dy="{"0" if i==0 else "14"}">{ln}</tspan>'
            for i, ln in enumerate(lines)
        )
        t = (f'<text x="{cx}" y="{ty}" text-anchor="middle" fill="{fg}" '
             f'font-size="{font_size}" font-weight="700" '
             f'font-family="Arial,sans-serif" dominant-baseline="central">{spans}</text>')
    return r + t


def _pasillo(label, x, y, w, h, vertical=False):
    cx, cy = x + w / 2, y + h / 2
    r = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="0" '
         f'fill="url(#hatch)" stroke="#bfc8d0" stroke-width="1"/>')
    if vertical:
        t = (f'<text transform="rotate(-90 {cx} {cy})" x="{cx}" y="{cy+4}" '
             f'text-anchor="middle" fill="#6c757d" font-size="8" '
             f'font-family="Arial,sans-serif">{label}</text>')
    else:
        t = (f'<text x="{cx}" y="{cy+4}" text-anchor="middle" fill="#6c757d" '
             f'font-size="9" font-weight="700" font-family="Arial,sans-serif">{label}</text>')
    return r + t


def _lbl(text, x, y, size=11, fill="#1a2e42", anchor="middle", weight="700"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" '
            f'font-size="{size}" font-weight="{weight}" '
            f'font-family="Arial,sans-serif">{text}</text>')


def make_warehouse_svg(slot_map, diff_locs, delivery_locs, start_locs, today_count, selected=None):
    kw = dict(slot_map=slot_map, diff_locs=diff_locs, delivery_locs=delivery_locs,
              start_locs=start_locs, today_count=today_count, selected=selected)

    # ── Fixed structural skeleton ──────────────────────────────────────
    p = [
        '<svg viewBox="0 0 1200 760" xmlns="http://www.w3.org/2000/svg" '
        'style="width:100%;display:block;border-radius:8px;'
        'border:2px solid #2c3e50;background:#dde8f0;">',

        '<defs><pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8" '
        'patternTransform="rotate(45 0 0)"><line x1="0" y1="0" x2="0" y2="8" '
        'stroke="#b0bec5" stroke-width="2.5"/></pattern></defs>',

        # outer building
        '<rect x="4" y="4" width="1192" height="752" rx="6" fill="#f7f9fb" '
        'stroke="#2c3e50" stroke-width="3"/>',

        # top banner
        '<rect x="235" y="4" width="775" height="24" fill="#1a2e42"/>',
        _lbl("ZONA DE RECEPCIÓN — MUELLES DE CARGA", 622, 20, size=13, fill="#ffffff"),

        # reception background
        '<rect x="235" y="28" width="775" height="168" rx="3" fill="#fef9ee" '
        'stroke="#c8a020" stroke-width="1.5" stroke-dasharray="8,4"/>',

        # left andén background
        '<rect x="4" y="195" width="230" height="453" rx="3" fill="#eef2f6" '
        'stroke="#adb5bd" stroke-width="1" stroke-dasharray="6,3"/>',
        _lbl("ANDÉN DE RECEPCIÓN", 119, 188, size=10, fill="#495057"),

        # main interior frame
        '<rect x="235" y="196" width="775" height="457" rx="3" fill="none" '
        'stroke="#2c3e50" stroke-width="2.5"/>',

        # top pasillo de tráfico
        _pasillo("PASILLO DE TRÁFICO", 235, 196, 775, 36),

        # storage label
        _lbl("ALMACENAMIENTO PRINCIPAL  —  Estanterías 100–800", 622, 250),

        # middle pasillo de tráfico
        _pasillo("PASILLO DE TRÁFICO", 235, 440, 775, 35),

        # picking label
        _lbl("ÁREA DE PICKING / PREPARACIÓN", 622, 492),

        # bottom pasillo de tráfico
        _pasillo("PASILLO DE TRÁFICO", 235, 617, 775, 35),

        # bottom banner
        '<rect x="235" y="743" width="775" height="13" fill="#1a2e42"/>',
        _lbl("ZONA DE EXPEDICIÓN", 622, 753, fill="#ffffff"),

        # right admin background
        '<rect x="1012" y="4" width="184" height="752" rx="3" fill="#f0f4f0" '
        'stroke="#adb5bd" stroke-width="1" stroke-dasharray="4,3"/>',
    ]

    # ── Dynamic zones from database ────────────────────────────────────
    sorted_zones = sorted(slot_map.items(), key=lambda x: x[1].get("sort", 0))
    for slot_key, data in sorted_zones:
        p.append(_rect(
            slot_key, data["name"],
            data["svg_x"], data["svg_y"],
            data["svg_w"], data["svg_h"],
            vertical=data["svg_vertical"],
            **kw,
        ))

    p.append("</svg>")
    return "".join(p)


# ══════════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════════
st.title("📦 Gestor de Inventarios")

tab_layout, tab_diff, tab_rhythm = st.tabs(
    ["🗺️ Layout", "📋 Diferencias", "🔄 Ritmo de Inventarios"]
)

# ─────────────────────────────────────────────────────────────────────
# TAB 1 · LAYOUT
# ─────────────────────────────────────────────────────────────────────
with tab_layout:

    locations = db.get_locations()

    # Auto-populate if no slots exist
    no_slots = (
        locations.empty
        or not locations["slot_key"].astype(str).str.strip().any()
    )
    if no_slots:
        st.info("El mapa está vacío. Carga las zonas del almacén para comenzar.")
        if st.button("🏭 Cargar zonas del almacén", type="primary"):
            added = db.batch_add_warehouse_zones()
            st.success(f"Se cargaron {added} zonas.")
            st.rerun()
        st.stop()

    diff_locs, delivery_locs, start_locs, today_count = db.get_location_status()

    # Build slot_map with SVG position data
    slot_map = {
        row["slot_key"]: {
            "id":           int(row["id"]),
            "name":         row["name"],
            "zone":         row["zone"] or "",
            "svg_x":        int(row.get("svg_x") or 0),
            "svg_y":        int(row.get("svg_y") or 0),
            "svg_w":        int(row.get("svg_w") or 100),
            "svg_h":        int(row.get("svg_h") or 60),
            "svg_vertical": bool(row.get("svg_vertical") or 0),
            "sort":         int(row.get("row_pos") or 0),
        }
        for _, row in locations.iterrows()
        if row.get("slot_key") and str(row["slot_key"]).strip()
    }

    # ── Legend ────────────────────────────────────────────────────────
    l1, l2, l3, l4, l5 = st.columns(5)
    l1.markdown("⬜ Sin actividad")
    l2.markdown("🟡 Iniciado")
    l3.markdown("🟢 Entregado")
    l4.markdown("🔴 Diferencias")
    l5.markdown("🟣 Conteo hoy")

    # ── SVG MAP ───────────────────────────────────────────────────────
    st.markdown(
        make_warehouse_svg(
            slot_map, diff_locs, delivery_locs, start_locs, today_count,
            selected=st.session_state.sel_slot,
        ),
        unsafe_allow_html=True,
    )

    st.divider()

    # ── EDITOR: Mover y redimensionar zonas ───────────────────────────
    with st.expander("🖊️ Editar posición y tamaño de una zona"):
        zones_df = locations[locations["slot_key"].astype(str).str.strip() != ""]
        if not zones_df.empty:
            zone_options = zones_df["name"].tolist()
            edit_name = st.selectbox(
                "Zona a editar", zone_options, key="edit_pos_sel"
            )
            ez = zones_df[zones_df["name"] == edit_name].iloc[0]

            st.caption(
                "💡 El canvas del mapa mide **1200 × 760**. "
                "Arrastra los sliders para reubicar la zona hasta que encaje con tu almacén real."
            )

            with st.form("form_edit_svg"):
                c1, c2 = st.columns(2)
                new_x = c1.slider("Posición X  (izquierda ↔ derecha)",  0, 1150,
                                   int(ez.get("svg_x") or 0), step=5)
                new_y = c2.slider("Posición Y  (arriba ↕ abajo)",        0, 720,
                                   int(ez.get("svg_y") or 0), step=5)
                new_w = c1.slider("Ancho (W)",  20, 800,
                                   int(ez.get("svg_w") or 100), step=5)
                new_h = c2.slider("Alto (H)",   20, 500,
                                   int(ez.get("svg_h") or 60), step=5)
                new_v = st.checkbox(
                    "Texto vertical (ideal para racks angostos)",
                    value=bool(ez.get("svg_vertical") or 0),
                )

                s1, s2 = st.columns(2)
                if s1.form_submit_button("💾 Guardar posición", use_container_width=True):
                    db.update_location_svg(
                        int(ez["id"]), new_x, new_y, new_w, new_h, int(new_v)
                    )
                    st.success("✅ Posición guardada.")
                    st.rerun()
                if s2.form_submit_button("↩️ Restablecer original", use_container_width=True):
                    db.reset_location_svg(str(ez.get("slot_key", "")))
                    st.success("Posición restablecida al valor genérico.")
                    st.rerun()

    # ── EDITOR: Renombrar / cambiar grupo ─────────────────────────────
    with st.expander("✏️ Renombrar zona o cambiar grupo"):
        all_names = locations["name"].tolist()
        sel_name  = st.selectbox(
            "Zona a editar", ["— Selecciona —"] + all_names, key="loc_selector"
        )
        if sel_name != "— Selecciona —":
            sel_row = locations[locations["name"] == sel_name].iloc[0]
            lid = int(sel_row["id"])
            p1, p2 = st.columns(2)
            with p1:
                with st.form("form_edit_loc"):
                    new_name = st.text_input("Nombre / Código", value=sel_row["name"])
                    new_zone = st.text_input("Grupo / Zona",    value=sel_row["zone"] or "")
                    if st.form_submit_button("💾 Guardar", use_container_width=True):
                        ok, msg = db.update_location(lid, new_name, new_zone)
                        if ok:
                            st.rerun()
                        else:
                            st.error(msg)
            with p2:
                st.markdown(" ")
                st.markdown(" ")
                if st.button("🗑️ Eliminar ubicación", type="secondary", use_container_width=True):
                    db.delete_location(lid)
                    st.rerun()

    # ── Agregar ubicación extra ────────────────────────────────────────
    with st.expander("➕ Agregar zona extra (no incluida en el mapa base)"):
        with st.form("form_add_extra", clear_on_submit=True):
            c1, c2 = st.columns(2)
            extra_name = c1.text_input("Nombre *", placeholder="RACK-XL")
            extra_zone = c2.text_input("Zona / Grupo", placeholder="Almacenamiento")
            if st.form_submit_button("Agregar"):
                if extra_name.strip():
                    ok, msg = db.add_location(extra_name, extra_zone, 99, 0)
                    if ok:
                        st.success(f"✅ {extra_name.upper()} agregado.")
                        st.rerun()
                    else:
                        st.error(msg)


# ─────────────────────────────────────────────────────────────────────
# TAB 2 · DIFERENCIAS
# ─────────────────────────────────────────────────────────────────────
with tab_diff:
    st.subheader("Registro de Diferencias")
    locations = db.get_locations()

    if locations.empty:
        st.warning("Primero carga las zonas en la pestaña **Layout**.")
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
            if locs_filter: filt = filt[filt["location"].isin(locs_filter)]
            if tipo_filter == "Faltantes": filt = filt[filt["difference"] < 0]
            elif tipo_filter == "Sobrantes": filt = filt[filt["difference"] > 0]

            display = filt[["id","article","location","zone","difference","price","impact","created_date"]].copy()
            display.columns = ["ID","Artículo","Ubicación","Zona","Diferencia","Precio ($)","Impacto ($)","Fecha"]
            display["Fecha"] = pd.to_datetime(display["Fecha"]).dt.strftime("%d/%m/%Y")

            def _cn(v):
                if not isinstance(v, (int, float)): return ""
                return "color:#dc3545;font-weight:700" if v < 0 else ("color:#198754;font-weight:700" if v > 0 else "")

            st.dataframe(display.style.map(_cn, subset=["Diferencia","Impacto ($)"]),
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
        st.warning("Primero carga las zonas en la pestaña **Layout**.")
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
                    fv       = int(row["frequency_days"]) if pd.notna(row["frequency_days"]) else 30
                    freq_in  = c1.number_input("Frecuencia (días)", 1, 365, fv)
                    has_s    = c2.checkbox("¿Tiene fecha de inicio?",   value=bool(_pd(row["start_date"])))
                    has_d    = c3.checkbox("¿Tiene fecha de entrega?",  value=bool(_pd(row["delivery_date"])))
                    si = di  = None
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
