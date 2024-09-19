import unittest
from utils.generator import validate_uuid, generate_uuid, generate_device_name

class TestGeneratorFunctions(unittest.TestCase):

    def test_validate_uuid(self):
        valid_uuid = "1234567890abcdef1234567890abcdef"
        invalid_uuid = "12345"
        self.assertTrue(validate_uuid(valid_uuid, 32))
        self.assertFalse(validate_uuid(invalid_uuid, 32))

    def test_generate_uuid(self):
        uuid = generate_uuid(32)
        self.assertEqual(len(uuid), 32)

    def test_generate_device_name(self):
        adjectives = ["swift", "brave"]
        animals = ["panther", "eagle"]
        device_name = generate_device_name(adjectives, animals)
        self.assertIn(device_name.split("_")[0], adjectives)
        self.assertIn(device_name.split("_")[1], animals)

if __name__ == '__main__':
    unittest.main()
