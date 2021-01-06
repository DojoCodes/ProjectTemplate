import os
import requests
import yaml

DOJO_URL = "https://api.dojo.codes"
ACCOUNT_USERNAME = os.environ["DOJO_USERNAME"]
ACCOUNT_PASSWORD = os.environ["DOJO_TOKEN"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]


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


def create_or_update_challenge(challenge_path: str):
    print(f"Loading challenge definition at '{challenge_path}'")
    with open(
        os.path.join(challenge_path, "challenge.yml"), encoding="utf-8"
    ) as challenge_file:
        challenge_content = challenge_file.read()
        challenge_content = _fill_variables(challenge_content)
        challenge = yaml.load(challenge_content, Loader=yaml.FullLoader)

    challenge_id = challenge["id"].strip()
    challenge_already_exists = _check_if_challenge_already_exists(challenge_id)

    if challenge_already_exists:
        challenge_requests_method = requests.patch
        challenge_requests_url = f"{DOJO_URL}/challenge/{challenge_id}"
        required_fields = ["id", "name"]
    else:
        challenge_requests_method = requests.post
        challenge_requests_url = f"{DOJO_URL}/challenge"
        required_fields = [
            "id",
            "name",
            "description",
            "author",
            "difficulty",
            "disabled",
            "instructions",
        ]

    token = _get_token()

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
        key: (
            challenge[key]
            if key in required_fields
            else challenge.get(key, KeyNotFound)
        )
        for key in challenge.keys()
    }
    payload["instructions"] = instructions
    payload["checks"] = checks

    # Stripping empty keys
    payload = {key: value for key, value in payload.items() if value is not KeyNotFound}

    # Sending payload
    print("Sending payload", payload)
    response = challenge_requests_method(
        challenge_requests_url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    print(response, response.json())


with open("project.yml", encoding="utf-8") as project_file:
    project = yaml.load(project_file.read(), Loader=yaml.FullLoader)

print(project)
for challenge in project["challenges"]:
    create_or_update_challenge(challenge)
