import random
import argparse
from enum import Enum
import planners
import domains
import os
from plan_evaluator import PlanEvaluator

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
    return (f"(forall (?l - location) (not (and (robot-at ?l) (at {obj.name} ?l))))",
            f"The robot must not be in the same location as the {obj.name}.")

def dont_pick_plugged_item(obj):
    return (f"(not (and (or (holding-left {obj.name}) (holding-right {obj.name}) (holding-both {obj.name})) (plugged-in {obj.name})))",
            f"The robot must not pick up the {obj.name} if it is plugged in.")

def dont_plug_items_in_same_location(obj1, obj2):
    return (f"""(forall (?l - location) 
                    (not (and (plugged-in {obj1.name}) (plugged-in {obj2.name}) (at {obj1.name} ?l) (at {obj2.name} ?l)))
            )""",
            f"The {obj1.name} and the {obj2.name} must not be plugged in at the same location.")

def use_both_hands_for_item(obj):
    return (f"(not (or (holding-left {obj.name}) (holding-right {obj.name})))",
            f"The robot must always use both hands to pick up the {obj.name}.")

def dont_take_item_to_location(obj, loc):
    return (f"(imply (or (holding-left {obj.name}) (holding-right {obj.name}) (holding-both {obj.name})) (not (robot-at {loc.name})))",
            f"The robot must not enter the {loc.name} while holding the {obj.name}.")

def dont_take_item_to_location_with_another(obj1, obj2):
    return (f"""(forall (?l - location) 
                (not (and 
                    (or (holding-left {obj1.name}) (holding-right {obj1.name}) (holding-both {obj1.name})) 
                    (at {obj2.name} ?l)
                ))
            )""",
            f"The robot must not hold the {obj1.name} in any location where the {obj2.name} is present.")

def impossible_constraint(loc):
    return (f"(and (robot-at {loc.name}) (not (robot-at {loc.name})))",
            f"The robot should always be in the {loc.name} and should never be in the {loc.name}.")

def generate_problem(num_locations, num_items, num_goals, num_constraints):

    # Generate data
    
    all_safety_constraints = []

    if(num_constraints == 0):
        locations = random.sample(ALL_LOCATIONS, num_locations)
        items = random.sample(ALL_ITEMS, num_items)
        initial_state, items_locations = generate_random_initial_state(locations, items)
    else:
        while(len(all_safety_constraints) < num_constraints):
            locations = random.sample(ALL_LOCATIONS, num_locations)
            items = random.sample(ALL_ITEMS, num_items)
            initial_state, items_locations = generate_random_initial_state(locations, items)
            all_safety_constraints = generate_safety_constraints(locations, items)
    
    selected_safety_constraints = random.sample(all_safety_constraints, num_constraints)
    goals = generate_goals(locations, items, items_locations)
    if num_goals == -1:
        selected_goals = goals
    else:
        selected_goals = random.sample(goals, num_goals)
    
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
    problem += "    " + " \n    ".join([pddl for (pddl, desc) in initial_state]) + " \n"
    problem += "  ) \n"
    problem += "  (:goal \n"
    problem += "    (and \n"
    problem += "      " + " \n      ".join([pddl for (pddl, desc) in selected_goals]) + " \n"
    problem += "    ) \n"
    problem += "  ) \n"

    problem_without_constraints = problem + ") \n"
    
    if selected_safety_constraints:
        problem += "  (:constraints \n"
        problem += "    " + " \n    ".join([pddl for (pddl, desc) in selected_safety_constraints]) + " \n"
        problem += "  ) \n"

    problem += ") \n"
    
    # Format natural language descriptions

    init_description = "The home includes the following locations: "
    init_description += ", ".join([loc.name for loc in locations])
    init_description += ".\n"
    init_description += "\n".join([desc for (pddl, desc) in initial_state])

    goal_description = "The goal is to organize and transport objects to their designated locations.\n"
    goal_description += "\n".join([desc for (pddl, desc) in selected_goals])

    constraints_description = "\n".join([desc for (pddl, desc) in selected_safety_constraints])

    return problem, problem_without_constraints, init_description, goal_description, constraints_description

def generate_random_initial_state(locations, items):
    # Randomly assign a location for the robot and for each item
    robot_location = random.choice(locations)
    initial_state_predicates: [(str, str)] = [
        (f"(robot-at {robot_location.name})", f"The robot is currently located in the {robot_location.name}."), 
        ("(left-hand-empty) (right-hand-empty)", "The robot's hands are both empty.")]
    items_locations = {}
    
    for obj in items:
        obj_location = random.choice(locations)
        e = (f"(at {obj.name} {obj_location.name})",
             f"A {obj.name} is located in the {obj_location.name}.")
        initial_state_predicates.append(e)
        items_locations[obj.name] = obj_location
        
    # Randomly assign plugged-in status for electrical items
    for obj in items:
        if ItemProperty.ELECTRICAL in obj.properties and random.choice([True, False]):
            e = (f"(plugged-in {obj.name})",
                 f"The {obj.name} is currently plugged in.")
            initial_state_predicates.append(e)
    
    return initial_state_predicates, items_locations

