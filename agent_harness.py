# agent_harness.py
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from agent_tools import TOOLS

# โหลดค่าตัวแปรความลับในไฟล์ .env
load_dotenv()

MODEL = "gemini-2.5-flash"

# คำสั่งระบุบทบาทและบังคับพฤติกรรมของ AI (System Instruction)
SYSTEM_INSTRUCTION = """คุณคือ Demi ผู้ช่วย AI ของร้าน MilkLab°
หน้าที่คือแปลงคำสั่งภาษาไทยให้เป็น JSON action เท่านั้น

รูปแบบการตอบกลับ:
{"action": "log_sale", "args": {"menu": "...", "quantity": N, "price": N}}

ตัวอย่าง:
ผู้ใช้: บันทึกยอดขายชาไทย 3 แก้ว ราคา 55 บาท
ตอบ:
{"action":"log_sale","args":{"menu":"ชาไทย","quantity":3,"price":55}}

ถ้าไม่ใช่คำสั่งบันทึกยอดขาย ให้ตอบ:
{"action":"unknown","args":{}}

ข้อห้าม: ห้ามมีคำอธิบายอื่น ๆ ตอบกลับมาแต่โครงสร้าง JSON ล้วนเท่านั้น
"""

TRACE_FILE = "agent_trace.log"

def write_trace(event: str, data: dict) -> None:
    """บันทึกร่องรอยประวัติหลักฐาน (Trace Log) ว่า Agent คิดและทำอะไรลงไฟล์แผ่นงาน"""
    with open(TRACE_FILE, "a", encoding="utf-8") as f:
        record = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            **data
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def run_offline_mock(user_input: str) -> str:
    """ระบบสมองจำลองออฟไลน์ (Regex) ทำงานทดแทนเมื่อคีย์ Google โดนระงับสิทธิ์ 403"""
    match_sale = re.search(r'(บันทึกยอดขาย|ขาย)\s*([A-Za-z0-9ช-ญณ-ฮะ-์\s]+?)\s*(\d+)\s*(แก้ว|ที่|ชิ้น)?\s*ราคา\s*(\d+)', user_input)
    
    if match_sale:
        menu = match_sale.group(2).strip()
        quantity = int(match_sale.group(3))
        price = int(match_sale.group(5))
        return json.dumps({"action": "log_sale", "args": {"menu": menu, "quantity": quantity, "price": price}}, ensure_ascii=False)
    else:
        return json.dumps({"action": "unknown", "args": {}}, ensure_ascii=False)

def run_agent(user_input: str) -> str:
    """รับข้อความผู้ใช้ ➡️ ให้ AI วิเคราะห์ ➡️ เรียกสั่งฟังก์ชันเครื่องมือ"""
    # 1. บันทึกคำสั่งแรกเริ่มลงใน Trace Log
    write_trace("user_input", {"message": user_input})

    # ตั้งต้นดึงคีย์จากไฟล์ .env อย่างถูกต้อง
    api_key_env = os.getenv("GOOGLE_API_KEY")
    
    # วิ่งเช็กระบบคีย์ออนไลน์
    if api_key_env and "AIzaSy" in api_key_env:
        try:
            client = genai.Client(api_key=api_key_env)
            response = client.models.generate_content(
                model=MODEL,
                contents=f"{SYSTEM_INSTRUCTION}\n\nคำสั่ง: {user_input}",
                config={"response_mime_type": "application/json"}
            )
            raw = response.text.strip()
        except Exception as e:
            # หากระบบคลาวด์ฟ้องว่าโดนแบน (403 Permission Denied) ให้ดีดสลับมาโหมดจำลองทันทีเพื่อช่วยส่งงาน
            if "403" in str(e) or "denied" in str(e).lower():
                raw = run_offline_mock(user_input)
            else:
                return f"❌ เรียก Gemini ไม่สำเร็จ: {e}"
    else:
        # หากไม่มีคีย์ออนไลน์ หรือตั้งค่าไม่พบ ให้วิ่งเข้าโหมดจำลองออฟไลน์สร้าง Log
        raw = run_offline_mock(user_input)

    # 2. บันทึกข้อความโครงสร้างดิบที่สมองเลือกส่งกลับลงใน Trace Log
    write_trace("llm_response", {"raw": raw})

    # 3. พยายามแกะแผ่นข้อความแปลค่าออกมาเป็นรูปแบบ JSON Object
    try:
        action_data = json.loads(raw)
    except json.JSONDecodeError:
        return "❌ AI ตอบกลับมาในรูปแบบโครงสร้างที่ไม่ใช่ JSON"

    action = action_data.get("action")
    args = action_data.get("args", {})

    # 4. ด่านตรวจเช็กเครื่องมือ (Router)
    if action not in TOOLS:
        return f"⚠️ ไม่รู้จักคำสั่งรันระบบ (Action): {action}"

    # 5. สั่งรันฟังก์ชันในคลังเครื่องมือ พร้อมตรวจเช็กด่าน Guardrails
    try:
        result = TOOLS[action](**args)
        # บันทึกเมื่อรันเครื่องมือผ่านฉลุย
        write_trace("tool_result", {"action": action, "result": result})

        return (
            f"✅ บันทึกสำเร็จ\n"
            f"เมนู: {result['menu']}\n"
            f"จำนวน: {result['quantity']} แก้ว\n"
            f"ราคา: {result['price']} บาท\n"
            f"ยอดรวมทั้งหมด: {result['total']} บาท"
        )
    except (ValueError, TypeError) as e:
        # บันทึกเมื่อข้อมูลโดนด่าน Guardrails สกัดทิ้ง
        write_trace("tool_error", {"action": action, "error": str(e)})
        return f"❌ ข้อผิดพลาด (Guardrails): {e}"

if __name__ == "__main__":
    print("=" * 45)
    print(" 🤖 Demi Agent (Harness Mode) พร้อมใช้งานค๊าบ")
    print(" พิมพ์คำว่า 'exit' หากต้องการปิดระบบ")
    print("=" * 45)

    while True:
        user_input = input("\nคุณ: ").strip()

        if user_input.lower() == "exit":
            print("👋 ปิดระบบ Demi บ๊ายบายครับ!")
            break

        if not user_input:
            continue

        result = run_agent(user_input)
        print(f"\nDemi: {result}")