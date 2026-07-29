# Agent 11 — Local Voice & Messaging Notification Agent
### Option B: Fully local, no Twilio account, two-way Tamil voice + WhatsApp + SMS

## 1. Role in the System

This is the agent that turns everything the other 10 agents detect into something a human actually notices — a phone call, a WhatsApp message, or an SMS. It has two directions:

- **Outbound (automated):** when an agent detects something critical (effluent violation, safety intrusion, machine about to fail), this agent calls the responsible person, speaks the alert in Tamil, and asks for acknowledgment.
- **Inbound (two-way):** a person can also call **into** the system's local extension, and the system answers in Tamil, listens to what they say, and responds — for example, a supervisor calling to ask "இன்று என்ன பிரச்சனைகள் இருந்தது?" (what problems happened today?) and getting a spoken answer pulled live from the shared mill state.

## 2. Being honest about "fully local"

A real phone call to a real mobile number ultimately has to travel through a telecom carrier somewhere — no software stack removes that fact. "Fully local" here means: **no Twilio account, no per-message cloud billing, everything runs on your own machine/network**, using one of these two realistic paths:

| Path | What it gives you | What it needs |
|---|---|---|
| **A — Local PBX simulation (recommended for the hackathon)** | A completely free, self-hosted phone system (Asterisk) where "phones" are softphone apps on laptops/phones connected over your own wifi — the full call flow, two-way voice, IVR menu, all working exactly like a real call, demoed live | Just your laptop + a free softphone app (Zoiper/Linphone) on a teammate's phone, no internet dependency, no telecom account |
| **B — Real PSTN reach (for an actual pilot later)** | Calls/SMS that reach any real mobile number | A cheap GSM modem + local SIM card (~₹1500 hardware, one-time) for SMS/calls, no recurring cloud cost — this is the genuine "real deployment" answer, but isn't needed for the hackathon demo |

Recommendation: build and demo with **Path A**. Mention Path B in your pitch as "how this becomes a real mill deployment" — that's honest and actually sounds more credible to a jury than pretending free software can dial arbitrary real phone numbers with zero infrastructure.

## 3. Architecture Overview

```
                     ┌─────────────────────────────┐
                     │   MillState / Event Bus       │  ← from Agents 1-10
                     └───────────────┬─────────────┘
                                     │ (violation / alert event)
                                     ▼
                     ┌─────────────────────────────┐
                     │  Notification & Escalation     │
                     │  Manager (Python service)      │
                     │  decides: channel + urgency    │
                     └──┬───────────┬───────────┬────┘
                        │           │           │
              ┌─────────▼──┐ ┌──────▼─────┐ ┌───▼──────────┐
              │ Voice (IVR)  │ │ WhatsApp    │ │ SMS           │
              │ via Asterisk │ │ via         │ │ via GSM modem │
              │ PBX          │ │ whatsapp-   │ │ (or simulated │
              │              │ │ web.js      │ │ for demo)     │
              └──────┬───────┘ └─────────────┘ └───────────────┘
                     │
       ┌─────────────┼──────────────┐
       ▼                            ▼
┌───────────────┐           ┌───────────────┐
│ Outbound call   │           │ Inbound call    │
│ (system → human)│           │ (human → system)│
│ Tamil TTS plays │           │ Tamil greeting, │
│ alert, waits for│           │ STT listens,    │
│ DTMF/voice ack  │           │ answers query   │
└───────────────┘           └───────────────┘
```

## 4. Components & Tech Stack

| Component | Purpose | Tool |
|---|---|---|
| Call engine / PBX | Handles all call routing, IVR menus, DTMF, call origination | **Asterisk** (open source, self-hosted) |
| Call scripting | Runs the logic during a call (play prompt, record, decide next step) | Asterisk **AGI** scripts in Python |
| Speech-to-Text (Tamil) | Converts the caller's spoken Tamil into text | **OpenAI Whisper** (runs fully locally, multilingual, handles Tamil) |
| Text-to-Speech (Tamil) | Converts the system's response text into spoken Tamil audio | **AI4Bharat Indic TTS** (open source, built for Indian languages) or **Coqui TTS** with a Tamil model |
| Softphone (demo "human's phone") | Stand-in for a real mobile phone during the demo | **Zoiper** or **Linphone** (free apps, register as a SIP extension on your Asterisk server) |
| WhatsApp messaging | Send alert messages over WhatsApp without a paid API | **whatsapp-web.js** (Node library that automates a real WhatsApp Web session — scan a QR code once with any phone, then send programmatically) |
| SMS (real deployment path) | Send SMS without a cloud SMS API | **python-gsmmodem** + a USB GSM modem with a local SIM |
| Orchestrator bridge | Lets the call/message scripts query the mill's live state | A small **FastAPI** client calling the Master Orchestrator's API (Section 8 of the master brain doc) |
| Escalation logic | Decides who gets contacted, on what channel, and when to escalate | Python service with a simple rules engine + a scheduler (APScheduler) |

