import customtkinter as ctk
import requests
import re
import json
from googletrans import Translator
from spellchecker import SpellChecker
import textdistance
from abc import ABC, abstractmethod
import inspect
import sys

#######################################################################################################################
# utils.py -> For Helper Classes and Methods ###########################################################################
#######################################################################################################################


class Utils:

    # Utils -> Provides Helper Functions For Configuration And Input Validation.

    # Location Of The API Data
    CONFIG_FILE_PATH = "config.json"

    @staticmethod
    def load_config(api_name=None, config_file=None):

        # This Method Loads Configuration Data From A JSON File
        config_file = config_file or Utils.CONFIG_FILE_PATH
        try:
            with open(config_file, "r") as file:
                config = json.load(file)
            if api_name:
                api_config = config.get(api_name)
                if not api_config:
                    raise KeyError(f"Missing Configuration For {api_name} In {config_file}")
                return api_config
            return config
        except FileNotFoundError:
            raise Exception(f"Configuration File {config_file} Missing!")
        except json.JSONDecodeError:
            raise Exception(f"Error Reading The JSON File: {config_file}!")
        except KeyError as e:
            raise Exception(str(e))


    @staticmethod
    def load_translators():

        # Scans The Config File And Automatically Instantiates All Enabled Translators.
        config = Utils.load_config()

        translators = []

        # Get all classes in the current module
        current_module = sys.modules[__name__]

        for translator_name, settings in config.items():

            # Check if the translator is enabled in the configuration
            if settings.get("enabled", False):
                try:
                    # Check if a class with the given name exists in the current module
                    translator_class = getattr(current_module, translator_name, None)

                    # If the class exists and is a valid class, create an instance
                    if translator_class and inspect.isclass(translator_class):
                        translators.append(translator_class())

                except Exception as e:
                    print(f"[Error Loading {translator_name}] {e}")

        return translators

    @staticmethod
    def validate_input(value):

        # This Method Validates The Input Using A Regular Expression
        # It Ensures That Only Alphabetical Characters And German Umlauts Are Allowed
        pattern = "^[a-zA-ZäöüÄÖÜß]*$"
        return bool(re.match(pattern, value))


#######################################################################################################################
# model.py -> Handles Application Logic, Data Structures, And Persistence #############################################
#######################################################################################################################

class TranslatorStrategy(ABC):

    # Abstract Base Class For Translation Strategies.

    # This Class Defines A Common Interface For Different Translation Implementations
    # Any Subclass Must Implement The `translate` Method

    @abstractmethod
    def translate(self, text, source_lang, target_lang):
        pass


class DeepLTranslator(TranslatorStrategy):

    # DeepLTranslator Class That Connects To The DeepL API For Translations

    def __init__(self):
        try:
            config = Utils.load_config("DeepLTranslator")
            self.api_key = config["api_key"]
            self.api_url = config["api_url"]

            if not self.api_key or not self.api_url:
                raise ValueError("DeepL Configuration Contains Empty Values For 'api_key' Or 'api_url'.")

        except KeyError as e:
            raise Exception(f"Missing Configuration For DeepLTranslator: {e}")
        except ValueError as e:
            raise Exception(f"Invalid Configuration For DeepLTranslator: {e}")

    def translate(self, text, source_lang, target_lang):
        params = {"auth_key": self.api_key,
                  "text": text,
                  "source_lang": source_lang.upper(),
                  "target_lang": target_lang.upper(),
                  }
        try:
            response = requests.post(self.api_url, data=params)
            response.raise_for_status()
            result = response.json()
            if "translations" in result and len(result["translations"]) > 0:
                return result["translations"][0]["text"], "DeepLTranslator"
            return None, "DeepLTranslator"

        except requests.exceptions.RequestException as e:
            print(f"[DeepLTranslator API-Error] {e}")
            return None, "DeepLTranslator"

        except AttributeError as e:
            print(f"[DeepLTranslator Error] {e}")
            return None, "DeepLTranslator"

        except Exception as e:
            print(f"[DeepLTranslator Unknown Error] {e}")
            return None, "DeepLTranslator"


