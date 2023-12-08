from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

from server.conference.exceptions import (
    ForbiddenConferenceActionError,
    ConferenceValidationError,
)

from server.conference.message_coding.base_message_coder import BaseMessageCoder
from server.conference.conference import Conference, ConferenceMember
from server.conference.constants import MemberRole
from server.conference.member_connections import (
    MemberConnectionsPool,
    BaseMemberConnection,
    MemberConnectionClosed,
)
from server.conference.messages import (
    BaseConferenceMessage,
    BaseClientMessage,
    WriteCanvasMessage,
    FullCanvasMessage,
    MemberInfoMessage,
)


class ConferenceController:
    conference: Conference
    message_coding: BaseMessageCoder
    connections_pool: MemberConnectionsPool
    is_owner_role_vacant: bool
    is_alive: bool

    def __init__(self, message_coding: BaseMessageCoder, conference: Conference):
        self.message_coding = message_coding
        self.connections_pool = MemberConnectionsPool()
        self.is_owner_role_vacant = True
        self.is_alive = True
        self.conference = conference

    @property
    def conference_id(self):
        return self.conference.id

    async def broadcast_message(self, message: BaseConferenceMessage):
        encoded_message = self.message_coding.encode_message(message)
        for reciever in message.recievers:
            connection = self.connections_pool.get_connection(reciever.id)
            await connection.send_text(encoded_message)

    async def on_connect(self, connection: BaseMemberConnection) -> ConferenceMember:
        self.conference.poke()

        if self.is_owner_role_vacant:
            role = MemberRole.OWNER
        else:
            role = MemberRole.PARTICIPANT
        new_member = self.conference.create_member(role)
        if self.is_owner_role_vacant:
            new_member.canvas.set_visibility_role(MemberRole.LISTENER)
        self.is_owner_role_vacant = False

        self.connections_pool.add_connection(id=new_member.id, connection=connection)

        welcoming_message = MemberInfoMessage(
            recievers=(new_member,),  # NOTE: May change to iter_all_members()
            conference=self.conference,
            member=new_member,
        )
        await self.broadcast_message(welcoming_message)

        for canvas in self.conference.iter_all_canvases():
            if canvas.check_view_permission(member=new_member):
                canvas_message = FullCanvasMessage(
                    recievers=(new_member,),
                    conference=self.conference,
                    target_canvas=canvas,
                )
                await self.broadcast_message(canvas_message)

        if self.conference.check_canvas_owning_right(new_member):
            my_canvas_message = FullCanvasMessage(
                recievers=self.conference.iter_all_members(exclude=[new_member]),
                conference=self.conference,
                target_canvas=new_member.canvas,
            )
            await self.broadcast_message(my_canvas_message)

        return new_member

    async def on_disconnect(self, member: ConferenceMember):
        self.conference.poke()
        self.connections_pool.remove_connection(member.id)
        if not self.conference.is_active():
            self.is_alive = False

    async def on_message(self, message: BaseClientMessage):
        self.conference.poke()
        match message:
            case WriteCanvasMessage():
                try:
                    self.conference.write_canvas(
                        sender=message.sender,
                        canvas=message.target_canvas,
                        new_data=message.data_override,
                    )
                except ForbiddenConferenceActionError:
                    # TODO: Handle forbidden action
                    return
                response_message = FullCanvasMessage(
                    recievers=self.conference.iter_canvas_viewers(
                        message.target_canvas,
                        exclude=[
                            message.sender,
                        ],
                    ),
                    conference=self.conference,
                    target_canvas=message.target_canvas,
                )
                await self.broadcast_message(response_message)
            case _:
                pass

    def should_be_terminated(self, timestamp: datetime | None = None) -> bool:
        return not (self.is_alive and self.conference.is_active(timestamp))

    async def run_connection_loop(self, connection: BaseMemberConnection):
        member = await self.on_connect(connection)
        try:
            while True:
                data = await connection.receive_text()
                try:
                    message = self.message_coding.decode_message(
                        message_str=data, sender=member, conference=self.conference
                    )
                    await self.on_message(message)
                except ConferenceValidationError:
                    # TODO: Handle invalid data
                    continue
        except MemberConnectionClosed:
            await self.on_disconnect(member)