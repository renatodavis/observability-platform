from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Integration as IntegrationModel
from app.schemas import Integration, IntegrationCreate, IntegrationUpdate

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("", response_model=list[Integration])
def list_integrations(db: Session = Depends(get_db)) -> list[IntegrationModel]:
    stmt = select(IntegrationModel).order_by(IntegrationModel.id)
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=Integration, status_code=status.HTTP_201_CREATED)
def create_integration(
    payload: IntegrationCreate, db: Session = Depends(get_db)
) -> IntegrationModel:
    exists = db.execute(
        select(IntegrationModel).where(IntegrationModel.name == payload.name)
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="integration name already exists")
    obj = IntegrationModel(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{integration_id}", response_model=Integration)
def get_integration(integration_id: int, db: Session = Depends(get_db)) -> IntegrationModel:
    obj = db.get(IntegrationModel, integration_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="integration not found")
    return obj


@router.patch("/{integration_id}", response_model=Integration)
def update_integration(
    integration_id: int,
    payload: IntegrationUpdate,
    db: Session = Depends(get_db),
) -> IntegrationModel:
    obj = db.get(IntegrationModel, integration_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="integration not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(integration_id: int, db: Session = Depends(get_db)) -> None:
    obj = db.get(IntegrationModel, integration_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="integration not found")
    db.delete(obj)
    db.commit()
