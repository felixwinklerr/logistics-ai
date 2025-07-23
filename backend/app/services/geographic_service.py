"""
Geographic Service Layer - PostGIS Integration for Logistics Operations

Implements the geographic service architecture designed in Sprint 3 creative phase.
Provides coordinate validation, distance calculations, geocoding, and spatial queries
with Redis caching for optimal performance.

Romanian-specific optimizations included for local postal system integration.
"""

import logging
from typing import Optional, Tuple, List, Dict, Any
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime, timedelta

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_Transform, ST_AsText
import httpx
from pydantic import BaseModel, Field, validator

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CoordinateSystem(str, Enum):
    """Supported coordinate systems for Romanian operations"""
    WGS84 = "EPSG:4326"  # Storage standard
    ROMANIAN_STEREO = "EPSG:3844"  # Romanian national grid
    WEB_MERCATOR = "EPSG:3857"  # Web mapping


@dataclass
class Coordinates:
    """Geographic coordinates with validation"""
    latitude: float
    longitude: float
    system: CoordinateSystem = CoordinateSystem.WGS84
    
    def __post_init__(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}")


@dataclass
class DistanceResult:
    """Distance calculation result with metadata"""
    distance_km: Decimal
    calculation_time: float
    coordinate_system: CoordinateSystem
    cached: bool = False


class GeocodingResult(BaseModel):
    """Geocoding service response"""
    coordinates: Optional[Coordinates] = None
    formatted_address: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: str = "RO"
    components: Dict[str, str] = Field(default_factory=dict)


class SpatialQuery(BaseModel):
    """Spatial query parameters"""
    center: Coordinates
    radius_km: float = Field(..., gt=0, le=1000)
    limit: int = Field(default=50, ge=1, le=1000)
    filters: Dict[str, Any] = Field(default_factory=dict)


