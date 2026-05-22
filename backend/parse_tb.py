from bs4 import BeautifulSoup
import sys

try:
    with open('debug_out.html', 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
    exception_value = soup.find('pre', class_='exception_value')
    if exception_value:
        print("Exception:", exception_value.text.strip())
        
    browser_tb = soup.find('div', id='browserTraceback')
    if browser_tb:
        print("\nTraceback:")
        print(browser_tb.text.strip())
        
except Exception as e:
    print(f"Error parsing HTML: {e}")
