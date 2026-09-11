"""Bound request bodies before FastAPI materializes JSON, including chunked bodies."""
from starlette.responses import JSONResponse
from threading import BoundedSemaphore


class ChatAdmissionLimit:
    """One process: reject excess costly generations while keeping health/auth usable."""
    def __init__(self, app, maximum=4):
        if not 1 <= maximum <= 64:
            raise ValueError('NEXUS_MAX_CONCURRENT_CHATS must be between 1 and 64')
        self.app = app
        self.slots = BoundedSemaphore(maximum)

    async def __call__(self, scope, receive, send):
        costly = (scope['type'] == 'http' and scope['method'] == 'POST'
                  and scope['path'].endswith(('/messages', '/messages/stream')))
        if not costly:
            return await self.app(scope, receive, send)
        if not self.slots.acquire(blocking=False):
            return await JSONResponse({'detail': 'All chat workers are busy. Please try again shortly.'},
                                      status_code=429, headers={'Retry-After': '5'})(scope, receive, send)
        try:
            await self.app(scope, receive, send)
        finally:
            self.slots.release()


class RequestBodyLimit:
    def __init__(self, app, max_bytes=64 * 1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in {'POST', 'PUT', 'PATCH'}:
            return await self.app(scope, receive, send)
        # RAG requires a larger bounded body; ordinary API calls do not.
        limit = self.max_bytes if '/admin/rag/documents' in scope['path'] else 256 * 1024
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body', b''))
            if size > limit:
                response = JSONResponse({'detail': 'Request body is too large.'}, status_code=413)
                return await response(scope, receive, send)
            chunks.append(message)
            if not message.get('more_body', False):
                break
        iterator = iter(chunks)

        async def replay():
            return next(iterator, None) or await receive()

        await self.app(scope, replay, send)
