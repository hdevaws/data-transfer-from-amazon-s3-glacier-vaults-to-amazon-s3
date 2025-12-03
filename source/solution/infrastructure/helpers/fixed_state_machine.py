"""
Fixed StateMachine that ensures ExecutionType is present in all ProcessorConfig entries.
"""

import json
from typing import Any, Dict, Optional
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk.aws_stepfunctions import CfnStateMachine
from constructs import Construct


def fix_processor_configs_in_definition(definition: Dict[str, Any]) -> None:
    """Recursively fix all ProcessorConfig entries in a state machine definition."""
    if isinstance(definition, dict):
        # Fix ProcessorConfig if found
        if "ProcessorConfig" in definition:
            if not isinstance(definition["ProcessorConfig"], dict):
                definition["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
            else:
                definition["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Fix ItemProcessor ProcessorConfig
        if "ItemProcessor" in definition:
            if not isinstance(definition["ItemProcessor"], dict):
                definition["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
            else:
                if "ProcessorConfig" not in definition["ItemProcessor"]:
                    definition["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                else:
                    definition["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Special handling for Map states
        if definition.get("Type") == "Map":
            if "ItemProcessor" not in definition:
                definition["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
            elif "ProcessorConfig" not in definition["ItemProcessor"]:
                definition["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
            else:
                definition["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Recursively process all values
        for value in definition.values():
            if isinstance(value, (dict, list)):
                fix_processor_configs_in_definition(value)
                
    elif isinstance(definition, list):
        for item in definition:
            if isinstance(item, (dict, list)):
                fix_processor_configs_in_definition(item)


class FixedStateMachine(sfn.StateMachine):
    """StateMachine that automatically fixes ExecutionType in ProcessorConfig entries."""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        definition_body: Optional[sfn.DefinitionBody] = None,
        **kwargs
    ) -> None:
        # Create the state machine normally first
        super().__init__(scope, construct_id, definition_body=definition_body, **kwargs)
        
        # Get the underlying CfnStateMachine
        cfn_state_machine = self.node.default_child
        if isinstance(cfn_state_machine, CfnStateMachine):
            # Override the synthesize method to fix the definition
            original_synthesize = cfn_state_machine._synthesize
            
            def fixed_synthesize(session):
                # Call original synthesize first
                original_synthesize(session)
                
                # Now fix the definition string if it exists
                if hasattr(cfn_state_machine, '_definition_string'):
                    definition_string = cfn_state_machine._definition_string
                    if isinstance(definition_string, str):
                        try:
                            definition = json.loads(definition_string)
                            fix_processor_configs_in_definition(definition)
                            cfn_state_machine._definition_string = json.dumps(definition)
                        except (json.JSONDecodeError, TypeError):
                            pass
                
                # Also check the raw properties
                if hasattr(cfn_state_machine, '_raw_overrides'):
                    overrides = cfn_state_machine._raw_overrides
                    if 'Properties' in overrides and 'DefinitionString' in overrides['Properties']:
                        definition_string = overrides['Properties']['DefinitionString']
                        if isinstance(definition_string, str):
                            try:
                                definition = json.loads(definition_string)
                                fix_processor_configs_in_definition(definition)
                                overrides['Properties']['DefinitionString'] = json.dumps(definition)
                            except (json.JSONDecodeError, TypeError):
                                pass
            
            cfn_state_machine._synthesize = fixed_synthesize
            
            # Also override the _render_properties method
            original_render_properties = cfn_state_machine._render_properties
            
            def fixed_render_properties(properties):
                result = original_render_properties(properties)
                
                if result and "DefinitionString" in result:
                    definition_string = result["DefinitionString"]
                    
                    if isinstance(definition_string, str):
                        try:
                            definition = json.loads(definition_string)
                            fix_processor_configs_in_definition(definition)
                            result["DefinitionString"] = json.dumps(definition)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    elif isinstance(definition_string, dict) and "Fn::Join" in definition_string:
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
                
                return result
            
            cfn_state_machine._render_properties = fixed_render_properties