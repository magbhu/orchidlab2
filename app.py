import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import os

# Function to load data
@st.cache_data
def load_data(file_path):
    """Loads CSV data from the given file path."""
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        st.error(f"Error: File not found at {file_path}")
        return pd.DataFrame()

# Function to load JSON mappings
@st.cache_data
def load_json_mapping(file_path):
    """Loads JSON data from the given file path."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Error: Mapping file not found at {file_path}")
        return {}

# Load mapping files
member_mapping = load_json_mapping('member_mapping.json')
sector_mapping = load_json_mapping('sector_mapping.json')
stock_mapping = load_json_mapping('stock_mapping.json')
titles_mapping = load_json_mapping('titles.json')

# Default portfolio file path
DEFAULT_PORTFOLIO_FILE = 'portfolioinputs.csv' # [cite: 21]

def get_text(key, lang):
    """Retrieves localized text from the titles mapping."""
    return titles_mapping.get(key, {}).get(lang, key)

def format_currency(value):
    """Formats a number as Indian Rupees."""
    return f"₹ {value:,.2f}"

def get_member_name(member_code, lang):
    """Retrieves localized member name."""
    return member_mapping.get(member_code, {}).get(lang, member_code)

def get_sector_name(sector_name_en, lang):
    """Retrieves localized sector name based on English name."""
    for key, value in sector_mapping.items():
        if value['en'] == sector_name_en:
            return value.get(lang, sector_name_en)
    return sector_name_en

def get_stock_name(isin_code, lang):
    """Retrieves localized stock name."""
    return stock_mapping.get(isin_code, {}).get(lang, isin_code)

st.set_page_config(layout="wide")

# Language selection
lang = st.sidebar.selectbox(
    get_text("Select Language", "en"), # [cite: 7, 10, 13, 14, 15]
    options=["en", "ta"],
    format_func=lambda x: "English" if x == "en" else "தமிழ்"
)

st.title(get_text("Portfolio Summary", lang)) # [cite: 15, 16]

# File uploader 
uploaded_file = st.sidebar.file_uploader(get_text("Upload Portfolio CSV", lang), type="csv") # 

df = pd.DataFrame()
if uploaded_file is not None:
    df = load_data(uploaded_file)
else:
    if os.path.exists(DEFAULT_PORTFOLIO_FILE):
        df = load_data(DEFAULT_PORTFOLIO_FILE)
    else:
        st.info("Please upload a portfolio CSV file.")

if not df.empty:
    # Data Cleaning and Type Conversion (if necessary)
    df['Value At Cost'] = pd.to_numeric(df['Value At Cost'], errors='coerce')
    df['Value At Market Price'] = pd.to_numeric(df['Value At Market Price'], errors='coerce')
    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce')

    # Apply mappings for display
    df['Member Name'] = df['Member Code'].apply(lambda x: get_member_name(x, lang)) # [cite: 6, 7, 8, 19]
    df['Stock Display Name'] = df['ISIN Code'].apply(lambda x: get_stock_name(x, lang)) # [cite: 12, 13, 14]
    df['Sector Display Name'] = df['Sector Name'].apply(lambda x: get_sector_name(x, lang)) # [cite: 9, 10, 11]

    # Calculate HPR 
    # Handle potential division by zero
    df['HPR'] = ((df['Value At Market Price'] - df['Value At Cost']) / df['Value At Cost'] * 100).round(2) # [cite: 7, 10]
    df['HPR'] = df['HPR'].fillna(0) # Replace NaN with 0 for display purposes

    # Filters 
    all_portfolios = ['All'] + df['Portfolio'].unique().tolist()
    selected_portfolio = st.sidebar.selectbox(get_text("Select Portfolio", lang), all_portfolios) # [cite: 20]

    all_members = ['All'] + df['Member Name'].unique().tolist()
    selected_member = st.sidebar.selectbox(get_text("Select Member", lang), all_members) # 

    all_sectors = ['All'] + df['Sector Display Name'].unique().tolist()
    selected_sector = st.sidebar.selectbox(get_text("Select Sector", lang), all_sectors) # 

    all_brokers = ['All'] + df['Broker'].unique().tolist()
    selected_broker = st.sidebar.selectbox(get_text("Select Broker", lang), all_brokers) # 

    # Apply filters
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
        st.warning("No data available for the selected filters.")
    else:
        # 3A. Total Summary (one liner) 
        total_investment = filtered_df['Value At Cost'].sum() # 
        total_current_value = filtered_df['Value At Market Price'].sum() # 
        total_hpr = ((total_current_value - total_investment) / total_investment * 100).round(2) if total_investment != 0 else 0 # 

        st.subheader(get_text("Portfolio Summary", lang)) # 
        st.write(f"**{get_text('Investment', lang)}:** {format_currency(total_investment)} | " # 
                 f"**{get_text('Current Value', lang)}:** {format_currency(total_current_value)} | " # 
                 f"**{get_text('HPR', lang)}:** {total_hpr:.2f}%") # 

        # 3B. Summary Table (aggregation values alone) 
        st.subheader(get_text("Summary Table", lang)) # 

        summarize_by_options = {
            "Member": "Member Name",
            "Sector": "Sector Display Name",
            "Broker": "Broker"
        }
        # Initial sort order to be member 
        summarize_by_selection = st.radio(get_text("Summarize By", lang), options=list(summarize_by_options.keys()), index=0, horizontal=True) # 
        group_by_column = summarize_by_options[summarize_by_selection]

        summary_table = filtered_df.groupby(group_by_column).agg( # 
            Investment=('Value At Cost', 'sum'), # 
            Current_Value=('Value At Market Price', 'sum') # 
        ).reset_index()

        summary_table['HPR'] = ((summary_table['Current_Value'] - summary_table['Investment']) / summary_table['Investment'] * 100).round(2) # 
        summary_table['HPR'] = summary_table['HPR'].fillna(0) # Handle division by zero for HPR

        # Apply formatting
        summary_table['Investment'] = summary_table['Investment'].apply(format_currency) # 
        summary_table['Current_Value'] = summary_table['Current_Value'].apply(format_currency) # 
        summary_table['HPR'] = summary_table['HPR'].apply(lambda x: f"{x:.2f}%") # 

        # Conditional formatting for HPR 
        def highlight_hpr(s):
            if isinstance(s, str) and '%' in s:
                value = float(s.replace('%', ''))
                return ['background-color: #ffe6e6' if value < 0 else '' for _ in s] # Light red for negative returns
            return ['' for _ in s]

        st.dataframe(
            summary_table.style.apply(highlight_hpr, subset=['HPR']),
         #   hide_row_index=True,
            column_config={
                group_by_column: st.column_config.TextColumn(group_by_column),
                "Investment": st.column_config.Column(get_text("Investment", lang), width="medium"), # 
                "Current_Value": st.column_config.Column(get_text("Current Value", lang), width="medium"), # 
                "HPR": st.column_config.Column(get_text("HPR", lang), width="small") # 
            }
        )

        # 3D. Visual charts like pie chart 
        st.subheader(get_text("Investment Allocation", lang)) # 
        allocation_by = st.selectbox(
            get_text("Allocation by", lang), # 
            options=list(summarize_by_options.keys()),
            format_func=lambda x: get_text(x, lang) # Translate options
        )
        allocation_column = summarize_by_options[allocation_by]

        allocation_data = filtered_df.groupby(allocation_column)['Value At Cost'].sum().reset_index()
        fig = go.Figure(data=[go.Pie(
            labels=allocation_data[allocation_column],
            values=allocation_data['Value At Cost'],
            hoverinfo='label+percent',
            textinfo='value',
            texttemplate='%{value:,.2f}',
            marker=dict(line=dict(color='#000000', width=1))
        )])
        fig.update_layout(showlegend=True, title_text=f"{get_text('Investment Allocation', lang)} ({get_text(allocation_by, lang)})")
        st.plotly_chart(fig, use_container_width=True)

        # 3C. Detail Table 
        st.subheader(get_text("Detailed Holdings", lang)) # 

        # Prepare for display, applying mappings and formatting
        display_df = filtered_df[[
            'Member Name', # 
            'Broker', # 
            'Sector Display Name', # 
            'Stock Display Name', # 
            'Qty', # 
            'Value At Cost', # 
            'Value At Market Price', # 
            'HPR' # 
        ]].copy()

        # Apply currency formatting
        display_df['Value At Cost'] = display_df['Value At Cost'].apply(format_currency) # 
        display_df['Value At Market Price'] = display_df['Value At Market Price'].apply(format_currency) # 
        display_df['HPR'] = display_df['HPR'].apply(lambda x: f"{x:.2f}%") # 

        # Rename columns for display in selected language
        display_df.rename(columns={
            'Member Name': get_text('Select Member', lang),
            'Broker': get_text('Select Broker', lang),
            'Sector Display Name': get_text('Select Sector', lang),
            'Stock Display Name': get_text('Stock Name', lang) if lang == 'en' else get_stock_name('ISIN Code', lang), # Fallback if specific stock name not in titles.json
            'Qty': get_text('Quantity', lang) if lang == 'en' else 'அளவு', # Example, add to titles.json for proper localization
            'Value At Cost': get_text('Investment', lang),
            'Value At Market Price': get_text('Current Value', lang),
            'HPR': get_text('HPR', lang)
        }, inplace=True)

        # Conditional formatting for negative HPR in detailed table 
        st.dataframe(
            display_df.style.apply(highlight_hpr, subset=[get_text('HPR', lang)]),
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