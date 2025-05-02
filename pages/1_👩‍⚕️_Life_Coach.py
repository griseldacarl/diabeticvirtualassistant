import json
import os
from datetime import datetime, timezone
from typing import Optional

import bs4
import chromadb
import firebase_admin
import pandas as pd
import plotly.express as px
import pytz
import requests
import streamlit as st
from bs4 import BeautifulSoup
from chromadb.config import DEFAULT_DATABASE, DEFAULT_TENANT, Settings
from firebase_admin import credentials, firestore
from langchain import hub
from langchain.agents import (
    AgentExecutor,
    AgentType,
    create_react_agent,
    create_tool_calling_agent,
    initialize_agent,
)
from langchain.tools import BaseTool, Tool
from langchain.tools.retriever import create_retriever_tool
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.embeddings import fastembed
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langflow.load import run_flow_from_json

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

# Langflow Configuration
LANGFLOW_URL = os.environ.get("BASE_API_URL")
FLOW_ID = os.environ.get("FLOW_ID")
DIABETIC_ADVICE_ENDPOINT = os.environ.get("DIABETIC_ADVICE_ENDPOINT")
LANGFLOW_API_KEY = os.environ.get("LANGFLOW_API_KEY")
OPEN_API_KEY = os.environ.get("OPEN_API_KEY")

try:
    app = firebase_admin.get_app()
except ValueError:
    st.session_state.cred = credentials.Certificate(FILE_PATH_SERVICEACCOUNTKEY)
    firebase_admin.initialize_app(st.session_state.cred)


# End of Web Agent setup

if "selected_food" not in st.session_state:
    st.session_state.selected_food = None


db = firestore.client()  # Example for Firesto


