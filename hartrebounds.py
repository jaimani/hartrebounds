import requests
import re
import os
import subprocess
import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def extract_game_info_from_url(url):
    """
    Extracts game ID and team abbreviations from an NBA.com game URL.
    
    Args:
        url (str): NBA.com game URL (format: /game/xxx-vs-yyy-0022300xxx)
    
    Returns:
        tuple: (game_id, away_team, home_team) or (None, None, None) if extraction fails
    """
    # Extract game ID using regex
    game_id_match = re.search(r'/game/.*?(\d{10})', url)
    if game_id_match:
        game_id = game_id_match.group(1)
        print(f"Extracted Game ID: {game_id}")
    else:
        print("Invalid URL format. Could not extract Game ID.")
        return None, None, None

    # Extract team abbreviations from URL
    teams_match = re.search(r'/game/([a-z]{3})-vs-([a-z]{3})', url)
    if teams_match:
        away_team = teams_match.group(1).upper()
        home_team = teams_match.group(2).upper()
        print(f"Extracted Teams - Away: {away_team}, Home: {home_team}")
    else:
        print("Invalid URL format. Could not extract team abbreviations.")
        return None, None, None

    return game_id, away_team, home_team

def get_game_date(game_id):
    """
    Fetches the game date from NBA stats API using the game ID.
    
    Args:
        game_id (str): NBA game ID
        
    Returns:
        str: Formatted date string (MM/DD/YYYY) or None if fetch fails
    """
    url = 'https://stats.nba.com/stats/boxscoresummaryv2'
    params = {
        'GameID': game_id
    }
    # Required headers for NBA.com API requests
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.nba.com/',
        'Accept': 'application/json, text/plain, */*',
        'Host': 'stats.nba.com',
        'Connection': 'keep-alive',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        game_date = data['resultSets'][0]['rowSet'][0][0]
        date_obj = datetime.strptime(game_date, '%Y-%m-%dT%H:%M:%S')
        date_str = date_obj.strftime('%m/%d/%Y')
        print(f"Game Date: {date_str}")
        return date_str
    except requests.exceptions.RequestException as e:
        print(f"Error fetching game date: {e}")
        return None
    except (IndexError, ValueError) as e:
        print(f"Error parsing game date: {e}")
        return None

def fetch_play_by_play_data(game_id):
    """
    Fetches play-by-play data from NBA.com's JSON endpoint.
    
    Args:
        game_id (str): NBA game ID
        
    Returns:
        dict: JSON response containing play-by-play data or None if fetch fails
    """
    url = f'https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.nba.com/',
        'Accept': 'application/json, text/plain, */*',
        'Connection': 'keep-alive',
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        print("Fetched play-by-play data successfully.")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching play-by-play data: {e}")
        return None

def extract_events(data, player_name='Hart REBOUND'):
    """
    Extracts rebound events for specified player from play-by-play data.
    
    Args:
        data (dict): Play-by-play data
        player_name (str): Player name to search for in event descriptions
        
    Returns:
        list: List of dictionaries containing event information
    """
    events = data.get('game', {}).get('actions', [])
    print(f"Total events in game: {len(events)}")
    filtered_events = []
    for event in events:
        description = event.get('description', '').strip()
        if player_name in description:
            event_num = event.get('actionNumber')
            game_id = data.get('game', {}).get('gameId')
            if not event_num or not game_id:
                print("Missing event number or game ID.")
                continue
            # Create URL for NBA.com's event viewer page
            video_page_url = f"https://www.nba.com/stats/events?CFID=&CFPARAMS=&GameEventID={event_num}&GameID={game_id}&Season=2024-25&flag=1&title={requests.utils.quote(description)}"
            filtered_events.append({
                'description': description,
                'video_page_url': video_page_url,
                'event_num': event_num,
                'event': event
            })
            print(f"Found event - Event ID: {event_num}, Description: {description}")
    print(f"Extracted {len(filtered_events)} events containing '{player_name}'.")
    return filtered_events

