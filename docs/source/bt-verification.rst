BT-Only Verification with Mock Plugins
======================================

Overview
--------

The BT-only verification feature enables thorough verification of Behavior Tree logic without external system constraints. Instead of using real SCXML plugins for BT nodes, this mode generates mock plugins that randomly return different states, ensuring full coverage of all possible BT execution paths.

Problem Statement
-----------------

Traditional BT verification in AS2FM couples the BT to the specific behavior of external components (ROS nodes, environment models, etc.). This approach limits the explored states by how the rest of the model executes, preventing thorough evaluation of the BT itself.

**Current Limitations:**
- BT exploration limited by external component behavior
- Cannot verify BT-specific properties like execution order
- Difficult to test internal BT state relationships
- Verification results depend on specific system implementation

**Solution:**
- Generate mock plugins for all BT conditions and actions
- Mock plugins randomly return SUCCESS, FAILURE, or RUNNING states
- Enable verification of BT-specific properties
- Provide full coverage of all possible execution paths

Implementation
--------------

### Mock Plugin Generator

The implementation uses SCXML template files for generating mock BT plugins, providing better readability and maintainability:

.. code-block:: python

    from as2fm.scxml_converter.mock_bt_generator import create_mock_bt_converter_scxml

    # Generate mock BT converter using SCXML templates
    scxml_models = create_mock_bt_converter_scxml(
        bt_xml_path="bt.xml",
        bt_tick_rate=2.0,
        tick_if_not_running=True,
        custom_data_types={},
        seed=42,
        condition_success_probability=0.8,  # Customize condition behavior
        action_success_probability=0.7,     # Customize action behavior
        action_running_probability=0.2      # Customize running behavior
    )

**Template Files:**
- `src/as2fm/resources/mock_bt_nodes/mock_condition.scxml` - Template for condition nodes
- `src/as2fm/resources/mock_bt_nodes/mock_action.scxml` - Template for action nodes

**Benefits of SCXML Template Approach:**
- **Readability**: Templates are human-readable and easy to understand
- **Maintainability**: Easy to modify mock behavior by editing template files
- **Consistency**: Uses the same approach as BT control nodes
- **Customization**: Simple template-based parameter substitution
- **Separation of Concerns**: Logic separated from code generation
- **Debugging**: Easier to debug and verify mock behavior

### Mock Plugin Behavior

**Condition Mock Plugins:**
- Randomly return SUCCESS (50% probability) or FAILURE (50% probability)
- Track execution count and last result
- Configurable success probability

**Action Mock Plugins:**
- Can return SUCCESS (60% probability), FAILURE (20% probability), or RUNNING (20% probability)
- When returning RUNNING, will eventually transition to SUCCESS after configurable ticks
- Track execution count, last result, and running state

### Command-Line Interface

A new command `as2fm_bt_only_verification` provides the interface:

.. code-block:: bash

    as2fm_bt_only_verification \
        --bt-xml bt.xml \
        --properties bt_verification_properties.jani \
        --max-time 200 \
        --bt-tick-rate 2.0 \
        --seed 42 \
        --jani-out-file my_bt_verification.jani

**Parameters:**
- `--bt-xml`: Path to Behavior Tree XML file (required)
- `--properties`: Path to JANI properties file (required)
- `--max-time`: Maximum simulation time in seconds (default: 100)
- `--bt-tick-rate`: BT tick rate in Hz (default: 1.0)
- `--seed`: Random seed for reproducible behavior (default: None)
- `--jani-out-file`: Output JANI file path (default: bt_verification.jani)

Property Specification
----------------------

The BT-only verification supports several types of properties that can be verified:

### Property Types

1. **action_execution_after_condition**: Probability that the action (node 1002) reaches SUCCESS state
2. **sequence_completion**: Probability that the root sequence (node 1000) reaches SUCCESS state
3. **condition_failure_leads_to_sequence_failure**: Probability that when condition (node 1001) fails, the sequence (node 1000) also fails
4. **action_execution_frequency**: Probability that the action (node 1002) reaches SUCCESS state at least once

