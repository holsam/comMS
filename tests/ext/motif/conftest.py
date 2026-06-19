'''
comMS motif extension: shared fixtures and markers
'''

# -- Import external dependencies
import pytest

# -- Register custom markers
def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'meme: integration test requiring a real MEME Suite install'
    )