class GoogleTranslator(TranslatorStrategy):

    # GoogleTranslator Module That Uses The Google Translate API

    def __init__(self):
        self.translator = Translator()

    def translate(self, text, source_lang, target_lang):
        try:
            # Google Translate Expects Lowercase Language Codes (For Example, "en" Instead Of "EN")
            source_lang = source_lang.lower()
            target_lang = target_lang.lower()

            result = self.translator.translate(text, src=source_lang, dest=target_lang)

            if not hasattr(result, "text"):
                raise AttributeError("Object Is Empty Or Invalid")

            return result.text, "GoogleTranslator"

        except AttributeError as e:
            print(f"[GoogleTranslator Error] {e}")
            return None, "GoogleTranslator"

        except requests.exceptions.RequestException as e:
            print(f"[GoogleTranslator API-Error] {e}")
            return None, "GoogleTranslator"

        except Exception as e:
            print(f"[GoogleTranslator Unknown Error] {e}")
            return None, "GoogleTranslator"


class FallbackTranslator(TranslatorStrategy):

    # FallbackTranslator Implements The Strategy Pattern For Translation

    # This Class Tries To Translate Using Multiple Translator Instances
    # If One Translator Fails, The Next One In The List Is Used
    # If No Translator Succeeds, An Error Message Is Returned

    def __init__(self, translators):
        if not translators:
            raise ValueError("Translator List Cannot Be Empty.")
        self.translators = translators

    def translate(self, text, source_lang, target_lang):
        for translator in self.translators:

            # Store The Translator's Class Name In `name`
            name = type(translator).__name__
            try:
                result, name = translator.translate(text, source_lang, target_lang)
                if result is not None:
                    return result, name
            except Exception as e:
                print(f"[Error In {name}] {e}")
                # Try The Next Translator If An Error Occurs
                continue

        return "Translation failed.", "No API worked"


class TranslatorModel:

    # TranslatorModel Handles Text Translation And Spelling Suggestions

    # This Class Uses A Fallback Translator To Attempt Translations Across Multiple APIs
    # It Also Provides Spelling Checking And Fuzzy Search For Similar Words

    def __init__(self):
        # List Of Available Translators
        available_translators = Utils.load_translators()
        if not available_translators:
            raise ValueError("No Translators Are Enabled In The Configuration!")
        self.translator = FallbackTranslator(available_translators)

    def translate_text(self, text, source_lang, target_lang):
        return self.translator.translate(text, source_lang, target_lang)

    def is_in_dict(self, text, language):

        # Check If The Input Is Available In the Dictionary
        return text in SpellChecker(language=language)

    def fuzzy_search(self, word, language, n=8, max_distance=1):

        # Use Damerau-Levenshtein Algorithm To Find Similar Words
        spell = SpellChecker(language=language)
        word_list = list(spell.word_frequency.dictionary.keys())

        # Is No Words Are Available
        if not word_list:
            return [word]

        # Calculate The Similarity
        similar_words = sorted(
            word_list,
            key=lambda w: textdistance.damerau_levenshtein(word.lower(), w.lower())
        )
        # Filter Words That Have A Distance Of `max_distance` And Start With The Same Letter As The Input Word.
        filtered_words = [
            w for w in similar_words
            if textdistance.damerau_levenshtein(word.lower(), w.lower()) <= max_distance
               and w.lower().startswith(word.lower()[0])
        ]

        # Return Up To `n` Words Without Random Entries.
        return filtered_words[:min(n, len(filtered_words))]


#######################################################################################################################
# view.py -> Manages The Graphical User Interface (GUI) And User Interactions #########################################
#######################################################################################################################

