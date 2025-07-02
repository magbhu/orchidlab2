import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import os

# Function to load data
@st.cache_data
def load_data(file_path):
    """
    Loads CSV data from the given file path.
    Uses st.cache_data to cache the data for performance.
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        st.error(f"Error: File not found at {file_path}")
        return pd.DataFrame()

# Function to load JSON mappings
@st.cache_data
def load_json_mapping(file_path):
    """
    Loads JSON data from the given file path.
    Uses st.cache_data to cache the mapping data.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Error: Mapping file not found at {file_path}")
        return {}

# Load mapping files
# These mappings are used for multilingual support and displaying user-friendly names.
member_mapping = load_json_mapping('member_mapping.json')
sector_mapping = load_json_mapping('sector_mapping.json')
stock_mapping = load_json_mapping('stock_mapping.json')
titles_mapping = load_json_mapping('titles.json')

# Default portfolio file path
# This file will be loaded if no other file is uploaded by the user.
DEFAULT_PORTFOLIO_FILE = 'portfolioinputs.csv'

def get_text(key, lang):
    """
    Retrieves localized text from the titles mapping JSON.
    If the key or language is not found, it defaults to the key itself.
    """
    return titles_mapping.get(key, {}).get(lang, key)

def format_currency(value):
    """
    Formats a numeric value as Indian Rupees with two decimal places and commas.
    """
    return f"₹ {value:,.2f}"

def get_member_name(member_code, lang):
    """
    Retrieves the localized member name from the member_mapping.
    """
    return member_mapping.get(member_code, {}).get(lang, member_code)

def get_sector_name(sector_name_en, lang):
    """
    Retrieves the localized sector name from the sector_mapping.
    It iterates through the mapping to find the English name and then returns the localized version.
    """
    for key, value in sector_mapping.items():
        if value['en'] == sector_name_en:
            return value.get(lang, sector_name_en)
    return sector_name_en

def get_stock_name(isin_code, lang):
    """
    Retrieves the localized stock name from the stock_mapping using ISIN code.
    """
    return stock_mapping.get(isin_code, {}).get(lang, isin_code)

# Set Streamlit page configuration
st.set_page_config(layout="wide")

# Language selection in the sidebar
lang = st.sidebar.selectbox(
    get_text("Select Language", "en"), # Display "Select Language" in English regardless of current lang
    options=["en", "ta"],
    format_func=lambda x: "English" if x == "en" else "தமிழ்" # Display options as English/Tamil
)

# Main title of the dashboard, localized
st.title(get_text("Portfolio Summary", lang))

# File uploader in the sidebar
uploaded_file = st.sidebar.file_uploader(get_text("Upload Portfolio CSV", lang), type="csv")

df = pd.DataFrame()
if uploaded_file is not None:
    # If a file is uploaded, load data from it
    df = load_data(uploaded_file)
else:
    # Otherwise, try to load the default portfolio file
    if os.path.exists(DEFAULT_PORTFOLIO_FILE):
        df = load_data(DEFAULT_PORTFOLIO_FILE)
    else:
        st.info("Please upload a portfolio CSV file or ensure 'portfolioinputs.csv' is in the directory.")

