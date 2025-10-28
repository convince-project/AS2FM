#!/bin/bash

# BT-Only Verification Example
# This script demonstrates how to use the BT-only verification feature

echo "=========================================="
echo "BT-Only Verification Example"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "bt.xml" ]; then
    echo "Error: bt.xml not found. Please run this script from the bt_verification_example directory."
    exit 1
fi

echo "1. BT XML file: bt.xml"
echo "   - Simple ReactiveSequence with one condition and one action"
echo "   - Condition: TopicCondition (alarm)"
echo "   - Action: TopicAction (charge)"

echo ""
echo "2. Properties file: bt_verification_properties.jani"
echo "   - action_execution_after_condition: Verifies action only executes after condition"
echo "   - sequence_completion: Probability of BT completing successfully"
echo "   - condition_failure_leads_to_sequence_failure: Failure propagation"
echo "   - action_execution_frequency: Probability of action executing at least once"

echo ""
echo "3. Running BT-only verification..."

# Run the BT-only verification
as2fm_bt_only_verification \
    --bt-xml bt.xml \
    --properties bt_verification_properties.jani \
    --seed 42 \
    --bt-tick-rate 1.0 \
    --max-time 100 \
    --jani-out-file bt_verification.jani \
    --condition-success-probability 0.8 \
    --action-success-probability 0.7 \
    --action-running-probability 0.2

if [ $? -eq 0 ]; then
    echo ""
    echo "4. Verification successful! Generated bt_verification.jani"
    echo ""
    echo "5. To verify properties with Storm (if installed):"
    echo "   smc_storm --model bt_verification.jani --properties-names action_execution_after_condition"
    echo "   smc_storm --model bt_verification.jani --properties-names sequence_completion"
    echo "   smc_storm --model bt_verification.jani --properties-names condition_failure_leads_to_sequence_failure"
    echo "   smc_storm --model bt_verification.jani --properties-names action_execution_frequency"
    echo ""
    echo "6. Expected results:"
echo "   - action_execution_after_condition: Should be > 0.0 (depends on mock probabilities)"
echo "   - sequence_completion: Should be > 0.0 (depends on mock probabilities)"
echo "   - condition_failure_leads_to_sequence_failure: Should be 1.0 (always true)"
echo "   - action_execution_frequency: Should be > 0.0 (depends on mock probabilities)"
else
    echo "Error: BT-only verification failed!"
    exit 1
fi

echo ""
echo "=========================================="
echo "Example completed successfully!"
echo "=========================================="
