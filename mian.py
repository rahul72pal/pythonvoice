import speech_recognition as sr
import google.generativeai as genai
import webbrowser
import pywhatkit
import os
import json
import time
import threading
from dotenv import load_dotenv
from urllib.parse import quote_plus
from speak import speak

import requests

def check_internet_speed():
    try:
        print("Checking internet speed...")
        start = time.time()
        requests.get("https://www.google.com", timeout=5)
        print(f"Internet latency: {(time.time() - start) * 1000:.2f} ms")
    except Exception as e:
        print("Internet not available or very slow:", e)

check_internet_speed()

def speak_async(text):
    threading.Thread(target=speak, args=(text,), daemon=True).start()
# --- 2. Setup and Configuration ---

# Load environment variables from a .env file
load_dotenv()

# Configure the Generative AI model
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    speak("AI model configured successfully.")
except Exception as e:
    print(f"Fatal Error during AI Setup: {e}")
    speak("There was a critical error setting up the AI model. Please check your API key and environment file. The program will now exit.")
    exit()

def open_website(url: str):
    """Opens a given URL in the default web browser."""
    if not url:
        speak("You need to specify a website to open.")
        return
    if not url.startswith("http"):
        url = f"https://{url}"
    webbrowser.open(url)
    speak(f"Opening {url}")

def play_on_youtube(query: str):
    """Plays a video on YouTube based on a search query."""
    if not query:
        speak("You need to tell me what to play.")
        return
    speak(f"Playing {query} on YouTube.")
    pywhatkit.playonyt(query)

def search_google(query: str):
    """Searches for a given query on Google."""
    if not query:
        speak("You need to tell me what to search for.")
        return
    speak(f"Searching Google for {query}")
    pywhatkit.search(query)

def search_on_youtube(query: str):
    """Searches for a given query on YouTube and shows the results page."""
    if not query:
        speak("You need to tell me what to search for on YouTube.")
        return
    speak(f"Searching YouTube for {query}")
    # Construct the Youtube URL safely
    search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    webbrowser.open(search_url)

def stop_assistant():
    """Stops the assistant's active listening mode."""
    speak("Goodbye Sir.")
    # We return a "sleep" signal to the main loop
    return "sleep"


# This dictionary maps the AI's tool names to our Python functions
available_tools = {
    "open_website": open_website,
    "play_on_youtube": play_on_youtube,
    "search_google": search_google,
    "search_on_youtube": search_on_youtube,
    "stop_assistant": stop_assistant,
}

STOP_KEYWORDS = {"stop", "exit", "quit", "goodbye", "bye", "shutdown"}

# Define this once at the top of your file (outside the function)
BASE_PROMPT = """
You are a voice assistant controller. Your job is to determine the user's intent and map it to one of the available tools.
You must respond ONLY with a JSON object in the format: {"tool_name": "name_of_the_tool", "argument": "argument_value"}

Available tools:
- "open_website": Opens a website (e.g., "google.com").
- "play_on_youtube": Plays a song/video on YouTube (e.g., "Shape of You").
- "search_google": Searches Google with a query.
- "search_on_youtube": Searches on YouTube without autoplay.
- "stop_assistant": Stops the assistant. Argument should be empty.
- "conversation": For general responses. Return the full text response as argument.
"""

def process_command_dynamic(command: str):
    command = command.lower().strip()
    if not command:
        return
    
    # Check if command is a stop command (quick local check)
    if any(word in command for word in STOP_KEYWORDS):
        return stop_assistant()

    prompt = f"{BASE_PROMPT}\nUser Command: \"{command}\"\nJSON Response:"

    try:
        # Measure execution time
        start_time = time.time()
        response = model.generate_content(prompt, stream=True)

        # Collect all streamed text parts
        full_text = ''.join([chunk.text for chunk in response])
        duration = time.time() - start_time
        print(f"AI response time: {duration:.2f} seconds")

        # Clean JSON text
        result_text = full_text.strip().removeprefix("```json").removesuffix("```").strip()

        # Parse JSON
        result_json = json.loads(result_text)

        tool_name = result_json.get("tool_name")
        argument = result_json.get("argument", "")

        if tool_name in available_tools:
            tool_function = available_tools[tool_name]
            if tool_name == "stop_assistant":
                return tool_function()
            else:
                tool_function(argument)
        elif tool_name == "conversation":
            speak(argument)
        else:
            speak("I'm not sure how to do that. Could you try rephrasing?")

    except json.JSONDecodeError:
        print(f"Invalid JSON:\n{full_text}")
        speak("I couldn't understand the command properly. Please try again.")
    except Exception as e:
        print(f"Error: {e}")
        speak("Sorry, something went wrong.")

    return None



