import sounddevice as sd
import scipy.io.wavfile as wavfile
import numpy as np
import time
import os

# --- Ustawienia Nagrywania ---
SAMPLERATE = 44100
CZAS_NAGRYWANIA_S = 5

# --- NOWOŚĆ: Ustawienia ścieżek ---
FOLDER_NAGRAN = "temp_audio"  # Nazwa naszego folderu na "śmieci"
NAZWA_PLIKU = "nagranie_testowe.wav"
# Mądrze łączymy ścieżkę, żeby działało na każdym systemie
SCIEZKA_PLIKU = os.path.join(FOLDER_NAGRAN, NAZWA_PLIKU)

def nagraj_audio(nazwa_pliku, czas_trwania_s, samplerate):
    """
    Nagrywa audio z domyślnego mikrofonu i zapisuje do pliku .wav.
    """
    print("Zaczynam nagrywanie...")
    print(f"Mów teraz! Masz {czas_trwania_s} sekund.")

    nagranie = sd.rec(int(czas_trwania_s * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()  
    print("Nagrywanie zakończone.")

    # Zapisywanie pliku
    wavfile.write(nazwa_pliku, samplerate, nagranie)
    print(f"Nagranie zapisane jako: {nazwa_pliku}")


# --- Główna część skryptu ---
if __name__ == "__main__":
    print("Witaj w projekcie 'Kasia'.")

    # --- NOWOŚĆ: Sprawdzanie i tworzenie folderu ---
    # Upewniamy się, że nasz folder na nagrania istnieje
    if not os.path.exists(FOLDER_NAGRAN):
        print(f"Tworzę folder na nagrania: {FOLDER_NAGRAN}")
        os.makedirs(FOLDER_NAGRAN)
    # --- Koniec nowej części ---

    print("Za chwilę rozpocznie się test nagrywania mikrofonu.")
    time.sleep(2) 

    # Wywołujemy funkcję z nową, pełną ścieżką
    nagraj_audio(SCIEZKA_PLIKU, CZAS_NAGRYWANIA_S, SAMPLERATE)

    print(f"Test zakończony. Sprawdź plik w folderze {FOLDER_NAGRAN}.")