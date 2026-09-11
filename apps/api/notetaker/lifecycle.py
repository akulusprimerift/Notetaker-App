"""Final snapshots and deletion reconciliation survive requests, workers and restarts."""
import asyncio
import logging
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from typing import Literal
from fastapi import Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update, delete, func
from . import models as m
from .security import error, mutation
from .transcription import lock_lecture, current_runs, schedule, freeze_transcript, transcript_json
from .notes import latest, notes_json, schedule_notes, markdown
from .note_edits import head

log=logging.getLogger('notetaker.lifecycle')


def notify(db, lecture, kind, entity):
    lecture.update_seq+=1
    db.add(m.LectureUpdate(lecture_id=lecture.id,sequence=lecture.update_seq,kind=kind,entity_id=entity,entity_version=lecture.update_seq))


def editing_version(db, lecture):
    selected=head(db,lecture.id)
    return selected.version if selected else 0


def final_json(db, row):
    snapshot=db.scalar(select(m.FinalSnapshot.id).where(m.FinalSnapshot.finalization_id==row.id))
    return {'id':row.id,'status':row.status,'issues':row.issues,'snapshot_id':snapshot,'created_at':row.created_at.isoformat()+'Z'}


def deletion_json(db, row):
    total=db.scalar(select(func.count()).select_from(m.DeletionObject).where(m.DeletionObject.deletion_id==row.id))
    removed=db.scalar(select(func.count()).select_from(m.DeletionObject).where(m.DeletionObject.deletion_id==row.id,m.DeletionObject.removed.is_(True)))
    return {'id':row.id,'lecture_id':row.lecture_id,'kind':row.kind,'status':row.status,'objects_total':total,'objects_removed':removed,'error':row.error,'browser_ack':row.browser_ack,
        'created_at':row.created_at.isoformat()+'Z'}


def seal_available(db, lecture):
    """Freeze intake without pretending unacknowledged or missing audio was saved."""
    issues=[]
    for run in current_runs(db,lecture):
        rows=db.scalars(select(m.UploadReservation).where(m.UploadReservation.run_id==run.id).order_by(m.UploadReservation.sequence)).all()
        if run.state=='recording' or run.last_sequence is None:
            issues.append('Recording ended with an unknown tail; browser-only audio is excluded.')
            run.gaps=[*run.gaps,{'reason':'finalized_available','after_sample':max((r.identity['start_sample']+r.identity['sample_count'] for r in rows),default=0),'unknown_extent':True}]
        run.last_sequence=max(run.last_sequence if run.last_sequence is not None else -1,max((r.sequence for r in rows),default=-1))
        run.final_sample_count=max(run.final_sample_count or 0,max((r.identity['start_sample']+r.identity['sample_count'] for r in rows),default=0))
        verified=[r for r in rows if r.state=='verified']
        saved=sum(r.identity['sample_count'] for r in verified)
        if saved!=run.final_sample_count:
            issues.append('Some declared audio was not saved; available intervals will be transcribed.')
        run.state='finalized'
        existing=db.scalar(select(m.AudioManifestRevision.id).where(m.AudioManifestRevision.run_id==run.id,m.AudioManifestRevision.version==run.manifest_version))
        if existing:continue
        run.manifest_version+=1
        db.add(m.AudioManifestRevision(lecture_id=lecture.id,run_id=run.id,version=run.manifest_version,content={
            'complete':saved==run.final_sample_count,'available_only':True,'final_sample_count':run.final_sample_count,
            'chunks':[dict(r.identity,chunk_id=r.id,storage_state=r.state) for r in rows],'gaps':run.gaps}))
    return sorted(set(issues))


