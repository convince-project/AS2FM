.. _howto:

How To Guides
=============


.. _scxml_howto:

High Level SCXML Model Implementation
-------------------------------------

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

As for ROS nodes, in AS2FM we support the implementation of custom BT plugins using ROS-SCXML.

Since BT plugins rely on a specific interface, we extended the SCXML language to support the following features:

* :ref:`BT communication <bt_communication>`: A set of XML tags for modeling the BT Communication interface, based on BT ticks and BT responses.
* :ref:`BT Ports <bt_ports>`: A special BT interface to parametrize a specific plugin instance.


.. _bt_communication:

BT Communication
_________________

Normally, a BT plugin (or BT node), is idle until it receives a BT tick from a control node.
The BT tick is used to trigger the execution of the BT plugin, which will then return a BT response to the control node that sent the tick.

The BT plugin `AlwaysSuccess`, that returns `SUCCESS` each time it is ticked, can be implemented as follows:

.. code-block:: xml

    <scxml name="AlwaysSuccess" initial="idle">
        <state id="idle">
            <bt_tick target="idle">
                <bt_return_status status="SUCCESS" />
            </bt_tick>
            <bt_halt target="idle">
                <bt_return_halted/>
            </bt_halt>
        </state>
    </scxml>

In this example, there is only the `idle` state, always listening for an incoming `bt_tick` event.
When the tick is received, the plugin starts executing the body of the `bt_tick` tag, that returns a `SUCCESS` response and starts listening for a new `bt_tick`.

The BT plugin could receive also an `halt` request from the BT controller, that starts the execution of the `bt_halt` body.
In this example the `bt_halt` body contains only the `bt_return_halted` tag, that signals to the node that requested the halt that this was handled.

All BT plugins are expected to contain at least `bt_tick` and `bt_halt` tags.

Additionally, it is possible to model BT control nodes, that can send ticks to their children (that, in turns, are BT nodes as well) and receive their responses:

.. code-block:: xml

    <scxml initial="wait_for_tick" name="Inverter">
        <!-- A default BT port reporting the amount of children -->
        <bt_declare_port_in key="CHILDREN_COUNT" type="int8" />

        <datamodel>
            <data id="children_count" type="int8">
                <expr>
                    <bt_get_input key="CHILDREN_COUNT" />
                </expr>
            </data>
        </datamodel>

        <state id="wait_for_tick">
            <!-- Check if the state is valid. If not, go to error and stop -->
            <transition target="error" cond="children_count != 1" />
            <!-- React to an incoming BT Tick -->
            <bt_tick target="tick_child" />
            <bt_halt target="reset_child" />
        </state>

        <state id="reset_child">
            <onentry>
                <bt_halt_child id="0" />
            </onentry>
            <bt_child_halted id="0" target="wait_for_tick">
                <bt_return_halted/>
            </bt_child_halted>
        </state>

        <state id="tick_child">
            <onentry>
                <bt_tick_child id="0"/>
            </onentry>
            <bt_child_status id="0" cond="_bt.status == SUCCESS" target="wait_for_tick">
                <bt_return_status status="FAILURE" />
            </bt_child_status>
            <bt_child_status id="0" cond="_bt.status == FAILURE" target="wait_for_tick">
                <bt_return_status status="SUCCESS" />
            </bt_child_status>
            <bt_child_status id="0" cond="_bt.status == RUNNING" target="wait_for_tick">
                <bt_return_status status="RUNNING" />
            </bt_child_status>
        </state>

        <!-- A state to transition to when something did not work -->
        <state id="error" />

    </scxml>

In this example, the `Inverter` control node waits for a tick, then sends a tick to its child (identified by the id `0`), and waits for the response.
Once the child response is available, the control node inverts the response and sends it back to the control node that ticked it in the first place.

Similarly, in case it receives a halt request, the node sends a halt request to its child and waits for its response, before responding to its parent node that the halting request was fulfilled.

In this model, the `CHILDREN_COUNT` BT port is used to access the number of children of a control node instance, to check it is correctly configured.

