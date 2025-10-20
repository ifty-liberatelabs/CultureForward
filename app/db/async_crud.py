from app.db.db_manager import DatabaseManager
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
import json


class AsyncSurveyCRUD:
    """Async CRUD operations for Survey table"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def create(self, title: str, goal: str, company_url: str, themes: Optional[List] = None) -> Dict:
        """Create a new survey"""
        async with self.db_manager.get_connection() as conn:
            query = """
                INSERT INTO survey (id, title, goal, company_url, themes, created_at, updated_at)
                VALUES (gen_random_uuid(), %s, %s, %s, %s::jsonb, NOW(), NOW())
                RETURNING id, title, goal, company_url, themes, created_at, updated_at
            """
            themes_json = json.dumps(themes or [])
            result = await conn.execute(query, (title, goal, company_url, themes_json))
            row = await result.fetchone()
            
            if row:
                return {
                    "id": str(row[0]),
                    "title": row[1],
                    "goal": row[2],
                    "company_url": row[3],
                    "themes": row[4] if row[4] else [],
                    "created_at": row[5].isoformat(),
                    "updated_at": row[6].isoformat()
                }
            return None
    
    async def get_by_id(self, survey_id: str) -> Optional[Dict]:
        """Get survey by ID"""
        async with self.db_manager.get_connection() as conn:
            query = """
                SELECT id, title, goal, company_url, themes, created_at, updated_at
                FROM survey WHERE id = %s
            """
            result = await conn.execute(query, (survey_id,))
            row = await result.fetchone()
            
            if row:
                return {
                    "id": str(row[0]),
                    "title": row[1],
                    "goal": row[2],
                    "company_url": row[3],
                    "themes": row[4] if row[4] else [],
                    "created_at": row[5].isoformat(),
                    "updated_at": row[6].isoformat()
                }
            return None
    
    async def update_themes(self, survey_id: str, themes: List) -> Optional[Dict]:
        """Update themes for a survey"""
        async with self.db_manager.get_connection() as conn:
            query = """
                UPDATE survey 
                SET themes = %s::jsonb, updated_at = NOW()
                WHERE id = %s
                RETURNING id, title, goal, company_url, themes, created_at, updated_at
            """
            themes_json = json.dumps(themes)
            result = await conn.execute(query, (themes_json, survey_id))
            row = await result.fetchone()
            
            if row:
                return {
                    "id": str(row[0]),
                    "title": row[1],
                    "goal": row[2],
                    "company_url": row[3],
                    "themes": row[4] if row[4] else [],
                    "created_at": row[5].isoformat(),
                    "updated_at": row[6].isoformat()
                }
            return None


class AsyncMessageCRUD:
    """Async CRUD operations for Message table"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def create(self, role: str, content: str, survey_id: str) -> Dict:
        """Create a new message"""
        async with self.db_manager.get_connection() as conn:
            query = """
                INSERT INTO messages (id, role, content, survey_id, created_at, updated_at)
                VALUES (gen_random_uuid(), %s, %s, %s, NOW(), NOW())
                RETURNING id, role, content, survey_id, created_at, updated_at
            """
            result = await conn.execute(query, (role, content, survey_id))
            row = await result.fetchone()
            
            if row:
                return {
                    "id": str(row[0]),
                    "role": row[1],
                    "content": row[2],
                    "survey_id": str(row[3]),
                    "created_at": row[4].isoformat(),
                    "updated_at": row[5].isoformat()
                }
            return None
    
    async def get_by_survey_id(self, survey_id: str) -> List[Dict]:
        """Get all messages for a survey"""
        async with self.db_manager.get_connection() as conn:
            query = """
                SELECT id, role, content, survey_id, created_at, updated_at
                FROM messages
                WHERE survey_id = %s
                ORDER BY created_at ASC
            """
            result = await conn.execute(query, (survey_id,))
            rows = await result.fetchall()
            
            messages = []
            for row in rows:
                messages.append({
                    "id": str(row[0]),
                    "role": row[1],
                    "content": row[2],
                    "survey_id": str(row[3]),
                    "created_at": row[4].isoformat(),
                    "updated_at": row[5].isoformat()
                })
            return messages


class AsyncThreadCRUD:
    """Async CRUD operations for Thread table"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def create(self, survey_id: str) -> Optional[Dict]:
        """Create a new thread for a survey"""
        async with self.db_manager.get_connection() as conn:
            query = """
                INSERT INTO threads (id, survey_id, created_at, updated_at)
                VALUES (gen_random_uuid(), %s, NOW(), NOW())
                RETURNING id, survey_id, created_at, updated_at
            """
            result = await conn.execute(query, (survey_id,))
            row = await result.fetchone()
            
            if row:
                return {
                    "id": str(row[0]),
                    "survey_id": str(row[1]),
                    "created_at": row[2].isoformat(),
                    "updated_at": row[3].isoformat()
                }
            return None
    
    async def get_by_id(self, thread_id: str) -> Optional[Dict]:
        """Get thread by ID"""
        async with self.db_manager.get_connection() as conn:
            query = """
                SELECT id, survey_id, created_at, updated_at
                FROM threads WHERE id = %s
            """
            result = await conn.execute(query, (thread_id,))
            row = await result.fetchone()
            
            if row:
                return {
                    "id": str(row[0]),
                    "survey_id": str(row[1]),
                    "created_at": row[2].isoformat(),
                    "updated_at": row[3].isoformat()
                }
            return None
    
    async def get_by_survey_id(self, survey_id: str) -> List[Dict]:
        """Get all threads for a survey"""
        async with self.db_manager.get_connection() as conn:
            query = """
                SELECT id, survey_id, created_at, updated_at
                FROM threads
                WHERE survey_id = %s
                ORDER BY created_at ASC
            """
            result = await conn.execute(query, (survey_id,))
            rows = await result.fetchall()
            
            threads = []
            for row in rows:
                threads.append({
                    "id": str(row[0]),
                    "survey_id": str(row[1]),
                    "created_at": row[2].isoformat(),
                    "updated_at": row[3].isoformat()
                })
            return threads


class AsyncSurveyMessageCRUD:
    """Async CRUD operations for SurveyMessage table"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def create(self, role: str, content: str, thread_id: str) -> Dict:
        """Create a new survey message"""
        async with self.db_manager.get_connection() as conn:
            query = """
                INSERT INTO survey_messages (id, role, content, thread_id, created_at, updated_at)
                VALUES (gen_random_uuid(), %s, %s, %s, NOW(), NOW())
                RETURNING id, role, content, thread_id, created_at, updated_at
            """
            result = await conn.execute(query, (role, content, thread_id))
            row = await result.fetchone()
            
            if row:
                return {
                    "id": str(row[0]),
                    "role": row[1],
                    "content": row[2],
                    "thread_id": str(row[3]),
                    "created_at": row[4].isoformat(),
                    "updated_at": row[5].isoformat()
                }
            return None
    
    async def get_by_thread_id(self, thread_id: str) -> List[Dict]:
        """Get all messages for a thread"""
        async with self.db_manager.get_connection() as conn:
            query = """
                SELECT id, role, content, thread_id, created_at, updated_at
                FROM survey_messages
                WHERE thread_id = %s
                ORDER BY created_at ASC
            """
            result = await conn.execute(query, (thread_id,))
            rows = await result.fetchall()
            
            messages = []
            for row in rows:
                messages.append({
                    "id": str(row[0]),
                    "role": row[1],
                    "content": row[2],
                    "thread_id": str(row[3]),
                    "created_at": row[4].isoformat(),
                    "updated_at": row[5].isoformat()
                })
            return messages

