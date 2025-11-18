.. _installation:

Installation
------------

Docker
^^^^^^

In the root folder of the repository, pull the necessary docker image:

.. sybil-new-environment: IGNORE

.. code-block:: bash

    $ docker compose pull
    ...

Then verify that the correct versions are installed

.. code-block:: bash

    $ docker compose run --remove-orphans base smc_storm --version
    [+] Creating 1/1
    ...
    0.1.8

Local installation
^^^^^^^^^^^^^^^^^^

Requirements
````````````

The scripts have been tested with Python 3.10 and pip version 24.0.

You need to install ROS. We currently support the following distributions:

* `Humble <https://docs.ros.org/en/humble/index.html>`_
* `Jazzy <https://docs.ros.org/en/jazzy/index.html>`_

Don't forget to source ROS, e.g.:

.. sybil-new-environment: IGNORE
.. TODO: this needs actual bash instead of sh

.. code-block:: bash

    $ source /opt/ros/humble/setup.bash

Install SMC Storm by downloading the `latest release <https://github.com/convince-project/smc_storm/releases>`_ and executing the installation script.
Verify your installation:

.. sybil-new-environment: smc_storm

.. code-block:: bash

    $ smc_storm --version
    0.1.8

AS2FM Python Package
````````````````````

.. warning::

    Before proceeding with the installation, make sure that pip's version is at least 24.0.

    - To check pip's version: `python3 -m pip --version`
    - To upgrade pip: `python3 -m pip install --upgrade pip`

.. note::

    Since we switched from a multi-package to a mono-package setup, make sure to uninstall the previous version of the AS2FM tools.
    It can be done using the following instructions:

    .. sybil-new-environment: IGNORE

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

Verify your installation by **sourcing your ROS distribution** (i.e. running `source /opt/ros/<ros-distro>/setup.bash`) and then running:

.. sybil-new-environment: pip
    :cwd: /

.. code-block:: bash

    $ as2fm_roaml_to_jani --help

    usage: as2fm_roaml_to_jani [-h] [--generated-scxml-dir GENERATED_SCXML_DIR]
                            [--jani-out-file JANI_OUT_FILE]
                            main_xml

    Convert SCXML robot system models to JANI model.

    positional arguments:
    main_xml              The path to the main XML file to interpret.

    options:
    -h, --help            show this help message and exit
    --generated-scxml-dir GENERATED_SCXML_DIR
                            Path to the folder containing the generated plain-
                            SCXML files.
    --jani-out-file JANI_OUT_FILE
                            Path to the generated jani file.
