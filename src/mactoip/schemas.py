from datetime import datetime
from typing import Optional
import ipaddress
from pydantic import BaseModel, ConfigDict, field_validator

from mactoip.utils import normalize_mac

class HeartbeatRequest(BaseModel):
    mac: str
    ip: str
    hostname: Optional[str] = None

    @field_validator("mac")
    @classmethod
    def validate_and_normalize_mac(cls, value: str) -> str:
        return normalize_mac(value)

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, value: str) -> str:
        cleaned = value.strip()
        try:
            # Проверяем, что это валидный IPv4 или IPv6 адрес
            ipaddress.ip_address(cleaned)
            return cleaned
        except ValueError:
            raise ValueError(f"Некорректный IP-адрес: '{value}'")

class DeviceUpdateRequest(BaseModel):
    hostname: Optional[str] = None
    comment: Optional[str] = None

class DeviceResponse(BaseModel):
    id: int
    mac: str
    ip: str
    hostname: Optional[str] = None
    comment: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    update_count: int

    model_config = ConfigDict(from_attributes=True)

class HeartbeatResponse(BaseModel):
    status: str  # "created" | "ip_updated" | "heartbeat"
    message: str
    device: DeviceResponse

class DeviceIPResponse(BaseModel):
    mac: str
    ip: str
    last_seen: datetime
    update_count: int
