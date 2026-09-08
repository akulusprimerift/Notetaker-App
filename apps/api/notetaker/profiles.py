"""Saved prompt presets are copied into immutable lecture settings on apply."""
from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from .models import PromptProfile, CommandReceipt
from .security import error


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=120)
    detail_prompt: str = Field(default='', max_length=2000)
    layout_prompt: str = Field(default='', max_length=2000)
    instructions: str = Field(default='', max_length=1000)
    expected_version: int = Field(default=0, ge=0)


def profile_json(row):
    return {key:getattr(row,key) for key in ('id','name','detail_prompt','layout_prompt','instructions','version')}


def install_profiles(app, current, db_session, receipt):
    @app.get('/prompt-profiles')
    def profiles(session=Depends(current), db=Depends(db_session)):
        return [profile_json(row) for row in db.scalars(select(PromptProfile).where(PromptProfile.owner_id==session.owner_id, PromptProfile.deleted.is_(False)).order_by(PromptProfile.name, PromptProfile.id))]

    def save(profile_id, body, request, session, db):
        action='prompt_profile:'+str(profile_id or 'new')
        previous,key,fingerprint=receipt(db,request,session,action,body.model_dump())
        if previous:
            return profile_json(db.get(PromptProfile,previous.result_id))
        row=db.get(PromptProfile,profile_id) if profile_id else None
        if profile_id and (not row or row.owner_id!=session.owner_id or row.deleted):
            error(404,'unavailable','This profile is unavailable.')
        if body.expected_version != (row.version if row else 0):
            error(409,'profile_version','This profile changed in another window. Reload profiles before updating it.')
        if not body.name.strip():
            error(422,'profile_name','Give this profile a name.')
        if not row:
            row=PromptProfile(owner_id=session.owner_id, name=body.name)
            db.add(row)
            db.flush()
        for field in ('name','detail_prompt','layout_prompt','instructions'):
            setattr(row,field,getattr(body,field))
        row.version=body.expected_version+1
        db.flush()
        db.add(CommandReceipt(owner_id=session.owner_id,action=action,key=key,fingerprint=fingerprint,result_id=row.id))
        db.commit()
        return profile_json(row)

    @app.post('/prompt-profiles',status_code=201)
    def create(body: ProfileInput, request: Request, session=Depends(current), db=Depends(db_session)):
        return save(None,body,request,session,db)

    @app.put('/prompt-profiles/{profile_id}')
    def change(profile_id: str, body: ProfileInput, request: Request, session=Depends(current), db=Depends(db_session)):
        return save(profile_id,body,request,session,db)
