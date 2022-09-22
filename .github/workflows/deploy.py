import os
import requests
import yaml

DOJO_URL = os.environ.get("DOJO_API_URL", "https://api.dojo.codes")
ACCOUNT_USERNAME = os.environ["DOJO_USERNAME"]
ACCOUNT_PASSWORD = os.environ["DOJO_TOKEN"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]


def make_custom_yaml_loader_for(file_path: str):
    """
    Returns a yaml loader that can read arbitrary files relative to the
    given *file_path*.
    """
    # Used in the custom constructor below to find relative files
    # to that input file.
    file_dir = os.path.dirname(file_path)

    def yaml_read_file_tag(loader: yaml.Loader, node):
        relative_file_path = loader.construct_scalar(node)
        if not isinstance(relative_file_path, str):
            raise yaml.MarkedYAMLError(
                problem="Must be a string", problem_mark=node.start_mark
            )
        full_file_path = os.path.join(file_dir, relative_file_path)
        if not os.path.exists(full_file_path):
            raise yaml.MarkedYAMLError(
                problem=f"File '{full_file_path}' does not exist",
                problem_mark=node.start_mark,
            )
        with open(full_file_path, encoding="utf-8") as f:
            return f.read()

    # Let's make a new loader on purpose so we don't have to modify
    # the builtin loader. Which would not make sense since the custom
    # constructor is bound to a local var of _this_ maker function.
    class LoaderForThatFile(yaml.SafeLoader):
        pass

    LoaderForThatFile.add_constructor("!read_text_file", yaml_read_file_tag)
    return LoaderForThatFile


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


