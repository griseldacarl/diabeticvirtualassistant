import os
from datetime import datetime

import firebase_admin
import pandas as pd
import streamlit as st
from firebase_admin import auth, credentials, firestore

st.set_page_config(
    "Settings", page_icon=":material/manage_accounts:", layout="centered"
)

FILE_PATH_SERVICEACCOUNTKEY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "diabeticvirtualassistant-firebase-adminsdk-fbsvc-b7c63be69b.json",
)


try:
    app = firebase_admin.get_app()
except ValueError:
    st.session_state.cred = credentials.Certificate(FILE_PATH_SERVICEACCOUNTKEY)
    firebase_admin.initialize_app(st.session_state.cred)

if "users_df" not in st.session_state:
    st.session_state.users_df = None

if "selected_user" not in st.session_state:
    st.session_state.selected_user = None


if "delete_button_status" not in st.session_state:
    st.session_state.delete_button_status = True


def handle_user_table_selected():
    if st.session_state.get("user_dataframe").get("selection").get("rows") != []:
        st.session_state.selected_user = st.session_state.users_df.iloc[
            st.session_state.get("user_dataframe").get("selection").get("rows")[0]
        ]
        st.session_state.delete_button_status = False
    else:
        st.session_state.delete_button_status = True
    # st.write(st.session_state.selected_user.loc["Name"])
    # st.write(st.session_state.selected_user.loc["Email"])


db = firestore.client()  # Firestore

if "users" not in st.session_state:
    st.session_state.users = []
    users_ref = db.collection("users")
    for doc in users_ref.stream():
        userid = {"userid": doc.id}
        user = {**userid, **doc.to_dict()}
        st.session_state.users.append(user)

st.title("Here are few housekeeping items that we need to get done:")
with st.expander("Users (Diabetics)", icon=":material/group:"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button(
            "", icon=":material/delete:", disabled=st.session_state.delete_button_status
        ):
            if (
                st.session_state.get("user_dataframe").get("selection").get("rows")
                != []
            ):
                st.session_state.selected_user = st.session_state.users_df.iloc[
                    st.session_state.get("user_dataframe")
                    .get("selection")
                    .get("rows")[0]
                ]
                # st.write(st.session_state.selected_user.loc["Email"])
                for usr in st.session_state.users:
                    if usr.get("email") == st.session_state.selected_user.loc["Email"]:
                        db.collection("users").document(usr.get("userid")).delete()
                st.session_state.delete_button_status = True
                st.rerun()

    users_ref = db.collection("users")
    st.session_state.users = []
    st.session_state.users_df = pd.DataFrame()
    for doc in users_ref.stream():
        userid = {"userid": doc.id}
        user = {**userid, **doc.to_dict()}
        st.session_state.users.append(user)
        new_user_df = pd.DataFrame(
            {"Name": [user.get("displayName")], "Email": [user.get("email")]}
        )
        st.session_state.users_df = pd.concat(
            [st.session_state.users_df, new_user_df], ignore_index=True
        )

    st.dataframe(
        st.session_state.users_df,
        use_container_width=True,
        selection_mode="single-row",
        hide_index=True,
        on_select=handle_user_table_selected,
        key="user_dataframe",
    )

    if "user_firstname" not in st.session_state:
        st.session_state.user_firstname = None

    if "user_lastname" not in st.session_state:
        st.session_state.user_lastname = None

    if "user_email" not in st.session_state:
        st.session_state.user_email = None

    if "user_age" not in st.session_state:
        st.session_state.user_age = None

    if "user_height" not in st.session_state:
        st.session_state.user_height = None

    if "user_gender" not in st.session_state:
        st.session_state.user_gender = "Other"

    if "user_notes" not in st.session_state:
        st.session_state.user_notes = None

    user_firstname = st.text_input(
        "First Name",
        placeholder="Enter your first name...",
        value=st.session_state.user_firstname,
    )
    user_lastname = st.text_input(
        "Last Name",
        placeholder="Enter your last name...",
        value=st.session_state.user_lastname,
    )
    user_displayName = f"{user_firstname} {user_lastname}"
    user_email = st.text_input(
        "Email:", placeholder="Enter email..", value=st.session_state.user_email
    )
    user_height = st.text_input(
        "Height:", placeholder="Enter your height..", value=st.session_state.user_height
    )
    user_age = st.number_input(
        "Enter age:",
        step=1,
        value=st.session_state.user_age,
    )
    options = ["Male", "Female", "Other"]
    user_gender = st.radio("Gender", options)

    user_activity = st.select_slider(
        "What is your activity level?",
        options=[
            "little to no exercise",
            "light exercise 1-3 times per week",
            "moderate exercise 3-5 times per week",
            "heavy physical exercise 5-6 times per week",
            "heavy physical exercise 6-7 times per week",
        ],
    )
    st.write("Ok, so you are ", user_activity)
    user_notes = st.text_area(
        "What are your physical and mental limitations? Is this your first time exercise? What is your experience?",
        value=st.session_state.user_notes,
    )
    user_manager_submitted = st.button(
        "Add User",
        icon=":material/group_add:",
        type="primary",
        use_container_width=True,
    )

    if user_manager_submitted:
        new_user = {
            "firstname": user_firstname,
            "lastname": user_lastname,
            "displayName": user_displayName,
            "email": user_email,
            "age": user_age,
            "height": user_height,
            "gender": user_gender,
            "activity": user_activity,
            "notes": user_notes,
        }

        db.collection("users").add(new_user)

        st.session_state.user_firstname = ""
        st.session_state.user_lastname = ""
        st.session_state.user_height = ""
        st.session_state.user_email = ""
        st.session_state.user_notes = ""
        st.session_state.user_age = 0

        st.rerun()
