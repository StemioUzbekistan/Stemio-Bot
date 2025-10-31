"""
Exode API Integration Module for Telegram Bot
Complete implementation with all necessary functions for user management
"""

import requests
import json
import logging
from typing import Dict, Optional, Any
from app.core.config import (
    EXODE_API_BASE_URL,
    EXODE_TOKEN,
    SELLER_ID,
    SCHOOL_ID
)

# Configure logging
logger = logging.getLogger(__name__)


def _get_headers() -> Dict[str, str]:
    """
    Get headers for Exode API requests.
    
    Returns:
        Dict with required headers for API authentication
    """
    return {
        'Authorization': f'Bearer {EXODE_TOKEN}',
        'Seller-Id': SELLER_ID,
        'School-Id': SCHOOL_ID,
        'Content-Type': 'application/json'
    }


def _format_phone(phone: str) -> str:
    """
    Format phone number to international format.
    
    Args:
        phone: Phone number in any format
        
    Returns:
        Formatted phone number with + prefix
    """
    if not phone:
        return phone
    
    # Remove all non-digit characters except +
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Add + if not present
    if not phone.startswith('+'):
        # Check if it's Uzbek number
        if phone.startswith('998'):
            phone = '+' + phone
        elif len(phone) == 9 and phone[0] in '789':
            # Uzbek mobile number without country code
            phone = '+998' + phone
        else:
            phone = '+' + phone
    
    return phone


