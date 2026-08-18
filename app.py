import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px


# ============================================================
# CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Aviation Analytics Dashboard",
    page_icon="✈️",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parent / "aviation_local.db"


# ============================================================
# DATABASE HELPERS
# ============================================================
def get_connection():
    """Create a fresh SQLite connection for each query."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. Run the data collection + SQL cells in the notebook first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_db(sql, params=None):
    """Execute a read-only SQL query and return a DataFrame."""
    params = params or []
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def scalar_query(sql, params=None):
    """Execute a SQL query that returns one scalar value."""
    params = params or []
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
    return row[0] if row else 0


# ============================================================
# HEADER
# ============================================================
st.title("✈️ Aviation Analytics Dashboard")
st.caption("Interactive flight analysis powered by Streamlit + SQLite SQL queries")

if not DB_PATH.exists():
    st.error(
        "aviation.db was not found. Run the SQL creation and data insertion cells in the Colab notebook before launching this app."
    )
    st.stop()


# ============================================================
# SIDEBAR FILTERS
# ============================================================
st.sidebar.header("🔎 Filters")

def safe_distinct(col):
    try:
        return query_db(f"SELECT DISTINCT {col} FROM flights WHERE {col} IS NOT NULL AND TRIM({col}) <> '' ORDER BY {col}")[col].tolist()
    except Exception:
        return []

status_options = safe_distinct('status')
origin_options = safe_distinct('origin_iata')
destination_options = safe_distinct('destination_iata')
airline_options = safe_distinct('airline_code')

date_bounds = query_db("""
    SELECT
        MIN(date(substr(COALESCE(scheduled_departure, scheduled_arrival), 1, 10))) AS min_date,
        MAX(date(substr(COALESCE(scheduled_departure, scheduled_arrival), 1, 10))) AS max_date
    FROM flights
