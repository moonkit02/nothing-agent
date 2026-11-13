# nothing-agent

A personal voice assistant for the Nothing Phone 3a. You speak a command in
Malaysian rojak (Mandarin, English, Malay). The assistant works out what you
want and runs one of a few hardcoded actions, such as playing a song in
YouTube Music.

Single user. Overfitting to one voice and one account is fine.

## Topology (MVP)

```
phone                                   PC (home)
  speak -> speech-to-text --[tunnel]--> brain.py (/parse)
                                           returns {intent, query}
  <----------------------------------- 
  do the action (e.g. play the song)
```

The phone captures audio, turns it into text, and sends the text to the brain
on the PC. The brain returns a structured action. The phone performs it.

The PC side is a stub for now. Whether the PC earns its place over the phone
calling an LLM API directly is still an open design question.

## Run the brain (PC)

```
python3 brain.py          # start the server on 127.0.0.1:8080
python3 brain.py --check  # run the self-check
```

Expose it to the phone with a tunnel that forwards to 127.0.0.1:8080.
