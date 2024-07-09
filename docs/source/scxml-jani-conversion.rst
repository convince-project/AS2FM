SCXML to Jani Conversion
========================

SCXML and Jani
----------------

In CONVINCE, we expect developers to use Behavior Trees and SCXML to model the different parts of a robotic systems.

SCXML (Scope XML) is an high level format that describes a single state machine, and allows it to exchange information with other state machines using events. Each SCXML file defines its variables (datamodel), states and transitions.

With SCXML, the system consists of a set of state machines, each one represented by a SCXML file, that are synchronized together using events. Operations are carried out when a state machine receives an event, enters a state, or exits a state.

With Jani, the whole system is contained in a single JSON file, consisting of a set of global variables, automata (equivalent to state machines) with their edges (equivalent to transitions), and a composition description, describing how Automata should be synchronized by the mean of advancing specific edges at the same time.

The main difference between SCXML and Jani is that in Jani there is no concept of events, so synchronization must be achieved using the global variables and composition description.

High-Level (ROS) SCXML Implementation
---------------------------------------

In CONVINCE, we extended the standard SCXML format defined `here <https://www.w3.org/TR/scxml/>`_ with ROS specific features, to make it easier for ROS developers to model ROS-based systems.

In this guide we will refer to the extended SCXML format as High-Level SCXML and the standard SCXML format as Low-Level SCXML.

Currently, the supported ROS-features are:
- ROS Topics
- ROS Timers (Rate-callbacks)

TODO: Example of Topic and Timer declaration + usage.

Low-Level SCXML Conversion
----------------------------

Low-Level SCXML is the standard SCXML format defined `here <https://www.w3.org/TR/scxml/>`_.

Our converter is able to convert High-Level SCXML to Low-Level SCXML by translating the ROS specific features to standard SCXML features.
In case of timers, we need additional information that cannot be encoded in SCXML, so that information is generated at runtime.

The conversion between the two SCXML formats is implemented in ScxmlRoot.as_plain_scxml(). TODO: Link to API.

TODO: Describe how we translate the High-Level SCXML to the Low-Level SCXML.

Jani Conversion
----------------

Once the Low-Level SCXML is obtained, together with the timers information, we can convert it to Jani.

The core of the conversion lies in the translation of the SCXML state machines to Jani automata and the handling of the synchronization between them.

The following picture shows how our conversion works:

.. image:: graphics/scxml_to_jani.drawio.svg
    :alt: Conversion process
    :align: center

The main idea...