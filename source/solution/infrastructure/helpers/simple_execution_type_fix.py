import json
from aws_cdk.aws_stepfunctions import CfnStateMachine

# Store original methods
original_init = CfnStateMachine.__init__
original_setter = CfnStateMachine.definition_string.fset if hasattr(CfnStateMachine.definition_string, 'fset') else None

def fix_configs(obj):
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
        for v in obj.values():
            fix_configs(v)
    elif isinstance(obj, list):
        for item in obj:
            fix_configs(item)

def fixed_init(self, scope, construct_id, **kwargs):
    # Fix definition_string in kwargs before calling original init
    if "definition_string" in kwargs and kwargs["definition_string"]:
        try:
            data = json.loads(kwargs["definition_string"])
            fix_configs(data)
            kwargs["definition_string"] = json.dumps(data)
        except:
            pass
    original_init(self, scope, construct_id, **kwargs)

def fixed_setter(self, value):
    if value:
        try:
            data = json.loads(value)
            fix_configs(data)
            value = json.dumps(data)
        except:
            pass
    if original_setter:
        original_setter(self, value)
    else:
        self._definition_string = value

# Apply patches
CfnStateMachine.__init__ = fixed_init
if original_setter:
    CfnStateMachine.definition_string = CfnStateMachine.definition_string.setter(fixed_setter)
else:
    # Fallback for different CDK versions
    setattr(CfnStateMachine, '_definition_string', None)
    CfnStateMachine.definition_string = property(
        lambda self: getattr(self, '_definition_string', None),
        fixed_setter
    )