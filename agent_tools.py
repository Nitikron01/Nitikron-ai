# agent_tools.py
from datetime import datetime

def validate_sale(menu: str, quantity: int, price: float) -> None:
    """Guardrails: raise ValueError แจ้งเตือนถ้าข้อมูลไม่ถูกต้องป้องกันข้อมูลขยะ"""
    if not menu or not menu.strip():
        raise ValueError("ชื่อเมนูห้ามว่าง")
    if quantity <= 0:
        raise ValueError("จำนวนต้องมากกว่า 0")
    if price <= 0:
        raise ValueError("ราคาต้องมากกว่า 0")

def log_sale(menu: str, quantity: int, price: float) -> dict:
    """บันทึกยอดขาย (เวอร์ชันจำลอง เพื่อตรวจเช็กการทำงานคู่กับ Harness)"""
    # วิ่งผ่านด่านตรวจ Guardrails ก่อน
    validate_sale(menu, quantity, price)
    
    total = quantity * price
    return {
        "status": "success",
        "menu": menu,
        "quantity": quantity,
        "price": price,
        "total": total,
        "timestamp": datetime.now().isoformat(),
    }

# คลังรวมเครื่องมือทั้งหมดที่ระบบอนุญาตให้ AI เรียกสั่งใช้งานได้
TOOLS = {
    "log_sale": log_sale,
}