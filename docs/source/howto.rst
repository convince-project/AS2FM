How To Guides
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
            <data id="counter" expr="0" type="int16"/>
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

* :ref:`ROS Timers <ros_timers>`: to schedule events at a specific rate
* :ref:`ROS Topics <ros_topics>`: to publish-receive messages via a ROS topic
* :ref:`ROS Services <ros_services>`: to call a ROS service and implement service servers
* :ref:`ROS Actions <ros_actions>`: to call a ROS action and implement action servers (under development)

All functionalities require the interface to be declared before being used, similarly to variables in the SCXML datamodel.


.. _ros_timers:

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


.. _ros_topics:

ROS Topics
___________

ROS Topics are used to publish (via a ROS Publisher) and receive (via a ROS Subscriber) messages via a ROS topic across different automata. They can be declared as follows:

.. code-block:: xml

    <!-- ROS Topic Subscriber -->
    <ros_topic_subscriber topic="/topic1" type="std_msgs/Bool" />
    <!-- ROS Topic Publisher -->
    <ros_topic_publisher topic="/topic2" type="std_msgs/Int32" />

Once created, subscribers and publishers can be referenced using the `topic` name, and can be used in the states to send messages and perform callbacks upon messages receipt, as in the following:

.. code-block:: xml

    <datamodel>
        <data id="internal_bool" expr="True" type="bool" />
    </datamodel>

    <state id="src_state">
        <ros_topic_callback topic="/topic1" target="target_state">
            <assign location="internal_var" expr="_msg.data" />
        </ros_topic_callback>
    </state>

    <state id="target_state">
        <onentry>
            <if cond="internal_bool">
                <ros_topic_publish topic="/topic2" >
                    <field name="data" expr="10">
                </ros_topic_publish>
            <else />
                <ros_topic_publish topic="/topic2" >
                    <field name="data" expr="20">
                </ros_topic_publish>
            </if>
        </onentry>
        <transition target="src_state" />
    </state>


.. _ros_services:

ROS Services
____________

ROS Services are used to provide, for a given topic, one server and, possibly, multiple clients.
The clients makes a request and the server provides a response to that request only to the client that made the request.

The declaration of a ROS Service server and the one of a client looks as in the following:

.. code-block:: xml

    <!-- ROS Service Server -->
    <ros_service_server service_name="/service1" type="std_srvs/SetBool" />
    <!-- ROS Service Client -->
    <ros_service_client service_name="/service2" type="std_srvs/Trigger" />

Once created, servers and clients can be referenced using the `service_name` name, and can be used in the states of a SCXML model to provide and request services.
In the following, an exemplary client is provided:

.. code-block:: xml

    <datamodel>
        <data id="internal_bool" expr="False" type="bool" />
    </datamodel>

    <state id="send_req">
        <onentry>
            <ros_service_send_request service_name="/service2">
            </ros_service_send_request>
        </onentry>
        <ros_service_handle_response service_name="/service2" target="done">
            <assign location="internal_bool" expr="_res.success" />
        </ros_service_handle_response>
    </state>

And here, an example of a server:

..code-block:: xml

    <datamodel>
        <data id="temp_data" type="bool" expr="False" />
    </datamodel>

    <state id="idle">
        <ros_service_handle_request service_name="/service1" target="idle">
            <assign location="temp_data" expr="_req.data" />
            <ros_service_send_response service_name="/adder">
                <field name="success" expr="temp_data" />
            </ros_service_send_response>
        </ros_service_handle_request>
    </state>


.. _ros_actions:

ROS Actions
___________

TODO


.. _bt_plugin_scxml:

Creating a SCXML model of a BT plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO
