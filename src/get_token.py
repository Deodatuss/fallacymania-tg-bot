import os
import json


def get_token() -> str:
    script_dir = os.path.dirname(__file__)

    json_file_path = os.path.join(script_dir, "../config/token.json")

    with open(json_file_path, "r") as json_file:
        data = json.load(json_file)

    return data["token"]
