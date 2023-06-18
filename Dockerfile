FROM python:3.10

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH "$PATH:/root/.local/bin"

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false
RUN poetry install

COPY . ./
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
