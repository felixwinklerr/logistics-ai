"""
Email Authentication Service with OAuth2 support

Handles authentication for Gmail, Outlook, and generic IMAP servers
with automatic token refresh and caching.
"""

import json
import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta

import redis.asyncio as redis
import httpx
from loguru import logger

from app.core.config import get_settings
from app.services.email_service import EmailAccount, EmailProvider


class EmailClient:
    """Email client wrapper with authentication"""
    
    def __init__(self, account: EmailAccount, token_data: Optional[Dict] = None):
        self.account = account
        self.token_data = token_data
        self._imap_client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Connect to IMAP server with authentication"""
        try:
            if self.account.provider == EmailProvider.GMAIL:
                await self._connect_gmail()
            elif self.account.provider == EmailProvider.OUTLOOK:
                await self._connect_outlook()
            else:
                await self._connect_generic_imap()
                
            logger.debug(f"Connected to {self.account.email}")
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.account.email}: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from IMAP server"""
        if self._imap_client:
            try:
                # Close IMAP connection
                await self._close_imap_connection()
                self._imap_client = None
                logger.debug(f"Disconnected from {self.account.email}")
            except Exception as e:
                logger.warning(f"Error disconnecting from {self.account.email}: {e}")
    
    async def fetch_emails_since(self, since: datetime) -> List[Dict]:
        """Fetch emails since the given timestamp"""
        try:
            # This is a placeholder implementation
            # In production, this would use imapclient or similar
            logger.debug(f"Fetching emails for {self.account.email} since {since}")
            
            # Mock implementation for now
            return await self._mock_fetch_emails(since)
            
        except Exception as e:
            logger.error(f"Failed to fetch emails for {self.account.email}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on email connection"""
        try:
            # Simple connection test
            await self.connect()
            await self.disconnect()
            
            return {
                "is_healthy": True,
                "account": self.account.email,
                "provider": self.account.provider.value,
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "is_healthy": False,
                "account": self.account.email,
                "provider": self.account.provider.value,
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    async def _connect_gmail(self):
        """Connect to Gmail using OAuth2"""
        if not self.token_data:
            raise ValueError("Gmail requires OAuth2 token")
        
        # Import imapclient here to avoid import errors if not available
        try:
            import imapclient
            
            # Create IMAP client with OAuth2
            self._imap_client = imapclient.IMAPClient(
                host=self.account.imap_host,
                port=self.account.imap_port,
                ssl=True
            )
            
            # Authenticate with OAuth2
            await self._authenticate_oauth2_gmail()
            
        except ImportError:
            logger.warning("imapclient not available, using mock implementation")
            self._imap_client = "mock_gmail_client"
    
    async def _connect_outlook(self):
        """Connect to Outlook using OAuth2"""
        if not self.token_data:
            raise ValueError("Outlook requires OAuth2 token")
        
        try:
            import imapclient
            
            self._imap_client = imapclient.IMAPClient(
                host=self.account.imap_host,
                port=self.account.imap_port,
                ssl=True
            )
            
            # Authenticate with OAuth2
            await self._authenticate_oauth2_outlook()
            
        except ImportError:
            logger.warning("imapclient not available, using mock implementation")
            self._imap_client = "mock_outlook_client"
    
    async def _connect_generic_imap(self):
        """Connect to generic IMAP server"""
        try:
            import imapclient
            
            self._imap_client = imapclient.IMAPClient(
                host=self.account.imap_host,
                port=self.account.imap_port,
                ssl=True
            )
            
            # Use username/password authentication
            settings = get_settings()
            self._imap_client.login(
                settings.email_username,
                settings.email_password
            )
            
        except ImportError:
            logger.warning("imapclient not available, using mock implementation")
            self._imap_client = "mock_imap_client"
    
    async def _authenticate_oauth2_gmail(self):
        """Authenticate with Gmail using OAuth2"""
        access_token = self.token_data.get("access_token")
        if not access_token:
            raise ValueError("No access token available")
        
        # Gmail OAuth2 authentication
        auth_string = f"user={self.account.email}\x01auth=Bearer {access_token}\x01\x01"
        auth_bytes = auth_string.encode('utf-8')
        
        try:
            self._imap_client.oauth2_login(self.account.email, auth_bytes)
        except Exception as e:
            logger.error(f"Gmail OAuth2 authentication failed: {e}")
            raise
    
    async def _authenticate_oauth2_outlook(self):
        """Authenticate with Outlook using OAuth2"""
        access_token = self.token_data.get("access_token")
        if not access_token:
            raise ValueError("No access token available")
        
        # Outlook OAuth2 authentication
        auth_string = f"user={self.account.email}\x01auth=Bearer {access_token}\x01\x01"
        auth_bytes = auth_string.encode('utf-8')
        
        try:
            self._imap_client.oauth2_login(self.account.email, auth_bytes)
        except Exception as e:
            logger.error(f"Outlook OAuth2 authentication failed: {e}")
            raise
    
    async def _close_imap_connection(self):
        """Close IMAP connection properly"""
        if hasattr(self._imap_client, 'logout'):
            self._imap_client.logout()
    
    async def _mock_fetch_emails(self, since: datetime) -> List[Dict]:
        """Mock email fetching for development/testing"""
        from app.services.email_service import Email
        
        # Return empty list for now - in development this would be populated
        # with test data or actual IMAP implementation
        return []


class EmailAuthService:
    """OAuth2 authentication management for email providers"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.token_cache_ttl = 3300  # 55 minutes (tokens expire at 60)
        self.settings = get_settings()
    
    async def get_authenticated_client(self, account: EmailAccount) -> EmailClient:
        """Get authenticated email client with token refresh"""
        
        if account.provider in [EmailProvider.GMAIL, EmailProvider.OUTLOOK]:
            # OAuth2 providers - get cached or refresh token
            token_data = await self._get_or_refresh_token(account)
            return EmailClient(account, token_data)
        else:
            # Generic IMAP - no OAuth2 needed
            return EmailClient(account)
    
    async def _get_or_refresh_token(self, account: EmailAccount) -> Dict[str, Any]:
        """Get cached token or refresh if expired"""
        
        # Check for cached token
        cache_key = f"email_token:{account.id}"
        cached_token = await self.redis.get(cache_key)
        
        if cached_token:
            token_data = json.loads(cached_token.decode())
            
            # Check if token is still valid (with 5-minute buffer)
            expires_at = datetime.fromisoformat(token_data.get("expires_at", ""))
            if expires_at > datetime.now() + timedelta(minutes=5):
                logger.debug(f"Using cached token for {account.email}")
                return token_data
        
        # Token expired or not cached - refresh
        logger.info(f"Refreshing OAuth2 token for {account.email}")
        new_token = await self._refresh_oauth_token(account)
        
        # Cache new token
        await self.redis.setex(
            cache_key, 
            self.token_cache_ttl, 
            json.dumps(new_token)
        )
        
        return new_token
    
    async def _refresh_oauth_token(self, account: EmailAccount) -> Dict[str, Any]:
        """Refresh OAuth2 token for email account"""
        
        if account.provider == EmailProvider.GMAIL:
            return await self._refresh_gmail_token(account)
        elif account.provider == EmailProvider.OUTLOOK:
            return await self._refresh_outlook_token(account)
        else:
            raise ValueError(f"Unsupported OAuth2 provider: {account.provider}")
    
    async def _refresh_gmail_token(self, account: EmailAccount) -> Dict[str, Any]:
        """Refresh Gmail OAuth2 token"""
        
        oauth_config = account.oauth_config
        refresh_token = oauth_config.get("refresh_token")
        
        if not refresh_token:
            raise ValueError("No refresh token available for Gmail")
        
        # Gmail OAuth2 token refresh
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "client_id": oauth_config["client_id"],
            "client_secret": oauth_config["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                
                token_response = response.json()
                
                # Calculate expiration time
                expires_in = token_response.get("expires_in", 3600)
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                token_data = {
                    "access_token": token_response["access_token"],
                    "token_type": token_response.get("token_type", "Bearer"),
                    "expires_at": expires_at.isoformat(),
                    "expires_in": expires_in
                }
                
                logger.info(f"Successfully refreshed Gmail token for {account.email}")
                return token_data
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Gmail token refresh failed: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Gmail token refresh error: {e}")
                raise
    
    async def _refresh_outlook_token(self, account: EmailAccount) -> Dict[str, Any]:
        """Refresh Outlook OAuth2 token"""
        
        oauth_config = account.oauth_config
        refresh_token = oauth_config.get("refresh_token")
        
        if not refresh_token:
            raise ValueError("No refresh token available for Outlook")
        
        # Microsoft OAuth2 token refresh
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        
        data = {
            "client_id": oauth_config["client_id"],
            "client_secret": oauth_config["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": "https://outlook.office.com/IMAP.AccessAsUser.All"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                
                token_response = response.json()
                
                # Calculate expiration time
                expires_in = token_response.get("expires_in", 3600)
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                token_data = {
                    "access_token": token_response["access_token"],
                    "token_type": token_response.get("token_type", "Bearer"),
                    "expires_at": expires_at.isoformat(),
                    "expires_in": expires_in
                }
                
                logger.info(f"Successfully refreshed Outlook token for {account.email}")
                return token_data
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Outlook token refresh failed: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Outlook token refresh error: {e}")
                raise
    
    async def revoke_token(self, account: EmailAccount):
        """Revoke cached token for an account"""
        cache_key = f"email_token:{account.id}"
        await self.redis.delete(cache_key)
        logger.info(f"Revoked cached token for {account.email}")
    
    async def get_token_status(self, account: EmailAccount) -> Dict[str, Any]:
        """Get token status for an account"""
        cache_key = f"email_token:{account.id}"
        cached_token = await self.redis.get(cache_key)
        
        if not cached_token:
            return {
                "has_token": False,
                "account": account.email
            }
        
        token_data = json.loads(cached_token.decode())
        expires_at = datetime.fromisoformat(token_data.get("expires_at", ""))
        
        return {
            "has_token": True,
            "account": account.email,
            "expires_at": expires_at.isoformat(),
            "is_expired": expires_at <= datetime.now(),
            "token_type": token_data.get("token_type", "Bearer")
        } 