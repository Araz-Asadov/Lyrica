"""
Music Notes and Chords Extraction Service
Extracts musical information from audio files.
"""
import os
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MusicNotes:
    """Extracted music notes and chords"""
    key: Optional[str] = None  # e.g., "C major", "A minor"
    bpm: Optional[int] = None
    chords: List[str] = None  # e.g., ["C", "G", "Am", "F"]
    notes: List[str] = None  # e.g., ["C", "D", "E", "F", "G"]
    tempo: Optional[str] = None  # e.g., "Allegro", "Andante"
    
    def __post_init__(self):
        if self.chords is None:
            self.chords = []
        if self.notes is None:
            self.notes = []


class NotesExtractionService:
    """Service for extracting musical notes and chords from audio"""
    
    def __init__(self):
        self.has_librosa = self._check_librosa()
    
    def _check_librosa(self) -> bool:
        """Check if librosa is available"""
        try:
            import librosa
            return True
        except ImportError:
            logger.warning("librosa not available, notes extraction will be limited")
            return False
    
    async def extract_notes(self, audio_path: str) -> Optional[MusicNotes]:
        """
        Extract notes and chords from audio file.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            MusicNotes object or None on error
        """
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return None
        
        if not self.has_librosa:
            # Fallback: return basic info
            return MusicNotes(
                key="Unknown",
                bpm=None,
                chords=[],
                notes=[],
            )
        
        try:
            return await self._extract_with_librosa(audio_path)
        except Exception as e:
            logger.error(f"Notes extraction error: {e}")
            return None
    
    async def _extract_with_librosa(self, audio_path: str) -> MusicNotes:
        """Extract notes using librosa"""
        try:
            import librosa
            import numpy as np
        except ImportError:
            logger.error("librosa not available")
            return MusicNotes()
        
        import librosa
        import numpy as np
        
        # Load audio
        y, sr = librosa.load(audio_path, duration=30)  # First 30 seconds
        
        # Extract tempo (BPM)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = int(round(tempo))
        
        # Extract key (tonality)
        # Using chroma features to estimate key
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        
        # Simple key detection (can be improved)
        key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        max_idx = np.argmax(chroma_mean)
        detected_key = key_names[max_idx]
        
        # Determine major/minor (simplified)
        # In a real implementation, you'd use more sophisticated methods
        key = f"{detected_key} major"  # Simplified
        
        # Extract chords (simplified)
        # Real chord detection requires more complex analysis
        chords = self._detect_chords(chroma_mean, key_names)
        
        # Extract notes (simplified - based on pitch)
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        notes = self._extract_notes_from_pitches(pitches, magnitudes, key_names)
        
        return MusicNotes(
            key=key,
            bpm=bpm,
            chords=chords,
            notes=notes[:10],  # Limit to first 10 notes
        )
    
    def _detect_chords(self, chroma: 'np.ndarray', key_names: List[str]) -> List[str]:
        """Simple chord detection based on chroma features"""
        # This is a simplified implementation
        # Real chord detection is much more complex
        chords = []
        
        # Common chord patterns
        chord_patterns = {
            "C": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
            "G": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
            "Am": [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
            "F": [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
        }
        
        # Find best matching chord
        for chord_name, pattern in chord_patterns.items():
            similarity = sum(chroma[i] * pattern[i] for i in range(12))
            if similarity > 0.5:  # Threshold
                chords.append(chord_name)
        
        return chords[:4]  # Return up to 4 chords
    
    def _extract_notes_from_pitches(
        self,
        pitches: 'np.ndarray',
        magnitudes: 'np.ndarray',
        key_names: List[str]
    ) -> List[str]:
        """Extract note sequence from pitch tracking"""
        notes = []
        
        # Find prominent pitches
        threshold = np.percentile(magnitudes, 75)
        prominent_pitches = pitches[magnitudes > threshold]
        
        # Convert frequencies to note names
        for freq in prominent_pitches[:10]:  # Limit to 10
            if freq > 0:
                # Convert frequency to MIDI note number
                midi = 69 + 12 * np.log2(freq / 440.0)
                note_idx = int(round(midi)) % 12
                notes.append(key_names[note_idx])
        
        return notes


# Global instance
_notes_service = None


def get_notes_service() -> NotesExtractionService:
    """Get global notes extraction service instance"""
    global _notes_service
    if _notes_service is None:
        _notes_service = NotesExtractionService()
    return _notes_service

