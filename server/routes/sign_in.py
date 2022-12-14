import secrets
from sqlalchemy.future import select
from server.config import server
from server.models import User, UserSession
from server.server_utils.db_utils import async_session
from utils.logger import logger
from utils.protocol import Message, Connection
from global_enums import Protocol, SignIn


@server.message_handler(SignIn.COMMAND.value)
async def sign_in(message: Message, connection: Connection):
    content = message.encode_content_from_json()
    logger.info(f"Sign in attempt {content.get('nickname')}, {content.get('password')}")
    async with async_session() as session, session.begin():
        user = await session.scalar(select(User).where(User.nickname == content.get("nickname")))
        if user is not None and user.password == content.get("password"):
            token = await create_session(session, user, connection)
            response = Message(
                SignIn.COMMAND.value,
                Protocol.SERVER.value,
                Protocol.CLIENT.value,
                token,
                Message.decode_content_to_json(
                    {
                        "response": SignIn.RESPONSE_SIGN_IN_SUCCESSFUL.value,
                        "nickname": user.nickname,
                        "user_id": user.id,
                    }
                ),
            )
            return await connection.send_message(response)
        elif user is not None and user.password != content.get("password"):
            response = Message(
                SignIn.COMMAND.value,
                Protocol.SERVER.value,
                Protocol.CLIENT.value,
                Protocol.EMPTY_TOKEN.value,
                Message.decode_content_to_json({"response": SignIn.RESPONSE_INCORRECT_PASSWORD.value}),
            )
            return await connection.send_message(response)
        response = Message(
            SignIn.COMMAND.value,
            Protocol.SERVER.value,
            Protocol.CLIENT.value,
            Protocol.EMPTY_TOKEN.value,
            Message.decode_content_to_json({"response": SignIn.RESPONSE_USER_NOT_FOUND.value}),
        )
        return await connection.send_message(response)


async def create_session(session: async_session, user: User, connection: Connection) -> str:
    token = secrets.token_hex(64)
    user_session = UserSession(user_id=user.id, token=token)
    session.add(user_session)
    server.sessions[user.id] = {"user_session": user_session, "user_connection": connection}
    logger.info(f"New user session: <{user.nickname}>, connection: {connection.writer.get_extra_info('peername')}")
    return token
