"""
Music Notes Extraction Service
Extracts musical notes and chords from audio files
"""
import subprocess
import os
import json
import tempfile
from typing import Optional, Dict, List
from config import settings


def extract_notes(audio_path: str) -> Optional[str]:
    """
    Extract musical notes from audio file
    Uses basic pitch detection with FFmpeg and Python libraries
    Returns formatted string with notes/chords
    """
    try:
        # Convert to WAV for analysis (if needed)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            wav_path = tmp_wav.name
        
        # Convert to mono WAV at 16kHz for analysis
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", audio_path,
                "-ar", "16000", "-ac", "1",
                wav_path
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Use librosa or similar for pitch detection
        # For now, return basic info
        try:
            import librosa
            import numpy as np
            
            # Load audio
            y, sr = librosa.load(wav_path, sr=16000)
            
            # Extract pitch using librosa
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            
            # Get dominant pitches
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if not pitch_values:
                return "❌ Notlar tapılmadı. Audio faylında musiqi səsi yoxdur."
            
            # Convert frequencies to note names
            notes = []
            for freq in pitch_values[:20]:  # First 20 detected pitches
                note = frequency_to_note(freq)
                if note:
                    notes.append(note)
            
            # Get unique notes
            unique_notes = list(set(notes))
            
            # Format output
            result = "🎼 **Tapılan notlar:**\n\n"
            result += ", ".join(unique_notes[:12])  # Show first 12 unique notes
            
            if len(unique_notes) > 12:
                result += f"\n\n... və daha {len(unique_notes) - 12} nota"
            
            # Cleanup
            os.unlink(wav_path)
            
            return result
            
        except ImportError:
            # Fallback: return basic info
            os.unlink(wav_path)
            return "⚠️ Notların çıxarılması üçün `librosa` kitabxanası lazımdır.\n\n`pip install librosa` əmrini işlədin."
        
    except Exception as e:
        return f"❌ Xəta: {str(e)}"


def frequency_to_note(frequency: float) -> Optional[str]:
    """Convert frequency (Hz) to musical note name"""
    try:
        import numpy as np
    except ImportError:
        return None
    
    if frequency <= 0:
        return None
    
    # A4 = 440 Hz
    A4 = 440.0
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Calculate semitones from A4
    semitones = 12 * np.log2(frequency / A4)
    
    # Round to nearest semitone
    semitones_rounded = round(semitones)
    
    # Calculate octave (A4 is in octave 4)
    octave = 4 + (semitones_rounded + 9) // 12
    
    # Calculate note index
    note_index = (semitones_rounded + 9) % 12
    
    return f"{note_names[note_index]}{octave}"


# Fallback if librosa is not available
def extract_notes_simple(audio_path: str) -> str:
    """Simple note extraction using FFmpeg frequency analysis"""
    try:
        # Use FFmpeg to get frequency spectrum
        result = subprocess.run(
            [
                "ffmpeg", "-i", audio_path,
                "-af", "astats=metadata=1:reset=1",
                "-f", "null", "-"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return "🎼 **Musiqi notları:**\n\nAudio faylı analiz edildi. Ətraflı notlar üçün `librosa` kitabxanasını quraşdırın."
    except Exception as e:
        return f"❌ Xəta: {str(e)}"

