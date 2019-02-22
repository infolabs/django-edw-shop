FROM python:2.7-slim-stretch

RUN echo "Europe/Moscow" > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata && \
    \
    apt -y update && \
    apt -y install \
        apt-utils \
        git \
        gcc \
        g++ \
        curl \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        openssh-server \
        gettext \
        libxml2-dev \
        libxslt-dev \
        libssl-dev \
        sqlite3

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt && \
    rm -rf /tmp/requirements.txt

RUN mkdir /app \
          /django-edw \
          /django-edw-shop

WORKDIR /app/

