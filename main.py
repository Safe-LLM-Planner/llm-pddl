import argparse
import glob
import json
import os
import random
import sys
import time
import backoff
import textattack

import openai

# FAST_DOWNWARD_ALIAS = "lama"
# FAST_DOWNWARD_ALIAS = "seq-opt-fdss-1"
FAST_DOWNWARD_ALIAS = None
# FAST_DOWNWARD_SEARCH = "eager_greedy([add()])"
FAST_DOWNWARD_SEARCH = None
JULIA_PLANNER_SCRIPT = "run_planner.jl"

def postprocess(x):
    return x.strip()


def get_cost(x):
    splitted = x.split()
    counter = 0
    found = False
    cost = 1e5
    for i, xx in enumerate(splitted):
        if xx == "cost":
            counter = i
            found = True
            break
    if found:
        cost = float(splitted[counter+2])
    return cost

def plan_and_collect(run, method, task_suffix, time_limit, domain_pddl_file, task_pddl_file_name):

    # C. run fastforward to plan
    plan_file_name = f"./experiments/run{run}/plans/{method}/{task_suffix}"
    sas_file_name  = f"./experiments/run{run}/plans/{method}/{task_suffix}.sas"
    if(FAST_DOWNWARD_ALIAS):
        run_command = f"python ./downward/fast-downward.py --alias {FAST_DOWNWARD_ALIAS} " + \
                f"--search-time-limit {time_limit} --plan-file {plan_file_name} " + \
                f"--sas-file {sas_file_name} " + \
                f"{domain_pddl_file} {task_pddl_file_name}"
    elif (FAST_DOWNWARD_SEARCH):
        run_command = f"python ./downward/fast-downward.py " + \
                f"--search-time-limit {time_limit} --plan-file {plan_file_name} " + \
                f"--sas-file {sas_file_name} " + \
                f"{domain_pddl_file} {task_pddl_file_name} " + \
                f"--search '{FAST_DOWNWARD_SEARCH}'"
    else:
        run_command = f"julia {JULIA_PLANNER_SCRIPT} {domain_pddl_file} {task_pddl_file_name} {plan_file_name}"
    
    # print(run_command)
    os.system(run_command)

    # D. collect the least cost plan
    best_cost = 1e10
    best_plan = None
    for fn in glob.glob(f"{plan_file_name}.*"):
        with open(fn, "r") as f:
            try:
                plans = f.readlines()
                cost = get_cost(plans[-1])
                if cost < best_cost:
                    best_cost = cost
                    best_plan = "\n".join([p.strip() for p in plans[:-1]])
            except:
                continue

    return best_plan, best_cost

###############################################################################
#
# Define different problem domains
#
###############################################################################

DOMAINS = [
    "barman",
    "blocksworld",
    "floortile",
    "grippers",
    "storage",
    "termes",
    "tyreworld",
    "manipulation"
]


class Domain:
    def __init__(self):
        # every domain should contain the context as in "in-context learning" (ICL)
        # which are the example problem in natural language.
        # For instance, in our case, context is:
        # 1. p_example.nl  (a language description of the problem)
        # 2. p_example.pddl (the ground-truth problem pddl for the problem)
        # 3. p_example.sol  (the ground-truth solution in natural language to the problem)
        self.context = ("p_example.nl", "p_example.pddl", "p_example.sol")
        self.tasks = [] # should be list of tuples like (descritpion, ground_truth_pddl)

        self.grab_tasks()

    def grab_tasks(self):
        path = f"./domains/{self.name}"
        nls = []
        for fn in glob.glob(f"{path}/*.nl"):
            fn_ = fn.split("/")[-1]
            if "domain" not in fn_ and "p_example" not in fn_:
                if os.path.exists(fn.replace("nl", "pddl")):
                    nls.append(fn_)
        sorted_nls = sorted(nls)
        self.tasks = [(nl, nl.replace("nl", "pddl")) for nl in sorted_nls]

    def __len__(self):
        return len(self.tasks)

    def get_task_suffix(self, i):
        nl, pddl = self.tasks[i]
        return f"{self.name}/{pddl}"

    def get_task_file(self, i):
        nl, pddl = self.tasks[i]
        return f"./domains/{self.name}/{nl}", f"./domains/{self.name}/{pddl}"

    def get_task(self, i):
        nl_f, pddl_f = self.get_task_file(i)
        with open(nl_f, 'r') as f:
            nl = f.read()
        with open(pddl_f, 'r') as f:
            pddl = f.read()
        return postprocess(nl), postprocess(pddl)

    def get_context(self):
        nl_f   = f"./domains/{self.name}/{self.context[0]}"
        pddl_f = f"./domains/{self.name}/{self.context[1]}"
        sol_f  = f"./domains/{self.name}/{self.context[2]}"
        with open(nl_f, 'r') as f:
            nl   = f.read()
        with open(pddl_f, 'r') as f:
            pddl = f.read()
        with open(sol_f, 'r') as f:
            sol  = f.read()
        return postprocess(nl), postprocess(pddl), postprocess(sol)

    def get_domain_pddl(self):
        domain_pddl_f = self.get_domain_pddl_file()
        with open(domain_pddl_f, 'r') as f:
            domain_pddl = f.read()
        return postprocess(domain_pddl)

    def get_domain_pddl_file(self):
        domain_pddl_f = f"./domains/{self.name}/domain.pddl"
        return domain_pddl_f

    def get_domain_nl(self):
        domain_nl_f = self.get_domain_nl_file()
        try:
            with open(domain_nl_f, 'r') as f:
                domain_nl = f.read()
        except:
            domain_nl = "Nothing"
        return postprocess(domain_nl)

    def get_domain_nl_file(self):
        domain_nl_f = f"./domains/{self.name}/domain.nl"
        return domain_nl_f


class Barman(Domain):
    name = "barman" # this should match the directory name

class Floortile(Domain):
    name = "floortile" # this should match the directory name

class Termes(Domain):
    name = "termes" # this should match the directory name

class Tyreworld(Domain):
    name = "tyreworld" # this should match the directory name

class Grippers(Domain):
    name = "grippers" # this should match the directory name

class Storage(Domain):
    name = "storage" # this should match the directory name

class Blocksworld(Domain):
    name = "blocksworld" # this should match the directory name

class Manipulation(Domain):
    name = "manipulation" # this should match the directory name

###############################################################################
#
# The agent that leverages classical planner to help LLMs to plan
#
###############################################################################


class Planner:
    def __init__(self):
        self.openai_api_keys = self.load_openai_keys()
        self.use_chatgpt = True

    def load_openai_keys(self,):
        openai_keys_file = os.path.join(os.getcwd(), "keys/openai_keys.txt")
        with open(openai_keys_file, "r") as f:
            context = f.read()
        context_lines = context.strip().split('\n')
        print(context_lines)
        return context_lines

    def create_llm_prompt(self, task_nl, domain_nl):
        # Baseline 1 (LLM-as-P): directly ask the LLM for plan
        prompt = f"{domain_nl} \n" + \
                 f"Now consider a planning problem. " + \
                 f"The problem description is: \n {task_nl} \n" + \
                 f"Can you provide a correct plan, in the way of a " + \
                 f"sequence of behaviors, to solve the problem?"
        return prompt

    def create_llm_stepbystep_prompt(self, task_nl, domain_nl):
        # Baseline 1 (LLM-as-P): directly ask the LLM for plan
        prompt = f"{domain_nl} \n" + \
                 f"Now consider a planning problem. " + \
                 f"The problem description is: \n {task_nl} \n" + \
                 f"Can you provide a correct plan, in the way of a " + \
                 f"sequence of behaviors, to solve the problem? \n" + \
                 f"Please think step by step."
        return prompt

    def create_llm_tot_ic_prompt(self, task_nl, domain_nl, context, plan):
        context_nl, context_pddl, context_sol = context
        prompt = f"Given the current state, provide the set of feasible actions and their corresponding next states, using the format 'action -> state'. \n" + \
                 f"Keep the list short. Think carefully about the requirements of the actions you select and make sure they are met in the current state. \n" + \
                 f"Start with actions that are most likely to make progress towards the goal. \n" + \
                 f"Only output one action per line. Do not return anything else. " + \
                 f"Here are the rules. \n {domain_nl} \n\n" + \
                 f"An example planning problem is: \n {context_nl} \n" + \
                 f"A plan for the example problem is: \n {context_sol} \n" + \
                 f"Now I have a new planning problem and its description is: \n {task_nl} \n" + \
                 f"You have taken the following actions: \n {plan} \n"
        # print(prompt)
        return prompt

    def create_llm_tot_ic_value_prompt(self, task_nl, domain_nl, context, plan):
        context_nl, context_pddl, context_sol = context
        context_sure_1 = context_sol.split('\n')[0]
        context_sure_2 = context_sol.split('\n')[0] + context_sol.split('\n')[1]
        context_impossible_1 = '\n'.join(context_sol.split('\n')[1:])
        context_impossible_2 = context_sol.split('\n')[-1]
        '''
        prompt = f"Evaluate if a given plan reaches the goal or is an optimal partial plan towards the goal (reached/sure/maybe/impossible). \n" + \
                 f"Only answer 'reached' if the goal conditions are reached by the exact plan in the prompt. \n" + \
                 f"Only answer 'sure' if you are sure that preconditions are satisfied for all actions in the plan, and the plan makes fast progress towards the goal. \n" + \
                 f"Answer 'impossible' if one of the actions has unmet preconditions. \n" + \
                 f"Here are the rules. \n {domain_nl} \n\n" + \
                 f"Here are some example evaluations for the planning problem: \n {context_nl} \n\n " + \
                 f"Plan: {context_sure_1} \n" + \
                 f"Answer: Sure. \n\n" + \
                 f"Plan: {context_sure_2} \n" + \
                 f"Answer: Sure. \n\n" + \
                 f"Plan: {context_sol} \n" + \
                 f"Answer: Reached. \n\n" + \
                 f"Plan: {context_impossible_1} \n" + \
                 f"Answer: Impossible. \n\n" + \
                 f"Plan: {context_impossible_2} \n" + \
                 f"Answer: Impossible. \n\n" + \
                 f"Now I have a new planning problem and its description is: \n {task_nl} \n" + \
                 f"Evaluate the following partial plan as reached/sure/maybe/impossible. DO NOT RETURN ANYTHING ELSE. DO NOT TRY TO COMPLETE THE PLAN. \n" + \
                 f"Plan: {plan} \n"
        '''
        prompt = f"Determine if a given plan reaches the goal or give your confidence score that it is an optimal partial plan towards the goal (reached/impossible/0-1). \n" + \
                 f"Only answer 'reached' if the goal conditions are reached by the exact plan in the prompt. \n" + \
                 f"Answer 'impossible' if one of the actions has unmet preconditions. \n" + \
                 f"Otherwise,give a number between 0 and 1 as your evaluation of the partial plan's progress towards the goal. \n" + \
                 f"Here are the rules. \n {domain_nl} \n\n" + \
                 f"Here are some example evaluations for the planning problem: \n {context_nl} \n\n " + \
                 f"Plan: {context_sure_1} \n" + \
                 f"Answer: 0.8. \n\n" + \
                 f"Plan: {context_sure_2} \n" + \
                 f"Answer: 0.9. \n\n" + \
                 f"Plan: {context_sol} \n" + \
                 f"Answer: Reached. \n\n" + \
                 f"Plan: {context_impossible_1} \n" + \
                 f"Answer: Impossible. \n\n" + \
                 f"Plan: {context_impossible_2} \n" + \
                 f"Answer: Impossible. \n\n" + \
                 f"Now I have a new planning problem and its description is: \n {task_nl} \n" + \
                 f"Evaluate the following partial plan as reached/impossible/0-1. DO NOT RETURN ANYTHING ELSE. DO NOT TRY TO COMPLETE THE PLAN. \n" + \
                 f"Plan: {plan} \n"

        return prompt


    def tot_bfs(self, task_nl, domain_nl, context, time_left=200, max_depth=2):
        from queue import PriorityQueue
        start_time = time.time()
        plan_queue = PriorityQueue()
        plan_queue.put((0, ""))
        while time.time() - start_time < time_left and not plan_queue.empty():
            priority, plan = plan_queue.get()
            # print (priority, plan)
            steps = plan.split('\n')
            if len(steps) > max_depth:
                return ""
            candidates_prompt = self.create_llm_tot_ic_prompt(task_nl, domain_nl, context, plan)
            candidates = self.query(candidates_prompt).strip()
            print (candidates)
            lines = candidates.split('\n')
            for line in lines:
                if time.time() - start_time > time_left:
                    break
                if len(line) > 0 and '->' in line:
                    new_plan = plan + "\n" + line
                    value_prompt = self.create_llm_tot_ic_value_prompt(task_nl, domain_nl, context, new_plan)
                    answer = self.query(value_prompt).strip().lower()
                    print(new_plan)
                    print("Response \n" + answer)

                    if "reached" in answer:
                        return new_plan

                    if "impossible" in answer:
                        continue

                    if "answer: " in answer:
                        answer = answer.split("answer: ")[1]

                    try:
                        score = float(answer)
                    except ValueError:
                        continue

                    if score > 0:
                        new_priority = priority + 1 / score
                        plan_queue.put((new_priority, new_plan))

        return ""

    def create_llm_ic_prompt(self, task_nl, domain_nl, context):
        # Baseline 2 (LLM-as-P with context): directly ask the LLM for plan
        context_nl, context_pddl, context_sol = context
        prompt = f"{domain_nl} \n" + \
                 f"An example planning problem is: \n {context_nl} \n" + \
                 f"A plan for the example problem is: \n {context_sol} \n" + \
                 f"Now I have a new planning problem and its description is: \n {task_nl} \n" + \
                 f"Can you provide a correct plan, in the way of a " + \
                 f"sequence of behaviors, to solve the problem?"
        return prompt

    def create_llm_pddl_prompt(self, task_nl, domain_nl):
        # Baseline 3 (LM+P w/o context), no context, create the problem PDDL
        prompt = f"{domain_nl} \n" + \
                 f"Now consider a planning problem. " + \
                 f"The problem description is: \n {task_nl} \n" + \
                 f"Provide me with the problem PDDL file that describes " + \
                 f"the planning problem directly without further explanations?" +\
                 f"Keep the domain name consistent in the problem PDDL. Only return the PDDL file. Do not return anything else."
        return prompt

    def create_llm_ic_pddl_prompt(self, task_nl, domain_pddl, context):
        # our method (LM+P), create the problem PDDL given the context
        context_nl, context_pddl, context_sol = context
        prompt = f"I want you to solve planning problems. " + \
                 f"An example planning problem is: \n {context_nl} \n" + \
                 f"The problem PDDL file to this problem is: \n {context_pddl} \n" + \
                 f"Now I have a new planning problem and its description is: \n {task_nl} \n" + \
                 f"Provide me with the problem PDDL file that describes " + \
                 f"the new planning problem directly without further explanations? Only return the PDDL file. Do not return anything else."
        return prompt

    def query(self, prompt_text):
        server_flag = 0
        server_cnt = 0
        result_text = ""
        while server_cnt < 10:
            try:
                self.update_key()
                if self.use_chatgpt: # currently, we will always use chatgpt
                    @backoff.on_exception(backoff.expo, openai.error.RateLimitError)
                    def completions_with_backoff(**kwargs):
                        return openai.ChatCompletion.create(**kwargs)

                    # response = openai.ChatCompletion.create(
                    response = completions_with_backoff(
                        model="gpt-4",
                        temperature=0.0,
                        top_p=1,
                        frequency_penalty=0,
                        presence_penalty=0,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt_text},
                        ],
                    )
                    result_text = response['choices'][0]['message']['content']
                else:
                    response =  openai.Completion.create(
                        model="text-davinci-003",
                        prompt=prompt_text,
                        temperature=0.0,
                        max_tokens=1024,
                        top_p=1,
                        frequency_penalty=0,
                        presence_penalty=0
                    )
                    result_text = response['choices'][0]['text']
                server_flag = 1
                if server_flag:
                    break
            except Exception as e:
                server_cnt += 1
                print(e)
        return result_text

    def update_key(self):
        curr_key = self.openai_api_keys[0]
        openai.api_key = curr_key
        self.openai_api_keys.remove(curr_key)
        self.openai_api_keys.append(curr_key)

    def parse_result(self, pddl_string):
        # remove extra texts
        #try:
        #    beg = pddl_string.find("```") + 3
        #    pddl_string = pddl_string[beg: beg + pddl_string[beg:].find("```")]
        #except:
        #    raise Exception("[error] cannot find ```pddl-file``` in the pddl string")

        # remove comments, they can cause error
        #t0 = time.time()
        #while pddl_string.find(";") >= 0:
        #    start = pddl_string.find(";")
        #    i = 0
        #    while pddl_string[start+i] != ")" and pddl_string[start+i] != "\n":
        #        i += 1
        #    pddl_string = pddl_string[:start] + pddl_string[start+i:]
        #pddl_string = pddl_string.strip() + "\n"
        #t1 = time.time()
        #print(f"[info] remove comments takes {t1-t0} sec")
        return pddl_string

    def plan_to_language(self, plan, task_nl, domain_nl, domain_pddl):
        domain_pddl_ = " ".join(domain_pddl.split())
        task_nl_ = " ".join(task_nl.split())
        prompt = f"A planning problem is described as: \n {task_nl} \n" + \
                 f"The corresponding domain PDDL file is: \n {domain_pddl_} \n" + \
                 f"A correct PDDL plan is: \n {plan} \n" + \
                 f"Transform the PDDL plan into a sequence of behaviors without further explanation."
        res = self.query(prompt).strip() + "\n"
        return res

