#!/bin/bash
source /opt/ros/jazzy/setup.bash
source /colcon_ws/install/setup.bash

# Execute what was passed into this entrypoint.
exec "$@"
