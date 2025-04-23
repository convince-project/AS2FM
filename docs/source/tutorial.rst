Tutorial (WIP)

Expected to take 1h
Background: CS / Robotics Developer, no formal methods / MC Background required

Prerequisite: Docker container

1. Model introduction

- picture of environment
- system architecture: showing which files are there, which nodes do what, ...

2. Running model

- explain how to translate, run it -> introduction to tooling architecture and tooling functionalities
- We provide an initial (working) property that verifies the 1st part of the task works correctly (i.e. the robot picks and places)
- Monitor the system execution traces in plot juggler

3. Introducing probabilistic failures

- Picking does not work, e.g., item slips out of gripper
- Robot does drive to different location
- Then a property  of the model that previously == 1 is now something 0 < p < 1
- Run storm generating a failing trace
- Monitor the (failing) execution trace in plot juggler

4. Enhanced policy (BT functionality) to robustly handle probabilistically failing model

- We provide an additional (not working) property that verifies the complete task (i.e. that the object is eventually located at its target location)
- Monitor the system execution traces in plot juggler (again)
- Come to the conclusion that some functionality to make it work is not implemented, add it to the BT
- Check again, now it works