def llm_ic_pddl_planner(args, planner, domain):
    """
    Our method:
        context: (task natural language, task problem PDDL)
        Condition on the context (task description -> task problem PDDL),
        LLM will be asked to provide the problem PDDL of a new task description.
        Then, we use a planner to find a correct solution, and translate
        that back to natural language.
    """

    def aux(task_suffix, task_nl):
        start_time = time.time()

        # A. generate problem pddl file
        
        prompt             = planner.create_llm_ic_pddl_prompt(task_nl, domain_pddl, context)
        raw_result         = planner.query(prompt)
        task_pddl_         = planner.parse_result(raw_result)

        # B. write the problem file into the problem folder
        task_pddl_file_name = f"./experiments/run{args.run}/problems/llm_ic_pddl/{task_suffix}"
        with open(task_pddl_file_name, "w") as f:
            f.write(task_pddl_)
        time.sleep(1)

        # C. run fastforward to plan
        # D. collect the least cost plan
        best_plan, best_cost = plan_and_collect(args.run, "llm_ic_pddl", task_suffix,args.time_limit,domain_pddl_file,task_pddl_file_name)

        # E. translate the plan back to natural language, and write it to result
        # commented out due to exceeding token limit of gpt-4
        '''
        if best_plan:
            plans_nl = planner.plan_to_language(best_plan, task_nl, domain_nl, domain_pddl)
            plan_nl_file_name = f"./experiments/run{args.run}/results/llm_ic_pddl/{task_suffix}"
            with open(plan_nl_file_name, "w") as f:
                f.write(plans_nl)
        '''
        end_time = time.time()
        if best_plan:
            print(f"[info] task {task} takes {end_time - start_time} sec, found a plan with cost {best_cost}")
        else:
            print(f"[info] task {task} takes {end_time - start_time} sec, no solution found")

    context          = domain.get_context()
    domain_pddl      = domain.get_domain_pddl()
    domain_pddl_file = domain.get_domain_pddl_file()
    domain_nl        = domain.get_domain_nl()
    domain_nl_file   = domain.get_domain_nl_file()

    # create the tmp / result folders
    problem_folder = f"./experiments/run{args.run}/problems/llm_ic_pddl/{domain.name}"
    plan_folder    = f"./experiments/run{args.run}/plans/llm_ic_pddl/{domain.name}"
    result_folder  = f"./experiments/run{args.run}/results/llm_ic_pddl/{domain.name}"

    os.makedirs(problem_folder, exist_ok=True)
    os.makedirs(plan_folder, exist_ok=True)
    os.makedirs(result_folder, exist_ok=True)

    task = args.task

    if(args.command == "robustness-experiment"):

        perturbations_folder = f"./experiments/run{args.run}/perturbed_descriptions/"

        task_suffix = domain.get_task_suffix(task)
        task_suffix = os.path.splitext(task_suffix)[0]

        for fn in glob.glob(f"{perturbations_folder}/{task_suffix}_*"):
            perturbed_task_suffix = f"{domain.name}/{os.path.splitext(os.path.basename(fn))[0]}.pddl"
            with open(fn, "r") as f:
                perturbed_task_nl = f.read()
                aux(perturbed_task_suffix, perturbed_task_nl)

    else:
        task_suffix = domain.get_task_suffix(task)
        task_nl, _ = domain.get_task(task) 
        aux(task_suffix, task_nl)

