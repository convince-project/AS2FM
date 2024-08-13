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

TODO

.. _bt_plugin_scxml:

Creating a SCXML model of a BT plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO
