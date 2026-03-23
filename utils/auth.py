import streamlit as st
import hmac
import os


def _get_users():
    try:
        users = {}
        for username, info in st.secrets["users"].items():
            users[username] = {"password": info["password"], "role": info["role"]}
        return users
    except Exception:
        return {
            "admin":  {"password": "silverwatch_admin_2024", "role": "admin"},
            "viewer": {"password": "silverwatch_2024",        "role": "viewer"},
        }


def check_password(username: str, password: str) -> bool:
    users = _get_users()
    user  = users.get(username)
    if not user:
        return False
    return hmac.compare_digest(password, user["password"])


def get_role() -> str:
    return st.session_state.get("role", "")


def is_admin() -> bool:
    return get_role() == "admin"


def require_login():
    if st.session_state.get("authenticated"):
        return

    # Show Maiora logo + SILVERWATCH in fixed header on login page too
    from utils.ui import _fixed_header_html, LAYOUT_CSS
    st.markdown(LAYOUT_CSS, unsafe_allow_html=True)
    st.markdown(_fixed_header_html("logo_maiora.png", "", ""), unsafe_allow_html=True)

    # Silversea logo left-aligned above login form
    if os.path.exists("logo.png"):
        st.image("logo.png", width=160)

    st.title("SilverWatch — Login")
    st.markdown("Please enter your credentials to access the dashboard.")

    with st.form("login_form"):
        username  = st.text_input("Username")
        password  = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        if check_password(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"]      = username
            st.session_state["role"]          = _get_users()[username]["role"]
            st.rerun()
        else:
            st.error("Incorrect username or password.")

    st.stop()


def logout_button():
    st.sidebar.divider()
    user = st.session_state.get("username", "")
    role = st.session_state.get("role", "")
    st.sidebar.caption(f"Logged in as **{user}** ({role})")
    if st.sidebar.button("Log out"):
        for key in ["authenticated", "username", "role"]:
            st.session_state.pop(key, None)
        st.rerun()
