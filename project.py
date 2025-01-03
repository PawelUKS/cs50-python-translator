import customtkinter
import requests
import re
import json
from googletrans import Translator
from spellchecker import SpellChecker


class SimpleTranslatorApp:
    def __init__(self, root):
        self.root = root
        # translater
        self.google_translator = FallbackTranslator()
        #load deepl config
        config = SimpleTranslatorApp.load_config()
        self.deepl_translator = MainTranslator(api_key=config["deepl_api_key"])

        # gui settings
        self.gui_settings()

        # UI-Elemente
        self.label_header = None
        self.label_left = None
        self.label_right = None
        self.entry_left = None
        self.entry_right = None
        self.switch_button = None
        self.translate_button = None
        self.status_label = None

        self.create_widgets()

    def gui_settings(self):
        # GUI-Einstellungen
        customtkinter.set_appearance_mode("dark")
        self.root.title("Simple Translator")
        window_width = 600
        window_height = 300

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_coordinate = int((screen_width / 2) - (window_width / 2))
        y_coordinate = int((screen_height / 2) - window_height)
        self.root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

        self.root.grid_rowconfigure(4, weight=1)  # Leerzeile vor der Statusleiste
        self.root.grid_rowconfigure(5, weight=0)  # Statusleiste (fixierte Höhe)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)

    def create_widgets(self):
        # Überschrift
        self.label_header = customtkinter.CTkLabel(
            self.root,
            text="Simple Translator ",
            font=("Monotype Corsiva", 40, "bold"),
            text_color="#FF5733"
        )
        self.label_header.grid(row=0, column=0, columnspan=3, pady=20)

        # Sprachen-Labels
        self.label_left = customtkinter.CTkLabel(self.root, text="English", font=("Arial", 14))
        self.label_left.grid(row=1, column=0, padx=20, pady=(5, 0), sticky="n")

        self.label_right = customtkinter.CTkLabel(self.root, text="German", font=("Arial", 14))
        self.label_right.grid(row=1, column=2, padx=20, pady=(5, 0), sticky="n")

        # Eingabefelder
        self.entry_left = customtkinter.CTkEntry(self.root, width=200, justify="center", validate="key",
                                                 validatecommand=(
                                                     self.root.register(SimpleTranslatorApp.validate_input), "%P"))
        self.entry_left.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.entry_right = customtkinter.CTkEntry(self.root, width=200, justify="center")
        self.entry_right.grid(row=2, column=2, padx=20, pady=10, sticky="ew")
        self.entry_right.bind("<Key>", lambda e: None if (e.keysym == "c" and (e.state & 0x4)) else "break")

        # Buttons
        self.switch_button = customtkinter.CTkButton(self.root, text="Switch", command=self.switch_languages, width=80)
        self.switch_button.grid(row=2, column=1, padx=20, pady=10)

        self.translate_button = customtkinter.CTkButton(self.root, text="Translate", command=self.translate_text,
                                                        width=160, height=40)
        self.translate_button.grid(row=3, column=1, padx=20, pady=10)

        # Statusleiste
        self.status_label = customtkinter.CTkLabel(
            self.root,
            text="Ready",
            font=("Arial", 12),
            text_color="green",
            fg_color="#333333",  # Dunkelgrauer Hintergrund für die Leiste
            height=23
        )
        self.status_label.grid(row=5, column=0, columnspan=3, sticky="nsew")

    @staticmethod
    def load_config(file_path="config.json"):
        """Lädt eine JSON-Konfigurationsdatei."""
        try:
            with open(file_path, "r") as config_file:
                return json.load(config_file)
        except FileNotFoundError:
            raise Exception(f"Die Konfigurationsdatei '{file_path}' wurde nicht gefunden.")
        except json.JSONDecodeError:
            raise Exception(f"Fehler beim Lesen der Konfigurationsdatei '{file_path}'. Überprüfe das JSON-Format.")

    @staticmethod
    def validate_input(value):
        # Regulärer Ausdruck für erlaubte Zeichen: nur Buchstaben (einschließlich deutscher Umlaute) und Leerzeichen
        pattern = "^[a-zA-ZäöüÄÖÜß]*$"
        if re.match(pattern, value):
            return True
        return False

    def switch_languages(self):
        # Sprachen wechseln
        left_text = self.label_left.cget("text")
        right_text = self.label_right.cget("text")
        self.label_left.configure(text=right_text)
        self.label_right.configure(text=left_text)

        # Leere das rechte Eingabefeld (entry_right)
        self.entry_right.delete(0, "end")



    def is_in_dict(self, text, language):
        check = SpellChecker(language=language)
        if text in check:
            return True
        else:
            return False

    def translate_text(self):
        left_input = self.entry_left.get().strip()
        source_lang = "en" if self.label_left.cget("text") == "English" else "de"
        target_lang = "de" if source_lang == "en" else "en"
        if not left_input:
            self.status_label.configure(text="No input given.", text_color="red")
            self.entry_right.delete(0, "end")
            return

        if not self.is_in_dict(left_input, source_lang):
            self.status_label.configure(text="No translation available for the given input.", text_color="red")
            self.entry_right.delete(0, "end")
            return
        # Versuche die Übersetzung mit der API
        try:
            translated_text = self.deepl_translator.translate(left_input.lower(), source_lang, target_lang)

            if translated_text:
                print("Using API Translator")
                self.status_label.configure(text="Translated with DeepL", text_color="green")
            else:
                raise Exception("API returned no result")
        except Exception as e:
            #print(f"API failed: {e}")
            translated_text = self.google_translator.translate(left_input, source_lang, target_lang)
            if translated_text:
                print("Using Google Translate as fallback")
                self.status_label.configure(text="Translated with Google", text_color="green")
            else:
                print("Translation failed completely.")
                self.entry_right.delete(0, "end")
                self.entry_right.insert(0, "Error: Translation failed.")
                self.status_label.configure(text="Translation failed completely", text_color="red")
                return
        # Übersetzte Ausgabe anzeigen

        self.entry_right.delete(0, "end")
        self.entry_right.insert(0, translated_text)


