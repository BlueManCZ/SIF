import json
import unittest

DATABASE_FILE = "database.json"


class DatabaseValidity(unittest.TestCase):
    with open(DATABASE_FILE) as json_file:
        database = json.load(json_file)

    def test_database_structure(self):
        self.assertEqual(self.database.keys(), {"wm_classes", "wm_names"})

    def test_database_sorted(self):
        keys = list(map(lambda x: int(x), self.database["wm_classes"].keys()))
        sorted_keys = sorted(keys)

        self.assertEqual(keys, sorted_keys)

        keys = list(map(lambda x: int(x), self.database["wm_names"].keys()))
        sorted_keys = sorted(keys)

        self.assertEqual(keys, sorted_keys)


if __name__ == "__main__":
    unittest.main()
