FROM ros:foxy

# Install requirements
RUN apt update\
    && apt install -y python3-pip wget tar\
    && rm -rf /var/lib/apt/lists/*

# Get SMC Storm
RUN wget https://github.com/convince-project/smc_storm/releases/latest/download/smc_storm_executable.tar.gz
RUN tar -xzf smc_storm_executable.tar.gz
RUN ./install.sh --install-dependencies

# Add AS2FM
ADD . as2fm
RUN python3 -m pip install as2fm/
