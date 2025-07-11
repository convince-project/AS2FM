# The model

In this model, we simulate a complete system with a robot that docks, undocks, navigates and cleans the environment.

The expected outcome is that the robot is always able to undock, clean and, once it finishes, drive back to the dock before terminating the mission.

Since the robot could get stuck in any of those stages, we also expect that the robot performs some unstuck operation before resuming its operation.


## Important details

The cleaning mission is started only once using a ROS action, and the coverage status gets updated at 10 Hz. For each update, there is the possibility for the robot to get stuck.
If coverage steps forward before the robot gets unstuck, the action server tries up to a number pf times, and then fails. This results in the BT failing, too.

In the current model, this should never happen.

## Properties

* *tree_success*: The BT reports success and cleaning coverage is above 95%
* *tree_finished_robot_docked*: Once the BT is not running, we expect the robot to be docked and the online_coverage_done flag in the BT Blackboard to be set.

Both of them are expected to return 1.0 probability of the property being verified.
