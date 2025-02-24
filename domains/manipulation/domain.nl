You control a home robot with a hand that can move objects between different locations.

There are three actions defined in this domain:

The go-to action: This action allows the robot to move from one location to another. The action has a single precondition, which is that the robot is currently at a location. The effect of this action is to move the robot to another location and to remove the fact that it is at the original location.

The pick action: This action allows the robot to pick up an object using the hand. The action has three preconditions: (1) the object is located at a location (2) the robot is currently at the same location and (3) the hand is empty (i.e., not holding any object). The effect of this action is to update the state of the world to show that the robot is holding the object, the object is no longer at the location, and the hand is no longer empty.

The place action: This action allows the robot to place an object that it is holding. The action has two preconditions: (1) the robot is currently holding the object using the hand, and (2) the robot is currently at the target location. The effect of this action is to update the state of the world to show that the robot is no longer holding the object, the object is now located at the target location, and the hand is now empty.
