Tutorials
=========

The scripts have been tested with Python 3.8.10 and pip version 24.0. 

How to convert from CONVINCE robotic Jani to plain Jani?
-----------------------------------------------------------

We provide a Python script to convert models describing the system and its environment together, given in the CONVINCE robotics Jani flavor as specified in the `data model repository <https://github.com/convince-project/data-model>`_, into `plain JANI <https://jani-spec.org>`_ accepted as input by model checkers.

1. Installation using pip

To run the Python script install the required dependencies with the following command:

```bash
cd <path-to-convince_toolchain>/jani_generator
python3 -m pip install -e .
```

2. Running the script

After it has been installed, the script can be run on a CONVINCE robotics Jani model. It outputs a plain Jani conversion.

```bash
convince_to_plain_jani --convince_jani path_to_convince_file.jani --output output_plain_file.jani
```

3. Example

Let's convert a first simple robotic Jani model. An example can be found in `jani_generator/test/_test_data/first-model-mc-version.jani`. The environment model describes a room with three straight edges and one edge with a small corner in the middle. The room describing the environment in which the robot operates looks like this:

.. image:: graphics/room.PNG
    :width: 200
    :alt: An image illustrating the room's shape

Lengths are given in meters. 
The robot is placed at coordinates (0.5, 0.5) initially, and has a round shape with a radius of 0.3 m and a height of 0.2 m. In the small and simple example there are no further obstacles and the robot drives with a linear and angular velocity of 0.5 m/s and 0.5 rad/s, respectively.

The behavior describing how the robot drives around in the room is modeled as a Deterministic Markov Chain (DTMC). In each step, the robot moves forward in 50% of the cases and rotates in 50% of the cases. In case it bumps into a wall, it just stops at the collision point and continues operating from there.

The property given in the Jani file checks for the minimal probability that eventually within 10 000 steps the position (1.0, 1.0) is reached with an error range of 0.05 m.

How to convert from (Sc)XML to plain Jani?
--------------------------------------------
A full system model can be converted into a model-checkable Jani file as follows.

1. Installation using pip

```bash
cd <path-to-convince_toolchain>
python3 -m pip install -e mc_toolchain_jani_common
python3 -m pip install -e scxml_converter
```

The `main.py` script takes 

* the property to check in temporal logic, currently given in Jani, later support for ScXML will be added, 
* the behavior tree in XML, 
* one or multiple nodes in ScXML,
* the plugins of the nodes in ScXML, and
* the environment model in ScXML

and converts all of those components into one Jani DTMC model.

We demonstrate the usage of this conversion for a full model based on an example of a battery which is continuously drained. 
In `jani_generator/test/_test_data/ros_example` all input files can be found. The core functionality of the battery drainer is implemented in `battery_drainer.scxml`. The percentage level of the battery is stored in `battery_percent`. The current `level` of the battery is published on a ROS topic. The battery can be used, which sends the `level`` of the battery on that topic and reduces `battery_percent` by one.
All of that happens with a frequency of 1 Hz given by the ros time rate `my_timer`.
In addition, there is the `battery_manager.scxml` file. The manager subscribed to the `level` topic of the battery drainer to check its level and sends a `battery_alarm` as soon as the `level` is less or equal 30%. 
This means there is a communication between the two processes described by the drainer and the manager.
In `main.xml` the two processes are put together, the time resolution is specified and the property to use is indicated. 
The Jani property given in `battery_depleted.jani` checks the minimal probability that the battery level is below or equal to zero eventually.


How to model check the robotic system?
----------------------------------------

The resulting Jani model from one of the approaches above can then be given to any model checker accepting Jani as an input format and being able to handle DTMC models. This could for example be the `Storm SMC extension smc-storm <https://github.com/convince-project/smc_storm>`_, which we developed as part of the CONVINCE toolchain. Check out the documentation of SMC Storm for further details.