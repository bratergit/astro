import streamlit as st
from datetime import datetime
import pandas as pd

from synthesis_engine import (
    calculate_biorhythms,
    calculate_name_number,
    calculate_expression_number,
    calculate_chinese_zodiac,
    find_nearest_ley_line,
    analyze_palm_image,
    synthesize_profile,
    get_name_meaning,
    get_location_meaning,
)
from astrocartography import (
    julian_day_utc,
    best_places_to_live,
    format_line_label,
    PLANETS,
    FAVORABLE_PLANETS,
    PLANET_MEANINGS,
)

st.set_page_config(page_title="Synthesis Profile", page_icon="✨", layout="centered")

st.title("✨ Synthesis Profile")

tab_profile, tab_astro = st.tabs(["Perfil de Síntese", "🌍 Astrocartografia"])

# ============================================================
# TAB 1 — Original synthesis profile (numerology + biorhythms +
# ley lines + right-hand photo)
# ============================================================
with tab_profile:
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

# ============================================================
# TAB 2 — Astrocartografia
# ============================================================
with tab_astro:
    st.header("Astrocartografia")
    st.write(
        "Descubra os 3 melhores locais para você morar no mundo, traçados pelas "
        "linhas planetárias do seu mapa de nascimento."
    )

    col_p1, col_p2 = st.columns(2)

    with col_p1:
        st.subheader("Pessoa 1 (principal)")
        astro_name1 = st.text_input(
            "Nome completo", value="Adalberto Caldeira Brant Filho", key="astro_name1"
        )
        astro_bd1 = st.date_input(
            "Data de nascimento",
            value=datetime(1995, 6, 15),
            min_value=datetime(1900, 1, 1),
            max_value=datetime.now(),
            key="astro_bd1",
        )

    with col_p2:
        st.subheader("Pessoa 2 (opcional — análise de casal)")
        include_partner = st.checkbox("Incluir parceiro(a)", value=False, key="include_partner")
        astro_name2 = st.text_input(
            "Nome do parceiro(a)", value="", key="astro_name2", disabled=not include_partner
        )
        astro_bd2 = st.date_input(
            "Data de nascimento",
            value=datetime(1995, 6, 15),
            min_value=datetime(1900, 1, 1),
            max_value=datetime.now(),
            key="astro_bd2",
            disabled=not include_partner,
        )

    correlate_meaning = st.checkbox(
        "Correlacionar com o significado do nome e do local", value=False, key="correlate_meaning"
    )

    st.caption(
        "Cálculo baseado nas posições planetárias no instante do nascimento "
        "(meio-dia UTC quando o horário não é informado). As linhas mostram onde "
        "cada planeta está angular (Ascendente, Meio-Céu, Fundo do Céu e "
        "Descendente). Locais sob linhas benéficas — Vênus, Júpiter, Sol e Lua — "
        "tendem a ser mais favoráveis."
    )

    # planet legend row
    legend_cols = st.columns(len(PLANETS))
    for col, planet in zip(legend_cols, PLANETS.keys()):
        marker = "🟢" if planet in FAVORABLE_PLANETS else "⚪"
        col.markdown(f"{marker} **{planet}**")

    astro_submit = st.button("Calcular astrocartografia", type="primary")

    if astro_submit:
        if not astro_name1.strip():
            st.error("Informe o nome completo da Pessoa 1.")
            st.stop()

        with st.spinner("Calculando posições planetárias e traçando linhas..."):
            birth1 = datetime(astro_bd1.year, astro_bd1.month, astro_bd1.day)
            jd1 = julian_day_utc(birth1)

            jd2 = None
            if include_partner and astro_name2.strip():
                birth2 = datetime(astro_bd2.year, astro_bd2.month, astro_bd2.day)
                jd2 = julian_day_utc(birth2)

            places = best_places_to_live(jd1, top_n=3, jd_ut_partner=jd2)

            exp_number, exp_meaning = calculate_expression_number(astro_name1)
            zodiac = calculate_chinese_zodiac(birth1)
            bio_today = calculate_biorhythms(birth1, datetime.now())

            name_meaning = get_name_meaning(astro_name1) if correlate_meaning else None

        st.success("Cálculo concluído.")

        # --- Profile summary ---
        st.subheader(f"Perfil de {astro_name1}")
        st.caption("Análise onomástica e biorritmo")

        st.metric(f"Número de Expressão {exp_number}", exp_meaning)
        st.write(f"**Horóscopo chinês:** {zodiac['label']} — {zodiac['traits']}")

        if name_meaning is not None:
            with st.expander("Significado do nome"):
                if name_meaning["success"]:
                    st.write(name_meaning["text"])
                else:
                    st.warning(name_meaning["text"])

        bc1, bc2, bc3 = st.columns(3)
        bc1.metric("Físico", f"{round((bio_today['physical'] + 1) / 2 * 100)}%")
        bc2.metric("Emocional", f"{round((bio_today['emotional'] + 1) / 2 * 100)}%")
        bc3.metric("Intelectual", f"{round((bio_today['intellectual'] + 1) / 2 * 100)}%")

        st.divider()

        # --- Top 3 places ---
        for i, place in enumerate(places, start=1):
            st.markdown(f"### {i}. {place['name']}")
            st.caption(place["country"])

            if place["favorable_lines_p1"]:
                st.write("**Linhas favoráveis:**")
                for line in place["favorable_lines_p1"]:
                    label = format_line_label(line["planet"], line["angle"])
                    meaning = PLANET_MEANINGS.get(line["planet"], "")
                    st.markdown(f"- **{label}** ({round(line['distance_km'])} km) — {meaning}")
            else:
                st.caption("Nenhuma linha benéfica próxima dentro do raio considerado.")

            if jd2 is not None and place["favorable_lines_p2"]:
                partner_label = astro_name2 or "parceiro(a)"
                st.write(f"**Linhas favoráveis para {partner_label}:**")
                for line in place["favorable_lines_p2"]:
                    label = format_line_label(line["planet"], line["angle"])
                    meaning = PLANET_MEANINGS.get(line["planet"], "")
                    st.markdown(f"- **{label}** ({round(line['distance_km'])} km) — {meaning}")

            if correlate_meaning:
                with st.expander(f"Significado de {place['name']}"):
                    loc_meaning = get_location_meaning(place["name"])
                    if loc_meaning["success"]:
                        st.write(loc_meaning["text"])
                    else:
                        st.warning(loc_meaning["text"])

            st.divider()

    st.caption(
        "A astrocartografia é uma técnica astrológica sem validade científica "
        "comprovada. Este cálculo usa posições planetárias reais (efeméride "
        "Moshier) e é apresentado apenas para fins de entretenimento."
    )
