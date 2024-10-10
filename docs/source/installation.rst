.. _installation:

Installation
--------------

Prerequisites
^^^^^^^^^^^^^^

The scripts have been tested with Python 3.10 and pip version 24.0.

Additionally, the following dependencies are required to be installed:

* `ROS Humble <https://docs.ros.org/en/humble/index.html>`_
* `bt_tools <https://github.com/boschresearch/bt_tools>`_


AS2FM Package Installations
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::

    Before proceeding with the installation, make sure that pip's version is at least 24.0.

    - To check pip's version: `python3 -m pip --version -m pip --version`
    - To upgrade pip: `python3 -m pip install --upgrade pip`

.. note::

    Since we switched from a multi-package to a mono-package setup, make sure to uninstall the previous version of the AS2FM tools.
    It can be done using the following instructions:

    .. code-block:: bash

        python3 -m pip uninstall as2fm_common
        python3 -m pip uninstall jani_generator
        python3 -m pip uninstall scxml_converter
        python3 -m pip uninstall jani_visualizer
        python3 -m pip uninstall trace_visualizer

AS2FM can be installed using pip:

.. code-block:: bash

    # Non-editable mode
    python3 -m pip install AS2FM/
    # Editable mode
    python3 -m pip install -e AS2FM/

Verify your installation by **sourcing the ROS workspace containing btlib** and then running:

.. code-block:: bash

    as2fm_scxml_to_jani --help
