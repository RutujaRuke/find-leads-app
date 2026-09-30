from io import BytesIO
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from find_leads import business_row, search_places


load_dotenv()
configured_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
if configured_api_key.startswith("replace_with_"):
    configured_api_key = ""

st.set_page_config(page_title="Find Leads", page_icon="🔎", layout="wide")
st.title("Business Lead Finder")
st.caption("Search Google Places, review business details, and export your results.")

with st.sidebar:
    st.subheader("Google Places API")
    if configured_api_key:
        # Keep the server's key on the server; never send it to the browser.
        api_key = configured_api_key
        st.success("Using the API key configured on the server.")
    else:
        api_key = st.text_input(
            "API key",
            type="password",
            help="Your key is sent only to Google's Places API.",
        ).strip()
    st.caption("Enable Places API (New) and billing in the key's Google Cloud project.")

with st.form("lead_search"):
    query = st.text_input("Business search", placeholder="Hotels in Nashik")
    controls = st.columns([1, 1, 2])
    limit = controls[0].number_input("Maximum results", min_value=1, max_value=60, value=20)
    find_emails = controls[1].checkbox("Look for public website emails", value=True)
    submitted = controls[2].form_submit_button("Search", type="primary", use_container_width=True)

if submitted:
    if not api_key:
        st.error("Enter a Google Places API key in the sidebar before searching.")
    elif not query.strip():
        st.error("Enter a business and location to search, for example: hotels in Nashik.")
    else:
        try:
            with st.spinner("Searching Google Places and checking business websites..."):
                places = search_places(query.strip(), api_key, int(limit))
                rows = [business_row(place, find_emails=find_emails) for place in places]
                st.session_state["lead_results"] = pd.DataFrame(
                    rows,
                    columns=[
                        "Name", "Phone", "Email", "Address", "Website", 
                    ],
                )
                st.session_state["lead_query"] = query.strip()
        except Exception as error:
            st.error(str(error))
            if "API_KEY_INVALID" in str(error):
                st.info(
                    "Create or copy a valid key in Google Cloud Console. Confirm Places API (New) "
                    "is enabled, billing is attached, and API restrictions allow Places API."
                )

if "lead_results" in st.session_state:
    results = st.session_state["lead_results"]
    st.subheader(f"Results for {st.session_state['lead_query']}")
    if results.empty:
        st.info("No businesses were returned for this search. Try a broader phrase or another location.")
    else:
        st.caption(f"{len(results)} businesses found. Email addresses are best-effort and may be missing.")
        st.dataframe(results, use_container_width=True, hide_index=True, column_config={
            "Website": st.column_config.LinkColumn("Website"),
        })
        workbook = BytesIO()
        results.to_excel(workbook, index=False, engine="openpyxl")
        st.download_button(
            "Download Excel",
            data=workbook.getvalue(),
            file_name="business_leads.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

st.divider()
st.caption(
    "Google Places does not provide email addresses. This app checks public pages on business "
    "websites when enabled. API usage may incur Google charges; review Google Maps Platform terms."
)