## 5. Outbound Flow — "The system calls a human"

**Trigger:** any agent (most commonly Agent 4 Effluent, Agent 6 Predictive Maintenance, or Agent 7 Worker Safety) writes a `critical` severity event to shared state.

1. Notification Manager picks up the event and looks up the escalation rule for that event type (Section 7).
2. It generates the Tamil alert text from a template, filling in the specific details (batch ID, parameter, reading).
3. It calls the Asterisk **ARI (Asterisk REST Interface)** to originate a call to the target SIP extension (the softphone standing in for the supervisor's phone).
4. When the call connects, an AGI script:
   - Plays the pre-generated (or just-in-time generated) Tamil TTS audio of the alert.
   - Uses `<Gather>`-equivalent AGI commands to wait for a DTMF keypress ("Press 1 to acknowledge") **or** records a few seconds of speech and runs it through Whisper to detect a spoken "ஆம்" (yes)/acknowledgment.
5. The acknowledgment (or lack of one) is written back to shared state.
6. If no acknowledgment within the timeout window, the Escalation Manager automatically triggers the next channel/contact in the chain (Section 7).

```python
# Simplified outbound call trigger (using Asterisk ARI)
import requests

def originate_alert_call(extension: str, message_text_tamil: str):
    audio_path = generate_tamil_tts(message_text_tamil)   # AI4Bharat/Coqui TTS
    requests.post(
        f"http://localhost:8088/ari/channels",
        params={
            "endpoint": f"PJSIP/{extension}",
            "app": "notification_app",
            "appArgs": audio_path
        },
        auth=("ariuser", "aripass")
    )
```

## 6. Inbound Flow — "A human calls the system"

**Trigger:** a supervisor dials the mill's local IVR extension from their softphone.

1. Asterisk answers the call and the AGI script plays a Tamil greeting: *"வணக்கம், இது டெக்ஸ்வர்ஸ் AI. உங்கள் கேள்வியை கேளுங்கள்."* ("Hello, this is TexVerse AI. Please ask your question.")
2. The script records the caller's spoken response (a few seconds of audio).
3. The audio is passed to **Whisper** for Tamil speech-to-text.
4. The transcribed text is matched against a small set of supported intents (keyword/pattern matching is enough for a hackathon — no need for a full NLU model):
   - "இன்று பிரச்சனை" (today's problems) → query MillState for today's flagged events across all agents
   - "எந்திரம் [name]" (machine health) → query Agent 6's maintenance queue for that machine
   - "கழிவுநீர்" (effluent) → query Agent 4's current compliance status
5. The matched intent's answer is generated as Tamil text, converted to speech via TTS, and played back to the caller.
6. If no intent matches, the system says (in Tamil) that it will connect them to a person, and the AGI script transfers the call to a human extension.

```python
# Simplified inbound AGI logic (pseudocode structure)
def handle_inbound_call(agi):
    play_audio(agi, tts_cache["greeting_ta"])
    recording = record_speech(agi, max_seconds=6)
    transcript = whisper_transcribe(recording, language="ta")
    intent = match_intent(transcript)
    if intent:
        answer_text = query_millstate_for_intent(intent)
        audio = generate_tamil_tts(answer_text)
        play_audio(agi, audio)
    else:
        play_audio(agi, tts_cache["transfer_to_human_ta"])
        transfer_call(agi, target_extension="1000")
```

## 7. Escalation Rules (Severity → Channel → Timeout)

| Severity | First contact | Channel | Ack timeout | If unacknowledged |
|---|---|---|---|---|
| Low | — | Dashboard only | — | No escalation |
| Medium | Shift supervisor | WhatsApp | 15 min | Send follow-up SMS |
| High | Compliance/safety officer | WhatsApp + SMS | 5 min | Trigger outbound call |
| Critical | Plant manager | Outbound call (Tamil IVR) | 2 min, no DTMF/voice ack | Call secondary contact, then all channels simultaneously |

This table itself should be a config file (`escalation_rules.yaml`), not hardcoded — plant managers will want to tune contacts and timeouts without a developer editing code.

## 8. WhatsApp Flow (No Paid API)

```javascript
// whatsapp-web.js — scan QR once with any phone that has WhatsApp
const { Client } = require('whatsapp-web.js');
const client = new Client();

client.on('qr', qr => { /* display QR for one-time scan */ });
client.on('ready', () => console.log('WhatsApp bridge ready'));

function sendAlert(phoneNumber, message) {
    client.sendMessage(`${phoneNumber}@c.us`, message);
}
client.initialize();
```
**Caveat to state in your pitch:** this automates a personal WhatsApp Web session, which is why it's free — for an actual production deployment at scale, the official WhatsApp Business API (through a provider) is the compliant long-term choice. Fine and honest to use this for a hackathon/pilot demo.

## 9. SMS Flow

- **Demo (no hardware):** simulate — log the "SMS" to the dashboard as if sent, clearly labeled as simulated.
- **Real deployment:** a USB GSM modem (e.g., a SIM800L-based module) with `python-gsmmodem`:
```python
from gsmmodem.modem import GsmModem

modem = GsmModem('/dev/ttyUSB0', 115200)
modem.connect()
modem.sendSms('+91XXXXXXXXXX', 'TexVerse AI Alert: Effluent violation, batch B-2026-0001')
```

## 10. How This Connects to the Other 10 Agents

- **Subscribes** to the shared event bus / MillState updates published by Agents 4, 6, 7 (the always-on monitors) as its primary triggers — these are the agents most likely to generate genuinely urgent, human-needs-to-act-now events.
- **Reads on demand** from any agent's current state when answering an inbound query (Section 6) — it doesn't duplicate data, it queries the Master Orchestrator's API live.
- **Writes back** acknowledgment records into shared state, so the dashboard shows not just "alert sent" but "acknowledged by [contact] at [time]" — this closes the loop for audit purposes, which matters a lot for the compliance-related alerts (Agent 4).

## 11. API Contract (this agent's own endpoints)

```
POST /agents/notify/trigger        { "event_type": "...", "severity": "...", "details": {...} }
POST /agents/notify/ack            { "alert_id": "...", "channel": "...", "ack_by": "..." }
GET  /agents/notify/status/{alert_id}
GET  /agents/notify/health
```

## 12. Deployment (added to your docker-compose)

```yaml
services:
  asterisk:
    image: andrius/asterisk
    ports: ["5060:5060/udp", "8088:8088"]
    volumes: ["./asterisk-config:/etc/asterisk"]

  notification-agent:
    build: ./agents/notification
    environment:
      - ARI_URL=http://asterisk:8088
      - ORCHESTRATOR_URL=http://orchestrator:8000
    depends_on: [asterisk]

  whatsapp-bridge:
    build: ./agents/notification/whatsapp
    volumes: ["./wa-session:/app/session"]   # persists the QR login
```

## 13. Testing Strategy

- Test outbound flow with a softphone registered on your own laptop first — call yourself before involving a teammate's phone.
- Test Whisper's Tamil transcription accuracy against a handful of pre-recorded sample phrases before relying on it live — background noise at a hackathon venue will affect accuracy, so keep the required spoken vocabulary small and forgiving (a DTMF "press 1" fallback is more reliable than requiring speech recognition to work perfectly live).
- Test the escalation timeout logic with a short artificial timeout (10 seconds instead of 5 minutes) during development so you don't wait real minutes per test cycle.

## 14. Production Considerations

- Asterisk running continuously needs its own monitoring — if the PBX process crashes, no alerts of any kind go out; treat it as a critical-path service with its own health check and auto-restart.
- Store call recordings and transcripts only as long as genuinely needed, and be clear with anyone whose voice is recorded that calls may be processed by a speech-to-text system.
- The WhatsApp Web automation approach is inherently tied to one phone's session — for a real multi-shift deployment, plan the migration to the official WhatsApp Business API sooner rather than later.

## 15. What to Say in the Pitch

*"Every alert in TexVerse AI can reach a person the way they'd actually respond fastest — in Tamil, by voice, with no cloud telephony bill. And it's two-way: a supervisor can call the system itself and ask what happened today, in Tamil, and get a spoken answer pulled live from the mill's own data. This is built entirely on free, self-hosted, open-source tools — and the same architecture scales to a real GSM line or WhatsApp Business API without changing how the rest of the system works."*
