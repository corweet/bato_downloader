import requests
from bs4 import BeautifulSoup
import os
import re
import json
import time # Import time for sleep

def search_manga(query, max_pages=5):
    all_results = []
    seen_urls = set() # Use a set to store unique URLs
    page = 1
    while page <= max_pages:
        search_url = f"https://bato.to/search?word={requests.utils.quote(query)}&page={page}"
        print(f"Searching page {page}: {search_url}")
        try:
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching search page {page}: {e}")
            break

        soup = BeautifulSoup(response.content, 'html.parser')

        page_results_found = False # Flag to check if any new results were found on this page
        for item in soup.find_all('div', class_='item-text'):
            title_element = item.find('a', class_='item-title')
            if title_element:
                title = title_element.text.strip()
                url = "https://bato.to" + title_element['href']
                if url not in seen_urls: # Check if URL is already seen
                    all_results.append({'title': title, 'url': url})
                    seen_urls.add(url)
                    page_results_found = True
        
        if not page_results_found: # If no new results were found on this page
            print(f"No new results found on page {page}. Stopping search.")
            break
        
        page += 1
        time.sleep(1)
    return all_results

def get_manga_info(series_url):
    response = requests.get(series_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    manga_title = soup.find('h3', class_='item-title').text.strip()
    chapters = []
    
    # Find all chapter links
    chapter_elements = soup.find_all('a', class_='chapt')
    for chapter_element in chapter_elements:
        chapter_title = chapter_element.text.strip()
        chapter_url = "https://bato.to" + chapter_element['href']
        chapters.append({'title': chapter_title, 'url': chapter_url})
    
    # Reverse the order of chapters so that Chapter 1 is listed first
    chapters.reverse()
    
    return manga_title, chapters

def download_chapter(chapter_url, manga_title, chapter_title, output_dir="."):
    response = requests.get(chapter_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Sanitize chapter_title for use in file paths
    # Remove characters that are invalid in Windows file paths
    sanitized_chapter_title = re.sub(r'[<>:"/\\|?*]', '', chapter_title).strip()
    # Replace spaces with underscores and remove multiple underscores
    sanitized_chapter_title = re.sub(r'\s+', '_', sanitized_chapter_title)
    sanitized_chapter_title = re.sub(r'_+', '_', sanitized_chapter_title).strip('_')
    
    chapter_dir = os.path.join(output_dir, manga_title, sanitized_chapter_title)
    os.makedirs(chapter_dir, exist_ok=True)

    image_urls = []
    script_tags = soup.find_all('script')
    for script in script_tags:
        if 'imgHttps' in script.text:
            match = re.search(r'imgHttps = (\[.*?\]);', script.text)
            if match:
                try:
                    image_urls = json.loads(match.group(1))
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from script tag: {e}")
                break

    if not image_urls:
        print(f"No image URLs found for {chapter_title} at {chapter_url}.")
        dump_file_path = os.path.join(chapter_dir, f"{sanitized_chapter_title}_dump.html")
        with open(dump_file_path, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"Full HTML content dumped to {dump_file_path} for inspection.")
        return

    for i, img_url in enumerate(image_urls):
        if img_url and img_url.startswith('http'):
            try:
                img_data = requests.get(img_url).content
                img_extension = img_url.split('.')[-1].split('?')[0]
                with open(os.path.join(chapter_dir, f"page_{i+1}.{img_extension}"), 'wb') as handler:
                    handler.write(img_data)
                print(f"Downloaded {img_url} to {chapter_dir}")
            except Exception as e:
                print(f"Error downloading {img_url}: {e}")
