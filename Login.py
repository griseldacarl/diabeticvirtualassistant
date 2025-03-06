import os

import firebase_admin
import pandas as pd
import requests as http_requests
import streamlit as st
from firebase_admin import auth, credentials, firestore

st.set_page_config("Login", page_icon=":material/login:", layout="centered")

FILE_PATH_ICON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "/icons/Assets.xcassets/AppIcon.appiconset/180.png",
)


FILE_PATH_SERVICEACCOUNTKEY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "diabeticvirtualassistant-firebase-adminsdk-fbsvc-b7c63be69b.json",
)


try:
    app = firebase_admin.get_app()
except ValueError:
    st.session_state.cred = credentials.Certificate(FILE_PATH_SERVICEACCOUNTKEY)
    firebase_admin.initialize_app(st.session_state.cred)

db = firestore.client()  # Example for Firesto


def login(email):
    try:
        user = auth.get_user_by_email(email)
        # Sign in user with email and password
        # Set user data in session state
        st.session_state["user"] = user
        st.success("Logged in successfully!")
        return True
    except Exception as e:
        st.error(f"Login failed: {e}")
        return False


def main():

    st.title("Can you give me your email? I need to know who you are.")
    if "user" not in st.session_state:
        email = st.text_input("Email", placeholder="Please give email...")

        if st.button(
            "Login", icon=":material/login:", type="primary", use_container_width=True
        ):
            if login(email):
                st.rerun()
    else:
        if st.session_state.get("user"):
            st.write(f"Welcome, {st.session_state['user'].email}!")
            # Display protected content
            # Load all of data from database here!!

            if "users" not in st.session_state:
                st.session_state.users = []
                users_ref = db.collection("users")
                for doc in users_ref.stream():
                    userid = {"userid": doc.id}
                    user = {**userid, **doc.to_dict()}
                    st.session_state.users.append(user)

            if "current_user" not in st.session_state and st.session_state.get("user"):
                st.session_state.current_user = [
                    usr
                    for usr in st.session_state.users
                    if usr.get("email") == st.session_state["user"].email
                ]

            if "userid" not in st.session_state and "current_user" in st.session_state:
                st.session_state.userid = st.session_state.current_user[0].get("userid")

            if "glucose_data" not in st.session_state:
                st.session_state.glucose_data = pd.DataFrame()
                bloodsugar_ref = db.collection("bloodsugars")

                for doc in bloodsugar_ref.stream():
                    bloodsugarid = {"bloodsugarid": doc.id}
                    bloodsugar = {**bloodsugarid, **doc.to_dict()}
                    bloodsugar_df = pd.DataFrame(
                        {
                            "Timestamp": [bloodsugar.get("timestamp")],
                            "Glucose Level": [bloodsugar.get("bloodsugar")],
                        }
                    )
                    
                    if st.session_state.userid == bloodsugar.get("userid"):
                        st.session_state.glucose_data = pd.concat(
                            [st.session_state.glucose_data, bloodsugar_df],
                            ignore_index=True,
                        )

            if "weight_data" not in st.session_state:
                st.session_state.weight_data = pd.DataFrame()
                weight_ref = db.collection("weights")
                for doc in weight_ref.stream():
                    weightid = {"weightid":doc.id}
                    weight ={**weightid,**doc.to_dict()}
                    weight_df = pd.DataFrame(
                        {"Timestamp":[weight.get("timestamp")],"Weight":[weight.get("weight")]}
                    )

                    if st.session_state.userid == weight.get("userid"):
                        st.session_state.weight_data = pd.concat(
                            [st.session_state.weight_data, weight_df],
                            ignore_index=True,
                        )


            st.write(
                "You should be able to access the content that needed a login. Thanks!"
            )

        else:
            st.warning("Please log in to access this content.")

        if st.button(
            "Logout", icon=":material/logout:", type="primary", use_container_width=True
        ):
            del st.session_state["user"]
            del st.session_state.current_user
            del st.session_state.userid
            del st.session_state.glucose_data
            del st.session_state.weight_data

            st.rerun()


if __name__ == "__main__":
    main()
