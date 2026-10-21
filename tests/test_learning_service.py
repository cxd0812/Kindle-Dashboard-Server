import datetime as dt
import tempfile
import unittest
from pathlib import Path

import learning_service


class LearningServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_file = Path(self.temp_dir.name) / "school.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_thursday_plan_adds_course_supplies_and_pinyin(self):
        target = dt.date(2026, 10, 22)
        settings = learning_service.get_settings(target, self.data_file)
        learning_service.save_settings({
            "schedule": settings["schedule"],
            "homework": "读课文第6课两遍\n完成数学练习册第12页",
            "extras": "水壶\n红领巾",
        }, target, self.data_file)

        plan = learning_service.get_plan(target, self.data_file)

        self.assertEqual(plan["weekday"], "星期四")
        self.assertIn("尤克里里", plan["carry"])
        self.assertEqual(plan["carry"][:4], ["数学课本", "数学作业", "语文课本", "语文作业"])
        self.assertEqual(plan["carry"][-2:], ["水壶", "红领巾"])
        self.assertEqual(plan["homework"][0]["text"], "读课文第6课两遍")
        self.assertEqual(plan["homework"][0]["pinyin"], "dú kè wén dì liù kè liǎng biàn")
        self.assertEqual(plan["homework"][1]["pinyin"], "wán chéng shù xué liàn xí cè dì shí èr yè")

    def test_art_course_adds_art_supplies(self):
        target = dt.date(2026, 10, 23)
        plan = learning_service.get_plan(target, self.data_file)
        self.assertIn("美术工具", plan["carry"])


if __name__ == "__main__":
    unittest.main()