def settle_final(db, lecture, request, available=False):
    if lecture.tombstoned or request.lifecycle_epoch!=lecture.lifecycle_epoch or request.audio_epoch!=lecture.audio_epoch:
        request.status='cancelled';return
    if editing_version(db,lecture)!=request.expected_edit_version:
        request.status='needs_attention';request.issues=sorted(set([*request.issues,'Student notes changed during finalization. Review them, then finalize again.']));return
    if not lecture.audio_removed:
        made=schedule(db,lecture)
        if made: freeze_transcript(db,lecture)
    speech=transcript_json(db,lecture)
    pending=speech['counts']['due']+speech['counts']['running']
    if pending and not available:
        if speech['errors']:
            request.status='needs_attention';request.issues=sorted(set([*request.issues,'Speech processing needs attention: '+', '.join(speech['errors'])]));return
        request.status='speech';return
    if speech['counts']['failed'] and not available:
        request.status='needs_attention';request.issues=sorted(set([*request.issues,'Some speech processing failed. Retry or finalize available results.']));return
    if not available and not lecture.audio_removed:
        schedule_notes(db,lecture)
    db.flush()
    notes=notes_json(db,lecture)
    if notes['status'] in ('queued','generating') and not available:
        request.status='notes';return
    if notes['status']=='needs_attention' and not available:
        request.status='needs_attention';request.issues=sorted(set([*request.issues,'Note generation failed. Retry or finalize available results.']));return
    issues=list(request.issues)
    if speech['snapshot']:
        messages={
            'finalized_available':'Recording ended with an unknown tail; browser-only audio is excluded.',
            'transcription_due':'Speech processing was still pending when available results were finalized.',
            'transcription_running':'Speech processing was still pending when available results were finalized.',
            'transcription_failed':'Some audio could not be transcribed.',
            'transcription_cancelled':'Some speech processing was cancelled.',
            'uncertain_speech':'Some speech could not be recognized confidently.',
            'awaiting_saved_audio':'Some recording content was not available for transcription.',
            'between_runs':'The lecture includes separately recorded segments.',
        }
        issues.extend(messages.get(i['reason'],'A recording interruption remains marked in the transcript.') for i in speech['snapshot']['issues'])
    else: issues.append('No transcript is available.')
    selected=notes['editing']['selected'] or notes['revision']
    if not selected: issues.append('No saved notes are available.')
    if notes['editing']['sources_changed']: issues.append('The selected student revision uses earlier sources or settings.')
    if notes['stale']: issues.append('Saved notes do not cover the current transcript and preferences.')
    if pending: issues.append('Speech processing was still pending when available results were finalized.')
    if selected:
        issues.extend(i['detail'] for i in selected['content']['issues'])
        if any(c['disposition']!='used' for c in selected['content']['coverage']): issues.append('Some transcript passages are omitted or unclear in these notes.')
    if lecture.audio_removed: issues.append('Audio has been removed; retained transcript and notes are included.')
    if available:
        db.execute(update(m.Job).where(m.Job.lecture_id==lecture.id,m.Job.status.in_(['due','running'])).values(status='cancelled',error_code='finalized_available'))
        db.execute(update(m.NoteRequest).where(m.NoteRequest.lecture_id==lecture.id).values(preview='',preview_attempt=''))
    settings=latest(db,m.SettingsVersion,lecture.id,m.SettingsVersion.version)
    snapshot=m.FinalSnapshot(lecture_id=lecture.id,finalization_id=request.id,content=deepcopy({
        'title':lecture.title,'transcript':speech['snapshot'],'notes':selected,'issues':sorted(set(issues)),
        'settings':{key:getattr(settings,key) for key in ('id','version','depth','format','instructions','detail_prompt','layout_prompt','ai_explanations')},
        'lifecycle_epoch':lecture.lifecycle_epoch,'audio_epoch':lecture.audio_epoch}),markdown='')
    import html
    def escaped(value):
        return ''.join('\\'+c if c in '\\`*_{}[]()#+-.!|>' else c for c in html.escape(value,quote=False))
    if selected:
        if selected.get('student'):
            edit=head(db,lecture.id);base=db.get(m.NoteRevision,edit.generated_id)
            revision=SimpleNamespace(request_id=base.request_id,revision=edit.version,content=edit.content,metadata_json={**base.metadata_json,'student_revision':True})
        else: revision=db.get(m.NoteRevision,selected['id'])
        snapshot.markdown=markdown(db,lecture,revision)
    else:
        snapshot.markdown='# Final lecture content\n\n'+escaped(lecture.title)+'\n\nNo saved notes.\n'
    snapshot.markdown+='\n\n## Finalization status\n\n'+('\n'.join('- '+escaped(i) for i in sorted(set(issues))) if issues else 'All available processing completed.')
    # Snapshot export carries transcript even when no model output is available.
    if not selected and speech['snapshot']:
        snapshot.markdown+='\n\n## Available transcript\n\n'+'\n\n'.join(escaped(s['text']) for s in speech['snapshot']['segments'])
    db.add(snapshot);db.flush()
    request.status='incomplete' if issues else 'complete';request.issues=sorted(set(issues));lecture.status='finalized'
    notify(db,lecture,'lecture.finalized',snapshot.id)


