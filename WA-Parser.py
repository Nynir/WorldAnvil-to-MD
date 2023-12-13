import os
import json
import requests
import re
import yaml
from tqdm import tqdm

version = 1.0

DEBUG = False

source_directory = 'World-Anvil-Export' # should point at the local folder with your world anvil exports
destination_directory = 'World-Anvil-Output' # where you want the formatted files and folders to end up
obsidian_resource_folder = 'images'

attempt_bbcode = True

# Define the list of tags you want to extract for the main content. Usually the default is what you want
content_tags_to_extract = [
    'title',
    'content',
]

os.makedirs(destination_directory, exist_ok=True)

def download_image(url, filename):
    if not url:
        if DEBUG:
            print(f"No URL provided for image: {filename}")
        return
    if DEBUG: print(url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            if not filename.lower().endswith((".png", ".jpeg", ".jpg")): # I had one case where an image didn't get an extension .. never seen it again
                filename = filename + ".png" # Hoping and guessing its a png, i'll read bytes later
            with open(f'{obsidian_resource_folder}/{filename}', 'wb') as f:
                f.write(response.content)
                # Loading bar for downloading images... do we want this?
                #for chunk in tqdm(response.iter_content(chunk_size=1024), total=(int(response.headers.get('content-length', 0)) // 1024) + 1, unit='KB'):
                #    f.write(chunk)
    except Exception as e:
        print(f"Failed to download or save image {filename}. Error: {e}")

# Function for extracting the extra sections if they are above 10 length,
# this is sections like the scrapbook, geography, etc.
def extract_sections(data, markdown_file):
    sections = data.get("sections", {})
    for section_key, section_data in sections.items():
        if isinstance(section_data, dict) and "content" in section_data:
            content = section_data["content"]
            if isinstance(content, str) and len(content) > 10:
                section_content = format_content({'text': content})
                section_key = ' '.join(section_key.split('_')).title()
                markdown_file.write(f"\n## {section_key}\n\n{section_content}\n")

def extract_relations(data, markdown_file):
    relations = data.get("relations", {})
    for relation_key, relation_data in relations.items():
        if isinstance(relation_data, dict) and "items" in relation_data:
            content = ''
            if isinstance(relation_data["items"], list):
                for item in relation_data["items"]:
                    if item["relationshipType"] == "article":
                        content = content + '[[' + item["title"] + ']]\n'
                    else:
                        content = content + item["title"] + '\n'
            else:
                content = "[[" + relation_data["items"]["title"] + "]]"
            markdown_file.write(f"\n## {relation_key}\n\n{content}\n")



def create_parent_directory(file_path):
    parent_directory = os.path.dirname(file_path)
    os.makedirs(parent_directory, exist_ok=True)

def format_content(content):
    if not content:
        return ""
    text = content['text']
    if not isinstance(text, str):
        return str(text)

    text = re.sub(r'@\[([^\]]+)\]\([^)]+\)', r'[[\1]]', text) # Replaces World Anvil links with Obsidian internal links
    text = re.sub(r'\r\n\r', r'\n', text) # This was to fix some extra spacing issues that came from my export

    # THIS SECTION IS A WIP, some of these are ChatGPT-assisted regexes that aren't perfect
    if attempt_bbcode:
        text = re.sub(r'[ \t]+', ' ', text) # Strip extra spaces and tabs
        text = re.sub(r'\n +(\[h\d\])', r'\n\1', text) # Remove leading spaces before headings
        text = re.sub(r'\[br\]', r'\n', text) # [br] to newline
        text = re.sub(r'\[h1\](.*?)\[/h1\]', r'# \1', text) # Convert [h1]...[/h1] to # ... (L1 heading)
        text = re.sub(r'\[h2\](.*?)\[/h2\]', r'## \1', text) # Convert [h2]...[/h2] to ## ... (L2 heading)
        text = re.sub(r'\[h3\](.*?)\[/h3\]', r'### \1', text) # Convert [h3]...[/h3] to ### ... (L3 heading)
        text = re.sub(r'\[h4\](.*?)\[/h4\]', r'#### \1', text) # Convert [h4]...[/h4] to #### ... (L4 heading)
        text = re.sub(r'\[p\](.*?)\[/p\]', r'\1\n', text) # Convert [p]...[/p] to a simple newline-delimited paragraph
        text = re.sub(r'\[b\](.*?)\[/b\]', r'**\1**', text) # Convert [b]...[/b] to **...** (bold)
        text = re.sub(r'\[i\](.*?)\[/i\]', r'*\1*', text) # Convert [i]...[/i] to *...* (italic)
        text = re.sub(r'\[u\](.*?)\[/u\]', r'<u>\1</u>', text) # Convert [u]...[/u] to <u>...</u> (underline)
        text = re.sub(r'\[s\](.*?)\[/s\]', r'~~\1~~', text) # Convert [s]...[/s] to ~~...~~ (strikethrough)
        text = re.sub(r'\[url\](.*?)\[/url\]', r'[\1]', text) # Convert [url]URL[/url] to [text](URL)
        text = re.sub(r'\[list\](.*?)\[/list\]', lambda m: re.sub(r'\[\*\](.*?)\n?', r'* \1\n', m.group(1), flags=re.DOTALL), text, flags=re.DOTALL) # Convert [list]...[/list] to bullet point lists
        text = re.sub(r'\[code\](.*?)\[/code\]', r'```\n\1\n```', text) # Convert [code]...[/code] to code blocks
        text = re.sub(r'\[quote\]([\s\S]*?)\[/quote\]', lambda m: '> ' + '\n> '.join(m.group(1).split('\n')), text, flags=re.DOTALL) # Convert [quote] ... [/quote] to Obsidian block quotes
        
        # These two items will require a CSS snippet to work properly, I included a sample in the repo
        text = re.sub(r'\[sup\](.*?)\[/sup\]', r'<sup>\1</sup>', text) # Superscript
        text = re.sub(r'\[sub\](.*?)\[/sub\]', r'<sub>\1</sub>', text) # Subscript

        # List Items
        text = re.sub(r'\[ol\]|\[/ol\]', r'', text)
        text = re.sub(r'\[ul\]|\[/ul\]', r'', text)
        text = re.sub(r'\[li\](.*?)\[/li\]', r'- \1', text)

    return text

# loading bar
def count_json_files(directory):
    json_count = 0
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.json'):
                json_count += 1
    return json_count

total_files = count_json_files(source_directory)
progress_bar = tqdm(total=total_files, unit=' articles')

# Iterate through JSON files in the source directory.
try:
    for root, dirs, files in os.walk(source_directory):
        for filename in files:
            if filename.endswith('.json'):
                json_file = os.path.join(root, filename)
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extracting data to use as yaml metadata in the Obsidian document
                yaml_data = {
                    "creationDate": data.get("creationDate", {}).get("date", ""),
                    "template": data.get("template", ""),
                    "world": data.get("world", {}).get("title", ""),
                }

                # This creates a subfolder based on the template
                template = yaml_data.get("template", "other")
                create_parent_directory(f"{destination_directory}/{template}/")

                # Create a Markdown file in the destination directory.
                markdown_filename = os.path.join(destination_directory, template, os.path.splitext(filename)[0] + '.md')
                with open(markdown_filename, 'w') as markdown_file:
                    
                    # Download the image referenced by "cover[url]" with the name from "cover[title]".
                    try:
                        cover_url = data.get("cover", {}).get("url", "")
                        cover_title = data.get("cover", {}).get("title", "")
                        hasImage = True
                    except:
                        if DEBUG: print(f"No image for {filename}")
                        hasImage = False

                    if hasImage == True:
                        download_image(cover_url, cover_title)

                    # Writing the metadata yaml
                    markdown_file.write('---\n')
                    yaml.dump(yaml_data, markdown_file, default_style='', default_flow_style=False)
                    markdown_file.write('---\n')

                    if hasImage:
                        markdown_file.write(f'![[{cover_title}]]\n\n')

                    # Writing the main content
                    for tag in content_tags_to_extract:
                        value = data.get(tag, '')
                        if tag == 'content':
                            formatted_content = format_content({'text': value})
                            markdown_file.write(f"{formatted_content}\n\n")
                        elif value:
                            tag.capitalize
                            markdown_file.write(f"# {tag.capitalize()}: {value}\n\n") # This creates a L1 header based on the filename

                    markdown_file.write("# Extras\n\n") # Change this if you want to change the extras L1 header
                    
                    # Extract extra sections, create L2 headers and put their content below
                    extract_sections(data, markdown_file)
                    extract_relations(data, markdown_file)

                    progress_bar.update(1)

except Exception as e:
    print(f"Failed to convert. Error: {e}")

finally:
    progress_bar.close()

print("WA-Parser is finished; Please validate your results")
