import streamlit as st
import yaml
import pandas as pd
import requests
import os

def load_credentials():
    with open('cred.yml') as f:
        return yaml.load(f, Loader=yaml.FullLoader)

def save_credentials(creds):
    with open('cred.yml', 'w') as f:
        yaml.dump(creds, f)

def fetch_live_orders():
    try:
        response = requests.get("http://127.0.0.1:8000/orderbook")
        response.raise_for_status()
        data = response.json()
        if 'error' in data:
            raise Exception(data['error'])
        return data
    except requests.exceptions.RequestException as e:
        raise Exception(f"HTTP error: {e}")
    except Exception as e:
        raise Exception(f"Error fetching live orders: {e}")

# Streamlit Page Configuration
st.set_page_config(page_title="Algorithmic Trading Toolkit", layout="wide")

# Custom CSS for better styling 
st.markdown("""
    <style>
        .main {
            background-color: #2471A3;
            padding: 2rem;
            border-radius: 10px;
        }
        .stButton > button {
            background-color: #4CAF50;
            color: white;
        }
        .stButton > button:hover {
            background-color: #45a049;
        }
        .stCheckbox, .stTextInput, .stSubheader {
            margin-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

st.title("Algorithmic Trading Toolkit")

# API Credentials Section
with st.expander("API Credentials"):
    creds = load_credentials()
    col1, col2, col3 = st.columns(3)
    with col1:
        apikey = st.text_input("API KEY", value=creds.get('apikey', ''))
    with col2:
        username = st.text_input("Username", value=creds.get('user', ''))
    with col3:
        password = st.text_input("Password", type="password")

    if st.button("Save Credentials"):
        creds['apikey'] = apikey
        creds['user'] = username
        creds['pwd'] = password
        save_credentials(creds)
        st.success("Credentials saved successfully")

# Trading Configurations Section
with st.expander("Trading Configurations"):
    col1, col2, col3 = st.columns(3)
    with col1:
        normal_log = st.checkbox("Take logs", value=True)
    with col2:
        paper_trade = st.checkbox("Paper Trade", value=False)
    with col3:
        place_order = st.checkbox("Place Order", value=False)

    # Updating global variables based on checkboxes
    NORMAL_LOG = normal_log
    LOG_NEEDED = paper_trade
    AUTO_PLACE_ORDER = place_order

# Live Orders Section
st.subheader("Live Orders")
if st.button("Fetch Live Orders"):
    try:
        orders = fetch_live_orders()
        orders_df = pd.DataFrame(orders)
        st.dataframe(orders_df)
    except Exception as e:
        st.error(f"Error fetching live orders: {e}")

# Login and Logout Buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("Login"):
        st.info("Starting backend server (UVicorn)...")
        os.system("start /B cmd /c \"uvicorn main:app --host 127.0.0.1 --port 8000\"")
        st.success("Backend server (UVicorn) started successfully!")
with col2:
    if st.button("Logout"):
        os.system("taskkill /f /im uvicorn.exe")
        st.success("Backend server (UVicorn) stopped successfully!")
