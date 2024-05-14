CONVINCE Model Checking Toolchain Components
===============================================
This is the documentation of the model checking components of the `CONVINCE project's <https://convince-project.eu/>`_ toolchain. Besides illustrative :doc:`tutorials <../tutorials>` on how to use the provided scripts, their :doc:`API <../api>` is documented to foster contributions from users outside of the core project's team.

The purpose of the provided components is to convert all specifications of components of the robotic system under investigation into a format which can be given as input to model checkers for verifying the robustness of the system functionalities.

As a first toolchain component, we provide a Python script to convert models describing the system and its environment together, given in the CONVINCE robotics JANI flavor as specified in the `data model repository <https://github.com/convince-project/data-model>`_, into `plain JANI <https://jani-spec.org>`_ accepted as input by model checkers. A tutorial on how to use the conversion can be found in the :doc:`tutorial section <../tutorials>`. 

The second part of the provided toolchain components centers around system specifications given in ScXML and how to convert them into a plain Jani file for model checking. 
We expect that a full robotic system and the information needed for model checking consist of: 

* the property to check in temporal logic, currently given in Jani, later support for ScXML will be added, 
* the behavior tree in XML, 
* one or multiple nodes in ScXML,
* the plugins of the nodes in ScXML, and
* the environment model in ScXML.

Some of those parts can be converted into Jani individually. We also offer a push-button solution for the full bundle conversion of all of those input files into one model-checkable plain Jani model.
A tutorial on how to use the conversion scripts can be found in the :doc:`tutorial section <../tutorials>`. 

Contents
--------

.. toctree::

   tutorials
   api