def download_video_from_page(video_page_url, file_name):
    """
    Downloads video from NBA.com stats page using Playwright.
    
    Args:
        video_page_url (str): URL of the NBA stats event page
        file_name (str): Output file name for the video
    """
    with sync_playwright() as p:
        # Chrome is required for video codec support
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

        # Launch browser in non-headless mode for better stability
        browser = p.chromium.launch(headless=False, executable_path=chrome_path)
        page = browser.new_page()

        # Implement retry logic for flaky pages
        max_retries = 5
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1} to load page.")
                page.goto(video_page_url, timeout=10000)
                try:
                    # Wait for video player to load
                    page.wait_for_selector('video#vjs_video_3_html5_api', timeout=15000)
                except Exception as e:
                    print(f"Error waiting for video element: {e}")
                    browser.close()
                    return
                break
            except Exception as e:
                print(f"Error loading page: {e}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    time.sleep(3)
                else:
                    print("Max retries reached. Exiting.")
                    browser.close()
                    return
        
        # Extract video source URL
        video_element = page.locator('video#vjs_video_3_html5_api')
        video_url = video_element.get_attribute('src')
        if not video_url:
            raise Exception('Video source not found!')

        print('Video source URL:', video_url)

        file_path = os.path.join(os.getcwd(), file_name)

        # Download video file in chunks
        response = requests.get(video_url, stream=True)
        if response.status_code == 200:
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    file.write(chunk)
            print(f"Download completed: {file_path}")
        else:
            print(f"Failed to download file, status code: {response.status_code}")

        browser.close()

def get_video_url_from_video_page(video_page_url):
    """
    Alternative method to extract video URL using BeautifulSoup (not currently used).
    
    Args:
        video_page_url (str): URL of the NBA stats event page
        
    Returns:
        str: Video source URL or None if extraction fails
    """
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.nba.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive',
    }
    try:
        response = requests.get(video_page_url, headers=headers, timeout=5000)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        video_tag = soup.find('video', class_='vjs-tech')
        print("video_tag: ", video_tag)
        if video_tag and video_tag.has_attr('src'):
            video_url = video_tag['src']
            print(f"Found video URL from video tag: {video_url}")
            return video_url
        else:
            print(f"No video URL found in video tag on page: {video_page_url}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching video page: {e}")
        return None
    except Exception as e:
        print(f"Error parsing video URL: {e}")
        return None

def extract_off_def(description):
    """
    Extracts offensive and defensive rebound counts from event description.
    
    Args:
        description (str): Event description text
        
    Returns:
        tuple: (offensive_rebounds, defensive_rebounds) or (None, None) if extraction fails
    """
    match = re.search(r'Off:(\d+)\s*Def:(\d+)', description)
    if match:
        off = int(match.group(1))
        deff = int(match.group(2))
        return off, deff
    return None, None

def overlay_text_on_video(input_video, output_video, text, font_size=56, x_pos='10', y_pos='main_h - 60'):
    """
    Adds text overlay to video using FFmpeg.
    
    Args:
        input_video (str): Input video file path
        output_video (str): Output video file path
        text (str): Text to overlay
        font_size (int): Font size for overlay
        x_pos (str): X position for text
        y_pos (str): Y position for text
    """
    safe_text = text.replace(":", r'\:').replace("'", r"\\'")
    drawtext = f"drawtext=text='{safe_text}':fontcolor=white:fontsize={font_size}:box=1:boxcolor=black@0.5:boxborderw=5:x={x_pos}:y={y_pos}"

    command = [
        'ffmpeg',
        '-y',
        '-i', input_video,
        '-vf', drawtext,
        '-codec:a', 'copy',
        output_video
    ]
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Overlayed text on video: {output_video}")
    except subprocess.CalledProcessError as e:
        print(f"Error overlaying text on video {output_video}: {e}")
        print("FFmpeg error output:")
        print(e.stderr)

def concatenate_videos(video_files, output_file):
    """
    Concatenates multiple video files into a single video using FFmpeg.
    
    Args:
        video_files (list): List of video file paths to concatenate
        output_file (str): Output video file path
    """
    # Create temporary file list for FFmpeg
    with open('videos.txt', 'w') as f:
        for video in video_files:
            f.write(f"file '{os.path.abspath(video)}'\n")
    command = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', 'videos.txt',
        '-c', 'copy',
        output_file
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print(f"Created final video: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error concatenating videos into {output_file}: {e}")
    finally:
        # Clean up temporary file list
        os.remove('videos.txt')

def replace_clip(clip_number, new_url, video_files):
    """
    Replaces a specific clip in the compilation with a new video.
    
    Args:
        clip_number (int): Index of clip to replace
        new_url (str): URL of replacement video
        video_files (list): List of video files to update
    """
    # Find the original filename in the video_files list
    original_filename = video_files[clip_number]

    # Extract stats from original filename
    match = re.search(r'Off(\d+)_Def(\d+)_Total(\d+)', original_filename)
    if not match:
        print(f"Could not find Off/Def/Total values in the filename: {original_filename}")
        return

    # Preserve original stats for overlay
    off = match.group(1)
    deff = match.group(2)
    overlay_text = f'Off: {off} Def: {deff}'

    # Define temporary and final filenames
    input_video = f'temp_clip_{clip_number}.mp4'
    output_video = f'processed_clip_{clip_number}_Off{off}_Def{deff}_Total{int(off) + int(deff)}.mp4'

    # Download and process replacement clip
    print(f"Downloading replacement clip for clip {clip_number}...")
    download_video_from_page(new_url, input_video)

    print(f"Applying overlay to replacement clip {clip_number}...")
    overlay_text_on_video(input_video, output_video, overlay_text)

    # Update video_files list with new filename
    video_files[clip_number] = output_video

    print(f"Replacement for clip {clip_number} completed.\n")

