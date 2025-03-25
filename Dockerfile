FROM ubuntu:25.04


# Might be necessary.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update

# Install required packages for Chrome
RUN apt-get install -y wget gnupg

RUN apt-get install -y build-essential libssl-dev libffi-dev python3-dev
RUN apt-get install -y libgtk-3-dev libnotify-dev libnss3 libxss1 libasound2t64

# From stack overflow. TODO: Remove the ones that aren't needed.


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



# RUN apt-get install -y --fix-missing gconf-service

# RUN apt-get install -y --fix-missing libasound2
# RUN apt-get install -y --fix-missing libatk1.0-0
# RUN apt-get install -y --fix-missing libc6
# RUN apt-get install -y --fix-missing libcairo2
# RUN apt-get install -y --fix-missing libcups2
# RUN apt-get install -y --fix-missing libdbus-1-3
# RUN apt-get install -y --fix-missing libexpat1
# RUN apt-get install -y --fix-missing libfontconfig1
# RUN apt-get install -y --fix-missing libgcc1
# RUN apt-get install -y --fix-missing libgconf-2-4


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

RUN apt-get install -y python3-pip


RUN apt-get install -y ca-certificates
RUN apt-get install -y --fix-missing bash

# Add Chrome repository and install specific version of Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable

# Install ChromeDriver 114.0.5735.90 (which is compatible with Chrome 114)
RUN mkdir -p /opt/chromedriver && \
    wget -q https://storage.googleapis.com/chrome-for-testing-public/114.0.5735.90/linux64/chromedriver-linux64.zip -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /opt/chromedriver/ && \
    chmod +x /opt/chromedriver/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

# Add ChromeDriver to PATH
ENV PATH="/opt/chromedriver:${PATH}"

RUN mkdir -p /mytemp && chmod 1777 /mytemp
ENV TMPDIR=/mytemp

RUN pip install -U magic-wormhole uv --break-system-packages

# Add after the initial FROM statement and before any installations
RUN useradd -m -u 1001 -s /bin/bash user

# Add near the end of the file, before the WORKDIR directive
# Change ownership of the app directory to the new user
RUN mkdir -p /app && chown -R user:user /app


# Ensure /app is owned by the new user
WORKDIR /app
USER user

# Add requirements and install
COPY  pyproject.toml .

RUN uv venv && \
    uv pip install -r pyproject.toml

COPY . .

RUN uv pip install -e .

# ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket
EXPOSE 80
ENV PORT=80

CMD ["uv", "run", "entrypoint.py"]
