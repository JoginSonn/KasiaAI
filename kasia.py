import sounddevice as sd
import scipy.io.wavfile as wavfile
import numpy as np
import time
import os
import requests # Używamy do API Whispera i ElevenLabs
from dotenv import load_dotenv
import pygame # Używamy pygame do odtwarzania

# --- NOWY IMPORT DLA LOKALNEGO "MÓZGU" ---
import ollama

# --- Ładowanie sekretów ---
load_dotenv() 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# GOOGLE_API_KEY już niepotrzebny
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") 

WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"

# --- Konfiguracja "Mózgu" (Gemini) ---
# WYRZUCILIŚMY CAŁY BLOK GEMINI. JESTEŚMY LOKALNI!
print("Mózg (Lokalny - Ollama) gotowy.")


# --- Konfiguracja "Głosu" (ElevenLabs) ---
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
TESTING_BEZ_NAGRYWANIA = False 

def nagraj_audio(nazwa_pliku, czas_trwania_s, samplerate):
    """Nagrywa audio z domyślnego mikrofonu i zapisuje do pliku .wav."""
    print("\nZaczynam nagrywanie...")
    print(f"Mów teraz! Masz {czas_trwania_s} sekund.")
    nagranie = sd.rec(int(czas_trwania_s * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()  
    print("Nagrywanie zakończone.")
    wavfile.write(nazwa_pliku, samplerate, nagranie)
    print(f"Nagranie zapisane jako: {nazwa_pliku}")

def transkrybuj_audio(nazwa_pliku):
    """Wysyła plik audio do API Whisper i zwraca tekst."""
    print(f"Wysyłam plik {nazwa_pliku} do transkrypcji ('Słuch')...")
    if not OPENAI_API_KEY:
        print("BŁĄD: Nie znaleziono klucza OPENAI_API_KEY.")
        return None
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    files = {
        'file': (nazwa_pliku, open(nazwa_pliku, 'rb'), 'audio/wav'),
        'model': (None, 'whisper-1'),
        'language': (None, 'pl')
    }
    try:
        response = requests.post(WHISPER_API_URL, headers=headers, files=files)
        response.raise_for_status() 
        data = response.json()
        tekst = data.get("text")
        if tekst:
            print(f"\nWhisper usłyszał: >>> {tekst} <<<")
            return tekst
        else:
            print("BŁĄD: Nie udało się uzyskać tekstu z odpowiedzi API Whispera.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"BŁĄD: Wystąpił problem z API OpenAI (Whisper): {e}")
        return None

# --- NOWA FUNKCJA "MÓZG" (LOKALNA - OLLAMA) ---
def pobierz_odpowiedz_ai(tekst_uzytkownika):
    """Wysyła tekst do lokalnego modelu Ollama i zwraca odpowiedź AI."""
    print("Wysyłam tekst do lokalnego 'Mózgu' (Ollama)...")
    
    # Tworzymy instrukcję systemową dla Kasi
    messages = [
        {'role': 'system', 'content': "Jesteś 'Kasia', pomocnym asystentem AI. Mówisz po polsku. Odpowiadaj zwięźle i bezpośrednio."},
        {'role': 'user', 'content': tekst_uzytkownika}
    ]

    try:
        # Wysyłamy zapytanie do lokalnie działającego serwera Ollama
        # Używamy modelu 'llama3:8b', który pobrałeś
        response = ollama.chat(model='llama3:8b', messages=messages)
        
        # Wyciągamy sam tekst odpowiedzi
        odpowiedz_tekst = response['message']['content']
        
        print(f"\nKasia (AI) mówi (tekst): >>> {odpowiedz_tekst} <<<")
        return odpowiedz_tekst
        
    except Exception as e:
        print(f"BŁĄD: Problem z lokalnym modelem Ollama: {e}")
        print("UPEWNIJ SIĘ, ŻE OLLAMA JEST URUCHOMIONA W TLE!")
        print("Upewnij się też, że pobrałeś model komendą 'ollama pull llama3:8b'")
        return "Błąd: Mózg lokalny nie odpowiada."

# --- Funkcja "Głosu" (zostaje ta, która działała - V1.5) ---
def mow_glos(tekst_do_powiedzenia):
    """Generuje mowę z ElevenLabs (przez czyste API HTTP) i odtwarza z pygame."""
    if not ELEVENLABS_API_KEY:
        print("BŁĄD: Klient ElevenLabs nie jest skonfigurowany.")
        return

    print("Wysyłam tekst do 'Głosu' (ElevenLabs - Metoda HTTP)...")
    VOICE_ID = "NacdHGUYR1k3M0FAbAia" # ID Głosu "Rachel"
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

        # Odtworzenie pliku audio za pomocą pygame
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
    print("Witaj w projekcie 'Kasia'. (Wersja 2.0: Słuch API + Mózg LOKALNY + Głos API)")

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

    # --- KROK 2: SŁUCH (WHISPER) ---
    print("\n--- KROK 2: SŁUCH (WHISPER) ---")
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