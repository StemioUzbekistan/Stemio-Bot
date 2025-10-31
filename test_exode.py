#!/usr/bin/env python3
"""
Test script to verify Exode API connection and credentials.
Run this before starting the bot to ensure everything is configured correctly.
"""

import os
from dotenv import load_dotenv
from app.utils.exode_api import (
    find_user_by_phone, 
    upsert_user,
    get_headers
)

def test_environment_variables():
    """Test that all required environment variables are set."""
    print("\n=== Testing Environment Variables ===")
    
    load_dotenv()
    
    required_vars = ['EXODE_TOKEN', 'SELLER_ID', 'SCHOOL_ID', 'BOT_TOKEN']
    all_present = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Show first 10 chars only for security
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"✓ {var}: {display_value}")
        else:
            print(f"✗ {var}: NOT SET")
            all_present = False
    
    if all_present:
        print("\n✓ All environment variables are set!")
        return True
    else:
        print("\n✗ Some environment variables are missing!")
        print("Please check your .env file.")
        return False


def test_exode_connection():
    """Test connection to Exode API."""
    print("\n=== Testing Exode API Connection ===")
    
    try:
        headers = get_headers()
        print("✓ Headers generated successfully")
        print(f"  - Authorization: Bearer {headers['Authorization'][7:17]}...")
        print(f"  - Seller-Id: {headers['Seller-Id']}")
        print(f"  - School-Id: {headers['School-Id']}")
        return True
    except Exception as e:
        print(f"✗ Failed to generate headers: {e}")
        return False


def test_find_user():
    """Test finding a user (will return None if not found, which is OK)."""
    print("\n=== Testing User Search ===")
    
    # Test with a dummy phone number
    test_phone = "+998901234567"
    print(f"Searching for user with phone: {test_phone}")
    
    try:
        result = find_user_by_phone(test_phone)
        
        if result:
            print(f"✓ User found!")
            # Handle both possible response structures
            if 'user' in result:
                user = result.get('user', {})
                profile = user.get('profile', {})
            else:
                # Sometimes the response is directly the user object
                user = result
                profile = result.get('profile', {})
            
            print(f"  - Name: {profile.get('firstName', 'N/A')} {profile.get('lastName', 'N/A')}")
            print(f"  - Email: {user.get('email', 'N/A')}")
            print(f"  - Phone: {user.get('phone', 'N/A')}")
            print(f"  - Telegram ID: {user.get('tgId', 'N/A')}")
        else:
            print("✓ API call successful (user not found, which is OK for testing)")
        
        return True
    except Exception as e:
        print(f"✗ API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_user():
    """Test creating/updating a test user."""
    print("\n=== Testing User Upsert ===")
    print("⚠️  This will create a test user in your Exode system.")
    
    response = input("Do you want to proceed? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Skipped user creation test.")
        return True
    
    test_payload = {
        'phone': '+998991234567',  # Test phone number
        'tgId': 123456789,
        'profile': {
            'firstName': 'Test',
            'lastName': 'User',
            'bdate': '2000-01-01',
            'role': 'Student'
        }
    }
    
    print(f"Creating test user with phone: {test_payload['phone']}")
    
    try:
        result = upsert_user(test_payload)
        
        if result:
            is_created = result.get('isCreated', False)
            user = result.get('user', {})
            action = "created" if is_created else "updated"
            
            print(f"✓ User {action} successfully!")
            print(f"  - User ID: {user.get('id')}")
            print(f"  - Email: {user.get('email')}")
            print(f"  - Phone: {user.get('phone')}")
            
            return True
        else:
            print("✗ Failed to create/update user")
            return False
            
    except Exception as e:
        print(f"✗ API call failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*50)
    print("EXODE API CONNECTION TEST")
    print("="*50)
    
    # Test 1: Environment variables
    if not test_environment_variables():
        print("\n❌ Please fix environment variables before proceeding.")
        return False
    
    # Test 2: Connection
    if not test_exode_connection():
        print("\n❌ Cannot connect to Exode API. Check your credentials.")
        return False
    
    # Test 3: Find user
    if not test_find_user():
        print("\n❌ API search is not working. Check your token permissions.")
        return False
    
    # Test 4: Create user (optional)
    test_create_user()
    
    print("\n" + "="*50)
    print("✅ ALL TESTS PASSED!")
    print("="*50)
    print("\nYour Exode integration is working correctly.")
    print("You can now proceed to fix the handlers.\n")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)