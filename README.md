# ✈️ Flight Analytics Dashboard

An interactive aviation analytics platform that collects real-time flight data and provides comprehensive insights through an intuitive web dashboard.

## 📋 Project Overview

Flight Analytics combines **AeroDataBox API** for flight data collection, **SQLite** for local data storage, and **Streamlit** for an interactive analytics dashboard. The project enables users to explore flight patterns, analyze delays, and monitor airport activity across multiple dimensions.

## 🎯 Features

### Dashboard Tabs

1. **📊 Dashboard** - Network overview with visualization of flights by status and top 10 routes
2. **🔎 Flight Search** - Search and filter flights by number, airline, status, origin, destination, and date range
3. **🏢 Airport Details** - View airport information and linked flights
4. **⏱️ Delay Analysis** - Analyze delay statistics, delay percentages, and airport performance
5. **🏆 Route Leaderboards** - Discover busiest routes and most delayed airports

### Key Capabilities

- **Interactive Filtering**: Filter flights by status, origin/destination airports, airline, date range, and flight number
- **Real-time KPIs**: Display total airports, matching flights, and average delays
- **Delay Analytics**: Weighted average delays, cancellation rates, and performance metrics by airport
- **Route Analysis**: Identify busiest routes and airport performance patterns
- **Data Export**: View flight data in interactive tables with up to 1,000 records per view

## 🗂️ Project Structure

```
flight_analytics/
├── Air_Tracker_Flight_Analytics.ipynb  # Data collection and database setup
├── app.py                              # Streamlit dashboard application
├── connect_db.py                       # Database utility functions
├── requirements.txt                    # Python dependencies
└── README.md                           # This file
```

## 🔧 Components

### Air_Tracker_Flight_Analytics.ipynb
Jupyter notebook that handles:
- Authentication with AeroDataBox API
- Flight data collection and aggregation
- SQLite database creation and schema setup
- Data insertion and initial data load
- Creates `aviation_local.db` database

### app.py
Streamlit web application featuring:
- Page configuration and styling
- Database connection management with SQLite
- Multi-tab dashboard interface
- Dynamic filtering system
- KPI metrics calculation
- Interactive Plotly visualizations
- Data aggregation and analysis queries

### connect_db.py
Utility module providing:
- `connect_db()` - Establish SQLite connection
- `list_tables()` - List all database tables
- `show_table_sample()` - Display sample rows from tables
- Command-line interface for database inspection

## 📦 Dependencies

```
pandas           # Data manipulation and analysis
numpy            # Numerical computing
requests         # HTTP library for API calls
streamlit        # Web application framework
altair           # Declarative visualization
plotly           # Interactive visualizations
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- SQLite3

### Installation

1. **Clone the repository or navigate to project directory**
   ```bash
   cd flight_analytics
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

1. **Prepare the database** (First time only)
   - Open `Air_Tracker_Flight_Analytics.ipynb` in Jupyter
   - Run the data collection and SQL creation cells to generate `aviation_local.db`

2. **Launch the dashboard**
   ```bash
   streamlit run app.py
   ```
   The dashboard will open at `http://localhost:8501`

3. **Inspect the database**
   ```bash
   python connect_db.py [path_to_database]
   # Example: python connect_db.py aviation_local.db
   ```

## 📊 Database Schema

The SQLite database includes the following main tables:
- **flights** - Flight records with scheduling and actual times, status, and aircraft info
- **airport** - Airport details including codes, location, and timezone information
- **airport_delays** - Pre-aggregated delay statistics by airport

## 🎨 Dashboard Interface

The Streamlit dashboard includes:
- **Sidebar Filters**: Flight number/airline search, status, airports, airline, and date range selection
- **KPI Cards**: Summary metrics for quick insights
- **Visualizations**: Bar charts and data tables powered by Plotly
- **Responsive Layout**: Wide layout with multi-column designs for optimal viewing

## 🔍 Key Queries

- Flight filtering with multiple dimensions
- Delay percentage calculations
- Route volume analysis
- Airport performance metrics
- Time-based aggregations

## 💡 Usage Tips

- **Date Range Selection**: Use the sidebar date picker to focus on specific periods
- **Multi-select Filters**: Hold Ctrl/Cmd to select multiple values in dropdown filters
- **Flight Search**: Enter partial flight numbers or airline codes (e.g., "AI101" or "AI")
- **Data Limits**: Flight search tab shows maximum 1,000 records per query

## 📝 Notes

- The database path defaults to `aviation_local.db` in the project directory
- All queries are executed against the local SQLite database
- Timezone information is preserved in the database for accurate time representation
- ISO 8601 datetime format is used throughout (YYYY-MM-DDTHH:MM:SSZ)

## 🤝 Contributing

To extend functionality:
1. Modify `app.py` to add new tabs or visualizations
2. Update notebook cells to include additional data sources
3. Extend `connect_db.py` utility functions for new database operations
