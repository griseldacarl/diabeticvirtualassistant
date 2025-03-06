FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip
RUN pip install  -r requirements.txt

COPY . .

EXPOSE 8501

CMD [ "streamlit","run","Login.py" ]
