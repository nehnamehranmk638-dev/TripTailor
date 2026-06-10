import streamlit as st

def show_landing():
    st.markdown("""
    <style>
    .landing-container {
        text-align: center;
        padding: 60px 20px;
    }
    .landing-title {
        font-size: 72px;
        font-weight: 300;
        font-family: Georgia, serif;
        color: #2C3E50;
        margin-bottom: 0;
        letter-spacing: -2px;
    }
    .landing-subtitle {
        font-size: 20px;
        color: #7F8C8D;
        margin-bottom: 40px;
        font-style: italic;
    }
    .feature-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin: 8px;
        border: 1px solid #ECF0F1;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="landing-container">
            <div class="landing-title">✈️ TripTailor</div>
            <div class="landing-subtitle">Your journey, tailored by AI</div>
        </div>
        """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    features = [
        ("🤖", "AI Planning", "Just describe your dream trip"),
        ("🧠", "Learns You", "Gets smarter with every feedback"),
        ("🗺️", "Visual Maps", "See your route come alive"),
        ("💬", "Mid-trip Help", "Change plans on the go")
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3, col4], features):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div style="font-size:32px">{icon}</div>
                <div style="font-weight:600; margin:8px 0">{title}</div>
                <div style="font-size:13px; color:#7F8C8D">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)