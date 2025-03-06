import os
from datetime import datetime, timezone
import chromadb
import firebase_admin
import pandas as pd
import plotly.express as px
import pytz
import streamlit as st
from firebase_admin import credentials, firestore
import requests
import json
from typing import Optional
from langflow.load import run_flow_from_json
from bs4 import BeautifulSoup
import bs4
from langchain import hub
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import fastembed
from langchain_ollama import ChatOllama
from chromadb.config import DEFAULT_DATABASE, DEFAULT_TENANT, Settings
from langchain_chroma import Chroma
from langchain.tools import Tool,BaseTool
from langchain_core.tools import tool
from langchain.pydantic_v1 import BaseModel, Field
from langchain.agents import create_react_agent, AgentType, initialize_agent, create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools.retriever import create_retriever_tool
from langchain_openai import ChatOpenAI
from langchain_core.vectorstores import InMemoryVectorStore

st.set_page_config(
    "Life Coach", page_icon=":material/self_improvement:", layout="centered"
)


FILE_PATH_DIABETIC_ADVICE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "langflow/diabetic-advice.json",
)



FILE_PATH_NUTRITION = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "documents/nutrition",
)

FILE_PATH_PERSONALTRAINER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "documents/personaltrainer",
)

FILE_PATH_SERVICEACCOUNTKEY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "diabeticvirtualassistant-firebase-adminsdk-fbsvc-b7c63be69b.json",
)

#Langflow Configuration
LANGFLOW_URL  = os.environ.get("BASE_API_URL")
FLOW_ID = os.environ.get("FLOW_ID")
DIABETIC_ADVICE_ENDPOINT=os.environ.get("DIABETIC_ADVICE_ENDPOINT")
LANGFLOW_API_KEY =os.environ.get("LANGFLOW_API_KEY")
OPEN_API_KEY  =os.environ.get("OPEN_API_KEY")

try:
    app = firebase_admin.get_app()
except ValueError:
    st.session_state.cred = credentials.Certificate(FILE_PATH_SERVICEACCOUNTKEY)
    firebase_admin.initialize_app(st.session_state.cred)







# End of Web Agent setup

if "selected_food" not in st.session_state:
    st.session_state.selected_food = None


db = firestore.client()  # Example for Firesto

def get_diabetic_advice(question,profile):
    TWEAKS = {
  "TextInput-KpJPD": {
    "input_value": question
  },
  "TextInput-t9gYO": {
    "input_value": profile
  },
   
  }
    return run_flow_from_json(flow=FILE_PATH_DIABETIC_ADVICE,input_type="text",input_value=question,fallback_to_env_vars=True,tweaks=TWEAKS)



