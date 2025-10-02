#!/usr/bin/env python
"""
Manual verification script to test port assignment logic.
This script simulates the port assignment flow to verify production readiness.
"""

import json
import sys
import os

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)


def verify_config_ports():
    """Verify that all config files use list format for ports."""
    print("=" * 60)
    print("VERIFICATION: Config Files Port Format")
    print("=" * 60)
    
    config_path = os.path.join(script_dir, "template", "user-config.json")
    
    with open(config_path) as f:
        config = json.load(f)
    
    apps_with_ports = []
    for app_name, app_config in config["apps"].items():
        if "ports" in app_config:
            port_value = app_config["ports"]
            is_list = isinstance(port_value, list)
            apps_with_ports.append({
                "name": app_name,
                "ports": port_value,
                "is_list": is_list,
                "status": "✓" if is_list else "✗"
            })
    
    # Check dashboard
    if "m4b_dashboard" in config and "ports" in config["m4b_dashboard"]:
        port_value = config["m4b_dashboard"]["ports"]
        is_list = isinstance(port_value, list)
        apps_with_ports.append({
            "name": "m4b_dashboard",
            "ports": port_value,
            "is_list": is_list,
            "status": "✓" if is_list else "✗"
        })
    
    print(f"\nFound {len(apps_with_ports)} items with ports configuration:\n")
    for item in apps_with_ports:
        print(f"  {item['status']} {item['name']}: {item['ports']}")
        if not item['is_list']:
            print(f"     ^ ERROR: Not a list!")
    
    all_lists = all(item['is_list'] for item in apps_with_ports)
    print(f"\n{'✓ PASS' if all_lists else '✗ FAIL'}: All ports are lists")
    return all_lists


def verify_function_signatures():
    """Verify that key functions have correct type hints."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Function Type Hints")
    print("=" * 60)
    
    try:
        from utils.fn_setupApps import assign_app_ports
        from utils.generator import substitute_port_placeholders
        
        # Check assign_app_ports return type
        import inspect
        
        sig1 = inspect.signature(assign_app_ports)
        return_annotation1 = sig1.return_annotation
        print(f"\nassign_app_ports return type: {return_annotation1}")
        correct1 = "list[int]" in str(return_annotation1)
        print(f"{'✓' if correct1 else '✗'} Expected: list[int]")
        
        # Check substitute_port_placeholders parameter type
        sig2 = inspect.signature(substitute_port_placeholders)
        params2 = sig2.parameters
        actual_ports_type = params2['actual_ports'].annotation
        print(f"\nsubstitute_port_placeholders actual_ports type: "
              f"{actual_ports_type}")
        correct2 = "list[int]" in str(actual_ports_type)
        print(f"{'✓' if correct2 else '✗'} Expected: list[int]")
        
        all_correct = correct1 and correct2
        print(f"\n{'✓ PASS' if all_correct else '✗ FAIL'}: Type hints correct")
        return all_correct
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False


def verify_logic_flow():
    """Verify the actual logic flow with mock data."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Logic Flow")
    print("=" * 60)
    
    try:
        # Test 1: Single port assignment
        print("\nTest 1: Single port app (dawn)")
        from unittest.mock import patch
        from utils.fn_setupApps import assign_app_ports
        
        app = {
            "compose_config": {
                "ports": ["${DAWN_PORT}:5000"]
            }
        }
        config = {"ports": [5000]}
        
        with patch("utils.fn_setupApps.find_next_available_port") as mock:
            mock.return_value = 5000
            result = assign_app_ports("dawn", app, config)
            
        print(f"  Input config: {config}")
        print(f"  Result: {result}")
        print(f"  Type: {type(result)}")
        test1_pass = isinstance(result, list) and len(result) == 1
        print(f"  {'✓ PASS' if test1_pass else '✗ FAIL'}: Returns list")
        
        # Test 2: Multiple port assignment
        print("\nTest 2: Multiple port app (wipter)")
        app2 = {
            "compose_config": {
                "ports": [
                    "${WIPTER_PORT_1}:5900",
                    "${WIPTER_PORT_2}:6080"
                ]
            }
        }
        config2 = {"ports": [5900, 6080]}
        
        with patch("utils.fn_setupApps.find_next_available_port") as mock:
            mock.side_effect = lambda x: x
            result2 = assign_app_ports("wipter", app2, config2)
            
        print(f"  Input config: {config2}")
        print(f"  Result: {result2}")
        print(f"  Type: {type(result2)}")
        test2_pass = isinstance(result2, list) and len(result2) == 2
        print(f"  {'✓ PASS' if test2_pass else '✗ FAIL'}: Returns list")
        
        # Test 3: Port substitution
        print("\nTest 3: Port placeholder substitution")
        from utils.generator import substitute_port_placeholders
        
        placeholders = ["${DAWN_PORT}:5000"]
        actual_ports = [8080]
        
        result3 = substitute_port_placeholders(placeholders, actual_ports)
        print(f"  Placeholders: {placeholders}")
        print(f"  Actual ports: {actual_ports}")
        print(f"  Result: {result3}")
        test3_pass = result3 == ["8080:5000"]
        print(f"  {'✓ PASS' if test3_pass else '✗ FAIL'}: Correct substitution")
        
        all_pass = test1_pass and test2_pass and test3_pass
        print(f"\n{'✓ PASS' if all_pass else '✗ FAIL'}: All logic tests passed")
        return all_pass
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification checks."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "PORT LOGIC PRODUCTION VERIFICATION" + " " * 12 + "║")
    print("╚" + "=" * 58 + "╝")
    
    results = []
    
    # Run verification checks
    results.append(("Config Files", verify_config_ports()))
    results.append(("Type Hints", verify_function_signatures()))
    results.append(("Logic Flow", verify_logic_flow()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL CHECKS PASSED - CODE IS PRODUCTION READY")
    else:
        print("✗ SOME CHECKS FAILED - REVIEW REQUIRED")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
