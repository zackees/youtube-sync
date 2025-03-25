# Base image
FROM ubuntu:25.04

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y \
    wget curl gnupg sudo aria2 unzip \
    build-essential libssl-dev libffi-dev python3-dev \
    libgtk-3-dev libnotify-dev libnss3 libxss1 libasound2t64 \
    libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libxfixes3 libxi6 libxrandr2 \
    libxrender1 libxss1 libxtst6 fonts-liberation lsb-release \
    xdg-utils libgbm-dev libappindicator3-1 ca-certificates bash \
    software-properties-common python3-pip

    
RUN curl https://rclone.org/install.sh | sudo bash

RUN apt-get install -y firefox

# Install geckodriver manually
ENV GECKODRIVER_VERSION=v0.36.0
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" && \
    tar -xzf "geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" -C /usr/local/bin && \
    rm "geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" && \
    chmod +x /usr/local/bin/geckodriver


# Temporary directory
RUN mkdir -p /mytemp && chmod 1777 /mytemp
ENV TMPDIR=/mytemp

# Python tools
RUN pip install -U magic-wormhole uv --break-system-packages

# Create non-root user
RUN useradd -m -u 1001 -s /bin/bash user
RUN mkdir -p /app && chown -R user:user /app

# Switch to user
WORKDIR /app
USER user

# Install dependencies
COPY pyproject.toml .
RUN uv venv && uv pip install -r pyproject.toml

COPY --chown=user:user . /app
RUN uv pip install -e .

EXPOSE 80
ENV PORT=80

CMD ["uv", "run", "entrypoint.py"]