def llm_pddl_planner(args, planner, domain):
    """
    Baseline method:
        Same as ours, except that no context is given. In other words, the LLM
        will be asked to directly give a problem PDDL file without any context.
    """
    context          = domain.get_context()
    domain_pddl      = domain.get_domain_pddl()
    domain_pddl_file = domain.get_domain_pddl_file()
    domain_nl        = domain.get_domain_nl()
    domain_nl_file   = domain.get_domain_nl_file()

    # create the tmp / result folders
    problem_folder = f"./experiments/run{args.run}/problems/llm_pddl/{domain.name}"
    plan_folder    = f"./experiments/run{args.run}/plans/llm_pddl/{domain.name}"
    result_folder  = f"./experiments/run{args.run}/results/llm_pddl/{domain.name}"

    if not os.path.exists(problem_folder):
        os.system(f"mkdir -p {problem_folder}")
    if not os.path.exists(plan_folder):
        os.system(f"mkdir -p {plan_folder}")
    if not os.path.exists(result_folder):
        os.system(f"mkdir -p {result_folder}")

    task = args.task

    start_time = time.time()

    # A. generate problem pddl file
    task_suffix        = domain.get_task_suffix(task)
    task_nl, task_pddl = domain.get_task(task) 
    prompt             = planner.create_llm_pddl_prompt(task_nl, domain_nl)
    raw_result         = planner.query(prompt)
    task_pddl_         = planner.parse_result(raw_result)

    # B. write the problem file into the problem folder
    task_pddl_file_name = f"./experiments/run{args.run}/problems/llm_pddl/{task_suffix}"
    with open(task_pddl_file_name, "w") as f:
        f.write(task_pddl_)
    time.sleep(1)

    # C. run fastforward to plan
    # D. collect the least cost plan
    best_plan, best_cost = plan_and_collect(args.run, "llm_pddl", task_suffix,args.time_limit,domain_pddl_file,task_pddl_file_name)

    # E. translate the plan back to natural language, and write it to result
    # commented out due to exceeding token limit of gpt-4
    '''
    if best_plan:
        plans_nl = planner.plan_to_language(best_plan, task_nl, domain_nl, domain_pddl)
        plan_nl_file_name = f"./experiments/run{args.run}/results/llm_pddl/{task_suffix}"
        with open(plan_nl_file_name, "w") as f:
            f.write(plans_nl)
    '''
    end_time = time.time()
    if best_plan:
        print(f"[info] task {task} takes {end_time - start_time} sec, found a plan with cost {best_cost}")
    else:
        print(f"[info] task {task} takes {end_time - start_time} sec, no solution found")


