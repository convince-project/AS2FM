FROM ros:jazzy
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install requirements
ARG DEBIAN_FRONTEND=noninteractive
RUN apt update && \
    apt install -y python3-pip curl tar && \
    rm -rf /var/lib/apt/lists/*

# Get SMC Storm
RUN mkdir /smc_storm_executable
RUN curl -O -L https://github.com/convince-project/smc_storm/releases/download/0.0.7/smc_storm_executable.tar.gz
RUN tar -xzf smc_storm_executable.tar.gz -C /smc_storm_executable
RUN cd /smc_storm_executable && \
    ./install.sh --install-dependencies && \
    rm -rf /var/lib/apt/lists/*
RUN ln /smc_storm_executable/bin/smc_storm /usr/local/bin

# Add AS2FM
COPY . as2fm
RUN pip3 install --break-system-packages as2fm/
