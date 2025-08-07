Autonomous Systems to Formal Models (AS2FM)
===============================================

This is the documentation of the AS2FM tools from the `CONVINCE project's <https://convince-project.eu/>`_ toolbox. Besides illustrative :doc:`tutorials <../tutorials>` on how to use the provided scripts, their :doc:`API <../api>` is documented to foster contributions from users outside of the core project's team.

Overview
--------

The purpose of the provided components is to convert all specifications of components of the robotic system under investigation into a format which can be given as input to model checkers for verifying the robustness of the system functionalities.

AS2FM focuses on converting the model of the system, provided as a combination of `Behavior Tree (BT) XML <https://www.behaviortree.dev/docs/learn-the-basics/xml_format>`_ and :ref:`High-Level (HL)-SCXML<hl_scxml>` into a format that can be used by model checking tools (i.e. JANI or plain SCXML).
A full robotic system and the information needed for model checking consists of:

* one or multiple ROS nodes in SCXML,
* the environment model in SCXML,
* the Behavior Tree in XML,
* the plugins of the Behavior Tree leaf nodes in SCXML,
* the property to check in temporal logic, currently given in JANI, later support for XML will be added.

We offer a push-button solution for the full bundle conversion of all of those input files into one model-checkable format.
We suggest using `smc_storm <https://github.com/convince-project/smc_storm>`_ for verifying JANI models and `SCAN <https://github.com/convince-project/SCAN>`_ to verify plain SCXML models..

.. image:: graphics/as2fm_overview.drawio.svg
    :alt: How AS2FM works
    :align: center

A tutorial on how to use the conversion script can be found in the :doc:`tutorial section <../tutorials>`.

Contents
--------

.. toctree::
   :maxdepth: 2

   installation
   quick-guide
   tutorials
   howto
   scxml-jani-conversion
   bt-verification
   api
   contacts
