import streamlit as st
from streamlit_extras.switch_page_button import switch_page

from lib import init_page, value_or_default, HOLDER, STREET, POSTCODE

st.set_page_config(page_title="Enter Contextual Info")

init_page()

st.write("## Context information")

st.write("Information about where the collection is kept and who is responsible for it.")

st.session_state[HOLDER] = st.text_input("Name of Custodian",
              help="The name of the person responsible for custody of this collection",
              value=value_or_default(HOLDER))

st.session_state[STREET] = st.text_input("Street address",
              help="The address where this collection is held",
              value=value_or_default(STREET))

st.session_state[POSTCODE] = st.text_input("Postal code",
              help="The postal code where this collection is located",
              value=value_or_default(POSTCODE))

col1, col2 = st.columns(2)
if col1.button("Back"):
    switch_page("Identifying Information")
if col2.button("Next"):
    switch_page("Descriptive Information")