def _check_if_environment_already_exists(environment_id: str):
    token = _get_token()
    environment_already_exists_response = requests.get(
        f"{DOJO_URL}/environments/{environment_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if environment_already_exists_response.status_code == 200:
        print("Environment already exists, updating existing one...")
        return True
    elif environment_already_exists_response.status_code == 404:
        print("Environment id not found, creating new one...")
        return False
    else:
        raise RuntimeError(
            "Impossible to know whether the environment already exists or not"
        )


def _check_if_campaign_already_exists(campaign_route_name: str):
    token = _get_token()
    campaign_already_exists_response = requests.get(
        f"{DOJO_URL}/route/campaign/{campaign_route_name}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if campaign_already_exists_response.status_code == 200:
        print("Campaign already exists, updating existing one...")
        return True, campaign_already_exists_response.json()["id"]
    elif campaign_already_exists_response.status_code == 404:
        print("Campaign id not found, creating new one...")
        return False, None
    else:
        raise RuntimeError(
            "Impossible to know whether the campaign already exists or not"
        )


def _check_if_score_rule_already_exists(rule_id: str):
    token = _get_token()
    rule_already_exists_response = requests.get(
        f"{DOJO_URL}/scoring/rule/{rule_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if rule_already_exists_response.status_code == 200:
        print("Rule already exists, updating existing one...")
        return True
    elif rule_already_exists_response.status_code == 404:
        print("Rule id not found, creating new one...")
        return False
    else:
        raise RuntimeError("Impossible to know whether the rule already exists or not")


def _check_if_scoreboard_already_exists(scoreboard_id: str):
    token = _get_token()
    scoreboard_already_exists_response = requests.get(
        f"{DOJO_URL}/scoring/scoreboard/{scoreboard_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if scoreboard_already_exists_response.status_code == 200:
        print("Scoreboard already exists, updating existing one...")
        return True
    elif scoreboard_already_exists_response.status_code == 404:
        print("Scoreboard not found, creating new one...")
        return False
    else:
        raise RuntimeError(
            "Impossible to know whether the scoreboard already exists or not"
        )


def _fill_variables(text: str):
    text = text.replace("${github_username}", GITHUB_USERNAME)
    text = text.replace("${dojo_username}", ACCOUNT_USERNAME)
    return text


class KeyNotFound:
    pass


def create_or_update_challenge(challenge: dict):
    challenge_id = challenge["id"].strip()
    challenge_environments = challenge.get("environments", [])
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
    environments_variations = {}
    for environment in challenge_environments:
        variations = requests.get(
            f'{DOJO_URL}/environments?filter=id[startswith]"{environment}::"&only_visible=false',
            headers={"Authorization": f"Bearer {token}"},
        ).json()["environments"]
        variations = [variation["id"] for variation in variations]
        environments_variations[environment] = variations

    for environment_name, variations in environments_variations.items():
        if variations:
            challenge["environments"].remove(environment_name)
            challenge["environments"] += variations

    # Building payload
    payload = {
        key: (
            challenge[key]
            if key in required_fields
            else challenge.get(key, KeyNotFound)
        )
        for key in challenge.keys()
    }

    # Stripping empty keys
    payload = {key: value for key, value in payload.items() if value is not KeyNotFound}

    # Sending payload
    response = challenge_requests_method(
        challenge_requests_url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    if response.ok:
        pass
    else:
        raise RuntimeError(
            f"Could not create or edit challenge : {response} ({response.text})"
        )


def read_checks(checks_filepath: str):
    with open(checks_filepath, encoding="utf-8") as checks_file:
        yaml_loader = make_custom_yaml_loader_for(checks_filepath)
        checks: dict = yaml.load(checks_file.read(), Loader=yaml_loader)

    # basic validation
    for check_id, check in checks.items():
        if check.get("name") is None:
            if check.get("visible") is True:
                raise RuntimeError(
                    f"Check '{check_id}': visible check should have a name"
                )
            else:
                # It is a private check, we don't need a human name
                check["name"] = check_id

    return checks


def read_challenge(challenge_dir: str):
    challenge_filepath = os.path.join(challenge_dir, "challenge.yml")
    print(f"Reading challenge definition at '{challenge_filepath}'")
    with open(challenge_filepath, encoding="utf-8") as challenge_file:
        challenge_content = challenge_file.read()
        challenge_content = _fill_variables(challenge_content)
        yaml_loader = make_custom_yaml_loader_for(challenge_filepath)
        challenge = yaml.load(challenge_content, Loader=yaml_loader)

    assert isinstance(challenge["id"], str)

    # Reading instructions from file
    instructions = KeyNotFound
    if "instructions" in challenge and list(challenge["instructions"]):
        # NOTE: we take the first one for now
        instructions = challenge["instructions"][list(challenge["instructions"])[0]]
    challenge["instructions"] = instructions  # overwrite with real data

    # Reading checks
    checks = KeyNotFound
    if "checks" in challenge:
        assert isinstance(
            challenge["checks"], str
        ), "checks must be a string (a relative path)"
        checks_filepath = os.path.join(challenge_dir, challenge["checks"])
        checks = read_checks(checks_filepath=checks_filepath)
    challenge["inputs"] = checks  # overwrite with real data
    return challenge


def read_environment(environment_dir: str):
    environment_filepath = os.path.join(environment_dir, "environment.yml")
    print(f"Reading environment definition at '{environment_filepath}'")
    with open(environment_filepath, encoding="utf-8") as environment_file:
        environment_content = environment_file.read()
        environment_content = _fill_variables(environment_content)
        yaml_loader = make_custom_yaml_loader_for(environment_filepath)
        environment = yaml.load(environment_content, Loader=yaml_loader)

    assert isinstance(environment["id"], str)

    return environment


def read_scoreboard(scoreboard_path: str):
    print(f"Reading scoreboard definition at '{scoreboard_path}'")
    with open(scoreboard_path, encoding="utf-8") as scoreboard_file:
        scoreboard_content = scoreboard_file.read()
        yaml_loader = make_custom_yaml_loader_for(scoreboard_path)
        scoreboard = yaml.load(scoreboard_content, Loader=yaml_loader)

    assert isinstance(scoreboard["id"], str)

    return scoreboard


def read_project():
    with open("project.yml", encoding="utf-8") as project_file:
        project = yaml.load(project_file.read(), Loader=yaml.SafeLoader)

    # Read challenges content
    challenges = [
        read_challenge(challenge_dir=challenge_dir)
        for challenge_dir in project.get("challenges", [])
    ]
    project["challenges"] = challenges

    # Read environments content
    environments = [
        read_environment(environment_dir=environment_dir)
        for environment_dir in project.get("environments", [])
    ]
    project["environments"] = environments

    scoreboards = [
        read_scoreboard(scoreboard_path=scoreboard_path)
        for scoreboard_path in project.get("scoreboards", [])
    ]
    project["scoreboards"] = scoreboards

    return project


def create_or_update_environment(environment: dict):
    token = _get_token()

    if environment["base_environment"] == "*":
        environment_list = requests.get(
            f"{DOJO_URL}/environments",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["environments"]
        environment_list = [env["id"] for env in environment_list]
        print()
    elif isinstance(environment["base_environment"], list):
        environment_list = environment["base_environment"]
    else:
        environment_list = [environment["base_environment"]]

    environment_name = environment["name"]
    for base_environment in environment_list:
        if environment["name"] == "$base_environment":
            environment_name = requests.get(
                f"{DOJO_URL}/environments/{base_environment}",
                headers={"Authorization": f"Bearer {token}"},
            ).json()["name"]
        environment_id = environment["id"].strip()
        if len(environment_list) > 1:
            environment_id = f"{environment_id}::{base_environment}"
        environment_already_exists = _check_if_environment_already_exists(
            environment_id
        )

        if environment_already_exists:
            environment_requests_method = requests.patch
            environment_requests_url = f"{DOJO_URL}/environments/{environment_id}"
            required_fields = ["id", "name"]
        else:
            environment_requests_method = requests.post
            environment_requests_url = f"{DOJO_URL}/environments"
            required_fields = [
                "id",
                "name",
                "description",
                "base_environment",
                "injection_method",
                "visible",
                "code",
                "interpret_as",
            ]
        environment_copy = environment.copy()
        environment_copy["id"] = environment_id
        environment_copy["base_environment"] = base_environment
        environment_copy["name"] = environment_copy["name"].replace(
            "$base_environment", environment_name
        )
        environment_copy["interpret_as"] = environment_copy["interpret_as"].replace(
            "$base_environment", base_environment
        )
        # Building payload
        payload = {
            key: (
                environment_copy[key]
                if key in required_fields
                else environment_copy.get(key, KeyNotFound)
            )
            for key in environment_copy.keys()
        }

        # Stripping empty keys
        payload = {
            key: value for key, value in payload.items() if value is not KeyNotFound
        }

        # Sending payload
        print("Sending payload", payload)
        response = environment_requests_method(
            environment_requests_url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        if response.ok:
            print(response, response.json())
        else:
            raise RuntimeError(
                f"Could not create or edit environment : {response} ({response.text})"
            )


def create_or_update_campaign(campaign_id: str, campaign: dict):
    campaign["id"] = campaign_id
    campaign_route_name = campaign["route_name"].strip()
    campaign_already_exists, campaign_id = _check_if_campaign_already_exists(
        campaign_route_name
    )

    if campaign_already_exists:
        campaign_requests_method = requests.patch
        campaign_requests_url = f"{DOJO_URL}/campaign/{campaign_id}"
        required_fields = ["route_name"]
    else:
        campaign_requests_method = requests.post
        campaign_requests_url = f"{DOJO_URL}/campaign"
        required_fields = [
            "route_name",
            "name",
            "description",
            "mode",
            "challenge_selection_mode",
        ]

    token = _get_token()

    # Building payload
    payload = {
        key: (
            campaign[key] if key in required_fields else campaign.get(key, KeyNotFound)
        )
        for key in campaign.keys()
    }

    # Stripping empty keys
    payload = {key: value for key, value in payload.items() if value is not KeyNotFound}
    if "start_date" in payload:
        payload["start_date"] = payload["start_date"].isoformat() if payload["start_date"] else None
    if "expiration_date" in payload:
        payload["expiration_date"] = payload["expiration_date"].isoformat() if payload["end_date"] else None

    # Sending payload
    print("Sending payload", payload)
    response = campaign_requests_method(
        campaign_requests_url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    if response.ok:
        print(response, response.json())
    else:
        raise RuntimeError(
            f"Could not create or edit campaign : {response} ({response.text})"
        )


def create_or_update_score_rule(rule_id: str, rule: dict):
    rule_already_exists = _check_if_score_rule_already_exists(rule_id)

    token = _get_token()

    payload = None
    if rule_already_exists:
        response = requests.delete(
            f"{DOJO_URL}/scoring/rule/{rule_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
    rule_requests_method = requests.post
    rule_requests_url = f"{DOJO_URL}/scoring/rule"
    payload = {"id": rule_id, "name": rule["name"], "rule": rule}

    # Sending payload
    print("Sending payload", payload)
    response = rule_requests_method(
        rule_requests_url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    if response.ok:
        print(response, response.json())
    else:
        raise RuntimeError(
            f"Could not create or edit rule : {response} ({response.text})"
        )


def create_or_update_scoreboard(scoreboard: dict):
    for rule_id, rule in scoreboard["rules"].items():
        create_or_update_score_rule(rule_id, rule)
    scoreboard_already_exists = _check_if_scoreboard_already_exists(scoreboard["id"])

    token = _get_token()
    if scoreboard_already_exists:
        response = requests.delete(
            f"{DOJO_URL}/scoring/scoreboard/{scoreboard['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()

    scoreboard_requests_method = requests.post
    scoreboard_requests_url = f"{DOJO_URL}/scoring/scoreboard"
    required_fields = ["id"]
    scoreboard["rules"] = list(scoreboard["rules"].keys())

    # Building payload
    payload = {
        key: (
            scoreboard[key]
            if key in required_fields
            else scoreboard.get(key, KeyNotFound)
        )
        for key in scoreboard.keys()
    }

    # Stripping empty keys
    payload = {key: value for key, value in payload.items() if value is not KeyNotFound}

    # Sending payload
    print("Sending payload", payload)
    response = scoreboard_requests_method(
        scoreboard_requests_url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    if response.ok:
        print(response, response.json())
    else:
        raise RuntimeError(
            f"Could not create or edit scoreboard : {response} ({response.text})"
        )


def add_campaign_associated_scoreboard(campaign_id: str, scoreboard_id: str):
    token = _get_token()
    requests.patch(
        f"{DOJO_URL}/campaign/{campaign_id}",
        json={"associated_scoreboard": scoreboard_id},
        headers={"Authorization": f"Bearer {token}"},
    )


def main():
    project = read_project()
    for environment in project["environments"]:
        create_or_update_environment(environment=environment)
    for challenge in project["challenges"]:
        create_or_update_challenge(challenge=challenge)
    deferred_campaign_scoreboard_association = {}
    for campaign_id, campaign in project["campaigns"].items():
        if "associated_scoreboard" in campaign:
            deferred_campaign_scoreboard_association[campaign_id] = campaign.pop(
                "associated_scoreboard"
            )
        create_or_update_campaign(campaign_id=campaign_id, campaign=campaign)
    for scoreboard in project["scoreboards"]:
        create_or_update_scoreboard(scoreboard=scoreboard)
    for campaign_id, scoreboard_id in deferred_campaign_scoreboard_association.items():
        add_campaign_associated_scoreboard(campaign_id, scoreboard_id)


if __name__ == "__main__":
    main()