BT-only verification enables specification of BT-specific properties that were previously impossible to verify:

### Execution Order Properties

Verify that actions are executed (check if action reaches SUCCESS state):

.. code-block:: json

    {
      "name": "action_execution_after_condition",
      "expression": {
        "op": "filter",
        "fun": "values",
        "values": {
          "op": "Pmin",
          "exp": {
            "op": "F",
            "exp": {
              "op": "=",
              "left": "bt_1002_response__status",
              "right": 1
            }
          }
        },
        "states": {
          "op": "initial"
        }
      }
    }

### Internal State Properties

Verify relationships between different BT nodes:

.. code-block:: json

    {
      "name": "sequence_integrity",
      "expression": {
        "op": "filter",
        "fun": "values",
        "values": {
          "op": "Pmin",
          "exp": {
            "op": "G",
            "exp": {
              "op": "⇒",
              "left": {
                "op": "=",
                "left": "bt_1002_response__status",
                "right": 1
              },
              "right": {
                "op": "=",
                "left": "bt_1000_response__status",
                "right": 1
              }
            }
          }
        },
        "states": {
          "op": "initial"
        }
      }
    }

### Completion Properties

Calculate probability of BT root sequence completion (SUCCESS state):

.. code-block:: json

    {
      "name": "sequence_completion",
      "expression": {
        "op": "filter",
        "fun": "values",
        "values": {
          "op": "Pmin",
          "exp": {
            "op": "F",
            "exp": {
              "op": "=",
              "left": "bt_1000_response__status",
              "right": 1
            }
          }
        },
        "states": {
          "op": "initial"
        }
      }
    }

### Failure Propagation Properties

Verify that condition failure leads to sequence failure (implication):

.. code-block:: json

    {
      "name": "condition_failure_leads_to_sequence_failure",
      "expression": {
        "op": "filter",
        "fun": "values",
        "values": {
          "op": "Pmin",
          "exp": {
            "op": "G",
            "exp": {
              "op": "⇒",
              "left": {
                "op": "=",
                "left": "bt_1001_response__status",
                "right": 2
              },
              "right": {
                "op": "=",
                "left": "bt_1000_response__status",
                "right": 2
              }
            }
          }
        },
        "states": {
          "op": "initial"
        }
      }
    }

Variable Naming Convention
--------------------------

Mock plugins follow a consistent naming convention for easy property specification:

**Format:** `bt_{tick_id}_{response|tick|halt}.{variable}`

**Examples:**
- `bt_1000_response__status` - Status of node 1000
- `bt_1001_response__status` - Status of node 1001
- `bt_1002_response__status` - Status of node 1002
- `bt_1000_tick.valid` - Tick signal for node 1000
- `bt_1000_halt.valid` - Halt signal for node 1000

**Where:**
- `tick_id`: Sequential ID assigned to each BT node
- `response`: Status response from the node
- `tick`: Tick signal to the node
- `halt`: Halt signal to the node
- `status`: Node status (0=RUNNING, 1=SUCCESS, 2=FAILURE)

**BT Status Values:**
- `0`: RUNNING
- `1`: SUCCESS
- `2`: FAILURE

Usage Examples
--------------

### Basic Usage

.. code-block:: python

    from as2fm.scxml_converter.mock_bt_generator import create_mock_bt_converter_scxml

    # Generate mock BT converter with custom probabilities
    scxml_models = create_mock_bt_converter_scxml(
        bt_xml_path="my_bt.xml",
        bt_tick_rate=2.0,
        tick_if_not_running=True,
        custom_data_types={},
        seed=42,
        condition_success_probability=0.8,  # 80% success for conditions
        action_success_probability=0.7,     # 70% success for actions
        action_running_probability=0.2      # 20% running for actions
    )

### Advanced Usage with Custom Probabilities

