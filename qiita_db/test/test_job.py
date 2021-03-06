# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import TestCase, main
from os import remove, mkdir
from os.path import join, exists
from shutil import rmtree
from datetime import datetime

from qiita_core.util import qiita_test_checker
from qiita_db.job import Job, Command
from qiita_db.user import User
from qiita_db.util import get_mountpoint
from qiita_db.analysis import Analysis
from qiita_db.exceptions import (QiitaDBDuplicateError, QiitaDBStatusError,
                                 QiitaDBUnknownIDError)


@qiita_test_checker()
class JobTest(TestCase):
    """Tests that the job object works as expected"""

    def setUp(self):
        self.job = Job(1)
        self.options = {"option1": False, "option2": 25, "option3": "NEW"}
        self._delete_path = []
        self._delete_dir = []
        _, self._job_folder = get_mountpoint("job")[0]

    def tearDown(self):
        # needs to be this way because map does not play well with remove and
        # rmtree for python3
        for item in self._delete_path:
            remove(item)
        for item in self._delete_dir:
            rmtree(item)

    def test_exists(self):
        """tests that existing job returns true"""
        # need to insert matching sample data into analysis 2
        self.conn_handler.execute(
            "DELETE FROM qiita.analysis_sample WHERE analysis_id = 2")
        self.conn_handler.execute(
            "INSERT INTO qiita.analysis_sample "
            "(analysis_id, processed_data_id, sample_id) VALUES "
            "(2, 1,'1.SKB8.640193'), (2, 1,'1.SKD8.640184'), "
            "(2, 1,'1.SKB7.640196'), (2, 1,'1.SKM9.640192'), "
            "(2, 1,'1.SKM4.640180')")
        self.assertTrue(Job.exists("18S", "Beta Diversity",
                                   {"--otu_table_fp": 1,
                                    "--mapping_fp": 1}, Analysis(1)))

    def test_exists_return_jobid(self):
        """tests that existing job returns true"""
        # need to insert matching sample data into analysis 2
        self.conn_handler.execute(
            "DELETE FROM qiita.analysis_sample WHERE analysis_id = 2")
        self.conn_handler.execute(
            "INSERT INTO qiita.analysis_sample "
            "(analysis_id, processed_data_id, sample_id) VALUES "
            "(2, 1,'1.SKB8.640193'), (2, 1,'1.SKD8.640184'), "
            "(2, 1,'1.SKB7.640196'), (2, 1,'1.SKM9.640192'), "
            "(2, 1,'1.SKM4.640180')")
        exists, jid = Job.exists("18S", "Beta Diversity",
                                 {"--otu_table_fp": 1, "--mapping_fp": 1},
                                 Analysis(1), return_existing=True)
        self.assertTrue(exists)
        self.assertEqual(jid, Job(2))

    def test_exists_noexist_options(self):
        """tests that non-existant job with bad options returns false"""
        # need to insert matching sample data into analysis 2
        # makes sure failure is because options and not samples
        self.conn_handler.execute(
            "DELETE FROM qiita.analysis_sample WHERE analysis_id = 2")
        self.conn_handler.execute(
            "INSERT INTO qiita.analysis_sample "
            "(analysis_id, processed_data_id, sample_id) VALUES "
            "(2, 1,'1.SKB8.640193'), (2, 1,'1.SKD8.640184'), "
            "(2, 1,'1.SKB7.640196'), (2, 1,'1.SKM9.640192'), "
            "(2, 1,'1.SKM4.640180')")
        self.assertFalse(Job.exists("18S", "Beta Diversity",
                                    {"--otu_table_fp": 1,
                                     "--mapping_fp": 27}, Analysis(1)))

    def test_exists_noexist_return_jobid(self):
        """tests that non-existant job with bad samples returns false"""
        exists, jid = Job.exists(
            "16S", "Beta Diversity",
            {"--otu_table_fp": 1, "--mapping_fp": 27}, Analysis(1),
            return_existing=True)
        self.assertFalse(exists)
        self.assertEqual(jid, None)

    def test_get_commands(self):
        exp = [
            Command('Summarize Taxa', 'summarize_taxa_through_plots.py',
                    '{"--otu_table_fp":null}', '{}',
                    '{"--mapping_category":null, "--mapping_fp":null,'
                    '"--sort":null}', '{"--output_dir":null}'),
            Command('Beta Diversity', 'beta_diversity_through_plots.py',
                    '{"--otu_table_fp":null,"--mapping_fp":null}', '{}',
                    '{"--tree_fp":null,"--color_by_all_fields":null,'
                    '"--seqs_per_sample":null}', '{"--output_dir":null}'),
            Command('Alpha Rarefaction', 'alpha_rarefaction.py',
                    '{"--otu_table_fp":null,"--mapping_fp":null}', '{}',
                    '{"--tree_fp":null,"--num_steps":null,''"--min_rare_depth"'
                    ':null,"--max_rare_depth":null,'
                    '"--retain_intermediate_files":false}',
                    '{"--output_dir":null}')
            ]
        self.assertEqual(Job.get_commands(), exp)

    def test_delete_files(self):
        try:
            Job.delete(1)
            with self.assertRaises(QiitaDBUnknownIDError):
                Job(1)

            obs = self.conn_handler.execute_fetchall(
                "SELECT * FROM qiita.filepath WHERE filepath_id = 12 OR "
                "filepath_id = 19")
            self.assertEqual(obs, [])

            obs = self.conn_handler.execute_fetchall(
                "SELECT * FROM qiita.job_results_filepath WHERE job_id = 1")
            self.assertEqual(obs, [])

            obs = self.conn_handler.execute_fetchall(
                "SELECT * FROM qiita.analysis_job WHERE job_id = 1")
            self.assertEqual(obs, [])

            self.assertFalse(exists(join(self._job_folder,
                             "1_job_result.txt")))
        finally:
            f = join(self._job_folder, "1_job_result.txt")
            if not exists(f):
                with open(f, 'w') as f:
                    f.write("job1result.txt")

    def test_delete_folders(self):
        try:
            Job.delete(2)
            with self.assertRaises(QiitaDBUnknownIDError):
                Job(2)

            obs = self.conn_handler.execute_fetchall(
                "SELECT * FROM qiita.filepath WHERE filepath_id = 13")
            self.assertEqual(obs, [])

            obs = self.conn_handler.execute_fetchall(
                "SELECT * FROM qiita.job_results_filepath WHERE job_id = 2")
            self.assertEqual(obs, [])

            obs = self.conn_handler.execute_fetchall(
                "SELECT * FROM qiita.analysis_job WHERE job_id = 2")
            self.assertEqual(obs, [])

            self.assertFalse(exists(join(self._job_folder, "2_test_folder")))
        finally:
            # put the test data back
            basedir = self._job_folder
            if not exists(join(basedir, "2_test_folder")):
                mkdir(join(basedir, "2_test_folder"))
                mkdir(join(basedir, "2_test_folder", "subdir"))
                with open(join(basedir, "2_test_folder",
                               "testfile.txt"), 'w') as f:
                    f.write("DATA")
                with open(join(basedir, "2_test_folder",
                               "testres.htm"), 'w') as f:
                    f.write("DATA")
                with open(join(basedir, "2_test_folder",
                               "subdir", "subres.html"), 'w') as f:
                    f.write("DATA")

    def test_create(self):
        """Makes sure creation works as expected"""
        # make first job
        new = Job.create("18S", "Alpha Rarefaction", {"opt1": 4}, Analysis(1))
        self.assertEqual(new.id, 4)
        # make sure job inserted correctly
        obs = self.conn_handler.execute_fetchall("SELECT * FROM qiita.job "
                                                 "WHERE job_id = 4")
        exp = [[4, 2, 1, 3, '{"opt1":4}', None]]
        self.assertEqual(obs, exp)
        # make sure job added to analysis correctly
        obs = self.conn_handler.execute_fetchall("SELECT * FROM "
                                                 "qiita.analysis_job WHERE "
                                                 "job_id = 4")
        exp = [[1, 4]]
        self.assertEqual(obs, exp)

        # make second job with diff datatype and command to test column insert
        new = Job.create("16S", "Beta Diversity", {"opt1": 4}, Analysis(1))
        self.assertEqual(new.id, 5)
        # make sure job inserted correctly
        obs = self.conn_handler.execute_fetchall("SELECT * FROM qiita.job "
                                                 "WHERE job_id = 5")
        exp = [[5, 1, 1, 2, '{"opt1":4}', None]]
        self.assertEqual(obs, exp)
        # make sure job added to analysis correctly
        obs = self.conn_handler.execute_fetchall("SELECT * FROM "
                                                 "qiita.analysis_job WHERE "
                                                 "job_id = 5")
        exp = [[1, 5]]
        self.assertEqual(obs, exp)

    def test_create_exists(self):
        """Makes sure creation doesn't duplicate a job"""
        with self.assertRaises(QiitaDBDuplicateError):
            Job.create("18S", "Beta Diversity",
                       {"--otu_table_fp": 1, "--mapping_fp": 1},
                       Analysis(1))

    def test_create_exists_return_existing(self):
        """Makes sure creation doesn't duplicate a job by returning existing"""
        Analysis.create(User("demo@microbio.me"), "new", "desc")
        self.conn_handler.execute(
            "INSERT INTO qiita.analysis_sample "
            "(analysis_id, processed_data_id, sample_id) VALUES "
            "(3, 1, '1.SKB8.640193'), (3, 1, '1.SKD8.640184'), "
            "(3, 1, '1.SKB7.640196'), (3, 1, '1.SKM9.640192'), "
            "(3, 1, '1.SKM4.640180')")
        new = Job.create("18S", "Beta Diversity",
                         {"--otu_table_fp": 1, "--mapping_fp": 1},
                         Analysis(3), return_existing=True)
        self.assertEqual(new.id, 2)

    def test_retrieve_datatype(self):
        """Makes sure datatype retrieval is correct"""
        self.assertEqual(self.job.datatype, '18S')

    def test_retrieve_command(self):
        """Makes sure command retrieval is correct"""
        self.assertEqual(self.job.command, ['Summarize Taxa',
                                            'summarize_taxa_through_plots.py'])

    def test_retrieve_options(self):
        self.assertEqual(self.job.options, {
            '--otu_table_fp': 1,
            '--output_dir': join(
                self._job_folder,
                '1_summarize_taxa_through_plots.py_output_dir')})

    def test_set_options(self):
        new = Job.create("18S", "Alpha Rarefaction", {"opt1": 4}, Analysis(1))
        new.options = self.options
        self.options['--output_dir'] = join(self._job_folder,
                                            '4_alpha_rarefaction.'
                                            'py_output_dir')
        self.assertEqual(new.options, self.options)

    def test_retrieve_results(self):
        self.assertEqual(self.job.results, ["1_job_result.txt"])

    def test_retrieve_results_folder(self):
        job = Job(2)
        self.assertEqual(job.results, ['2_test_folder/testres.htm',
                                       '2_test_folder/subdir/subres.html'])

    def test_retrieve_results_empty(self):
        new = Job.create("18S", "Beta Diversity", {"opt1": 4}, Analysis(1))
        self.assertEqual(new.results, [])

    def test_set_error(self):
        before = datetime.now()
        self.job.set_error("TESTERROR")
        after = datetime.now()
        self.assertEqual(self.job.status, "error")

        error = self.job.error

        self.assertEqual(error.severity, 2)
        self.assertEqual(error.msg, 'TESTERROR')
        self.assertTrue(before < error.time < after)

    def test_retrieve_error_blank(self):
        self.assertEqual(self.job.error, None)

    def test_set_error_completed(self):
        self.job.status = "error"
        with self.assertRaises(QiitaDBStatusError):
            self.job.set_error("TESTERROR")

    def test_retrieve_error_exists(self):
        self.job.set_error("TESTERROR")
        self.assertEqual(self.job.error.msg, "TESTERROR")

    def test_add_results(self):
        self.job.add_results([(join(self._job_folder, "1_job_result.txt"),
                             "plain_text")])

        # make sure files attached to job properly
        obs = self.conn_handler.execute_fetchall(
            "SELECT * FROM qiita.job_results_filepath WHERE job_id = 1")

        self.assertEqual(obs, [[1, 12], [1, 19]])

    def test_add_results_dir(self):
        # Create a test directory
        test_dir = join(self._job_folder, "2_test_folder")

        # add folder to job
        self.job.add_results([(test_dir, "directory")])

        # make sure files attached to job properly
        obs = self.conn_handler.execute_fetchall(
            "SELECT * FROM qiita.job_results_filepath WHERE job_id = 1")
        self.assertEqual(obs, [[1, 12], [1, 19]])

    def test_add_results_completed(self):
        self.job.status = "completed"
        with self.assertRaises(QiitaDBStatusError):
            self.job.add_results([("/fake/dir/", "directory")])