def llm_planner(args, planner, domain):
    """
    Baseline method:
        The LLM will be asked to directly give a plan based on the task description.
    """
    context          = domain.get_context()
    domain_pddl      = domain.get_domain_pddl()
    domain_pddl_file = domain.get_domain_pddl_file()
    domain_nl        = domain.get_domain_nl()
    domain_nl_file   = domain.get_domain_nl_file()

    # create the tmp / result folders
    problem_folder = f"./experiments/run{args.run}/problems/llm/{domain.name}"
    plan_folder    = f"./experiments/run{args.run}/plans/llm/{domain.name}"
    result_folder  = f"./experiments/run{args.run}/results/llm/{domain.name}"

    if not os.path.exists(problem_folder):
        os.system(f"mkdir -p {problem_folder}")
    if not os.path.exists(plan_folder):
        os.system(f"mkdir -p {plan_folder}")
    if not os.path.exists(result_folder):
        os.system(f"mkdir -p {result_folder}")

    task = args.task

    start_time = time.time()

    # A. generate problem pddl file
    task_suffix        = domain.get_task_suffix(task)
    task_nl, task_pddl = domain.get_task(task) 
    prompt             = planner.create_llm_prompt(task_nl, domain_nl)
    text_plan          = planner.query(prompt)

    # B. write the problem file into the problem folder
    text_plan_file_name = f"./experiments/run{args.run}/results/llm/{task_suffix}"
    with open(text_plan_file_name, "w") as f:
        f.write(text_plan)
    end_time = time.time()
    print(f"[info] task {task} takes {end_time - start_time} sec")


