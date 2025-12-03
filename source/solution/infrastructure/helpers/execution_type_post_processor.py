"""
Post-processor to inject ExecutionType into Step Functions definitions after CDK synthesis.
"""

import json
import os
from pathlib import Path

def inject_execution_type():
    """Inject ExecutionType into all ProcessorConfig entries in generated templates."""
    cdk_out = Path("cdk.out")
    if not cdk_out.exists():
        return
    
    template_file = cdk_out / "data-transfer-from-amazon-s3-glacier-vaults-to-amazon-s3.template.json"
    if not template_file.exists():
        return
    
    with open(template_file, 'r') as f:
        template = json.load(f)
    
    # Find and fix all Step Functions state machines
    for resource_name, resource in template.get("Resources", {}).items():
        if resource.get("Type") == "AWS::StepFunctions::StateMachine":
            definition_string = resource.get("Properties", {}).get("DefinitionString")
            if definition_string:
                try:
                    if isinstance(definition_string, dict):
                        definition = definition_string
                    elif isinstance(definition_string, str):
                        if definition_string.startswith('"'):
                            definition_string = json.loads(definition_string)
                        definition = json.loads(definition_string)
                    else:
                        continue
                    
                    _fix_execution_type_recursive(definition)
                    resource["Properties"]["DefinitionString"] = definition
                    print(f"Fixed {resource_name}")
                except Exception as e:
                    print(f"Error processing {resource_name}: {e}")
                    pass
    
    # Write back the fixed template
    with open(template_file, 'w') as f:
        json.dump(template, f, indent=2)

def _fix_execution_type_recursive(obj):
    """Recursively fix ExecutionType in all ProcessorConfig entries."""
    if isinstance(obj, dict):
        if "ProcessorConfig" in obj:
            if not isinstance(obj["ProcessorConfig"], dict):
                obj["ProcessorConfig"] = {}
            obj["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        if "ItemProcessor" in obj:
            if not isinstance(obj["ItemProcessor"], dict):
                obj["ItemProcessor"] = {}
            if "ProcessorConfig" not in obj["ItemProcessor"]:
                obj["ItemProcessor"]["ProcessorConfig"] = {}
            obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        for value in obj.values():
            _fix_execution_type_recursive(value)
    elif isinstance(obj, list):
        for item in obj:
            _fix_execution_type_recursive(item)

if __name__ == "__main__":
    inject_execution_type()