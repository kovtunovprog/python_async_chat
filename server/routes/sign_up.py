from sqlalchemy.future import select
from server.config import server
from server.server_utils.db_utils import async_session
from server.models.user import User
from utils.protocol import Message, Connection
from utils.logger import logger
from global_enums import SignUP, Protocol


@server.message_handler(SignUP.COMMAND.value)
async def sign_up(message: Message, connection: Connection):
    content = message.encode_content_from_json()
    logger.info(f"Sign up attempt {content.get('nickname'), content.get('password'), content.get('email')}")
    nickname_credentials, password_credentials = check_nickname_password_credentials(
        content.get("nickname"), content.get("password")
    )
    if nickname_credentials is not True:
        return await handle_response(
            SignUP.RESPONSE_INVALID_NICKNAME.value,
            connection,
        )
    if password_credentials is not True:
        return await handle_response(
            SignUP.RESPONSE_INVALID_PASSWORD.value,
            connection,
        )
    async with async_session() as session, session.begin():
        user = await session.scalar(select(User).where(User.nickname == content.get("nickname")))
        if user is not None:
            return await handle_response(SignUP.RESPONSE_LOGIN_EXISTS.value, connection, session)
        else:
            return await handle_response(SignUP.RESPONSE_REGISTRATION_SUCCESS.value, connection, session, content)


def check_nickname_password_credentials(nickname: str, password: str):
    nickname_result = (
        4 <= len(nickname) <= 16 and (nickname.isascii() is True and nickname.isalpha() is True) and nickname[0] != " "
    ) and True
    password_result = (len(password) <= 50 and password.isascii() is True and password[0] != " ") and True
    return nickname_result, password_result


async def add_user_to_db(content: dict, session, connection: Connection):
    user = User(
        nickname=content.get("nickname"),
        password=content.get("password"),
        email=content.get("email"),
    )
    session.add(user)
    logger.info(
        f"New user was registered: <{user.nickname}>, connection: {connection.writer.get_extra_info('peername')}"
    )


async def handle_response(
    response_text: str,
    connection: Connection,
    session: async_session = None,
    content: dict = None,
):
    response = Message(
        SignUP.COMMAND.value,
        Protocol.SERVER.value,
        Protocol.CLIENT.value,
        Protocol.EMPTY_TOKEN.value,
        Message.decode_content_to_json({"response": response_text}),
    )
    if response_text == SignUP.RESPONSE_REGISTRATION_SUCCESS.value:
        await add_user_to_db(content, session, connection)
    return await connection.send_message(response)
