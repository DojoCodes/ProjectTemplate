import os
import requests
import yaml

DOJO_URL = "https://api.dojo.codes"
ACCOUNT_USERNAME = os.environ["DOJO_USERNAME"]
ACCOUNT_PASSWORD = os.environ["DOJO_TOKEN"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]

print("Account username", ACCOUNT_USERNAME)


def _get_token():
    token_payload = {
        "username": ACCOUNT_USERNAME,
        "token": ACCOUNT_PASSWORD,
    }
    response = requests.post(
        f"{DOJO_URL}/authentication/personal_access_token_login",
        json=token_payload,
    )
    return response.json()["access_token"]


def _check_if_challenge_already_exists(challenge_id: str):
    token = _get_token()
    challenge_already_exists_response = requests.get(
        f"{DOJO_URL}/challenge/{challenge_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if challenge_already_exists_response.status_code == 200:
        print("Challenge already exists, updating existing one...")
        return True
    elif challenge_already_exists_response.status_code == 404:
        print("Challenge id not found, creating new one...")
        return False
    else:
        raise RuntimeError(
            "Impossible to know whether the challenge already exists or not"
        )


def _fill_variables(text: str):
    text = text.replace("${github_username}", GITHUB_USERNAME)
    text = text.replace("${dojo_username}", ACCOUNT_USERNAME)
    return text


class KeyNotFound:
    pass


def update_challenge(challenge_path: str, challenge: dict):
    token = _get_token()

    challenge_id = challenge["id"]

    # Reading instructions from file
    instructions = KeyNotFound
    if "instructions" in challenge and list(challenge["instructions"]):
        instruction_filename = challenge["instructions"][
            list(challenge["instructions"])[0]
        ]
        with open(
            os.path.join(challenge_path, instruction_filename),
            encoding="utf-8",
        ) as instruction_file:
            instructions = instruction_file.read()

    # Reading checks
    checks = KeyNotFound
    if "checks" in challenge:
        if isinstance(challenge["checks"], str):
            with open(
                os.path.join(challenge_path, challenge["checks"]), encoding="utf-8"
            ) as checks_file:
                checks = yaml.load(checks_file.read(), Loader=yaml.FullLoader)
        else:
            raise RuntimeError("checks must be a string")

    # Building payload
    payload = {
        "name": challenge["name"],
        "description": challenge.get("description", KeyNotFound),
        "author": challenge.get("author", KeyNotFound),
        "difficulty": challenge.get("difficulty", KeyNotFound),
        "disabled": challenge.get("disabled", KeyNotFound),
        "instructions": instructions,
        "checks": checks,
        "environments": challenge.get("environments", KeyNotFound),
    }
    # Stripping empty keys
    payload = {key: value for key, value in payload.items() if value is not KeyNotFound}
    print("Sending payload", payload)
    response = requests.patch(
        f"{DOJO_URL}/challenge/{challenge_id}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    print(response, response.json())


def create_challenge(challenge_path: str, challenge: dict):
    token = _get_token()

    challenge_id = challenge["id"]

    # Reading instructions from file
    instructions = KeyNotFound
    if "instructions" in challenge and list(challenge["instructions"]):
        instruction_filename = challenge["instructions"][
            list(challenge["instructions"])[0]
        ]
        with open(
            os.path.join(challenge_path, instruction_filename),
            encoding="utf-8",
        ) as instruction_file:
            instructions = instruction_file.read()

    # Reading checks
    checks = KeyNotFound
    if "checks" in challenge:
        if isinstance(challenge["checks"], str):
            with open(
                os.path.join(challenge_path, challenge["checks"]), encoding="utf-8"
            ) as checks_file:
                checks = yaml.load(checks_file.read(), Loader=yaml.FullLoader)
        else:
            raise RuntimeError("checks must be a string")

    # Building payload
    payload = {
        "id": challenge_id,
        "name": challenge["name"],
        "description": challenge["description"],
        "author": challenge["author"],
        "difficulty": challenge["difficulty"],
        "disabled": challenge["disabled"],
        "instructions": instructions,
        "checks": checks,
        "environments": challenge.get("environments", KeyNotFound),
    }
    # Stripping empty keys
    payload = {key: value for key, value in payload.items() if value is not KeyNotFound}
    print("Sending payload", payload)
    response = requests.post(
        f"{DOJO_URL}/challenge",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    print(response, response.json())


def create_or_update_challenge(challenge_path: str):
    print(f"Loading challenge definition at '{challenge_path}'")
    with open(
        os.path.join(challenge_path, "challenge.yml"), encoding="utf-8"
    ) as challenge_file:
        challenge_content = challenge_file.read()
        challenge_content = _fill_variables(challenge_content)
        challenge = yaml.load(challenge_content, Loader=yaml.FullLoader)

    challenge_already_exists = _check_if_challenge_already_exists(challenge["id"])

    if challenge_already_exists:
        update_challenge(challenge_path, challenge)
    else:
        create_challenge(challenge_path, challenge)


with open("project.yml", encoding="utf-8") as project_file:
    project = yaml.load(project_file.read(), Loader=yaml.FullLoader)

print(project)
for challenge in project["challenges"]:
    create_or_update_challenge(challenge)
