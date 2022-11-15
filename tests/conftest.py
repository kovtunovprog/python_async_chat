import asyncio
import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()


@pytest.fixture
def generate_valid_login():
    pass


@pytest.fixture
def generate_valid_pw():
    import secrets
    import string

    legacy_chars = string.ascii_letters
    password = "".join(secrets.choice(legacy_chars) for i in range(20))
    return password


def generate_wrong_login_list():
    import secrets
    import string

    legacy_chars = string.ascii_letters
    invalid_login = []
    for max_symbols in [3, 10, 17]:
        invalid_login.append("".join(secrets.choice(legacy_chars) for i in range(max_symbols)))
    invalid_login[1] = " " + invalid_login[1]
    return invalid_login


invalid_logins = generate_wrong_login_list()


@pytest.fixture(params=invalid_logins)
def get_invalid_login(request):
    return request.param


@pytest_asyncio.fixture(scope="module")
async def client():
    from client.client import ChatClient

    test_client = ChatClient("localhost", 5050)
    asyncio.create_task(test_client.quick_start())
    await asyncio.sleep(1)
    yield test_client
    await test_client.disconnect()


@pytest_asyncio.fixture
async def session():
    from server.server_utils.db_utils import async_session

    async with async_session() as session, session.begin():
        yield session


@pytest.fixture
def generate_correct_login_and_pw():
    import secrets
    import string

    legacy_chars = string.ascii_letters
    login = "".join(secrets.choice(legacy_chars) for i in range(10))
    password = "".join(secrets.choice(legacy_chars) for i in range(20))
    return login, password


@pytest.fixture
def generate_incorrect_password(generate_correct_login_and_pw):
    login, password = generate_correct_login_and_pw
    return login, f"  {password}"


@pytest.fixture
def generate_incorrect_login(generate_correct_login_and_pw):
    login, password = generate_correct_login_and_pw
    return f"  {login}", password


@pytest_asyncio.fixture
async def generate_user_in_db(generate_correct_login_and_pw):
    from server.models import User
    from server.server_utils.db_utils import async_session

    login, password = generate_correct_login_and_pw
    user = User(nickname=login, password=password)
    async with async_session() as user_session, user_session.begin():
        user_session.add(user)
    yield login, password
    async with async_session() as user_session, user_session.begin():
        await user_session.delete(user)


@pytest_asyncio.fixture
async def create_user_session(client, generate_user_in_db):
    login, password = generate_user_in_db
    data = {"nickname": login, "password": password}
    response = await client.sign_in(data)
    content = response.encode_content_from_json()
    client.token = response.token
    client.user_id = content.get("user_id")
    return client
