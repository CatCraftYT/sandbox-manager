from typing import Any

def simple_merge(dict1 : dict[str, Any], dict2 : dict[str, Any]) -> dict[str, Any]:
    for (k,v) in dict2.items():
        d1_value = dict1.get(k)
        if d1_value == None:
            dict1[k] = v
        elif type(d1_value) != type(v):
            raise RuntimeError(f"Type mismatch in simple_merge:\n{d1_value}\n{v}")
        else:
            if isinstance(v, list):
                dict1[k] += v
            elif isinstance(v, dict):
                dict1[k] = simple_merge(dict1[k], dict2[k])
            else:
                raise RuntimeError(f"Unsupported type used in simple_merge: {type(v)}")
    return dict1
