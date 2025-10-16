from langgraph.checkpoint.memory import MemorySaver
from typing import Dict
from uuid import UUID


class SurveyMemoryStore:
    def __init__(self):
        self._checkpointer = MemorySaver()
        self._init_data: Dict[UUID, Dict] = {}
    
    def get_checkpointer(self) -> MemorySaver:
        return self._checkpointer
    
    def store_init_data(self, survey_id: UUID, data: Dict) -> None:
        self._init_data[survey_id] = data
    
    def get_init_data(self, survey_id: UUID) -> Dict:
        return self._init_data.get(survey_id)
    
    def clear_store(self, survey_id: UUID) -> None:
        if survey_id in self._init_data:
            del self._init_data[survey_id]


survey_memory_store = SurveyMemoryStore()