if not df.empty:
    # Data Cleaning and Type Conversion
    # Convert relevant columns to numeric, coercing errors to NaN
    df['Value At Cost'] = pd.to_numeric(df['Value At Cost'], errors='coerce')
    df['Value At Market Price'] = pd.to_numeric(df['Value At Market Price'], errors='coerce')
    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce')

    # Apply mappings for display purposes
    # Create new columns with localized names
    df['Member Name'] = df['Member Code'].apply(lambda x: get_member_name(x, lang))
    df['Stock Display Name'] = df['ISIN Code'].apply(lambda x: get_stock_name(x, lang))
    df['Sector Display Name'] = df['Sector Name'].apply(lambda x: get_sector_name(x, lang))

    # Calculate Holding Period Return (HPR)
    # Handle potential division by zero by setting HPR to 0 if Value At Cost is 0
    df['HPR'] = ((df['Value At Market Price'] - df['Value At Cost']) / df['Value At Cost'] * 100).round(2)
    df['HPR'] = df['HPR'].fillna(0) # Replace NaN values (e.g., from division by zero) with 0

    # Filters in the sidebar
    # Add 'All' option to each filter for showing all data
    all_portfolios = ['All'] + df['Portfolio'].unique().tolist()
    selected_portfolio = st.sidebar.selectbox(get_text("Select Portfolio", lang), all_portfolios)

    all_members = ['All'] + df['Member Name'].unique().tolist()
    selected_member = st.sidebar.selectbox(get_text("Select Member", lang), all_members)

    all_sectors = ['All'] + df['Sector Display Name'].unique().tolist()
    selected_sector = st.sidebar.selectbox(get_text("Select Sector", lang), all_sectors)

    all_brokers = ['All'] + df['Broker'].unique().tolist()
    selected_broker = st.sidebar.selectbox(get_text("Select Broker", lang), all_brokers)

    # Apply filters to the DataFrame
    filtered_df = df.copy()
    if selected_portfolio != 'All':
        filtered_df = filtered_df[filtered_df['Portfolio'] == selected_portfolio]
    if selected_member != 'All':
        filtered_df = filtered_df[filtered_df['Member Name'] == selected_member]
    if selected_sector != 'All':
        filtered_df = filtered_df[filtered_df['Sector Display Name'] == selected_sector]
    if selected_broker != 'All':
        filtered_df = filtered_df[filtered_df['Broker'] == selected_broker]

    if filtered_df.empty:
        st.warning(get_text("No data available for the selected filters.", lang)) # Localized warning
    else:
        # 3A. Portfolio Total Summary (one liner)
        st.subheader(get_text("Portfolio Summary", lang)) # Localized subheader

        total_investment = filtered_df['Value At Cost'].sum()
        total_current_value = filtered_df['Value At Market Price'].sum()
        # Calculate overall HPR, handling division by zero
        total_hpr = ((total_current_value - total_investment) / total_investment * 100).round(2) if total_investment != 0 else 0

        # Display the summary line with localized labels and currency formatting
        st.write(f"**{get_text('Investment', lang)}:** {format_currency(total_investment)} | "
                 f"**{get_text('Current Value', lang)}:** {format_currency(total_current_value)} | "
                 f"**{get_text('HPR', lang)}:** {total_hpr:.2f}%")

        # 3B. Summary Table (aggregation values alone)
        st.subheader(get_text("Summary Table", lang)) # Localized subheader

        # Options for summarizing the table
        summarize_by_options = {
            get_text("Member", "en"): "Member Name", # Use English key for internal logic, but display localized
            get_text("Sector", "en"): "Sector Display Name",
            get_text("Broker", "en"): "Broker"
        }
        # Radio buttons for "Summarize By" option, with initial sort order by Member
        summarize_by_selection = st.radio(
            get_text("Summarize By", lang),
            options=[get_text("Member", "en"), get_text("Sector", "en"), get_text("Broker", "en")], # Display localized options
            index=0, # Default to Member
            horizontal=True,
            format_func=lambda x: get_text(x, lang) # Localize the displayed options
        )
        group_by_column = summarize_by_options[summarize_by_selection]

        # Group data and aggregate investment and current value
        summary_table = filtered_df.groupby(group_by_column).agg(
            Investment=('Value At Cost', 'sum'),
            Current_Value=('Value At Market Price', 'sum')
        ).reset_index()

        # Calculate HPR for the summary table
        summary_table['HPR'] = ((summary_table['Current_Value'] - summary_table['Investment']) / summary_table['Investment'] * 100).round(2)
        summary_table['HPR'] = summary_table['HPR'].fillna(0) # Handle division by zero

        # Apply formatting to currency and HPR columns
        summary_table['Investment'] = summary_table['Investment'].apply(format_currency)
        summary_table['Current_Value'] = summary_table['Current_Value'].apply(format_currency)
        summary_table['HPR'] = summary_table['HPR'].apply(lambda x: f"{x:.2f}%")

        # Conditional formatting function for negative HPR
        def highlight_hpr(s):
            # This function needs to be applied to the raw HPR values before formatting to string
            # For a styled dataframe, it receives the entire series.
            # We need to check if the value is a string (already formatted) and parse it.
            return ['background-color: #ffe6e6' if isinstance(val, str) and float(val.replace('%', '')) < 0 else '' for val in s]

        # Display the summary table with conditional formatting
        st.dataframe(
            summary_table.style.apply(highlight_hpr, subset=['HPR']), # Apply to the 'HPR' column
          #  hide_row_index=True,
            column_config={
                group_by_column: st.column_config.TextColumn(get_text(summarize_by_selection, lang)), # Localize column header
                "Investment": st.column_config.Column(get_text("Investment", lang), width="medium"),
                "Current_Value": st.column_config.Column(get_text("Current Value", lang), width="medium"),
                "HPR": st.column_config.Column(get_text("HPR", lang), width="small")
            }
        )

        # 3D. Visual charts like pie chart for Investment Allocation
        st.subheader(get_text("Investment Allocation", lang)) # Localized subheader
        allocation_by_options = {
            get_text("Member", "en"): "Member Name",
            get_text("Sector", "en"): "Sector Display Name",
            get_text("Broker", "en"): "Broker"
        }
        allocation_by = st.selectbox(
            get_text("Allocation by", lang),
            options=[get_text("Member", "en"), get_text("Sector", "en"), get_text("Broker", "en")],
            format_func=lambda x: get_text(x, lang) # Localize options
        )
        allocation_column = allocation_by_options[allocation_by]

        allocation_data = filtered_df.groupby(allocation_column)['Value At Cost'].sum().reset_index()
        fig = go.Figure(data=[go.Pie(
            labels=allocation_data[allocation_column],
            values=allocation_data['Value At Cost'],
            hoverinfo='label+percent',
            textinfo='value',
            texttemplate='%{value:,.2f}', # Format values in the pie chart slices
            marker=dict(line=dict(color='#000000', width=1))
        )])
        fig.update_layout(showlegend=True, title_text=f"{get_text('Investment Allocation', lang)} ({get_text(allocation_by, lang)})")
        st.plotly_chart(fig, use_container_width=True)

        # 3C. Detail Table
        st.subheader(get_text("Detailed Holdings", lang)) # Localized subheader

        # Prepare DataFrame for display, selecting relevant columns and applying mappings
        display_df = filtered_df[[
            'Member Name',
            'Broker',
            'Sector Display Name',
            'Stock Display Name',
            'Qty',
            'Value At Cost',
            'Value At Market Price',
            'HPR'
        ]].copy()

        # Apply currency formatting to monetary columns
        display_df['Value At Cost'] = display_df['Value At Cost'].apply(format_currency)
        display_df['Value At Market Price'] = display_df['Value At Market Price'].apply(format_currency)
        display_df['HPR'] = display_df['HPR'].apply(lambda x: f"{x:.2f}%") # Format HPR as percentage string

        # Rename columns for display in the selected language
        display_df.rename(columns={
            'Member Name': get_text('Select Member', lang),
            'Broker': get_text('Select Broker', lang),
            'Sector Display Name': get_text('Select Sector', lang),
            'Stock Display Name': get_text('Stock Name', lang) if get_text('Stock Name', lang) != 'Stock Name' else 'Stock Name', # Use localized title, fallback to 'Stock Name'
            'Qty': get_text('Quantity', lang) if get_text('Quantity', lang) != 'Quantity' else 'Quantity', # Add 'Quantity' to titles.json for full localization
            'Value At Cost': get_text('Investment', lang),
            'Value At Market Price': get_text('Current Value', lang),
            'HPR': get_text('HPR', lang)
        }, inplace=True)

        # Display the detailed table with conditional formatting for HPR
        st.dataframe(
            display_df.style.apply(highlight_hpr, subset=[get_text('HPR', lang)]), # Apply to the localized HPR column
           # hide_row_index=True,
            column_config={
                get_text('Investment', lang): st.column_config.Column(
                    get_text('Investment', lang),
                    width="medium"
                ),
                get_text('Current Value', lang): st.column_config.Column(
                    get_text('Current Value', lang),
                    width="medium"
                )
            }
        )
