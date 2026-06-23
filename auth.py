import streamlit as st

def show_login():
    st.markdown("## 🏐 Federico Roberti — Lab 2026")
    st.markdown("### Accedi")

    role = st.radio("Accedi come", ["Allenatore", "Federico"], horizontal=True)

    if role == "Allenatore":
        pwd = st.text_input("Password", type="password")
        if st.button("Accedi", type="primary"):
            if pwd == st.secrets["auth"]["admin_password"]:
                st.session_state["role"] = "admin"
                st.rerun()
            else:
                st.error("Password non corretta.")
    else:
        pin = st.text_input("PIN", type="password", max_chars=6)
        if st.button("Accedi", type="primary"):
            if pin == st.secrets["auth"]["player_pin"]:
                st.session_state["role"] = "player"
                st.rerun()
            else:
                st.error("PIN non corretto.")

def require_login():
    if "role" not in st.session_state:
        show_login()
        st.stop()

def require_admin():
    require_login()
    if st.session_state.get("role") != "admin":
        st.error("Accesso riservato all'allenatore.")
        st.stop()

def logout_button():
    if st.sidebar.button("🚪 Logout"):
        st.session_state.pop("role", None)
        st.rerun()

def is_admin():
    return st.session_state.get("role") == "admin"
