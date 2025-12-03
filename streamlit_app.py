import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime, timedelta

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
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
            border: 1px solid #2B2B2B;
        }
        
        /* Buttons - Apple Blue Pills */
        div.stButton > button {
            background-color: #0A84FF !important;
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
        
        /* Restore Streamlit Menu (Hamburger) */
        #MainMenu {visibility: visible;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'budget_v3.db'

# --- 2. DATABASE FUNCTIONS ---
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
        df = pd.read_sql_query("SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC", conn, params=(user_id,))
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date']) 
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
    # --- LOAD DATA ---
    df = get_user_data(st.session_state.user_id)
    goals_df = get_goals(st.session_state.user_id)
    
    # --- CALCULATIONS ---
    if df.empty:
        total_inc, total_exp, total_sav, current_bal = 0.0, 0.0, 0.0, 0.0
    else:
        total_inc = df[df['type'] == 'Income']['amount'].sum()
        total_outflow_mask = df['type'].isin(['Expense', 'Bill', 'Debt', 'Withdrawal'])
        total_exp = df[total_outflow_mask]['amount'].sum()
        total_sav = df[df['type'] == 'Savings']['amount'].sum()
        current_bal = total_inc - (total_exp + total_sav)
    
    # --- SIDEBAR ACTIONS ---
    with st.sidebar:
        st.markdown(f"### Hello, {st.session_state.username}")
        if st.button("Sign Out", key="logout"):
            st.session_state.user_id = None
            st.rerun()
        st.markdown("---")
        
        # Action 1: Add Transaction
        with st.expander("➕ New Transaction", expanded=True):
            with st.form("add_tx_form", border=False):
                ft_type = st.selectbox("Type", ["Expense", "Income", "Bill", "Debt", "Savings"], label_visibility="collapsed")
                ft_desc = st.text_input("Description", placeholder="e.g. Starbucks")
                c_amt, c_cat = st.columns([1, 1.5])
                ft_amt = c_amt.number_input("Price", min_value=0.01, step=10.0, label_visibility="collapsed")
                cats = ["Food", "Rent", "Transport", "Shopping", "Entertainment", "Health", "Salary", "Invest", "Loan"]
                ft_cat = c_cat.selectbox("Category", cats, label_visibility="collapsed")
                ft_date = st.date_input("Date", datetime.today(), label_visibility="collapsed")
                
                if st.form_submit_button("Add Entry", use_container_width=True):
                    if ft_type in ["Expense", "Bill", "Debt", "Savings"]:
                        if ft_amt > current_bal:
                            st.error(f"❌ Insufficient Balance! (${current_bal:,.2f})")
                        else:
                            add_transaction(st.session_state.user_id, ft_type, ft_cat, ft_amt, ft_date, ft_desc)
                            st.toast("Entry Added", icon="✅")
                            st.rerun()
                    else:
                        add_transaction(st.session_state.user_id, ft_type, ft_cat, ft_amt, ft_date, ft_desc)
                        st.toast("Income Added", icon="✅")
                        st.rerun()

        # Action 2: Quick Transfer
        with st.expander("🔁 Quick Transfer", expanded=False):
            with st.form("quick_transfer", border=False):
                st.caption("Move money between Savings and Balance")
                t_act = st.selectbox("Action", ["Save", "Cash Out"], label_visibility="collapsed")
                col_t1, col_t2 = st.columns(2)
                t_val = col_t1.number_input("Amt", min_value=1.0, label_visibility="collapsed")
                t_date = col_t2.date_input("Date", datetime.today(), label_visibility="collapsed")
                
                if st.form_submit_button("Execute", use_container_width=True):
                    try:
                        val = float(t_val)
                        dt_str = t_date.strftime("%Y-%m-%d")
                        
                        if t_act == "Save":
                            if val > current_bal:
                                st.error(f"❌ Insufficient Funds! (${current_bal:,.2f})")
                            else:
                                add_transaction(st.session_state.user_id, "Savings", "Transfer", val, dt_str, "Manual Save")
                                st.toast("Saved to Pot", icon="✅")
                                st.rerun()
                        else: # Cash Out
                            if val > current_bal:
                                st.error(f"❌ Insufficient Funds! (${current_bal:,.2f})")
                            else:
                                add_transaction(st.session_state.user_id, "Withdrawal", "Cash", val, dt_str, "Cash Withdrawal")
                                st.toast("Withdrawn from Balance", icon="✅")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Transfer Failed: {e}")
        
        # Action 3: Set Goal
        with st.expander("🎯 Set Goal", expanded=False):
            with st.form("goal_form", border=False):
                g_cat = st.selectbox("Category", cats)
                g_lim = st.number_input("Monthly Limit ($)", min_value=1.0)
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
    
    c_title, c_filter = st.columns([3, 1])
    with c_title:
        st.title("Overview")
        # st.markdown(f"<div style='color: #86868B; margin-top: -15px; margin-bottom: 20px;'>{datetime.today().strftime('%B %d, %Y')}</div>", unsafe_allow_html=True)
    with c_filter:
        time_range = st.selectbox("Time Period", ["This Month", "All Time", "Today", "Yesterday", "This Week", "This Year", "Custom Range"], label_visibility="collapsed")

    # Apply Filter Logic
    if not df.empty:
        today = datetime.today()
        # Factor used to scale goals (e.g. if viewing year, multiply monthly goal by 12)
        goal_scale_factor = 1.0 
        
        if time_range == "Today":
            filtered_df = df[df['date'].dt.date == today.date()]
            goal_scale_factor = 1/30
        elif time_range == "Yesterday":
            filtered_df = df[df['date'].dt.date == (today - timedelta(days=1)).date()]
            goal_scale_factor = 1/30
        elif time_range == "This Week":
            start_week = today - timedelta(days=today.weekday())
            filtered_df = df[df['date'].dt.date >= start_week.date()]
            goal_scale_factor = 0.25 # Approx 1 week out of 4
        elif time_range == "This Month":
            filtered_df = df[(df['date'].dt.month == today.month) & (df['date'].dt.year == today.year)]
            goal_scale_factor = 1.0
        elif time_range == "This Year":
            filtered_df = df[df['date'].dt.year == today.year]
            goal_scale_factor = 12.0
        elif time_range == "Custom Range":
            # Show Date Range Picker
            c_d1, c_d2 = st.columns(2)
            d_start = c_d1.date_input("Start", today - timedelta(days=30))
            d_end = c_d2.date_input("End", today)
            if d_start <= d_end:
                filtered_df = df[(df['date'].dt.date >= d_start) & (df['date'].dt.date <= d_end)]
                # Calculate scale based on number of days
                days_diff = (d_end - d_start).days + 1
                goal_scale_factor = days_diff / 30.0
            else:
                st.error("End date must be after start date.")
                filtered_df = df
        else:
            filtered_df = df
            goal_scale_factor = 1.0 # All Time - difficult to scale, keeping 1.0 or separate logic
    else:
        filtered_df = pd.DataFrame()
        goal_scale_factor = 1.0

    if df.empty:
        st.info("No transactions yet. Add one from the sidebar.")
    else:
        if not filtered_df.empty:
            p_inc = filtered_df[filtered_df['type'] == 'Income']['amount'].sum()
            p_out_mask = filtered_df['type'].isin(['Expense', 'Bill', 'Debt', 'Withdrawal'])
            p_exp = filtered_df[p_out_mask]['amount'].sum()
        else:
            p_inc, p_exp = 0.0, 0.0

        # Row 1: Metrics
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(f"Income ({time_range})", f"${p_inc:,.0f}")
        k2.metric(f"Expenses ({time_range})", f"${p_exp:,.0f}")
        k3.metric("Total Savings", f"${total_sav:,.0f}") 
        k4.metric("Current Balance", f"${current_bal:,.0f}", delta_color="normal")
        st.markdown("<br>", unsafe_allow_html=True)

        # Row 2: Charts
        if not filtered_df.empty:
            c_left, c_right = st.columns([2, 1])
            with c_left:
                st.subheader("Activity")
                chart_df = filtered_df.copy()
                if time_range in ["Today", "Yesterday"]:
                    trend = chart_df.groupby(['type'])['amount'].sum().reset_index()
                    fig = px.bar(trend, x='type', y='amount', color='type', 
                                 color_discrete_map={'Income': '#30D158', 'Expense': '#FF453A', 'Withdrawal': '#FF9F0A', 'Savings': '#0A84FF'})
                else:
                    chart_df['day'] = chart_df['date'].dt.strftime('%b %d')
                    trend = chart_df.groupby(['day', 'type'])['amount'].sum().reset_index()
                    trend = trend[trend['type'].isin(['Income', 'Expense', 'Withdrawal'])]
                    fig = px.bar(trend, x='day', y='amount', color='type', barmode='group',
                                 color_discrete_map={'Income': '#30D158', 'Expense': '#FF453A', 'Withdrawal': '#FF9F0A'})
                
                fig.update_layout(plot_bgcolor='#1E1E1E', paper_bgcolor='#1E1E1E', font=dict(color='#FAFAFA'), xaxis=dict(showgrid=False, title=""), yaxis=dict(showgrid=True, gridcolor='#333333', title=""), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""), margin=dict(t=30, l=0, r=0, b=0), height=300)
                st.plotly_chart(fig, use_container_width=True)

            with c_right:
                st.subheader("Breakdown")
                df_exp_period = filtered_df[filtered_df['type'].isin(['Expense', 'Bill', 'Debt', 'Withdrawal'])]
                if not df_exp_period.empty:
                    fig_pie = px.pie(df_exp_period, values='amount', names='category', hole=0.7, color_discrete_sequence=['#0A84FF', '#5E5CE6', '#BF5AF2', '#FF375F', '#FF9F0A', '#FFD60A'])
                    fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=200, plot_bgcolor='#1E1E1E', paper_bgcolor='#1E1E1E', annotations=[dict(text=f"${p_exp:,.0f}", x=0.5, y=0.5, font_size=20, showarrow=False, font=dict(color="#FAFAFA"))])
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.caption("No expenses in this period.")
                    
                if not goals_df.empty:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if time_range == "This Month":
                        st.subheader("Monthly Goals")
                    else:
                        st.subheader(f"Goals (Scaled for {time_range})")
                    
                    # Filter data for goals based on selected range
                    outflow_period_mask = filtered_df['type'].isin(['Expense', 'Bill', 'Debt', 'Withdrawal'])
                    
                    for _, row in goals_df.iterrows():
                        cat = row['category']
                        # Scale the monthly limit based on the time range selected
                        limit = row['amount'] * goal_scale_factor
                        
                        # Calculate spend ONLY for the filtered period
                        spent = filtered_df[(filtered_df['category'] == cat) & outflow_period_mask]['amount'].sum()
                        
                        ratio = spent / limit if limit > 0 else 0
                        pct = min(ratio * 100, 100)
                        
                        if ratio >= 1.0: bar_color = "#FF453A"
                        elif ratio >= 0.75: bar_color = "#FFD60A"
                        else: bar_color = "#30D158"

                        st.markdown(f"""<div style="margin-bottom: 5px; display: flex; justify-content: space-between; font-size: 14px; color: #A0A0A0;"><span>{cat}</span><span>${spent:,.0f} / ${limit:,.0f}</span></div><div style="background-color: #2C2C2E; border-radius: 10px; height: 8px; width: 100%;"><div style="background-color: {bar_color}; width: {pct}%; height: 100%; border-radius: 10px;"></div></div><br>""", unsafe_allow_html=True)
        else:
            st.info(f"No records found for {time_range}.")

        # Row 3: Recent Transactions
        st.markdown("---")
        st.subheader("All Transactions")
        
        # Displaying ALL filtered rows, no .head(10) restriction
        if not filtered_df.empty:
            grid_df = filtered_df[['id', 'date', 'description', 'category', 'amount', 'type']]
            st.dataframe(
                grid_df,
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "date": st.column_config.DateColumn("Date", format="MMM DD"),
                    "amount": st.column_config.NumberColumn("Amount", format="$%d"),
                    "type": st.column_config.TextColumn("Type"),
                },
                use_container_width=True,
                height=400 # Fixed height with scrollbar
            )
        else:
            st.caption("No transactions available.")
