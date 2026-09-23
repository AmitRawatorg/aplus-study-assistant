"""Small local authentication layer using streamlit-authenticator hashing."""

from __future__ import annotations

import re
import secrets

import streamlit as st
from streamlit_authenticator.utilities.hasher import Hasher

from database import create_user, get_user


USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,29}$")

BUTTON_CSS = """
<style>
.st-key-google_btn button, .st-key-apple_btn button {
    height: 3.2rem;
    border-radius: 10px;
    border: 1px solid #dadce0;
    background-color: #ffffff;
    box-shadow: none;
}
.st-key-google_btn button p, .st-key-apple_btn button p {
    font-size: 1.2rem;
    font-weight: 600;
    margin: 0;
    color: #3c4043;
}
.st-key-google_btn button:hover {
    background-color: #f7f8f8;
    border-color: #c6c9cc;
}
.st-key-google_btn button {
    background-repeat: no-repeat;
    background-position: 1.2rem center;
    background-size: 1.5rem;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'><path fill='%23EA4335' d='M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z'/><path fill='%234285F4' d='M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z'/><path fill='%23FBBC05' d='M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z'/><path fill='%2334A853' d='M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z'/></svg>");
}
</style>
"""


def validate_signup(username: str, name: str, password: str, confirmation: str) -> str | None:
    if not USERNAME_PATTERN.fullmatch(username.strip().lower()):
        return "Username must be 3–30 characters and use letters, numbers, dots, dashes, or underscores."
    if len(name.strip()) < 2:
        return "Please enter your name."
    if len(password) < 6:
        return "Password must be at least 6 characters."
    if password != confirmation:
        return "Passwords do not match."
    if get_user(username):
        return "That username is already registered."
    return None


def register_user(username: str, name: str, password: str, confirmation: str) -> tuple[bool, str]:
    error = validate_signup(username, name, password, confirmation)
    if error:
        return False, error
    password_hash = Hasher.hash(password)
    if not create_user(username, name, password_hash):
        return False, "That username is already registered."
    return True, "Account created. You can now log in."


def authenticate_user(username: str, password: str) -> tuple[bool, str]:
    user = get_user(username)
    if not user or not Hasher.check_pw(password, user["password_hash"]):
        return False, "Incorrect username or password."
    return True, user["name"]


def google_login_user() -> bool:
    """If Google login is done, fill session state and return True."""
    if not st.user.get("is_logged_in", False):
        return False
    email = (st.user.get("email") or "").strip().lower()
    if not email or not st.user.get("email_verified", True):
        return False
    name = st.user.get("name") or email.split("@")[0]
    if not get_user(email):
        # random password: nobody can log in with it, Google login only
        create_user(email, name, Hasher.hash(secrets.token_urlsafe(32)))
    st.session_state.authenticated = True
    st.session_state.username = email
    st.session_state.display_name = name
    return True


def sign_out() -> None:
    """Use this in app.py for the Log out button."""
    was_google = bool(st.user.get("is_logged_in", False))
    for key in ("authenticated", "username", "display_name"):
        st.session_state.pop(key, None)
    if was_google:
        st.logout()
    else:
        st.rerun()


def show_auth_screen() -> None:
    """Render login/signup and update session state when the user succeeds."""
    if google_login_user():
        st.rerun()

    st.title("A+ Study Assistant")
    st.caption("Founded by Amit Rawat · Learn smarter, not harder.")
    st.write("Your focused study companion for everyday learning.")

    st.markdown(BUTTON_CSS, unsafe_allow_html=True)
    if st.button("Continue with Google", key="google_btn", use_container_width=True):
        st.login()
    st.button("Continue with Apple (coming soon)", key="apple_btn",
              use_container_width=True, disabled=True)

    st.divider()
    login_tab, signup_tab = st.tabs(["Log in", "Create account"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g. amit.rawat")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if submitted:
            authenticated, result = authenticate_user(username, password)
            if authenticated:
                st.session_state.authenticated = True
                st.session_state.username = username.strip().lower()
                st.session_state.display_name = result
                st.rerun()
            st.error(result)

    with signup_tab:
        with st.form("signup_form"):
            name = st.text_input("Full name")
            username = st.text_input("Choose a username")
            password = st.text_input("Create a password", type="password")
            confirmation = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
        if submitted:
            created, message = register_user(username, name, password, confirmation)
            if created:
                st.success(message)
            else:
                st.error(message)