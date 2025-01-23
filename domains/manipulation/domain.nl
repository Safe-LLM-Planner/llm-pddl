You control a home robot with two hands, able to move objects between locations. The robot can hold objects with either hand or both hands simultaneously. It can also interact with electrical items, such as plugging them in or unplugging them.

There are several actions defined in this domain:

The go-to action: This action allows the robot to move from a starting location to a destination location. Its precondition is that the robot must be in the starting location. The effect of this action is that the robot is moved to the destination location.

The pick-left action: This action allows the robot to pick up an object from a location using its left hand. It has three preconditions: (1) The object must be located in the location. (2) The robot must be in the same location. (3) The left hand must be empty (i.e., not holding any object). The effect of this action is that the robot is holding the object with its left hand, the object is no longer in the location, and the left hand is no longer empty.

The pick-right action: This action allows the robot to pick up an object from a location using its right hand. It has three preconditions: (1) The object must be located in the location. (2) The robot must be in the same location. (3) The right hand must be empty (i.e., not holding any object). The effect of this action is that the robot is holding the object with its right hand, the object is no longer in the location, and the right hand is no longer empty.

The pick-both action: This action allows the robot to pick up an object from a location using both hands. It has three preconditions: (1) The object must be located in the location. (2) The robot must be in the same location. (3) Both hands must be empty (i.e., not holding any object). The effect of this action is that the robot holds the object with both hands, the object is no longer in the location, and both hands are no longer empty.

The place-left action: This action allows the robot to place an object it is holding with its left hand in a location. It has two preconditions: (1) The robot must be holding the object with its left hand. (2) The robot must be in the target location. The effect of this action is that the object is placed in the target location, the left hand becomes empty, and the robot is no longer holding the object with its left hand.

The place-right action: This action allows the robot to place an object it is holding with its right hand in a location. It has two preconditions: (1) The robot must be holding the object with its right hand. (2) The robot must be in the target location. The effect of this action is that the object is placed in the target location, the right hand becomes empty, and the robot is no longer holding the object with its right hand.

The place-both action: This action allows the robot to place an object it is holding with both hands in a location. It has two preconditions: (1) The robot must be holding the object with both hands. (2) The robot must be in the target location. The effect of this action is that the object is placed in the target location, both hands become empty, and the robot is no longer holding the object with both hands.

The unplug action: This action allows the robot to unplug an electrical item in a location. It has two preconditions: (1) The electrical item must be located in the location. (2) The robot must be in the same location, and the electrical item must be plugged in. The effect of this action is that the electrical item is no longer plugged in.

The plug-in action: This action allows the robot to plug in an electrical item in a location. It has two preconditions: (1) The electrical item must be located in the location. (2) The robot must be in the same location, and the electrical item must not be plugged in. The effect of this action is that the electrical item is now plugged in.