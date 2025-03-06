import os
import tempfile
import time
from uuid import uuid4

import chromadb
import streamlit as st
from chromadb.config import DEFAULT_DATABASE, DEFAULT_TENANT, Settings
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import fastembed
from langchain_ollama import ChatOllama

st.set_page_config(
    "Diabetic Educator", page_icon=":material/glucose:", layout="centered"
)

FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "documents/diabeticeducator",
)

HOST_NAME = os.environ.get("CHROMA_HOST_NAME")
BASE_URL = os.environ.get("OLLAMA_URL")
MODEL = "llama3.2:1b"
COLLECTION_NAME = "guidelines_collection"

client = chromadb.HttpClient(
    host=HOST_NAME,
    port=8000,
    ssl=False,
    headers=None,
    settings=Settings(),
    tenant=DEFAULT_TENANT,
    database=DEFAULT_DATABASE,
)

model = ChatOllama(base_url=BASE_URL, model=MODEL)

vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=fastembed.FastEmbedEmbeddings(),
    client=client,
)


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def get_collection_size(
    client_collection: chromadb.Client, collection_name: str
) -> int:
    """Check if a collection with the given name exist in ChromaDB

    Args:
        client_collection (chromadb.Client): The ChromaDB client instance.
        collection_name (str): The name of the collection to check

    Returns:
        int: Size of the collection.  If the collection doesn't exist, then the size is zero.
    """
    try:
        collection = client_collection.get_collection(name=collection_name)
        return collection.count()
    except ValueError:
        return 0
    except Exception:
        return 0


def load_pdfs_from_directory(directory: str) -> list:
    """
    Loads all PDF files from a directory using PyPDFLoader and returns a list of LangChain Documents.

    Args:
        directory: The path to the directory containing the PDF files.

    Returns:
        A list of LangChain Documents, or an empty list if no PDFs are found or an error occurs.
    """

    documents = []
    try:
        for filename in os.listdir(directory):
            if filename.lower().endswith(
                ".pdf"
            ):  # Robust check for PDF extension (case-insensitive)
                filepath = os.path.join(directory, filename)
                try:  # Inner try-except for individual file loading
                    loader = PyPDFLoader(filepath)
                    loaded_docs = loader.load()

                    # Splitting the documents (Important for RAG)
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1024, chunk_overlap=20
                    )  # Adjust chunk size as needed
                    docs = text_splitter.split_documents(loaded_docs)

                    documents.extend(docs)  # Add the SPLIT documents to the list.

                except Exception as e:
                    print(
                        f"Error loading PDF file '{filename}': {e}"
                    )  # Handle individual file errors
        return documents

    except FileNotFoundError:
        print(f"Directory '{directory}' not found.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []


def main():

    st.title("Hi, I am your Diabetic Educator!🧑‍⚕️")
    st.subheader("Please ask me questions about diabetes.")

    collection_count = get_collection_size(
        client_collection=client, collection_name=COLLECTION_NAME
    )

    if collection_count == 0:
        st.write("Give me a minute to gather my thoughts....")
    else:
        st.write("I am ready to help...")

    if collection_count == 0:
        with st.spinner("Loading files..."):
            document_chunks = load_pdfs_from_directory(FILE_PATH)
            vector_store.add_documents(documents=document_chunks)

    prompt_template = PromptTemplate.from_template(
        """
             <s> [INST] You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. 
             If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise. [/INST]</s>
             [INST] Questions: {question}
             Context: {context}
             Answer:[/INST]
            """
    )
    retriever = vector_store.as_retriever()

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt_template
        | model
        | StrOutputParser()
    )
    if "diabetic_educator_messages" not in st.session_state:
        st.session_state.diabetic_educator_messages = []

    st.sidebar.title("Sometimes we all have the same questions!")
    question_map = [
        "What is a good diabetes medication?",
        "What is metformin?",
        "How does insulin help diabetes?",
        "What is a good HbA1c?",
    ]

    selection = None
    if st.sidebar.checkbox(
        "Would like to use some questions that I have prepared for you?"
    ):
        selection = st.sidebar.pills(
            "Here are a few common questions about diabetes:",
            options=question_map,
            selection_mode="single",
        )

    for messages in st.session_state.diabetic_educator_messages:
        with st.chat_message(messages["role"]):
            st.markdown(messages["content"])

    if selection is not None:

        with st.chat_message("user"):
            st.markdown(selection)

        st.session_state.diabetic_educator_messages.append(
            {"role": "user", "content": selection}
        )
        with st.status("Thinking..."):
            response = rag_chain.invoke(selection)
            
        with st.chat_message("assistant"):
            st.markdown(response)

        st.session_state.diabetic_educator_messages.append(
            {"role": "assistant", "content": response}
        )
        selection = None

    if prompt := st.chat_input("How can I help?"):
        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.diabetic_educator_messages.append(
            {"role": "user", "content": prompt}
        )
        with st.status("Thinking..."):
            response = rag_chain.invoke(prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response)

        st.session_state.diabetic_educator_messages.append(
            {"role": "assistant", "content": response}
        )


if __name__ == "__main__":
    main()
