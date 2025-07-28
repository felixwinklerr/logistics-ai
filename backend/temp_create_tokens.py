    def create_tokens(self, user: User) -> Tuple[str, str, int]:
        """
        Create access and refresh tokens for a user
        
        Args:
            user: User model instance
            
        Returns:
            Tuple of (access_token, refresh_token, expires_in_seconds)
        """
        try:
            # Use hardcoded values as fallback if settings fail
            try:
                access_token_minutes = settings.access_token_expire_minutes
            except AttributeError:
                access_token_minutes = 15  # Default fallback
                
            access_token_expires = timedelta(minutes=access_token_minutes)
            
            # Create tokens
            access_token = create_access_token(
                subject=str(user.id),
                expires_delta=access_token_expires
            )
            refresh_token = create_refresh_token(subject=str(user.id))
            
            expires_in = access_token_minutes * 60  # Convert to seconds
            
            return access_token, refresh_token, expires_in
            
        except Exception as e:
            logger.error(f"Token creation error: {str(e)}")
            raise
