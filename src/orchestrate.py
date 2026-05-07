from src.drive_utils import get_drive_service, get_sheets_client
from src.processors import process_unregistered_card

def run_pipeline():
    service = get_drive_service()
    gc      = get_sheets_client()

    print("🚀 Pipeline bắt đầu...")
    process_unregistered_card(service, gc)
    print("✅ Pipeline hoàn thành")
