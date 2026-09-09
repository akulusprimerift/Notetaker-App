"""Delete a course through the same durable child-lecture reconciliation."""
from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, delete, update
from . import models as m
from .security import error
from .lifecycle import notify
from .transcription import lock_lecture


def tombstone_lecture(db, lecture, owner):
    existing=db.scalar(select(m.Deletion).where(m.Deletion.lecture_id==lecture.id,m.Deletion.kind=='lecture'))
    if existing:return existing
    lecture.tombstoned=True;lecture.audio_removed=True;lecture.lifecycle_epoch+=1
    lecture.audio_epoch+=1;lecture.capture_epoch+=1;lecture.status='deleting'
    db.execute(update(m.Job).where(m.Job.lecture_id==lecture.id,m.Job.status.in_(['due','running'])).values(status='cancelled',attempt_token=None,error_code='data_removed'))
    db.execute(update(m.NoteRequest).where(m.NoteRequest.lecture_id==lecture.id).values(preview='',preview_attempt=''))
    db.execute(update(m.Finalization).where(m.Finalization.lecture_id==lecture.id,m.Finalization.status.in_(['speech','notes','needs_attention'])).values(status='cancelled'))
    row=m.Deletion(lecture_id=lecture.id,owner_id=owner,kind='lecture',lifecycle_epoch=lecture.lifecycle_epoch,audio_epoch=lecture.audio_epoch)
    db.add(row);db.flush()
    for key in db.scalars(select(m.UploadReservation.object_key).where(m.UploadReservation.lecture_id==lecture.id)):
        db.add(m.DeletionObject(deletion_id=row.id,object_key=key))
    notify(db,lecture,'lecture.data_removed',row.id)
    return row


def progress(db, course):
    rows=list(db.scalars(select(m.Deletion).join(m.Lecture,m.Lecture.id==m.Deletion.lecture_id)
        .where(m.Lecture.course_id==course.id,m.Deletion.kind=='lecture')))
    complete=sum(r.status=='complete' for r in rows)
    return {'id':course.id,'status':'complete' if complete==len(rows) else 'removing',
        'lectures_total':len(rows),'lectures_removed':complete}


def reconcile_courses(sessions):
    with sessions() as db:
        for course in db.scalars(select(m.Course).where(m.Course.tombstoned.is_(True))):
            if progress(db,course)['status']=='complete':
                db.execute(delete(m.CourseMaterial).where(m.CourseMaterial.course_id==course.id))
                course.name='Deleted course';course.code=''
        db.commit()


class CourseDelete(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    expected_lecture_ids:list[str]=Field(max_length=10000)


def install_course_deletion(app,current,db_session,receipt):
    @app.post('/courses/{course_id}/deletion',status_code=202)
    def remove(course_id:str,body:CourseDelete,request:Request,session=Depends(current),db=Depends(db_session)):
        prior,key,fingerprint=receipt(db,request,session,'delete_course:'+course_id,body.model_dump())
        course=db.scalar(select(m.Course).where(m.Course.id==course_id,m.Course.owner_id==session.owner_id).with_for_update().execution_options(populate_existing=True))
        if not course:error(404,'unavailable','This course is unavailable.')
        if prior or course.tombstoned:return progress(db,course)
        lectures=list(db.scalars(select(m.Lecture).where(m.Lecture.course_id==course_id,m.Lecture.tombstoned.is_(False)).order_by(m.Lecture.id)))
        if sorted(body.expected_lecture_ids)!=sorted(r.id for r in lectures):
            error(409,'course_changed','The course lectures changed. Review the updated list before deleting the course.')
        course.tombstoned=True
        for lecture in lectures:tombstone_lecture(db,lock_lecture(db,lecture.id),session.owner_id)
        db.add(m.CommandReceipt(owner_id=session.owner_id,action='delete_course:'+course_id,key=key,fingerprint=fingerprint,result_id=course.id))
        if not lectures:
            db.execute(delete(m.CourseMaterial).where(m.CourseMaterial.course_id==course.id,m.CourseMaterial.lecture_id.is_(None)))
            course.name='Deleted course';course.code=''
        db.commit();return progress(db,course)

    @app.get('/course-deletions')
    def deletions(session=Depends(current),db=Depends(db_session)):
        return [progress(db,row) for row in db.scalars(select(m.Course).where(m.Course.owner_id==session.owner_id,m.Course.tombstoned.is_(True)))]
