import os
import re
from typing import Optional, Dict, Any, List

class AlexaIntentParser:
    """
    Local pattern-based intent grammar matcher inspired by the Alexa Skills Kit.
    Evaluates 85-90% of routine playback requests in < 10ms with ZERO API tokens.
    Handles multi-intent conjunction splitting ("and", "then").
    """

    wake_word: str = os.getenv("DAISY_WAKE_WORD", "daisy")

    @classmethod
    def set_wake_word(cls, name: str):
        if name and name.strip():
            cls.wake_word = name.strip()

    PATTERNS = [
        ("AMAZON.PauseIntent", re.compile(r"^(pause|stop|halt|hold\s+up|quiet|shut\s+up|hush|be\s+quiet|(?:pause|stop)(?:\s+the)?(?:\s+music|\s+song|\s+playback|\s+track)?)$", re.IGNORECASE)),
        ("AMAZON.ResumeIntent", re.compile(r"^(resume|continue|unpause|keep\s+playing|start\s+playing|(?:resume|continue|unpause|start|play)(?:\s+the)?(?:\s+music|\s+song|\s+playback|\s+track)?)$", re.IGNORECASE)),
        ("AMAZON.NextIntent", re.compile(r"^(next|skip|forward|(?:play\s+)?next(?:\s+song|\s+track)?|skip(?:\s+this)?(?:\s+song|\s+track)?|change(?:\s+the)?(?:\s+song|\s+track))$", re.IGNORECASE)),
        ("AMAZON.PreviousIntent", re.compile(r"^(previous|prev|back|go\s+back|(?:play\s+)?previous(?:\s+song|\s+track)?|(?:play\s+)?last(?:\s+song|\s+track)?)$", re.IGNORECASE)),
        ("AMAZON.VolumeIntent", re.compile(r"^(volume\s+(?:up|down|\d+)|turn\s+it\s+(?:up|down)|turn\s+up\s+the\s+volume|turn\s+down\s+the\s+volume|set\s+volume\s+to\s+(\d+)|mute|unmute|louder|make\s+it\s+louder|quieter|make\s+it\s+quieter)$", re.IGNORECASE)),
        ("AMAZON.ShuffleIntent", re.compile(r"^(shuffle\s+(?:on|off)|toggle\s+shuffle|shuffle)$", re.IGNORECASE)),
        ("AMAZON.RepeatIntent", re.compile(r"^(repeat\s+(?:on|off|track)|toggle\s+repeat|loop\s+this)$", re.IGNORECASE)),
        ("AMAZON.GetPlaybackInfoIntent", re.compile(r"^(what('s|\s+is)\s+playing|what\s+song\s+is\s+this|current\s+song|who\s+sings\s+this)$", re.IGNORECASE)),
        # Direct slot-based PlayMusicIntent: "play <song> [by <artist>]"
        ("PlayMusicIntent", re.compile(r"^play\s+(.+)$", re.IGNORECASE)),
    ]

    @classmethod
    def clean_utterance(cls, text: str) -> str:
        """Strips wake word (custom wake word or 'Daisy') and trailing punctuation."""
        clean = text.strip().strip("?!.,;\"'")
        wakes = list(set([re.escape(cls.wake_word.lower()), "daisy"]))
        pattern = rf"^(?:hey\s+|ok\s+|hi\s+|hello\s+)?(?:{'|'.join(wakes)})\s*[,:\s]*"
        clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip()
        # Strip leading courtesies e.g. "can you", "could you", "would you", "please"
        clean = re.sub(r"^(?:can\s+you\s+|could\s+you\s+|would\s+you\s+|please\s+)", "", clean, flags=re.IGNORECASE).strip()
        # Strip trailing courtesies e.g. "please", "thanks", "thank you"
        clean = re.sub(r"(?:\s+please|\s+thanks|\s+thank\s+you)$", "", clean, flags=re.IGNORECASE).strip()
        return clean.strip("?!.,;\"'")

    @classmethod
    def split_conjunctions(cls, prompt: str) -> List[str]:
        """Splits multi-intent commands chained with 'and' or 'then'."""
        clean = cls.clean_utterance(prompt)
        parts = re.split(r"\s+(?:and|then)\s+", clean, flags=re.IGNORECASE)
        return [cls.clean_utterance(p) for p in parts if p.strip()]

    @classmethod
    def parse_single(cls, utterance: str) -> Optional[Dict[str, Any]]:
        raw_clean = utterance.strip().strip("?!.,;\"'").lower()
        wakes = list(set([cls.wake_word.lower(), "daisy"]))
        wake_triggers = []
        for w in wakes:
            wake_triggers.extend([w, f"hey {w}", f"hi {w}", f"hello {w}", f"ok {w}", f"wake up {w}"])
        wake_triggers.extend(["are you there", "hello", "hi"])

        if raw_clean in wake_triggers:
            return {
                "intent": "AMAZON.WakeGreetingIntent",
                "action": "wake_greeting",
                "slots": {},
                "tokens": 0
            }

        # Self-Close / Direct Exit Intent: "sayonara daisy", "go home daisy", "goodbye", "shutdown daisy", etc.
        exit_phrases = [
            "sayonara", "sayonara daisy", "go home", "go home daisy",
            "goodbye", "goodbye daisy", "bye", "bye daisy", "bye bye",
            "exit daisy", "quit daisy",
            "shut down", "shutdown", "shutdown daisy", "shut down daisy",
            "turn off", "turn off daisy", "go to sleep", "sleep daisy"
        ]
        if raw_clean in exit_phrases or any(raw_clean == f"{p} {cls.wake_word.lower()}" for p in ["sayonara", "go home", "goodbye", "bye", "shutdown"]):
            return {"intent": "Daisy.ExitIntent", "action": "exit_app", "slots": {}, "tokens": 0}

        # Confirmation intents for interactive questions (e.g., "Are you sure you want to close Chrome?")
        yes_words = {
            "yes", "yeah", "yep", "sure", "ok", "okay", "confirm", "do it",
            "close it", "go ahead", "yup", "definitely", "absolutely", "please",
            "yes please", "yes do it", "yes close it", "proceed", "sounds good",
            "affirmative", "positive", "approve", "approved"
        }
        if raw_clean in yes_words or any(raw_clean == f"{w} {cls.wake_word.lower()}" for w in ["yes", "yeah", "sure", "approve"]):
            return {"intent": "AMAZON.YesIntent", "action": "confirm_yes", "slots": {}, "tokens": 0}

        no_words = {
            "no", "nope", "nah", "cancel", "cancel it", "cancel that", "don't", "dont", "nevermind",
            "never mind", "stop", "leave it", "keep it", "abort", "abort it", "no thanks",
            "don't close", "dont close", "no don't", "no dont", "negative",
            "skip", "skip it", "reject", "deny", "don't do it", "dont do it"
        }
        if raw_clean in no_words or any(raw_clean == f"{w} {cls.wake_word.lower()}" for w in ["no", "nope", "nah", "cancel", "deny"]):
            return {"intent": "AMAZON.NoIntent", "action": "confirm_no", "slots": {}, "tokens": 0}

        # Local conversational intents (0 tokens, no API key required)
        if any(raw_clean == q or raw_clean.startswith(q) for q in ["who are you", "what is your name", "introduce yourself"]):
            return {"intent": "Daisy.IdentityIntent", "action": "identity", "slots": {}, "tokens": 0}
        if any(raw_clean == q or raw_clean.startswith(q) for q in ["what can you do", "help", "what commands", "show commands"]):
            return {"intent": "Daisy.HelpIntent", "action": "help", "slots": {}, "tokens": 0}
        if any(raw_clean == q or raw_clean.startswith(q) for q in ["how are you", "how are you doing"]):
            return {"intent": "Daisy.StatusIntent", "action": "status_check", "slots": {}, "tokens": 0}
        if raw_clean in ["thank you", "thanks", "thanks daisy", "thank you daisy"]:
            return {"intent": "Daisy.ThanksIntent", "action": "thanks", "slots": {}, "tokens": 0}

        clean = cls.clean_utterance(utterance)
        clean_lower = clean.lower()

        # App Close Intent: "close Chrome", "quit Notepad", "close Spotify", "exit Calculator"
        close_match = re.match(r"^(?:close|quit|exit|kill|terminate|stop)\s+(?:app\s+)?(.+)$", clean_lower, re.IGNORECASE)
        if close_match:
            target = close_match.group(1).strip()
            clean_target = re.sub(r"^(?:the\s+|this\s+)", "", target).strip()
            if target in ["daisy", "yourself", "assistant", "app", "this app", "the app", "window"]:
                return {"intent": "Daisy.AppCloseIntent", "action": "close_app", "slots": {"app_name": "Daisy"}, "tokens": 0}
            elif clean_target not in ["music", "song", "track", "playback", "playing"]:
                return {
                    "intent": "Daisy.AppCloseIntent",
                    "action": "close_app",
                    "slots": {"app_name": target},
                    "tokens": 0
                }

        # App Launch Intent: "open Spotify", "launch VS Code", "open Chrome", "start Notepad", "open calculator"
        app_match = re.match(r"^(?:open|launch|start|run)\s+(?:up\s+)?(.+)$", clean_lower, re.IGNORECASE)
        if app_match:
            app_target = app_match.group(1).strip()
            if app_target not in ["music", "song", "track", "playing"]:
                return {
                    "intent": "Daisy.AppLaunchIntent",
                    "action": "launch_app",
                    "slots": {"app_name": app_target},
                    "tokens": 0
                }

        # Document Query Intent: "what does my resume say about Python", "search notes for project deadlines"
        rag_query_match = re.match(
            r"^(?:what\s+does\s+(?:the\s+|my\s+)?(.+?)\s+say\s+about\s+(.+)|(?:search|find\s+in|check)\s+(?:the\s+|my\s+)?(.+?)\s+(?:for|about)\s+(.+)|ask\s+(?:the\s+|my\s+)?(.+?)\s+(?:about\s+)?(.+))$",
            clean_lower,
            re.IGNORECASE
        )
        if rag_query_match:
            g = rag_query_match.groups()
            doc = g[0] or g[2] or g[4]
            q = g[1] or g[3] or g[5]
            if doc and q:
                return {
                    "intent": "Daisy.DocumentQueryIntent",
                    "action": "query_document",
                    "slots": {"doc_name": doc.strip(), "query": q.strip()},
                    "tokens": 0
                }

        # Document Summarize Intent: "summarize notes.txt on my desktop", "read my resume"
        rag_sum_match = re.match(
            r"^(?:summarize|give\s+me\s+a\s+summary\s+of|read)\s+(?:the\s+|my\s+)?(.+?)(?:\s+(?:on\s+|from\s+)(?:my\s+)?(?:desktop|documents|downloads))?$",
            clean_lower,
            re.IGNORECASE
        )
        if rag_sum_match:
            doc = rag_sum_match.group(1).strip()
            if doc and doc not in ["music", "song", "track", "playback"]:
                return {
                    "intent": "Daisy.DocumentSummarizeIntent",
                    "action": "summarize_document",
                    "slots": {"doc_name": doc},
                    "tokens": 0
                }

        for intent_name, regex in cls.PATTERNS:
            match = regex.match(clean)
            if not match:
                continue

            # Handle volume slots
            if intent_name == "AMAZON.VolumeIntent":
                full = match.group(0).lower()
                num_match = re.search(r"\d+", full)
                if num_match:
                    level = int(num_match.group(0))
                    return {"intent": intent_name, "action": "set_volume", "slots": {"level": level}, "tokens": 0}
                elif any(w in full for w in ["up", "louder"]):
                    return {"intent": intent_name, "action": "volume_up", "slots": {"delta": 10}, "tokens": 0}
                elif any(w in full for w in ["down", "quieter"]):
                    return {"intent": intent_name, "action": "volume_down", "slots": {"delta": -10}, "tokens": 0}
                elif "unmute" in full:
                    return {"intent": intent_name, "action": "set_volume", "slots": {"level": 70}, "tokens": 0}
                elif "mute" in full:
                    return {"intent": intent_name, "action": "set_volume", "slots": {"level": 0}, "tokens": 0}

            # Handle PlayMusicIntent slots
            elif intent_name == "PlayMusicIntent":
                query = match.group(1).strip()
                # Check for "play <track> by <artist>"
                by_match = re.match(r"^(.+?)\s+by\s+(.+)$", query, re.IGNORECASE)
                if by_match:
                    return {
                        "intent": intent_name,
                        "action": "play",
                        "slots": {"track": by_match.group(1).strip(), "artist": by_match.group(2).strip()},
                        "tokens": 0
                    }
                # Check for "play album <album>"
                album_match = re.match(r"^album\s+(.+)$", query, re.IGNORECASE)
                if album_match:
                    return {
                        "intent": intent_name,
                        "action": "play_album",
                        "slots": {"album": album_match.group(1).strip()},
                        "tokens": 0
                    }
                # General track / query
                return {
                    "intent": intent_name,
                    "action": "play",
                    "slots": {"query": query},
                    "tokens": 0
                }

            if intent_name == "AMAZON.ShuffleIntent":
                state = match.group(1).lower() if match.lastindex else "toggle"
                return {"intent": intent_name, "action": "toggle_shuffle", "slots": {"state": state}, "tokens": 0}

            if intent_name == "AMAZON.RepeatIntent":
                state = match.group(1).lower() if match.lastindex else "toggle"
                return {"intent": intent_name, "action": "toggle_repeat", "slots": {"state": state}, "tokens": 0}

            # Standard transport intents
            action_map = {
                "AMAZON.PauseIntent": "pause",
                "AMAZON.ResumeIntent": "resume",
                "AMAZON.NextIntent": "next_track",
                "AMAZON.PreviousIntent": "previous_track",
                "AMAZON.ShuffleIntent": "toggle_shuffle",
                "AMAZON.RepeatIntent": "toggle_repeat",
                "AMAZON.GetPlaybackInfoIntent": "get_playback_info",
            }
            return {
                "intent": intent_name,
                "action": action_map.get(intent_name, "unknown"),
                "slots": {},
                "tokens": 0
            }

        return None

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Normalizes text by removing punctuation and collapsing spaces."""
        t = re.sub(r"[^\w\s]", " ", text.lower()).strip()
        return re.sub(r"\s+", " ", t)

    @classmethod
    def parse(cls, prompt: str) -> List[Dict[str, Any]]:
        """Parses a prompt, supporting multi-command conjunctions."""
        norm = cls.normalize_text(prompt)

        # 1. Check Small Talk: "what's up", "how's it going", etc.
        if any(s in norm for s in ["what s up", "whats up", "what is up", "how is it going", "hows it going", "what are you doing"]):
            return [{
                "intent": "AMAZON.SmallTalkIntent",
                "action": "smalltalk",
                "slots": {},
                "tokens": 0
            }]

        # 2. Check Wake Greetings
        wakes = list(set([cls.wake_word.lower(), "daisy"]))
        wake_greetings = []
        for w in wakes:
            wake_greetings.extend([w, f"hey {w}", f"hi {w}", f"hello {w}", f"ok {w}", f"wake up {w}"])
        wake_greetings.extend(["are you there", "hello", "hi", "hey", "good morning", "good afternoon", "good evening", "good night"])

        if norm in wake_greetings:
            return [{
                "intent": "AMAZON.WakeGreetingIntent",
                "action": "wake_greeting",
                "slots": {},
                "tokens": 0
            }]

        # 3. Check Conversational Queries
        if any(q in norm for q in ["who are you", "what is your name", "introduce yourself"]):
            return [{"intent": "Daisy.IdentityIntent", "action": "identity", "slots": {}, "tokens": 0}]
        if any(q in norm for q in ["what can you do", "help me", "show commands"]):
            return [{"intent": "Daisy.HelpIntent", "action": "help", "slots": {}, "tokens": 0}]
        if any(q in norm for q in ["how are you", "how are you doing"]):
            return [{"intent": "Daisy.StatusIntent", "action": "status_check", "slots": {}, "tokens": 0}]
        if any(q in norm for q in ["thank you", "thanks"]):
            return [{"intent": "Daisy.ThanksIntent", "action": "thanks", "slots": {}, "tokens": 0}]

        sub_commands = cls.split_conjunctions(prompt)
        results = []
        for cmd in sub_commands:
            parsed = cls.parse_single(cmd)
            if parsed:
                results.append(parsed)
            else:
                # Needs Gemini Semantic Fallback
                results.append({
                    "intent": "GeminiSemanticFallback",
                    "action": "delegate_llm",
                    "slots": {"raw_prompt": cmd},
                    "tokens": -1 # Will consume Gemini tokens
                })
        return results

if __name__ == "__main__":
    test_cases = [
        "pause",
        "resume",
        "volume 80",
        "turn it down",
        "next song",
        "play Starboy by The Weeknd",
        "play album After Hours",
        "what's playing",
        "pause and volume 60",
        "play some late night synthwave for coding"
    ]
    for tc in test_cases:
        print(f"'{tc}' => {AlexaIntentParser.parse(tc)}")
