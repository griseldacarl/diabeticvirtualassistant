import os

import streamlit as st

st.set_page_config("Sugar Grame", page_icon=":material/share:", layout="centered")
os.environ.get("BASE_API_URL")
st.page_link("http://147.182.203.196:3001", label="SugarGram", icon=":material/share:")