""")

search_text = st.sidebar.text_input("Flight number / airline", placeholder="e.g. AI101 or AI")

selected_status = st.sidebar.multiselect("Flight status", options=status_options)
selected_origin = st.sidebar.multiselect("Origin airport", options=origin_options)
selected_destination = st.sidebar.multiselect("Destination airport", options=destination_options)
selected_airlines = st.sidebar.multiselect("Airline", options=airline_options)

import datetime as dt

if not date_bounds.empty:
    # Extract scalar values from the single-row DataFrame returned by the query
    min_val = date_bounds["min_date"].iloc[0]
    max_val = date_bounds["max_date"].iloc[0]
    # Convert to python date, falling back to today if null
    min_date = pd.to_datetime(min_val).date() if pd.notnull(min_val) else dt.date.today()
    max_date = pd.to_datetime(max_val).date() if pd.notnull(max_val) else dt.date.today()
else:
    min_date = max_date = dt.date.today()

selected_dates = st.sidebar.date_input("Scheduled date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates


# ============================================================
# REUSABLE SQL FILTER BUILDER
# ============================================================
def build_flight_filters():
    clauses = ["1=1"]
    params = []

    if search_text.strip():
        clauses.append("(LOWER(f.flight_number) LIKE LOWER(?) OR LOWER(f.airline_code) LIKE LOWER(?))")
        pattern = f"%{search_text.strip()}%"
        params.extend([pattern, pattern])

    if selected_status:
        placeholders = ",".join(["?"] * len(selected_status))
        clauses.append(f"f.status IN ({placeholders})")
        params.extend(selected_status)

    if selected_origin:
        placeholders = ",".join(["?"] * len(selected_origin))
        clauses.append(f"f.origin_iata IN ({placeholders})")
        params.extend(selected_origin)

    if selected_destination:
        placeholders = ",".join(["?"] * len(selected_destination))
        clauses.append(f"f.destination_iata IN ({placeholders})")
        params.extend(selected_destination)

    if selected_airlines:
        placeholders = ",".join(["?"] * len(selected_airlines))
        clauses.append(f"f.airline_code IN ({placeholders})")
        params.extend(selected_airlines)

    # Use substr(...,1,10) to strip timezone 'Z' and keep YYYY-MM-DD so SQLite's date() works
    clauses.append("date(substr(COALESCE(f.scheduled_departure, f.scheduled_arrival), 1, 10)) BETWEEN ? AND ?")
    params.extend([str(start_date), str(end_date)])

    return " AND ".join(clauses), params


# ============================================================
# KPI CARDS
# ============================================================
kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

total_airports = scalar_query("SELECT COUNT(*) FROM airport")

filter_sql, filter_params = build_flight_filters()

total_flights = scalar_query(f"SELECT COUNT(*) FROM flights f WHERE {filter_sql}", filter_params)

avg_delay = scalar_query(
    f"""
    SELECT COALESCE(ROUND(AVG(CASE WHEN actual_time IS NOT NULL AND scheduled_time IS NOT NULL THEN MAX((julianday(actual_time) - julianday(scheduled_time)) * 1440, 0) END), 2), 0)
    FROM (SELECT CASE WHEN f.scheduled_departure IS NOT NULL AND TRIM(f.scheduled_departure) <> '' THEN f.scheduled_departure ELSE f.scheduled_arrival END AS scheduled_time, CASE WHEN f.actual_departure IS NOT NULL AND TRIM(f.actual_departure) <> '' THEN f.actual_departure ELSE f.actual_arrival END AS actual_time, f.* FROM flights f) f
    WHERE {filter_sql}
    """,
    filter_params,
)

kpi_col1.metric("🏢 Total Airports", f"{total_airports:,}")
kpi_col2.metric("✈️ Flights Matching Filters", f"{int(total_flights):,}")
kpi_col3.metric("⏱️ Average Delay (min)", f"{float(avg_delay):.2f}")


# ============================================================
# MAIN TABS
# ============================================================
tab_dashboard, tab_flights, tab_airport, tab_delay, tab_routes = st.tabs([
    "📊 Dashboard",
    "🔎 Flight Search",
    "🏢 Airport Details",
    "⏱️ Delay Analysis",
    "🏆 Route Leaderboards",
])


# Dashboard tab
with tab_dashboard:
    st.subheader("Network Overview")

    status_df = query_db(f"SELECT f.status, COUNT(*) AS total_flights FROM flights f WHERE {filter_sql} GROUP BY f.status ORDER BY total_flights DESC", filter_params)

    col1, col2 = st.columns(2)

    with col1:
        if not status_df.empty:
            fig = px.bar(status_df, x="status", y="total_flights", title="Flights by Status", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        route_df = query_db(f"SELECT f.origin_iata || ' → ' || f.destination_iata AS route, COUNT(*) AS total_flights FROM flights f WHERE {filter_sql} GROUP BY f.origin_iata, f.destination_iata ORDER BY total_flights DESC LIMIT 10", filter_params)
        if not route_df.empty:
            fig = px.bar(route_df.sort_values("total_flights"), x="total_flights", y="route", orientation="h", title="Top 10 Routes", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)


with tab_flights:
    st.subheader("Search and Filter Flights")
    flights_df = query_db(f"SELECT f.flight_number, f.airline_code, f.aircraft_registration, f.origin_iata, f.destination_iata, f.scheduled_departure, f.actual_departure, f.scheduled_arrival, f.actual_arrival, f.status FROM flights f WHERE {filter_sql} ORDER BY COALESCE(f.scheduled_departure, f.scheduled_arrival) LIMIT 1000", filter_params)
    st.write(f"Showing **{len(flights_df):,}** matching flights (maximum 1,000 displayed).")
    st.dataframe(flights_df, use_container_width=True, hide_index=True)


with tab_airport:
    st.subheader("Airport Details Viewer")
    airport_choices = query_db("SELECT iata_code, name, city, country, timezone FROM airport WHERE iata_code IS NOT NULL ORDER BY iata_code")
    if airport_choices.empty:
        st.warning("No airport records found.")
    else:
        selected_airport = st.selectbox("Select an airport", airport_choices["iata_code"].tolist())
        airport = query_db("SELECT iata_code, icao_code, name, city, country, continent, latitude, longitude, timezone FROM airport WHERE iata_code = ?", [selected_airport])
        if not airport.empty:
            st.dataframe(airport, use_container_width=True, hide_index=True)
        linked_flights = query_db("SELECT flight_number, airline_code, origin_iata, destination_iata, scheduled_departure, scheduled_arrival, status FROM flights WHERE origin_iata = ? OR destination_iata = ? ORDER BY COALESCE(scheduled_departure, scheduled_arrival) LIMIT 500", [selected_airport, selected_airport])
        st.write(f"### Linked Flights ({len(linked_flights):,})")
        st.dataframe(linked_flights, use_container_width=True, hide_index=True)


with tab_delay:
    st.subheader("Airport Delay Analysis")
    delay_df = query_db("""
        SELECT airport_iata, SUM(total_flights) AS total_flights, SUM(delayed_flights) AS delayed_flights, ROUND(100.0 * SUM(delayed_flights) / NULLIF(SUM(total_flights), 0), 2) AS delay_percentage, ROUND(SUM(avg_delay_min * delayed_flights) / NULLIF(SUM(delayed_flights), 0), 2) AS weighted_avg_delay_min, SUM(canceled_flights) AS canceled_flights FROM airport_delays GROUP BY airport_iata ORDER BY delay_percentage DESC
    """)
    if not delay_df.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(delay_df, x="airport_iata", y="delay_percentage", title="Delay Percentage by Airport", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            chart_df = delay_df.sort_values("weighted_avg_delay_min", ascending=False).head(10)
            fig = px.bar(chart_df.sort_values("weighted_avg_delay_min"), x="weighted_avg_delay_min", y="airport_iata", orientation="h", title="Average Delay by Airport", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(delay_df, use_container_width=True, hide_index=True)
    else:
        st.info("No delay records available to display.")


with tab_routes:
    st.subheader("Route Leaderboards")
    busiest_routes = query_db(f"SELECT f.origin_iata, f.destination_iata, f.origin_iata || ' → ' || f.destination_iata AS route, COUNT(*) AS total_flights FROM flights f WHERE {filter_sql} GROUP BY f.origin_iata, f.destination_iata ORDER BY total_flights DESC LIMIT 20", filter_params)
    most_delayed = query_db("""
        SELECT airport_iata, SUM(total_flights) AS total_flights, SUM(delayed_flights) AS delayed_flights, ROUND(100.0 * SUM(delayed_flights) / NULLIF(SUM(total_flights), 0), 2) AS delay_percentage, ROUND(SUM(avg_delay_min * delayed_flights) / NULLIF(SUM(delayed_flights), 0), 2) AS avg_delay_min FROM airport_delays GROUP BY airport_iata HAVING SUM(total_flights) > 0 ORDER BY avg_delay_min DESC LIMIT 20
    """)
    left, right = st.columns(2)
    with left:
        st.markdown("### 🛫 Busiest Routes")
        st.dataframe(busiest_routes, use_container_width=True, hide_index=True)
    with right:
        st.markdown("### ⚠️ Most Delayed Airports")
        st.dataframe(most_delayed, use_container_width=True, hide_index=True)


st.divider()
st.caption("Data source: AeroDataBox API → SQLite database → Streamlit SQL queries. Dashboard queries are executed against the local SQL database on each interaction.")
