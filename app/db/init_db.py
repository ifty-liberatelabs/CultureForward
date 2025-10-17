from app.core.logging import logger
from app.core.config import settings
from urllib.parse import urlparse
import psycopg2
from psycopg2 import sql, OperationalError


def check_and_create_db():
    """Check if database exists and create if it doesn't"""
    database_url = settings.DATABASE_URL
    target_db = settings.POSTGRES_DB

    parsed_url = urlparse(database_url)
    user = parsed_url.username
    password = parsed_url.password
    host = parsed_url.hostname
    port = parsed_url.port

    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port,
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute(
            sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [target_db]
        )
        exists = cursor.fetchone()

        if exists:
            logger.info(f"Database '{target_db}' already exists")
        else:
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db))
            )
            logger.info(f"Database '{target_db}' created successfully")

    except OperationalError as e:
        logger.error(f"OperationalError: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()


def init_db():
    """Initialize database tables using raw SQL"""
    try:
        database_url = settings.DATABASE_URL
        
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create survey table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS survey (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title VARCHAR NOT NULL,
                goal TEXT NOT NULL,
                company_url VARCHAR NOT NULL,
                themes JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
            )
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                role VARCHAR NOT NULL,
                content TEXT NOT NULL,
                survey_id UUID NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                FOREIGN KEY (survey_id) REFERENCES survey(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_survey_id_created_at ON messages(survey_id, created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_survey_created_at ON survey(created_at)
        """)
        
        # Create trigger function for updated_at
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)
        
        # Create triggers
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_survey_updated_at ON survey
        """)
        cursor.execute("""
            CREATE TRIGGER update_survey_updated_at
                BEFORE UPDATE ON survey
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
        """)
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_messages_updated_at ON messages
        """)
        cursor.execute("""
            CREATE TRIGGER update_messages_updated_at
                BEFORE UPDATE ON messages
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
        """)
        
        cursor.close()
        conn.close()
        
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