def reconcile_finalizations(sessions):
    with sessions() as db:
        ids=db.scalars(select(m.Finalization.id).where(m.Finalization.status.in_(['speech','notes']))).all()
    for id in ids:
        with sessions() as db:
            row=db.get(m.Finalization,id);lecture=lock_lecture(db,row.lecture_id)
            db.refresh(row)
            if row.status in ('speech','notes'):settle_final(db,lecture,row)
            db.commit()


def erase_content(db, lecture):
    # Reverse dependency order, retaining only minimal deletion receipts/tombstone.
    keep={'lectures','deletions','deletion_objects'}
    for table in reversed(m.Base.metadata.sorted_tables):
        if 'lecture_id' in table.c and table.name not in keep:
            db.execute(delete(table).where(table.c.lecture_id==lecture.id))
    # Command receipts contain identifiers/hashes, not lecture text, and remain for retries.
    lecture.title='Deleted lecture';lecture.status='deleted'


def reconcile_deletion(sessions, store, id):
    # Every pass re-lists the prefix: even a crashed upload finishing after an
    # earlier deletion is caught. A tombstoned lecture never receives new objects.
    with sessions() as db:
        row=db.get(m.Deletion,id)
        if not row:return
        lecture=lock_lecture(db,row.lecture_id)
        if row.audio_epoch>lecture.audio_epoch or not (lecture.tombstoned or lecture.audio_removed):return
        prefix=lecture.id+'/'
        known=set(db.scalars(select(m.UploadReservation.object_key).where(m.UploadReservation.lecture_id==lecture.id)))
        db.commit()
    try:
        discovered=set(store.list_keys(prefix)) if store.available else set()
        if not store.available and known: raise RuntimeError('audio_store_unavailable')
        with sessions() as db:
            row=db.get(m.Deletion,id);lecture=lock_lecture(db,row.lecture_id)
            for key in known|discovered:
                if not key.startswith(prefix):raise ValueError('object_prefix')
                item=db.get(m.DeletionObject,(id,key))
                if not item:db.add(m.DeletionObject(deletion_id=id,object_key=key))
                elif key in discovered:item.removed=False
            db.commit()
        with sessions() as db:
            keys=list(db.scalars(select(m.DeletionObject.object_key).where(m.DeletionObject.deletion_id==id,m.DeletionObject.removed.is_(False))))
        for key in keys:
            store.delete_verified(key)
            with sessions() as db:
                db.get(m.DeletionObject,(id,key)).removed=True;db.commit()
        # Confirm the inventory against storage, not just delete responses.
        if store.available and store.list_keys(prefix):raise RuntimeError('objects_still_present')
        with sessions() as db:
            row=db.get(m.Deletion,id);lecture=lock_lecture(db,row.lecture_id)
            if row.kind=='lecture':erase_content(db,lecture)
            else:
                db.execute(update(m.UploadReservation).where(m.UploadReservation.lecture_id==lecture.id).values(state='removed'))
            row.status='complete';row.error=None;row.reconciled_at=m.now();db.commit()
    except Exception:
        log.warning('deletion_retry deletion_id=%s',id)
        with sessions() as db:
            row=db.get(m.Deletion,id)
            if row:row.status='retrying';row.error='Storage cleanup is waiting for another attempt.';row.reconciled_at=m.now();db.commit()


def reconcile_deletions(sessions, store):
    with sessions() as db:
        ids=db.scalars(select(m.Deletion.id).where((m.Deletion.status!='complete') | (m.Deletion.reconciled_at<m.now()-timedelta(seconds=30)))).all()
    for id in ids:reconcile_deletion(sessions,store,id)


async def coordinator(app):
    from starlette.concurrency import run_in_threadpool
    while True:
        try:
            await run_in_threadpool(reconcile_finalizations,app.state.sessions)
            await run_in_threadpool(reconcile_deletions,app.state.sessions,app.state.audio_store)
            from .course_deletion import reconcile_courses
            await run_in_threadpool(reconcile_courses,app.state.sessions)
        except Exception:log.warning('lifecycle_reconciliation_retry')
        await asyncio.sleep(2)


class FinalInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_cursor:int=Field(ge=0)
    expected_edit_version:int=Field(ge=0)
    available_only:bool=False


class DeleteInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_cursor:int=Field(ge=0)
    kind:Literal['audio','lecture']


