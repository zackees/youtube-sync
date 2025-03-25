# Base image
FROM mcr.microsoft.com/playwright:v1.51.1-noble

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive



# Optional tools
RUN curl https://rclone.org/install.sh | sudo bash
RUN pip install -U magic-wormhole uv --break-system-packages

# Install Playwright (Python version) and its browser binaries
RUN pip install --break-system-packages playwright && \
    playwright install --with-deps

# Create a non-root user
RUN useradd -m -u 1001 -s /bin/bash user
RUN mkdir -p /app && chown -R user:user /app

# Set up working directory
WORKDIR /app
USER user

# Set temp dir
RUN mkdir -p /mytemp
ENV TMPDIR=/mytemp

# Dependency setup
COPY pyproject.toml ./
RUN uv venv && uv pip install -r pyproject.toml

COPY --chown=user:user . /app
RUN uv pip install -e .

# Runtime config
EXPOSE 80
ENV PORT=80
ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket

# Entrypoint
CMD ["uv", "run", "entrypoint.py"]
