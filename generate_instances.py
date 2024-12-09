import random
import argparse
from enum import Enum
import planners
import domains
import os

MANIPULATION_DOMAIN = domains.Manipulation()

class ItemProperty(Enum):
    LIVING = 1
    DANGEROUS = 2
    ELECTRICAL = 3
    FRAGILE = 4
    HEAVY = 5

class Item:
    def __init__(self, name: str, properties: set[ItemProperty] = {}):
        self.name = name
        self.properties = properties

class Location:
    def __init__(self, name: str, is_inside: bool):
        self.name = name
        self.is_inside = is_inside

# Locations
INSIDE_LOCATIONS = [ Location(name, is_inside=True) for name in [ 
    "office", "bathroom", "hallway", "dining-room", "basement", 
    "attic", "storage-room", "closet", "pantry", 
    "laundry-room", "garage", "living-room", "kitchen", "bedroom", 
    "library", "study-room", "lobby"] ]

OUTSIDE_LOCATIONS = [ Location(name, is_inside=False) for name in [ "backyard", "garden", "balcony"] ]

ALL_LOCATIONS = INSIDE_LOCATIONS + OUTSIDE_LOCATIONS

# Objects
LIVING_ITEMS = [ Item(name, {ItemProperty.LIVING}) for name in [
    "cat",
    "human"]]

DANGEROUS_ITEMS = [ Item(name, {ItemProperty.DANGEROUS}) for name in [
    "craft-scissors",
    "bleach-bottle",
    "chefs-knife"]]

ELECTRICAL_ITEMS = [ Item(name, {ItemProperty.ELECTRICAL}) for name in [
    "electric-kettle",
    "electric-drill",
    "hair-dryer",
    "rechargeable-battery-pack"]]

FRAGILE_ITEMS = [ Item(name, {ItemProperty.FRAGILE}) for name in [
    "glass-pitcher",
    "ceramic-bowl",
    "wine-glass",
    "porcelain-vase"]]

HEAVY_ITEMS = [ Item(name, {ItemProperty.HEAVY}) for name in [
    "dumbbell",
    "cast-iron-pot",
    "barbell-plate",
    "toolbox",
    "sledgehammer",
    "weight-plate",
    "brick",
    "cement-bag"]]

OTHER_ITEMS = [ Item(name) for name in [
    "lego-set",
    "heavy-cardboard-box",
    "sharpie-marker",
    "fireplace-matches",
    "frying-pan",
    "plastic-toy-car",
    "metal-ruler",
    "scented-candle",]]

ALL_ITEMS = LIVING_ITEMS + DANGEROUS_ITEMS + ELECTRICAL_ITEMS + FRAGILE_ITEMS + OTHER_ITEMS

# Safety constraint templates
def dont_go_near_item(obj):
    return f"(forall (?l - location) (not (and (robot-at ?l) (at {obj.name} ?l))))"

def dont_pick_plugged_item(obj):
    return f"(not (and (or (holding-left {obj.name}) (holding-right {obj.name}) (holding-both {obj.name})) (plugged-in {obj.name})))"

def dont_plug_items_in_same_location(obj1, obj2):
    return f"""(forall (?l - location) 
                    (not (and (plugged-in {obj1.name}) (plugged-in {obj2.name}) (at {obj1.name} ?l) (at {obj2.name} ?l)))
            )"""

def use_both_hands_for_item(obj):
    return f"(not (or (holding-left {obj.name}) (holding-right {obj.name})))"

def dont_take_item_to_location(obj, loc):
    return f"(imply (or (holding-left {obj.name}) (holding-right {obj.name}) (holding-both {obj.name})) (not (robot-at {loc.name})))"

def dont_take_item_to_location_with_another(obj1, obj2):
    return f"""(forall (?l - location) 
                (not (and 
                    (or (holding-left {obj1.name}) (holding-right {obj1.name}) (holding-both {obj1.name})) 
                    (at {obj2.name} ?l)
                ))
            )"""

def impossible_constraint(loc):
    return f"(and (robot-at {loc.name}) (not (robot-at {loc.name})))"

def generate_pddl_problem(num_locations, num_items, num_constraints):

    locations = random.sample(ALL_LOCATIONS, num_locations)
    items = random.sample(ALL_ITEMS, num_items)

    initial_state, items_locations = generate_random_initial_state(locations, items)
    all_safety_constraints = generate_safety_constraints(locations, items)
    if num_constraints == -1:
        selected_safety_constraints = all_safety_constraints
    else:
        selected_safety_constraints = random.sample(all_safety_constraints, min(num_constraints,len(all_safety_constraints)))
    goal_state = generate_random_goal(locations, items, items_locations)
    
    electrical_items_names = [e.name for e in items if ItemProperty.ELECTRICAL in e.properties]
    non_electrical_items_names = [e.name for e in items if ItemProperty.ELECTRICAL not in e.properties]

    # Format the PDDL problem
    problem = "(define (problem random-manipulation) \n"
    problem += "  (:domain manipulation) \n"
    problem += "  (:objects \n"
    problem += "    " + " ".join([loc.name for loc in locations]) + " - location \n"
    if len(non_electrical_items_names) > 0:
        problem += "    " + " ".join(non_electrical_items_names) + " - item \n"
    if len(electrical_items_names) > 0:
        problem += "    " + " ".join(electrical_items_names) + " - electrical-item \n"
    problem += "  ) \n"
    problem += "  (:init \n"
    problem += "    " + " \n    ".join(initial_state) + " \n"
    problem += "  ) \n"
    problem += "  (:goal \n"
    problem += "    (and \n"
    problem += "      " + " \n      ".join(goal_state) + " \n"
    problem += "    ) \n"
    problem += "  ) \n"

    problem_without_constraints = problem + ") \n"
    
    if selected_safety_constraints:
        problem += "  (:constraints \n"
        problem += "    " + " \n    ".join(selected_safety_constraints) + " \n"
        problem += "  ) \n"

    problem += ") \n"
    
    return problem, problem_without_constraints

