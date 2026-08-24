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
        MIN(date(substr(COALESCE(NULLIF(scheduled_departure, ''), scheduled_arrival), 1, 10))) AS min_date,
        MAX(date(substr(COALESCE(NULLIF(scheduled_departure, ''), scheduled_arrival), 1, 10))) AS max_date
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
    # NULLIF treats empty strings as NULL so COALESCE picks the next non-empty value
    clauses.append("date(substr(COALESCE(NULLIF(f.scheduled_departure, ''), f.scheduled_arrival), 1, 10)) BETWEEN ? AND ?")
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
tab_dashboard, tab_flights, tab_airport, tab_delay, tab_sql_queries, tab_routes = st.tabs([
    "📊 Dashboard",
    "🔎 Flight Search",
    "🏢 Airport Details",
    "⏱️ Delay Analysis",
    "🧮 SQL Queries",
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
    
    flights_df = query_db(f"SELECT f.flight_number, f.airline_code, f.origin_iata, f.destination_iata, f.scheduled_departure, f.actual_departure, CASE WHEN f.scheduled_arrival = '' THEN NULL ELSE f.scheduled_arrival END AS scheduled_arrival, CASE WHEN f.actual_arrival = '' THEN NULL ELSE f.actual_arrival END AS actual_arrival, f.aircraft_registration, f.status FROM flights f WHERE {filter_sql} ORDER BY COALESCE(f.scheduled_departure, f.scheduled_arrival) LIMIT 2000", filter_params)
    st.write(f"Showing **{len(flights_df):,}** matching flights (maximum 2,000 displayed).")
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


with tab_sql_queries:
    st.subheader("SQL Queries")

    sql_queries = {
        "Query 1": """
SELECT
    a.model,
    COUNT(f.flight_id) AS total_flights
FROM aircraft a
LEFT JOIN flights f ON a.registration = f.aircraft_registration
GROUP BY a.model
ORDER BY total_flights DESC;
""",
        "Query 2": """
SELECT
    a.registration,
    a.model,
    COUNT(f.flight_id) AS flight_count
FROM aircraft a
JOIN flights f ON a.registration = f.aircraft_registration
GROUP BY a.registration, a.model
HAVING COUNT(f.flight_id) > 5
ORDER BY flight_count DESC;
""",
        "Query 3": """
SELECT
    ap.name AS airport_name,
    COUNT(f.flight_id) AS outbound_flights
FROM airport ap
JOIN flights f ON ap.iata_code = f.origin_iata
GROUP BY ap.airport_id, ap.name
HAVING COUNT(f.flight_id) > 5
ORDER BY outbound_flights DESC;
""",
        "Query 4": """
SELECT
    ap.name AS airport_name,
    ap.city,
    COUNT(f.flight_id) AS arriving_flights
FROM airport ap
JOIN flights f ON ap.iata_code = f.destination_iata
GROUP BY ap.airport_id, ap.name, ap.city
ORDER BY arriving_flights DESC
LIMIT 3;
""",
        "Query 5": """
SELECT
    f.flight_number,
    f.origin_iata,
    f.destination_iata,
    orig.country AS origin_country,
    dest.country AS dest_country,
    CASE
        WHEN orig.country = dest.country THEN 'Domestic'
        ELSE 'International'
    END AS flight_type
FROM flights f
JOIN airport orig ON f.origin_iata = orig.iata_code
JOIN airport dest ON f.destination_iata = dest.iata_code;
""",
        "Query 6": """
SELECT
    f.flight_number,
    f.aircraft_registration,
    orig.name AS departure_airport,
    COALESCE(f.actual_arrival, f.scheduled_arrival) AS arrival_time
FROM flights f
JOIN airport orig ON f.origin_iata = orig.iata_code
WHERE f.destination_iata = 'DEL'
ORDER BY arrival_time DESC
LIMIT 5;
""",
        "Query 7": """
SELECT
    ap.iata_code,
    ap.name,
    ap.city,
    ap.country
FROM airport ap
LEFT JOIN flights f ON ap.iata_code = f.destination_iata
WHERE f.flight_id IS NULL;
""",
        "Query 8": """
SELECT
    f.airline_code,
    COUNT(f.flight_id) AS total_flights,
    SUM(CASE WHEN LOWER(f.status) LIKE '%on%time%' OR LOWER(f.status) = 'landed' THEN 1 ELSE 0 END) AS on_time_count,
    SUM(CASE WHEN LOWER(f.status) LIKE '%delay%' THEN 1 ELSE 0 END) AS delayed_count,
    SUM(CASE WHEN LOWER(f.status) LIKE '%cancel%' THEN 1 ELSE 0 END) AS cancelled_count
FROM flights f
GROUP BY f.airline_code;
""",
        "Query 9": """
SELECT
    f.flight_number,
    f.scheduled_departure,
    f.aircraft_registration,
    orig.name AS origin_airport,
    dest.name AS destination_airport,
    f.status
FROM flights f
LEFT JOIN airport orig ON f.origin_iata = orig.iata_code
LEFT JOIN airport dest ON f.destination_iata = dest.iata_code
WHERE LOWER(f.status) LIKE '%cancel%'
ORDER BY f.scheduled_departure DESC;
""",
        "Query 10": """
SELECT
    orig.city AS origin_city,
    dest.city AS destination_city,
    COUNT(DISTINCT a.model) AS distinct_models_count
FROM flights f
JOIN airport orig ON f.origin_iata = orig.iata_code
JOIN airport dest ON f.destination_iata = dest.iata_code
JOIN aircraft a ON f.aircraft_registration = a.registration
GROUP BY orig.city, dest.city
HAVING COUNT(DISTINCT a.model) > 2
ORDER BY distinct_models_count DESC;
""",
        "Query 11": """
SELECT
    ap.iata_code,
    ap.name AS destination_airport,
    COUNT(f.flight_id) AS total_arrivals,
    SUM(CASE WHEN LOWER(f.status) LIKE '%delay%' THEN 1 ELSE 0 END) AS delayed_arrivals,
    ROUND(
        (CAST(SUM(CASE WHEN LOWER(f.status) LIKE '%delay%' THEN 1 ELSE 0 END) AS REAL) / COUNT(f.flight_id)) * 100,
        2
    ) AS delay_percentage
FROM airport ap
JOIN flights f ON ap.iata_code = f.destination_iata
GROUP BY ap.iata_code, ap.name
ORDER BY delay_percentage DESC;
""",
    }

    query_questions = {
        "Query 1": "Show the total number of flights for each aircraft model, listing the model and its count.",
        "Query 2": "List all aircraft (registration, model) that have been assigned to more than 5 flights.",
        "Query 3": "For each airport, display its name and the number of outbound flights, but only for airports with more than 5 flights.",
        "Query 4": "Find the top 3 destination airports (name, city) by number of arriving flights, sorted by count descending.",
        "Query 5": "Show for each flight: number, origin, destination, and a label 'Domestic' or 'International' using CASE WHEN on country match.",
        "Query 6": "Show the 5 most recent arrivals at 'DEL' airport including flight number, aircraft, departure airport name, and arrival time, ordered by latest arrival.",
        "Query 7": "Find all airports with no arriving flights (never used as a destination in flights table).",
        "Query 8": "For each airline, count the number of flights by status (e.g., 'On Time', 'Delayed', 'Cancelled) using CASE WHEN.",
        "Query 9": "Show all cancelled flights, with aircraft and both airports, ordered by departure time descending.",
        "Query 10": "List all city pairs (origin-destination) that have more than 2 different aircraft models operating flights between them.",
        "Query 11": "For each destination airport, compute the % of delayed flights (status='Delayed') among all arrivals, sorted by highest percentage.",
    }

    selected_query_name = st.selectbox("Select a query to run", list(sql_queries))
    selected_query = sql_queries[selected_query_name]
    st.markdown(f"**Question:** {query_questions[selected_query_name]}")
    st.code(selected_query.strip(), language="sql")
    query_result = query_db(selected_query)
    st.write(f"Returned **{len(query_result):,}** rows.")
    st.dataframe(query_result, use_container_width=True, hide_index=True)


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
