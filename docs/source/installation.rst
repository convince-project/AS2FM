.. _installation:

Installation
--------------

Pre-requisites
^^^^^^^^^^^^^^

The scripts have been tested with Python 3.10 and pip version 24.0.

Additionally, the following dependencies are required to be installed:

* `ROS Humble <https://docs.ros.org/en/humble/index.html>`_
* `bt_tools <https://github.com/boschresearch/bt_tools>`_


AS2FM packages installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before installing the AS2FM packages, make sure to source the ROS workspace containing the `bt_tools` package by executing ``source <path_to_ws>/install/setup.bash``.

Afterwards, install the AS2FM packages with the following commands:

.. code-block:: bash

    python3 -m pip install as2fm_common/
    python3 -m pip install jani_generator/
    python3 -m pip install scxml_converter/
