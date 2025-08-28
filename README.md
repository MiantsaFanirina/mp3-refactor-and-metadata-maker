# Metadata Maker (Test Version)

Metadata Maker is a Python script that automatically recognizes songs, downloads album covers, and saves metadata into your `.mp3` files.  

It uses the [Audd.io API](https://audd.io) for song recognition and metadata retrieval, then updates your music files with proper **artist, title, album, release date, label, producer**, and **embedded cover art**.

---

## Features
- Recognizes `.mp3` songs using [Audd.io](https://audd.io)  
- Retrieves metadata (artist, title, album, release date, etc.)  
- Automatically downloads album cover art (from Spotify, Deezer, or Apple Music)  
- Embeds cover art into `.mp3` files  
- Organizes songs into artist folders  
- Skips files if they already exist (prevents duplicates)  
- Creates a detailed log of successes and failures  

---

## How It Works
1. Place your `.mp3` files in the **`test`** folder (source).  
2. Run the script.  
3. For each `.mp3` file:
   - The script sends the audio to the Audd.io API for recognition.  
   - If recognized, metadata is retrieved (artist, title, album, etc.).  
   - The script tries to fetch cover art:
     - First from Spotify  
     - If not available, tries Deezer  
     - If not available, tries Apple Music  
   - The `.mp3` file is copied into the **`result`** folder under the artist’s name.  
   - Metadata and cover art are embedded into the copied file.  
4. Logs of recognition and failures are stored in `recognition_log.txt`.

---

## Project Structure
```bash
metadataMaker/
│── test/ # Source folder (put your MP3s here)
│── result/ # Output folder (processed MP3s saved here)
│── recognition_log.txt # Log file (created after running script)
│── metadata_maker.py # Main script
```


---

## Requirements
- Python 3.8+  
- Required Python libraries:
  ```bash
  pip install requests mutagen
  ```


---

## Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/metadataMaker.git
cd metadataMaker
```

2. Get a free API token from audd.io
3. Open metadata_maker.py and replace:
```bash
audd_api_token = "YOUR_API_KEY" /with your token
``` 

4. Place some .mp3 files into the test folder.

---

## Usage
Run the script with:

```bash
python metadata_maker.py
```
Example output:
```bash
Recognizing: song1.mp3
Cover URL found: https://i.scdn.co/album/cover.jpg
Embedding cover art...
Cover art embedded.
Success: song1.mp3 -> Artist - Title
```
At the end you’ll see:
```bash
Recognition complete: 5 succeeded, 2 failed, 1 skipped.
See log file 'recognition_log.txt' for details.
```

---
## Notes

- This is a test version – it only works with .mp3 files.
- Some songs may not be recognized if they are rare or unofficial.
- Internet connection is required for recognition and cover downloads.
- If the script skips a file, it means it already exists in the result folder.

---

## License
MIT License – feel free to use, modify, and contribute.
