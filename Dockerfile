# FROM ubuntu:22.04
FROM python:3.10.4-slim-bullseye


# Might be necessary.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ENV DEBIAN_FRONTEND=noninteractive

# From stack overflow. TODO: Remove the ones that aren't needed.
RUN apt-get update

RUN apt-get install -y bash
RUN apt-get install -y --fix-missing -o Acquire::Retries=5 software-properties-common

#RUN add-apt-repository ppa:apt-fast/stable -y && \
#    apt-get update && \
#    apt-get -y install apt-fast

ENV ARIA2_OPTS="--disable-ipv6"


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gnupg \
    curl \
    wget \
    sudo \
    aria2
    
RUN mkdir -p /etc/apt/keyrings

RUN curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xBC5934FD3DEBD4DAEA544F791E2824A7F22B44BD" \
    | gpg --dearmor -o /etc/apt/keyrings/apt-fast.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/apt-fast.gpg] http://ppa.launchpad.net/apt-fast/stable/ubuntu focal main" \
    > /etc/apt/sources.list.d/apt-fast.list 
    
RUN apt-get update && apt-get install -y apt-fast

# RUN apt-get install -y --no-install-recommends sed

# # Use a mirror for debian packages.
# RUN sed -i 's|http://deb.debian.org/debian|http://ftp.us.debian.org/debian|g' /etc/apt/sources.list && \
#     sed -i 's|http://security.debian.org/debian-security|http://ftp.us.debian.org/debian-security|g' /etc/apt/sources.list



RUN apt-get install -y --fix-missing gconf-service

RUN apt-get install -y --fix-missing libasound2
RUN apt-get install -y --fix-missing libatk1.0-0
RUN apt-get install -y --fix-missing libc6
RUN apt-get install -y --fix-missing libcairo2
RUN apt-get install -y --fix-missing libcups2
RUN apt-get install -y --fix-missing libdbus-1-3
RUN apt-get install -y --fix-missing libexpat1
RUN apt-get install -y --fix-missing libfontconfig1
RUN apt-get install -y --fix-missing libgcc1
RUN apt-get install -y --fix-missing libgconf-2-4


RUN apt-get install -y --fix-missing \
  libgdk-pixbuf2.0-0 \
  libglib2.0-0 \
  libgtk-3-0 \
  libxfixes3 \
  libxi6 \
  libxrandr2 \
  libxrender1 \
  libxss1 \
  libxtst6 \
  fonts-liberation \
  libnss3 \
  lsb-release \
  xdg-utils \
  libgbm-dev \
  libappindicator3-1


# fix on gihtub runner
# run: |
# sudo apt-get -y install fluxbox
# Xvfb :99 &
# fluxbox -display :99 &
# echo "DISPLAY=:99" >> "$GITHUB_ENV"

RUN apt-get install -y --fix-missing fluxbox
RUN apt-get install -y --fix-missing xvfb



RUN apt-get install -y ca-certificates
RUN apt-get install -y --fix-missing bash

RUN mkdir -p /mytemp && chmod 1777 /mytemp
ENV TMPDIR=/mytemp

RUN pip install --upgrade pip && \
    pip install -U magic-wormhole uv

# ---- ADD NON-ROOT USER HERE ----
# Create a non-root user and group
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Ensure /app is owned by the new user
RUN mkdir -p /app && chown appuser:appuser /app
WORKDIR /app

# Switch to non-root user from this point on
USER appuser

# Add requirements and install
COPY --chown=appuser:appuser pyproject.toml .

RUN uv venv && \
    uv pip install -r pyproject.toml

COPY --chown=appuser:appuser . .

RUN uv pip install -e .

ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket
EXPOSE 80
ENV PORT=80

CMD ["uv", "run", "entrypoint.py"]
