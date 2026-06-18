import streamlit as st

def show_landing():
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("✈️ TripTailor")
        st.subheader("Your journey, tailored by AI")

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### Why TripTailor?")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.info("🤖 **AI Planning**\n\nJust describe your dream trip in plain words")

    with col2:
        st.success("🧠 **Learns You**\n\nGets smarter with every thumbs up or down")

    with col3:
        st.warning("🗺️ **Visual Maps**\n\nSee your full route come alive on a map")

    with col4:
        st.error("💬 **Mid-trip Help**\n\nChange plans on the go with AI assistance")

    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)