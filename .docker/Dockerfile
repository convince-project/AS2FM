FROM ros:jazzy AS moco
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install requirements
ARG DEBIAN_FRONTEND=noninteractive
RUN apt update && \
    apt install -y python3-pip curl tar nano ros-jazzy-example-interfaces ros-jazzy-plotjuggler && \
    rm -rf /var/lib/apt/lists/*

# Get SMC Storm
RUN mkdir /smc_storm_executable
RUN curl -O -L https://github.com/convince-project/smc_storm/releases/latest/download/smc_storm_executable.tar.gz
RUN tar -xzf smc_storm_executable.tar.gz -C /smc_storm_executable
RUN cd /smc_storm_executable && \
    ./install.sh --install-dependencies && \
    rm -rf /var/lib/apt/lists/*
RUN ln /smc_storm_executable/bin/smc_storm /usr/local/bin

# Add MOCO
RUN mkdir -p /colcon_ws/src
COPY . /colcon_ws/src/moco
#TODO fix package name once release is up
RUN pip3 install --break-system-packages /colcon_ws/src/moco[dev]  


# Make ROS workspace and build it
RUN source /opt/ros/jazzy/setup.bash && \
    cd /colcon_ws && \
    colcon build

# Set up the entrypoint.
CMD /bin/bash
COPY .docker/entrypoint.sh /entrypoint.sh
RUN chmod +x entrypoint.sh
WORKDIR /colcon_ws/src/moco

ENTRYPOINT [ "/entrypoint.sh" ]
