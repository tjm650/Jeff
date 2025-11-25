
import unittest
from . import test_workflow

class TestWorkflow(unittest.TestCase):
    def test_run_workflow(self):
        self.assertEqual(test_workflow.main(), 0)
