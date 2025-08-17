Setup

This is a demo of a voice agent that can talk in Urdu using LiveKit and Uplift AIs voice. For complete tutorial visit https://docs.upliftai.org

1. `pip install -r requirements.txt` (install required libraries)
2. `python agent.py download-files` (setup the offline model stuff needed.)
3. Setup the keys in `.env` file:
   - `OPENAI_API_KEY` (get this from https://platform.openai.com/account/api-keys)
   - `UPLIFTAI_API_KEY` (get this from https://platform.upliftai.org/studio/home)
   - `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` (get these from https://livekit.io/ by creating a free account, and visit API keys page)
3. Start agent multiple options:
  - `python agent.py console` -> talk directly in the console
  - `python agent.py dev` -> talk through web interface 
    - before this you will need to create livekit credentials that you can get from https://livekit.io/ by creating a free acount, and visit API keys page.
      - Put the following in your .env file:
        - LIVEKIT_URL
        - LIVEKIT_API_KEY
        - LIVEKIT_API_SECRET