"""
Synthesis-level ExecutionType fix that intercepts to_state_json() calls during CDK synthesis.
This ensures ExecutionType is added to all ProcessorConfig entries before state machine 
definitions are sent to AWS.
"""

import json
from typing import Any, Dict
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk.aws_stepfunctions import CfnStateMachine
from aws_cdk import CfnResource


def fix_processor_configs(obj: Any) -> None:
    """Recursively fix all ProcessorConfig entries to include ExecutionType."""
    if isinstance(obj, dict):
        # Fix ProcessorConfig if found - always ensure ExecutionType is present
        if "ProcessorConfig" in obj:
            if not isinstance(obj["ProcessorConfig"], dict):
                obj["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
            else:
                obj["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Fix ItemProcessor ProcessorConfig - ensure it exists and has ExecutionType
        if "ItemProcessor" in obj:
            if not isinstance(obj["ItemProcessor"], dict):
                obj["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
            else:
                if "ProcessorConfig" not in obj["ItemProcessor"]:
                    obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                else:
                    if not isinstance(obj["ItemProcessor"]["ProcessorConfig"], dict):
                        obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                    else:
                        obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Special handling for Map states - ensure they have proper ProcessorConfig
        if obj.get("Type") == "Map":
            if "ItemProcessor" not in obj:
                obj["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
            elif "ProcessorConfig" not in obj["ItemProcessor"]:
                obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
            else:
                obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Recursively process all values
        for value in obj.values():
            fix_processor_configs(value)
            
    elif isinstance(obj, list):
        for item in obj:
            fix_processor_configs(item)


# Store original methods
_original_map_to_state_json = sfn.Map.to_state_json
_original_custom_state_init = sfn.CustomState.__init__
_original_cfn_state_machine_init = CfnStateMachine.__init__


def patched_map_to_state_json(self):
    """Patch Map.to_state_json to fix ProcessorConfig during synthesis."""
    state_json = _original_map_to_state_json(self)
    
    # Ensure Map state has proper ItemProcessor with ProcessorConfig
    if state_json.get("Type") == "Map":
        if "ItemProcessor" not in state_json:
            state_json["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
        elif "ProcessorConfig" not in state_json["ItemProcessor"]:
            state_json["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
        else:
            state_json["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
    
    # Force ExecutionType in all ProcessorConfigs recursively
    def force_execution_type(obj):
        if isinstance(obj, dict):
            if "ProcessorConfig" in obj:
                if not isinstance(obj["ProcessorConfig"], dict):
                    obj["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                else:
                    obj["ProcessorConfig"]["ExecutionType"] = "STANDARD"
            
            # Ensure ItemProcessor has ProcessorConfig
            if "ItemProcessor" in obj:
                if not isinstance(obj["ItemProcessor"], dict):
                    obj["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
                elif "ProcessorConfig" not in obj["ItemProcessor"]:
                    obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                else:
                    obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
            
            for value in obj.values():
                force_execution_type(value)
        elif isinstance(obj, list):
            for item in obj:
                force_execution_type(item)
    
    force_execution_type(state_json)
    return state_json


def patched_custom_state_init(self, scope, construct_id, **kwargs):
    """Patch CustomState.__init__ to fix state_json during construction."""
    if "state_json" in kwargs and kwargs["state_json"]:
        fix_processor_configs(kwargs["state_json"])
    _original_custom_state_init(self, scope, construct_id, **kwargs)


def patched_cfn_state_machine_init(self, scope, construct_id, **kwargs):
    """Patch CfnStateMachine.__init__ to fix definition_string during synthesis."""
    if "definition_string" in kwargs and kwargs["definition_string"]:
        try:
            data = json.loads(kwargs["definition_string"])
            fix_processor_configs(data)
            kwargs["definition_string"] = json.dumps(data)
        except (json.JSONDecodeError, TypeError):
            pass
    _original_cfn_state_machine_init(self, scope, construct_id, **kwargs)


# Store original StateMachine init
_original_state_machine_init = sfn.StateMachine.__init__

def patched_state_machine_init(self, scope, construct_id, **kwargs):
    """Patch StateMachine.__init__ to fix definition during construction."""
    # Fix definition_body if present
    if "definition_body" in kwargs and kwargs["definition_body"]:
        definition_body = kwargs["definition_body"]
        if hasattr(definition_body, '_chainable'):
            # For chainable definitions, we'll let the bind method handle it
            pass
    
    _original_state_machine_init(self, scope, construct_id, **kwargs)

# Apply patches immediately when module is imported
sfn.Map.to_state_json = patched_map_to_state_json
sfn.CustomState.__init__ = patched_custom_state_init
CfnStateMachine.__init__ = patched_cfn_state_machine_init
sfn.StateMachine.__init__ = patched_state_machine_init


# Additional patch for DefinitionBody.bind method
if hasattr(sfn.DefinitionBody, 'bind'):
    _original_definition_body_bind = sfn.DefinitionBody.bind
    
    def patched_definition_body_bind(self, scope, state_machine):
        """Patch DefinitionBody.bind to fix definition during synthesis."""
        result = _original_definition_body_bind(self, scope, state_machine)
        if hasattr(result, 'definition_string') and result.definition_string:
            try:
                data = json.loads(result.definition_string)
                fix_processor_configs(data)
                result.definition_string = json.dumps(data)
            except (json.JSONDecodeError, TypeError):
                pass
        return result
    
    sfn.DefinitionBody.bind = patched_definition_body_bind

# Patch the CfnStateMachine's definition_string property setter
if hasattr(CfnStateMachine, 'definition_string'):
    _original_definition_string_setter = None
    if hasattr(CfnStateMachine.definition_string, 'fset'):
        _original_definition_string_setter = CfnStateMachine.definition_string.fset
        
        def patched_definition_string_setter(self, value):
            """Patch definition_string setter to fix ProcessorConfigs."""
            if value:
                try:
                    data = json.loads(value)
                    fix_processor_configs(data)
                    value = json.dumps(data)
                except (json.JSONDecodeError, TypeError):
                    pass
            _original_definition_string_setter(self, value)
        
        CfnStateMachine.definition_string = CfnStateMachine.definition_string.setter(patched_definition_string_setter)

# Patch CfnResource._render_properties to catch Step Functions definitions
_original_render_properties = CfnResource._render_properties

def patched_render_properties(self, properties):
    """Patch CfnResource._render_properties to fix Step Functions definitions."""
    result = _original_render_properties(self, properties)
    
    # Only patch Step Functions state machines
    if isinstance(self, CfnStateMachine) and result and "DefinitionString" in result:
        try:
            definition_string = result["DefinitionString"]
            
            # Handle both string and Fn::Join formats
            if isinstance(definition_string, str):
                data = json.loads(definition_string)
                fix_processor_configs(data)
                result["DefinitionString"] = json.dumps(data)
            elif isinstance(definition_string, dict) and "Fn::Join" in definition_string:
                # Fix Fn::Join format by processing the string parts
                parts = definition_string["Fn::Join"][1]
                for i, part in enumerate(parts):
                    if isinstance(part, str) and "ProcessorConfig" in part:
                        # Use regex to fix ProcessorConfig entries
                        import re
                        def fix_processor_config(match):
                            config = match.group(0)
                            if '"ExecutionType"' not in config:
                                config = config[:-1] + ',"ExecutionType":"STANDARD"}'
                            return config
                        
                        parts[i] = re.sub(r'"ProcessorConfig":\{[^}]*\}', fix_processor_config, part)
        except (json.JSONDecodeError, TypeError):
            pass
    
    return result

CfnResource._render_properties = patched_render_properties

# Import and apply post-synthesis fix
from aws_cdk import App

# Store original App.synth method
_original_app_synth = App.synth

def patched_app_synth(self, **kwargs):
    """Patch App.synth to apply post-synthesis fixes."""
    # Call original synth
    result = _original_app_synth(self, **kwargs)
    
    # Apply post-synthesis fixes to all stacks
    from .post_synthesis_execution_type_fix import fix_processor_configs_in_template
    import re
    
    for stack in result.stacks:
        template = stack.template
        fixes_applied = fix_processor_configs_in_template(template)
        
        # Also fix Fn::Join definitions with more aggressive pattern matching
        resources = template.get("Resources", {})
        for resource_name, resource in resources.items():
            if resource.get("Type") == "AWS::StepFunctions::StateMachine":
                definition_string = resource.get("Properties", {}).get("DefinitionString")
                
                if isinstance(definition_string, dict) and "Fn::Join" in definition_string:
                    parts = definition_string["Fn::Join"][1]
                    
                    # Process each string part with more comprehensive regex
                    for i, part in enumerate(parts):
                        if isinstance(part, str) and "ProcessorConfig" in part:
                            # Fix ProcessorConfig entries - handle various formats
                            def fix_processor_config(match):
                                config = match.group(0)
                                if '"ExecutionType"' not in config:
                                    # Handle both empty and non-empty ProcessorConfig
                                    if config.endswith('{}'):
                                        config = config[:-1] + '"ExecutionType":"STANDARD"}'
                                    else:
                                        config = config[:-1] + ',"ExecutionType":"STANDARD"}'
                                return config
                            
                            # Match ProcessorConfig with any content
                            fixed_part = re.sub(r'"ProcessorConfig":\{[^}]*\}', fix_processor_config, part)
                            
                            # Also handle cases where ProcessorConfig might be split across parts
                            if '"ProcessorConfig":' in part and not fixed_part.endswith('"STANDARD"}'):
                                # Look for incomplete ProcessorConfig patterns
                                if part.endswith('{}'):
                                    fixed_part = part.replace('{}', '{"ExecutionType":"STANDARD"}')
                                elif '"ProcessorConfig":{' in part and not '}' in part:
                                    # ProcessorConfig starts but doesn't end in this part
                                    fixed_part = part.replace('"ProcessorConfig":{', '"ProcessorConfig":{"ExecutionType":"STANDARD",')
                            
                            if fixed_part != part:
                                parts[i] = fixed_part
    
    return result

App.synth = patched_app_synth