def get_diabetic_advice(question, profile):
    TWEAKS = {
        "TextInput-KpJPD": {"input_value": question},
        "TextInput-t9gYO": {"input_value": profile},
    }
    return run_flow_from_json(
        flow=FILE_PATH_DIABETIC_ADVICE,
        input_type="text",
        input_value=question,
        fallback_to_env_vars=True,
        tweaks=TWEAKS,
    )


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

        with st.expander("What is a good estimate of my Hemoglobin A1c?"):
            flow_id = FLOW_ID
            question = "What is a good estimate of my Hemoglobin A1c?"
            profile = st.session_state.profile
            prompt = f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """

            if st.button(
                "Please give me an recommendation...",
                icon=":material/psychology:",
                type="primary",
                use_container_width=True,
                key="bloodsugar_A1c",
            ):
                if flow_id and question and profile:
                    with st.spinner("Thinking..."):
                        try:
                            result = get_diabetic_advice(prompt, profile)
                            question_answer = json.loads(
                                result[0].outputs[0].results["text"].data["text"]
                            )
                            if len(question_answer["answer"]) < 2:
                                for recommendation in question_answer["answer"][
                                    "recommendations"
                                ]:
                                    st.write(recommendation["advice"])
                            else:
                                st.write(question_answer["answer"])

                        except requests.exceptions.RequestException as e:
                            st.warning(f"Error: {e}")
                        except json.JSONDecodeError as ex:
                            st.warning(f"Error decoding JSON: {ex}")

        with st.expander("What can I do to lower my blood sugars?"):
            flow_id = FLOW_ID
            question = "What can I do to lower my blood sugars?"
            profile = st.session_state.profile
            prompt = f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """

            if st.button(
                "Please give me an recommendation...",
                icon=":material/psychology:",
                type="primary",
                use_container_width=True,
                key="bloodsugar_lower",
            ):
                if flow_id and question and profile:
                    with st.spinner("Thinking..."):
                        try:
                            result = get_diabetic_advice(prompt, profile)
                            question_answer = json.loads(
                                result[0].outputs[0].results["text"].data["text"]
                            )

                            st.write(question_answer["answer"])

                        except requests.exceptions.RequestException as e:
                            st.warning(f"Error: {e}")
                        except json.JSONDecodeError as ex:
                            st.warning(f"Error decoding JSON: {ex}")

        with st.expander(
            "What are some of the complications that I might develop if I continue with my current diabetes care?"
        ):
            flow_id = FLOW_ID
            question = "What are some of the complications that I might develop if I continue with my current diabetes care?"
            profile = st.session_state.profile
            prompt = f"""
                        {question}
                        This is my current profile and goals: {profile}
                        """

            if st.button(
                "Please give me an recommendation...",
                icon=":material/psychology:",
                type="primary",
                use_container_width=True,
                key="bloodsugar_complications",
            ):
                if flow_id and question and profile:
                    with st.spinner("Thinking..."):
                        try:
                            result = get_diabetic_advice(prompt, profile)
                            question_answer = json.loads(
                                result[0].outputs[0].results["text"].data["text"]
                            )
                            if len(question_answer["answer"]) < 2:
                                for recommendation in question_answer["answer"][
                                    "recommendations"
                                ]:
                                    st.write(recommendation["advice"])
                            else:
                                st.write(question_answer["answer"])

                        except requests.exceptions.RequestException as e:
                            st.warning(f"Error: {e}")
                        except json.JSONDecodeError as ex:
                            st.warning(f"Error decoding JSON: {ex}")

    with tab2:

        with st.expander("Should I eat more protein or carbohydrates?"):
            flow_id = FLOW_ID
            question = "Should I eat more protein or carbohydrates?"
            profile = st.session_state.profile
            prompt = f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """

            if st.button(
                "Please give me an recommendation...",
                icon=":material/psychology:",
                type="primary",
                use_container_width=True,
                key="food_carbohydrates",
            ):
                if flow_id and question and profile:
                    with st.spinner("Thinking..."):
                        try:
                            result = get_diabetic_advice(prompt, profile)
                            question_answer = json.loads(
                                result[0].outputs[0].results["text"].data["text"]
                            )
                            if len(question_answer["answer"]) < 2:
                                for recommendation in question_answer["answer"][
                                    "recommendations"
                                ]:
                                    st.write(recommendation["advice"])
                            else:
                                st.write(question_answer["answer"])

                        except requests.exceptions.RequestException as e:
                            st.warning(f"Error: {e}")
                        except json.JSONDecodeError as ex:
                            st.warning(f"Error decoding JSON: {ex}")

        with st.expander("Is a diet high in fiber good for diabetes?"):
            flow_id = FLOW_ID
            question = "Is a diet high in fiber good for diabetes?"
            profile = st.session_state.profile
            prompt = f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """

            if st.button(
                "Please give me an recommendation...",
                icon=":material/psychology:",
                type="primary",
                use_container_width=True,
                key="food_fiber",
            ):
                if flow_id and question and profile:
                    with st.spinner("Thinking..."):
                        try:
                            result = get_diabetic_advice(prompt, profile)
                            question_answer = json.loads(
                                result[0].outputs[0].results["text"].data["text"]
                            )
                            if len(question_answer["answer"]) < 2:
                                for recommendation in question_answer["answer"][
                                    "recommendations"
                                ]:
                                    st.write(recommendation["advice"])
                            else:
                                st.write(question_answer["answer"])

                        except requests.exceptions.RequestException as e:
                            st.warning(f"Error: {e}")
                        except json.JSONDecodeError as ex:
                            st.warning(f"Error decoding JSON: {ex}")
        with st.expander("Should I avoid alcohol with my diabetes?"):
            flow_id = FLOW_ID
            question = "Should I avoid alcohol with my diabetes?"
            profile = st.session_state.profile
            prompt = f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """

            if st.button(
                "Please give me an recommendation...",
                icon=":material/psychology:",
                type="primary",
                use_container_width=True,
                key="food_alcohol",
            ):
                if flow_id and question and profile:
                    with st.spinner("Thinking..."):
                        try:
                            result = get_diabetic_advice(prompt, profile)
                            question_answer = json.loads(
                                result[0].outputs[0].results["text"].data["text"]
                            )
                            if len(question_answer["answer"]) < 2:
                                for recommendation in question_answer["answer"][
                                    "recommendations"
                                ]:
                                    st.write(recommendation["advice"])
                            else:
                                st.write(question_answer["answer"])

                        except requests.exceptions.RequestException as e:
                            st.warning(f"Error: {e}")
                        except json.JSONDecodeError as ex:
                            st.warning(f"Error decoding JSON: {ex}")
    with tab3:

        with st.expander("How does my weight affect my diabetes?"):
            flow_id = FLOW_ID
            question = "How does my weight affect my diabetes?"
            profile = st.session_state.profile
            prompt = f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """

            if st.button(
                "Please give me an recommendation...",
                icon=":material/psychology:",
                type="primary",
                use_container_width=True,
                key="weight_calories",
            ):
                if flow_id and question and profile:
                    with st.spinner("Thinking..."):
                        try:
                            result = get_diabetic_advice(prompt, profile)
                            question_answer = json.loads(
                                result[0].outputs[0].results["text"].data["text"]
                            )
                            if len(question_answer["answer"]) < 2:
                                for recommendation in question_answer["answer"][
                                    "recommendations"
                                ]:
                                    st.write(recommendation["advice"])
                            else:
                                st.write(question_answer["answer"])

                        except requests.exceptions.RequestException as e:
                            st.warning(f"Error: {e}")
                        except json.JSONDecodeError as ex:
                            st.warning(f"Error decoding JSON: {ex}")

        with st.expander(
            "What are your recommendations on exercise to accomplish my goals?"
        ):
            flow_id = FLOW_ID
            question = (
                "What are your recommendations on exercise to accomplish my goals?"
            )
            profile = st.session_state.profile
            prompt = f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """

            if st.button(
                "Please give me an recommendation...",
                icon=":material/psychology:",
                type="primary",
                use_container_width=True,
                key="weight_exercise",
            ):
                if flow_id and question and profile:
                    with st.spinner("Thinking..."):
                        try:
                            result = get_diabetic_advice(prompt, profile)
                            question_answer = json.loads(
                                result[0].outputs[0].results["text"].data["text"]
                            )
                            if len(question_answer["answer"]) < 2:
                                for recommendation in question_answer["answer"][
                                    "recommendations"
                                ]:
                                    st.write(recommendation["advice"])
                            else:
                                st.write(question_answer["answer"])

                        except requests.exceptions.RequestException as e:
                            st.warning(f"Error: {e}")
                        except json.JSONDecodeError as ex:
                            st.warning(f"Error decoding JSON: {ex}")

    with tab4:

        with st.expander("How many days a week should I exercise to gain more muscle?"):
            flow_id = FLOW_ID
            question = "How many days a week should I exercise to gain more muscle?"
            profile = st.session_state.profile
            prompt = f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """

            if st.button(
                "Please give me an recommendation...",
                icon=":material/psychology:",
                type="primary",
                use_container_width=True,
                key="exercise_protein_eat",
            ):
                if flow_id and question and profile:
                    with st.spinner("Thinking..."):
                        try:
                            result = get_diabetic_advice(prompt, profile)
                            question_answer = json.loads(
                                result[0].outputs[0].results["text"].data["text"]
                            )
                            if len(question_answer["answer"]) < 2:
                                for recommendation in question_answer["answer"][
                                    "recommendations"
                                ]:
                                    st.write(recommendation["advice"])
                            else:
                                st.write(question_answer["answer"])

                        except requests.exceptions.RequestException as e:
                            st.warning(f"Error: {e}")
                        except json.JSONDecodeError as ex:
                            st.warning(f"Error decoding JSON: {ex}")

        with st.expander("Should I lift weights or start running?"):
            flow_id = FLOW_ID
            question = "Should I lift weights or start running?"
            profile = st.session_state.profile
            prompt = f"""
                     {question}
                     This is my current profile and goals: {profile}
                    """

            if st.button(
                "Please give me an recommendation...",
                icon=":material/psychology:",
                type="primary",
                use_container_width=True,
                key="exercise_weight_lifting",
            ):
                if flow_id and question and profile:
                    with st.spinner("Thinking..."):
                        try:
                            result = get_diabetic_advice(prompt, profile)
                            question_answer = json.loads(
                                result[0].outputs[0].results["text"].data["text"]
                            )
                            if len(question_answer["answer"]) < 2:
                                for recommendation in question_answer["answer"][
                                    "recommendations"
                                ]:
                                    st.write(recommendation["advice"])
                            else:
                                st.write(question_answer["answer"])

                        except requests.exceptions.RequestException as e:
                            st.warning(f"Error: {e}")
                        except json.JSONDecodeError as ex:
                            st.warning(f"Error decoding JSON: {ex}")