@qiita_test_checker()
class CommandTest(TestCase):
    def setUp(self):
        com1 = Command('Summarize Taxa', 'summarize_taxa_through_plots.py',
                       '{"--otu_table_fp":null}', '{}',
                       '{"--mapping_category":null, "--mapping_fp":null,'
                       '"--sort":null}', '{"--output_dir":null}')
        com2 = Command('Beta Diversity', 'beta_diversity_through_plots.py',
                       '{"--otu_table_fp":null,"--mapping_fp":null}', '{}',
                       '{"--tree_fp":null,"--color_by_all_fields":null,'
                       '"--seqs_per_sample":null}', '{"--output_dir":null}')
        com3 = Command('Alpha Rarefaction', 'alpha_rarefaction.py',
                       '{"--otu_table_fp":null,"--mapping_fp":null}', '{}',
                       '{"--tree_fp":null,"--num_steps":null,'
                       '"--min_rare_depth"'
                       ':null,"--max_rare_depth":null,'
                       '"--retain_intermediate_files":false}',
                       '{"--output_dir":null}')
        self.all_comms = {
            "16S": [com1, com2, com3],
            "18S": [com1, com2, com3],
            "ITS": [com2, com3],
            "Proteomic": [com2, com3],
            "Metabolomic": [com2, com3],
            "Metagenomic": [com2, com3],
        }

    def test_get_commands_by_datatype(self):
        obs = Command.get_commands_by_datatype()
        self.assertEqual(obs, self.all_comms)
        obs = Command.get_commands_by_datatype(["16S", "Metabolomic"])
        exp = {k: self.all_comms[k] for k in ('16S', 'Metabolomic')}
        self.assertEqual(obs, exp)

    def test_equal(self):
        commands = Command.create_list()
        self.assertTrue(commands[1] == commands[1])
        self.assertFalse(commands[1] == commands[2])
        self.assertFalse(commands[1] == Job(1))

    def test_not_equal(self):
        commands = Command.create_list()
        self.assertFalse(commands[1] != commands[1])
        self.assertTrue(commands[1] != commands[2])
        self.assertTrue(commands[1] != Job(1))


if __name__ == "__main__":
    main()