def llm_stepbystep_planner(args, planner, domain):
    """
    Baseline method:
        The LLM will be asked to directly give a plan based on the task description.
    """
    context          = domain.get_context()
    domain_pddl      = domain.get_domain_pddl()
    domain_pddl_file = domain.get_domain_pddl_file()
    domain_nl        = domain.get_domain_nl()
    domain_nl_file   = domain.get_domain_nl_file()

    # create the tmp / result folders
    problem_folder = f"./experiments/run{args.run}/problems/llm_step/{domain.name}"
    plan_folder    = f"./experiments/run{args.run}/plans/llm_step/{domain.name}"
    result_folder  = f"./experiments/run{args.run}/results/llm_step/{domain.name}"

    if not os.path.exists(problem_folder):
        os.system(f"mkdir -p {problem_folder}")
    if not os.path.exists(plan_folder):
        os.system(f"mkdir -p {plan_folder}")
    if not os.path.exists(result_folder):
        os.system(f"mkdir -p {result_folder}")

    task = args.task

    start_time = time.time()

    # A. generate problem pddl file
    task_suffix        = domain.get_task_suffix(task)
    task_nl, task_pddl = domain.get_task(task) 
    prompt             = planner.create_llm_stepbystep_prompt(task_nl, domain_nl)
    text_plan          = planner.query(prompt)

    # B. write the problem file into the problem folder
    text_plan_file_name = f"./experiments/run{args.run}/results/llm_step/{task_suffix}"
    with open(text_plan_file_name, "w") as f:
        f.write(text_plan)
    end_time = time.time()
    print(f"[info] task {task} takes {end_time - start_time} sec")


def llm_tot_ic_planner(args, planner, domain):
    """
    Tree of Thoughts planner
    """
    context          = domain.get_context()
    domain_pddl      = domain.get_domain_pddl()
    domain_pddl_file = domain.get_domain_pddl_file()
    domain_nl        = domain.get_domain_nl()
    domain_nl_file   = domain.get_domain_nl_file()

    # create the tmp / result folders
    problem_folder = f"./experiments/run{args.run}/problems/llm_tot_ic/{domain.name}"
    plan_folder    = f"./experiments/run{args.run}/plans/llm_tot_ic/{domain.name}"
    result_folder  = f"./experiments/run{args.run}/results/llm_tot_ic/{domain.name}"

    if not os.path.exists(problem_folder):
        os.system(f"mkdir -p {problem_folder}")
    if not os.path.exists(plan_folder):
        os.system(f"mkdir -p {plan_folder}")
    if not os.path.exists(result_folder):
        os.system(f"mkdir -p {result_folder}")

    task = args.task

    start_time = time.time()

    # A. generate problem pddl file
    task_suffix        = domain.get_task_suffix(task)
    task_nl, task_pddl = domain.get_task(task)
    text_plan = planner.tot_bfs(task_nl, domain_nl, context, time_left=200, max_depth=10)

    # B. write the problem file into the problem folder
    text_plan_file_name = f"./experiments/run{args.run}/results/llm_tot_ic/{task_suffix}"
    with open(text_plan_file_name, "w") as f:
        f.write(text_plan)
    end_time = time.time()
    print(f"[info] task {task} takes {end_time - start_time} sec")


