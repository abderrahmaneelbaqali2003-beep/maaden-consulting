from sqlalchemy.orm import Session

from app.database.models import Manufacturer


def get_or_create_manufacturer(session: Session, name: str | None) -> Manufacturer | None:
    if not name:
        return None
    name = name.strip()
    manufacturer = session.query(Manufacturer).filter(Manufacturer.name == name).one_or_none()
    if manufacturer is None:
        manufacturer = Manufacturer(name=name)
        session.add(manufacturer)
        session.flush()
    return manufacturer
