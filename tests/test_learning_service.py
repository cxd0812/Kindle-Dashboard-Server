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
        self.assertEqual(plan["carry"][:4], ["带数学课本", "带数学作业", "带语文课本", "带语文作业"])
        self.assertEqual(plan["carry"][-2:], ["水壶", "红领巾"])
        self.assertEqual(plan["homework"][0]["text"], "读课文第6课两遍")
        self.assertEqual(plan["homework"][0]["pinyin"], "dú kè wén dì liù kè liǎng biàn")
        self.assertEqual(plan["homework"][1]["pinyin"], "wán chéng shù xué liàn xí cè dì shí èr yè")

    def test_art_course_adds_art_supplies(self):
        target = dt.date(2026, 10, 23)
        plan = learning_service.get_plan(target, self.data_file)
        self.assertIn("美术工具", plan["carry"])

    def test_readings_align_with_characters_and_numeric_groups(self):
        item = learning_service.homework_items("朗读第12页，读两遍")[0]
        self.assertEqual("".join(unit["text"] for unit in item["ruby"]), item["text"])
        self.assertEqual(next(unit["reading"] for unit in item["ruby"] if unit["text"] == "12"), "shí èr")
        self.assertEqual(next(unit["reading"] for unit in item["ruby"] if unit["text"] == "，"), "")
        manual = learning_service.homework_items("dú shū|读书")[0]
        self.assertEqual([unit["reading"] for unit in manual["ruby"]], ["dú", "shū"])

    def test_missing_target_homework_keeps_last_entry(self):
        first = dt.date(2026, 10, 22)
        later = dt.date(2026, 10, 23)
        settings = learning_service.get_settings(first, self.data_file)
        learning_service.save_settings({
            "schedule": settings["schedule"],
            "homework": "完成数学作业",
            "extras": "",
        }, first, self.data_file)
        later_settings = learning_service.get_settings(later, self.data_file)
        self.assertEqual(later_settings["homework"], "完成数学作业")
        later_plan = learning_service.get_plan(later, self.data_file)
        self.assertEqual(later_plan["homework"][0]["text"], "完成数学作业")

    def test_missing_target_carry_keeps_last_entry(self):
        first = dt.date(2026, 10, 22)
        later = dt.date(2026, 10, 23)
        settings = learning_service.get_settings(first, self.data_file)
        learning_service.save_settings({
            "schedule": settings["schedule"],
            "homework": "",
            "extras": "水杯\n跳绳",
        }, first, self.data_file)
        plan = learning_service.get_plan(later, self.data_file)
        self.assertEqual(plan["carry"][-2:], ["水杯", "跳绳"])

    def test_papers_generate_subject_reminders_and_preserve_free_text(self):
        target = dt.date(2026, 10, 22)
        settings = learning_service.get_settings(target, self.data_file)
        learning_service.save_settings({"schedule": settings["schedule"],
            "homework": "语文：完成试卷\n订正小卷\n数学：完成卷子\n科学：完成小卷",
            "extras": "天气冷，穿厚衣服"}, target, self.data_file)
        carry = learning_service.get_plan(target, self.data_file)["carry"]
        for item in ["带语文作业", "带数学作业", "带语文小卷", "带数学小卷", "带科学小卷", "天气冷，穿厚衣服"]:
            self.assertIn(item, carry)
        self.assertEqual(carry.count("带语文小卷"), 1)
        self.assertEqual(learning_service.get_plan(target + dt.timedelta(days=1), self.data_file)["carry"], carry)


if __name__ == "__main__":
    unittest.main()
