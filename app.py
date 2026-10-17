import sqlite3
import hashlib
import streamlit as st
import pandas as pd

st.set_page_config(page_title="WalletWise | Digital Wallet", page_icon="💳", layout="wide")
DB_NAME = "wallet.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def hash_password(password):
    # For this educational demo only; production apps should use a password-hashing library.
    return hashlib.sha256(password.encode()).hexdigest()


def initialize_database():
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS wallet (
            id INTEGER PRIMARY KEY,
            balance REAL NOT NULL
        )""")
        conn.execute("INSERT OR IGNORE INTO wallet (id, balance) VALUES (1, 1000.0)")
        conn.execute("""CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        columns = [r[1] for r in conn.execute("PRAGMA table_info(transactions)").fetchall()]
        if "user_id" not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER")
        conn.execute("""CREATE TABLE IF NOT EXISTS user_wallets (
            user_id INTEGER PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 1000.0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""")
        users = conn.execute("SELECT id FROM users ORDER BY id").fetchall()
        for (user_id,) in users:
            conn.execute("INSERT OR IGNORE INTO user_wallets (user_id, balance) VALUES (?, 1000.0)", (user_id,))
        # Preserve older transactions by assigning previously unassigned rows to the first existing account.
        if users:
            conn.execute("UPDATE transactions SET user_id = ? WHERE user_id IS NULL", (users[0][0],))


def register_user(username, password):
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password))
            )
            user_id = cur.lastrowid
            conn.execute("INSERT OR IGNORE INTO user_wallets (user_id, balance) VALUES (?, 1000.0)", (user_id,))
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user(username, password):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ? AND password_hash = ?",
            (username, hash_password(password))
        ).fetchone()
    return row[0] if row else None


def get_balance():
    user_id = st.session_state["logged_in_user"]
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO user_wallets (user_id, balance) VALUES (?, 1000.0)", (user_id,))
        row = conn.execute("SELECT balance FROM user_wallets WHERE user_id = ?", (user_id,)).fetchone()
    return row[0]


def get_transactions():
    user_id = st.session_state["logged_in_user"]
    with get_connection() as conn:
        rows = conn.execute("""SELECT transaction_type, amount, created_at
            FROM transactions WHERE user_id = ? ORDER BY id DESC""", (user_id,)).fetchall()
    return [{"Transaction": r[0], "Amount (₹)": r[1], "Date and Time": r[2]} for r in rows]


def add_money(amount):
    user_id = st.session_state["logged_in_user"]
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO user_wallets (user_id, balance) VALUES (?, 1000.0)", (user_id,))
        conn.execute("UPDATE user_wallets SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.execute("INSERT INTO transactions (transaction_type, amount, user_id) VALUES (?, ?, ?)",
                     ("Money Added", amount, user_id))


def send_money(receiver, amount):
    user_id = st.session_state["logged_in_user"]
    with get_connection() as conn:
        row = conn.execute("SELECT balance FROM user_wallets WHERE user_id = ?", (user_id,)).fetchone()
        if row is None or amount > row[0]:
            return False
        conn.execute("UPDATE user_wallets SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.execute("INSERT INTO transactions (transaction_type, amount, user_id) VALUES (?, ?, ?)",
                     (f"Sent to {receiver}", -amount, user_id))
    return True


def go_to_add_money():
    st.session_state["navigation"] = "Add Money"


def go_to_send_money():
    st.session_state["navigation"] = "Send Money"


initialize_database()

st.markdown("""
<style>
.stApp { background-color: #f5f7fb; color: #172033; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
[data-testid="stSidebar"] { background-color: #172554 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #f8fafc !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label p { color: #f8fafc !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) { background-color: #2563eb !important; border-radius: 10px !important; }
.stApp h1, .stApp h2, .stApp h3 { color: #172033 !important; }
[data-testid="stMetric"] { background-color: #fff !important; padding: 20px !important; border-radius: 14px !important; border: 1px solid #dbe3ef !important; box-shadow: 0 2px 8px rgba(15,23,42,.06); }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p, [data-testid="stMetricValue"], [data-testid="stMetricValue"] div { color: #172033 !important; opacity: 1 !important; }
.stTextInput input, .stNumberInput input { background-color: #fff !important; color: #172033 !important; border: 1px solid #94a3b8 !important; }
.stTextInput label, .stNumberInput label { color: #172033 !important; font-weight: 600 !important; }
.stApp div[role="radiogroup"] label p { color: #172033 !important; }
div.stButton > button { background-color: #2563eb !important; color: #fff !important; border: none; border-radius: 9px; min-height: 42px; font-weight: 600; }
div.stButton > button:hover { background-color: #1d4ed8 !important; color: #fff !important; }
hr { border-color: #dbe3ef; }
</style>
""", unsafe_allow_html=True)

