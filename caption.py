import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

menu_name = input("ชื่อเมนู: ")
price = input("ราคา: ")

prompt = f"""
ช่วยสร้าง caption Instagram ภาษาไทยสำหรับร้านนม

เมนู: {menu_name}
ราคา: {price}

ขอ Caption 3 สไตล์:
1. Cute
2. Minimal
3. Gen-Z

ใช้ภาษาทันสมัย อ่านง่าย น่ารัก
ใส่อีโมจิเล็กน้อย
"""

# ตรวจสอบจุดนี้ดีๆ ครับ ต้องมีเครื่องหมายจุลภาค (,) คั่นทุกบรรทัดด้านใน
response = client.chat.completions.create(
    model="google/gemini-2.5-flash", 
    max_tokens=1000,
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)

print("\n===== RESULT =====\n")
print(response.choices[0].message.content)