Additional control nodes implementations are available in the `src/as2fm/resources <https://github.com/convince-project/AS2FM/blob/main/src/as2fm/resources/bt_control_nodes>`_ folder, and can be used as a reference to implement new ones.

.. _bt_ports:

BT Ports
________

When loading a BT plugin in the BT XML tree, it is possible to configure a specific plugin instance by means of the BT ports.

As in the case of ROS functionalities, BT ports need to be declared before being used, to provide the port name and expected type.

.. code-block:: xml

    <bt_declare_port_in key="my_string_port" type="string" />
    <bt_declare_port_in key="start_value" type="int32" />
    <bt_declare_port_out key="output_int" type="int32" />

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

Finally, we can store a specific value to the blackboard (only for output ports).

.. code-block:: xml

    <state id="some_state">
        <onentry>
            ...
            <bt_set_output key="output_int" expr="new_value_expression" />
            ...
        </onentry>
        ...
    </state>


BT Ports can be declared either as input or output ports:

* input ports can refer to either fixed or mutable variables (i.e. blackboard variables)
* output ports on only refer to mutable variables

When a BT plugin declares an output port, this must be referenced to a `BT Blackboard` variable.
This is defined in the BT XML file, by providing a blackboard variable name wrapped by curly braces.


.. _main_xml_howto:

The System Description (High Level XML file)
---------------------------------------------

This file references all the components defining the system, including the Behavior Tree, its plugins and the additional nodes that might be running on the side.
Additionally, it contains additional configuration for the model, e.g. the maximum time the clock can reach or the tick rate of a Behavior Tree.

An exemplary system description is the following:

.. code-block:: xml

    <convince_mc_tc>
        <mc_parameters>
            <max_time value="100" unit="s" />
            <bt_tick_rate value="1.0" />
            <bt_tick_if_not_running value="true" />
        </mc_parameters>

        <behavior_tree>
            <input type="bt.cpp-xml" src="./bt.xml" />
            <input type="bt-plugin-ros-scxml" src="./bt_topic_condition.scxml" />
            <input type="bt-plugin-ros-scxml" src="./bt_topic_action.scxml" />
        </behavior_tree>

        <node_models>
            <input type="ros-scxml" src="./battery_drainer.scxml" />
            <input type="ros-scxml" src="./battery_manager.scxml" />
        </node_models>

        <properties>
            <input type="jani" src="./battery_properties.jani" />
        </properties>
    </convince_mc_tc>

.. _mc_parameters:

Available Parameters
~~~~~~~~~~~~~~~~~~~~~

AS2FM provides a number of parameters to control the generation of the formal model. They are all contained in the tag `<mc_parameters>`.

Max Time
____________

The maximum time the global clock is allowed to reach.

The tag is called `max_time`. The `value` argument is the max time, and the argument `unit` specifies the time unit of the provided value. Supported units are `s`, `ms`, `us`, `ns`.

For example `<max_time value="100" unit="s" />` would allow the model to run for 100 seconds.

Max Array Size
_________________

The maximum size assigned to a dynamic array.

The tag is called `max_array_size`. The `value` argument defines the max size the dynamic array can reach, and is 100 by default.

For example `<max_array_size value="100" />` would allow dynamic arrays to contain up tp 100 entries.

BT Tick Rate
_________________

The tick rate of the Behavior Tree (in Hz).

The tag is called `bt_tick_rate`. The `value` argument defines the tick rate in Hz, and is 1.0 by default.

For example `<bt_tick_rate value="10.0">` would tick the behavior tree with a frequency of _10Hz_.

BT Tick If Not Running
_________________________

Whether we shall keep ticking a Behavior Tree after it returns something different from `RUNNING` (i.e. `SUCCESS` or `FAILURE`).

The tag is called `bt_tick_if_not_running`. The `value` argument enables or disables the ticking of non-running Behavior Trees, and is set to `false` by default. After the tree is stopped, the model execution will stop as well.

For example `<bt_tick_if_not_running value="false" />` would stop ticking the tree after it returned either _SUCCESS_ or _FAILURE_.
