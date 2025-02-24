from juliacall import Main as jl
from typing import Union, Literal
from pydantic import BaseModel, create_model

# Initialize Julia and load PDDL package
jl.seval('using PDDL')

class BasePydanticModelGenerator:
    def __init__(self, domain_pddl: str):
        self.domain = jl.PDDL.parse_domain(domain_pddl)

    # Function to generate Pydantic models from domain actions
    def _generate_step_models(self) -> list:
        raise NotImplementedError

    # Function to create the Response model
    def create_response_model(self):
        step_models = self._generate_step_models()

        # Create a Union of all step models
        Step = Union[tuple(step_models)]

        # Define the Response model
        class ResponseModel(BaseModel):
            steps: list[Step]

        return ResponseModel

class StrictActionsPydModelGen(BasePydanticModelGenerator):
    def _generate_step_models(self) -> list:
        # Get actions from the PDDL domain
        actions = jl.PDDL.get_actions(self.domain)

        step_models = []

        for action in actions.values():
            # Extract action name and parameters
            action_name_str = str(jl.PDDL.get_name(action))
            arg_vars = [str(arg_v).lower() for arg_v in jl.PDDL.get_argvars(action)]
            arg_types = [str(arg_t) for arg_t in jl.PDDL.get_argtypes(action)]
            args = [arg_v + "_" + arg_t for arg_v, arg_t in zip(arg_vars, arg_types)]

            # Create a dictionary for model fields
            fields = {'action_name': (Literal[action_name_str], ...)}
            
            for arg in args:
                # Assuming all parameters are strings for simplicity
                fields[arg] = (str, ...)

            # Dynamically create a Pydantic model for each action
            model_name = f"{action_name_str.capitalize()}Step"
            step_models.append(create_model(model_name, **fields, __base__=BaseModel))

        return step_models

class SentenceActionsPydModelGen(BasePydanticModelGenerator):
    def _generate_step_models(self) -> list:
        
        ArbitraryActionModel = create_model(
            "ArbitraryActionModel", 
            action=(str, ...)
            )

        return [ArbitraryActionModel]

available_pydantic_generators = {
    "strict_actions": StrictActionsPydModelGen,
    "sentence_actions": SentenceActionsPydModelGen,
    "none": None
}