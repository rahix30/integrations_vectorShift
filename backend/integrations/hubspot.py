# hubspot.py

import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import requests
from integrations.integration_item import IntegrationItem

from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# Replace these with your HubSpot app credentials
CLIENT_ID = '6b5fd195-ea8b-44dc-94a5-84024fdf3569'
CLIENT_SECRET = '72daedd1-6798-47bf-9ceb-39f39ca0c95c'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
SCOPES = 'crm.objects.contacts.read crm.schemas.contacts.read crm.objects.contacts.write'

authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}'

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    return f'{authorization_url}&state={encoded_state}'

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))
    
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(encoded_state)

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                    'code': code
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}')
        )

    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)
    
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

def create_integration_item_from_contact(contact_data: dict) -> IntegrationItem:
    """Creates an integration item from HubSpot contact data"""
    properties = contact_data.get('properties', {})
    
    return IntegrationItem(
        id=contact_data.get('id'),
        type='contact',
        name=f"{properties.get('firstname', '')} {properties.get('lastname', '')}".strip() or 'Unnamed Contact',
        creation_time=properties.get('createdate'),
        last_modified_time=properties.get('lastmodifieddate'),
        parent_id=None,
        url=f"https://app.hubspot.com/contacts/{contact_data.get('id')}"  # Adding HubSpot contact URL
    )

async def get_items_hubspot(credentials) -> list[IntegrationItem]:
    """Fetches contacts from HubSpot and returns them as IntegrationItems"""
    try:
        credentials = json.loads(credentials)
        access_token = credentials.get('access_token')
        
        if not access_token:
            raise HTTPException(status_code=400, detail='Invalid credentials')

        response = requests.get(
            'https://api.hubapi.com/crm/v3/objects/contacts',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            params={
                'limit': 100,
                'properties': ['firstname', 'lastname', 'email', 'company', 'phone', 'createdate', 'lastmodifieddate']
            }
        )

        if response.status_code != 200:
            error_detail = response.json().get('message', 'Failed to fetch HubSpot contacts')
            print(f"HubSpot API Error: {error_detail}")  # Debug log
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        results = response.json().get('results', [])
        integration_items = [create_integration_item_from_contact(contact) for contact in results]
        
        print(f"Successfully fetched {len(integration_items)} contacts from HubSpot")  # Debug log
        return integration_items
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Invalid credentials format')
    except Exception as e:
        print(f"Error in get_items_hubspot: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))