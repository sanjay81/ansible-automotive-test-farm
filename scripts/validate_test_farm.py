#!/usr/bin/env python3
"""Validate a simulated automotive Linux test farm."""
import argparse
import hashlib
import json
import shutil
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--image', required=True)
    p.add_argument('--device', required=True)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--xml', required=True)
    p.add_argument('--min-free-mb', type=int, default=10)
    return p.parse_args()


def build_tests(args):
    class TestFarmValidation(unittest.TestCase):
        def test_workspace_exists(self):
            self.assertTrue(Path(args.workspace).is_dir(), 'Missing test-farm workspace')

        def test_adb_installed(self):
            self.assertIsNotNone(shutil.which('adb'), 'adb executable not on PATH')

        def test_firmware_checksum(self):
            image = Path(args.image)
            self.assertTrue(image.is_file(), f'Firmware not found: {image}')
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            self.assertEqual(digest, args.expected_sha256.lower(), 'Firmware differs from trusted source')

        def test_flash_report(self):
            report_file = Path(args.report)
            self.assertTrue(report_file.is_file(), 'Mock flash report missing')
            report = json.loads(report_file.read_text(encoding='utf-8'))
            self.assertEqual(report.get('device'), args.device)
            self.assertEqual(report.get('firmware'), Path(args.image).name)
            self.assertEqual(report.get('status'), 'SIMULATED_FLASH_SUCCESS')
            self.assertEqual(report.get('checksum'), args.expected_sha256.lower())

        def test_host_resources(self):
            disk = shutil.disk_usage(args.workspace)
            self.assertGreaterEqual(disk.free, args.min_free_mb * 1024 * 1024,
                                    'Insufficient free workspace disk space')

    return TestFarmValidation


def write_junit(tests, result, output):
    failures = {test.id(): ('failure', message) for test, message in result.failures}
    failures.update({test.id(): ('error', message) for test, message in result.errors})
    root = ET.Element('testsuite', name='InfrastructureValidation',
                      tests=str(result.testsRun), failures=str(len(result.failures)),
                      errors=str(len(result.errors)), skipped=str(len(result.skipped)))
    for test in tests:
        case = ET.SubElement(root, 'testcase', classname='InfrastructureValidation',
                             name=test._testMethodName)
        if test.id() in failures:
            category, message = failures[test.id()]
            ET.SubElement(case, category, message='Validation failed').text = message
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output_path, encoding='utf-8', xml_declaration=True)


def main():
    args = parse_args()
    if args.min_free_mb < 0:
        raise SystemExit('--min-free-mb cannot be negative')
    test_class = build_tests(args)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_class)
    cases = list(suite)
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    write_junit(cases, result, args.xml)
    print(f'Infrastructure validation: {result.testsRun} tests, '
          f'{len(result.failures)} failures, {len(result.errors)} errors')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())