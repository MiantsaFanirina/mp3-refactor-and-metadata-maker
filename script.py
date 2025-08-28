import os
import requests
import shutil
import logging
import tempfile
import imghdr
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, error, TXXX

# === CONFIG ===
source_folder = r"C:\Users\miant\OneDrive\Documents\DEV\metadataMaker\test"
target_folder = r"C:\Users\miant\OneDrive\Documents\DEV\metadataMaker\result"
log_file = "recognition_log.txt"
audd_api_token = "3fc2557af8e77bfacb0de120983836af"  # <-- get from https://audd.io

# Setup logger
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def recognize_song(file_path):
    url = "https://api.audd.io/"
    files = {'file': open(file_path, 'rb')}
    data = {
        'api_token': audd_api_token,
        'return': 'timecode,apple_music,deezer,spotify',
    }
    try:
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        result = response.json()
        if result['status'] == 'success' and result['result']:
            return result['result']
        else:
            return None
    except Exception as e:
        logging.error(f"API request failed for {file_path}: {e}")
        return None
    finally:
        files['file'].close()


def download_cover_image(url):
    if not url:
        print("No cover URL provided.")
        return None, None
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(r.content)
            tmp_path = tmpfile.name
        print(f"Downloaded cover image to temp file: {tmp_path}")
        with open(tmp_path, 'rb') as f:
            image_data = f.read()
        os.remove(tmp_path)
        mime_type = "image/jpeg"  # default mime type
        img_type = imghdr.what(None, h=image_data)
        if img_type:
            mime_type = f"image/{img_type}"
        print(f"Detected image MIME type: {mime_type}")
        return image_data, mime_type
    except Exception as e:
        print(f"Failed to download cover image: {e}")
        logging.warning(f"Failed to download cover image from {url}: {e}")
        return None, None


def save_file_with_metadata(source_path, metadata, cover_bytes, cover_mime):
    artist = metadata.get('artist', 'Unknown Artist')
    title = metadata.get('title', 'Unknown Title')
    album = metadata.get('album', '')
    release_date = metadata.get('release_date', '')
    label = metadata.get('label', '')
    producer = metadata.get('producer', '')

    # Clean filename to remove invalid Windows filename characters
    new_filename = f"{artist} - {title}.mp3"
    invalid_chars = r'\/:*?"<>|'
    for ch in invalid_chars:
        new_filename = new_filename.replace(ch, '')

    target_artist_folder = os.path.join(target_folder, artist)
    os.makedirs(target_artist_folder, exist_ok=True)

    target_file_path = os.path.join(target_artist_folder, new_filename)

    # Check if file already exists
    if os.path.exists(target_file_path):
        print(f"File already exists, skipping: {target_file_path}")
        logging.info(f"Skipped existing file: {target_file_path}")
        return False  # indicate skipping

    shutil.copy2(source_path, target_file_path)

    # Write standard tags with EasyID3
    try:
        audio = EasyID3(target_file_path)
    except mutagen.id3.ID3NoHeaderError:
        audio = mutagen.File(target_file_path, easy=True)
        audio.add_tags()

    audio['artist'] = artist
    audio['title'] = title
    if album:
        audio['album'] = album
    if release_date:
        audio['date'] = release_date

    audio.save()

    # Use ID3 for custom tags and cover art
    try:
        id3 = ID3(target_file_path)
    except error:
        id3 = ID3()

    # Clear previous custom tags
    id3.delall('TXXX:PRODUCER')
    id3.delall('TXXX:LABEL')

    if producer:
        id3.add(TXXX(encoding=3, desc='PRODUCER', text=producer))
    if label:
        id3.add(TXXX(encoding=3, desc='LABEL', text=label))

    # Embed cover art if available
    if cover_bytes and cover_mime:
        print("Embedding cover art...")
        id3.delall('APIC')
        id3.add(APIC(
            encoding=3,
            mime=cover_mime,
            type=3,  # front cover
            desc='Cover',
            data=cover_bytes
        ))
        print("Cover art embedded.")

    id3.save(target_file_path)
    return True


def main():
    os.makedirs(target_folder, exist_ok=True)
    success_count = 0
    fail_count = 0
    skipped_count = 0

    for filename in os.listdir(source_folder):
        if not filename.lower().endswith('.mp3'):
            continue

        source_path = os.path.join(source_folder, filename)
        print(f"Recognizing: {filename}")

        metadata = recognize_song(source_path)
        if metadata is None:
            logging.info(f"Failed to recognize: {filename}")
            print(f"Failed to recognize: {filename}")
            fail_count += 1
            continue

        # Extract cover URL from Spotify / Deezer / Apple Music in order
        cover_url = None

        if 'spotify' in metadata and metadata['spotify'] and 'album' in metadata['spotify']:
            images = metadata['spotify']['album'].get('images', [])
            if images:
                cover_url = images[0].get('url')

        if not cover_url and 'deezer' in metadata and metadata['deezer'] and 'album' in metadata['deezer']:
            cover_url = metadata['deezer']['album'].get('cover_big')

        if not cover_url and 'apple_music' in metadata and metadata['apple_music'] and 'artwork' in metadata['apple_music']:
            cover_template = metadata['apple_music']['artwork'].get('url')
            if cover_template:
                cover_url = cover_template.replace('{w}x{h}', '500x500')

        print(f"Cover URL found: {cover_url}")

        cover_bytes, cover_mime = download_cover_image(cover_url) if cover_url else (None, None)

        saved = save_file_with_metadata(source_path, metadata, cover_bytes, cover_mime)

        if saved is True:
            logging.info(f"Success: {filename} recognized as {metadata.get('artist')} - {metadata.get('title')}")
            print(f"Success: {filename} -> {metadata.get('artist')} - {metadata.get('title')}")
            success_count += 1
        elif saved is False:
            # File skipped because it already exists
            skipped_count += 1
        else:
            logging.info(f"Failed to save metadata: {filename}")
            print(f"Failed to save metadata: {filename}")
            fail_count += 1

    print(f"Recognition complete: {success_count} succeeded, {fail_count} failed, {skipped_count} skipped.")
    print(f"See log file '{log_file}' for details.")


if __name__ == "__main__":
    main()