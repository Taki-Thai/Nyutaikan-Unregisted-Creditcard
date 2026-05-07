import polars as pl
import pandas as pd
from gspread_dataframe import get_as_dataframe
from src.drive_utils import write_to_sheet
from src.loaders import load_ntk_contract, load_card_ng_offices
from config.settings import CARD_OUTPUT_ID, CARD_OUTPUT_SHEET

def process_unregistered_card(service, gc):

    # =====================
    # 0. Load sheet cũ
    # =====================
    ws1 = gc.open_by_key(CARD_OUTPUT_ID).worksheet(CARD_OUTPUT_SHEET)
    try:
        output_old = pl.from_pandas(
            get_as_dataframe(ws1, dtype=str).dropna(how="all")
        )
    except Exception:
        output_old = pl.DataFrame()

    # =====================
    # 1. Load data mới
    # =====================
    df_raw        = load_ntk_contract(service)       # pandas
    ng_office_set = load_card_ng_offices(gc)          # set

    df_input = pl.from_pandas(df_raw)

    # =====================
    # 1.5. Update 入金日 cho sheet cũ
    # =====================
    payment_map = (
        df_input
        .select(["請求番号", "入金日"])
        .rename({"請求番号": "請求書番号"})
        .with_columns(pl.col("請求書番号").cast(pl.Utf8).str.strip_chars())
        .unique(subset=["請求書番号"])
    )

    if output_old.width > 0:
        output_old = (
            output_old
            .with_columns(pl.col("請求書番号").cast(pl.Utf8).str.strip_chars())
            .join(payment_map, on="請求書番号", how="left", suffix="_new")
            .with_columns(
                pl.coalesce(["入金日_new", "入金日"]).alias("入金日")
            )
            .drop("入金日_new")
        )

    # =====================
    # 2. Normalize + Filter
    # =====================
    EMPTY_VALUES = ["", " ", "　", "0", "NaT", "nan"]

    df_new = (
        df_input
        .with_columns([
            pl.when(pl.col("入金日").is_in(EMPTY_VALUES))
              .then(None)
              .otherwise(pl.col("入金日"))
              .alias("入金日"),

            pl.col("事務手数料")
              .str.replace_all(",", "")
              .str.strip_chars()
              .cast(pl.Float64, strict=False)
              .alias("事務手数料"),

            pl.col("アカウント")
              .str.replace_all("　", " ")
              .str.strip_chars()
              .alias("アカウント"),
        ])
    )

    df_filtered = df_new.filter(
        pl.col("入金日").is_null()
        & (pl.col("事務手数料") == 1000)
        & pl.col("アカウント").is_in(["削除", "有効"])
    )

    # =====================
    # 3. Rename + Create columns
    # =====================
    df_filtered = (
        df_filtered
        .with_columns(
            (
                pl.col("姓").fill_null("").str.strip_chars()
                + " "
                + pl.col("名").fill_null("").str.strip_chars()
            ).str.strip_chars().alias("ユーザー名")
        )
        .rename({
            "請求番号":  "請求書番号",
            "契約開始日": "更新日（本来の支払日）",
            "有効期限":  "契約期間",
        })
        .filter(~pl.col("会社名").str.contains("VNファーマ"))
    )

    # =====================
    # 3.5. 金額 = (金額 + 事務手数料) * 1.1
    # =====================
    df_filtered = (
        df_filtered
        .with_columns([
            pl.col("金額")
              .str.replace_all(",", "")
              .str.strip_chars()
              .cast(pl.Float64, strict=False)
              .fill_null(0)
              .alias("金額"),
            pl.col("事務手数料").fill_null(0),
        ])
        .with_columns(
            ((pl.col("金額") + pl.col("事務手数料")) * 1.1)
            .round(0).cast(pl.Int64)
            .alias("金額")
        )
    )

    # =====================
    # 4. Filter NG offices + select columns
    # =====================
    OUTPUT_COLUMNS = [
        "会社名", "ユーザー名", "メールアドレス", "請求書番号",
        "金額", "更新日（本来の支払日）", "契約期間", "入金日",
    ]

    df_output = (
        df_filtered
        .select(OUTPUT_COLUMNS)
        .filter(~pl.col("会社名").is_in(ng_office_set))
    )

    # =====================
    # 5. Idempotent merge + write
    # =====================
    df_output = df_output.with_columns(
        pl.col("請求書番号").cast(pl.Utf8).str.strip_chars()
    )

    if output_old.width > 0:
        existing_keys = set(output_old["請求書番号"].to_list())
        df_new_rows = df_output.filter(
            ~pl.col("請求書番号").is_in(existing_keys)
        )
        output_final = pl.concat([output_old, df_new_rows], how="diagonal")
    else:
        output_final = df_output

    output_final = (
        output_final
        .unique(subset=["請求書番号"], keep="first")
        .sort("請求書番号")
    )

    write_to_sheet(gc, CARD_OUTPUT_ID, CARD_OUTPUT_SHEET, output_final.to_pandas())
    print("✅ process_unregistered_card hoàn thành")
