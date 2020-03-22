import asyncio


class MpdIo:
    def __init__(self, host, port=6600):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.scheduled_ping = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        line = await self._read_ok()
        if 'OK MPD' in line:
            self.scheduled_ping = asyncio.create_task(self._schedule_ping())
            return self
        return None

    async def _schedule_ping(self):
        return
        # while True:
        #     await self.ping()
        #     await asyncio.sleep(5)

    async def ping(self):
        self.writer.write('ping\n'.encode('utf-8'))
        await self.writer.drain()
        response = await self.reader.readline()
        response = response.decode('utf-8')
        return response

    async def status(self):
        self.writer.write('status\n'.encode())
        await self.writer.drain()
        response = await self.reader.read(2048)
        response = response.decode('utf-8')
        return MpdIo._parse_status(response)

    @staticmethod
    def _decode(s):
        return s.decode('utf-8')

    @staticmethod
    def _parse_status(response):
        parts = response.split('\n')
        d = {}
        for part in parts:
            if 'OK' != part:
                a = part.split(': ')
                if len(a) > 1:
                    k, v = a
                    d[k] = v
        return d

    async def _read_ok(self):
        line = await self.reader.readline()
        return line.decode('utf-8')


async def main():
    client = await MpdIo('localhost').connect()
    status = await client.status()
    print(status)


if __name__ == '__main__':
    asyncio.run(main())
