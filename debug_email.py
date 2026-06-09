import asyncio
import logging
import sys

# Cấu hình log hiển thị chi tiết ra terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from app.utils.email_service import send_invoice_for_booking_id

async def main():
    # ⚠️ HÃY THAY SỐ 1 BẰNG MỘT ID ĐƠN ĐẶT PHÒNG CÓ THẬT TRONG DATABASE MYSQL CỦA BẠN
    REAL_BOOKING_ID = 23
    
    print(f"\n=== BẮT ĐẦU CHẠY THỬ GỬI MAIL CHO BOOKING ID: {REAL_BOOKING_ID} ===")
    
    try:
        await send_invoice_for_booking_id(REAL_BOOKING_ID)
    except Exception as e:
        print(f"\n❌ LỖI CHÍ MẠNG XUẤT HIỆN KHI CHẠY SCRIPT: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n=== KẾT THÚC QUÁ TRÌNH CHẠY THỬ ===")

if __name__ == "__main__":
    asyncio.run(main())