class CoordinateService:
    """Coordinate system validation and transformation service"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        
    def validate_coordinates(self, coordinates: Coordinates) -> bool:
        """Validate coordinate values and system compatibility"""
        try:
            # Basic range validation in __post_init__
            if coordinates.system == CoordinateSystem.ROMANIAN_STEREO:
                # Romanian Stereo 70 specific validation
                if not (200000 <= coordinates.longitude <= 900000):
                    return False
                if not (200000 <= coordinates.latitude <= 700000):
                    return False
            return True
        except ValueError:
            return False
    
    async def transform_coordinates(
        self, 
        coordinates: Coordinates, 
        target_system: CoordinateSystem
    ) -> Coordinates:
        """Transform coordinates between systems using PostGIS"""
        if coordinates.system == target_system:
            return coordinates
            
        query = text("""
            SELECT ST_X(ST_Transform(ST_GeomFromText(:wkt, :source_srid), :target_srid)) as x,
                   ST_Y(ST_Transform(ST_GeomFromText(:wkt, :source_srid), :target_srid)) as y
        """)
        
        wkt = f"POINT({coordinates.longitude} {coordinates.latitude})"
        source_srid = int(coordinates.system.value.split(':')[1])
        target_srid = int(target_system.value.split(':')[1])
        
        result = await self.db_session.execute(
            query, 
            {
                "wkt": wkt, 
                "source_srid": source_srid, 
                "target_srid": target_srid
            }
        )
        row = result.fetchone()
        
        return Coordinates(
            latitude=row.y,
            longitude=row.x,
            system=target_system
        )


class DistanceService:
    """Distance calculation and route optimization service"""
    
    def __init__(self, db_session: AsyncSession, cache_service: 'CacheService'):
        self.db_session = db_session
        self.cache_service = cache_service
        
    async def calculate_distance(
        self, 
        coord1: Coordinates, 
        coord2: Coordinates,
        use_cache: bool = True
    ) -> DistanceResult:
        """Calculate distance between two points using PostGIS"""
        start_time = datetime.now()
        
        # Check cache first
        cache_key = self._generate_distance_cache_key(coord1, coord2)
        if use_cache:
            cached_result = await self.cache_service.get_distance(cache_key)
            if cached_result:
                return DistanceResult(
                    distance_km=cached_result,
                    calculation_time=0.0,
                    coordinate_system=CoordinateSystem.WGS84,
                    cached=True
                )
        
        # Calculate using PostGIS with Romanian projection for accuracy
        query = text("""
            SELECT ST_Distance(
                ST_Transform(ST_GeomFromText(:point1, 4326), 3844),
                ST_Transform(ST_GeomFromText(:point2, 4326), 3844)
            ) / 1000.0 as distance_km
        """)
        
        point1_wkt = f"POINT({coord1.longitude} {coord1.latitude})"
        point2_wkt = f"POINT({coord2.longitude} {coord2.latitude})"
        
        result = await self.db_session.execute(
            query, 
            {"point1": point1_wkt, "point2": point2_wkt}
        )
        row = result.fetchone()
        
        distance_km = Decimal(str(row.distance_km)).quantize(Decimal('0.01'))
        calculation_time = (datetime.now() - start_time).total_seconds()
        
        # Cache the result
        if use_cache:
            await self.cache_service.set_distance(cache_key, distance_km)
        
        return DistanceResult(
            distance_km=distance_km,
            calculation_time=calculation_time,
            coordinate_system=CoordinateSystem.ROMANIAN_STEREO,
            cached=False
        )
    
    def _generate_distance_cache_key(self, coord1: Coordinates, coord2: Coordinates) -> str:
        """Generate cache key for distance calculation"""
        # Sort coordinates to ensure consistent cache keys
        coords = sorted([
            f"{coord1.latitude:.6f},{coord1.longitude:.6f}",
            f"{coord2.latitude:.6f},{coord2.longitude:.6f}"
        ])
        return f"distance:{coords[0]}:{coords[1]}"


class GeocodingService:
    """Address to coordinate conversion service with Romanian focus"""
    
    def __init__(self, cache_service: 'CacheService'):
        self.cache_service = cache_service
        self.client = httpx.AsyncClient(timeout=10.0)
        
    async def geocode_address(
        self, 
        address: str, 
        country: str = "RO",
        use_cache: bool = True
    ) -> GeocodingResult:
        """Convert address to coordinates with Romanian postal system support"""
        
        # Check cache first
        cache_key = self._generate_geocoding_cache_key(address, country)
        if use_cache:
            cached_result = await self.cache_service.get_geocoding(cache_key)
            if cached_result:
                return cached_result
        
        # For MVP, implement basic geocoding simulation
        # In production, integrate with Google Maps, HERE, or Romanian postal service
        result = await self._simulate_romanian_geocoding(address, country)
        
        # Cache the result
        if use_cache and result.coordinates:
            await self.cache_service.set_geocoding(cache_key, result)
        
        return result
    
    async def reverse_geocode(
        self, 
        coordinates: Coordinates,
        use_cache: bool = True
    ) -> GeocodingResult:
        """Convert coordinates to address"""
        cache_key = f"reverse:{coordinates.latitude:.6f},{coordinates.longitude:.6f}"
        
        if use_cache:
            cached_result = await self.cache_service.get_geocoding(cache_key)
            if cached_result:
                return cached_result
                
        # Simulate reverse geocoding for MVP
        result = await self._simulate_reverse_geocoding(coordinates)
        
        if use_cache:
            await self.cache_service.set_geocoding(cache_key, result)
            
        return result
    
    async def _simulate_romanian_geocoding(self, address: str, country: str) -> GeocodingResult:
        """Simulate geocoding for Romanian addresses - MVP implementation"""
        
        # Romanian major cities coordinates for simulation
        romanian_cities = {
            "bucuresti": Coordinates(44.4268, 26.1025),
            "cluj-napoca": Coordinates(46.7712, 23.6236),
            "timisoara": Coordinates(45.7489, 21.2087),
            "iasi": Coordinates(47.1585, 27.6014),
            "constanta": Coordinates(44.1598, 28.6348),
            "craiova": Coordinates(44.3302, 23.7949),
            "brasov": Coordinates(45.6427, 25.5887),
            "galati": Coordinates(45.4353, 28.0080)
        }
        
        address_lower = address.lower()
        coordinates = None
        confidence = 0.5  # Default confidence
        
        # Simple city matching
        for city, coords in romanian_cities.items():
            if city in address_lower:
                coordinates = coords
                confidence = 0.9
                break
        
        # Default to Bucharest if no match found
        if not coordinates:
            coordinates = romanian_cities["bucuresti"]
            confidence = 0.3
            
        return GeocodingResult(
            coordinates=coordinates,
            formatted_address=address,
            confidence=confidence,
            country=country,
            components={"simulation": "true"}
        )
    
    async def _simulate_reverse_geocoding(self, coordinates: Coordinates) -> GeocodingResult:
        """Simulate reverse geocoding for coordinates"""
        return GeocodingResult(
            coordinates=coordinates,
            formatted_address=f"Address near {coordinates.latitude:.4f}, {coordinates.longitude:.4f}",
            confidence=0.5,
            country="RO",
            components={"reverse_simulation": "true"}
        )
    
    def _generate_geocoding_cache_key(self, address: str, country: str) -> str:
        """Generate cache key for geocoding"""
        return f"geocode:{country}:{address.lower().strip()}"


class SpatialQueryService:
    """PostGIS spatial operations service"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        
    async def find_nearby_points(
        self, 
        query: SpatialQuery,
        table_name: str = "orders"
    ) -> List[Dict[str, Any]]:
        """Find points within radius using PostGIS spatial index"""
        
        # Use GIST spatial index for performance
        sql_query = text(f"""
            SELECT 
                order_id,
                pickup_address,
                delivery_address,
                ST_AsText(pickup_coordinates) as pickup_coords,
                ST_AsText(delivery_coordinates) as delivery_coords,
                ST_Distance(
                    pickup_coordinates::geography,
                    ST_GeomFromText(:center_point, 4326)::geography
                ) / 1000.0 as distance_km
            FROM {table_name}
            WHERE ST_DWithin(
                pickup_coordinates::geography,
                ST_GeomFromText(:center_point, 4326)::geography,
                :radius_meters
            )
            ORDER BY distance_km
            LIMIT :limit
        """)
        
        center_wkt = f"POINT({query.center.longitude} {query.center.latitude})"
        radius_meters = query.radius_km * 1000
        
        result = await self.db_session.execute(
            sql_query,
            {
                "center_point": center_wkt,
                "radius_meters": radius_meters,
                "limit": query.limit
            }
        )
        
        return [dict(row._mapping) for row in result.fetchall()]


