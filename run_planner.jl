using PDDL, PlanningDomains, SymbolicPlanners

# load problem
domain = load_domain(ARGS[1])
problem = load_problem(ARGS[2])

# plan
planner = AStarPlanner(HAdd())
if isnothing(PDDL.get_constraints(problem))
    sol = planner(domain, problem)
else
    state = initstate(domain, problem)
    spec = StateConstrainedGoal(problem)
    sol = planner(domain, state, spec)
end

# write down plan
sol_str = join(["$(write_pddl(a))\n" for a in sol])
sol_str *= "; cost = $(length(sol))"
write(ARGS[3]*".1", sol_str)