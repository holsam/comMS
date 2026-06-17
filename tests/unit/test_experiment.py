'''
Unit tests for src/comms/commands/experiment.py
'''

# -- Import external dependencies
import logging
import pytest
from unittest.mock import patch

# -- Import functions under test
from comms.commands.experiment import launch_experiment_gui
from comms.utils.log import logMsg


# -- Define tests for the launch entry point (run_app mocked, no event loop)
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