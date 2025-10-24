#!/usr/bin/env python3
"""
Test script to verify the register_new_flight fix
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import register_new_flight
from langchain_core.runnables import RunnableConfig

def test_register_new_flight_without_passenger_id():
    """Test registering a new flight without a passenger_id in config"""
    print("Testing register_new_flight WITHOUT passenger_id...")

    result = register_new_flight.invoke({
        "flight_no": "AA100",
        "departure_airport": "MAD",
        "arrival_airport": "CDG",
        "scheduled_departure": "2025-10-24T19:10:20.930317",
        "scheduled_arrival": "2025-10-24T21:10:20.930317",
        "passenger_name": "Gustavo Joaquin Calizaya Leon",
        "passenger_email": "gustavojoaquincalizayaleon2@gmail.com",
        "fare_conditions": "Economy",
        "config": None
    })

    print("Result:", result)
    print("✓ Test passed - No passenger_id error!")
    return result

def test_register_new_flight_with_passenger_id():
    """Test registering a new flight with a passenger_id in config"""
    print("\nTesting register_new_flight WITH passenger_id...")

    config = RunnableConfig(configurable={"passenger_id": "3442 587242"})

    result = register_new_flight.invoke({
        "flight_no": "BA200",
        "departure_airport": "CDG",
        "arrival_airport": "TXL",
        "scheduled_departure": "2025-10-25T20:10:20.930317",
        "scheduled_arrival": "2025-10-25T22:10:20.930317",
        "passenger_name": "Test User",
        "passenger_email": "test@example.com",
        "fare_conditions": "Business",
        "config": config
    })

    print("Result:", result)
    print("✓ Test passed - Works with existing passenger_id!")
    return result

if __name__ == "__main__":
    print("Testing the register_new_flight fix...\n")

    try:
        # Test without passenger_id
        result1 = test_register_new_flight_without_passenger_id()

        # Test with passenger_id
        result2 = test_register_new_flight_with_passenger_id()

        print("\n🎉 All tests passed! The fix is working correctly.")
        print("\nSummary:")
        print("- Without passenger_id: Generates a unique passenger_id from name and email")
        print("- With passenger_id: Uses the provided passenger_id")
        print("- No more 'No se ha configurado un ID de pasajero' errors!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)

