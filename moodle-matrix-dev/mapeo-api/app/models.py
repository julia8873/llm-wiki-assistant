from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class MapeoBase(BaseModel):
    moodle_user_id: int
    moodle_course_id: int
    github_fork_url: str
    matrix_room_id: str

class MapeoCreate(MapeoBase):
    pass

class MapeoRead(MapeoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
