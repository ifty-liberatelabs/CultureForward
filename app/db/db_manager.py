from psycopg_pool import AsyncConnectionPool
from contextlib import asynccontextmanager
import asyncio

from app.core.logging import logger
from app.utils.errors import DatabaseConnectionError


class DatabaseManager:
    """
    Manages database connections with connection pooling for optimal resource usage.
    """

    def __init__(self, database_url: str):
        self.pool = AsyncConnectionPool(
            database_url,
            min_size=3,
            max_size=30,
            timeout=30.0,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool"""
        if not self._initialized:
            await self.pool.open()
            self._initialized = True
            logger.info(f"Database pool initialized: {self.pool.get_stats()}")

    async def cleanup(self):
        """Properly cleanup database resources"""
        if self._initialized:
            await self.pool.close()
            self._initialized = False
            logger.info("Database pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection with automatic retry on failure"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with self.pool.connection() as conn:
                    yield conn
                    return
                            
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to get database connection after {max_retries} attempts", error=str(e))
                    raise DatabaseConnectionError(str(e))
                
                logger.warning(f"Database connection attempt {attempt + 1} failed, retrying...", error=str(e))
                await asyncio.sleep(retry_delay * (2 ** attempt))

