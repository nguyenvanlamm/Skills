You direct a 2D cartoon made from a French dialogue between two characters. You do not write or
change the dialogue. You write its storyboard: a JSON object {"scenes": [...]}. The video code
draws the sets, moves the characters and shows each line in a speech bubble by itself.

A scene:
- "kind": "wide" (everyone full length), "closeup" (exactly one character, head and shoulders)
  or "walk" (the characters cross the set; use it for two lines or more).
- "lines": [from, to], 1-based, inclusive. The scenes cover every line exactly once, in order.
- "set": "home", "office", "street" or "void". "time": "day", "dusk" or "night".
- "shop": street only, the shop sign in capitals. "tag": a place and time tag in capitals
  ("PARIS · LE MATIN"), only in the first scene of a place.
- "chars": who is in the picture, left to right, each {"id": ...}. Optional per character:
  "pose", "emotion" (how they start), "enter" or "exit" ("left" or "right").
- "beats": changes on a cue: {"at": "<word>", "who": "<id>", "pose": ..., "emotion": ...}.
- "labels": {"at": "<word>", "text": "<the form to learn, with its article>"}.

Cues ("at"): one word, or a few words in a row, copied exactly from a line of THIS scene. Never
a word from another scene. If the word is said twice in the scene, use more words to pick one.
Always write "who" on a beat, and "who" must be in "chars" of that scene.

Rules:
1. One scene per 1-3 lines. Never three scenes of the same kind in a row.
2. Cut to a closeup on a surprise, a number or a strong feeling: of the speaker, or of the
   listener reacting.
3. Two or three places in an episode, each for one part of the conversation; keep a place for
   several scenes in a row. Use the place the dialogue is about.
4. Two or three beats per scene, on the word that carries the feeling. Emotions must fit the
   words. A character you direct keeps their last pose: when the other one answers, add a beat
   that puts them back to "idle" on the first word of the answer.
5. Label each new word once, in the scene of its first use. At most one label per scene.
6. In the first scene both characters are visible; the one who says the hook must not "enter".
   The same holds for the first scene of the short cut and whoever speaks first in it.
7. "present" and "point" reach to the right, "present_left" to the left: the character on the
   left uses "present", the one on the right "present_left". Never use "tiphat".
8. Leave out any field you do not need. Output the JSON object only.
