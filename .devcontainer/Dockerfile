# Dev container for Span Panel Home Assistant integration
FROM mcr.microsoft.com/devcontainers/python:3.13

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    # For markdownlint-cli2
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install markdownlint-cli2 globally for pre-commit hooks
RUN npm install -g markdownlint-cli2

# Install Poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VERSION=2.1.3
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# Configure Poetry to create virtualenvs in project directory
RUN poetry config virtualenvs.in-project true

# Set working directory
WORKDIR /workspaces/span

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock* ./

# Note: Dependencies will be installed in post-create.sh
# because we need access to the sibling span-panel-api directory