class TranslatorView:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.suggestion_buttons = []
        self.setup_ui()

    def setup_ui(self):

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Custom Theme Settings
        custom_fonts = {
            "header": ("Poppins", 35, "bold"),
            "label": ("Roboto", 18, "bold"),
            "button": ("Montserrat", 16, "bold"),
            "entry": ("Inter", 16, "bold"),
            "status": ("Roboto", 18, "bold"),
            "suggestion": ("Montserrat", 14, "italic", "bold")
        }

        custom_colors = {
            "header": "#A3E135",
            "label": "#D1D5DB",
            "button_text": "white",
            "button_bg": "#4CAF50",
            "button_hover": "#388E3C",
            "entry_text": "#E5E7EB",
            "entry_bg": "#005c29",
            "entry_border": "#66BB6A",
            "entry_placeholder": "#9CA3AF",
            "status_bg": "#4CAF50",
            "suggestion_bg": "#1E1E1E",
            "suggestion_text": "#A3E635"
        }

        # Window Title
        self.root.title("Simple Translator Vers. 1.0")

        # Application Window Size
        window_width, window_height = 400, 700

        # Calculate The Center Of The Screen
        screen_width, screen_height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x_coordinate, y_coordinate = (screen_width - window_width) // 2, (screen_height - window_height) // 2

        # Center The Application Window On The Screen
        self.root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

        # Configure The Grid Layout
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(6, weight=0)
        self.root.grid_rowconfigure(7, weight=0)
        self.root.grid_rowconfigure(8, weight=1)
        self.root.grid_rowconfigure(9, weight=0)

        # Set Title
        self.label_header = ctk.CTkLabel(
            self.root,
            text="Simple Translator",
            font=custom_fonts["header"],
            text_color=custom_colors["header"]
        )
        self.label_header.grid(row=0, column=0, columnspan=3, pady=20)

        # Input Field Label
        self.label_left = ctk.CTkLabel(
            self.root,
            text="English",
            font=custom_fonts["label"],
            text_color=custom_colors["label"]
        )
        self.label_left.grid(row=1, column=0, columnspan=3, padx=20, pady=(6, 0))

        # Output Field Label
        self.label_right = ctk.CTkLabel(
            self.root,
            text="German",
            font=custom_fonts["label"],
            text_color=custom_colors["label"]
        )
        self.label_right.grid(row=4, column=0, columnspan=3, padx=20, pady=(6, 0))

        # Input Field Entry
        self.entry_left = ctk.CTkEntry(
            self.root,
            width=200,
            corner_radius=20,
            font=custom_fonts["entry"], text_color=custom_colors["entry_text"],
            fg_color=custom_colors["entry_bg"],
            border_color=custom_colors["entry_border"],
            placeholder_text_color=custom_colors["entry_placeholder"],
            justify="center",
            height=34,
            validate="key",
            validatecommand=(self.root.register(Utils.validate_input), "%P")
        )
        self.entry_left.grid(row=2, column=0, columnspan=3, padx=60, pady=0, sticky="ew")

        # Output Field Entry
        self.entry_right = ctk.CTkEntry(
            self.root,
            width=200,
            font=custom_fonts["entry"],
            text_color=custom_colors["entry_text"],
            fg_color=custom_colors["entry_bg"],
            border_color=custom_colors["entry_border"],
            placeholder_text_color=custom_colors["entry_placeholder"],
            justify="center",
            height=34,
            corner_radius=20
        )
        self.entry_right.grid(row=5, column=0, columnspan=3, padx=60, pady=0, sticky="ew")
        self.entry_right.bind("<Key>", lambda e: None if (e.keysym == "c" and (e.state & 0x4)) else "break")

        # Switch Button
        self.switch_button = ctk.CTkButton(
            self.root,
            text="Switch",
            corner_radius=20,
            font=custom_fonts["button"],
            text_color=custom_colors["button_text"],
            fg_color=custom_colors["button_bg"],
            hover_color=custom_colors["button_hover"],
            command=self.switch_languages,
            width=80,
            height=34
        )
        self.switch_button.grid(row=3, column=0, columnspan=3, padx=80, pady=15)

        # Translate Button
        self.translate_button = ctk.CTkButton(
            self.root,
            text="Translate",
            corner_radius=20,
            font=custom_fonts["button"],
            text_color=custom_colors["button_text"],
            fg_color=custom_colors["button_bg"],
            hover_color=custom_colors["button_hover"],
            command=self.controller.translate_text,
            height=34
        )
        self.translate_button.grid(row=6, column=0, columnspan=3, padx=20, pady=15)

        # Status Label
        self.status_label = ctk.CTkLabel(
            self.root,
            text="Ready",
            text_color=custom_colors["button_text"],
            font=custom_fonts["status"],
            fg_color=custom_colors["status_bg"],
            height=30
        )
        self.status_label.grid(row=9, column=0, columnspan=3, padx=0, pady=(5, 0), sticky="nsew")

        # Create A Frame For Suggestions And Hide It Initially
        self.suggestion_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.suggestion_frame.grid(row=7, column=0, columnspan=3, pady=(0, 0))

        # Label Displaying The "Did You Mean" Text
        self.suggestion_label = ctk.CTkLabel(
            self.suggestion_frame,
            text="Did You Mean:",
            font=custom_fonts["suggestion"],
            text_color=custom_colors["suggestion_text"]
        )

        # Position The Label At The Top Inside The Frame
        self.suggestion_label.pack(side="top", pady=(5, 2))

        # Hide The Label Initially
        self.suggestion_label.pack_forget()

        # Configuration For Suggestion Buttons
        self.suggestion_button_config = {
            "corner_radius": 20,
            "width": 200,
            "fg_color": "#4CAF50",
            "hover_color": "#388E3C",
            "text_color": "white",
            "font": ("Poppins", 16, "bold")
        }

    def switch_languages(self):

        # Swaps The Source And Target Languages And Clears The Output Field
        left_text = self.label_left.cget("text")
        right_text = self.label_right.cget("text")
        self.label_left.configure(text=right_text)
        self.label_right.configure(text=left_text)

        # Clear The Output Field
        self.entry_right.delete(0, "end")

        # Reset Status Label To Indicate Ready State
        self.show_status("Ready", color="white")

    def get_input_text(self):
        return self.entry_left.get()

    def get_source_language(self):
        return "en" if self.label_left.cget("text") == "English" else "de"

    def get_target_language(self):
        return "de" if self.get_source_language() == "en" else "en"

    def set_input_text(self, text):
        self.entry_left.delete(0, "end")
        self.entry_left.insert(0, text)

    def show_translation(self, translation, api_used):
        self.clear_suggestions()
        self.entry_right.delete(0, "end")
        input_text = self.get_input_text()

        if self.get_source_language() == "de":

            # If The Input Is Fully Uppercase, The Translation Remains Uppercase
            if input_text.isupper():
                translation = translation.upper()

            # Otherwise, Always Lowercase
            else:
                translation = translation.lower()

        if self.get_source_language() == "en":

            # If The Input Is Fully Uppercase, The Translation Remains Uppercase
            if input_text.isupper():
                translation = translation.upper()

            # Otherwise, Capitalize First Letter
            else:
                translation = translation.capitalize()

        self.entry_right.insert(0, translation)
        self.status_label.configure(text=f"Translated with {api_used}", text_color="black")

    def show_status(self, message, color="#7a0000"):
        self.status_label.configure(text=message, text_color=color)

    def show_suggestions(self, suggestions):

        # Displays The Found Word Suggestions In The GUI
        self.clear_suggestions()

        if suggestions:
            self.suggestion_frame.grid()
            self.suggestion_label.pack(side="top", pady=(5, 2))

            for suggestion in suggestions:
                btn = ctk.CTkButton(
                    self.suggestion_frame,
                    text=suggestion,
                    command=lambda s=suggestion: self.controller.on_suggestion_click(s),
                    **self.suggestion_button_config
                )
                # Show Button
                btn.pack(side="top", padx=10, pady=2)
                # Store Button
                self.suggestion_buttons.append(btn)

        else:

            # Remove Frame If No Suggestions
            self.suggestion_frame.grid_remove()
            # Remove Label
            self.suggestion_label.pack_forget()

    def clear_suggestions(self):

        # Removes All Suggestion Buttons And Hides The Suggestion Label
        for btn in self.suggestion_buttons:
            btn.destroy()
        self.suggestion_buttons = []
        self.suggestion_label.pack_forget()


