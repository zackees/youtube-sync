# FROM ubuntu:22.04
FROM python:3.10.4-slim-bullseye


# Might be necessary.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ENV DEBIAN_FRONTEND=noninteractive

# From stack overflow. TODO: Remove the ones that aren't needed.
RUN apt-get update
RUN apt-get install -y --fix-missing \
  sudo \
  curl \
  gconf-service libasound2 \
  libatk1.0-0 libc6 libcairo2 \
  libcups2 libdbus-1-3 libexpat1 \
  libfontconfig1 libgcc1 \
  libgconf-2-4 libgdk-pixbuf2.0-0 \
  libglib2.0-0 libgtk-3-0 \
  libxfixes3 libxi6 libxrandr2 \
  libxrender1 libxss1 libxtst6 \
  fonts-liberation libnss3 \
  lsb-release xdg-utils wget libgbm-dev


RUN pip install --upgrade pip
# Install the necessary packages, magic-wormhole to get files off the container easily
# and uv to run the app.
RUN python -m pip install -U \
  magic-wormhole \
  uv

WORKDIR /app
# Add requirements file and install.

COPY pyproject.toml .

RUN uv venv
RUN uv pip install -r pyproject.toml
COPY . .
RUN uv pip install -e .

RUN apt-get install -y ca-certificates

ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket

# Expose the port and then launch the app.
EXPOSE 80

#Blah
#CMD ["python", "-m", "http.server", "80"]
CMD ["uv", "run", "-m", "youtube_sync.cli.sync_multiple", "config.json"]