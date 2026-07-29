import os
from gtts import gTTS

TAMIL_ALERT_TEMPLATES = {
    "effluent_ph": "எச்சரிக்கை! கழிவுநீர் சுத்திகரிப்பு பிரிவில் pH அளவு {reading} ஆக உயர்ந்துள்ளது. உடனே சரிபார்க்கவும்.",
    "weaving_defect": "கவனம்! தறி எந்திரம் {loom_id} இல் துணி குறைபாடு கண்டறியப்பட்டுள்ளது. ரோல் பொசிஷன் {roll_pos} மீட்டர்கள்.",
    "safety_violation": "அவசர எச்சரிக்கை! பகுதி {zone} இல் பாதுகாப்பு கவசம் அணிவதில்லை என கண்டறியப்பட்டுள்ளது.",
    "energy_surge": "எச்சரிக்கை! எந்திரம் {machine} இல் அதிக மின் நுகர்வு {reading} kW ஏற்பட்டுள்ளது.",
    "general": "எச்சரிக்கை! {agent_name} இலிருந்து அவசர அறிவிப்பு: {message}"
}

TAMIL_INBOUND_RESPONSES = {
    "today_problems": "இன்று ஆலையில் 2 அவசர எச்சரிக்கைகள் பதிவாகியுள்ளன: 1. கழிவுநீர் pH வரம்பு மீறல், 2. தறி எந்திரம் 4 பழுது.",
    "shift_status": "தற்போதைய ஷிப்ட் இயக்கம் சீராக உள்ளது. உற்பத்தி திறன் 94 சதவீதமாக உள்ளது.",
    "water_status": "கழிவுநீர் சுத்திகரிப்பு பிளாண்ட் 100 சதவீதம் ZLD விதிமுறைகளுக்கு உட்பட்டு இயங்குகிறது.",
    "unknown": "வணக்கம். உங்கள் கேள்வி புரியவில்லை. 'இன்று பிரச்சனை' அல்லது 'ஷிப்ட் விபரம்' எனக் கேட்கவும்."
}

def generate_tamil_alert_text(event_type: str, details: dict) -> str:
    template = TAMIL_ALERT_TEMPLATES.get(event_type, TAMIL_ALERT_TEMPLATES["general"])
    try:
        return template.format(**details)
    except Exception:
        return f"எச்சரிக்கை! {event_type}: {str(details)}"

def process_inbound_speech_query(transcription_tamil: str) -> str:
    query = transcription_tamil.strip()
    if "பிரச்சனை" in query or "பிரச்சனைகள்" in query or "problems" in query.lower():
        return TAMIL_INBOUND_RESPONSES["today_problems"]
    elif "ஷிப்ட்" in query or "shift" in query.lower():
        return TAMIL_INBOUND_RESPONSES["shift_status"]
    elif "நீர்" in query or "கழிவுநீர்" in query or "water" in query.lower():
        return TAMIL_INBOUND_RESPONSES["water_status"]
    else:
        return TAMIL_INBOUND_RESPONSES["unknown"]

def generate_tamil_tts_audio(text: str, output_path: str = "alert_audio.mp3") -> bool:
    """
    Synthesizes Tamil text to speech and saves it as an audio file (.mp3).
    """
    try:
        # Use gTTS to generate the Tamil speech audio file
        tts = gTTS(text=text, lang='ta')
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        tts.save(output_path)
        print(f"Generated Tamil TTS Audio saved at {output_path}")
        return True
    except Exception as e:
        print(f"Failed to generate Tamil TTS: {e}")
        return False
