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
            with st.spinner(
                f"Loading Profile for {st.session_state['user'].email} ...",
                show_time=True,
            ):
                if "users" not in st.session_state:
                    st.session_state.users = []
                    users_ref = db.collection("users")
                    for doc in users_ref.stream():
                        userid = {"userid": doc.id}
                        user = {**userid, **doc.to_dict()}
                        st.session_state.users.append(user)

                if "current_user" not in st.session_state and st.session_state.get(
                    "user"
                ):
                    st.session_state.current_user = [
                        usr
                        for usr in st.session_state.users
                        if usr.get("email") == st.session_state["user"].email
                    ]

                if (
                    "userid" not in st.session_state
                    and "current_user" in st.session_state
                ):
                    st.session_state.userid = st.session_state.current_user[0].get(
                        "userid"
                    )

                if "glucose_data" not in st.session_state:
                    st.session_state.glucose_data = pd.DataFrame()
                    bloodsugar_ref = db.collection("bloodsugars")

                    for doc in bloodsugar_ref.stream():
                        bloodsugarid = {"bloodsugarid": doc.id}
                        bloodsugar = {**bloodsugarid, **doc.to_dict()}
                        bloodsugar_df = pd.DataFrame(
                            {
                                "DateTime": [bloodsugar.get("DateTime")],
                                "BloodSugarLevel(mg/dl)": [
                                    bloodsugar.get("BloodSugarLevel(mg/dl)")
                                ],
                                "userid": [bloodsugar.get("userid")],
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
                        weightid = {"weightid": doc.id}
                        weight = {**weightid, **doc.to_dict()}
                        weight_df = pd.DataFrame(
                            {
                                "Date": [weight.get("Date")],
                                "Weight": [weight.get("Weight(pounds)")],
                                "userid": [weight.get("userid")],
                            }
                        )

                        if st.session_state.userid == weight.get("userid"):
                            st.session_state.weight_data = pd.concat(
                                [st.session_state.weight_data, weight_df],
                                ignore_index=True,
                            )

                if "exercise_data" not in st.session_state:
                    st.session_state.exercise_data = pd.DataFrame()
                    exercise_ref = db.collection("exercises")
                    for doc in exercise_ref.stream():
                        exerciseid = {"exerciseid": doc.id}
                        exercise = {**exerciseid, **doc.to_dict()}
                        exercise_df = pd.DataFrame(
                            {
                                "Date": [exercise.get("Date")],
                                "Exercise": [exercise.get("Exercise")],
                                "Reps": [exercise.get("Reps")],
                                "Sets": [exercise.get("Sets")],
                            }
                        )
                        if st.session_state.userid == exercise.get("userid"):
                            st.session_state.exercise_data = pd.concat(
                                [st.session_state.exercise_data, exercise_df],
                                ignore_index=True,
                            )

                if "food_data" not in st.session_state:
                    st.session_state.food_data = pd.DataFrame()
                    food_ref = db.collection("foods")
                    for doc in food_ref.stream():
                        foodid = {"foodid": doc.id}
                        food = {**foodid, **doc.to_dict()}
                        food_df = pd.DataFrame(
                            {
                                "datetime": [food.get("datetime")],
                                "calories": [food.get("calories")],
                                "fats": [food.get("fats")],
                                "carbohydrates": [food.get("carbohydrates")],
                                "fiber": [food.get("fiber")],
                                "name": [food.get("name")],
                                "protein": [food.get("protein")],
                                "sodium": [food.get("sodium")],
                                "sugar": [food.get("sugar")],
                                "type": [food.get("type")],
                                "userid": [food.get("userid")],
                                "weight": [food.get("weight")],
                            }
                        )
                        if st.session_state.userid == food.get("userid"):
                            st.session_state.food_data = pd.concat(
                                [st.session_state.food_data, food_df],
                                ignore_index=True,
                            )

                if "post_data" not in st.session_state:
                    st.session_state.post_data = pd.DataFrame()
                    post_ref = db.collection("posts")
                    for doc in post_ref.stream():
                        postid = {"postid": doc.id}
                        post = {**postid, **doc.to_dict()}
                        post_df = pd.DataFrame(
                            {
                                "isPostImage": [post.get("isPostImage")],
                                "postImage": [post.get("postImage")],
                                "postVideo": [post.get("postVideo")],
                                "userDisplayName": [post.get("userDisplayName")],
                                "userID": [post.get("userID")],
                                "userMessage": [post.get("userMessage")],
                            }
                        )
                        if st.session_state.userid == post.get("userID"):
                            st.session_state.post_data = pd.concat(
                                [st.session_state.post_data, post_df],
                                ignore_index=True,
                            )
                if "sleep_data" not in st.session_state:
                    st.session_state.sleep_data = pd.DataFrame()
                    sleep_ref = db.collection("sleep")
                    for doc in sleep_ref.stream():
                        sleepid = {"sleepid": doc.id}
                        sleep = {**sleepid, **doc.to_dict()}
                        sleep_df = pd.DataFrame(
                            {
                                "Date": [sleep.get("Date")],
                                "Sleep": [sleep.get("Sleep(hours)")],
                                "userid": [sleep.get("userid")],
                            }
                        )
                        if st.session_state.userid == sleep.get("userid"):
                            st.session_state.sleep_data = pd.concat(
                                [st.session_state.sleep_data, sleep_df],
                                ignore_index=True,
                            )
                if "water_data" not in st.session_state:
                    st.session_state.water_data = pd.DataFrame()
                    water_ref = db.collection("water")
                    for doc in water_ref.stream():
                        waterid = {"waterid": doc.id}
                        water = {**waterid, **doc.to_dict()}
                        water_df = pd.DataFrame(
                            {
                                "Date": [water.get("Date")],
                                "Water": [water.get("Water(ounces)")],
                                "userid": [water.get("userid")],
                            }
                        )
                        if st.session_state.userid == water.get("userid"):
                            st.session_state.water_data = pd.concat(
                                [st.session_state.water_data, water_df],
                                ignore_index=True,
                            )
                if "foodunderstanding_data" not in st.session_state:
                    st.session_state.foodunderstanding_data = pd.DataFrame()
                    foodunderstanding_ref = db.collection("foodunderstanding")
                    for doc in foodunderstanding_ref.stream():
                        foodunderstandingid = {"foodunderstandingid": doc.id}
                        foodunderstanding = {**foodunderstandingid, **doc.to_dict()}
                        foodunderstanding_df = pd.DataFrame(
                            {
                                "Date": [foodunderstanding.get("Date")],
                                "CarbohydrateError": [
                                    foodunderstanding.get("Water(onces)")
                                ],
                                "userid": [foodunderstanding.get("userid")],
                            }
                        )
                        if st.session_state.userid == foodunderstanding.get("userid"):
                            st.session_state.foodunderstanding_data = pd.concat(
                                [
                                    st.session_state.foodunderstanding_data,
                                    foodunderstanding_df,
                                ],
                                ignore_index=True,
                            )

                if "profile" not in st.session_state:
                    st.session_state.weight_data.sort_values(by="Date", inplace=True)
                    original_weight = st.session_state.weight_data.iloc[0]["Weight"]
                    current_weight = st.session_state.weight_data.iloc[-1]["Weight"]
                    df_glucose_data_cleaned = st.session_state.glucose_data.dropna(
                        subset=["BloodSugarLevel(mg/dl)"]
                    )
                    df_glucose_data_cleaned["Sugar"] = df_glucose_data_cleaned[
                        "BloodSugarLevel(mg/dl)"
                    ].astype(int)
                    average_bloodglucose_level = df_glucose_data_cleaned["Sugar"].mean()
                    estimated_a1c = (average_bloodglucose_level + 46.7) / 28.7
                    most_frequent_exercise = (
                        st.session_state.exercise_data["Exercise"]
                        .value_counts()
                        .idxmax()
                    )
                    most_frequent_food = (
                        st.session_state.food_data["name"].value_counts().idxmax()
                    )
                    df_food_data_cleaned_carbohydrates = (
                        st.session_state.food_data.dropna(subset=["carbohydrates"])
                    )

                    df_food_data_cleaned_carbohydrates["carbohydratesint"] = (
                        df_food_data_cleaned_carbohydrates["carbohydrates"].astype(int)
                    )

                    average_carbohydrates_per_day = df_food_data_cleaned_carbohydrates[
                        "carbohydratesint"
                    ].mean()

                    df_food_data_cleaned_proteins = st.session_state.food_data.dropna(
                        subset=["protein"]
                    )
                    df_food_data_cleaned_proteins["proteinint"] = (
                        df_food_data_cleaned_proteins["protein"].astype(int)
                    )

                    average_protein_per_day = df_food_data_cleaned_proteins[
                        "proteinint"
                    ].mean()

                    df_food_data_cleaned_fats = st.session_state.food_data.dropna(
                        subset=["fats"]
                    )
                    df_food_data_cleaned_fats["fatsint"] = df_food_data_cleaned_fats[
                        "fats"
                    ].astype(int)
                    average_fats_per_day = df_food_data_cleaned_fats["fatsint"].mean()

                    social_media_comments = st.session_state.post_data[
                        "userMessage"
                    ].to_list()
                    post_comments = ", ".join(social_media_comments)

                    average_sleep_per_day = 0

                    if len(st.session_state.sleep_data) > 0:
                        df_sleep = st.session_state.sleep_data
                        df_sleep["Sleep"] = df_sleep["Sleep"].astype(int)
                        average_sleep_per_day = df_sleep["Sleep"].mean()

                    average_water_per_day = 0

                    if len(st.session_state.water_data) > 0:
                        df_water = st.session_state.water_data
                        df_water["Water"] = df_water["Water"].astype(int)
                        average_water_per_day = df_water["Water"].mean()

                    average_error_carbohydrates = 0
                    if len(st.session_state.foodunderstanding_data) > 0:
                        average_error_carbohydrates = (
                            "fair"
                            if st.session_state.foodunderstanding_data[
                                "CarbohydrateError"
                            ].mean()
                            < 100
                            else "poor"
                        )

                    st.session_state.profile = f""" MY PROFILE IS THE FOLLOWING:
                    Facts about me:
                    I am a  {st.session_state.current_user[0].get("age")}-year-old {st.session_state.current_user[0].get("gender")} who was diagnosed with Type 2 diabetes.  
                    I take metformin daily for my diabetes. I would describe my activity level as {st.session_state.current_user[0].get("activity")}. My height is {st.session_state.current_user[0].get("height")}.
                    I used to weight {original_weight} pounds, but after trying to eat better and exercise my new weight is {current_weight} pounds. In fact, my most favorite exercise is {most_frequent_exercise},
                    and my most favorite food is {most_frequent_food}. I count my macronutrients. Most of my calories have on average {average_carbohydrates_per_day:.2f} 
                    of carbohydrates per meal, {average_protein_per_day:.2f} of protein per meal, and {average_fats_per_day:.2f} of fats per meal. 
                    My average blood glucose level in mg/dl is {average_bloodglucose_level:.2f},which give me an estimated hemoglobin A1c of {estimated_a1c:.2f}. 
                    I often sleep on average of {average_sleep_per_day:.2f} hours a day. I drink on average {average_water_per_day:.2f} ounces of water a day. 
                    I would say that I have {average_error_carbohydrates} understanding of picking foods with the right amount carbohydrates.
                    When I share my feeling with others about my diabetes I have the following comments:
                    {post_comments}
                    GOALS:
                    I guess my goals can be summed up in the following sentences: {st.session_state.current_user[0].get("notes")}
                    """

            st.write(st.session_state.profile)

            st.write(
                "You should be able to access the content that needed a login. Thanks!"
            )

        else:
            st.warning("Please log in to access this content.")

        if st.button(
            "Logout", icon=":material/logout:", type="primary", use_container_width=True
        ):
            del st.session_state["user"]
            del st.session_state.users
            del st.session_state.current_user
            del st.session_state.userid
            del st.session_state.glucose_data
            del st.session_state.weight_data
            del st.session_state.sleep_data
            del st.session_state.water_data
            del st.session_state.post_data
            del st.session_state.food_data
            del st.session_state.exercise_data

            keys = list(st.session_state.keys())
            for key in keys:
                st.session_state.pop(key)

            st.rerun()


if __name__ == "__main__":
    main()
