.. _howto:

How To Guides
=============


.. _scxml_howto:

(ROS) SCXML Model Implementation
---------------------------------

SCXML is the language of choice to model the autonomous systems that are processed by AS2FM.

It relies on multiple SCXML files, each one representing a different state-based automaton, to represent a complete system.
Those automata can exchange data and synchronize their execution through the use of **events**.

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

In this example, the SCXML model consists of three states, `s0`, `s1`, and `s2`, and three transitions, triggered by the events `e1`, `e2` and `e3`, respectively. Each transition advances the automaton's current state to the next one.
Additionally, on each transition, a counter is incremented.

The events are expected to be sent by another SCXML model, similarly to how it is done in the `s2` state.

In order to make SCXML fit more to the typical robotics tech-stack, we extended the default SCXML language to support ROS specific features and Behavior Trees.

The following sections guide you through the process of :ref:`creating a SCXML model of a ROS node <ros_node_scxml>` and of a :ref:`BT plugin <bt_plugin_scxml>` that can be processed by AS2FM.


.. _ros_node_scxml:

Creating an SCXML model of a ROS node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In AS2FM, we extended the SCXML language with some additional functionalities, to support the following ROS specific features:

* :ref:`ROS Timers <ros_timers>`: to trigger callbacks at a specific rate
* :ref:`ROS Topics <ros_topics>`: to publish-receive messages via a ROS topic
* :ref:`ROS Services <ros_services>`: to call a ROS service and implement service servers
* :ref:`ROS Actions <ros_actions>`: to call a ROS action and implement action servers (under development)

All functionalities require the interface to be declared before being used, similarly to how ROS requires the interfaces to be declared in a node.
In (ROS) SCXML, this is done similarly to how variables are defined in the data model.

.. _ros_timers:

ROS Timers
___________

ROS Timers are used to trigger callbacks (behaving like an SCXML transition) at a specific rate. They can be declared as follows:

.. code-block:: xml

    <ros_time_rate rate_hz="1" name="my_timer" />

This will create a ROS timer that triggers the related callbacks at a rate of 1 Hz, w.r.t. the internal, simulated time.

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

ROS topics are used to publish (via a ROS Publisher) and receive (via a ROS Subscriber) messages via a ROS topic across different automata. They can be declared as follows:

.. code-block:: xml

    <!-- ROS Topic Subscriber -->
    <ros_topic_subscriber name="bool_topic" topic="/topic1" type="std_msgs/Bool" />
    <!-- ROS Topic Publisher -->
    <ros_topic_publisher name="int_topic" topic="/topic2" type="std_msgs/Int32" />

The two declarations above will create a ROS subscriber called `bool_topic` that reads messages of type `std_msgs/Bool` from the topic `/topic1` and a ROS publisher called `int_topic` that writes messages of type `std_msgs/Int32` on the topic `/topic2`.
The `name` argument is optional, and if not provided, it will be set to the same value as the `topic` argument.

Once created, subscribers and publishers can be referenced using their names (`bool_topic` and `int_topic`), and can be used in the states to send messages and perform callbacks upon receiving messages:

.. code-block:: xml

    <datamodel>
        <data id="internal_bool" expr="True" type="bool" />
    </datamodel>

    <state id="src_state">
        <ros_topic_callback name="bool_topic" target="target_state">
            <assign location="internal_var" expr="_msg.data" />
        </ros_topic_callback>
    </state>

    <state id="target_state">
        <onentry>
            <if cond="internal_bool">
                <ros_topic_publish name="int_topic" >
                    <field name="data" expr="10">
                </ros_topic_publish>
            <else />
                <ros_topic_publish name="int_topic" >
                    <field name="data" expr="20">
                </ros_topic_publish>
            </if>
        </onentry>
        <transition target="src_state" />
    </state>

Note that the `ros_topic_publish` can be used where one would normally use executable content in SCXML: in `transition`, in `onentry` and `onexit` tags.
The `ros_topic_callback` tag is similarly to the `ros_rate_callback` used like a transition and will transition the state machine to the state declared in `target` upon receiving a message.
Executable content within it can use `_msg` to access the message content.