class MainTranslator:
    def __init__(self, api_key, api_url="https://api-free.deepl.com/v2/translate"):
        """
        Initialisiert die API-Verbindung mit dem angegebenen API-Schlüssel und der API-URL.

        :param api_key: Dein DeepL API-Schlüssel
        :param api_url: URL der DeepL API (Standard: Free-Version)
        """
        self.api_key = api_key
        self.api_url = api_url

    def translate(self, text, source_lang, target_lang):
        """
        Übersetzt einen Text mit der DeepL API.

        :param text: Der zu übersetzende Text
        :param source_lang: Quellsprache (z. B. 'DE' für Deutsch)
        :param target_lang: Zielsprache (z. B. 'EN' für Englisch)
        :return: Der übersetzte Text
        """
        params = {
            "auth_key": self.api_key,
            "text": text,
            "source_lang": source_lang.upper(),
            "target_lang": target_lang.upper(),
        }

        try:
            response = requests.post(self.api_url, data=params)
            response.raise_for_status()  # Hebt HTTP-Fehler hervor (z. B. 401 oder 403)
            result = response.json()

            # Überprüfen, ob die Antwort das erwartete Format hat
            if "translations" in result and len(result["translations"]) > 0:
                return result["translations"][0]["text"]
            else:
                raise KeyError("DeepL API returned an unexpected format.")

        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP Error: {e}")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error: Unable to reach DeepL API.")
        except KeyError as e:
            raise Exception(f"Unexpected API response structure: {e}")
        except Exception as e:
            raise Exception(f"An unknown error occurred: {e}")


class FallbackTranslator:
    def __init__(self):
        self.translator = Translator()

    def translate(self, text, source_lang, target_lang):
        try:
            result = self.translator.translate(text, src=source_lang, dest=target_lang)
            return result.text
        except Exception as e:
            print(f"Google Translator Error: {e}")
            return None


if __name__ == "__main__":
    root = customtkinter.CTk()
    app = SimpleTranslatorApp(root)
    root.mainloop()