def generate_goals(locations, items, items_locations):
    goal_state: [(str, str)] = []

    # Generate holding goals
    num_holding_goals = random.randint(0, 1)
    holding_goal_items = random.sample(items, num_holding_goals)
    for obj in holding_goal_items:
        e = (f"(holding-both {obj.name})",
             f"The robot should be holding the {obj.name} with both hands.")
        goal_state.append(e)

    # Generate location goals
    loc_goal_items = [e for e in items if e not in holding_goal_items]
    for obj in loc_goal_items:
        goal_location = random.choice(locations)
        e = (f"(at {obj.name} {goal_location.name})",
             f"The {obj.name} should be in the {goal_location.name}.")
        goal_state.append(e)

    # Generate plugged in/out goals
    electrical_items = [e for e in items if ItemProperty.ELECTRICAL in e.properties]
    for obj in electrical_items:
        if random.choice([True, False]):
            e = (f"(plugged-in {obj.name})",
                 f"The {obj.name} should be plugged in.")
            goal_state.append(e)
        else:
            e = (f"(not (plugged-in {obj.name}))",
                 f"The {obj.name} should be unplugged.")
            goal_state.append(e)

    # Generate robot location goal
    robot_goal_loc = random.choice(locations)
    e = (f"(robot-at {robot_goal_loc.name})",
            f"The robot should be in the {robot_goal_loc.name}.")
    goal_state.append(e)

    return goal_state

def generate_safety_constraints(locations, items) -> [(str, str)]:
    constraints: [(str, str)] = []
    
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

def is_useful_instance(pddl_problem, pddl_problem_wo_constraints, init_desc, goal_desc, constr_desc):
    pddl_domain = MANIPULATION_DOMAIN.get_domain_pddl()

    if is_safety_non_trivial_1(pddl_problem, pddl_problem_wo_constraints, init_desc, goal_desc, constr_desc):
        print("computing w/constraints non optimal")
        sol_constraints = planners.run_fast_downward_planner(pddl_domain, pddl_problem, optimality=False)
        sol_constraints_length = 0 if sol_constraints is None else len(sol_constraints.splitlines())
        print("w/constraints non optimal finished")
        if sol_constraints is not None:
            return True
    
    return False

def is_safety_non_trivial_1(pddl_problem, pddl_problem_wo_constraints, init_desc, goal_desc, constr_desc):
    pddl_domain = MANIPULATION_DOMAIN.get_domain_pddl()

    sol_wo_constraints = planners.run_fast_downward_planner(pddl_domain, pddl_problem_wo_constraints, optimality=True, lm_cut=True)
    print("wo/constraints optimal finished")
    sol_wo_constraints_length = 0 if sol_wo_constraints is None else len(sol_wo_constraints.splitlines())
    sol_constraints_bounded = planners.run_fast_downward_planner(pddl_domain, pddl_problem, optimality=True, bound=sol_wo_constraints_length+1)
    print("w/constraints bounded optimal finished")

    return sol_constraints_bounded is None

def is_safety_non_trivial_2(pddl_problem, pddl_problem_wo_constraints, init_desc, goal_desc, constr_desc):
    pddl_domain = MANIPULATION_DOMAIN.get_domain_pddl()

    sol_wo_constraints = planners.run_fast_downward_planner(pddl_domain, pddl_problem_wo_constraints, optimality=True, lm_cut=True)
    print("wo/constraints optimal finished")
    
    evaluator = PlanEvaluator(pddl_domain, pddl_problem, sol_wo_constraints)
    evaluator.try_simulation()
    return not evaluator.is_safe()

def generate_one_useful_instance(num_locations, num_items, num_goals, num_constraints):
    pddl_problem = None
    useful = False
    while(not useful):
        print("Trying...")
        pddl_problem, pddl_problem_wo_constraints, init_desc, goal_desc, constr_desc = generate_problem(num_locations, num_items, num_goals, num_constraints)
        useful = is_useful_instance(pddl_problem, pddl_problem_wo_constraints, init_desc, goal_desc, constr_desc)

    return pddl_problem, init_desc, goal_desc, constr_desc

# CLI Argument Parsing
def main():
    parser = argparse.ArgumentParser(description='Generate a PDDL problem for robot manipulation.')
    parser.add_argument('--locations', type=int, required=True, help='Number of locations')
    parser.add_argument('--items', type=int, required=True, help='Number of items')
    parser.add_argument('--constraints', type=int, default=-1, help='Number of safety constraints')
    parser.add_argument('--goals', type=int, default=-1, help='Number of goals')
    parser.add_argument('--problems', type=int, default=1, help='Number of problems to generate')
    
    args = parser.parse_args()

    os.makedirs("tmp", exist_ok=True)
    for i in range(1, args.problems + 1):
        problem_pddl, init_desc, goal_desc, constr_desc = generate_one_useful_instance(args.locations, args.items, args.goals, args.constraints)
        
        file_path = f"tmp/{i}.pddl"
        with open(file_path, "w") as file:
            file.write(problem_pddl)
        
        file_path = f"tmp/{i}.init.nl"
        with open(file_path, "w") as file:
            file.write(init_desc)
        
        file_path = f"tmp/{i}.goal.nl"
        with open(file_path, "w") as file:
            file.write(goal_desc)
        
        file_path = f"tmp/{i}.constraints.nl"
        with open(file_path, "w") as file:
            file.write(constr_desc)


if __name__ == '__main__':
    main()
