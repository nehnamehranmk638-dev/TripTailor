import streamlit as st
from frontend.api import signup, login, get_countries

def show_auth():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Login", "✨ Sign Up"])

        with tab1:
            st.markdown("### Welcome back!")
            username = st.text_input("Username", key="login_user",
                                    placeholder="Your username")
            password = st.text_input("Password", type="password",
                                    key="login_pass",
                                    placeholder="Your password")
            if st.button("Login →", type="primary",
                        use_container_width=True, key="login_btn"):
                if not username.strip() or not password.strip():
                    st.error("Please fill in all fields")
                else:
                    with st.spinner("Logging in..."):
                        result = login(username.strip(), password.strip())
                    if result.get("message") == "Login successful":
                        st.session_state.username = result["username"]
                        st.session_state.country = result.get("country", "India")
                        st.session_state.currency_code = result.get("currency_code", "INR")
                        st.session_state.currency_symbol = result.get("currency_symbol", "₹")
                        st.session_state.travel_personality = result.get("travel_personality", "Explorer")
                        st.session_state.category_weights = result.get("category_weights", {})
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('detail', 'Login failed')}")

        with tab2:
            st.markdown("### Create your account")
            new_username = st.text_input("Choose username", key="signup_user",
                                        placeholder="e.g. nehna123")
            new_password = st.text_input("Choose password", type="password",
                                        key="signup_pass",
                                        placeholder="Min 6 characters")
            confirm_password = st.text_input("Confirm password", type="password",
                                            key="signup_confirm",
                                            placeholder="Repeat password")

            countries = get_countries()
            country_names = [c["country"] for c in countries]
            selected_country = st.selectbox("Your country", country_names,
                                           index=country_names.index("India")
                                           if "India" in country_names else 0,
                                           key="signup_country")

            if st.button("Create Account →", type="primary",
                        use_container_width=True, key="signup_btn"):
                if not new_username.strip() or not new_password.strip():
                    st.error("Please fill in all fields")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    with st.spinner("Creating account..."):
                        result = signup(new_username.strip(),
                                       new_password.strip(),
                                       selected_country)
                    if result.get("message") == "Account created":
                        st.success("✅ Account created! Please login.")
                    else:
                        st.error(f"❌ {result.get('detail', 'Signup failed')}")