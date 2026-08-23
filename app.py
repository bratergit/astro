import streamlit as st
from datetime import datetime
import pandas as pd

from synthesis_engine import (
    calculate_biorhythms,
    calculate_name_number,
    find_nearest_ley_line,
    analyze_palm_image,
    synthesize_profile,
)

st.set_page_config(page_title="Synthesis Profile", page_icon="✨", layout="centered")

st.title("✨ Synthesis Profile")
st.caption(
    "Numerology + biorhythms + ley-line proximity + a right-hand photo heuristic, "
    "blended into a fun, non-scientific personal profile."
)

with st.form("profile_form"):
    st.subheader("Your details")

    name = st.text_input("Full name", value="Adalberto Brant")
    birthdate = st.date_input(
        "Birthdate",
        value=datetime(1995, 6, 15),
        min_value=datetime(1900, 1, 1),
        max_value=datetime.now(),
    )

    st.subheader("Location")
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("Latitude", value=-18.9186, format="%.4f")
    with col2:
        lon = st.number_input("Longitude", value=-48.2772, format="%.4f")

    st.subheader("Right hand photo")
    st.caption("Upload a clear photo of your **right** palm, facing the camera.")
    palm_file = st.file_uploader("Right hand photo", type=["jpg", "jpeg", "png"])

    manual_override = st.checkbox("I'd rather set my heart-line type manually")
    heart_line_type = None
    if manual_override:
        heart_line_type = st.selectbox(
            "Heart line type",
            ["Curved/Deep", "Curved/Shallow", "Straight/Deep", "Straight/Shallow"],
        )

    is_single = st.checkbox("Generate a soulmate profile (I'm single)", value=True)

    submitted = st.form_submit_button("Generate profile")

if submitted:
    if not manual_override and palm_file is None:
        st.error("Upload a right-hand photo, or check the manual override box.")
        st.stop()

    with st.spinner("Synthesizing..."):
        palm_preview = None
        if palm_file is not None:
            palm_file.seek(0)
            palm_preview = palm_file
            palm_file.seek(0)

        try:
            profile = synthesize_profile(
                name=name,
                birthdate_str=birthdate.strftime("%Y-%m-%d"),
                lat=lat,
                lon=lon,
                is_single=is_single,
                heart_line_type=heart_line_type,
                palm_image_path=palm_file if not manual_override else None,
            )
        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.stop()

    st.success("Profile generated.")

    if palm_preview is not None:
        st.image(palm_preview, caption="Uploaded right hand", width=250)

    st.header(f"{profile['user_name']}'s Profile")

    c1, c2, c3 = st.columns(3)
    c1.metric("Numerology number", profile["numerology_number"])
    c2.metric("Planetary ruler", profile["planetary_ruler"])
    c3.metric("Heart line", profile["palmistry_heart_line"])

    if "palm_image_analysis" in profile:
        with st.expander("Palm photo analysis details"):
            pa = profile["palm_image_analysis"]
            st.write(f"**Curvature ratio:** {pa['curvature_ratio']}")
            st.write(f"**Depth score:** {pa['depth_score']}")
            st.write(f"**Dominant aura color:** {pa['dominant_aura_color']}")
            st.caption(pa["note"])

    st.subheader("Biorhythms today")
    bio = profile["biorhythms_current"]
    bio_df = pd.DataFrame(
        {"Cycle": list(bio.keys()), "Value": list(bio.values())}
    ).set_index("Cycle")
    st.bar_chart(bio_df)

    st.subheader("Geospatial")
    st.write(f"**Nearest ley node:** {profile['nearest_ley_node']}")
    st.write(f"**Astrocartography influence:** {profile['astrocartography_influence']}")

    if "soulmate_profile" in profile:
        st.subheader("💫 Soulmate profile")
        sp = profile["soulmate_profile"]
        st.write(f"**Archetype:** {sp['archetype']}")
        st.write(f"**Key traits:** {sp['key_traits']}")
        st.write(f"**Ideal meeting location:** {sp['ideal_meeting_location']}")
        st.write(f"**Biorhythmic readiness:** {sp['biorhythmic_readiness']}")

    with st.expander("Raw profile JSON"):
        st.json(profile)

st.divider()
st.caption(
    "For entertainment purposes only. Numerology, ley lines, astrocartography, and "
    "palmistry (including the photo heuristic above) have no established scientific "
    "predictive validity."
)
