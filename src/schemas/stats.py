
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

# Schema for validating date range input
class DateRange(BaseModel):
    start_date: str = Field(..., description="Start date in YYYY-MM-DD HH:MM:SS format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD HH:MM:SS format")

    @field_validator('start_date', 'end_date')
    def validate_datetime_format(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("Date must be in 'YYYY-MM-DD HH:MM:SS' format.")
        return v

    @classmethod
    def validate_date_range(cls, start_date: str, end_date: str) -> 'DateRange':
        start = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        if start > end:
            raise ValueError("Start date must be before or equal to end date.")
        return cls(start_date=start_date, end_date=end_date)

# Schema for user statistics    
class UserStatsSchema(BaseModel):
    endpoint: str
    count: int