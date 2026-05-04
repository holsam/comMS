'''
comMS sample sheet parser

N.B. expected columns:
    sample_id: unique identifier for each sample
    raw_file: filename of the .RAW (or .mzML) source file
    treatment: experimental group (e.g. MOCK, MYC)
    replicate: replicate number within treatment
    batch: batch label (optional, used for batch-correction)
'''

# -- Import external dependencies
import pandas
from pathlib import Path
from typing import Optional

# -- Import internal dependencies
from comms.utils.log import logMsg

# -- Define required columns
REQUIRED_COLUMNS = {"sample_id", "raw_file", "treatment", "replicate"}

# -- loadSampleSheet: returns dataframe of sample sheet contents
def loadSampleSheet(path: Path) -> pandas.DataFrame:
    logMsg.debug(f'Loading sample sheet: {path.name}')
    sep = '\t' if path.suffix.lower() in {'.tsv', '.txt'} else ','
    try:
        df = pandas.read_csv(path, sep=sep)
    except Exception as e:
        raise ValueError(f'Could not read sample sheet ({path.name}): {e}')
    df.columns = df.columns.str.strip().str.lower()
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f'Sample sheet ({path.name}) is missing required column(s): {", ".join(sorted(missing))}\n'
            f'Required columns: {", ".join(sorted(REQUIRED_COLUMNS))}'
        )
    if df['sample_id'].duplicated().any():
        raise ValueError(f'Sample sheet ({path.name}) contains duplicate sample_id values.')
    logMsg.debug(f'Sample sheet loaded: {len(df)} rows, {df["treatment"].nunique()} treatment(s)')
    return df

# -- getSamplesByTreatment: returns dataframe of a subset of input dataframe giving samples with a specific treatment value
def getSamplesByTreatment(df: pandas.DataFrame, treatment: str) -> pandas.DataFrame:
    logMsg.debug(f'Filtering samples for treatment: {treatment}')
    return df[df['treatment'].str.upper() == treatment.upper()].copy()


# -- getRawFileMap: returns dictionary of Paths for each sample_id in sample sheet
def getRawFileMap(df: pandas.DataFrame, input_dir: Path) -> dict:
    logMsg.debug(f'Building file map from {len(df)} sample(s)')
    file_map = {}
    for _, row in df.iterrows():
        raw_path = input_dir / row['raw_file']
        if raw_path.exists():
            file_map[row['sample_id']] = raw_path
        else:
            logMsg.warn(f'Raw file not found for sample {row["sample_id"]}: {raw_path}')
    return file_map