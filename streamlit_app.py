import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime

# --- 1. SETUP & APPLE-STYLE DARK MODE CSS ---
try:
    st.set_page_config(page_title="FinSight", page_icon="", layout="wide", initial_sidebar_state="expanded")
except AttributeError:
    pass

# Custom CSS for Apple Dark Mode Feel
st.markdown("""
    <style>
        /* FORCE DARK MODE VISUALS */
        .stApp {
            background-color: #0E1117 !important;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #151920 !important;
            border-right: 1px solid #2B2B2B;
        }
        
        /* Force Text Colors to White/Light Grey */
        h1, h2, h3, h4, h5, h6, p, span, div {
            color: #FAFAFA !important;
        }
        div[data-testid="stMetricLabel"] {
            color: #A0A0A0 !important;
        }
        div[data-testid="stMetricValue"] {
            color: #FFFFFF !important;
        }
        
        /* Cards (Metrics, Charts, Forms) */
        div[data-testid="stMetric"], div.stDataFrame, div.stPlotlyChart, div[data-testid="stForm"] {
            background-color: #1E1E1E !important;
            border-radius: 18px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4); /* Darker shadow for depth */
            border: 1px solid #2B2B2B;
        }
        
        /* Buttons - Apple Blue Pills */
        div.stButton > button {
            background-color: #0A84FF !important; /* Slightly brighter blue for dark mode */
            color: white !important;
            border-radius: 20px !important;
            border: none !important;
            padding: 10px 24px !important;
            font-weight: 500 !important;
        }
        
        /* Inputs */
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div {
            background-color: #2C2C2E !important;
            color: #FFFFFF !important;
            border: 1px solid #3A3A3C;
        }
        
        /* Centered Login Alignment */
        div.block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* Hide Streamlit Chrome */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'budget_v3.db'

# --- 2. DATABASE FUNCTIONS (Robust Context Managers) ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, category TEXT, amount REAL, date TEXT, description TEXT, FOREIGN KEY(user_id) REFERENCES users(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, category TEXT, amount REAL, FOREIGN KEY(user_id) REFERENCES users(id))''')
        conn.commit()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def register_user(username, password):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, make_hash(password)))
            conn.commit()
            return True
    except:
        return False

def login_user(username, password):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('SELECT id, username FROM users WHERE username = ? AND password = ?', (username, make_hash(password)))
        return c.fetchone()

def add_transaction(user_id, type_, category, amount, date, description):
    # FIX: Explicitly convert date to string to prevent data dropping issues
    date_str = str(date)
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO transactions (user_id, type, category, amount, date, description) VALUES (?, ?, ?, ?, ?, ?)''', (user_id, type_, category, amount, date_str, description))
        conn.commit()

def delete_transaction(tx_id):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        conn.commit()

def get_user_data(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC", conn, params=(user_id,))
    
    if not df.empty:
        # FIX: coercing errors handles bad date formats gracefully
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date']) # Drop rows with invalid dates
    return df

def set_goal(user_id, category, amount):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM goals WHERE user_id = ? AND category = ?", (user_id, category))
        data = c.fetchone()
        if data:
            c.execute("UPDATE goals SET amount = ? WHERE id = ?", (amount, data[0]))
        else:
            c.execute("INSERT INTO goals (user_id, category, amount) VALUES (?, ?, ?)", (user_id, category, amount))
        conn.commit()

def get_goals(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query("SELECT category, amount FROM goals WHERE user_id = ?", conn, params=(user_id,))

init_db()

# --- 3. UI VIEWS ---

def login_view():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>FinSight</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Sign In", "Create Account"])
        with tab1:
            with st.form("login_form"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Sign In", use_container_width=True):
                    user = login_user(u, p)
                    if user:
                        st.session_state.user_id = user[0]
                        st.session_state.username = user[1]
                        st.rerun()
                    else:
                        st.error("Incorrect username or password.")
        with tab2:
            with st.form("register_form"):
                nu = st.text_input("Choose Username")
                np = st.text_input("Choose Password", type="password")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Create ID", use_container_width=True):
                    if register_user(nu, np):
                        st.success("ID Created. You can now sign in.")
                    else:
                        st.error("Username unavailable.")

# --- 4. MAIN APP ---

if 'user_id' not in st.session_state: st.session_state.user_id = None

if st.session_state.user_id is None:
    login_view()
else:
    df = get_user_data(st.session_state.user_id)
    goals_df = get_goals(st.session_state.user_id)
    
    # --- SIDEBAR: ALL ACTIONS HERE (Fixes Overlap) ---
    with st.sidebar:
        st.markdown(f"### Hello, {st.session_state.username}")
        if st.button("Sign Out", key="logout"):
            st.session_state.user_id = None
            st.rerun()
        st.markdown("---")
        
        # Action 1: Add Transaction
        with st.expander("➕ New Transaction", expanded=True):
            with st.form("add_tx_form", border=False):
                ft_type = st.selectbox("Type", ["Expense", "Income", "Bill", "Savings"], label_visibility="collapsed")
                ft_desc = st.text_input("Description", placeholder="e.g. Starbucks")
                c_amt, c_cat = st.columns([1, 1.5])
                ft_amt = c_amt.number_input("Price", min_value=0.01, step=10.0, label_visibility="collapsed")
                cats = ["Food", "Rent", "Transport", "Shopping", "Entertainment", "Health", "Salary", "Invest"]
                ft_cat = c_cat.selectbox("Category", cats, label_visibility="collapsed")
                ft_date = st.date_input("Date", datetime.today(), label_visibility="collapsed")
                if st.form_submit_button("Add Entry", use_container_width=True):
                    add_transaction(st.session_state.user_id, ft_type, ft_cat, ft_amt, ft_date, ft_desc)
                    st.toast("Entry Added", icon="✅")
                    st.rerun()

        # Action 2: Quick Transfer
        with st.expander("🔁 Quick Transfer", expanded=False):
            with st.form("quick_transfer", border=False):
                col_t1, col_t2 = st.columns(2)
                t_act = col_t1.selectbox("Action", ["Save", "Withdraw"], label_visibility="collapsed")
                t_val = col_t2.number_input("Amt", min_value=1.0, label_visibility="collapsed")
                if st.form_submit_button("Execute", use_container_width=True):
                    val = t_val if t_act == "Save" else -t_val
                    add_transaction(st.session_state.user_id, "Savings", "Transfer", val, datetime.today(), "Quick Transfer")
                    st.toast("Transfer Complete", icon="✅")
                    st.rerun()
        
        # Action 3: Set Goal
        with st.expander("🎯 Set Goal", expanded=False):
            with st.form("goal_form", border=False):
                g_cat = st.selectbox("Category", cats)
                g_lim = st.number_input("Limit ($)", min_value=1.0)
                if st.form_submit_button("Save Goal", use_container_width=True):
                    set_goal(st.session_state.user_id, g_cat, g_lim)
                    st.toast("Goal Saved", icon="✅")
                    st.rerun()
        
        # Action 4: Delete Data
        with st.expander("🗑️ Delete Data", expanded=False):
            with st.form("delete_form", border=False):
                del_id = st.number_input("ID to Delete", min_value=0, step=1)
                if st.form_submit_button("Delete", use_container_width=True):
                    delete_transaction(del_id)
                    st.toast("Transaction Deleted", icon="🗑️")
                    st.rerun()

    # --- MAIN DASHBOARD ---
    st.title("Overview")
    st.markdown(f"<div style='color: #86868B; margin-top: -15px; margin-bottom: 20px;'>{datetime.today().strftime('%B %d, %Y')}</div>", unsafe_allow_html=True)

    if df.empty:
        st.info("No transactions yet. Add one from the sidebar.")
    else:
        inc = df[df['type'] == 'Income']['amount'].sum()
        outflow_mask = df['type'].isin(['Expense', 'Bill'])
        exp = df[outflow_mask]['amount'].sum()
        sav = df[df['type'] == 'Savings']['amount'].sum()
        bal = inc - (exp + sav)
        
        # Row 1: Metrics
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Income", f"${inc:,.0f}")
        k2.metric("Expenses", f"${exp:,.0f}")
        k3.metric("Savings", f"${sav:,.0f}")
        k4.metric("Balance", f"${bal:,.0f}", delta_color="normal")
        st.markdown("<br>", unsafe_allow_html=True)

        # Row 2: Charts (2/3 Bar, 1/3 Pie)
        c_left, c_right = st.columns([2, 1])
        with c_left:
            st.subheader("Activity")
            df['month'] = df['date'].dt.strftime('%b')
            trend = df.groupby(['month', 'type'])['amount'].sum().reset_index()
            trend = trend[trend['type'].isin(['Income', 'Expense'])]
            
            fig = px.bar(trend, x='month', y='amount', color='type', barmode='group',
                         color_discrete_map={'Income': '#30D158', 'Expense': '#FF453A'})
            
            fig.update_layout(
                plot_bgcolor='#1E1E1E', 
                paper_bgcolor='#1E1E1E',
                font=dict(color='#FAFAFA'),
                xaxis=dict(showgrid=False, title=""),
                yaxis=dict(showgrid=True, gridcolor='#333333', title=""),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
                margin=dict(t=30, l=0, r=0, b=0),
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)

        with c_right:
            st.subheader("Breakdown")
            df_exp = df[outflow_mask]
            if not df_exp.empty:
                fig_pie = px.pie(df_exp, values='amount', names='category', hole=0.7,
                                 color_discrete_sequence=['#0A84FF', '#5E5CE6', '#BF5AF2', '#FF375F', '#FF9F0A', '#FFD60A'])
                fig_pie.update_layout(
                    showlegend=False, 
                    margin=dict(t=0, b=0, l=0, r=0), 
                    height=200,
                    plot_bgcolor='#1E1E1E',
                    paper_bgcolor='#1E1E1E',
                    annotations=[dict(text=f"${exp:,.0f}", x=0.5, y=0.5, font_size=20, showarrow=False, font=dict(color="#FAFAFA"))]
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.caption("No expenses.")
                
            # Goals moved here, cleaner look
            if not goals_df.empty:
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("Goals")
                for _, row in goals_df.iterrows():
                    cat = row['category']
                    limit = row['amount']
                    spent = df[(df['category'] == cat) & outflow_mask]['amount'].sum()
                    pct = min(spent / limit, 1.0)
                    st.caption(f"{cat} · ${spent:,.0f} / ${limit:,.0f}")
                    st.progress(pct)

        # Row 3: Recent Transactions (Full Width to avoid overlap)
        st.markdown("---")
        st.subheader("Recent Transactions")
        # Added ID column to display so users know what to delete
        grid_df = df[['id', 'date', 'description', 'category', 'amount', 'type']].head(10)
        st.dataframe(
            grid_df,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "date": st.column_config.DateColumn("Date", format="MMM DD"),
                "amount": st.column_config.NumberColumn("Amount", format="$%d"),
                "type": st.column_config.TextColumn("Type"),
            },
            use_container_width=True
        )
