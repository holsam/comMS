'''
Unit tests for src/comms/commands/experiment.py
'''

# -- Import external dependencies
import logging
import pytest
from unittest.mock import patch

# -- Import functions under test
from comms.commands.experiment import launch_experiment_gui, run_experiment_headless
from comms.utils.log import logMsg


# -- Define tests for the GUI launch entrypoint (run_app mocked, no event loop)
class TestLaunchExperimentGui:
    def test_exits_with_run_app_return_code(self):
        with patch('comms.gui.app.run_app', return_value=0):
            with pytest.raises(SystemExit) as exc:
                launch_experiment_gui()
        assert exc.value.code == 0

    def test_logs_launch(self, caplog):
        with patch('comms.gui.app.run_app', return_value=0), caplog.at_level(logging.INFO):
            with pytest.raises(SystemExit):
                launch_experiment_gui()
        assert 'Launching' in caplog.text

    def test_logger_named_experiment(self):
        with patch('comms.gui.app.run_app', return_value=0):
            with pytest.raises(SystemExit):
                launch_experiment_gui()
        assert logMsg._instance.logger.name == 'experiment'


# -- Define tests for the close-event log message
@pytest.mark.usefixtures('qapp')
class TestMainWindowCloseLogging:
    def test_close_writes_log_message(self, caplog):
        from comms.gui.main_window import MainWindow
        window = MainWindow()
        with caplog.at_level(logging.INFO):
            window.close()
        assert 'closed' in caplog.text.lower()

    def test_logger_named_experiment_after_close(self):
        from comms.gui.main_window import MainWindow
        window = MainWindow()
        window.close()
        assert logMsg._instance.logger.name == 'experiment'

# -- Define tests for the headless mode
class TestRunExperimentHeadless:
    def test_writes_three_files(self, tmp_path):
        raw = tmp_path / 'raw'; raw.mkdir()
        raw_file = raw / 'sample_mock.mzML'; raw_file.write_text('')
        base = tmp_path / 'exp'
        prompts = iter([
            'exp',                           # experiment name
            str(base),                       # save to
            '',                              # bin dir (blank → auto-resolve)
            str(tmp_path / 'db.fasta'),      # combined database FASTA (new prompt)
            'MOCK', '',                      # treatments: 'MOCK', then '' to finish
            'WCL', '',                       # fractions: 'WCL', then '' to finish
            str(raw),                        # input directory
            str(raw_file), '',               # _prompt_list('data file'): path then '' to finish
            'MOCK',                          # treatment for sample_mock.mzML
            'WCL',                           # fraction for sample_mock.mzML
        ])
        with patch('typer.prompt', side_effect=lambda *a, **k: next(prompts)), \
             patch('typer.confirm', return_value=False):
            run_experiment_headless()
        out = base / 'comms'
        assert (out / 'sample_sheet.tsv').exists()
        assert (out / 'config.toml').exists()
        assert (out / 'experiment.toml').exists()