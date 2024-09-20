Autonomous Systems to Formal Models (AS2FM)
===============================================

This is the documentation of the AS2FM tools from the `CONVINCE project's <https://convince-project.eu/>`_ toolchain. Besides illustrative :doc:`tutorials <../tutorials>` on how to use the provided scripts, their :doc:`API <../api>` is documented to foster contributions from users outside of the core project's team.

Overview
--------

The purpose of the provided components is to convert all specifications of components of the robotic system under investigation into a format which can be given as input to model checkers for verifying the robustness of the system functionalities.

As a first toolchain component, we provide a Python script to convert models describing the system and its environment together, given in the CONVINCE robotics JANI flavor as specified in the `data model repository <https://github.com/convince-project/data-model>`_, into `plain JANI <https://jani-spec.org>`_, accepted as input by model checkers. A tutorial on how to use the conversion can be found in the :doc:`tutorial section <../tutorials>`. 

The second part of the provided toolchain components centers around system specifications given in SCXML and how to convert them into a plain JANI file for model checking. 
We expect that a full robotic system and the information needed for model checking consists of: 

* one or multiple ROS nodes in SCXML,
* the environment model in SCXML, 
* the Behavior Tree in XML, 
* the plugins of the Behavior Tree leaf nodes in SCXML,
* the property to check in temporal logic, currently given in JANI, later support for XML will be added.

We offer a push-button solution for the full bundle conversion of all of those input files into one model-checkable plain JANI model.
A tutorial on how to use the conversion script can be found in the :doc:`tutorial section <../tutorials>`. 

Contents
--------

.. toctree::
   :maxdepth: 2

   installation
   tutorials
   howto
   scxml-jani-conversion
   api
   contacts
