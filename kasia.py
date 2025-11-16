import os
import sys
import platform
import time
# HACK DLL USUNIĘTY - JUŻ GO NIE POTRZEBUJEMY

# Reszta naszych normalnych importów
import sounddevice as sd
import scipy.io.wavfile as wavfile
import numpy as np
import requests
from dotenv import load_dotenv
import pygame 
import ollama 

# Importujemy whispera
from faster_whisper import WhisperModel

# --- Ładowanie sekretów ---
load_dotenv() 
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") 

# --- Konfiguracja "Mózgu" (Lokalny - Ollama) ---
print("Mózg (Lokalny - Ollama) gotowy.")

# --- NOWA KONFIGURACJA "SŁUCHU" (LOKALNY - WERSJA CPU) ---
print("Ładowanie lokalnego 'Słuchu' (faster-whisper) na CPU...")
try:
    # Używamy modelu "medium" na CPU, z optymalizacją "int8"
    model_whisper = WhisperModel("medium", device="cpu", compute_type="int8")
    print("Lokalny 'Słuch' załadowany i gotowy. (Tryb CPU)")
except Exception as e:
    print(f"BŁĄD KRYTYCZNY: Nie udało się załadować modelu Whisper: {e}")
    exit() # Zamykamy skrypt, jeśli "Słuch" nie działa


# --- Konfiguracja "Głosu" (API - ElevenLabs) ---
NAZWA_PLIKU_ODPOWIEDZI = os.path.join("temp_audio", "odpowiedz.mp3") 
if not ELEVENLABS_API_KEY:
    print("BŁĄD: Nie znaleziono klucza ELEVENLABS_API_KEY. 'Głos' nie będzie działać.")
else:
    print("Głos (ElevenLabs) gotowy do użycia (tryb HTTP).")


# --- Ustawienia Nagrywania ---
SAMPLERATE = 44100
CZAS_NAGRYWANIA_S = 5
FOLDER_NAGRAN = "temp_audio"
NAZWA_PLIKU_NAGRANIA = "nagranie_testowe.wav"
SCIEZKA_PLIKU_NAGRANIA = os.path.join(FOLDER_NAGRAN, NAZWA_PLIKU_NAGRANIA)

# --- Przełącznik Deweloperski ---
TESTING_BEZ_NAGRYWANIA = True 