.. code-block:: python

    from as2fm.scxml_converter.mock_bt_generator import generate_mock_plugins_scxml

    # Generate individual mock plugins with different probabilities
    mock_plugins = generate_mock_plugins_scxml(
        bt_xml_path="my_bt.xml",
        condition_success_probability=0.9,  # High reliability conditions
        action_success_probability=0.6,     # Moderate reliability actions
        action_running_probability=0.3,     # More running states
        seed=123
    )

### Template Customization

To modify mock behavior, edit the template files directly:

- Edit `src/as2fm/resources/mock_bt_nodes/mock_condition.scxml` for condition behavior
- Edit `src/as2fm/resources/mock_bt_nodes/mock_action.scxml` for action behavior

### Command Line Usage

1. **Create BT XML file:**

   .. code-block:: xml

       <root BTCPP_format="4">
           <BehaviorTree>
               <ReactiveSequence>
                   <Condition ID="TopicCondition" name="alarm" />
                   <Action ID="TopicAction" name="charge" />
               </ReactiveSequence>
           </BehaviorTree>
       </root>

2. **Create properties file:**

   .. code-block:: json

       {
         "properties": [
           {
             "name": "action_execution_after_condition",
             "expression": {
               "op": "filter",
               "fun": "values",
               "values": {
                 "op": "Pmin",
                 "exp": {
                   "op": "F",
                   "exp": {
                     "op": "=",
                     "left": "bt_1002_response__status",
                     "right": 1
                   }
                 }
               },
               "states": {
                 "op": "initial"
               }
             }
           }
         ]
       }

3. **Run verification:**

   .. code-block:: bash

       as2fm_bt_only_verification \
         --bt-xml bt.xml \
         --properties properties.jani \
         --seed 42

4. **Verify with Storm:**

   .. code-block:: bash

       smc_storm --model bt_verification.jani --properties-names action_execution_after_condition

### Advanced Usage

For complex BTs with multiple sequences and fallbacks, the verification can test sophisticated properties:

- **Mutual exclusion** between different action paths
- **Preference ordering** between sequences
- **Failure propagation** through the BT structure
- **Execution frequency** analysis
- **Internal state relationships** between nodes

Benefits and Applications
-------------------------

### Key Benefits

1. **Full Coverage**: All possible BT execution paths are explored
2. **BT-Specific Properties**: Can verify BT logic independently of external systems
3. **Reproducible Results**: Optional random seed ensures consistent verification
4. **No External Dependencies**: Focus purely on BT behavior
5. **Comprehensive Testing**: Test BT properties that are impossible with real plugins

### Applications

1. **BT Design Validation**: Verify BT logic before implementing real plugins
2. **Regression Testing**: Ensure BT changes don't break expected behavior
3. **Property Verification**: Test specific BT properties like execution order
4. **Performance Analysis**: Analyze BT execution patterns and frequencies
5. **Debugging**: Identify issues in BT structure and logic

### Comparison with Traditional Approach

**Coverage**: Traditional approach is limited by external behavior, while BT-Only Verification provides full BT coverage.

**Properties**: Traditional approach focuses on system-level properties only, while BT-Only Verification enables BT-specific properties.

**Dependencies**: Traditional approach requires full system model, while BT-Only Verification focuses on BT only.

**Reproducibility**: Traditional approach is system-dependent, while BT-Only Verification is seed-controlled.

**Focus**: Traditional approach focuses on system behavior, while BT-Only Verification focuses on BT logic.

Future Enhancements
-------------------

Potential future improvements to the BT-only verification feature:

1. **Configurable Probabilities**: Allow user-defined success/failure probabilities
2. **Temporal Properties**: Support for time-based BT properties
3. **Custom Mock Behaviors**: User-defined mock plugin behaviors
4. **Property Templates**: Pre-defined property templates for common BT patterns
5. **Visualization**: Tools for visualizing BT execution paths and properties
