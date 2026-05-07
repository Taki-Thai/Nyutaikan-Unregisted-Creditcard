from dotenv import load_dotenv
from src.orchestrate import run_pipeline

if __name__ == "__main__":
    # Tải các biến môi trường từ file .env (nếu có) vào hệ thống
    load_dotenv()
    
    # Bắt đầu chạy pipeline
    run_pipeline()