def adjust_datetime_for_phoenix(dt, from_timezone="UTC"):
    """
    Adjusts a datetime object to Phoenix, Arizona time.

    Args:
        dt: The datetime object to adjust.
        from_timezone: The timezone of the input datetime object (e.g., "UTC", "America/New_York").

    Returns:
        A datetime object in Phoenix, Arizona time.
    """
    try:
        from_tz = pytz.timezone(from_timezone)
        phoenix_tz = pytz.timezone("America/Phoenix")  # Phoenix, Arizona timezone

        # Make the input datetime aware of its original timezone
        if (
            dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None
        ):  # check if datetime object is timezone aware or not.
            dt = from_tz.localize(dt)

        # Convert to Phoenix time
        phoenix_dt = dt.astimezone(phoenix_tz)
        return phoenix_dt

    except pytz.exceptions.UnknownTimeZoneError as e:
        print(f"Error: Unknown timezone: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


if st.session_state.get("user"):
    st.title("Hi, I am your Life Coach! 👩‍⚕️")
    st.session_state.current_user = [
        usr
        for usr in st.session_state.users
        if usr.get("email") == st.session_state["user"].email
    ]
    # st.write(st.session_state.current_user)
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🩸 Blood Sugars", "🥑 Food", "⚖️ Weight", "🏋️‍♀️ Exercise"]
    )
    with tab1:
        st.header("What do you Blood Sugars look like today?")
        # Pull the blood sugars from the database to start this on load

        with st.expander("Blood Glucose", icon=":material/glucose:"):
            st.session_state.blood_glucose_value = 150

            st.session_state.blood_glucose_value = st.slider(
                "Enter your Glucose",
                60,
                300,
                st.session_state.blood_glucose_value,
                step=10,
            )
            st.session_state.blood_glucose_value = st.number_input(
                "You entered",
                value=st.session_state.blood_glucose_value,
                placeholder="What did you get?",
            )

            st.markdown(
                f"""<svg viewBox="0 0 240 80" xmlns="http://www.w3.org/2000/svg">
                <text x="65" y="55" fill="blue" font-size="35">{st.session_state.blood_glucose_value} mg/dl</text>
            </svg>
    """,
                unsafe_allow_html=True,
            )

            is_ok_add_blood_sugar = st.button(
                "Would you like to Add this sugar?",
                icon=":material/glucose:",
                type="primary",
                use_container_width=True,
            )

            if is_ok_add_blood_sugar:
                new_reading = pd.DataFrame(
                    {
                        "Timestamp": [
                            adjust_datetime_for_phoenix(datetime.now(timezone.utc))
                        ],
                        "Glucose Level": [st.session_state.blood_glucose_value],
                    }
                )
                st.session_state.glucose_data = pd.concat(
                    [st.session_state.glucose_data, new_reading], ignore_index=True
                )
                # Add to database here
                new_bloodsugar = {
                    "bloodsugar": st.session_state.blood_glucose_value,
                    "userid": st.session_state.userid,
                    "timestamp": adjust_datetime_for_phoenix(datetime.now(timezone.utc)),
                }

                # st.write(st.session_state.userid)
                db.collection("bloodsugars").add(new_bloodsugar)

            # Display data and visualizations
            if not st.session_state.glucose_data.empty:
                # Show the line graph
                st.subheader("Blood Glucose History")

                fig = px.line(
                    st.session_state.glucose_data,
                    x="Timestamp",
                    y="Glucose Level",
                    title="Blood Glucose Levels Over Time",
                )

                # Add reference ranges
                fig.add_hline(
                    y=70,
                    line_dash="dash",
                    line_color="yellow",
                    annotation_text="Lower Normal Range (70 mg/dL)",
                )
                fig.add_hline(
                    y=99,
                    line_dash="dash",
                    line_color="green",
                    annotation_text="Upper Normal Range (99 mg/dL)",
                )
                fig.add_hline(
                    y=180,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="High (180 mg/dL)",
                )
                # Update layout
                fig.update_layout(
                    yaxis_title="Glucose Level (mg/dL)",
                    xaxis_title="Time",
                    hovermode="x unified",
                )

                st.plotly_chart(fig, use_container_width=True)

                # Show statistics
                st.subheader("Statistics")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "Latest Reading",
                        f"{st.session_state.glucose_data['Glucose Level'].iloc[-1]} mg/dL",
                    )
                with col2:
                    st.metric(
                        "Average",
                        f"{st.session_state.glucose_data['Glucose Level'].mean():.1f} mg/dL",
                    )
                with col3:
                    st.metric("Total Readings", len(st.session_state.glucose_data))

            else:
                st.info(
                    "You haven't shared your blood sugars. This is the best way we know how to help. Add your first reading above!"
                )
        with st.expander("What is a good estimate of my Hemoglobin A1c?"):
            flow_id = FLOW_ID
            question = "What is a good estimate of my Hemoglobin A1c?"
            profile = "profile: my fasting blood sugar is 200 goal: lower blood sugar"
            prompt =f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """
            
            if st.button("Please give me an recommendation...",icon=":material/psychology:",type="primary",use_container_width=True,key="bloodsugar_A1c"):
                if flow_id and question and profile:
                   with st.spinner("Thinking..."):
                    try:
                        result = get_diabetic_advice(prompt, profile)
                        question_answer = json.loads(result[0].outputs[0].results["text"].data["text"])
                        if len(question_answer["answer"]) <2:
                            for recommendation in question_answer["answer"]["recommendations"]:
                                st.write(recommendation["advice"])
                        else:
                            st.write(question_answer['answer'])

                    except requests.exceptions.RequestException as e:
                        st.warning(f"Error: {e}")
                    except json.JSONDecodeError as ex:
                        st.warning(f"Error decoding JSON: {ex}")

            

    with tab2:
        st.header("What are you eating?")

        if st.session_state.selected_food:
           st.write(st.session_state.selected_food)

        df_group1 = pd.read_csv(
            os.path.join(FILE_PATH_NUTRITION, "FOOD-DATA-GROUP1.csv")
        )
        df_group2 = pd.read_csv(
            os.path.join(FILE_PATH_NUTRITION, "FOOD-DATA-GROUP2.csv")
        )
        df_group3 = pd.read_csv(
            os.path.join(FILE_PATH_NUTRITION, "FOOD-DATA-GROUP3.csv")
        )
        df_group4 = pd.read_csv(
            os.path.join(FILE_PATH_NUTRITION, "FOOD-DATA-GROUP4.csv")
        )
        df_group5 = pd.read_csv(
            os.path.join(FILE_PATH_NUTRITION, "FOOD-DATA-GROUP5.csv")
        )
        df_food_groups = pd.concat(
            [df_group1, df_group2, df_group3, df_group4, df_group5]
        )

        search_item = st.text_input(
            "Narrow your selection:", placeholder="Enter food name..."
        )

       
        mask = df_food_groups.apply(
            lambda x: x.astype(str).str.contains(search_item, case=False)
        ).any(axis=1)
        st.session_state.current_selected_foods = df_food_groups[mask]
       
        food_selected = st.selectbox("Select your food", index=None,options=st.session_state.current_selected_foods["food"])

        new_food = {
                    "food": food_selected,
                    "userid": st.session_state.userid,
                    "timestamp": adjust_datetime_for_phoenix(datetime.now(timezone.utc)),
                }
        st.write("You selected:", food_selected) 
        if st.button("Add selected food to list?",use_container_width=True,type="primary"):
            if not food_selected == None:
               db.collection("foods").add(new_food)
            else:
               st.warning("Please select some food first!!")

              
                             
                          
                         

    with tab3:
        
        st.header("How are you doing with your weight?")
        with st.expander("Weight", icon=":material/monitor_weight:"):

            st.session_state.weight_value = 150

            st.session_state.weight_value = st.slider(
                "Enter your Weight", 100, 300, st.session_state.weight_value, step=10
            )
            st.session_state.weight_value = st.number_input(
                "You entered",
                value=st.session_state.weight_value,
                placeholder="What did that scale say?",
            )

            st.markdown(
                f"""<svg viewBox="0 0 240 80" xmlns="http://www.w3.org/2000/svg">
                    <text x="65" y="55" fill="blue" font-size="35">{st.session_state.weight_value} lbs</text>
                </svg>
        """,
                unsafe_allow_html=True,
            )

            is_ok_add_weight = st.button(
                "Would you like to add this weight?",
                icon=":material/monitor_weight:",
                type="primary",
                use_container_width=True,
            )

            if is_ok_add_weight:
                new_weight_reading = pd.DataFrame(
                    {
                        "Timestamp": [
                            adjust_datetime_for_phoenix(datetime.now(timezone.utc))
                        ],
                        "Weight": [st.session_state.weight_value],
                    }
                )
                st.session_state.weight_data = pd.concat(
                    [st.session_state.weight_data, new_weight_reading],
                    ignore_index=True,
                )
               # Add to database here
                new_weight = {
                    "bloodsugar": st.session_state.blood_glucose_value,
                    "userid": st.session_state.userid,
                    "timestamp": adjust_datetime_for_phoenix(datetime.now(timezone.utc)),
                }

                # st.write(st.session_state.userid)
                db.collection("weights").add(new_weight)






            # Display data and visualizations
            if "weight_data" in st.session_state and not st.session_state.weight_data.empty:
                # Show the line graph
                st.subheader("Weight History")
                fig = px.line(
                    st.session_state.weight_data,
                    x="Timestamp",
                    y="Weight",
                    title="Blood Weight Over Time",
                )

                # Update layout
                fig.update_layout(
                    yaxis_title="Weight (lbs)",
                    xaxis_title="Time",
                    hovermode="x unified",
                )

                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info(
                    "You haven't told us your weight. Don't worry. We are good a keeping secrets. Add your first reading above!"
                )
        with st.expander("How many calories, carbohydrates, proteins and fats should I eat to accomplish my goals?"):
            flow_id = FLOW_ID
            question = "How many calories, carbohydrates, proteins and fats should I eat to accomplish my goals?"
            profile = "profile:  male, weight: 200lbs, height: 5 feet 10 inches, activity: no active; goals: loose weight"
            prompt =f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """
            
            if st.button("Please give me an recommendation...",icon=":material/psychology:",type="primary",use_container_width=True,key="weight_calories"):
                if flow_id and question and profile:
                   with st.spinner("Thinking..."):
                    try:
                        result = get_diabetic_advice(prompt, profile)
                        question_answer = json.loads(result[0].outputs[0].results["text"].data["text"])
                        if len(question_answer["answer"]) <2:
                            for recommendation in question_answer["answer"]["recommendations"]:
                                st.write(recommendation["advice"])
                        else:
                            st.write(question_answer['answer'])

                    except requests.exceptions.RequestException as e:
                        st.warning(f"Error: {e}")
                    except json.JSONDecodeError as ex:
                        st.warning(f"Error decoding JSON: {ex}")

        with st.expander("What are your recommendations on exercise to accomplish my goals?"):
            flow_id = FLOW_ID
            question = "What are your recommendations on exercise to accomplish my goals?"
            profile = "profile:  male, weight: 200lbs, height: 5 feet 10 inches, activity: no active; goals: loose weight"
            prompt =f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """
            
            if st.button("Please give me an recommendation...",icon=":material/psychology:",type="primary",use_container_width=True,key="weight_exercise"):
                if flow_id and question and profile:
                   with st.spinner("Thinking..."):
                    try:
                        result = get_diabetic_advice(prompt, profile)
                        question_answer = json.loads(result[0].outputs[0].results["text"].data["text"])
                        if len(question_answer["answer"]) <2:
                            for recommendation in question_answer["answer"]["recommendations"]:
                                st.write(recommendation["advice"])
                        else:
                            st.write(question_answer['answer'])

                    except requests.exceptions.RequestException as e:
                        st.warning(f"Error: {e}")
                    except json.JSONDecodeError as ex:
                        st.warning(f"Error decoding JSON: {ex}")

    with tab4:
        
        st.header("Did we get some exercise done today?")
        search_item_gym = st.text_input(
            "Search for exercise items:", placeholder="Enter your exercise..."
        )
        df_gym = pd.read_csv(
               os.path.join(FILE_PATH_PERSONALTRAINER, "workout.csv")
             )
        

        
        mask_gym = df_gym.apply(
                lambda x: x.astype(str).str.contains(search_item_gym, case=False)
            ).any(axis=1)
        st.session_state.current_df_gym = df_gym[mask_gym]
        
        
        exercise_selected = st.selectbox("Select your exercise", index=None,options=st.session_state.current_df_gym["Workout"])

        new_exercise = {
                    "exercise": exercise_selected,
                    "userid": st.session_state.userid,
                    "timestamp": adjust_datetime_for_phoenix(datetime.now(timezone.utc)),
                }
        st.write("You selected:", exercise_selected) 
        if st.button("Add selected exercise to list?",use_container_width=True,type="primary"):
            if not exercise_selected == None:
                db.collection("exercises").add(new_exercise)
            else:
               st.warning("Please select some food first!!")

else:
    st.warning("Please log in to access this content.")
