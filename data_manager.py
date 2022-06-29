import json


class DataManager:
    def __init__(self) -> None:
        self.data = self.read_json()

    # Returns dict with data from json file
    def read_json(self) -> dict:
        with open("projects_data.json") as readFile:
            dataFromJson = json.load(readFile)
        return dataFromJson

    # Writing information to a file
    def write_json(self):
        with open("projects_data.json", 'w') as writeFile:
            json.dump(self.data, writeFile)

    # Updating information
    def update_json(self, project, task="", name="", times={}):
        self.data = self.read_json()
        name = name.lower()
        if project not in self.data:
            self.data[project] = {}
        if task != "" and task not in self.data[project]:
            self.data[project][task] = {}
        if name != "" and name not in self.data[project][task]:
            self.data[project][task][name] = {}
        if times != {}:
            self.data[project][task][name] = times
        self.write_json()
