"""
Streamlit Dashboard — PRJ-053 Restaurant Sales Dashboard
Complete 3-Week Implementation — Stunning UI
Run: streamlit run frontend/app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import httpx
from datetime import date, timedelta
import io, csv

API = "http://localhost:8000"

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🍽️ Restaurant Sales Dashboard",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background: #0f0f1a; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background: #1a1a2e; border-right: 1px solid #16213e; }
    
    /* Metric cards */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 15px rgba(255,107,53,0.1);
    }
    [data-testid="stMetricValue"] { color: #FF6B35 !important; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #a0aec0 !important; }
    
    /* Headers */
    h1, h2, h3 { color: #FF6B35 !important; }
    
    /* Dataframe */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: #1a1a2e; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { color: #a0aec0; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #FF6B35; border-bottom: 2px solid #FF6B35; }
    
    /* Divider */
    hr { border-color: #0f3460; }
    
    /* Selectbox and inputs */
    .stSelectbox > div > div { background: #1a1a2e; border-color: #0f3460; color: white; }
    
    /* Success/info boxes */
    .stSuccess { background: #1a2e1a; border-color: #2ecc71; }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #FF6B35, #f7931e);
        color: white; border: none; border-radius: 8px;
        font-weight: bold;
    }
    
    /* Card style for sections */
    .metric-row { margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── Helper ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch(endpoint, qp={}):
    try:
        r = httpx.get(f"{API}{endpoint}", params=qp, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return None

CHART_COLORS = ["#FF6B35","#F7931E","#FFD700","#2ECC71","#3498DB","#9B59B6","#E74C3C","#1ABC9C"]

def make_chart(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(26,26,46,0.8)",
        font=dict(color="#a0aec0", size=12),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#a0aec0")),
        xaxis=dict(gridcolor="#16213e", zerolinecolor="#16213e"),
        yaxis=dict(gridcolor="#16213e", zerolinecolor="#16213e"),
    )
    return fig

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:10px 0'>
        <div style='font-size:3rem'>🍽️</div>
        <div style='color:#FF6B35; font-size:1.2rem; font-weight:bold'>Restaurant Dashboard</div>
        <div style='color:#a0aec0; font-size:0.8rem'>PRJ-053 · Ya Khaiyum.A</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 📅 Date Range")
    today         = date.today()
    default_start = date(2025, 2, 1)
    default_end   = date(2025, 4, 30)

    col_a, col_b  = st.columns(2)
    with col_a:
        start_date = st.date_input("From", value=default_start)
    with col_b:
        end_date   = st.date_input("To",   value=default_end)

    if start_date > end_date:
        st.error("Start must be before End")
        st.stop()

    st.markdown("### 🔍 Filters")
    order_type   = st.selectbox("Order Type",   ["All","Dine-in","Takeaway","Delivery"])
    payment_mode = st.selectbox("Payment Mode", ["All","Cash","UPI","Card","Online"])
    top_n        = st.slider("Top N Items", 5, 20, 10)

    st.markdown("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

params = {"start": start_date.isoformat(), "end": end_date.isoformat()}
order_params = {**params}
if order_type   != "All": order_params["order_type"]   = order_type
if payment_mode != "All": order_params["payment_mode"] = payment_mode

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a1a2e,#16213e); 
     padding:20px 30px; border-radius:15px; border-left:4px solid #FF6B35;
     margin-bottom:20px'>
    <h1 style='margin:0; color:#FF6B35'>🍽️ Restaurant Sales Dashboard</h1>
    <p style='margin:5px 0 0 0; color:#a0aec0'>
        Business Intelligence Dashboard · Period: <b style='color:#FF6B35'>
        {start_date.strftime("%d %b %Y")}</b> → <b style='color:#FF6B35'>
        {end_date.strftime("%d %b %Y")}</b>
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview", "🍽️ Menu Analytics",
    "👥 Customers", "📅 Time Analysis", "📋 Orders & Export"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    kpi  = fetch("/kpis",            params)
    trend= fetch("/revenue-trend",   params)
    peak = fetch("/peak-hours",      params)
    cat  = fetch("/category-split",  params)
    ot   = fetch("/order-type-split",params)
    pay  = fetch("/payment-split",   params)

    # KPI Cards
    if kpi:
        st.markdown("### 💰 Key Performance Indicators")
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("💰 Revenue",          f"₹{kpi['total_revenue']:,.0f}")
        c2.metric("🛒 Total Orders",      f"{kpi['total_orders']:,}")
        c3.metric("✅ Completed",         f"{kpi['completed_orders']:,}")
        c4.metric("📊 Avg Order",         f"₹{kpi['avg_order_value']:,.0f}")
        c5.metric("👤 Customers",         f"{kpi['unique_customers']:,}")
        c6.metric("🔁 Repeat",           f"{kpi['repeat_customers']:,}")

    st.markdown("---")

    # Revenue Trend + Peak Hours
    col1, col2 = st.columns([2,1])

    with col1:
        st.markdown("### 📈 Daily Revenue Trend")
        if trend:
            df_t = pd.DataFrame(trend)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_t["day"], y=df_t["revenue"],
                fill="tozeroy", fillcolor="rgba(255,107,53,0.15)",
                line=dict(color="#FF6B35", width=2),
                name="Revenue"
            ))
            fig.add_trace(go.Bar(
                x=df_t["day"], y=df_t["order_count"],
                name="Orders", yaxis="y2",
                marker_color="rgba(247,147,30,0.4)"
            ))
            fig.update_layout(
                yaxis2=dict(overlaying="y", side="right", showgrid=False, color="#F7931E"),
                height=300
            )
            st.plotly_chart(make_chart(fig), use_container_width=True)

    with col2:
        st.markdown("### ⏰ Peak Hours")
        if peak:
            df_p = pd.DataFrame(peak)
            fig  = px.bar(df_p, x="hour", y="order_count",
                          color="order_count", color_continuous_scale=["#1a1a2e","#FF6B35"])
            fig.update_layout(height=300, showlegend=False,
                              coloraxis_showscale=False)
            st.plotly_chart(make_chart(fig), use_container_width=True)

    # Category + Order Type + Payment
    col3, col4, col5 = st.columns(3)

    with col3:
        st.markdown("### 🍕 Category Revenue")
        if cat:
            df_c = pd.DataFrame(cat)
            fig  = px.pie(df_c, names="category", values="revenue",
                          hole=0.5, color_discrete_sequence=CHART_COLORS)
            fig.update_traces(textfont_color="white")
            fig.update_layout(height=280)
            st.plotly_chart(make_chart(fig), use_container_width=True)

    with col4:
        st.markdown("### 🚗 Order Type")
        if ot:
            df_ot = pd.DataFrame(ot)
            fig   = px.pie(df_ot, names="order_type", values="order_count",
                           hole=0.5, color_discrete_sequence=["#FF6B35","#F7931E","#FFD700"])
            fig.update_traces(textfont_color="white")
            fig.update_layout(height=280)
            st.plotly_chart(make_chart(fig), use_container_width=True)

    with col5:
        st.markdown("### 💳 Payment Mode")
        if pay:
            df_pay = pd.DataFrame(pay)
            fig    = px.pie(df_pay, names="payment_mode", values="revenue",
                            hole=0.5, color_discrete_sequence=["#2ECC71","#3498DB","#9B59B6","#E74C3C"])
            fig.update_traces(textfont_color="white")
            fig.update_layout(height=280)
            st.plotly_chart(make_chart(fig), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MENU ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    best   = fetch("/bestsellers",      {**params,"top_n":top_n})
    menu_p = fetch("/menu-performance", params)
    cat2   = fetch("/category-split",   params)

    col1, col2 = st.columns([3,2])

    with col1:
        st.markdown(f"### 🏆 Top {top_n} Best-Selling Items")
        if best:
            df_b = pd.DataFrame(best)
            fig  = px.bar(df_b.sort_values("total_qty"),
                          x="total_qty", y="name", orientation="h",
                          color="category", color_discrete_sequence=CHART_COLORS,
                          labels={"total_qty":"Qty Sold","name":"Item"})
            fig.update_layout(height=400)
            st.plotly_chart(make_chart(fig), use_container_width=True)

    with col2:
        st.markdown("### 💹 Revenue by Category")
        if cat2:
            df_c2 = pd.DataFrame(cat2)
            fig   = px.bar(df_c2, x="category", y=["revenue","profit"],
                           barmode="group", color_discrete_sequence=["#FF6B35","#2ECC71"],
                           labels={"value":"Amount (₹)","variable":"Type"})
            fig.update_layout(height=400)
            st.plotly_chart(make_chart(fig), use_container_width=True)

    st.markdown("### 📊 Full Menu Performance")
    if menu_p:
        df_mp = pd.DataFrame(menu_p)
        df_mp["margin_pct"] = df_mp["margin_pct"].apply(lambda x: f"{x}%")
        df_mp["revenue"]    = df_mp["revenue"].apply(lambda x: f"₹{x:,.0f}")
        df_mp["profit"]     = df_mp["profit"].apply(lambda x: f"₹{x:,.0f}")
        df_mp["price"]      = df_mp["price"].apply(lambda x: f"₹{x:,.0f}")
        st.dataframe(
            df_mp[["name","category","price","total_sold","revenue","profit","margin_pct"]].rename(columns={
                "name":"Item","category":"Category","price":"Price",
                "total_sold":"Sold","revenue":"Revenue","profit":"Profit","margin_pct":"Margin"
            }),
            use_container_width=True, height=400
        )

    # Profit scatter
    if menu_p:
        df_mp2 = pd.DataFrame(menu_p)
        st.markdown("### 💡 Price vs Profit Analysis")
        fig = px.scatter(df_mp2, x="price", y="profit", size="total_sold",
                         color="category", hover_name="name",
                         color_discrete_sequence=CHART_COLORS,
                         labels={"price":"Price (₹)","profit":"Profit (₹)","total_sold":"Units Sold"})
        fig.update_layout(height=350)
        st.plotly_chart(make_chart(fig), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CUSTOMERS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    repeat  = fetch("/repeat-customers", {**params,"top_n":top_n})
    top_c   = fetch("/top-customers",    {**params,"top_n":top_n})
    forecast= fetch("/revenue-forecast", {"days":7})

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"### 🔁 Top {top_n} Repeat Customers")
        if repeat:
            df_r = pd.DataFrame(repeat)
            fig  = px.bar(df_r, x="name", y="visit_count",
                          color="total_spent", color_continuous_scale=["#1a1a2e","#FF6B35"],
                          labels={"visit_count":"Visits","name":"Customer","total_spent":"Total Spent"})
            fig.update_layout(height=320, coloraxis_showscale=False)
            st.plotly_chart(make_chart(fig), use_container_width=True)

    with col2:
        st.markdown(f"### 💎 Top {top_n} Spenders")
        if top_c:
            df_tc = pd.DataFrame(top_c)
            fig   = px.bar(df_tc, x="name", y="total_spent",
                           color="order_count", color_continuous_scale=["#16213e","#2ECC71"],
                           labels={"total_spent":"Total Spent (₹)","name":"Customer"})
            fig.update_layout(height=320, coloraxis_showscale=False)
            st.plotly_chart(make_chart(fig), use_container_width=True)

    # Revenue Forecast
    st.markdown("### 🔮 7-Day Revenue Forecast")
    if forecast:
        trend2 = fetch("/revenue-trend", params)
        if trend2:
            df_hist = pd.DataFrame(trend2)
            df_hist["type"] = "actual"
            df_fore = pd.DataFrame(forecast)
            df_fore = df_fore.rename(columns={"forecast":"revenue"})

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_hist["day"].tail(30), y=df_hist["revenue"].tail(30),
                name="Actual", line=dict(color="#FF6B35", width=2)
            ))
            fig.add_trace(go.Scatter(
                x=df_fore["day"], y=df_fore["revenue"],
                name="Forecast", line=dict(color="#2ECC71", width=2, dash="dash"),
                fill="tozeroy", fillcolor="rgba(46,204,113,0.1)"
            ))
            fig.update_layout(height=300)
            st.plotly_chart(make_chart(fig), use_container_width=True)
            st.caption("📌 Forecast based on 7-day moving average of historical data")

    # Repeat customers table
    if repeat:
        st.markdown("### 📋 Repeat Customer Details")
        df_r2 = pd.DataFrame(repeat)
        df_r2["total_spent"] = df_r2["total_spent"].apply(lambda x: f"₹{x:,.0f}")
        df_r2["avg_spent"]   = df_r2["avg_spent"].apply(lambda x: f"₹{x:,.0f}")
        st.dataframe(df_r2.rename(columns={
            "name":"Customer","phone":"Phone","loyalty_pts":"Loyalty Pts",
            "visit_count":"Visits","total_spent":"Total Spent","avg_spent":"Avg/Visit"
        }), use_container_width=True, height=300)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — TIME ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    weekly = fetch("/weekly-trend",      params)
    daily  = fetch("/daily-comparison",  params)
    peak2  = fetch("/peak-hours",        params)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📅 Weekly Revenue Trend")
        if weekly:
            df_w = pd.DataFrame(weekly)
            fig  = px.bar(df_w, x="week", y="revenue",
                          color="revenue", color_continuous_scale=["#1a1a2e","#FF6B35"],
                          labels={"week":"Week","revenue":"Revenue (₹)"})
            fig.update_layout(height=320, coloraxis_showscale=False)
            st.plotly_chart(make_chart(fig), use_container_width=True)

    with col2:
        st.markdown("### 📆 Day of Week Analysis")
        if daily:
            df_d = pd.DataFrame(daily)
            fig  = px.bar(df_d, x="day_name", y="avg_revenue",
                          color="order_count", color_continuous_scale=["#16213e","#F7931E"],
                          labels={"day_name":"Day","avg_revenue":"Avg Revenue (₹)","order_count":"Orders"})
            fig.update_layout(height=320, coloraxis_showscale=False)
            st.plotly_chart(make_chart(fig), use_container_width=True)

    # Peak hours heatmap style
    st.markdown("### 🌡️ Revenue by Hour")
    if peak2:
        df_ph = pd.DataFrame(peak2)
        fig   = go.Figure()
        fig.add_trace(go.Bar(
            x=df_ph["hour"], y=df_ph["revenue"],
            marker=dict(color=df_ph["revenue"], colorscale=[[0,"#1a1a2e"],[1,"#FF6B35"]]),
            text=df_ph["order_count"].apply(lambda x: f"{x} orders"),
            textposition="outside"
        ))
        fig.update_layout(
            height=300,
            xaxis=dict(tickmode="linear", tick0=0, dtick=1,
                       ticktext=[f"{h}:00" for h in range(24)],
                       tickvals=list(range(24)))
        )
        st.plotly_chart(make_chart(fig), use_container_width=True)

    # Insight cards
    if peak2:
        df_ph2 = pd.DataFrame(peak2)
        peak_hour = df_ph2.loc[df_ph2["order_count"].idxmax(), "hour"]
        peak_rev  = df_ph2.loc[df_ph2["revenue"].idxmax(), "hour"]
        col_a, col_b, col_c = st.columns(3)
        col_a.success(f"🕐 **Busiest Hour:** {peak_hour}:00")
        col_b.info(f"💰 **Peak Revenue Hour:** {peak_rev}:00")
        col_c.warning(f"📊 **Total Hours Active:** {len(df_ph2)}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — ORDERS & EXPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### 📋 Order Management")

    col1, col2, col3 = st.columns(3)
    status_filter = col1.selectbox("Status", ["All","Completed","Cancelled","Refunded"])
    min_amt       = col2.number_input("Min Amount (₹)", value=0, step=100)
    max_amt       = col3.number_input("Max Amount (₹)", value=10000, step=100)

    ord_params = {**order_params}
    if status_filter != "All": ord_params["status"]     = status_filter
    if min_amt > 0:            ord_params["min_amount"] = min_amt
    if max_amt < 10000:        ord_params["max_amount"] = max_amt
    ord_params["page_size"] = 100

    orders_data = fetch("/orders", ord_params)

    if orders_data and orders_data["orders"]:
        df_ord = pd.DataFrame(orders_data["orders"])
        df_ord["order_date"]   = pd.to_datetime(df_ord["order_date"]).dt.strftime("%d %b %Y  %H:%M")
        df_ord["total_amount"] = df_ord["total_amount"].apply(lambda x: f"₹{x:,.0f}")

        st.markdown(f"**Showing {len(df_ord)} of {orders_data['total']} orders**")
        st.dataframe(
            df_ord.rename(columns={
                "order_id":"ID","customer":"Customer","order_date":"Date",
                "order_type":"Type","payment_mode":"Payment",
                "total_amount":"Amount","status":"Status"
            }),
            use_container_width=True, height=400
        )

        # Export section
        st.markdown("### 📥 Export Data")
        col_a, col_b, col_c = st.columns(3)

        # CSV Export
        csv_data = pd.DataFrame(orders_data["orders"]).to_csv(index=False).encode()
        col_a.download_button(
            "⬇️ Export Orders CSV",
            data=csv_data,
            file_name=f"orders_{start_date}_{end_date}.csv",
            mime="text/csv", use_container_width=True
        )

        # Summary CSV
        if kpi := fetch("/kpis", params):
            summary_csv = pd.DataFrame([kpi]).to_csv(index=False).encode()
            col_b.download_button(
                "⬇️ Export KPI Summary",
                data=summary_csv,
                file_name=f"kpi_summary_{start_date}_{end_date}.csv",
                mime="text/csv", use_container_width=True
            )

        # Bestsellers CSV
        if best := fetch("/bestsellers", {**params,"top_n":top_n}):
            best_csv = pd.DataFrame(best).to_csv(index=False).encode()
            col_c.download_button(
                "⬇️ Export Bestsellers",
                data=best_csv,
                file_name=f"bestsellers_{start_date}_{end_date}.csv",
                mime="text/csv", use_container_width=True
            )

    # Summary Report
    st.markdown("---")
    st.markdown("### 📊 Quick Summary Report")
    report = fetch("/summary-report", params)
    if report:
        with st.expander("📄 View Full Report", expanded=False):
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.markdown("**KPIs**")
                kpi_r = report["kpis"]
                st.write(f"- Total Revenue: ₹{kpi_r['total_revenue']:,.0f}")
                st.write(f"- Total Orders: {kpi_r['total_orders']:,}")
                st.write(f"- Avg Order Value: ₹{kpi_r['avg_order_value']:,.0f}")
                st.write(f"- Unique Customers: {kpi_r['unique_customers']:,}")
                st.markdown("**Top 5 Bestsellers**")
                for i,b in enumerate(report["bestsellers"],1):
                    st.write(f"{i}. {b['name']} — {b['total_qty']} sold")
            with col_r2:
                st.markdown("**Category Revenue**")
                for c in report["categories"]:
                    st.write(f"- {c['category']}: ₹{c['revenue']:,.0f}")
                st.markdown("**Payment Modes**")
                for p in report["payments"]:
                    st.write(f"- {p['payment_mode']}: ₹{p['revenue']:,.0f}")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#a0aec0; font-size:0.85rem; padding:10px'>
    🍽️ Restaurant Sales Dashboard · PRJ-053 · Ya Khaiyum.A PDKV<br>
    Built with FastAPI + Streamlit + PostgreSQL + Pandas + Plotly
</div>
""", unsafe_allow_html=True)