.. _ros_services:

ROS Services
____________

ROS services are used to provide, for a given service name, one server and, possibly, multiple clients.
The clients make a request and the server provides a response to that request only to the client that made the request.

The declaration of a ROS service server and the one of a client can be achieved like this:

.. code-block:: xml

    <!-- ROS Service Server -->
    <ros_service_server name="the_srv" service_name="/service1" type="std_srvs/SetBool" />
    <!-- ROS Service Client -->
    <ros_service_client name="the_client" service_name="/service2" type="std_srvs/Trigger" />

Once created, servers and clients can be referenced using the provided `name` (i.e., `the_srv` and `the_client`), and can be used in the states of an SCXML model to provide and request services.
In the following, an exemplary client is provided:

.. code-block:: xml

    <datamodel>
        <data id="internal_bool" expr="False" type="bool" />
    </datamodel>

    <state id="send_req">
        <onentry>
            <ros_service_send_request name="the_client">
            </ros_service_send_request>
        </onentry>
        <ros_service_handle_response name="the_client" target="done">
            <assign location="internal_bool" expr="_res.success" />
        </ros_service_handle_response>
    </state>

To send a request, the `ros_service_send_request` can be used where any other executable content may be used.
After the server has processed the service, `ros_service_handle_response` can be used similarly to an SCXML transition and is triggered when a response from the server is received.
The data of the request can be accessed with the `_res` field.

And here comes an example of a server:

.. code-block:: xml

    <datamodel>
        <data id="temp_data" type="bool" expr="False" />
    </datamodel>

    <state id="idle">
        <ros_service_handle_request name="the_srv" target="idle">
            <assign location="temp_data" expr="_req.data" />
            <ros_service_send_response name="the_srv">
                <field name="success" expr="temp_data" />
            </ros_service_send_response>
        </ros_service_handle_request>
    </state>

A service request from a client will trigger the `ros_service_handle_request` callback which transitions the automaton to the state declared in `target` (it is a self loop in the example).
After processing the request the server must use the `ros_service_send_response` to send the response.


.. _ros_actions:

ROS Actions
___________

TODO


.. _bt_plugin_scxml:

Creating an SCXML model of a BT plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SCXML models of BT plugins can be done similarly to the ones for ROS nodes. However, in BT plugins there are a few special functionalities that are provided:

* :ref:`BT communication <bt_communication>`: A set of special events that are used in each BT plugin for starting a BT node and providing results.
* :ref:`BT Ports <bt_ports>`: A special BT interface to parametrize a specific plugin instance.


.. _bt_communication:

BT Communication
_________________

TODO: describe `bt_tick`, `bt_running`, `bt_success`, `bt_failure`.


.. _bt_ports:

BT Ports
________

Additionally, when loading a BT plugin in the BT XML tree, it is possible to configure a specific plugin instance by means of the BT ports.

As in the case of ROS functionalities, BT ports need to be declared before being used, to provide the port name and expected type.

.. code-block:: xml

    <bt_port key="my_string_port" type="string" />
    <bt_port key="start_value" type="int32">

Once declared, it is possible to reference to the port in multiple SCXML entries.

For example, we can use `my_string_port` to define the topic used by a ROS publisher.

.. code-block:: xml

    <ros_topic_publisher name="int_topic" type="std_msgs/Int32">
        <topic>
            <bt_get_input key="my_string_port" />
        </topic>
    </ros_topic_publisher>

Or we can use `start_value` to define the initial value of a variable.

.. code-block:: xml

    <datamodel>
        <data id="counter" type="int32">
            <expr>
                <bt_get_input key="start_value" />
            </expr>
        </data>
    </datamodel>


BT ports can also be linked to variables in the `BT Blackboard` by wrapping the variable name in curly braces in the BT XML file. However, this feature is not yet supported.


.. _additional_params_howto:

Additional Parameters for the Main XML file
-------------------------------------------


.. _max_time_tag:

Max Time
~~~~~~~~

TODO
