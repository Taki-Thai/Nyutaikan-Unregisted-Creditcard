import os, io
import pandas as pd
from gspread_dataframe import get_as_dataframe
from src.drive_utils import list_files_in_folder, download_file
from config.setting import (
    CARD_INPUT_FOLDER_ID,
    CARD_INPUT_FILENAME,
    CARD_TMP_DIR,
    CARD_SHEET_ID,
    CARD_NG_SHEET,
)


def load_ntk_contract(service) -> pd.DataFrame:
    """入退館カード請求書CSVをDriveから取得する"""
    print("📥 Downloading 電子名札・入退館カードの請求書.csv...")
    os.makedirs(CARD_TMP_DIR, exist_ok=True)
    available = list_files_in_folder(service, CARD_INPUT_FOLDER_ID)
    if CARD_INPUT_FILENAME not in available:
        raise FileNotFoundError(f"Không tìm thấy {CARD_INPUT_FILENAME} trong Drive.")
    dest = os.path.join(CARD_TMP_DIR, CARD_INPUT_FILENAME)
    download_file(service, available[CARD_INPUT_FILENAME], dest)
    print(f"  ✓ {CARD_INPUT_FILENAME}")
    with open(dest, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    df = pd.read_csv(io.StringIO(text), on_bad_lines="skip").astype(str)
    print(f"  → df_ntk_contract: {df.shape}")
    return df


def load_card_ng_offices(gc) -> set:
    """カード未収金NG企業リストをGoogle Sheetから取得する"""
    print("📥 Downloading カードNG企業リスト...")
    ws = gc.open_by_key(CARD_SHEET_ID).worksheet(CARD_NG_SHEET)
    ng_df = pd.DataFrame(get_as_dataframe(ws, dtype=str).dropna(how="all"))
    ng_set = set(
        ng_df["officeName"]
        .dropna()
        .str.replace("　", "", regex=False)
        .str.strip()
    )
    print(f"  → ng_offices: {len(ng_set)} companies")
    return ng_set
