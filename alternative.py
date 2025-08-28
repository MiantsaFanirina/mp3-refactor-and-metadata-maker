import os
import shutil
import logging
import acoustid
import musicbrainzngs
import requests
import tempfile
import imghdr
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, error, TXXX

# === CONFIG ===
source_folder = r"C:\Users\miant\OneDrive\Documents\DEV\metadataMaker\test"
target_folder = r"C:\Users\miant\OneDrive\Documents\DEV\metadataMaker\result"
log_file = "recognition_log.txt"
acoustid_api_key = "HzKG3hXQQy"  # Your AcoustID API key

# Setup MusicBrainz client
musicbrainzngs.set_useragent("AutoRenameMp3", "1.0", "miantsafanirinarakotondrafara@gmail.com")

# Setup logging
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def identify(file_path):
    try:
        results = acoustid.match(acoustid_api_key, file_path)
        for score, recording_id, title, artist in results:
            # Return best match
            if artist and title:
                return {
                    "recording_id": recording_id,
                    "title": title,
                    "artist": artist
                }
        return None
    except acoustid.AcoustidError as e:
        logging.error(f"AcoustID error for {file_path}: {e}")
        return None


def fetch_metadata(recording_id):
    try:
        result = musicbrainzngs.get_recording_by_id(recording_id, includes=["artists", "releases"])
        recording = result['recording']
        title = recording.get('title', '')
        artist = recording['artist-credit'][0]['artist']['name'] if recording.get('artist-credit') else ''
        album = ''
        release_date = ''
        cover_url = ''

        if 'releases' in recording and len(recording['releases']) > 0:
            release = recording['releases'][0]
            album = release.get('title', '')
            release_date = release.get('date', '')
            release_id = release.get('id')
            if release_id:
                try:
                    cover_art = musicbrainzngs.get_release_coverart(release_id)
                    images = cover_art.get('images', [])
                    if images:
                        cover_url = images[0].get('image', '')
                except musicbrainzngs.ResponseError:
                    pass

        return {
            "title": title,
            "artist": artist,
            "album": album,
            "release_date": release_date,
            "cover_url": cover_url
        }
    except Exception as e:
        logging.error(f"MusicBrainz metadata fetch error for {recording_id}: {e}")
        return None


def download_cover_image(url):
    if not url:
        return None, None
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(r.content)
            tmp_path = tmpfile.name
        with open(tmp_path, 'rb') as f:
            image_data = f.read()
        os.remove(tmp_path)
        mime_type = "image/jpeg"
        img_type = imghdr.what(None, h=image_data)
        if img_type:
            mime_type = f"image/{img_type}"
        return image_data, mime_type
    except Exception as e:
        logging.warning(f"Failed to download cover image from {url}: {e}")
        return None, None


def save_file_with_metadata(source_path, metadata, cover_bytes, cover_mime):
    artist = metadata.get('artist', 'Unknown Artist')
    title = metadata.get('title', 'Unknown Title')
    album = metadata.get('album', '')
    release_date = metadata.get('release_date', '')
    label = metadata.get('label', '')
    producer = metadata.get('producer', '')

    # Clean filename
    new_filename = f"{artist} - {title}.mp3"
    invalid_chars = r'\/:*?"<>|'
    for ch in invalid_chars:
        new_filename = new_filename.replace(ch, '')

    target_artist_folder = os.path.join(target_folder, artist)
    os.makedirs(target_artist_folder, exist_ok=True)
    target_file_path = os.path.join(target_artist_folder, new_filename)

    shutil.copy2(source_path, target_file_path)

    # Write standard tags
    try:
        audio = EasyID3(target_file_path)
    except error.ID3NoHeaderError:
        audio = mutagen.File(target_file_path, easy=True)
        audio.add_tags()

    audio['artist'] = artist
    audio['title'] = title
    if album:
        audio['album'] = album
    if release_date:
        audio['date'] = release_date
    audio.save()

    # Use ID3 for custom tags & cover
    try:
        id3 = ID3(target_file_path)
    except error:
        id3 = ID3()

    id3.delall('TXXX:PRODUCER')
    id3.delall('TXXX:LABEL')

    if producer:
        id3.add(TXXX(encoding=3, desc='PRODUCER', text=producer))
    if label:
        id3.add(TXXX(encoding=3, desc='LABEL', text=label))

    if cover_bytes and cover_mime:
        id3.delall('APIC')
        id3.add(APIC(
            encoding=3,
            mime=cover_mime,
            type=3,
            desc='Cover',
            data=cover_bytes
        ))

    id3.save(target_file_path)
    return True


def main():
    os.makedirs(target_folder, exist_ok=True)
    success_count = 0
    fail_count = 0

    for filename in os.listdir(source_folder):
        if not filename.lower().endswith('.mp3'):
            continue

        source_path = os.path.join(source_folder, filename)
        print(f"Identifying: {filename}")

        id_result = identify(source_path)
        if not id_result:
            logging.info(f"Failed to identify: {filename}")
            print(f"Failed to identify: {filename}")
            fail_count += 1
            continue

        metadata = fetch_metadata(id_result['recording_id'])
        if not metadata:
            logging.info(f"Failed to fetch metadata for: {filename}")
            print(f"Failed to fetch metadata for: {filename}")
            fail_count += 1
            continue

        print(f"Artist: {metadata['artist']} | Title: {metadata['title']} | Album: {metadata['album']}")
        print(f"Cover URL: {metadata['cover_url']}")

        cover_bytes, cover_mime = download_cover_image(metadata['cover_url'])

        saved = save_file_with_metadata(source_path, metadata, cover_bytes, cover_mime)

        if saved:
            logging.info(f"Success: {filename} recognized as {metadata['artist']} - {metadata['title']}")
            print(f"Success: {filename} -> {metadata['artist']} - {metadata['title']}")
            success_count += 1
        else:
            logging.info(f"Failed to save metadata: {filename}")
            print(f"Failed to save metadata: {filename}")
            fail_count += 1

    print(f"Process complete: {success_count} succeeded, {fail_count} failed.")
    print(f"See log file '{log_file}' for details.")


if __name__ == "__main__":
    main()
