#!/usr/bin/env python3
"""
Debug Greenhouse Form - Inspect what fields are available
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

url = "https://job-boards.greenhouse.io/gitlab/jobs/8207075002"

print("=" * 70)
print("🔍 Inspecting Greenhouse Form Fields")
print("=" * 70)
print(f"\nOpening: {url}\n")

# Initialize Chrome
options = webdriver.ChromeOptions()
# options.add_argument('--headless')  # Comment out to see the browser
driver = webdriver.Chrome(options=options)

try:
    driver.get(url)
    time.sleep(3)  # Wait for page to load
    
    # Try to click Apply button if exists
    try:
        apply_btn = driver.find_element(By.CSS_SELECTOR, "a.app-btn, button.app-btn, .application-button")
        print(f"✅ Found Apply button: {apply_btn.text}")
        apply_btn.click()
        time.sleep(2)
    except:
        print("ℹ️  No Apply button found (form may be directly visible)")
    
    # List all input fields
    print("\n📋 All Input Fields on Page:")
    print("-" * 70)
    
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for i, inp in enumerate(inputs, 1):
        input_type = inp.get_attribute("type") or "text"
        input_name = inp.get_attribute("name") or "(no name)"
        input_id = inp.get_attribute("id") or "(no id)"
        input_placeholder = inp.get_attribute("placeholder") or ""
        
        print(f"{i}. Type: {input_type:15} | Name: {input_name:30} | ID: {input_id}")
        if input_placeholder:
            print(f"   Placeholder: {input_placeholder}")
    
    # Look specifically for file inputs
    print("\n📎 File Upload Fields:")
    print("-" * 70)
    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    if file_inputs:
        for i, finp in enumerate(file_inputs, 1):
            name = finp.get_attribute("name") or "(no name)"
            id_attr = finp.get_attribute("id") or "(no id)"
            accept = finp.get_attribute("accept") or "any"
            print(f"{i}. Name: {name} | ID: {id_attr} | Accepts: {accept}")
    else:
        print("❌ No file input fields found!")
    
    # Look for text areas
    print("\n📝 Text Areas:")
    print("-" * 70)
    textareas = driver.find_elements(By.TAG_NAME, "textarea")
    for i, ta in enumerate(textareas, 1):
        name = ta.get_attribute("name") or "(no name)"
        id_attr = ta.get_attribute("id") or "(no id)"
        placeholder = ta.get_attribute("placeholder") or ""
        print(f"{i}. Name: {name} | ID: {id_attr}")
        if placeholder:
            print(f"   Placeholder: {placeholder}")
    
    # Look for submit buttons
    print("\n🔘 Submit Buttons:")
    print("-" * 70)
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for i, btn in enumerate(buttons, 1):
        btn_type = btn.get_attribute("type") or "button"
        btn_text = btn.text or "(no text)"
        btn_id = btn.get_attribute("id") or "(no id)"
        if "submit" in btn_type.lower() or "submit" in btn_text.lower():
            print(f"{i}. Type: {btn_type} | Text: {btn_text} | ID: {btn_id}")
    
    print("\n" + "=" * 70)
    print("✅ Inspection Complete!")
    print("=" * 70)
    print("\nBrowser will stay open for 30 seconds for manual inspection...")
    time.sleep(30)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()
    print("\n✅ Browser closed")
