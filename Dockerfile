FROM python:3.6.8-alpine3.9

WORKDIR /usr/src/app
RUN pip install --upgrade pip 
RUN apk add --update --no-cache build-base \
  libffi-dev openssl-dev bash git gcc sqlite \
  curl

COPY . /usr/src/app/app/
WORKDIR /usr/src/app/app/

RUN --mount=type=cache,target=/root/.cache/pip && pip install -r requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install uwsgi
EXPOSE 80
ENTRYPOINT [ "./entrypoint.sh" ]

