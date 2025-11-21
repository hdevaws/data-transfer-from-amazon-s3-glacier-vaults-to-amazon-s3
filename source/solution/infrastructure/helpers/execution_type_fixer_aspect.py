"""
CDK Aspect to fix ExecutionType in all Step Functions ProcessorConfig entries.
"""

import json
import re
from typing import Any
from aws_cdk import IAspect, CfnResource
from aws_cdk.aws_stepfunctions import CfnStateMachine
from constructs import IConstruct


class ExecutionTypeFixer(IAspect):
    """Aspect that ensures all ProcessorConfig entries have ExecutionType field."""
    
    def visit(self, node: IConstruct) -> None:
        """Visit each node in the construct tree."""
        if isinstance(node, CfnStateMachine):
            self._fix_state_machine(node)
    
    def _fix_state_machine(self, state_machine: CfnStateMachine) -> None:
        """Fix the state machine definition to include ExecutionType in all ProcessorConfig entries."""
        # Override the definition string property
        state_machine.add_property_override(
            "DefinitionString",
            self._create_fixed_definition_token(state_machine)
        )
    
    def _create_fixed_definition_token(self, state_machine: CfnStateMachine) -> Any:
        """Create a token that will fix the definition at synthesis time."""
        # Get the original definition
        original_def = state_machine.definition_string
        
        # Create a custom token that will be resolved during synthesis
        from aws_cdk import CustomResource, Token
        from aws_cdk.custom_resources import Provider
        
        # We need to use a different approach - use add_override instead
        # This will be processed after the definition is generated
        return Token.as_any({
            "Fn::Sub": [
                self._fix_definition_string("${OriginalDef}"),
                {"OriginalDef": original_def}
            ]
        })
    
    def _fix_definition_string(self, definition_str: str) -> str:
        """Fix ProcessorConfig entries in a definition string."""
        # Use regex to find and fix ProcessorConfig entries
        def fix_processor_config(match):
            config = match.group(0)
            if '"ExecutionType"' not in config:
                # Add ExecutionType before the closing brace
                if config.endswith('{}'):
                    return config[:-1] + '"ExecutionType":"STANDARD"}'
                else:
                    return config[:-1] + ',"ExecutionType":"STANDARD"}'
            return config
        
        # Fix all ProcessorConfig entries
        fixed = re.sub(r'"ProcessorConfig":\{[^}]*\}', fix_processor_config, definition_str)
        return fixed
