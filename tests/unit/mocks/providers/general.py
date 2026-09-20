import uuid

from dishka import Provider, Scope, provide

from core.types import IntId


class MockGeneralProvider(Provider):
    def __init__(self, uuid_: uuid.UUID | None = None) -> None:
        super().__init__()
        self.uuid_ = uuid_ or uuid.uuid4()

    @provide(scope=Scope.APP)
    async def provide_random_uuid(self) -> uuid.UUID:
        return self.uuid_

    @provide(scope=Scope.APP)
    async def provide_random_int(self) -> IntId:
        return IntId(int(self.uuid_.hex[:15], 16))
