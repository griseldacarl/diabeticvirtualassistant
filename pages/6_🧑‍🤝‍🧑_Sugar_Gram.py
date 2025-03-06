import streamlit as st
import os

st.set_page_config("Sugar Grame", page_icon=":material/share:", layout="centered")
os.environ.get("BASE_API_URL")
st.page_link("http://192.168.6.176:3001",label="SugarGram",icon=":material/share:")