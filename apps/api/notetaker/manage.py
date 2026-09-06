"""Local administration: secrets are delivered to a local file, never application logs."""
import argparse
import os
import secrets
from datetime import timedelta
from pathlib import Path
from sqlalchemy import select
from .config import Settings
from .db import database
from .models import Bootstrap, Session, now
from .security import digest


def unlock(output: Path):
    settings=Settings()
    engine,sessions=database(settings.database_url)
    token=secrets.token_urlsafe(48)
    with sessions() as db:
        existing=db.get(Bootstrap,1)
        if existing:
            existing.token_hash=digest(token)
            existing.expires_at=now()+timedelta(minutes=30)
            existing.used=False
        else:
            db.add(Bootstrap(id=1,token_hash=digest(token),expires_at=now()+timedelta(minutes=30)))
        # Issuing a local recovery code revokes previous sessions deliberately.
        for session in db.scalars(select(Session).where(Session.revoked.is_(False))):
            session.revoked=True
        db.commit()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(token,encoding="utf8")
    if os.name != "nt":
        output.chmod(0o600)
    engine.dispose()
    print(f"One-use unlock code written to {output}. Expires in 30 minutes. Existing sessions revoked.")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=["unlock"])
    parser.add_argument("--output",type=Path,default=Path(".local/unlock-code.txt"))
    args=parser.parse_args()
    unlock(args.output)
