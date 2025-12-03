import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime

# --- 1. SETUP & ERROR HANDLING ---
# We wrap this in a try-except block to catch the specific error you are seeing.
try:
    # This must be the very first Streamlit command
    st.set_page_config(page_title="FinSight Pro", page_icon="💳", layout="wide")
except AttributeError as e:
    # This block runs ONLY if you have the "circular import" error
    if "partially initialized module 'streamlit'" in str(e):
        st.error("⚠️ CRITICAL ERROR DETECTED ⚠️")
        st.error("You have a file named 'streamlit.py' in your folder.")
        st.warning("Please DELETE or RENAME the file 'streamlit.py' in this directory: C:\\Users\\91979\\Desktop\\... (or wherever you saved this script).")
        st.stop()
    else:
        raise e

# Clean, Minimalist UI Styling
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; }
        div[data-testid="stMetricValue"] { font-size: 24px; font-weight: 700; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'budget_v3.db'

# --- 2. DATABASE FUNCTIONS ---
def init_db():
    """Initializes the database with necessary tables."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # User Table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE, 
                  password TEXT)''')
    
    # Transactions Table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_id INTEGER, 
                  type TEXT, 
                  category TEXT, 
                  amount REAL, 
                  date TEXT, 
                  description TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # Goals Table
    c.execute('''CREATE TABLE IF NOT EXISTS goals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  category TEXT,
                  amount REAL,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, make_hash(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, username FROM users WHERE username = ? AND password = ?', 
              (username, make_hash(password)))
    data = c.fetchone()
    conn.close()
    return data

def add_transaction(user_id, type_, category, amount, date, description):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''INSERT INTO transactions (user_id, type, category, amount, date, description) 
                 VALUES (?, ?, ?, ?, ?, ?)''', 
              (user_id, type_, category, amount, date, description))
    conn.commit()
    conn.close()

def delete_transaction(tx_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect(DB_FILE)
    # Automatically sort by Date Descending (Newest first)
    df = pd.read_sql_query("SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC", conn, params=(user_id,))
    conn.close()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

def set_goal(user_id, category, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM goals WHERE user_id = ? AND category = ?", (user_id, category))
    data = c.fetchone()
    if data:
        c.execute("UPDATE goals SET amount = ? WHERE id = ?", (amount, data[0]))
    else:
        c.execute("INSERT INTO goals (user_id, category, amount) VALUES (?, ?, ?)", (user_id, category, amount))
    conn.commit()
    conn.close()

def get_goals(user_id):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT category, amount FROM goals WHERE user_id = ?", conn, params=(user_id,))
    conn.close()
    return df

# Initialize DB on load
init_db()

# --- 3. AUTHENTICATION & LOGIN ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

def login_view():
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.title("FinSight Pro")
        st.write("Personal Finance Dashboard")
        
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Sign In", type="primary", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        with tab2:
            nu = st.text_input("New Username")
            np = st.text_input("New Password", type="password")
            if st.button("Create Account", use_container_width=True):
                if register_user(nu, np):
                    st.success("Account created! Please Login.")
                else:
                    st.error("Username taken.")

# --- 4. MAIN APPLICATION ---
if st.session_state.user_id is None:
    login_view()
else:
    # --- DATA LOADING ---
    df = get_user_data(st.session_state.user_id)
    goals_df = get_goals(st.session_state.user_id)

    # --- SIDEBAR ---
    with st.sidebar:
        st.subheader(f"👤 {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.user_id = None
            st.rerun()
        st.markdown("---")

        # 1. ADD TRANSACTION
        st.subheader("➕ New Transaction")
        with st.form("tx_form", border=True):
            tx_type = st.selectbox("Type", ["Expense", "Income", "Bill", "Debt", "Savings"])
            
            # Smart Categories
            if tx_type == "Income":
                cats = ["Salary", "Freelance", "Investment", "Other"]
            elif tx_type == "Savings":
                cats = ["Emergency Fund", "Retirement", "Vacation", "General"]
            else:
                cats = ["Food", "Rent", "Utilities", "Transport", "Shopping", "Entertainment", "Healthcare", "General"]
            
            tx_cat = st.selectbox("Category", cats)
            tx_desc = st.text_input("Description")
            tx_amount = st.number_input("Amount ($)", min_value=0.01)
            tx_date = st.date_input("Date", datetime.today())
            
            if st.form_submit_button("Add Record", type="primary", use_container_width=True):
                add_transaction(st.session_state.user_id, tx_type, tx_cat, tx_amount, tx_date, tx_desc)
                st.toast("Transaction Added!")
                st.rerun()

        st.markdown("---")

        # 2. SET GOALS
        with st.expander("🎯 Set Budget Goal"):
            with st.form("goal_form"):
                g_cat = st.selectbox("Category", ["Food", "Rent", "Utilities", "Transport", "Shopping", "Entertainment", "Healthcare", "General"])
                g_lim = st.number_input("Monthly Limit ($)", min_value=1.0)
                if st.form_submit_button("Set Goal"):
                    set_goal(st.session_state.user_id, g_cat, g_lim)
                    st.toast("Goal Updated!")
                    st.rerun()

    # --- MAIN DASHBOARD ---
    if df.empty:
        st.info("👋 Welcome! Add your first transaction in the sidebar to get started.")
    else:
        # --- KEY METRICS ---
        inc = df[df['type'] == 'Income']['amount'].sum()
        sav = df[df['type'] == 'Savings']['amount'].sum()
        # Calculate 'Outflow' (Expenses + Bills + Debt)
        outflow_mask = df['type'].isin(['Expense', 'Bill', 'Debt'])
        exp = df[outflow_mask]['amount'].sum()
        
        bal = inc - (exp + sav)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Net Income", f"${inc:,.0f}")
        k2.metric("Total Expenses", f"${exp:,.0f}")
        k3.metric("Total Savings", f"${sav:,.0f}")
        k4.metric("Balance", f"${bal:,.0f}", delta_color="normal" if bal >= 0 else "inverse")
        
        st.markdown("---")

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["📊 Analytics", "📉 Trends", "🛠️ Manage"])

        with tab1:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("Where did the money go?")
                df_out = df[outflow_mask]
                if not df_out.empty:
                    fig_pie = px.pie(df_out, values='amount', names='category', hole=0.5,
                                     color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.caption("No expenses recorded yet.")

            with c2:
                st.subheader("Budget Goals")
                if not goals_df.empty:
                    for _, row in goals_df.iterrows():
                        cat = row['category']
                        limit = row['amount']
                        # Calculate actual spending for this category
                        spent = df[(df['category'] == cat) & outflow_mask]['amount'].sum()
                        pct = min(spent / limit, 1.0)
                        
                        st.write(f"**{cat}**")
                        st.progress(pct)
                        st.caption(f"${spent:,.0f} / ${limit:,.0f}")
                else:
                    st.caption("Set goals in the sidebar.")

        with tab2:
            st.subheader("Income vs Expenses Over Time")
            df['month'] = df['date'].dt.to_period('M').astype(str)
            
            # Aggregate data
            trend = df.groupby(['month', 'type'])['amount'].sum().reset_index()
            trend['kind'] = trend['type'].apply(lambda x: 'Income' if x == 'Income' else 'Expense')
            
            # Simple Bar Chart
            fig_bar = px.bar(trend, x='month', y='amount', color='kind', barmode='group',
                             color_discrete_map={'Income': '#4ade80', 'Expense': '#f87171'})
            st.plotly_chart(fig_bar, use_container_width=True)

        with tab3:
            # TRANSFER TOOL
            st.subheader("🔁 Quick Transfer")
            with st.container(border=True):
                tc1, tc2, tc3 = st.columns([2, 2, 1])
                with tc1:
                    t_dir = st.selectbox("Direction", ["To Savings", "To Balance"])
                with tc2:
                    t_amt = st.number_input("Transfer Amount", min_value=1.0)
                with tc3:
                    st.write("")
                    st.write("")
                    if st.button("Transfer", type="primary", use_container_width=True):
                        today = datetime.today()
                        if t_dir == "To Savings":
                            add_transaction(st.session_state.user_id, "Savings", "Transfer", t_amt, today, "Manual Transfer")
                            st.toast(f"Moved ${t_amt} to Savings")
                        else:
                            # Negative Savings = Moving back to Balance
                            add_transaction(st.session_state.user_id, "Savings", "Transfer", -t_amt, today, "Manual Transfer")
                            st.toast(f"Moved ${t_amt} to Balance")
                        st.rerun()

            st.markdown("### Transaction History")
            # Editable Grid (Auto-sorted by date in query)
            edited_df = st.data_editor(
                df[['id', 'date', 'type', 'category', 'description', 'amount']],
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "date": st.column_config.DateColumn("Date")
                },
                use_container_width=True
            )
            
            with st.expander("Delete Record"):
                col_d1, col_d2 = st.columns([1, 4])
                del_id = col_d1.number_input("ID to Delete", min_value=0, step=1)
                if col_d2.button("Delete Transaction"):
                    delete_transaction(del_id)
                    st.toast("Deleted successfully")
                    st.rerun()
