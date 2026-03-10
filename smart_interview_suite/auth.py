import streamlit as st
from models import SessionLocal, User


def login():
    st.sidebar.subheader("Login")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    role = st.sidebar.selectbox("Role", ["ADMIN", "INTERVIEWER", "CANDIDATE"])

    if st.sidebar.button("Login"):
        db = SessionLocal()
        user = (
            db.query(User)
            .filter(
                User.email == email,
                User.password == password,
                User.role == role,
            )
            .first()
        )
        db.close()
        if user:
            st.session_state["user"] = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
            }
            st.sidebar.success(f"Logged in as {user.name} ({user.role})")
        else:
            st.sidebar.error("Invalid credentials")

    if "user" in st.session_state:
        if st.sidebar.button("Logout"):
            st.session_state.pop("user")
            st.rerun()


def require_role(roles):
    user = st.session_state.get("user")
    return user and user["role"] in roles
