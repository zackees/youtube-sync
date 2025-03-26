# Base image
FROM mcr.microsoft.com/playwright:v1.51.1-noble

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3-pip

# Optional tools
# RUN curl https://rclone.org/install.sh | sudo bash
RUN pip3 install -U magic-wormhole uv --break-system-packages



# Set up working directory
WORKDIR /app

# Set temp dir
RUN mkdir -p /mytemp
ENV TMPDIR=/mytemp

COPY pre-requirements.txt ./
RUN uv venv
RUN uv pip install -r pre-requirements.txt
RUN uv run playwright install chromium

# Install dependencies
RUN apt-get install -y \
      xvfb \
    #   nss \
    #   freetype \
    #   freetype-dev \
      #harfbuzz \
      ca-certificates \
#      ttf-freefont \
      chromium \
      chromium-chromedriver

# Dependency setup
COPY pyproject.toml ./
RUN uv pip install -r pyproject.toml

COPY . /app
RUN uv pip install -e .

# Runtime config
EXPOSE 80
ENV PORT=80
ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket

# Entrypoint
CMD ["uv", "run", "entrypoint.py"]