def install_lifecycle(app,current,db_session,owned_lecture,receipt):
    @app.get('/lectures/{lecture_id}/finalization')
    def state(lecture_id:str,session=Depends(current),db=Depends(db_session)):
        lecture=owned_lecture(db,session.owner_id,lecture_id)
        rows=db.scalars(select(m.Finalization).where(m.Finalization.lecture_id==lecture_id).order_by(m.Finalization.created_at.desc())).all()
        return {'cursor':lecture.update_seq,'edit_version':editing_version(db,lecture),'audio_removed':lecture.audio_removed,'status':lecture.status,'history':[final_json(db,row) for row in rows]}

    @app.post('/lectures/{lecture_id}/finalization',status_code=202)
    def start(lecture_id:str,body:FinalInput,request:Request,session=Depends(current),db=Depends(db_session)):
        action='finalize:'+lecture_id
        prior,key,fingerprint=receipt(db,request,session,action,body.model_dump())
        lecture=owned_lecture(db,session.owner_id,lecture_id);lecture=lock_lecture(db,lecture.id)
        if prior:return final_json(db,db.get(m.Finalization,prior.result_id))
        if lecture.update_seq!=body.expected_cursor or editing_version(db,lecture)!=body.expected_edit_version:
            error(409,'finalization_version','Lecture content changed. Review the latest state and try finalizing again.')
        db.execute(update(m.Finalization).where(m.Finalization.lecture_id==lecture.id,m.Finalization.status.in_(['speech','notes','needs_attention'])).values(status='cancelled'))
        lecture.status='finalizing'
        row=m.Finalization(lecture_id=lecture.id,lifecycle_epoch=lecture.lifecycle_epoch,audio_epoch=lecture.audio_epoch,expected_edit_version=body.expected_edit_version,issues=seal_available(db,lecture) if not lecture.audio_removed else [])
        db.add(row);db.flush()
        if not lecture.audio_removed:
            schedule(db,lecture);freeze_transcript(db,lecture)
            # Retry failed speech, preserving immutable prior generations.
            db.execute(update(m.Job).where(m.Job.lecture_id==lecture.id,m.Job.kind=='speech.window',m.Job.status.in_(['failed','cancelled']),m.Job.audio_epoch==lecture.audio_epoch).values(status='due',attempts=0,error_code=None,due_at=m.now()))
        if not body.available_only:
            db.execute(update(m.Job).where(m.Job.lecture_id==lecture.id,m.Job.kind=='notes.generate',m.Job.status.in_(['failed','cancelled']),m.Job.audio_epoch==lecture.audio_epoch).values(status='due',attempts=0,error_code=None,due_at=m.now()))
        notify(db,lecture,'lecture.finalizing',row.id)
        db.add(m.CommandReceipt(owner_id=session.owner_id,action=action,key=key,fingerprint=fingerprint,result_id=row.id))
        settle_final(db,lecture,row,body.available_only);db.commit()
        return final_json(db,row)

    @app.post('/lectures/{lecture_id}/finalization/reopen')
    def reopen(lecture_id:str,body:FinalInput,request:Request,session=Depends(current),db=Depends(db_session)):
        action='reopen_final:'+lecture_id
        prior,key,fingerprint=receipt(db,request,session,action,body.model_dump())
        lecture=owned_lecture(db,session.owner_id,lecture_id);lecture=lock_lecture(db,lecture.id)
        if prior:return {'status':lecture.status}
        if lecture.audio_removed:error(409,'audio_removed','Removed audio cannot be recovered into this lecture.')
        if lecture.update_seq!=body.expected_cursor or editing_version(db,lecture)!=body.expected_edit_version:
            error(409,'finalization_version','Lecture content changed. Refresh before reopening.')
        if lecture.status not in ('finalizing','finalized'):error(409,'not_final','This lecture already accepts audio.')
        db.execute(update(m.Finalization).where(m.Finalization.lecture_id==lecture.id,m.Finalization.status.in_(['speech','notes','needs_attention'])).values(status='cancelled'))
        db.execute(update(m.Job).where(m.Job.lecture_id==lecture.id,m.Job.status.in_(['due','running'])).values(status='cancelled',error_code='reopened'))
        for run in current_runs(db,lecture):
            if run.state=='finalized':
                run.state='interrupted';run.manifest_version+=1
                run.last_sequence=None;run.final_sample_count=None
        lecture.status='audio_pending';lecture.capture_epoch+=1
        notify(db,lecture,'lecture.reopened',lecture.id)
        db.add(m.CommandReceipt(owner_id=session.owner_id,action=action,key=key,fingerprint=fingerprint,result_id=lecture.id))
        db.commit();return {'status':lecture.status}

    @app.get('/lectures/{lecture_id}/final-snapshots/{snapshot_id}')
    def saved(lecture_id:str,snapshot_id:str,session=Depends(current),db=Depends(db_session)):
        owned_lecture(db,session.owner_id,lecture_id)
        row=db.get(m.FinalSnapshot,snapshot_id)
        if not row or row.lecture_id!=lecture_id:error(404,'unavailable','This final snapshot is unavailable.')
        return {'id':row.id,'created_at':row.created_at.isoformat()+'Z',**row.content}

    @app.get('/lectures/{lecture_id}/final-snapshots/{snapshot_id}/export')
    def export(lecture_id:str,snapshot_id:str,format:Literal['markdown','html']='markdown',session=Depends(current),db=Depends(db_session)):
        owned_lecture(db,session.owner_id,lecture_id);row=db.get(m.FinalSnapshot,snapshot_id)
        if not row or row.lecture_id!=lecture_id:error(404,'unavailable','This final snapshot is unavailable.')
        if format == 'html':
            from .visual_notes import html_notes
            notes = row.content.get('notes')
            return Response(html_notes(row.content['title'], notes['content'] if notes else {'blocks': []}, row.markdown),
                media_type='text/html', headers={'Content-Disposition':'attachment; filename="final-lecture.html"', 'X-Content-Type-Options':'nosniff'})
        return Response(row.markdown,media_type='text/markdown',headers={'Content-Disposition':'attachment; filename="final-lecture.md"'})

    @app.post('/lectures/{lecture_id}/deletion',status_code=202)
    def remove(lecture_id:str,body:DeleteInput,request:Request,session=Depends(current),db=Depends(db_session)):
        action='delete:'+lecture_id
        prior,key,fingerprint=receipt(db,request,session,action,body.model_dump())
        if prior:return deletion_json(db,db.get(m.Deletion,prior.result_id))
        lecture=owned_lecture(db,session.owner_id,lecture_id);lecture=lock_lecture(db,lecture.id)
        if lecture.update_seq!=body.expected_cursor:error(409,'deletion_version','Lecture content changed. Review it before removing data.')
        existing=db.scalar(select(m.Deletion).where(m.Deletion.lecture_id==lecture.id,m.Deletion.kind==body.kind))
        if existing:return deletion_json(db,existing)
        lecture.audio_removed=True;lecture.audio_epoch+=1;lecture.capture_epoch+=1
        if body.kind=='lecture':lecture.tombstoned=True;lecture.lifecycle_epoch+=1;lecture.status='deleting'
        else:
            lecture.status='audio_removed'
            pref=latest(db,m.NotePreference,lecture.id,m.NotePreference.version)
            if pref:db.add(m.NotePreference(lecture_id=lecture.id,version=pref.version+1,model=pref.model,model_digest=pref.model_digest,enabled=False))
            freeze_transcript(db,lecture)
        db.execute(update(m.Job).where(m.Job.lecture_id==lecture.id,m.Job.status.in_(['due','running'])).values(status='cancelled',attempt_token=None,error_code='data_removed'))
        db.execute(update(m.NoteRequest).where(m.NoteRequest.lecture_id==lecture.id).values(preview='',preview_attempt=''))
        db.execute(update(m.Finalization).where(m.Finalization.lecture_id==lecture.id,m.Finalization.status.in_(['speech','notes','needs_attention'])).values(status='cancelled'))
        row=m.Deletion(lecture_id=lecture.id,owner_id=session.owner_id,kind=body.kind,lifecycle_epoch=lecture.lifecycle_epoch,audio_epoch=lecture.audio_epoch)
        db.add(row);db.flush()
        for object_key in db.scalars(select(m.UploadReservation.object_key).where(m.UploadReservation.lecture_id==lecture.id)):
            db.add(m.DeletionObject(deletion_id=row.id,object_key=object_key))
        notify(db,lecture,'lecture.data_removed',row.id)
        db.add(m.CommandReceipt(owner_id=session.owner_id,action=action,key=key,fingerprint=fingerprint,result_id=row.id));db.commit()
        return deletion_json(db,row)

    @app.get('/deletions')
    def deletions(session=Depends(current),db=Depends(db_session)):
        return [deletion_json(db,row) for row in db.scalars(select(m.Deletion).where(m.Deletion.owner_id==session.owner_id).order_by(m.Deletion.created_at.desc()))]

    @app.post('/deletions/{deletion_id}/browser-purged')
    def ack(deletion_id:str,request:Request,session=Depends(current),db=Depends(db_session)):
        mutation(request,session);row=db.get(m.Deletion,deletion_id)
        if not row or row.owner_id!=session.owner_id:error(404,'unavailable','This deletion is unavailable.')
        row.browser_ack=True;db.commit();return deletion_json(db,row)
