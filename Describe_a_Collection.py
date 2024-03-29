#!/usr/bin/env python

import streamlit as st
import streamlit.components.v1 as components
from streamlit_extras.switch_page_button import switch_page

from lib import init_page, value_or_default, SITE_ID, load_stored_data, PREFIX, load_files, MODE, MODE_CREATE, \
    MODE_EDIT, FORMAT

init_page("WP11 Demo")

st.session_state[MODE] = st.selectbox("What would you like to do?", (MODE_CREATE, MODE_EDIT),
                    format_func=lambda v: "Create New Publication" if v == MODE_CREATE else "Edit Existing Publication",
                    index=0 if SITE_ID not in st.session_state else 1,
                    on_change=lambda: st.session_state.pop(PREFIX, None))

if st.session_state[MODE] == MODE_CREATE:
    st.session_state.clear()
    dataset_options = [""] + list(st.secrets.datasets.keys())
    selected = 0 if PREFIX not in st.session_state else dataset_options.index(st.session_state[PREFIX])
    dataset = st.selectbox("Select a test dataset:",
                           dataset_options,
                           format_func=lambda s: st.secrets.datasets[s].name if s else "---",
                           index=selected,
                           help="These datasets consist of files that have been uploaded to a specific Cloud storage "
                                "location that this demo tool can access. It is not currently possible to upload "
                                "additional datasets via this tool.")
    if dataset:
        st.session_state[PREFIX] = dataset
        st.session_state[FORMAT] = st.secrets.datasets[dataset].format
    else:
        st.session_state.pop(PREFIX, None)
        st.session_state.pop(FORMAT, None)
else:
    st.markdown("#### Add identifier key:")
    st.session_state[SITE_ID] = st.text_input("Enter the site ID given when you published this site:",
                                              help="This is typically a string beginning with 'E'",
                                              value=value_or_default(SITE_ID, default=''))
    if SITE_ID in st.session_state and st.session_state[SITE_ID]:
        info = load_stored_data(st.session_state[SITE_ID])
        st.markdown(f"Editing site at [{info.url()}]({info.url()})")

if PREFIX in st.session_state and st.session_state[PREFIX]:
    items = load_files(st.session_state.get(PREFIX))
    st.markdown(f"### Items found: {len(items)}")

    view = """<style>body { font-family: sans-serif; } a { color: #771646} </style>"""
    view += """<div style="display: grid; grid-gap: 1rem; grid-template-columns: 1fr 1fr 1fr 1fr">"""
    for i, (key, url, thumb_url) in enumerate(items):
        view += "<div>"
        view += f"""<a href="{url}" target="_blank">
    <img src="{thumb_url}" width="75" height="100" alt="{key}"  style="border: 1px solid #ccc"/></a>
    """
        view += f"""<a href="{url}" target="_blank">
    <h5>{key}</h5></a>
    """
        view += "</div>"
    view += "</div>"

    components.html(view, height=400, scrolling=True)
else:
    st.write("### No dataset selected")

st.divider()
if st.button("Next: Enter Basic Identifying Information"):
    switch_page("Identifying Information")