def prompt_for_replacements(video_files):
    """
    Interactive prompt for replacing clips in the compilation.
    
    Args:
        video_files (list): List of video files that can be replaced
        
    Returns:
        bool: True if any replacements were made, False otherwise
    """
    replacements_made = False
    while True:
        # Main replacement prompt
        replace_choice = input("Do you want to replace any clips? (yes/no): ").strip().lower()
        if replace_choice != 'yes':
            break

        try:
            # Get clip number and new URL
            clip_number = int(input(f"Enter the clip number to replace (1-{len(video_files)}): ").strip()) - 1
            if clip_number < 0 or clip_number >= len(video_files):
                print(f"Invalid clip number. Please enter a number between 1 and {len(video_files)}.")
                continue
            
            new_url = input(f"Enter the URL for the new clip to replace clip {clip_number + 1}: ").strip()
            replace_clip(clip_number, new_url, video_files)
            replacements_made = True
        
        except ValueError:
            print("Invalid input. Please enter a valid clip number.")
        
        # Check if user wants to replace more clips
        continue_replacement = input("Do you want to replace another clip? (yes/no): ").strip().lower()
        if continue_replacement != 'yes':
            break
    
    return replacements_made

def main():
    """
    Main function that orchestrates the video compilation process:
    1. Gets game information from URL
    2. Fetches play-by-play data
    3. Downloads individual rebound clips
    4. Adds statistical overlays
    5. Combines clips into final video
    6. Allows for clip replacement if needed
    7. Generates social media captions
    """
    # Get game URL from user
    url = input("Enter the NBA game URL: ").strip()
    game_id, away_team, home_team = extract_game_info_from_url(url)
    if not game_id or not away_team or not home_team:
        return

    # Fetch game data
    data = fetch_play_by_play_data(game_id)
    if not data:
        return

    # Get game date
    game_date = get_game_date(game_id)
    if not game_date:
        print("Game date not available. Cannot proceed.")
        return
    
    # Get rebound events
    events = extract_events(data)
    if not events:
        print("No matching events found.")
        return

    # Initialize tracking variables
    video_files = []  # Processed videos with overlays
    temp_videos = []  # Raw downloaded videos
    total_off = 0
    total_def = 0

    # Process each rebound event
    for idx, event_info in enumerate(events):
        description = event_info['description']
        event = event_info['event']
        off, deff = extract_off_def(description)

        if not off and not deff:
            print(f"Skipping event due to missing Off/Def values in description: {description}")
            continue

        # Update running totals
        total_off = off
        total_def = deff

        # Process video for current event
        print(f"Processing event {idx+1}/{len(events)}: Event ID {event_info['event_num']}")
        video_page_url = event_info['video_page_url']
        print("Video Page URL: ", video_page_url)
        input_video = f'clip_{idx}_Off{off}_Def{deff}_Total{off+deff}.mp4'
        output_video = f'processed_clip_{idx}_Off{off}_Def{deff}_Total{off+deff}.mp4'

        # Download and process video
        download_video_from_page(video_page_url, input_video)
        temp_videos.append(input_video)

        overlay_text = f'Off: {off} Def: {deff}'
        overlay_text_on_video(input_video, output_video, overlay_text)
        video_files.append(output_video)

        # Add delay to avoid rate limiting
        delay = random.uniform(1, 3)
        print(f"Waiting for {delay:.2f} seconds to avoid rate limits...")
        time.sleep(delay)

    if not video_files:
        print("No videos were processed.")
        return

    total_rebounds = total_off + total_def

    # Create final video with stats in filename
    output_filename = f"{away_team}_{home_team}_{game_date.replace('/', '_')}_Off{total_off}_Def{total_def}_Total{total_rebounds}.mp4"

    # Combine all clips
    concatenate_videos(video_files, output_filename)

    # Allow user to replace any clips
    replacements_made = prompt_for_replacements(video_files)
    
    # Recreate video if any clips were replaced
    if replacements_made:
        print("Replacements were made. Re-concatenating videos to generate an updated file...")
        concatenate_videos(video_files, output_filename)

    # Clean up temporary files
    all_clips = temp_videos + video_files
    for video in all_clips:
        os.remove(video)

    # Generate social media captions
    summary_tweet = f"Every @joshhart rebound from {away_team} @ {home_team} on {game_date}. Offensive: {total_off}, Defensive: {total_def}, Total: {total_rebounds} #Knicks"
    print("Summary Tweet: ")
    print(summary_tweet)
    summary_tiktok = f"Every Josh Hart rebound from {away_team} @ {home_team} on {game_date}. Offensive: {total_off}, Defensive: {total_def}, Total: {total_rebounds} #knicks"
    print("Summary TikTok: ")
    print(summary_tiktok)

    print("All done!")

if __name__ == '__main__':
    main()