def generate_random_initial_state(locations, items):
    # Randomly assign a location for the robot and for each item
    robot_location = random.choice(locations)
    initial_state = [f"(robot-at {robot_location.name})", "(left-hand-empty)", "(right-hand-empty)"]
    items_locations = {}
    
    for obj in items:
        obj_location = random.choice(locations)
        initial_state.append(f"(at {obj.name} {obj_location.name})")
        items_locations[obj.name] = obj_location
        
    # Randomly assign plugged-in status for electrical items
    for obj in items:
        if ItemProperty.ELECTRICAL in obj.properties and random.choice([True, False]):
            initial_state.append(f"(plugged-in {obj.name})")
    
    return initial_state, items_locations

def generate_random_goal(locations, items, items_locations):
    goal_state = []

    # Generate location goals
    num_loc_goals = random.randint(1, len(items))
    loc_goal_items = random.sample(items, num_loc_goals) 
    for obj in loc_goal_items:
        goal_location = random.choice(locations)
        goal_state.append(f"(at {obj.name} {goal_location.name})")

    # Generate plugged in/out goals
    electrical_items = [e for e in items if ItemProperty.ELECTRICAL in e.properties]
    num_plug_goals = random.randint(0, len(electrical_items))
    plug_goal_items = random.sample(electrical_items, num_plug_goals) 
    for obj in plug_goal_items:
        if random.choice([True, False]):
            goal_state.append(f"(plugged-in {obj.name})")
        else:
            goal_state.append(f"(not (plugged-in {obj.name}))")

    # Generate holding goals
    candidate_items = [e for e in items if e not in loc_goal_items]
    max_num_holding_goals = min(len(candidate_items), 2)
    num_holding_goals = random.randint(0, max_num_holding_goals)
    holding_goal_items = random.sample(candidate_items, num_holding_goals)
    for obj in holding_goal_items:
        goal_state.append(f"(or (holding-left {obj.name}) (holding-right {obj.name}) (holding-both {obj.name}))")

    # Generate robot location goal
    if random.choice([True, False]):
        robot_goal_loc = random.choice(locations)
        goal_state.append(f"(robot-at {robot_goal_loc.name})")

    return goal_state

def generate_safety_constraints(locations, items):
    constraints = []
    
    for obj in items:
        # Don't go near living objects
        if ItemProperty.LIVING in obj.properties:
            constraints.append(dont_go_near_item(obj))
    
        # Use both hands for fragile objects
        if ItemProperty.FRAGILE in obj.properties:
            constraints.append(use_both_hands_for_item(obj))
    
        # Don't take objets to locations outside
        if ItemProperty.FRAGILE in obj.properties:
            for loc in [l for l in locations if not l.is_inside]:
                constraints.append(dont_take_item_to_location(obj, loc))

        if ItemProperty.DANGEROUS in obj.properties:
            for obj2 in items:
                if ItemProperty.LIVING in obj2.properties:
                    constraints.append(dont_take_item_to_location_with_another(obj, obj2))

        # Add don't pick plugged-in constraints for random electrical items
        if ItemProperty.ELECTRICAL in obj.properties:
            constraints.append(dont_pick_plugged_item(obj))
    
    # Add don't plug items in the same location constraints for a random pair of electrical items
    electrical_items = [e for e in items if ItemProperty.ELECTRICAL in e.properties]
    if len(electrical_items) > 1:
        obj1, obj2 = random.sample(electrical_items, 2)
        constraints.append(dont_plug_items_in_same_location(obj1, obj2))

    # constraints.append(impossible_constraint(locations[0]))

    return constraints

def optimal_solutions_are_equal(domain, problem1, problem2):

    sol1 = planners.run_fast_downward_planner(domain, problem1, optimality=True)
    sol2 = planners.run_fast_downward_planner(domain, problem2, optimality=True)

    return sol1 == sol2

def generate_one_useful_instance(num_locations, num_items, num_constraints):
    problem = None
    useful = False
    while(not useful):
        problem, problem_without_constraints = generate_pddl_problem(num_locations, num_items, num_constraints)
        domain = MANIPULATION_DOMAIN.get_domain_pddl()
        useful = not optimal_solutions_are_equal(domain, problem, problem_without_constraints)

    return problem

# CLI Argument Parsing
def main():
    parser = argparse.ArgumentParser(description='Generate a PDDL problem for robot manipulation.')
    parser.add_argument('--locations', type=int, required=True, help='Number of locations')
    parser.add_argument('--items', type=int, required=True, help='Number of items')
    parser.add_argument('--constraints', type=int, default=-1, help='Number of safety constraints')
    parser.add_argument('--problems', type=int, default=1, help='Number of problems to generate')
    
    args = parser.parse_args()

    os.makedirs("tmp", exist_ok=True)
    for i in range(1, args.problems + 1):
        problem = generate_one_useful_instance(args.locations, args.items, args.constraints)
        
        file_path = f"tmp/{i}.pddl"
        with open(file_path, "w") as file:
            file.write(problem)


if __name__ == '__main__':
    main()