def llm_ic_planner(args, planner, domain):
    """
    Baseline method:
        The LLM will be asked to directly give a plan based on the task description.
    """

    def aux(task_suffix, task_nl):
        start_time = time.time()

        # A. generate problem pddl file

        prompt             = planner.create_llm_ic_prompt(task_nl, domain_nl, context)
        text_plan          = planner.query(prompt)

        # B. write the problem file into the problem folder
        text_plan_file_name = f"./experiments/run{args.run}/results/llm_ic/{task_suffix}"
        with open(text_plan_file_name, "w") as f:
            f.write(text_plan)
        end_time = time.time()
        print(f"[info] task {task} takes {end_time - start_time} sec")

    context          = domain.get_context()
    domain_pddl      = domain.get_domain_pddl()
    domain_pddl_file = domain.get_domain_pddl_file()
    domain_nl        = domain.get_domain_nl()
    domain_nl_file   = domain.get_domain_nl_file()

    # create the tmp / result folders
    problem_folder = f"./experiments/run{args.run}/problems/llm_ic/{domain.name}"
    plan_folder    = f"./experiments/run{args.run}/plans/llm_ic/{domain.name}"
    result_folder  = f"./experiments/run{args.run}/results/llm_ic/{domain.name}"

    os.makedirs(problem_folder, exist_ok=True)
    os.makedirs(plan_folder, exist_ok=True)
    os.makedirs(result_folder, exist_ok=True)

    task = args.task

    if(args.command == "robustness-experiment"):

        perturbations_folder = f"./experiments/run{args.run}/perturbed_descriptions/"

        task_suffix = domain.get_task_suffix(task)
        task_suffix = os.path.splitext(task_suffix)[0]

        for fn in glob.glob(f"{perturbations_folder}/{task_suffix}_*"):
            perturbed_task_suffix = f"{domain.name}/{os.path.splitext(os.path.basename(fn))[0]}.pddl"
            with open(fn, "r") as f:
                perturbed_task_nl = f.read()
                aux(perturbed_task_suffix, perturbed_task_nl)

    else:
        task_suffix = domain.get_task_suffix(task)
        task_nl, _ = domain.get_task(task) 
        aux(task_suffix, task_nl)

def print_all_prompts(planner):
    for domain_name in DOMAINS:
        domain = eval(domain_name.capitalize())()
        context = domain.get_context()
        domain_pddl = domain.get_domain_pddl()
        domain_pddl_file = domain.get_domain_pddl_file()
        domain_nl = domain.get_domain_nl()
        
        for folder_name in [
            f"./prompts/llm/{domain.name}",
            f"./prompts/llm_step/{domain.name}",
            f"./prompts/llm_ic/{domain.name}",
            f"./prompts/llm_pddl/{domain.name}",
            f"./prompts/llm_ic_pddl/{domain.name}"]:
            if not os.path.exists(folder_name):
                os.system(f"mkdir -p {folder_name}")

        for task in range(len(domain)):
            task_nl_file, task_pddl_file = domain.get_task_file(task) 
            task_nl, task_pddl = domain.get_task(task) 
            task_suffix = domain.get_task_suffix(task)

            llm_prompt = planner.create_llm_prompt(task_nl, domain_nl)
            llm_stepbystep_prompt = planner.create_llm_stepbystep_prompt(task_nl, domain_nl)
            llm_ic_prompt = planner.create_llm_ic_prompt(task_nl, domain_nl, context)
            llm_pddl_prompt = planner.create_llm_pddl_prompt(task_nl, domain_nl)
            llm_ic_pddl_prompt = planner.create_llm_ic_pddl_prompt(task_nl, domain_pddl, context)
            with open(f"./prompts/llm/{task_suffix}.prompt", "w") as f:
                f.write(llm_prompt)
            with open(f"./prompts/llm_step/{task_suffix}.prompt", "w") as f:
                f.write(llm_stepbystep_prompt)
            with open(f"./prompts/llm_ic/{task_suffix}.prompt", "w") as f:
                f.write(llm_ic_prompt)
            with open(f"./prompts/llm_pddl/{task_suffix}.prompt", "w") as f:
                f.write(llm_pddl_prompt)
            with open(f"./prompts/llm_ic_pddl/{task_suffix}.prompt", "w") as f:
                f.write(llm_ic_pddl_prompt)

def produce_perturbations(args, domain):

    task = args.task

    # produce perturbed instructions
    task_nl, _ = domain.get_task(task)
    task_suffix = domain.get_task_suffix(task)
    task_suffix = os.path.splitext(task_suffix)[0]

    augmenter_classes = {
        "wordnet": textattack.augmentation.recipes.WordNetAugmenter,
        "charswap": textattack.augmentation.recipes.CharSwapAugmenter,
        "back_trans": textattack.augmentation.recipes.BackTranslationAugmenter,
        "back_transcription": textattack.augmentation.recipes.BackTranscriptionAugmenter
    }

    augmenter = augmenter_classes[args.perturbation_recipe](
                                                    pct_words_to_swap=args.pct_words_to_swap, 
                                                    transformations_per_example=10)
    perturbed_task_nl_list = augmenter.augment(task_nl)

    # create the tmp / result folders
    perturbations_folder = f"./experiments/run{args.run}/perturbed_descriptions/"

    if not os.path.exists(perturbations_folder):
        os.makedirs(f"{perturbations_folder}/{domain.name}", exist_ok=True)
    
    for i in range(0, len(perturbed_task_nl_list)):

        with open(f"{perturbations_folder}/{task_suffix}_{i+1}.nl", "w") as f:
            f.write(perturbed_task_nl_list[i])


