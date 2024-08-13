How To guides
=============


.. _scxml_howto:

(ROS) SCXML Model Implementation
---------------------------------

SCXML is the language of choice to model the autonomous systems that we will be processed by AS2FM.

It relies on multiple SCXML files, each one representing a different state-based automaton, to represent a complete system.
Those automaton can exchange data and synchronize their execution through the use of **events**.

A simple, exemplary SCXML model is shown below:

.. code-block:: xml

    <scxml xmlns="http://www.w3.org/2005/07/scxml" version="1.0" initial="s0">
        <datamodel>
            <data id="counter" expr="0"/>
        </datamodel>
        <state id="s0">
            <transition event="e1" target="s1">
                <assign location="counter" expr="counter + 1"/>
            </transition>
        </state>
        <state id="s1">
            <transition event="e2" target="s2">
                <assign location="counter" expr="counter + 1"/>
            </transition>
        </state>
        <state id="s2">
            <onentry>
                <send event="extra_event"/>
            </onentry>
            <transition event="e3" target="s0">
                <assign location="counter" expr="counter + 1"/>
            </transition>
        </state>
    </scxml>

In this example, the SCXML model consists of three states, `s0`, `s1`, and `s2`, and three transitions, `e1`, `e2` and `e3`, that transition each state to the next one.
Additionally, on each transition, a counter is incremented.

The events are expected to be sent by another scxml model, similarly to how it is done in the `s2` state.

In order to make it more appealing to robotics developers, we have extended the default SCXML language with some ROS and BT specific features.

The following sections will guide you through the process of :ref:`creating a SCXML model of a ROS node <ros_node_scxml>` and of a :ref:`BT plugin <bt_plugin_scxml>` that can be processed by AS2FM.


.. _ros_node_scxml:

Creating a SCXML model of a ROS node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In AS2FM, we extended the SCXML language with some additional functionalities, to support the following ROS specific features:

* **ROS Timers**: to schedule events at a specific rate
* **ROS Topics**: to publish-receive messages via a ROS topic
* **ROS Services**: to call a ROS service and implement service servers
* **ROS Actions**: to call a ROS action and implement action servers (under development)

All functionalities require the interface to be declared before being used, similarly to variables in the SCXML datamodel.


ROS Timers
___________

ROS Timers are used to schedule events at a specific rate. They can be declared as follows:

.. code-block:: xml

    <ros_time_rate rate_hz="1" name="my_timer" />

This will create a ROS Timer that triggers the related callbacks at a rate of 1 Hz, w.r.t. the internal, simulated time.

The timer callbacks can be used similarly to SCXML transitions, and are specified as follows:

.. code-block:: xml

    <state id="src_state">
        <ros_rate_callback name="my_timer" target="target_state" cond="cond_expression">
            <assign location="internal_var" expr="some_expression" />
        </ros_rate_callback>
    </state>

Assuming the automaton is in the `src_state`, the transition to `target_state` will be triggered by the timer `my_timer`, if the condition `cond_expression` holds.
Additionally, the internal variable `internal_var` will be updated with the value of `some_expression` when that transition is performed.


ROS Topics
___________

TODO


ROS Services
____________

TODO


ROS Actions
___________

TODO


.. _bt_plugin_scxml:

Creating a SCXML model of a BT plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO
