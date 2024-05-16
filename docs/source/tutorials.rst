Tutorials
=========

The scripts have been tested with Python 3.10 and pip version 24.0. 

Installation
--------------
To run the Python script install the required dependencies with the following commands:

.. code-block:: bash

    python3 -m pip install mc_toolchain_jani_common/
    python3 -m pip install jani_generator/
    python3 -m pip install scxml_converter/

How to convert from CONVINCE robotic JANI to plain JANI?
-----------------------------------------------------------

We provide a Python script to convert models describing the system and its environment together, given in the CONVINCE robotics JANI flavor as specified in the `data model repository <https://github.com/convince-project/data-model>`_, into `plain JANI <https://jani-spec.org>`_ accepted as input by model checkers.

Running the script
```````````````````

After it has been installed, the script can be run on a CONVINCE robotics JANI model. It outputs a plain JANI conversion.

.. code-block:: bash

    convince_to_plain_jani --convince_jani path_to_convince_robotic_file.jani --output output_plain_file.jani


Example
`````````

Let's convert a first simple robotic JANI model. An example can be found in `here <https://github.com/convince-project/mc-toolchain-jani/blob/main/jani_generator/test/_test_data/convince_jani/first-model-mc-version.jani>`_. The environment model describes a room with three straight edges and one edge with a small corner in the middle. The room describing the environment in which the robot operates looks like this:

.. image:: graphics/room.PNG
    :width: 200
    :alt: An image illustrating the room's shape.

Lengths are given in meters. 
The robot is placed at coordinates (0.5, 0.5) initially, and has a round shape with a radius of 0.3 m and a height of 0.2 m. In the small and simple example there are no further obstacles and the robot drives with a linear and angular velocity of 0.5 m/s and 0.5 rad/s, respectively.

The behavior describing how the robot drives around in the room is modeled as a Deterministic Markov Chain (DTMC) shown in the picture below. In each step, the robot moves forward in 50% of the cases and rotates in 50% of the cases. In case it bumps into a wall, it just stops at the collision point and continues operating from there. What is omitted in the picture is the calculation of this collision point and and the conversion to and from floats to integers. The latter is only necessary to make the example run in Storm because the tool currently does not support transient floats.

.. image:: graphics/dtmc.PNG
    :width: 800
    :alt: An image of the DTMC representing the robot's behavior.

The property given in the JANI file checks for the minimal probability that eventually within 10 000 steps the position (1.0, 1.0) is reached with an error range of 0.05 m.






How to convert from (SC)XML to plain JANI?
--------------------------------------------

But writing a JANI model by hand is quite difficult. Therefore we also developed an approach to directly extract a JANI model from the robotic system specified in (SC)XML files, e.g., for the ROS nodes, the environment, the behavior tree, and the interaction of those components. 

Running the script
`````````````````````

A full system model can be converted into a model-checkable JANI file as follows.

.. code-block:: bash

    scxml_to_jani path_to_main.xml


Structure of input
`````````````````````

The `scxml_to_jani` tool takes an XML file, e.g. `main.xml <https://github.com/convince-project/mc-toolchain-jani/tree/main/jani_generator/test/_test_data/ros_example/main.xml>`_. With the following content:

* one or multiple ROS nodes in SCXML:

    .. code-block:: xml

        <input type="ros-scxml" src="./battery_manager.scxml" />

* the environment model in SCXML:

    .. code-block:: xml

        <input type="ros-scxml" src="./battery_drainer.scxml" />

* the behavior tree in XML (to be implemented), 
* the plugins of the behavior tree leaf nodes in SCXML (to be implemented),
* the property to check in temporal logic, currently given in JANI, later support for XML will be added:

    .. code-block:: xml

        <properties>
            <input type="jani" src="./battery_depleted.jani" />
        </properties>

* additionally, commonly shared variables for synchronization between the components are specified in the main file:
  
    .. code-block:: xml

        <mc_parameters>
            <max_time value="100" unit="s" />
        </mc_parameters>

All of those components are converted into one JANI DTMC model by the ``scxml_to_jani`` tool.


Example
`````````

We demonstrate the usage of this conversion for a full model based on an example of a battery which is continuously drained. 
All input files can be found in this `folder <https://github.com/convince-project/mc-toolchain-jani/tree/main/jani_generator/test/_test_data/ros_example>`_. The core functionality of the battery drainer is implemented in `battery_drainer.scxml <https://github.com/convince-project/mc-toolchain-jani/tree/main/jani_generator/test/_test_data/ros_example/battery_drainer.scxml>`_. 
The battery is drained by 1% at a frequency of 1 Hz given by the ros time rate ``my_timer``.
The percentage level of the battery is stored in ``battery_percent``. The current state of the battery is published on a ROS topic ``level``.

In addition, there is the `battery_manager.scxml <https://github.com/convince-project/mc-toolchain-jani/tree/main/jani_generator/test/_test_data/ros_example/battery_manager.scxml>`_ file. The manager subscribes to the ``level`` topic of the battery drainer to check its level and sets the ``battery_alarm`` to true as soon as the ``level`` is less than 30%. 
This means there is a communication between the two processes described by the drainer and the manager.

The JANI property given in `battery_depleted.jani <https://github.com/convince-project/mc-toolchain-jani/tree/main/jani_generator/test/_test_data/ros_example/battery_depleted.jani>`_ defines the property of interest to be model checked. In this case, it calculates the minimal probability that the battery level is below or equal to zero eventually, i.e., all we verify here is that the battery is empty at some point.

In the `main.xml file <https://github.com/convince-project/mc-toolchain-jani/tree/main/jani_generator/test/_test_data/ros_example/main.xml>`_ introduced earlier, the maximum run time of the system is specified with ``max_time`` and shared across the components. To make sure that the model checked property is fulfilled with probability 1, the allowed runtime needs to be high enough to have enough time to deplete the battery, i.e., in this example the maximal time needs to be at least 100s because the battery is depleted by 1% per second.
In addition, in this main file, all the components of the example are put together, and the property to use is indicated. 


How to model check the robotic system?
----------------------------------------

The resulting JANI model from one of the approaches above can then be given to any model checker accepting JANI as an input format and being able to handle DTMC models. This could for example be the `Storm SMC extension smc-storm <https://github.com/convince-project/smc_storm>`_, which we developed as part of the CONVINCE toolchain. Check out the documentation of SMC Storm for further details.
It can also be checked with external tools accepting JANI as input, e.g., the other engines of the `Storm model checker <https://stormchecker.org>`_ or the `Modest Toolset <https://modestchecker.net>`_.