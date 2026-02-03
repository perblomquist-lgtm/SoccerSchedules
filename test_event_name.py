import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def test_event_name():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Loading page...")
        await page.goto('https://system.gotsport.com/org_event/events/39474', 
                       wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(5)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        print("\n=== Page Title ===")
        print(await page.title())
        
        print("\n=== Looking for H1 tags ===")
        h1_tags = soup.find_all('h1')
        for i, h1 in enumerate(h1_tags):
            print(f"H1 {i}: {h1.get('class')} - {h1.get_text(strip=True)[:100]}")
        
        print("\n=== Looking for elements with 'title' or 'event' in class name ===")
        elements = soup.find_all(class_=lambda x: x and ('title' in str(x).lower() or 'event' in str(x).lower()))
        for i, elem in enumerate(elements[:20]):
            print(f"{elem.name} {i}: {elem.get('class')} - {elem.get_text(strip=True)[:100]}")
        
        print("\n=== Looking for div/span in header/nav ===")
        header = soup.find('header') or soup.find('nav')
        if header:
            for elem in header.find_all(['div', 'span', 'a', 'h1', 'h2']):
                text = elem.get_text(strip=True)
                if text and len(text) > 10 and len(text) < 200:
                    print(f"{elem.name}: {elem.get('class')} - {text[:100]}")
        
        print("\n=== Testing BeautifulSoup find with 'navbar-brand-event' ===")
        elem1 = soup.find('a', class_='navbar-brand-event')
        print(f"Found with class_='navbar-brand-event': {elem1}")
        if elem1:
            print(f"Text: {elem1.get_text(strip=True)}")
            print(f"Title attr: {elem1.get('title')}")
        
        elem2 = soup.find('a', {'class': 'no-pad-left navbar-brand-event'})
        print(f"Found with exact class match: {elem2}")
        
        elem3 = soup.find('a', class_=lambda x: x and 'navbar-brand-event' in x)
        print(f"Found with lambda: {elem3}")
        if elem3:
            print(f"Text: {elem3.get_text(strip=True)}")
        
        print("\n=== Testing widget-title ===")
        widget = soup.find('div', class_='widget-title')
        print(f"Found widget-title: {widget}")
        if widget:
            print(f"Text: {widget.get_text(strip=True)}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_event_name())
