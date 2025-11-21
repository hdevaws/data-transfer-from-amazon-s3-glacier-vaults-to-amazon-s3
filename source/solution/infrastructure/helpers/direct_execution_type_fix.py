"""
Direct ExecutionType fix that patches CDK at the lowest level to ensure
ExecutionType is always present in ProcessorConfig entries.
"""

import json
from typing import Any, Dict
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk.aws_stepfunctions import CfnStateMachine


# Store original methods
_original_cfn_state_machine_add_property_override = CfnStateMachine.add_property_override
_original_cfn_state_machine_add_override = CfnStateMachine.add_override


def fix_definition_string(definition_string: Any) -> Any:
    """Fix ExecutionType in definition string at the lowest level."""
    if isinstance(definition_string, str):
        try:
            data = json.loads(definition_string)
            fix_processor_configs_recursive(data)
            return json.dumps(data)
        except (json.JSONDecodeError, TypeError):
            pass
    elif isinstance(definition_string, dict):
        if "Fn::Join" in definition_string:
            # Handle CloudFormation Fn::Join
            parts = definition_string["Fn::Join"][1]
            for i, part in enumerate(parts):
                if isinstance(part, str) and "ProcessorConfig" in part:
                    # Fix ProcessorConfig entries in string parts
                    import re
                    def fix_processor_config(match):
                        config = match.group(0)
                        if '"ExecutionType"' not in config:
                            if config.endswith('{}'):
                                config = config[:-1] + '"ExecutionType":"STANDARD"}'
                            else:
                                config = config[:-1] + ',"ExecutionType":"STANDARD"}'
                        return config
                    
                    parts[i] = re.sub(r'"ProcessorConfig":\{[^}]*\}', fix_processor_config, part)
        else:
            # Handle regular dict
            fix_processor_configs_recursive(definition_string)
    
    return definition_string


def fix_processor_configs_recursive(obj: Any) -> None:
    """Recursively fix all ProcessorConfig entries."""
    if isinstance(obj, dict):
        # Fix ProcessorConfig if found
        if "ProcessorConfig" in obj:
            if not isinstance(obj["ProcessorConfig"], dict):
                obj["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
            else:
                obj["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Fix ItemProcessor ProcessorConfig
        if "ItemProcessor" in obj:
            if not isinstance(obj["ItemProcessor"], dict):
                obj["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
            else:
                if "ProcessorConfig" not in obj["ItemProcessor"]:
                    obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                else:
                    obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Special handling for Map states
        if obj.get("Type") == "Map":
            if "ItemProcessor" not in obj:
                obj["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
            elif "ProcessorConfig" not in obj["ItemProcessor"]:
                obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
            else:
                obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Recursively process all values
        for value in obj.values():
            fix_processor_configs_recursive(value)
            
    elif isinstance(obj, list):
        for item in obj:
            fix_processor_configs_recursive(item)


def patched_add_property_override(self, property_path: str, value: Any) -> None:
    """Patch add_property_override to fix DefinitionString."""
    if property_path == "DefinitionString":
        value = fix_definition_string(value)
    _original_cfn_state_machine_add_property_override(self, property_path, value)


def patched_add_override(self, path: str, value: Any) -> None:
    """Patch add_override to fix Properties.DefinitionString."""
    if path == "Properties.DefinitionString":
        value = fix_definition_string(value)
    _original_cfn_state_machine_add_override(self, path, value)


# Apply patches immediately
CfnStateMachine.add_property_override = patched_add_property_override
CfnStateMachine.add_override = patched_add_override


# Also patch the _render_properties method more aggressively
from aws_cdk import CfnResource

_original_cfn_resource_render_properties = CfnResource._render_properties

def patched_cfn_resource_render_properties(self, properties):
    """Patch _render_properties to fix Step Functions definitions."""
    result = _original_cfn_resource_render_properties(self, properties)
    
    if isinstance(self, CfnStateMachine) and result and "DefinitionString" in result:
        result["DefinitionString"] = fix_definition_string(result["DefinitionString"])
    
    return result

CfnResource._render_properties = patched_cfn_resource_render_properties


# Patch the property setter directly
if hasattr(CfnStateMachine, 'definition_string'):
    _original_definition_string_setter = None
    if hasattr(CfnStateMachine.definition_string, 'fset'):
        _original_definition_string_setter = CfnStateMachine.definition_string.fset
        
        def patched_definition_string_setter(self, value):
            """Patch definition_string setter."""
            if value:
                value = fix_definition_string(value)
            _original_definition_string_setter(self, value)
        
        CfnStateMachine.definition_string = CfnStateMachine.definition_string.setter(patched_definition_string_setter)


# Patch at the CloudFormation template level
from aws_cdk.core import CfnResource as CoreCfnResource

if hasattr(CoreCfnResource, '_render_properties'):
    _original_core_render_properties = CoreCfnResource._render_properties
    
    def patched_core_render_properties(self, properties):
        """Patch core _render_properties."""
        result = _original_core_render_properties(self, properties)
        
        if (hasattr(self, 'cfn_resource_type') and 
            self.cfn_resource_type == "AWS::StepFunctions::StateMachine" and 
            result and "DefinitionString" in result):
            result["DefinitionString"] = fix_definition_string(result["DefinitionString"])
        
        return result
    
    CoreCfnResource._render_properties = patched_core_render_properties


print("Direct ExecutionType fix applied - all Step Functions will have ExecutionType in ProcessorConfig")