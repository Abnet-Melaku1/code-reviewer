import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])
logger = logging.getLogger("codereviewer.api.websocket")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint that streams repository indexing and PR review progress events.

    Subscribes to the Redis pub/sub channel ``codereviewer:events`` and forwards
    all fanned-out messages directly to the client.
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    redis_client = websocket.app.state.redis_client
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("codereviewer:events")

    async def listen_to_client() -> None:
        """Continuously receive client frames to detect connection disconnects."""
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.warning(f"Error reading from WebSocket client: {e}")

    async def forward_pubsub_events() -> None:
        """Fetch messages from Redis pub/sub and send them to the connected client."""
        try:
            while True:
                # Non-blocking get_message using timeout
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                if message is not None:
                    payload = message["data"]
                    # Forward the raw JSON string published by the worker/agent
                    await websocket.send_text(payload)
                # yield control to the event loop
                await asyncio.sleep(0.05)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning(f"Error forwarding Redis events to WebSocket client: {e}")

    # Run tasks concurrently; terminate both when the client disconnects or an error occurs
    client_task = asyncio.create_task(listen_to_client())
    events_task = asyncio.create_task(forward_pubsub_events())

    try:
        await asyncio.wait(
            [client_task, events_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        client_task.cancel()
        events_task.cancel()
        try:
            await pubsub.unsubscribe("codereviewer:events")
            await pubsub.close()
        except Exception as e:
            logger.warning(f"Failed to cleanly close Redis pubsub connection: {e}")
