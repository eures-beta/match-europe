import csv
import io
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, Mock

from django.core.management import call_command
from django.test import SimpleTestCase

from eures_beta.occupations.tools import refresh_catalog as updates
from eures_beta.occupations.tools.promote_catalog import promote

URI = 'http://data.europa.eu/esco/occupation/00000000-0000-0000-0000-000000000001'


def esco_archive(language, label='Fictional occupation'):
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w') as archive:
        rows = io.StringIO()
        writer = csv.DictWriter(
            rows,
            fieldnames=[
                'conceptUri',
                'status',
                'code',
                'iscoGroup',
                'preferredLabel',
                'description',
                'altLabels',
                'hiddenLabels',
            ],
        )
        writer.writeheader()
        writer.writerow(
            dict(
                conceptUri=URI,
                status='released',
                code='1',
                iscoGroup='1',
                preferredLabel=label,
                description='Fictional description',
                altLabels='',
                hiddenLabels='',
            )
        )
        archive.writestr(f'occupations_{language}.csv', rows.getvalue())
        if language == 'en':
            archive.writestr(
                'broaderRelationsOccPillar_en.csv', 'conceptUri,broaderUri\n'
            )
    return result.getvalue()


class CatalogUpdateTests(SimpleTestCase):
    def test_promotion_validates_before_replacing_and_keeps_runtime_directory(self):
        from eures_beta.occupations import catalog as service

        previous = service.DATA_DIR
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'published'
            target.mkdir()
            marker = target / 'esco.json'
            marker.write_bytes(b'untouched')
            with self.assertRaises(OSError):
                promote(Path(directory) / 'missing', target)
            self.assertEqual(marker.read_bytes(), b'untouched')
            report = promote(updates.DATA_DIR, target)
            self.assertEqual(len(report['searchChecks']), 31)
            for name in (*updates.FILES, 'manifest.json'):
                self.assertEqual(
                    (target / name).read_bytes(), (updates.DATA_DIR / name).read_bytes()
                )
            self.assertEqual(service.DATA_DIR, previous)

    def test_esco_import_requires_matching_languages_and_keeps_official_ids(self):
        jobs = updates.parse_esco([esco_archive(lang) for lang in updates.LANGUAGES])
        self.assertEqual(jobs[0]['uri'], URI)
        self.assertEqual(set(jobs[0]['labels']), {'fr', 'en', 'de'})
        with self.assertRaises(ValueError):
            updates.parse_esco([esco_archive('fr'), esco_archive('en')])

    def test_rome_and_ogr_are_parsed_together_from_xlsx(self):
        raw = io.BytesIO()
        namespace = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        cells = ''.join(
            f'<c r="{column}1" t="inlineStr"><is><t>{value}</t></is></c>'
            for column, value in zip('ABCDE', ['D', '11', '02', 'Fictional fiche', '1'])
        )
        appellation = ''.join(
            f'<c r="{column}2" t="inlineStr"><is><t>{value}</t></is></c>'
            for column, value in zip(
                'ABCDE', ['D', '11', '02', 'Fictional appellation', '2']
            )
        )
        with zipfile.ZipFile(raw, 'w') as archive:
            archive.writestr(
                'xl/workbook.xml',
                f'<workbook xmlns="{namespace}"><sheets><sheet name="Info"/><sheet name="New official edition"/></sheets></workbook>',
            )
            archive.writestr(
                'xl/worksheets/sheet2.xml',
                f'<worksheet xmlns="{namespace}"><sheetData><row>{cells}</row><row>{appellation}</row></sheetData></worksheet>',
            )
        fiches, ogr = updates.parse_rome(raw.getvalue())
        self.assertEqual(fiches['D1102']['id'], '1')
        self.assertEqual(ogr['2']['ficheCodes'], ['D1102'])

    def test_mapping_keeps_relation_and_edition_metadata(self):
        headers = [
            'Classification 1 Version;1.2.1',
            'Classification 2 Version;26M10',
        ] + [';'] * 12
        raw = (
            '\n'.join(
                headers + [f'{URI};;;;;123;Fictional occupation;;skos:exactMatch']
            )
            + '\n'
        ).encode('cp1252')
        mappings, versions = updates.parse_mapping(raw)
        self.assertEqual(versions, ('1.2.1', '26M10'))
        self.assertEqual(mappings[0]['id'], '123')
        self.assertEqual(mappings[0]['relation'], 'skos:exactMatch')
        with self.assertRaises(ValueError):
            updates.parse_mapping(b'not a mapping')

    def test_download_rejects_untrusted_hosts_and_redirects(self):
        with patch.object(updates.requests, 'get') as get:
            for url in (
                'http://ec.europa.eu/file',
                'https://example.invalid/file',
                'https://ec.europa.eu@example.invalid/file',
                'https://127.0.0.1/file',
            ):
                with self.assertRaises(ValueError):
                    updates.download(url)
            get.assert_not_called()
            response = get.return_value.__enter__.return_value
            response.status_code = 302
            with self.assertRaises(ValueError):
                updates.download('https://ec.europa.eu/file')
            self.assertFalse(get.call_args.kwargs['allow_redirects'])

    def test_source_failure_does_not_publish_partial_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'staging'
            fetch = Mock(side_effect=ValueError('source unavailable'))
            with self.assertRaisesRegex(ValueError, 'source unavailable'):
                updates.refresh('esco', output, fetch=fetch)
            self.assertFalse(output.exists())

    def test_removed_ids_require_explicit_review_and_do_not_modify_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'staging'
            with patch.object(
                updates,
                'parse_esco',
                return_value=updates.parse_esco(
                    [esco_archive(lang) for lang in updates.LANGUAGES]
                ),
            ):
                with self.assertRaisesRegex(ValueError, 'removed identifiers'):
                    updates.refresh('esco', output, fetch=Mock(return_value=b'fixture'))
            self.assertFalse(output.exists())

    def test_source_specific_refresh_preserves_other_sources_and_is_repeatable(self):
        manifest, current = updates.read_bundle(updates.DATA_DIR)
        source_fiches = current['fiches']
        source_ogr = current['appellations']
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'staging'
            with patch.object(
                updates, 'parse_rome', return_value=(source_fiches, source_ogr)
            ):
                updates.refresh(
                    'rome', output, fetch=Mock(return_value=b'fictional xlsx')
                )
                first = {
                    name: (output / name).read_bytes()
                    for name in (*updates.FILES, 'manifest.json')
                }
                updates.refresh(
                    'rome', output, fetch=Mock(return_value=b'fictional xlsx')
                )
                self.assertEqual(
                    first, {name: (output / name).read_bytes() for name in first}
                )
            new_manifest, actual = updates.read_bundle(output)
            self.assertEqual(actual, current)
            self.assertEqual(new_manifest['sources'][:4], manifest['sources'][:4])
            report = json.loads((output / 'update-report.json').read_bytes())
            self.assertEqual(report['occupations']['removed'], [])

    def test_all_three_django_commands_are_discoverable_without_database(self):
        for command in ('sync_esco', 'sync_rome', 'sync_esco_rome'):
            with patch(
                'eures_beta.occupations.management.commands._sync_catalog.refresh',
                return_value={},
            ) as refresh:
                call_command(command, stdout=io.StringIO())
                refresh.assert_called_once()