import argparse

def create_common_args():
    common_args = argparse.ArgumentParser(add_help=False)
    common_group = common_args.add_argument_group('common arguments')
    common_group.add_argument('--domain', type=str, choices=DOMAINS, default="barman")
    common_group.add_argument('--time-limit', type=int, default=200)
    common_group.add_argument('--task', type=int, default=0)
    common_group.add_argument('--run', type=int, default=-1)
    common_group.add_argument('--print-prompts', action='store_true')
    return common_args

def create_parser():
    common_args = create_common_args()
    
    parser = argparse.ArgumentParser(description="LLM-Planner", parents=[common_args])
    parser.add_argument('--method', type=str, choices=["llm_ic_pddl_planner",
                                                        "llm_pddl_planner",
                                                        "llm_planner",
                                                        "llm_stepbystep_planner",
                                                        "llm_ic_planner",
                                                        "llm_tot_ic_planner"],
                                                        default="llm_ic_pddl_planner",
                                                        nargs="+"
                                                        )
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest='command')

    # Create the robustness experiment subcommand
    robustness_parser = subparsers.add_parser('robustness-experiment',
                                              help='Run robustness experiment',
                                              parents=[common_args])

    # Add additional arguments specific to robustness experiment
    robustness_parser.add_argument('--method', type=str, choices=["llm_ic_pddl_planner",
                                                                    # "llm_pddl_planner",
                                                                    # "llm_planner",
                                                                    # "llm_stepbystep_planner",
                                                                    "llm_ic_planner",
                                                                    # "llm_tot_ic_planner"
                                                                    ],
                                                                    default="llm_ic_pddl_planner",
                                                                    nargs="+"
                                                                    )
    robustness_parser.add_argument('--perturbation-recipe', type=str, choices=[
                                                                                "wordnet",
                                                                                "charswap",
                                                                                "back_trans",
                                                                                "back_transcription"
                                                                                ]
                                                                                )
    robustness_parser.add_argument('--pct-words-to-swap', type=restricted_float, help='Percentage of words to transform')

    return parser

def restricted_float(x):
    try:
        x = float(x)
    except ValueError:
        raise argparse.ArgumentTypeError("%r not a floating-point literal" % (x,))

    if x < 0.0 or x > 1.0:
        raise argparse.ArgumentTypeError("%r not in range [0.0, 1.0]"%(x,))
    return x

def save_args_to_file(args, filename):
    # Convert args namespace to a dictionary
    args_dict = vars(args)
    
    # Write to file
    with open(filename, 'w') as f:
        for key, value in args_dict.items():
            f.write(f"{key}: {value}\n")

def find_next_missing_run(directory):
    # List all items in the directory
    items = os.listdir(directory)
    
    # Filter out directories that start with 'run' and extract the numbers
    run_numbers = []
    for item in items:
        if item.startswith('run') and item[3:].isdigit():
            run_numbers.append(int(item[3:]))
    
    # Find the next missing number
    if run_numbers:
        next_run = max(run_numbers) + 1
    else:
        next_run = 0  # If no 'run' directories exist, start with 0
    
    return next_run

if __name__ == "__main__":

    parser = create_parser()
    args = parser.parse_args()
    
    # if run number is not set, compute next one
    if args.run == -1:
        args.run = find_next_missing_run("./experiments")

    # log cli arguments
    args_filepath = f"./experiments/run{args.run}/cli_args"
    os.makedirs(os.path.dirname(args_filepath))
    save_args_to_file(args, args_filepath)

    # 1. initialize problem domain
    domain = eval(args.domain.capitalize())()

    # 2. initialize the planner
    planner = Planner()

    # 3. Produce perturbations if needed
    if args.command == "robustness-experiment":
        produce_perturbations(args, domain)

    # 4. execute the llm planner
    available_methods = {
        "llm_ic_pddl_planner"   : llm_ic_pddl_planner,
        "llm_pddl_planner"      : llm_pddl_planner,
        "llm_planner"           : llm_planner,
        "llm_stepbystep_planner": llm_stepbystep_planner,
        "llm_ic_planner"        : llm_ic_planner,
        "llm_tot_ic_planner"       : llm_tot_ic_planner,
    }

    if args.print_prompts:
        print_all_prompts(planner)
    else:
        for method in args.method:
            available_methods[method](args, planner, domain)