class CacheService:
    """Redis caching service for geographic data"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.geocoding_ttl = 24 * 3600  # 24 hours
        self.distance_ttl = 3600  # 1 hour
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Geographic cache service initialized")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    async def get_distance(self, cache_key: str) -> Optional[Decimal]:
        """Get cached distance calculation"""
        if not self.redis_client:
            return None
            
        try:
            value = await self.redis_client.get(cache_key)
            if value:
                return Decimal(value)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None
    
    async def set_distance(self, cache_key: str, distance: Decimal):
        """Cache distance calculation"""
        if not self.redis_client:
            return
            
        try:
            await self.redis_client.setex(
                cache_key, 
                self.distance_ttl, 
                str(distance)
            )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    async def get_geocoding(self, cache_key: str) -> Optional[GeocodingResult]:
        """Get cached geocoding result"""
        if not self.redis_client:
            return None
            
        try:
            value = await self.redis_client.get(cache_key)
            if value:
                import json
                data = json.loads(value)
                if data.get('coordinates'):
                    coords_data = data['coordinates']
                    data['coordinates'] = Coordinates(
                        latitude=coords_data['latitude'],
                        longitude=coords_data['longitude'],
                        system=CoordinateSystem(coords_data.get('system', 'EPSG:4326'))
                    )
                return GeocodingResult(**data)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None
    
    async def set_geocoding(self, cache_key: str, result: GeocodingResult):
        """Cache geocoding result"""
        if not self.redis_client:
            return
            
        try:
            import json
            data = result.dict()
            if data.get('coordinates'):
                coords = data['coordinates']
                data['coordinates'] = {
                    'latitude': coords.latitude,
                    'longitude': coords.longitude,
                    'system': coords.system.value
                }
            
            await self.redis_client.setex(
                cache_key,
                self.geocoding_ttl,
                json.dumps(data)
            )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")


class GeographicService:
    """
    Main Geographic Service Layer Interface
    
    Provides unified access to all geographic operations including:
    - Coordinate validation and transformation
    - Distance calculations with caching
    - Address geocoding (Romanian-optimized)
    - Spatial queries using PostGIS
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.cache_service = CacheService()
        
        # Initialize component services
        self.coordinate_service = CoordinateService(db_session)
        self.distance_service = DistanceService(db_session, self.cache_service)
        self.geocoding_service = GeocodingService(self.cache_service)
        self.spatial_service = SpatialQueryService(db_session)
        
    async def initialize(self):
        """Initialize the geographic service and dependencies"""
        await self.cache_service.initialize()
        logger.info("GeographicService initialized successfully")
    
    # Coordinate Operations
    async def validate_coordinates(self, coordinates: Coordinates) -> bool:
        """Validate geographic coordinates"""
        return self.coordinate_service.validate_coordinates(coordinates)
    
    async def transform_coordinates(
        self, 
        coordinates: Coordinates, 
        target_system: CoordinateSystem
    ) -> Coordinates:
        """Transform coordinates between systems"""
        return await self.coordinate_service.transform_coordinates(coordinates, target_system)
    
    # Distance Operations
    async def calculate_distance(
        self, 
        coord1: Coordinates, 
        coord2: Coordinates
    ) -> DistanceResult:
        """Calculate distance between coordinates"""
        return await self.distance_service.calculate_distance(coord1, coord2)
    
    # Geocoding Operations
    async def geocode_address(self, address: str, country: str = "RO") -> GeocodingResult:
        """Convert address to coordinates"""
        return await self.geocoding_service.geocode_address(address, country)
    
    async def reverse_geocode(self, coordinates: Coordinates) -> GeocodingResult:
        """Convert coordinates to address"""
        return await self.geocoding_service.reverse_geocode(coordinates)
    
    # Spatial Queries
    async def find_nearby_orders(self, query: SpatialQuery) -> List[Dict[str, Any]]:
        """Find orders within radius"""
        return await self.spatial_service.find_nearby_points(query, "orders")
    
    async def find_nearby_subcontractors(self, query: SpatialQuery) -> List[Dict[str, Any]]:
        """Find subcontractors within radius"""
        return await self.spatial_service.find_nearby_points(query, "subcontractors")


# Service factory function
async def create_geographic_service(db_session: AsyncSession) -> GeographicService:
    """Factory function to create and initialize geographic service"""
    service = GeographicService(db_session)
    await service.initialize()
    return service 