from aiohttp import ClientSession


class HttpClient:
    session: ClientSession

    def start(self):
        self.session = ClientSession()

    async def stop(self):
        await self.session.close()

    def __call__(self) -> ClientSession:
        return self.session


http_client = HttpClient()
