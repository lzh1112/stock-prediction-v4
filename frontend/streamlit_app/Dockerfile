FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir streamlit httpx plotly

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
