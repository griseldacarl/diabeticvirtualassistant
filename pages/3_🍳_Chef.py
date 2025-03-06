import os

import chromadb
import streamlit as st
from chromadb.config import DEFAULT_DATABASE, DEFAULT_TENANT, Settings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import CSVLoader
from langchain_community.embeddings import fastembed
from langchain_ollama import ChatOllama

FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "documents/chef",
)
st.set_page_config("Chef", page_icon=":material/cooking:", layout="centered")

HOST_NAME = os.environ.get("CHROMA_HOST_NAME")
BASE_URL = os.environ.get("OLLAMA_URL")
MODEL = "llama3.2:1b"
COLLECTION_NAME = "chef_collection"


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


def load_csv_from_directory(csv_folder):
    """Builds a RAG system using LangChain to search multiple CSV files."""

    csv_files = [f for f in os.listdir(csv_folder) if f.endswith(".csv")]
    if not csv_files:
        print(f"No CSV files found in {csv_folder}")
        return None

    documents = []
    for file in csv_files:
        filepath = os.path.join(csv_folder, file)
        try:
            loader = CSVLoader(filepath, encoding="utf-8")  # Handle encoding if needed
            documents = loader.load()

            # Add file metadata to each document (important for context)
            for doc in documents:
                doc.metadata["source"] = file  # Add the filename as metadata
                # Add row number or other identifier if available in CSV
                # Example: doc.metadata["row"] = ... # If your data has row numbers

            documents.extend(documents)

        except Exception as e:
            print(f"Error reading CSV file {file}: {e}")
            return []

    return documents


def main():
    st.title("Hi, I am your Chef! 🍳")
    st.subheader(
        "Please ask me questions about recipes. I especially like to cook Mediterranean dishes."
    )

    collection_count = get_collection_size(
        client_collection=client, collection_name=COLLECTION_NAME
    )

    if collection_count == 0:
        st.write("Give me a minute to gather my thoughts....")
    else:
        st.write("I am ready to help...")

    if collection_count == 0:
        with st.spinner("Loading files..."):
            document_chunks = load_csv_from_directory(FILE_PATH)
            vector_store.add_documents(documents=document_chunks)

    prompt = PromptTemplate.from_template(
        """
             <s> [INST] You are an assistant for question-answering tasks related to mediterranean recipes. You trained as a Chef before this job. Use the following pieces of retrieved context to answer the question. 
             If you don't know the answer, just say that you don't know.  [/INST]</s>
             [INST] Questions: {question}
             Context: {context}
             Answer:[/INST]
            """
    )
    retriever = vector_store.as_retriever()

    if "chef_messages" not in st.session_state:
        st.session_state.chef_messages = []

    st.sidebar.title("Sometimes we all have the same questions!")
    question_map = [
        "What is a good recipe for a breakfast sandwich?",
        "What is a good grill chicken recipe?",
        "How should I prepare steak?",
        "What is a good recipe for fish?",
        "What is a good rice recipe?",
        "Give me a recipe with steak",
        "Give me a recipe with fish",
        "Give me a recipe with chicken",
    ]

    selection = None
    if st.sidebar.checkbox(
        "Would like to use some questions that I have prepared for you?"
    ):
        selection = st.sidebar.pills(
            "Here are a few common questions about Nutrition:",
            options=question_map,
            selection_mode="single",
        )

    prompt.invoke(
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
    )
    qa = RetrievalQA.from_chain_type(
        llm=model, chain_type="stuff", retriever=retriever
    )  # "stuff" chain type is common

    for messages in st.session_state.chef_messages:
        with st.chat_message(messages["role"]):
            st.markdown(messages["content"])

    if selection is not None:

        with st.chat_message("user"):
            st.markdown(selection)

        st.session_state.chef_messages.append({"role": "user", "content": selection})

        with st.status("Thinking...."):
            response = qa.invoke(selection)
        with st.chat_message("assistant"):
            st.markdown(response["result"])

        st.session_state.chef_messages.append(
            {"role": "assistant", "content": response}
        )

    if prompt := st.chat_input("How can I help?"):
        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.chef_messages.append({"role": "user", "content": prompt})
        
        with st.status("Thinking..."):
            response = qa.invoke(prompt)

        with st.chat_message("assistant"):
            st.markdown(response["result"])

        st.session_state.chef_messages.append(
            {"role": "assistant", "content": response}
        )


if __name__ == "__main__":
    main()
