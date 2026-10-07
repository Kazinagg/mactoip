from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime

from mactoip.database import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mac = Column(String(17), unique=True, index=True, nullable=False)
    ip = Column(String(45), index=True, nullable=False)
    hostname = Column(String(255), nullable=True)
    comment = Column(String(255), nullable=True)
    first_seen = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    update_count = Column(Integer, default=1, nullable=False)

    def __repr__(self) -> str:
        return f"<Device(mac='{self.mac}', ip='{self.ip}', hostname='{self.hostname}')>"