def find_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    Find user in Exode by phone number.
    
    Args:
        phone: Phone number to search for
        
    Returns:
        User data dict or None if not found/error
    """
    try:
        # Format phone number
        phone = _format_phone(phone)
        
        if not phone:
            logger.error("Empty phone number provided")
            return None
        
        url = f'{EXODE_API_BASE_URL}/user/find'
        headers = _get_headers()
        params = {'login': phone}
        
        logger.info(f"Searching for user with phone: {phone}")
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                payload = result.get('payload')
                if payload:
                    logger.info(f"User found with phone: {phone}")
                    return payload
                else:
                    logger.info(f"No user found with phone: {phone}")
                    return None
            else:
                logger.error(f"API error: {result.get('message', 'Unknown error')}")
                return None
        elif response.status_code == 401:
            logger.error("Authentication failed - check EXODE_API_TOKEN")
            return None
        elif response.status_code == 403:
            logger.error("Access denied - check SELLER_ID and SCHOOL_ID")
            return None
        else:
            logger.error(f"Unexpected status code: {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        logger.error("Connection error - check internet connection")
        return None
    except requests.exceptions.Timeout:
        logger.error("Request timeout - Exode API might be slow")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in find_user_by_phone: {e}")
        return None


def find_user_by_telegram_id(tg_id: int) -> Optional[Dict[str, Any]]:
    """
    Find user in Exode by Telegram ID.
    
    Args:
        tg_id: Telegram user ID
        
    Returns:
        User data dict or None if not found/error
    """
    try:
        url = f'{EXODE_API_BASE_URL}/user/find'
        headers = _get_headers()
        params = {'tgId': tg_id}
        
        logger.info(f"Searching for user with Telegram ID: {tg_id}")
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                payload = result.get('payload')
                if payload:
                    logger.info(f"User found with Telegram ID: {tg_id}")
                    return payload
                else:
                    logger.info(f"No user found with Telegram ID: {tg_id}")
                    return None
            else:
                logger.error(f"API error: {result.get('message', 'Unknown error')}")
                return None
        else:
            logger.error(f"Unexpected status code: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error in find_user_by_telegram_id: {e}")
        return None


def create_user(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create new user in Exode.
    
    Args:
        payload: User data including profile
        
    Returns:
        Created user data or None if failed
    """
    try:
        url = f'{EXODE_API_BASE_URL}/user/create'
        headers = _get_headers()
        
        # Validate that we have at least one login method
        has_login = any([
            payload.get('email'),
            payload.get('phone'),
            payload.get('tgId')
        ])
        
        if not has_login:
            logger.error("User must have email, phone, or tgId")
            return None
        
        # Format phone if present
        if payload.get('phone'):
            payload['phone'] = _format_phone(payload['phone'])
        
        # Clean empty strings
        if payload.get('email') == '':
            payload['email'] = None
        if payload.get('phone') == '':
            payload['phone'] = None
        
        logger.info(f"Creating user with data: {json.dumps(payload, ensure_ascii=False)}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code in [200, 201]:
            result = response.json()
            if result.get('success'):
                logger.info("User created successfully")
                return result.get('payload')
            else:
                logger.error(f"API error: {result.get('message', 'Unknown error')}")
                return None
        elif response.status_code == 400:
            error_data = response.json()
            logger.error(f"Validation error: {error_data}")
            # Check if it's duplicate user error
            if 'EmailIsBusy' in str(error_data) or 'PhoneIsBusy' in str(error_data):
                logger.warning("User already exists, consider using upsert instead")
            return None
        else:
            logger.error(f"Failed to create user. Status: {response.status_code}, Response: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error in create_user: {e}")
        return None


def update_user(user_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update existing user in Exode.
    
    Args:
        user_id: Exode user ID
        payload: Data to update
        
    Returns:
        Updated user data or None if failed
    """
    try:
        url = f'{EXODE_API_BASE_URL}/user/{user_id}/update'
        headers = _get_headers()
        
        # Format phone if present
        if payload.get('phone'):
            payload['phone'] = _format_phone(payload['phone'])
        
        logger.info(f"Updating user {user_id} with data: {json.dumps(payload, ensure_ascii=False)}")
        
        response = requests.put(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                logger.info(f"User {user_id} updated successfully")
                return result.get('payload')
            else:
                logger.error(f"API error: {result.get('message', 'Unknown error')}")
                return None
        elif response.status_code == 404:
            logger.error(f"User {user_id} not found")
            return None
        else:
            logger.error(f"Failed to update user. Status: {response.status_code}, Response: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error in update_user: {e}")
        return None


def upsert_user(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create or update user in Exode (upsert operation).
    If user exists (found by email/phone/tgId), updates it.
    If user doesn't exist, creates new one.
    
    Args:
        payload: User data including profile
        
    Returns:
        User data with 'isCreated' flag or None if failed
    """
    try:
        url = f'{EXODE_API_BASE_URL}/user/upsert'
        headers = _get_headers()
        
        # Validate that we have at least one identifier
        has_identifier = any([
            payload.get('email'),
            payload.get('phone'),
            payload.get('tgId')
        ])
        
        if not has_identifier:
            logger.error("Upsert requires email, phone, or tgId")
            return None
        
        # Format phone if present
        if payload.get('phone'):
            payload['phone'] = _format_phone(payload['phone'])
        
        # Clean empty strings
        if payload.get('email') == '':
            payload['email'] = None
        if payload.get('phone') == '':
            payload['phone'] = None
        
        logger.info(f"Upserting user with data: {json.dumps(payload, ensure_ascii=False)}")
        
        response = requests.put(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code in [200, 201]:
            result = response.json()
            if result.get('success'):
                is_created = result['payload'].get('isCreated', False)
                action = "created" if is_created else "updated"
                logger.info(f"User successfully {action}")
                return result.get('payload')
            else:
                logger.error(f"API error: {result.get('message', 'Unknown error')}")
                return None
        elif response.status_code == 400:
            error_data = response.json()
            logger.error(f"Validation error: {error_data}")
            return None
        else:
            logger.error(f"Failed to upsert user. Status: {response.status_code}, Response: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error in upsert_user: {e}")
        return None


def create_session_token(user_id: int, force_create: bool = False) -> Optional[Dict[str, Any]]:
    """
    Create or get session token for user.
    
    Args:
        user_id: Exode user ID
        force_create: Force create new session even if one exists
        
    Returns:
        Session data with token or None if failed
    """
    try:
        url = f'{EXODE_API_BASE_URL}/user/session/auth-token'
        headers = _get_headers()
        data = {
            'userId': user_id,
            'forceCreate': force_create
        }
        
        logger.info(f"Creating session token for user {user_id}")
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                is_created = result['payload'].get('isCreated', False)
                action = "created" if is_created else "retrieved"
                logger.info(f"Session {action} successfully")
                return result.get('payload')
            else:
                logger.error(f"API error: {result.get('message', 'Unknown error')}")
                return None
        else:
            logger.error(f"Failed to create session. Status: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error in create_session_token: {e}")
        return None


def get_user_state(user_id: int, key: str) -> Optional[Any]:
    """
    Get user state by key.
    
    Args:
        user_id: Exode user ID
        key: State key
        
    Returns:
        State value or None if not found/error
    """
    try:
        url = f'{EXODE_API_BASE_URL}/user/{user_id}/state/get'
        headers = _get_headers()
        params = {'key': key}
        
        logger.info(f"Getting state for user {user_id}, key: {key}")
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result['payload'].get('value')
            else:
                logger.error(f"API error: {result.get('message', 'Unknown error')}")
                return None
        else:
            logger.error(f"Failed to get state. Status: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error in get_user_state: {e}")
        return None


def set_user_state(user_id: int, key: str, value: Any) -> bool:
    """
    Set user state by key.
    
    Args:
        user_id: Exode user ID
        key: State key
        value: Value to set
        
    Returns:
        True if successful, False otherwise
    """
    try:
        url = f'{EXODE_API_BASE_URL}/user/{user_id}/state/set'
        headers = _get_headers()
        params = {'key': key}
        data = {'value': value}
        
        logger.info(f"Setting state for user {user_id}, key: {key}, value: {value}")
        
        response = requests.put(url, params=params, json=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                logger.info("State set successfully")
                return result['payload'].get('set', False)
            else:
                logger.error(f"API error: {result.get('message', 'Unknown error')}")
                return False
        else:
            logger.error(f"Failed to set state. Status: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error in set_user_state: {e}")
        return False


# Helper function to generate auth link
def generate_auth_link(user_id: int, base_url: str = "https://my-school.com/education") -> Optional[str]:
    """
    Generate automatic authentication link for user.
    
    Args:
        user_id: Exode user ID
        base_url: Base URL of the application
        
    Returns:
        Auth link or None if failed
    """
    session = create_session_token(user_id)
    if session and session.get('session'):
        token = session['session'].get('token')
        if token:
            return f"{base_url}?___uat={token}"
    return None


# Test function for debugging
def test_connection() -> bool:
    """
    Test Exode API connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        headers = _get_headers()
        
        # Try to find a non-existent user to test auth
        url = f'{EXODE_API_BASE_URL}/user/find'
        params = {'login': 'test@nonexistent.com'}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            logger.info("Exode API connection successful")
            return True
        elif response.status_code == 401:
            logger.error("Authentication failed - check API token")
            return False
        elif response.status_code == 403:
            logger.error("Access denied - check seller/school IDs")
            return False
        else:
            logger.error(f"Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False