if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None

if st.session_state["logged_in_user"] is None:
    st.title("💳 WalletWise")
    st.subheader("Welcome! Please log in or create an account.")
    auth_page = st.radio("Choose an option", ["Login", "Register"], horizontal=True, key="auth_page")
    if auth_page == "Register":
        st.subheader("Create a New Account")
        new_username = st.text_input("Choose a username", key="new_username")
        new_password = st.text_input("Choose a password", type="password", key="new_password")
        confirm_password = st.text_input("Confirm password", type="password", key="confirm_password")
        if st.button("Register", type="primary"):
            if not new_username.strip() or not new_password:
                st.warning("Please fill in all fields.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_password) < 8:
                st.warning("Password must be at least 8 characters long.")
            elif register_user(new_username.strip(), new_password):
                st.success("Account created! Select Login to sign in.")
            else:
                st.error("That username already exists.")
    else:
        st.subheader("Login to Your Account")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", type="primary"):
            user_id = verify_user(username.strip(), password)
            if user_id:
                st.session_state["logged_in_user"] = user_id
                st.rerun()
            else:
                st.error("Incorrect username or password.")
    st.stop()

with st.sidebar:
    st.title("💳 WalletWise")
    st.caption("DIGITAL WALLET")
    st.divider()
    page = st.radio("NAVIGATION", ["Dashboard", "Add Money", "Send Money", "Transactions"], key="navigation")
    st.divider()
    st.caption("Demo Wallet")
    st.success("Wallet Active")
    if st.button("Log out"):
        st.session_state["logged_in_user"] = None
        st.rerun()

balance = get_balance()
transactions = get_transactions()
total_added = sum(t["Amount (₹)"] for t in transactions if t["Amount (₹)"] > 0)
total_sent = sum(-t["Amount (₹)"] for t in transactions if t["Amount (₹)"] < 0)

st.title("Welcome to WalletWise 👋")
st.write("Manage your demo wallet and track your transactions.")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💰 Wallet Balance", f"₹{balance:,.2f}")
with col2:
    st.metric("➕ Total Money Added", f"₹{total_added:,.2f}")
with col3:
    st.metric("💸 Total Money Sent", f"₹{total_sent:,.2f}")
st.divider()


if page == "Dashboard":
    st.subheader("Quick Actions")

    col1, col2 = st.columns(2)
    with col1:
        st.info("➕ Add money to your wallet")
        st.button("Go to Add Money", use_container_width=True, on_click=go_to_add_money)
    with col2:
        st.info("💸 Transfer demo money")
        st.button("Go to Send Money", use_container_width=True, on_click=go_to_send_money)
   
    st.subheader("📊 Money Added vs Money Sent")

    if transactions:
        chart_data = pd.DataFrame(transactions)

        chart_data["Amount (₹)"] = pd.to_numeric(
            chart_data["Amount (₹)"], errors="coerce"
        ).fillna(0)

        chart_data["Type"] = chart_data["Amount (₹)"].apply(
            lambda amount: "Money Added" if amount > 0 else "Money Sent"
        )

        chart_data["Amount (₹)"] = chart_data["Amount (₹)"].abs()

        chart_summary = chart_data.groupby("Type")["Amount (₹)"].sum()
        st.bar_chart(chart_summary)
    else:
        st.info("No transactions available for the chart.")

    
    st.subheader("📅 Monthly Spending")

    if transactions:
        monthly_data = pd.DataFrame(transactions)

        monthly_data["Date and Time"] = pd.to_datetime(
            monthly_data["Date and Time"], errors="coerce"
        )

        monthly_data["Amount (₹)"] = pd.to_numeric(
            monthly_data["Amount (₹)"], errors="coerce"
        ).fillna(0)

        monthly_data = monthly_data[
            (monthly_data["Amount (₹)"] < 0)
            & monthly_data["Date and Time"].notna()
        ].copy()

        if not monthly_data.empty:
            monthly_data["Month"] = (
                monthly_data["Date and Time"].dt.to_period("M").astype(str)
            )

            monthly_data["Amount (₹)"] = (
                monthly_data["Amount (₹)"].abs()
            )

            monthly_summary = (
                monthly_data.groupby("Month")["Amount (₹)"]
                .sum()
                .sort_index()
            )

            st.bar_chart(monthly_summary)
        else:
            st.info("No spending transactions available yet.")
    else:
        st.info("No transactions available yet.")

    
    st.subheader("🧾 Recent Transactions")

    transaction_filter = st.selectbox(
        "Filter transactions",
        ["All Transactions", "Money Added", "Money Sent"]
    )

    date_filter = st.selectbox(
        "Select Date Range",
        ["All Time", "Last 7 Days", "This Month"]
    )

    if transactions:
        filtered_transactions = transactions.copy()

        if date_filter != "All Time":
            today = pd.Timestamp.now().normalize()
            dated_transactions = []
            for t in filtered_transactions:
                transaction_date = pd.to_datetime(
                    t["Date and Time"], errors="coerce"
                )

                if pd.isna(transaction_date):
                    continue

                transaction_date = transaction_date.normalize()

                if date_filter == "Last 7 Days":
                    start_date = today - pd.Timedelta(days=6)
                    if start_date <= transaction_date <= today:
                        dated_transactions.append(t)
                elif date_filter == "This Month":
                    if (
                        transaction_date.year == today.year
                        and transaction_date.month == today.month
                    ):
                        dated_transactions.append(t)

            filtered_transactions = dated_transactions

        
            if transaction_filter == "Money Added":
                filtered_transactions = [
                    t for t in filtered_transactions
                    if t["Amount (₹)"] > 0
                ]
            elif transaction_filter == "Money Sent":
                filtered_transactions = [
                    t for t in filtered_transactions
                    if t["Amount (₹)"] < 0
                ]

        if filtered_transactions:
            st.dataframe(
                filtered_transactions[:5],
                use_container_width=True,
                hide_index=True
            )
            
            csv_data = pd.DataFrame(filtered_transactions).to_csv(
                index=False
            )

            st.download_button(
                label="📥 Download Transactions as CSV",
                data=csv_data,
                file_name="walletwise_transactions.csv",
                mime="text/csv"
            )

        else:
            st.info("No transactions found for this filter.")
    else:
        st.info("No transactions yet. Add demo money to get started.")


elif page == "Add Money":
    st.subheader("➕ Add Money")
    st.write("Add simulated funds to your demo wallet.")
    amount = st.number_input("Amount in rupees", min_value=0.0, step=100.0, key="deposit_amount")
    if st.button("Add Money", type="primary"):
        if amount > 0:
            add_money(amount)
            st.success(f"₹{amount:,.2f} added successfully!")
            st.rerun()
        else:
            st.warning("Enter an amount greater than zero.")
elif page == "Send Money":
    st.subheader("💸 Send Money")
    st.write("Transfer simulated funds to a demo receiver.")
    receiver = st.text_input("Receiver's name")
    amount = st.number_input("Transfer amount in rupees", min_value=0.0, step=100.0, key="transfer_amount")
    if st.button("Send Money", type="primary"):
        if not receiver.strip():
            st.warning("Enter the receiver's name.")
        elif amount <= 0:
            st.warning("Enter an amount greater than zero.")
        elif send_money(receiver.strip(), amount):
            st.success(f"₹{amount:,.2f} sent successfully!")
            st.rerun()
        else:
            st.error("Insufficient balance. Transfer not completed.")
elif page == "Transactions":
    st.subheader("📜 Transaction History")
    if transactions:
        st.dataframe(transactions, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions available yet.")

st.divider()
st.caption("WalletWise | Educational project using Python, Streamlit and SQLite. Simulated funds only — no real payments are processed.")
