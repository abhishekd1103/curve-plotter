"""
Transient Study Plotter
-----------------------
An ETAP-style plotting tool that supports multiple curves PLUS user-defined
overlay reference lines (dotted/dashed) — something ETAP's native plot cannot do.

Run locally:   streamlit run app.py
Deploy:        Push to GitHub and connect at https://share.streamlit.io
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from io import BytesIO, StringIO

# ─────────────────────────────────────────────────────────────
# Custom "ETAP" template — light blue panel, white gridlines,
# crisp axes, no markers by default. Matches ETAP's plot style.
# ─────────────────────────────────────────────────────────────
pio.templates["etap"] = go.layout.Template(
    layout=dict(
        paper_bgcolor="white",
        plot_bgcolor="#E8EEF5",
        font=dict(family="Arial, sans-serif", size=13, color="#222"),
        xaxis=dict(
            gridcolor="white", gridwidth=1.5,
            zeroline=False,
            showline=True, linecolor="#B0B8C4", linewidth=1,
            ticks="outside", tickcolor="#B0B8C4", ticklen=4,
            mirror=True,
        ),
        yaxis=dict(
            gridcolor="white", gridwidth=1.5,
            zeroline=False,
            showline=True, linecolor="#B0B8C4", linewidth=1,
            ticks="outside", tickcolor="#B0B8C4", ticklen=4,
            mirror=True,
        ),
        colorway=["#1F77FF", "#E63946", "#2CA02C", "#9467BD",
                  "#FF7F0E", "#17BECF", "#8C564B", "#E377C2"],
    )
)
pio.templates.default = "etap"

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Transient Study Plotter",
    page_icon="⚡",
    layout="wide",
)

DASH_OPTIONS = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]

# ─────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────
if "curves" not in st.session_state:
    # Seed with an example curve so the plot isn't empty on first load
    st.session_state.curves = [{
        "name": "SW-B-1A1 Frequency — CASE01F (example)",
        "color": "#636EFA",
        "dash": "solid",
        "width": 2,
        "data": pd.DataFrame({
            "Time (s)": [0, 1, 2, 3, 4, 5, 7, 10, 15, 20, 25, 30],
            "Value":    [100, 100, 95, 98, 100.2, 100.4, 100.3, 100.2, 100.1, 100, 100, 100],
        }),
    }]

if "overlays" not in st.session_state:
    st.session_state.overlays = []

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def parse_pasted_data(text: str):
    """Accept CSV / TSV / whitespace-separated two-column data, with or without headers."""
    text = (text or "").strip()
    if not text:
        return None
    for sep in [",", "\t", r"\s+"]:
        try:
            df = pd.read_csv(StringIO(text), sep=sep, engine="python", header=None)
            if df.shape[1] >= 2:
                df = df.iloc[:, :2].copy()
                df.columns = ["Time (s)", "Value"]
                df = df.apply(pd.to_numeric, errors="coerce").dropna()
                if len(df) > 0:
                    return df.reset_index(drop=True)
        except Exception:
            continue
    return None


def build_figure(curves, overlays, settings):
    fig = go.Figure()

    # Curves
    for c in curves:
        fig.add_trace(go.Scatter(
            x=c["data"]["Time (s)"],
            y=c["data"]["Value"],
            mode="lines+markers" if settings["show_markers"] else "lines",
            name=c["name"],
            line=dict(
                color=c["color"],
                width=c["width"],
                dash=c["dash"],
                shape=settings["line_shape"],
            ),
            marker=dict(size=4, line=dict(width=0)),
            connectgaps=True,
            hovertemplate="<b>%{fullData.name}</b><br>t = %{x:.3f} s<br>y = %{y:.3f}<extra></extra>",
        ))

    # Overlay reference lines
    for ov in overlays:
        if ov["type"] == "Horizontal":
            fig.add_hline(
                y=ov["value"],
                line=dict(color=ov["color"], width=ov["width"], dash=ov["dash"]),
                annotation_text=ov["label"],
                annotation_position="top right",
                annotation_font_color=ov["color"],
            )
        else:  # Vertical
            fig.add_vline(
                x=ov["value"],
                line=dict(color=ov["color"], width=ov["width"], dash=ov["dash"]),
                annotation_text=ov["label"],
                annotation_position="top",
                annotation_font_color=ov["color"],
            )

    fig.update_layout(
        title=dict(text=settings["title"], x=0.5, xanchor="center", font=dict(size=18)),
        xaxis_title=settings["x_label"],
        yaxis_title=settings["y_label"],
        template=settings["theme"],
        height=620,
        hovermode="x unified",
        legend=dict(
            orientation="v", x=1.02, y=1,
            bgcolor="rgba(255,255,255,0)",
            bordercolor="rgba(0,0,0,0)", borderwidth=0,
        ),
        margin=dict(l=70, r=240, t=80, b=70),
    )

    if settings["x_range"]:
        fig.update_xaxes(range=settings["x_range"])
    if settings["y_range"]:
        fig.update_yaxes(range=settings["y_range"])

    return fig


# ─────────────────────────────────────────────────────────────
# Sidebar — plot settings
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🎨 Plot Settings")
    title = st.text_input("Plot Title", "Transient Stability Study — Bus Frequency")
    x_label = st.text_input("X-Axis Label", "Time (s)")
    y_label = st.text_input("Y-Axis Label", "f in %")
    theme = st.selectbox(
        "Theme",
        ["etap", "plotly", "plotly_white", "plotly_dark", "ggplot2", "seaborn", "simple_white"],
        index=0,
        help="`etap` matches the ETAP-style light blue panel with white gridlines.",
    )
    show_markers = st.checkbox(
        "Show data markers",
        value=False,
        help="Off = clean lines (recommended for dense ETAP data). "
             "On = small dots at each data point (best for sparse data, ≲ 30 points).",
    )
    line_shape = st.selectbox(
        "Line shape",
        ["linear", "spline", "hv", "vh", "hvh", "vhv"],
        index=0,
        help="`linear` = straight segments (default). `spline` = smoothed.",
    )

    st.divider()
    st.subheader("Axis Ranges (optional)")
    use_xrange = st.checkbox("Custom X range")
    x_range = None
    if use_xrange:
        c1, c2 = st.columns(2)
        x_range = [c1.number_input("X min", value=0.0), c2.number_input("X max", value=30.0)]

    use_yrange = st.checkbox("Custom Y range")
    y_range = None
    if use_yrange:
        c1, c2 = st.columns(2)
        y_range = [c1.number_input("Y min", value=0.0), c2.number_input("Y max", value=110.0)]

    st.divider()
    if st.button("🧹 Clear all curves"):
        st.session_state.curves = []
        st.rerun()
    if st.button("🧹 Clear all overlays"):
        st.session_state.overlays = []
        st.rerun()

settings = {
    "title": title, "x_label": x_label, "y_label": y_label,
    "theme": theme, "show_markers": show_markers, "line_shape": line_shape,
    "x_range": x_range, "y_range": y_range,
}

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
st.title("⚡ Transient Study Plotter")
st.caption("Add multiple curves, drop overlay reference lines, and export. Built for ETAP-style transient stability plots.")

tab_plot, tab_curves, tab_overlays = st.tabs(["🖼️ Plot & Export", "📈 Curves", "📏 Overlay Lines"])

# ---------- Plot tab ----------
with tab_plot:
    if not st.session_state.curves:
        st.warning("Add at least one curve in the **Curves** tab to see the plot.")
    else:
        fig = build_figure(st.session_state.curves, st.session_state.overlays, settings)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Export")
        ec1, ec2, ec3 = st.columns(3)

        # HTML (interactive)
        html_bytes = fig.to_html(include_plotlyjs="cdn").encode("utf-8")
        ec1.download_button(
            "💾 Interactive HTML", html_bytes,
            file_name="transient_plot.html", mime="text/html",
            use_container_width=True,
        )

        # PNG (requires kaleido)
        try:
            png_bytes = fig.to_image(format="png", width=1600, height=800, scale=2)
            ec2.download_button(
                "📷 PNG Image", png_bytes,
                file_name="transient_plot.png", mime="image/png",
                use_container_width=True,
            )
        except Exception:
            ec2.info("PNG export needs `kaleido` → `pip install kaleido`")

        # Excel (all curve data)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            for i, c in enumerate(st.session_state.curves):
                safe = "".join(ch for ch in c["name"] if ch not in r"[]:*?/\\")[:28] or f"Curve{i+1}"
                c["data"].to_excel(writer, sheet_name=safe, index=False)
            if st.session_state.overlays:
                pd.DataFrame(st.session_state.overlays).to_excel(writer, sheet_name="Overlays", index=False)
        ec3.download_button(
            "📊 Excel (data)", buf.getvalue(),
            file_name="transient_plot_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

# ---------- Curves tab ----------
with tab_curves:
    st.subheader("➕ Add a new curve")

    mode = st.radio(
        "Input method",
        ["Paste data", "Upload CSV / Excel", "Manual entry"],
        horizontal=True,
    )

    new_data = None

    if mode == "Paste data":
        st.caption("Two columns (Time, Value). Separator can be comma, tab, or space. Headers optional.")
        pasted = st.text_area(
            "Paste here",
            height=160,
            placeholder="0, 100\n1, 100\n2, 95\n3, 98\n5, 100.5\n10, 100.2\n...",
        )
        if pasted:
            new_data = parse_pasted_data(pasted)
            if new_data is not None:
                st.success(f"Parsed {len(new_data)} points")
                st.dataframe(new_data.head(), use_container_width=True)
            else:
                st.error("Couldn't parse — make sure there are two numeric columns.")

    elif mode == "Upload CSV / Excel":
        uploaded = st.file_uploader("File", type=["csv", "xlsx", "xls"])
        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
                cols = df.columns.tolist()
                c1, c2 = st.columns(2)
                tcol = c1.selectbox("Time column", cols, index=0)
                vcol = c2.selectbox("Value column", cols, index=min(1, len(cols) - 1))
                new_data = pd.DataFrame({
                    "Time (s)": pd.to_numeric(df[tcol], errors="coerce"),
                    "Value":    pd.to_numeric(df[vcol], errors="coerce"),
                }).dropna().reset_index(drop=True)
                st.success(f"Loaded {len(new_data)} points")
                st.dataframe(new_data.head(), use_container_width=True)
            except Exception as e:
                st.error(f"Error reading file: {e}")

    else:  # Manual entry
        st.caption("Edit the table; use the + row at the bottom to extend.")
        default = pd.DataFrame({
            "Time (s)": [0.0, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0],
            "Value":    [100.0, 95.0, 100.5, 100.2, 100.1, 100.0, 100.0],
        })
        new_data = st.data_editor(default, num_rows="dynamic", use_container_width=True, key="manual_editor")

    st.divider()
    st.markdown("**Curve appearance**")
    p1, p2, p3, p4 = st.columns([3, 1, 1, 1])
    new_name  = p1.text_input("Name", f"Curve {len(st.session_state.curves) + 1}")
    new_color = p2.color_picker("Color", "#EF553B")
    new_dash  = p3.selectbox("Style", DASH_OPTIONS, key="new_dash")
    new_width = p4.number_input("Width", 1.0, 6.0, 1.5, step=0.5, key="new_width")

    if st.button("➕ Add curve", type="primary", use_container_width=True):
        if new_data is not None and len(new_data) > 0:
            st.session_state.curves.append({
                "name": new_name, "color": new_color,
                "dash": new_dash, "width": float(new_width),
                "data": new_data.reset_index(drop=True),
            })
            st.success(f"Added: {new_name}")
            st.rerun()
        else:
            st.warning("No data yet — paste, upload, or enter values first.")

    st.divider()
    st.subheader(f"Existing curves ({len(st.session_state.curves)})")

    if not st.session_state.curves:
        st.info("No curves yet.")
    for i, c in enumerate(st.session_state.curves):
        with st.expander(f"{i+1}.  {c['name']}    ·    {len(c['data'])} points"):
            r1, r2, r3, r4, r5 = st.columns([3, 1, 1, 1, 0.7])
            c["name"]  = r1.text_input("Name", c["name"], key=f"n_{i}")
            c["color"] = r2.color_picker("Color", c["color"], key=f"c_{i}")
            c["dash"]  = r3.selectbox("Style", DASH_OPTIONS,
                                      index=DASH_OPTIONS.index(c["dash"]), key=f"d_{i}")
            c["width"] = float(r4.number_input("Width", 1.0, 6.0, float(c["width"]), step=0.5, key=f"w_{i}"))
            if r5.button("🗑️", key=f"del_{i}", help="Delete this curve"):
                st.session_state.curves.pop(i)
                st.rerun()
            edited = st.data_editor(c["data"], num_rows="dynamic",
                                    use_container_width=True, key=f"ed_{i}")
            st.session_state.curves[i]["data"] = edited

# ---------- Overlays tab ----------
with tab_overlays:
    st.subheader("➕ Add overlay reference line")
    st.caption("Use for under/over-frequency limits, trip times, setpoints, steady-state targets, etc.")

    o1, o2, o3, o4, o5, o6 = st.columns([1.1, 1, 2, 1, 1.2, 1])
    ov_type  = o1.selectbox("Type", ["Horizontal", "Vertical"], key="ov_type")
    ov_value = o2.number_input("Value", value=95.0, key="ov_value")
    ov_label = o3.text_input("Label", "Under-frequency limit (95%)", key="ov_label")
    ov_color = o4.color_picker("Color", "#E74C3C", key="ov_color")
    ov_dash  = o5.selectbox("Style", ["dash", "dot", "dashdot", "longdash", "longdashdot", "solid"], key="ov_dash")
    ov_width = o6.number_input("Width", 1, 6, 2, key="ov_width")

    if st.button("➕ Add overlay", type="primary", key="add_ov", use_container_width=True):
        st.session_state.overlays.append({
            "type": ov_type, "value": float(ov_value), "label": ov_label,
            "color": ov_color, "dash": ov_dash, "width": int(ov_width),
        })
        st.success(f"Added {ov_type.lower()} line at {ov_value}")
        st.rerun()

    st.divider()
    st.subheader(f"Existing overlays ({len(st.session_state.overlays)})")

    if not st.session_state.overlays:
        st.info(
            "No overlay lines yet. Typical examples: horizontal at **95 %** "
            "(under-frequency threshold), vertical at **10 s** (load-shedding trip time)."
        )
    else:
        for i, ov in enumerate(st.session_state.overlays):
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1.1, 1, 2, 1, 1.2, 1, 0.6])
            ov["type"]  = c1.selectbox("Type", ["Horizontal", "Vertical"],
                                       index=0 if ov["type"] == "Horizontal" else 1,
                                       key=f"ot_{i}")
            ov["value"] = float(c2.number_input("Value", value=float(ov["value"]), key=f"ov_{i}"))
            ov["label"] = c3.text_input("Label", ov["label"], key=f"ol_{i}")
            ov["color"] = c4.color_picker("Color", ov["color"], key=f"oc_{i}")
            dash_opts = ["dash", "dot", "dashdot", "longdash", "longdashdot", "solid"]
            ov["dash"]  = c5.selectbox("Style", dash_opts,
                                       index=dash_opts.index(ov["dash"]), key=f"od_{i}")
            ov["width"] = int(c6.number_input("Width", 1, 6, ov["width"], key=f"ow_{i}"))
            if c7.button("🗑️", key=f"ovdel_{i}"):
                st.session_state.overlays.pop(i)
                st.rerun()

# ─────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "💡 **Workflow tip:** Export your ETAP curve data as CSV → upload here → "
    "add your threshold lines (95 %, 98.5 %, trip time, etc.) → export as PNG or interactive HTML."
)
