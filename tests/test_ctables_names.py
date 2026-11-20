# Mario Kart DS Modding Trove
# tests/test_ctables_names.py — enum-name lookup for generated tables
# SPDX-License-Identifier: MIT
import unittest

from tools.ctables.common.cnames import enum_name


class EnumNameTests(unittest.TestCase):
    def test_race_course_names(self):
        self.assertEqual(enum_name("MkdsRaceCourse", 20),
                         "MKDS_RACE_COURSE_FIGURE_8_CIRCUIT")
        self.assertEqual(enum_name("MkdsRaceCourse", 29),
                         "MKDS_RACE_COURSE_RAINBOW_ROAD")
        self.assertEqual(enum_name("MkdsRaceCourse", 1),
                         "MKDS_RACE_COURSE_GCN_YOSHI_CIRCUIT")

    def test_kart_names(self):
        self.assertEqual(enum_name("MkdsKart", 0), "MKDS_KART_STANDARD_MR")
        self.assertEqual(enum_name("MkdsKart", 21), "MKDS_KART_STANDARD_BW")
        self.assertEqual(enum_name("MkdsKart", 35), "MKDS_KART_ROB_LGS")

    def test_character_and_nkm_names(self):
        self.assertEqual(enum_name("MkdsCharacter", 12),
                         "MKDS_CHARACTER_SHY_GUY")
        self.assertEqual(enum_name("NkmAreaShape", 0),
                         "NKM_AREA_SHAPE_BOX")
        self.assertEqual(enum_name("NkmCameraType", 0),
                         "NKM_CAMERA_FIXED_LOOK_DRIVER")

    def test_unknown_value_is_not_invented(self):
        self.assertIsNone(enum_name("MkdsRaceCourse", 200))
        self.assertIsNone(enum_name("NoSuchEnum", 0))


if __name__ == "__main__":
    unittest.main()