def nagraj_audio(nazwa_pliku, czas_trwania_s, samplerate):
    """Nagrywa audio z domyślnego mikrofonu i zapisuje do pliku .wav."""
    print("\nZaczynam nagrywanie...")
    print(f"Mów teraz! Masz {czas_trwania_s} sekund.")
    nagranie = sd.rec(int(czas_trwania_s * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()  
    print("Nagrywanie zakończone.")
    wavfile.write(nazwa_pliku, samplerate, nagranie)
    print(f"Nagranie zapisane jako: {nazwa_pliku}")

# --- ZAKTUALIZOWANA FUNKCJA "SŁUCH" (LOKALNA - CPU) ---
def transkrybuj_audio(nazwa_pliku):
    """Przetwarza plik audio przez lokalny model faster-whisper (na CPU)."""
    print(f"Przetwarzam plik {nazwa_pliku} przez lokalny 'Słuch' (CPU)...")
    try:
        segments, info = model_whisper.transcribe(nazwa_pliku, language="pl")
        tekst = "".join(segment.text for segment in segments)
        
        if tekst:
            print(f"\nLokalny Whisper usłyszał: >>> {tekst} <<<")
            return tekst
        else:
            print("BŁĄD: Lokalny Whisper nie zwrócił tekstu.")
            return None
    except Exception as e:
        print(f"BŁĄD: Wystąpił problem z lokalnym Whisperem: {e}")
        return None

# --- Funkcja "Mózgu" (Lokalna - Ollama) ---
def pobierz_odpowiedz_ai(tekst_uzytkownika):
    """Wysyła tekst do lokalnego modelu Ollama i zwraca odpowiedź AI."""
    print("Wysyłam tekst do lokalnego 'Mózgu' (Ollama)...")
    
    messages = [
        {'role': 'system', 'content': "Jesteś 'Kasia', pomocnym asystentem AI. Mówisz po polsku. Odpowiadaj zwięźle i bezpośrednio."},
        {'role': 'user', 'content': tekst_uzytkownika}
    ]

    try:
        response = ollama.chat(model='llama3:8b', messages=messages) 
        odpowiedz_tekst = response['message']['content']
        
        print(f"\nKasia (AI) mówi (tekst): >>> {odpowiedz_tekst} <<<")
        return odpowiedz_tekst
        
    except Exception as e:
        print(f"BŁĄD: Problem z lokalnym modelem Ollama: {e}")
        return "Błąd: Mózg lokalny nie odpowiada."

# --- Funkcja "Głosu" (API - ElevenLabs) ---
def mow_glos(tekst_do_powiedzenia):
    """Generuje mowę z ElevenLabs (przez czyste API HTTP) i odtwarza z pygame."""
    if not ELEVENLABS_API_KEY:
        print("BŁĄD: Klient ElevenLabs nie jest skonfigurowany.")
        return

    print("Wysyłam tekst do 'Głosu' (ElevenLabs - Metoda HTTP)...")
    VOICE_ID = "NacdHGUYR1k3M0FAbAia" # Hanna
    API_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": tekst_do_powiedzenia,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    try:
        response = requests.post(API_URL, json=data, headers=headers)
        response.raise_for_status() 

        with open(NAZWA_PLIKU_ODPOWIEDZI, 'wb') as f:
            f.write(response.content)
        
        print(f"Głos zapisany jako: {NAZWA_PLIKU_ODPOWIEDZI}")

        print("Odtwarzam odpowiedź (pygame)...")
        pygame.mixer.init() 
        pygame.mixer.music.load(NAZWA_PLIKU_ODPOWIEDZI)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        pygame.mixer.quit()
        print("Odtwarzanie zakończone.")

    except Exception as e:
        print(f"BŁĄD: Problem z API ElevenLabs (HTTP) lub odtwarzaniem pygame: {e}")

# --- GŁÓWNA PĘTLA APLIKACJI ---
if __name__ == "__main__":
    print("Witaj w projekcie 'Kasia'. (Wersja 2.4: Słuch LOKALNY-CPU + Mózg LOKALNY + Głos API)")

    if not os.path.exists(FOLDER_NAGRAN):
        os.makedirs(FOLDER_NAGRAN)

    # --- KROK 1: NAGRYWANIE (LUB POMINIĘCIE) ---
    if not TESTING_BEZ_NAGRYWANIA:
        print("\n--- KROK 1: NAGRYWANIE ---")
        time.sleep(1) 
        nagraj_audio(SCIEZKA_PLIKU_NAGRANIA, CZAS_NAGRYWANIA_S, SAMPLERATE) 
    else:
        print("\n--- KROK 1: NAGRYWANIE (POMINIĘTE W TRYBIE TESTOWYM) ---")
        print(f"Używam istniejącego pliku: {SCIEZKA_PLIKU_NAGRANIA}")

    # --- KROK 2: SŁUCH (LOKALNY - FASTER-WHISPER) ---
    print("\n--- KROK 2: SŁUCH (LOKALNY - FASTER-WHISPER) ---")
    tekst_uzytkownika = None
    if os.path.exists(SCIEZKA_PLIKU_NAGRANIA):
        tekst_uzytkownika = transkrybuj_audio(SCIEZKA_PLIKU_NAGRANIA)
    else:
        print(f"BŁĄD: Nie mogę znaleźć pliku {SCIEZKA_PLIKU_NAGRANIA}!")
        print("Uruchom program z TESTING_BEZ_NAGRYWANIA = False, aby go stworzyć.")

    # --- KROK 3: MÓZG (LOKALNY - OLLAMA) ---
    print("\n--- KROK 3: MÓZG (LOKALNY - OLLAMA) ---")
    odpowiedz_ai_tekst = None
    if tekst_uzytkownika:
        odpowiedz_ai_tekst = pobierz_odpowiedz_ai(tekst_uzytkownika)
    elif not tekst_uzytkownika:
         print("Brak tekstu od Whispera, 'Mózg' nie ma na co odpowiadać.")

    # --- KROK 4: GŁOS (ELEVENLABS) ---
    print("\n--- KROK 4: GŁOS (ELEVENLABS) ---")
    if odpowiedz_ai_tekst:
        mow_glos(odpowiedz_ai_tekst)
    else:
        print("Brak odpowiedzi od 'Mózgu', 'Głos' nie ma nic do powiedzenia.")

    print("\nPętla zakończona.")