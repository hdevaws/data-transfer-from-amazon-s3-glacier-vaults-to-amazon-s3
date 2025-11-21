"""
Definitive ExecutionType fix for all Step Functions state machines.
This module patches CDK at multiple levels to ensure ExecutionType is always present.
"""

import json
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk.aws_stepfunctions import CfnStateMachine
from aws_cdk import CfnResource

def fix_execution_type(obj):
    """Recursively fix ExecutionType in all ProcessorConfig entries."""
    if isinstance(obj, dict):
        # Fix any ProcessorConfig
        if "ProcessorConfig" in obj:
            if not isinstance(obj["ProcessorConfig"], dict):
                obj["ProcessorConfig"] = {}
            obj["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Fix any ItemProcessor
        if "ItemProcessor" in obj:
            if not isinstance(obj["ItemProcessor"], dict):
                obj["ItemProcessor"] = {}
            if "ProcessorConfig" not in obj["ItemProcessor"]:
                obj["ItemProcessor"]["ProcessorConfig"] = {}
            obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Recursively fix all nested objects
        for value in obj.values():
            fix_execution_type(value)
    elif isinstance(obj, list):
        for item in obj:
            fix_execution_type(item)

# Store original methods
_original_cfn_init = CfnStateMachine.__init__
_original_map_to_state_json = sfn.Map.to_state_json
_original_custom_state_init = sfn.CustomState.__init__
_original_cfn_resource_render_properties = CfnResource._render_properties

def patched_cfn_init(self, scope, construct_id, **kwargs):
    """Patch CfnStateMachine.__init__ to fix definition_string."""
    if "definition_string" in kwargs and kwargs["definition_string"]:
        try:
            data = json.loads(kwargs["definition_string"])
            fix_execution_type(data)
            kwargs["definition_string"] = json.dumps(data)
        except:
            pass
    _original_cfn_init(self, scope, construct_id, **kwargs)

def patched_map_to_state_json(self):
    """Patch Map.to_state_json to fix ProcessorConfig."""
    state_json = _original_map_to_state_json(self)
    fix_execution_type(state_json)
    return state_json

def patched_custom_state_init(self, scope, construct_id, **kwargs):
    """Patch CustomState.__init__ to fix state_json."""
    if "state_json" in kwargs and kwargs["state_json"]:
        fix_execution_type(kwargs["state_json"])
    _original_custom_state_init(self, scope, construct_id, **kwargs)

def patched_render_properties(self, properties):
    """Patch CfnResource._render_properties to fix Step Functions definitions."""
    result = _original_cfn_resource_render_properties(self, properties)
    
    # Only patch Step Functions state machines
    if isinstance(self, CfnStateMachine) and result and "DefinitionString" in result:
        try:
            data = json.loads(result["DefinitionString"])
            fix_execution_type(data)
            result["DefinitionString"] = json.dumps(data)
        except:
            pass
    
    return result

# Apply all patches
CfnStateMachine.__init__ = patched_cfn_init
sfn.Map.to_state_json = patched_map_to_state_json
sfn.CustomState.__init__ = patched_custom_state_init
CfnResource._render_properties = patched_render_properties

# Also patch the definition_string property setter
if hasattr(CfnStateMachine.definition_string, 'fset'):
    original_setter = CfnStateMachine.definition_string.fset
    
    def patched_setter(self, value):
        if value:
            try:
                data = json.loads(value)
                fix_execution_type(data)
                value = json.dumps(data)
            except:
                pass
        original_setter(self, value)
    
    CfnStateMachine.definition_string = CfnStateMachine.definition_string.setter(patched_setter)

# Additional patch for DefinitionBody
if hasattr(sfn.DefinitionBody, 'bind'):
    _original_definition_body_bind = sfn.DefinitionBody.bind
    
    def patched_definition_body_bind(self, scope, state_machine):
        result = _original_definition_body_bind(self, scope, state_machine)
        if hasattr(result, 'definition_string') and result.definition_string:
            try:
                data = json.loads(result.definition_string)
                fix_execution_type(data)
                result.definition_string = json.dumps(data)
            except:
                pass
        return result
    
    sfn.DefinitionBody.bind = patched_definition_body_bind