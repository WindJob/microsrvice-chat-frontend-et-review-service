import os
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from sqlalchemy.orm import Session
from shared.db_postgresql import get_engine, Base, get_db

import models
import crud
import schemas

# Charger les variables d'environnement du fichier .env
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


app = FastAPI(title="Messaging Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_db():
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # En environnement de test local sans Postgres, on ne doit pas planter l'app.
        print("Warning: failed to create DB schema on startup:", e)


def verify_jwt_from_header(auth_header: str | None):
    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    else:
        token = auth_header
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub") or payload.get("user_id")
        role = payload.get("role")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")
        return {"id": str(user_id), "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, List[WebSocket]] = {}

    async def connect(self, conversation_id: int, websocket: WebSocket):
        await websocket.accept()
        conns = self.active_connections.get(conversation_id) or []
        conns.append(websocket)
        self.active_connections[conversation_id] = conns

    def disconnect(self, conversation_id: int, websocket: WebSocket):
        conns = self.active_connections.get(conversation_id) or []
        if websocket in conns:
            conns.remove(websocket)
        if conns:
            self.active_connections[conversation_id] = conns
        else:
            self.active_connections.pop(conversation_id, None)

    async def broadcast(self, conversation_id: int, message: dict):
        conns = self.active_connections.get(conversation_id) or []
        for conn in conns:
            try:
                await conn.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


def conversation_to_out(conv: models.Conversation):
    return {
        "id": conv.id,
        "title": conv.title,
        "type": conv.type,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "participants": [part.user_external_id for part in conv.participants],
    }


@app.on_event("startup")
def startup_event():
    create_db()


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/v1/conversations", response_model=schemas.ConversationOut)
def create_conversation(payload: schemas.ConversationCreate, authorization: str | None = Header(None), db: Session = Depends(get_db)):
    user = verify_jwt_from_header(authorization)
    # ensure the requesting user is included
    if user["id"] not in payload.participants:
        payload.participants.insert(0, user["id"])
    conv = crud.create_conversation(db, payload.title, payload.participants)
    return conversation_to_out(conv)


@app.get("/api/v1/conversations", response_model=List[schemas.ConversationOut])
def list_conversations(authorization: str | None = Header(None), db: Session = Depends(get_db)):
    user = verify_jwt_from_header(authorization)
    convs = crud.get_conversations_for_user(db, user["id"])
    return [conversation_to_out(conv) for conv in convs]


@app.post("/api/v1/conversations/{conversation_id}/messages", response_model=schemas.MessageOut)
def post_message(conversation_id: int, payload: schemas.MessageCreate, authorization: str | None = Header(None), db: Session = Depends(get_db)):
    user = verify_jwt_from_header(authorization)
    # Basic validation
    if not payload.body and not payload.location:
        raise HTTPException(status_code=400, detail="Empty message")
    msg = crud.create_message(db, conversation_id, user["id"], payload.body, payload.message_type or "text")
    # attach location if provided
    if payload.location:
        loc = payload.location
        from models import LocationSnapshot
        snapshot = LocationSnapshot(
            message_id=msg.id,
            latitude=loc.get("latitude"),
            longitude=loc.get("longitude"),
            accuracy_m=loc.get("accuracy_m"),
            address=loc.get("address"),
        )
        db.add(snapshot)
        db.commit()
        db.refresh(msg)

    # broadcast to websocket listeners
    out = {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_external_id": msg.sender_external_id,
        "body": msg.body,
        "message_type": msg.message_type,
        "created_at": msg.created_at.isoformat()
    }
    # Fire and forget
    try:
        import asyncio
        asyncio.create_task(manager.broadcast(conversation_id, {"type": "message_created", "message": out}))
    except Exception:
        pass
    # Also notify global listeners (conversation_id = 0)
    try:
        import asyncio
        asyncio.create_task(manager.broadcast(0, {"type": "message_created", "message": out, "conversation_id": conversation_id}))
    except Exception:
        pass

    return msg


@app.get("/api/v1/conversations/{conversation_id}/messages", response_model=List[schemas.MessageOut])
def get_messages(conversation_id: int, limit: int = 50, offset: int = 0, authorization: str | None = Header(None), db: Session = Depends(get_db)):
    _ = verify_jwt_from_header(authorization)
    msgs = crud.list_messages(db, conversation_id, limit=limit, offset=offset)
    return msgs


@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: int):
    # Expect token query param ?token=...
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        verify_jwt_from_header(token)
    except HTTPException:
        await websocket.close(code=1008)
        return
    await manager.connect(conversation_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # For now accept ping messages
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(conversation_id, websocket)


@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    # Optional token query param ?token=...
    token = websocket.query_params.get("token")
    # Allow anonymous connections to notifications for dev; if token provided, verify
    if token:
        try:
            verify_jwt_from_header(token)
        except HTTPException:
            await websocket.close(code=1008)
            return
    # register under conversation_id 0 for global notifications
    await manager.connect(0, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(0, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8011)))