#######################################################################################################################
# controller.py -> Manages The Application Logic And Connects The Model With The View #################################
#######################################################################################################################

class TranslatorController:
    def __init__(self, model, view):
        self.model = model
        self.view = view

    def translate_text(self):
        text = self.view.get_input_text().strip()
        source_lang = self.view.get_source_language()
        target_lang = self.view.get_target_language()

        if not text:
            self.view.entry_right.delete(0, "end")
            self.view.show_status("No input given")
            return

        if not self.model.is_in_dict(text, source_lang):
            self.view.entry_right.delete(0, "end")
            self.view.show_status("Translation failed")
            suggestions = self.model.fuzzy_search(text, source_lang)
            return self.view.show_suggestions(suggestions)

        translation, api_used = self.model.translate_text(text, source_lang, target_lang)
        if translation:
            self.view.show_translation(translation, api_used)
        else:
            self.view.show_status("Translation failed")

    def switch_languages(self):
        self.view.switch_languages()

    def clear_suggestions(self):
        self.view.clear_suggestions()

    def on_suggestion_click(self, suggestion):
        self.view.set_input_text(suggestion)


#######################################################################################################################
# main.py -> Initializes And Starts The Application ###################################################################
#######################################################################################################################
if __name__ == "__main__":
    root = ctk.CTk(fg_color="#121212")
    model = TranslatorModel()
    controller = TranslatorController(model, None)
    view = TranslatorView(root, controller)
    controller.view = view
    root.mainloop()
