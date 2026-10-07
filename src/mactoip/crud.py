from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from mactoip.models import Device, utc_now
from mactoip.schemas import HeartbeatRequest, DeviceUpdateRequest

def seconds_since_last_seen(device: Device) -> Optional[float]:
    """Возвращает количество секунд, прошедших с момента последнего обращения устройства."""
    if not device.last_seen:
        return None
    
    last = device.last_seen
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
        
    return (datetime.now(timezone.utc) - last).total_seconds()

def get_device_by_mac(db: Session, mac: str) -> Optional[Device]:
    return db.query(Device).filter(Device.mac == mac).first()

def get_all_devices(db: Session) -> list[Device]:
    return db.query(Device).order_by(Device.last_seen.desc()).all()

def upsert_device(db: Session, req: HeartbeatRequest) -> tuple[Device, str]:
    """
    Добавляет новое устройство или обновляет существующее.
    Возвращает (device, status), где status: 'created', 'ip_updated' (если IP изменился), 'heartbeat' (если только пинг).
    """
    device = get_device_by_mac(db, req.mac)
    now = utc_now()

    if not device:
        # Новое устройство
        device = Device(
            mac=req.mac,
            ip=req.ip,
            hostname=req.hostname,
            first_seen=now,
            last_seen=now,
            update_count=1,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return device, "created"

    # Существующее устройство
    status = "heartbeat"
    if device.ip != req.ip:
        device.ip = req.ip
        status = "ip_updated"
    
    if req.hostname and device.hostname != req.hostname:
        device.hostname = req.hostname

    device.last_seen = now
    device.update_count += 1
    db.commit()
    db.refresh(device)
    return device, status

def update_device_meta(db: Session, mac: str, req: DeviceUpdateRequest) -> Optional[Device]:
    device = get_device_by_mac(db, mac)
    if not device:
        return None

    if req.hostname is not None:
        device.hostname = req.hostname
    if req.comment is not None:
        device.comment = req.comment

    db.commit()
    db.refresh(device)
    return device

def delete_device_by_mac(db: Session, mac: str) -> bool:
    device = get_device_by_mac(db, mac)
    if not device:
        return False

    db.delete(device)
    db.commit()
    return True
