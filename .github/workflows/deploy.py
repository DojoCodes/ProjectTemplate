import yaml


def create_or_update_challenge(challenge_path: str):
    print(f"Loading challenge definition at '{challenge_path}'")


project = yaml.load("project.yml")

for challenge in project["challenges"]:
    create_or_update_challenge(challenge)
