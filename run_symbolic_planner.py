import argparse
from juliacall import Main as jl
import planners

# Initialize Julia and load PDDL package
jl.seval('using PDDL, SymbolicPlanners')

def main():
    parser = argparse.ArgumentParser(description="Run symbolic planner on given PDDL files.")
    parser.add_argument("domain_file", type=str, help="Path to the domain PDDL file.")
    parser.add_argument("problem_file", type=str, help="Path to the problem PDDL file.")
    parser.add_argument("--julia-planner", action="store_true", help="Use the SymbolicPlanners.jl planner.")
    
    args = parser.parse_args()
    # Read the PDDL files
    with open(args.domain_file, 'r') as domain_file:
        domain_pddl_text = domain_file.read()
    
    with open(args.problem_file, 'r') as problem_file:
        problem_pddl_text = problem_file.read()

    # Run the symbolic planner
    if args.julia_planner:
        solution = planners.run_symbolic_planner_jl(domain_pddl_text, problem_pddl_text)
    else:
        solution = planners.run_fast_downward_planner(domain_pddl_text, problem_pddl_text)


    # Print the solution
    print(solution)

if __name__ == "__main__":
    main()