# def process_command_dynamic(command: str):
#     """
#     Uses Generative AI to understand and execute commands dynamically.
#     """
#     command = command.lower().strip()
#     if not command:
#         return # Ignore empty commands

#     # The prompt tells the AI how to behave and what tools it has.
#     prompt = f"""
#     You are a voice assistant controller. Your job is to determine the user's intent and map it to one of the available tools.
#     You must respond ONLY with a JSON object in the format: {{"tool_name": "name_of_the_tool", "argument": "argument_value"}}

#     Available tools are:
#     - "open_website": For opening a website. The argument is the domain (e.g., "google.com").
#     - "play_on_youtube": For playing a video/song on YouTube. The argument is the video/song name.
#     - "search_google": For general web searches on Google. The argument is the search query.
#     - "search_on_youtube": For searching on YouTube without playing a specific video. The argument is the search query.
#     - "stop_assistant": When the user wants to exit, stop, or go to sleep. The argument should be an empty string.
#     - "conversation": If the command is a general question or chat that doesn't fit a tool. The argument is the full text response you should give.

#     User Command: "{command}"

#     JSON Response:
#     """

#     try:
#         response = model.generate_content(prompt)
#         # Clean up the response to ensure it's valid JSON
#         result_text = response.text.strip().replace("```json", "").replace("```", "")
#         result_json = json.loads(result_text)

#         tool_name = result_json.get("tool_name")
#         argument = result_json.get("argument")

#         if tool_name in available_tools:
#             tool_function = available_tools[tool_name]
#             # Special case for stop_assistant to return the "sleep" signal
#             if tool_name == "stop_assistant":
#                 return tool_function()
#             else:
#                 tool_function(argument)
#         elif tool_name == "conversation":
#             speak(argument)
#         else:
#             speak("I'm not sure how to do that. Could you try rephrasing?")

#     except json.JSONDecodeError:
#         print(f"Error: AI returned invalid JSON: {response.text}")
#         speak("I had a little trouble understanding. Please say that again.")
#     except Exception as e:
#         print(f"Error processing command: {e}")
#         speak("Sorry, an unexpected error occurred.")
    
#     return None # Return None if not stopping


def listen_for_command(r):
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.3)
        print("Listening for command...")
        audio = r.listen(source, timeout=6, phrase_time_limit=8)
    return r.recognize_google(audio)

if __name__ == "__main__":
    speak("Hello, I am Friday.")
    r = sr.Recognizer()
    jarvis_active = False

    while True:
        try:
            if not jarvis_active:
                print("Listening for trigger word: 'Friday'...")
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.3)
                    audio = r.listen(source, timeout=5, phrase_time_limit=5)

                word = r.recognize_google(audio).lower()
                print(f"You said: {word}")

                if "friday" in word:
                    speak("Yes sir!")
                    jarvis_active = True
            else:
                try:
                    command = listen_for_command(r).lower()
                    print(f"Command: {command}")
                    result = process_command_dynamic(command)
                    if result == "sleep":
                        jarvis_active = False  # Deactivate after hearing stop phrase
                except sr.UnknownValueError:
                    print("Didn't catch that, waiting for next command...")
                except sr.WaitTimeoutError:
                    print("Command timeout, still active...")

        except sr.UnknownValueError:
            print("Didn't catch that.")
        except sr.RequestError as e:
            print(f"API Error: {e}")
        except sr.WaitTimeoutError:
            print("Timeout waiting for trigger word.")
        except Exception as e:
            print(f"Unexpected error: {e}")