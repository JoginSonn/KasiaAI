import sounddevice as sd
import scipy.io.wavfile as wavfile
import numpy as np
import time
import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from elevenlabs.client import ElevenLabs
import pygame # Używamy pygame do odtwarzania

# --- Ładowanie sekretów ---
load_dotenv() 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"

# --- Konfiguracja "Mózgu" (Gemini) ---
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    # Używamy nazwy modelu, którą znaleźliśmy
    model_gemini = genai.GenerativeModel('models/gemini-pro-latest') 
    print("Mózg (Gemini) pomyślnie skonfigurowany.")
else:
    print("BŁĄD: Nie znaleziono klucza GOOGLE_API_KEY. 'Mózg' nie będzie działać.")
    model_gemini = None

# --- Konfiguracja "Głosu" (ElevenLabs) ---
NAZWA_PLIKU_ODPOWIEDZI = os.path.join("temp_audio", "odpowiedz.mp3") 
if ELEVENLABS_API_KEY:
    client_elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    print("Głos (ElevenLabs) pomyślnie skonfigurowany.")
else:
    print("BŁĄD: Nie znaleziono klucza ELEVENLABS_API_KEY. 'Głos' nie będzie działać.")
    client_elevenlabs = None

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

def pobierz_odpowiedz_ai(tekst_uzytkownika):
    """Wysyła tekst do API Gemini i zwraca odpowiedź AI."""
    if not model_gemini:
         return "Błąd: Mózg nie jest podłączony."
    print("Wysyłam tekst do 'Mózgu' (Gemini)...")
    try:
        chat = model_gemini.start_chat(history=[])
        # Dajemy mu prosty kontekst, żeby był bardziej jak asystent
        instrukcja = "Jesteś 'Kasia', pomocnym asystentem AI. Odpowiadaj zwięźle i bezpośrednio."
        response = chat.send_message(instrukcja + "\n\nUżytkownik: " + tekst_uzytkownika)
        odpowiedz_tekst = response.text
        print(f"\nKasia (AI) mówi (tekst): >>> {odpowiedz_tekst} <<<")
        return odpowiedz_tekst
    except Exception as e:
        print(f"BŁĄD: Problem z API Gemini: {e}")
        return "Błąd: Mózg nie odpowiada."

# --- ZAKTUALIZOWANA FUNKCJA "GŁOS" (UŻYWA TERAZ .text_to_speech.generate) ---
def mow_glos(tekst_do_powiedzenia):
    """Wysyła tekst do ElevenLabs, zapisuje MP3 i odtwarza za pomocą pygame."""
    if not client_elevenlabs:
        print("BŁĄD: Klient ElevenLabs nie jest skonfigurowany.")
        return

    print("Wysyłam tekst do 'Głosu' (ElevenLabs)...")
    try:
        #
        # --- OTO JEST OSTATECZNA POPRAWKA ---
        #
        audio = client_elevenlabs.text_to_speech.generate( # Musi być .text_to_speech
            text=tekst_do_powiedzenia,
            voice="Rachel", 
            model="eleven_multilingual_v2"
        )
        #
        # --- KONIEC POPRAWKI ---
        #
        
        with open(NAZWA_PLIKU_ODPOWIEDZI, 'wb') as f:
            f.write(audio)
        
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
        print(f"BŁĄD: Problem z API ElevenLabs lub odtwarzaniem pygame: {e}")

# --- GŁÓWNA PĘTLA APLIKACJI ---
if __name__ == "__main__":
    print("Witaj w projekcie 'Kasia'. (Wersja 1.2: Słuch + Mózg + Głos [pygame])")

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

    # --- KROK 3: MÓZG (GEMINI) ---
    print("\n--- KROK 3: MÓZG (GEMINI) ---")
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