# syntax=docker/dockerfile:1
FROM python:3
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY game/Pipfile /code
COPY game/Pipfile.lock /code
RUN pip install pipenv
RUN pipenv install
RUN rm -rf /code
